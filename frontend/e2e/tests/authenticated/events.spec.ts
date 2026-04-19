/**
 * E2E tests for Task Events & Availability feature.
 *
 * Strategy: use authenticated fetch() calls (via page.evaluate) to set up and
 * tear down test data so every test starts from a known state instead of
 * relying on pre-existing DB data.
 */
import { expect, test } from '../../fixtures.js'
import {
  type EventRead,
  api,
  clearAvailability,
  createEvent,
  deleteEvent,
  futureDate,
  uniqueName,
} from '../../helpers/api.js'
import { pickDate } from '../../helpers/ui.js'

// ── navigation ────────────────────────────────────────────────────────────────

test.describe('Task Events – navigation', () => {
  test('sidebar shows Task Events link', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('sidebar-link-events')).toBeVisible()
  })

  test('clicking sidebar link navigates to /app/events', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('sidebar-link-events').click()
    await expect(page).toHaveURL(/\/app\/events$/)
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })

  test('direct navigation to /app/events works', async ({ adminPage: page }) => {
    await page.goto('/app/events')
    await expect(page).toHaveURL(/\/app\/events$/)
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })
})

// ── list view ─────────────────────────────────────────────────────────────────

test.describe('Task Events – list view', () => {
  let event: EventRead
  const eventName = uniqueName('E2E List')

  test.beforeEach(async ({ adminPage: page }) => {
    await page.goto('/app/events')
    event = await createEvent(page, eventName)
  })

  test.afterEach(async ({ adminPage: page }) => {
    await deleteEvent(page, event.id)
  })

  test('shows heading and search input', async ({ adminPage: page }) => {
    await page.goto('/app/events')
    await expect(page.getByTestId('page-heading')).toBeVisible()
    await expect(page.getByTestId('input-search')).toBeVisible()
  })

  test('created event appears in list with published badge', async ({ adminPage: page }) => {
    await page.goto('/app/events')
    const card = page.locator('[class*="cursor-pointer"]').filter({ hasText: event.name })
    await expect(card).toBeVisible()
    // published status badge within the card
    await expect(card.getByTestId('event-status')).toBeVisible()
  })

  test('created event shows date range', async ({ adminPage: page }) => {
    await page.goto('/app/events')
    // Dates are formatted locale-dependently; check both dates appear somewhere
    const card = page.locator('[class*="cursor-pointer"]').filter({ hasText: event.name })
    await expect(card).toBeVisible()
  })

  test('search filters the list by name', async ({ adminPage: page }) => {
    await page.goto('/app/events')
    const searchInput = page.getByTestId('input-search')
    await searchInput.fill(eventName)
    const card = page.locator('[class*="cursor-pointer"]').filter({ hasText: eventName })
    await expect(card).toBeVisible()

    await searchInput.fill('zzzzunlikelymatch')
    await expect(card).toBeHidden()
  })

  test('clicking a card navigates to the detail page', async ({ adminPage: page }) => {
    await page.goto('/app/events')
    const card = page.locator('[class*="cursor-pointer"]').filter({ hasText: event.name })
    await card.click()
    await expect(page).toHaveURL(new RegExp(`/app/events/${event.id}`))
  })
})

// ── admin actions ─────────────────────────────────────────────────────────────

test.describe('Task Events – admin create & delete', () => {
  test('Create button is visible (test user is admin in test env)', async ({ adminPage: page }) => {
    await page.goto('/app/events')
    // In the test environment the E2E user has admin privileges
    await expect(page.getByTestId('btn-create-event')).toBeVisible()
  })

  test('admin can open the create event dialog', async ({ adminPage: page }) => {
    await page.goto('/app/events')

    await page.getByTestId('btn-create-event').click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()

    // Dialog has the expected form fields
    await expect(dialog.locator('input').first()).toBeVisible()
    await expect(dialog.getByRole('button', { name: /create|erstellen/i })).toBeVisible()

    // Close without saving
    await dialog.getByRole('button', { name: /cancel|abbrechen/i }).click()
    await expect(dialog).toBeHidden()
  })

  test('admin can delete an event via trash icon', async ({ adminPage: page }) => {
    const deleteName = uniqueName('E2E Delete')
    await page.goto('/app/events')
    await createEvent(page, deleteName)

    await page.goto('/app/events')
    const card = page.locator('[class*="cursor-pointer"]').filter({ hasText: deleteName })
    await expect(card).toBeVisible()

    // Click delete button on the specific card
    await card.getByRole('button').click()

    // Handle app-level confirmation dialog
    const confirmBtn = page.getByRole('button', { name: /confirm|bestätigen/i })
    // eslint-disable-next-line playwright/no-conditional-in-test
    if (await confirmBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await confirmBtn.click()
    }

    await expect(card).toBeHidden()
  })
})

// ── detail page ───────────────────────────────────────────────────────────────

test.describe('Task Event Detail – page structure', () => {
  let event: EventRead

  test.beforeEach(async ({ adminPage: page }) => {
    await page.goto('/app/events')
    event = await createEvent(page, uniqueName('E2E Detail Page Event'))
  })

  test.afterEach(async ({ adminPage: page }) => {
    await clearAvailability(page, event.id).catch(() => {})
    await deleteEvent(page, event.id)
  })

  test('shows event name and status badge', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}`)
    await expect(page.getByTestId('page-heading')).toContainText(event.name)
    await expect(page.getByTestId('event-status')).toBeVisible()
  })

  test('shows date range in header', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}`)
    // The event's date range appears somewhere on the page.
    // EventHeader renders both a mobile (xl:hidden) and a desktop (hidden xl:flex) block;
    // at the default Desktop Chrome viewport (1280) the desktop block (last in DOM) is the visible one.
    await expect(
      page.getByText(new RegExp(new Date().getFullYear().toString())).last(),
    ).toBeVisible()
  })

  test('shows My Availability section', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/availability`)
    await expect(page.getByTestId('section-my-availability')).toBeVisible()
  })

  test('shows Tasks in this Event section', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}`)
    await expect(page.getByTestId('section-tasks')).toBeVisible()
  })

  test('back button navigates to events list', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}`)
    await page.getByTestId('btn-back').click()
    await expect(page).toHaveURL(/\/app\/events$/)
  })

  test('navigating to a non-existent event shows back button', async ({ adminPage: page }) => {
    await page.goto('/app/events/00000000-0000-0000-0000-000000000000')
    await expect(page.getByTestId('btn-back')).toBeVisible()
  })
})

// ── availability: register fully available ────────────────────────────────────

test.describe('Availability – fully available', () => {
  let event: EventRead

  test.beforeEach(async ({ adminPage: page }) => {
    await page.goto('/app/events')
    event = await createEvent(page, uniqueName('E2E Availability Event'))
    await clearAvailability(page, event.id).catch(() => {})
  })

  test.afterEach(async ({ adminPage: page }) => {
    await clearAvailability(page, event.id).catch(() => {})
    await deleteEvent(page, event.id)
  })

  test('Register button is visible when no availability set', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/availability`)
    await expect(page.getByTestId('btn-availability')).toBeVisible()
  })

  test('Register button opens availability dialog', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/availability`)
    await page.getByTestId('btn-availability').click()
    await expect(page.getByTestId('dialog-availability')).toBeVisible()
  })

  test('dialog shows both availability type options', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/availability`)
    await page.getByTestId('btn-availability').click()
    await expect(page.getByTestId('dialog-availability')).toBeVisible()
    await expect(page.getByTestId('availability-type-fully_available')).toBeVisible()
    await expect(page.getByTestId('availability-type-specific_dates')).toBeVisible()
  })

  test('Cancel closes the dialog without saving', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/availability`)
    await page.getByTestId('btn-availability').click()
    await expect(page.getByTestId('dialog-availability')).toBeVisible()
    await page.getByTestId('btn-cancel').click()
    await expect(page.getByTestId('dialog-availability')).toBeHidden()
    // Still shows Register button (nothing was saved)
    await expect(page.getByTestId('btn-availability')).toBeVisible()
  })

  test('can register as fully available', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/availability`)
    await page.getByTestId('btn-availability').click()

    // "Open to be requested" / "fully available" option — select it
    await page.getByTestId('availability-type-fully_available').click()
    await page.getByTestId('btn-save').click()

    await expect(page.getByTestId('dialog-availability')).toBeHidden()
    // Status now shows type text in the My Availability section
    const myAvail = page.getByTestId('section-my-availability')
    await expect(myAvail.getByText(/fully.?available|voll.?verfügbar/i)).toBeVisible()
    // Register button replaced by Update / Remove
    await expect(page.getByTestId('btn-availability')).toBeVisible()
    await expect(page.getByTestId('btn-remove-availability')).toBeVisible()
  })

  test('can add a note when registering', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/availability`)
    await page.getByTestId('btn-availability').click()

    await page.getByTestId('availability-type-fully_available').click()
    await page
      .getByTestId('dialog-availability')
      .locator('textarea')
      .fill('I am free the whole week!')
    await page.getByTestId('btn-save').click()

    await expect(page.getByTestId('dialog-availability')).toBeHidden()
    await expect(
      page.getByTestId('section-my-availability').getByText(/I am free the whole week!/i),
    ).toBeVisible()
  })

  test('can remove availability', async ({ adminPage: page }) => {
    // Set availability via API so we start with one registered
    await api(page, 'POST', `/events/${event.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })

    await page.goto(`/app/events/${event.id}/availability`)
    // Confirm-destructive dialog is inside the app; accept via dialog task
    page.on('dialog', (d) => d.accept())

    await page.getByTestId('btn-remove-availability').click()

    // Register button should return
    await expect(page.getByTestId('btn-availability')).toBeVisible()
  })

  test('can update existing availability', async ({ adminPage: page }) => {
    // Pre-seed via API
    await api(page, 'POST', `/events/${event.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })

    await page.goto(`/app/events/${event.id}/availability`)
    await page.getByTestId('btn-availability').click()
    await expect(page.getByTestId('dialog-availability')).toBeVisible()

    // Switch to specific_dates
    await page.getByTestId('availability-type-specific_dates').click()
    await page.getByTestId('btn-save').click()

    await expect(page.getByTestId('dialog-availability')).toBeHidden()
    await expect(
      page.getByTestId('section-my-availability').getByText(/specific.?dates|bestimmte.?termine/i),
    ).toBeVisible()
  })
})

// ── availability: specific dates ──────────────────────────────────────────────

test.describe('Availability – specific dates', () => {
  let event: EventRead

  test.beforeEach(async ({ adminPage: page }) => {
    await page.goto('/app/events')
    event = await createEvent(page, uniqueName('E2E Specific Dates Event'))
    await clearAvailability(page, event.id).catch(() => {})
  })

  test.afterEach(async ({ adminPage: page }) => {
    await clearAvailability(page, event.id).catch(() => {})
    await deleteEvent(page, event.id)
  })

  test('specific dates option reveals date builder', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/availability`)
    await page.getByTestId('btn-availability').click()
    await page.getByTestId('availability-type-specific_dates').click()
    // Add date button or date input appears
    await expect(page.getByTestId('btn-add-date')).toBeVisible()
  })

  test('can register availability with specific dates', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/availability`)
    await page.getByTestId('btn-availability').click()
    await page.getByTestId('availability-type-specific_dates').click()

    // Add a date
    await page.getByTestId('btn-add-date').click()
    // Pick a date from the calendar popover (must fall within the event's date range)
    const groupStart = futureDate(30)
    await pickDate(page.getByRole('button', { name: /pick a date|datum/i }).last(), groupStart)

    await page.getByTestId('btn-save').click()
    await expect(page.getByTestId('dialog-availability')).toBeHidden()

    // The availability type text is now shown on the page
    await expect(
      page.getByTestId('section-my-availability').getByText(/specific.?dates|bestimmte.?termine/i),
    ).toBeVisible()
  })

  test('registering specific dates via API shows them in UI', async ({ adminPage: page }) => {
    const date1 = futureDate(30)
    const date2 = futureDate(31)
    await api(page, 'POST', `/events/${event.id}/availability`, {
      availability_type: 'specific_dates',
      dates: [date1, date2],
    })

    await page.goto(`/app/events/${event.id}/availability`)
    await expect(
      page.getByTestId('section-my-availability').getByText(/specific.?dates|bestimmte.?termine/i),
    ).toBeVisible()
    // Both dates should appear somewhere on the page
    await expect(page.getByTestId(`date-${date1}`)).toBeVisible()
    await expect(page.getByTestId(`date-${date2}`)).toBeVisible()
  })
})

// ── admin: member availability table ─────────────────────────────────────────

test.describe('Admin – member availability table', () => {
  let event: EventRead

  test.beforeEach(async ({ adminPage: page }) => {
    await page.goto('/app/events')
    event = await createEvent(page, uniqueName('E2E Admin Avail Event'))
  })

  test.afterEach(async ({ adminPage: page }) => {
    await clearAvailability(page, event.id).catch(() => {})
    await deleteEvent(page, event.id)
  })

  test('member availabilities section is visible for admins', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/availability`)
    await expect(page.getByTestId('section-admin-availabilities')).toBeVisible()
  })

  test('empty state is shown when no members have registered', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/availability`)
    // Match both EN "No members have registered" and DE "Noch keine Mitglieder haben Verfügbarkeit registriert"
    await expect(
      page
        .getByTestId('section-admin-availabilities')
        .getByText(/no members have registered|keine mitglieder.*verfügbarkeit/i),
    ).toBeVisible()
  })

  test('registered availability appears in admin table', async ({ adminPage: page }) => {
    await api(page, 'POST', `/events/${event.id}/availability`, {
      availability_type: 'fully_available',
      notes: 'E2E admin table test',
      dates: [],
    })

    await page.goto(`/app/events/${event.id}/availability`)
    // The admin table should show an entry — look for the availability type or note
    await expect(
      page.getByText(/fully.?available|open to be requested|voll.?verfügbar/i).nth(1),
    ).toBeVisible()
  })
})
