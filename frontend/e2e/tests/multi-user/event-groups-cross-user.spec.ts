/**
 * Cross-user E2E tests — scenarios requiring both an admin and a member session.
 *
 * Uses browser.newContext() with explicit storage states so both users
 * can be active in the same test.
 */

import { expect, test } from '@playwright/test'
import { api, clearAvailability, createGroup, deleteGroup } from '../../helpers/api'
import type { EventGroupRead } from '../../helpers/api'

// ── Admin creates group → member sees it ─────────────────────────────────────

test.describe('Cross-user – visibility', () => {
  test('admin-published group is visible to member', async ({ browser }) => {
    const adminCtx = await browser.newContext({ storageState: 'e2e/.auth/user.json' })
    const memberCtx = await browser.newContext({ storageState: 'e2e/.auth/member.json' })
    const adminPage = await adminCtx.newPage()
    const memberPage = await memberCtx.newPage()

    await adminPage.goto('/app/event-groups')
    const group = await createGroup(adminPage, 'E2E Cross Published Group')

    try {
      await memberPage.goto('/app/event-groups')
      await expect(memberPage.getByText(group.name)).toBeVisible()
    } finally {
      await deleteGroup(adminPage, group.id)
      await adminCtx.close()
      await memberCtx.close()
    }
  })

  test('admin draft group is hidden from member', async ({ browser }) => {
    const adminCtx = await browser.newContext({ storageState: 'e2e/.auth/user.json' })
    const memberCtx = await browser.newContext({ storageState: 'e2e/.auth/member.json' })
    const adminPage = await adminCtx.newPage()
    const memberPage = await memberCtx.newPage()

    await adminPage.goto('/app/event-groups')
    const draft = await createGroup(adminPage, 'E2E Cross Draft Group', 'draft')

    try {
      await memberPage.goto('/app/event-groups')
      await expect(memberPage.getByText(draft.name)).toBeHidden()
    } finally {
      await deleteGroup(adminPage, draft.id)
      await adminCtx.close()
      await memberCtx.close()
    }
  })
})

// ── Member registers availability → admin sees it ────────────────────────────

test.describe('Cross-user – availability flow', () => {
  let group: EventGroupRead

  test.beforeEach(async ({ browser }) => {
    const adminCtx = await browser.newContext({ storageState: 'e2e/.auth/user.json' })
    const adminPage = await adminCtx.newPage()
    await adminPage.goto('/app/event-groups')
    group = await createGroup(adminPage, 'E2E Cross Availability Group')
    await adminCtx.close()
  })

  test.afterEach(async ({ browser }) => {
    const adminCtx = await browser.newContext({ storageState: 'e2e/.auth/user.json' })
    const adminPage = await adminCtx.newPage()
    await adminPage.goto('/app/event-groups')
    await deleteGroup(adminPage, group.id)
    await adminCtx.close()
  })

  test('member availability appears in admin member table', async ({ browser }) => {
    const adminCtx = await browser.newContext({ storageState: 'e2e/.auth/user.json' })
    const memberCtx = await browser.newContext({ storageState: 'e2e/.auth/member.json' })
    const adminPage = await adminCtx.newPage()
    const memberPage = await memberCtx.newPage()

    try {
      // Member registers availability via UI
      await memberPage.goto(`/app/event-groups/${group.id}`)
      await memberPage.getByRole('button', { name: /register availability/i }).click()
      await memberPage.getByText(/open to be requested|fully.?available/i).click()
      await memberPage.getByRole('button', { name: /save/i }).click()
      await expect(memberPage.getByRole('button', { name: /update|change/i })).toBeVisible()

      // Admin sees the entry in the member availability table
      await adminPage.goto(`/app/event-groups/${group.id}`)
      await expect(
        adminPage.getByText(/fully.?available|open to be requested/i).nth(1),
      ).toBeVisible({ timeout: 5000 })
    } finally {
      await clearAvailability(memberPage, group.id).catch(() => {})
      await adminCtx.close()
      await memberCtx.close()
    }
  })

  test('member removing availability is reflected in admin table', async ({ browser }) => {
    const adminCtx = await browser.newContext({ storageState: 'e2e/.auth/user.json' })
    const memberCtx = await browser.newContext({ storageState: 'e2e/.auth/member.json' })
    const adminPage = await adminCtx.newPage()
    const memberPage = await memberCtx.newPage()

    try {
      // Pre-seed availability as member via API
      await memberPage.goto(`/app/event-groups/${group.id}`)
      await api(memberPage, 'POST', `/event-groups/${group.id}/availability`, {
        availability_type: 'fully_available',
        dates: [],
      })

      // Member removes it via UI
      await memberPage.reload()
      memberPage.on('dialog', (d) => d.accept())
      await memberPage.getByRole('button', { name: /remove/i }).click()
      await expect(memberPage.getByRole('button', { name: /register availability/i })).toBeVisible({
        timeout: 5000,
      })

      // Admin table shows empty state
      await adminPage.goto(`/app/event-groups/${group.id}`)
      await expect(adminPage.getByText(/no.*(members|registrations|availability)/i)).toBeVisible()
    } finally {
      await clearAvailability(memberPage, group.id).catch(() => {})
      await adminCtx.close()
      await memberCtx.close()
    }
  })

  test('multiple members availability visible to admin', async ({ browser }) => {
    const adminCtx = await browser.newContext({ storageState: 'e2e/.auth/user.json' })
    const memberCtx = await browser.newContext({ storageState: 'e2e/.auth/member.json' })
    const adminPage = await adminCtx.newPage()
    const memberPage = await memberCtx.newPage()

    try {
      // Admin registers as fully available
      await adminPage.goto(`/app/event-groups/${group.id}`)
      await api(adminPage, 'POST', `/event-groups/${group.id}/availability`, {
        availability_type: 'fully_available',
        dates: [],
      })

      // Member registers with specific dates
      await memberPage.goto(`/app/event-groups/${group.id}`)
      await api(memberPage, 'POST', `/event-groups/${group.id}/availability`, {
        availability_type: 'specific_dates',
        dates: ['2026-06-10', '2026-06-11'],
      })

      // Admin sees both entries in the table
      await adminPage.reload()
      const rows = adminPage.getByText(/fully.?available|specific.?dates/i)
      await expect(rows).toHaveCount(2, { timeout: 5000 })
    } finally {
      await clearAvailability(adminPage, group.id).catch(() => {})
      await clearAvailability(memberPage, group.id).catch(() => {})
      await adminCtx.close()
      await memberCtx.close()
    }
  })
})
