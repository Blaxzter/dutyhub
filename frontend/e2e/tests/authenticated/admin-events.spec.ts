/**
 * E2E tests for the admin Manage Events page (/app/admin/events).
 *
 * The old /app/events page was replaced by a split:
 *   - /app/select-event (user-facing picker, covered in select-event.spec.ts)
 *   - /app/admin/events (this spec — table/CRUD view for admins)
 */
import { expect, test } from '../../fixtures.js'
import {
  type EventRead,
  createEvent,
  deleteEvent,
  uniqueName,
} from '../../helpers/api.js'

// ── navigation ────────────────────────────────────────────────────────────────

test.describe('Admin Events – navigation', () => {
  test('sidebar shows Manage Events link (admin)', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('sidebar-link-admin-events')).toBeVisible()
  })

  test('clicking sidebar link navigates to /app/admin/events', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('sidebar-link-admin-events').click()
    await expect(page).toHaveURL(/\/app\/admin\/events$/)
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })

  test('direct navigation to /app/admin/events works', async ({ adminPage: page }) => {
    await page.goto('/app/admin/events')
    await expect(page).toHaveURL(/\/app\/admin\/events$/)
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })

  test('member is redirected home from /app/admin/events', async ({ memberPage: member }) => {
    await member.goto('/app/admin/events')
    // Guard in router redirects unauthorized users to /app/home
    await expect(member).toHaveURL(/\/app\/home/)
  })
})

// ── list view ─────────────────────────────────────────────────────────────────

test.describe('Admin Events – list view', () => {
  let event: EventRead
  const eventName = uniqueName('E2E Admin List')

  test.beforeEach(async ({ adminPage: page }) => {
    event = await createEvent(page, eventName)
  })

  test.afterEach(async ({ adminPage: page }) => {
    await deleteEvent(page, event.id).catch(() => {})
  })

  test('shows heading and search input', async ({ adminPage: page }) => {
    await page.goto('/app/admin/events')
    await expect(page.getByTestId('page-heading')).toBeVisible()
    await expect(page.getByTestId('input-search')).toBeVisible()
  })

  test('created event appears as a table row', async ({ adminPage: page }) => {
    await page.goto('/app/admin/events')
    const row = page.getByTestId('admin-event-row').filter({ hasText: event.name })
    await expect(row).toBeVisible()
  })

  test('row exposes edit and delete actions', async ({ adminPage: page }) => {
    await page.goto('/app/admin/events')
    const row = page.getByTestId('admin-event-row').filter({ hasText: event.name })
    await expect(row.getByTestId('btn-edit-event')).toBeVisible()
    await expect(row.getByTestId('btn-delete-event')).toBeVisible()
  })

  test('search filters the list by name', async ({ adminPage: page }) => {
    await page.goto('/app/admin/events')
    const searchInput = page.getByTestId('input-search')
    const row = page.getByTestId('admin-event-row').filter({ hasText: event.name })

    await searchInput.fill(event.name)
    await expect(row).toBeVisible()

    await searchInput.fill('zzzzunlikelymatch')
    await expect(row).toBeHidden()
  })

  test('clicking edit navigates to /app/event-settings with eventId', async ({
    adminPage: page,
  }) => {
    await page.goto('/app/admin/events')
    const row = page.getByTestId('admin-event-row').filter({ hasText: event.name })
    await row.getByTestId('btn-edit-event').click()
    await expect(page).toHaveURL(new RegExp(`/app/event-settings\\?eventId=${event.id}`))
  })
})

// ── create & delete ───────────────────────────────────────────────────────────

test.describe('Admin Events – create & delete', () => {
  test('Create button is visible for admin', async ({ adminPage: page }) => {
    await page.goto('/app/admin/events')
    await expect(page.getByTestId('btn-create-event')).toBeVisible()
  })

  test('admin can open the create event dialog', async ({ adminPage: page }) => {
    await page.goto('/app/admin/events')
    await page.getByTestId('btn-create-event').click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.locator('input').first()).toBeVisible()
    await expect(dialog.getByRole('button', { name: /create|erstellen/i })).toBeVisible()

    await dialog.getByRole('button', { name: /cancel|abbrechen/i }).click()
    await expect(dialog).toBeHidden()
  })

  test('admin can delete an event via trash icon', async ({ adminPage: page }) => {
    const deleteName = uniqueName('E2E Admin Delete')
    const created = await createEvent(page, deleteName)

    await page.goto('/app/admin/events')
    const row = page.getByTestId('admin-event-row').filter({ hasText: deleteName })
    await expect(row).toBeVisible()

    await row.getByTestId('btn-delete-event').click()

    // App-level confirm-destructive dialog
    const confirmBtn = page.getByRole('button', { name: /confirm|bestätigen/i })
    if (await confirmBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await confirmBtn.click()
    }

    await expect(row).toBeHidden()
    // Double-confirm via API
    await deleteEvent(page, created.id).catch(() => {})
  })
})
