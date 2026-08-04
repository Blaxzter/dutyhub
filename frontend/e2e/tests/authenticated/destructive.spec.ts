/**
 * E2E tests for the destructive account flows (issue #136).
 *
 * Every test here mutates or removes the account it runs as, so they all use
 * the test-scoped `disposableUser` / `disposablePage` fixtures. The
 * worker-scoped `adminUser` / `memberUser` / `workerEvent` are shared by every
 * test the worker runs and must never be the target of a destructive action.
 */
import type { Locator, Page } from '@playwright/test'

import { IS_TESTING, expect, seedUser, serverApi, serverApiRaw, test } from '../../fixtures.js'

/**
 * The fixtures pin the UI locale to English (localStorage `locale` plus the
 * seeded `preferred_language`), so matching the row menu and the status badge
 * by their English label is deterministic. Keys live in
 * `src/locales/en/admin.json` under `users.*`.
 */
const MENU = {
  activate: 'Activate',
  deactivate: 'Deactivate',
  makeAdmin: 'Make Admin',
  removeAdmin: 'Remove Admin',
} as const

const STATUS = {
  active: 'Active',
  pending: 'Pending',
} as const

/** `src/locales/en/user.json` → `settings.deleteAccount.*` */
const DELETE_ACCOUNT = {
  trigger: 'Delete My Account',
  confirm: 'Yes, delete my account',
} as const

/** `src/locales/en/common.json` → `pendingApproval.approvalWrongPassword` */
const WRONG_APPROVAL_CODE = 'Invalid approval code. Please try again.'

// These flows need accounts that can be seeded and destroyed at will, which
// only exists in isolated mode. Auth0 mode has no throwaway users.
test.beforeEach(() => {
  // eslint-disable-next-line playwright/no-skipped-test -- Auth0 mode cannot seed or delete disposable users
  test.skip(!IS_TESTING, 'Destructive flows require the isolated TESTING backend')
})

/** Open the admin users page and narrow the table down to one user's row. */
async function findUserRow(page: Page, email: string): Promise<Locator> {
  await page.goto('/app/admin/users')
  const table = page.getByTestId('users-table')
  await expect(table).toBeVisible()
  await page.getByTestId('users-search').fill(email)
  const row = table.getByRole('row').filter({ hasText: email })
  await expect(row).toBeVisible()
  return row
}

/** Click one entry of the ⋮ actions menu on a users-table row. */
async function runRowAction(page: Page, row: Locator, item: string): Promise<void> {
  // The row's only button is the dropdown trigger; the menu itself is portalled
  // to the document body, so it is looked up from the page rather than the row.
  await row.getByRole('button').click()
  await page.getByRole('menuitem', { name: item, exact: true }).click()
}

/**
 * Save a new approval password from the card on the admin users page.
 *
 * The card's controls are icon-only buttons in a fixed order —
 * [show/hide, save, clear] — and a successful save clears the input again,
 * which is what we wait on.
 */
async function setApprovalPassword(card: Locator, password: string): Promise<void> {
  const input = card.locator('input[name="wirksam-approval-password"]')
  await input.fill(password)
  await card.getByRole('button').nth(1).click()
  await expect(input).toHaveValue('')
}

test.describe('Destructive – account self-deletion', () => {
  test('a user deletes their own account and loses access', async ({
    adminUser,
    disposablePage,
    disposableUser,
  }) => {
    await disposablePage.goto('/app/settings/dataPrivacy')
    const section = disposablePage.getByTestId('section-dataPrivacy')
    await expect(section).toBeVisible()

    await section.getByRole('button', { name: DELETE_ACCOUNT.trigger }).click()
    const dialog = disposablePage.getByRole('dialog')
    await expect(dialog).toBeVisible()

    // The confirmation word is translated, and the input's placeholder *is*
    // that word — read it back instead of hard-coding "DELETE".
    const confirmInput = dialog.getByRole('textbox')
    const confirmWord = (await confirmInput.getAttribute('placeholder')) ?? ''
    await confirmInput.fill(confirmWord)
    await dialog.getByRole('button', { name: DELETE_ACCOUNT.confirm }).click()

    // The record is gone: an admin lookup 404s.
    await expect
      .poll(
        async () => {
          const res = await serverApiRaw('GET', `/users/${disposableUser.id}`, adminUser.email)
          return res.status
        },
        { message: 'admin lookup of the deleted account should 404' },
      )
      .toBe(404)

    // The session is dead too — the identity no longer resolves to a user.
    const profile = await serverApiRaw('POST', '/users/me', disposableUser.email)
    expect(profile.status).toBe(401)

    // And the SPA can no longer reach an authenticated page.
    await disposablePage.goto('/app/home')
    await expect(disposablePage).not.toHaveURL(/\/app\/home/)
  })
})

test.describe('Destructive – deactivate and reactivate', () => {
  test('deactivating blocks a user and reactivating restores access', async ({
    adminPage,
    disposablePage,
    disposableUser,
  }) => {
    // Baseline: the account works.
    await expect(disposablePage).toHaveURL(/\/app\/home/)

    const row = await findUserRow(adminPage, disposableUser.email)
    await expect(row).toContainText(STATUS.active)
    await runRowAction(adminPage, row, MENU.deactivate)
    await expect(row).toContainText(STATUS.pending)

    // The blocked user is bounced to the pending-approval screen…
    await disposablePage.goto('/app/home')
    await expect(disposablePage).toHaveURL(/\/pending-approval/)

    // …and endpoints that require an active account reject them.
    const blocked = await serverApiRaw('GET', '/users/me/export', disposableUser.email)
    expect(blocked.status).toBe(403)

    const rowAgain = await findUserRow(adminPage, disposableUser.email)
    await runRowAction(adminPage, rowAgain, MENU.activate)
    await expect(rowAgain).toContainText(STATUS.active)

    await disposablePage.goto('/app/home')
    await expect(disposablePage).toHaveURL(/\/app\/home/)
    await expect(disposablePage.getByTestId('page-heading')).toBeVisible()

    const restored = await serverApiRaw('GET', '/users/me/export', disposableUser.email)
    expect(restored.status).toBe(200)
  })
})

test.describe('Destructive – grant and revoke admin', () => {
  test('the admin role opens and closes the admin area for that user', async ({
    adminPage,
    disposablePage,
    disposableUser,
  }) => {
    const adminNavLink = disposablePage.getByTestId('sidebar-link-admin-users')

    // Baseline: a plain member has neither the nav entry nor the route.
    await expect(adminNavLink).toBeHidden()
    await disposablePage.goto('/app/admin/users')
    await expect(disposablePage).toHaveURL(/\/app\/home/)

    const row = await findUserRow(adminPage, disposableUser.email)
    await runRowAction(adminPage, row, MENU.makeAdmin)
    await expect(row).toContainText('admin')

    // A fresh load re-fetches the profile, so the sidebar picks the role up.
    await disposablePage.goto('/app/home')
    await expect(adminNavLink).toBeVisible()
    await adminNavLink.click()
    await expect(disposablePage).toHaveURL(/\/app\/admin\/users/)
    await expect(disposablePage.getByTestId('users-table')).toBeVisible()

    const rowAgain = await findUserRow(adminPage, disposableUser.email)
    await runRowAction(adminPage, rowAgain, MENU.removeAdmin)
    await expect(rowAgain).not.toContainText('admin')

    await disposablePage.goto('/app/admin/users')
    await expect(disposablePage).toHaveURL(/\/app\/home/)
    await expect(adminNavLink).toBeHidden()
  })
})

test.describe('Destructive – pending approval', () => {
  test.use({ disposableUserOptions: { isActive: false } })

  test('an admin approves a pending user and unlocks the app', async ({
    adminPage,
    disposablePage,
    disposableUser,
  }) => {
    // A pending account never gets past the approval screen.
    await expect(disposablePage).toHaveURL(/\/pending-approval/)
    await expect(disposablePage.getByTestId('btn-withdraw')).toBeVisible()

    const row = await findUserRow(adminPage, disposableUser.email)
    await expect(row).toContainText(STATUS.pending)
    await runRowAction(adminPage, row, MENU.activate)
    await expect(row).toContainText(STATUS.active)

    await disposablePage.goto('/app/home')
    await expect(disposablePage).toHaveURL(/\/app\/home/)
    await expect(disposablePage.getByTestId('page-heading')).toBeVisible()
  })
})

test.describe('Destructive – approval password', () => {
  test.use({ disposableUserOptions: { isActive: false } })

  // The approval password is global site state, so it is always handed back
  // cleared — a leftover password would change what other tests see on the
  // admin users page and on the pending-approval screen.
  test.afterEach(async ({ adminUser }) => {
    await serverApi('PATCH', '/settings/', adminUser.email, { approval_password: null })
  })

  test('a pending user self-approves, and rotating the password revokes the old one', async ({
    adminPage,
    disposablePage,
    disposableUser,
  }) => {
    // Saving copies the password to the clipboard.
    await adminPage.context().grantPermissions(['clipboard-read', 'clipboard-write'])

    await adminPage.goto('/app/admin/users')
    const card = adminPage.getByTestId('section-approval-password')
    await expect(card).toBeVisible()

    const firstPassword = `e2e-approve-${Date.now()}`
    await setApprovalPassword(card, firstPassword)

    // Pending users may read the status even though they cannot read settings.
    const status = await serverApi<{ has_approval_password: boolean }>(
      'GET',
      '/users/approval-password-status',
      disposableUser.email,
    )
    expect(status.has_approval_password).toBe(true)

    // The waiting screen fetched the status on mount, before the password
    // existed, so reload to make the self-approval form appear.
    await expect(disposablePage).toHaveURL(/\/pending-approval/)
    await disposablePage.reload()
    await disposablePage.getByTestId('input-approval-code').fill(firstPassword)
    await disposablePage.getByTestId('btn-approve').click()
    await expect(disposablePage).toHaveURL(/\/app\/home/)

    // Rotate the password, then push the same account back into the pending
    // state so the rotation can be proven through the same UI.
    const secondPassword = `e2e-rotated-${Date.now()}`
    await setApprovalPassword(card, secondPassword)
    await seedUser(disposableUser.email, disposableUser.name, disposableUser.roles, false)

    await disposablePage.goto('/app/home')
    await expect(disposablePage).toHaveURL(/\/pending-approval/)

    // The retired password is rejected…
    await disposablePage.getByTestId('input-approval-code').fill(firstPassword)
    await disposablePage.getByTestId('btn-approve').click()
    await expect(disposablePage.getByText(WRONG_APPROVAL_CODE)).toBeVisible()
    await expect(disposablePage).toHaveURL(/\/pending-approval/)

    // …while the rotated one is accepted.
    await disposablePage.getByTestId('input-approval-code').fill(secondPassword)
    await disposablePage.getByTestId('btn-approve').click()
    await expect(disposablePage).toHaveURL(/\/app\/home/)
  })
})
