/**
 * E2E tests for the admin Manage Events page (/app/events).
 *
 * The old /app/events page was replaced by a split:
 *   - /app/select-event (user-facing picker, covered in select-event.spec.ts)
 *   - /app/events (this spec — table/CRUD view for admins)
 */
import { expect, test } from '../../fixtures.js'
import {
  type EventRead,
  createEvent,
  deleteEvent,
  futureDate,
  uniqueName,
} from '../../helpers/api.js'
import { pickDate } from '../../helpers/ui.js'

// ── navigation ────────────────────────────────────────────────────────────────

test.describe('Admin Events – navigation', () => {
  test('sidebar shows Manage Events link (admin)', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('sidebar-link-my-events')).toBeVisible()
  })

  test('clicking sidebar link navigates to /app/events', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('sidebar-link-my-events').click()
    await expect(page).toHaveURL(/\/app\/events$/)
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })

  test('direct navigation to /app/events works', async ({ adminPage: page }) => {
    await page.goto('/app/events')
    await expect(page).toHaveURL(/\/app\/events$/)
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })

  test('member is redirected home from /app/events', async ({ memberPage: member }) => {
    await member.goto('/app/events')
    // The page is for people who run an event; a plain participant runs none,
    // so the router sends them home.
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
    await page.goto('/app/events')
    await expect(page.getByTestId('page-heading')).toBeVisible()
    await expect(page.getByTestId('input-search')).toBeVisible()
  })

  test('created event appears as a table row', async ({ adminPage: page }) => {
    await page.goto('/app/events')
    const row = page.getByTestId('admin-event-row').filter({ hasText: event.name })
    await expect(row).toBeVisible()
  })

  test('row exposes edit and delete actions', async ({ adminPage: page }) => {
    await page.goto('/app/events')
    const row = page.getByTestId('admin-event-row').filter({ hasText: event.name })
    await expect(row.getByTestId('btn-edit-event')).toBeVisible()
    await expect(row.getByTestId('btn-delete-event')).toBeVisible()
  })

  test('search filters the list by name', async ({ adminPage: page }) => {
    await page.goto('/app/events')
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
    await page.goto('/app/events')
    const row = page.getByTestId('admin-event-row').filter({ hasText: event.name })
    await row.getByTestId('btn-edit-event').click()
    await expect(page).toHaveURL(new RegExp(`/app/event-settings/${event.id}`))
  })
})

// ── create & delete ───────────────────────────────────────────────────────────

test.describe('Admin Events – create & delete', () => {
  test('Create button is visible for admin', async ({ adminPage: page }) => {
    await page.goto('/app/events')
    await expect(page.getByTestId('btn-create-event')).toBeVisible()
  })

  test('create button opens the create event page', async ({ adminPage: page }) => {
    await page.goto('/app/events')
    await page.getByTestId('btn-create-event').click()

    await expect(page).toHaveURL(/\/app\/events\/create/)
    await expect(page.getByTestId('input-event-name')).toBeVisible()
    // Nothing filled in yet, so there is nothing to submit.
    await expect(page.getByTestId('btn-submit-create-event')).toBeDisabled()

    await page.getByTestId('btn-cancel-create-event').click()
    await expect(page).toHaveURL(/\/app\/events$/)
  })

  test('admin can create an event from the create page', async ({ adminPage: page }) => {
    const name = uniqueName('E2E Created From View')
    await page.goto('/app/events/create')

    await page.getByTestId('input-event-name').fill(name)
    await pickDate(page.getByTestId('picker-start-date').getByRole('button'), futureDate(30))
    await pickDate(page.getByTestId('picker-end-date').getByRole('button'), futureDate(34))
    await expect(page.getByTestId('btn-submit-create-event')).toBeEnabled()

    const [response] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/events/') && r.request().method() === 'POST',
      ),
      page.getByTestId('btn-submit-create-event').click(),
    ])
    const created = (await response.json()) as EventRead

    // Lands back on the list with the new event in it.
    await expect(page).toHaveURL(/\/app\/events$/)
    await page.getByTestId('input-search').fill(name)
    await expect(page.getByTestId('admin-event-row').filter({ hasText: name })).toBeVisible()

    await deleteEvent(page, created.id).catch(() => {})
  })

  test('admin can delete an event via trash icon', async ({ adminPage: page }) => {
    const deleteName = uniqueName('E2E Admin Delete')
    const created = await createEvent(page, deleteName)

    await page.goto('/app/events')
    // Active list is paginated (PAGE_SIZE=4); search to scope reliably.
    await page.getByTestId('input-search').fill(deleteName)
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
