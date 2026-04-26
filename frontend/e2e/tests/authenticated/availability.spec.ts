/**
 * E2E tests for Availability registration at /app/availability.
 *
 * Availability is now scoped to the user's selected_event_id. The fixture
 * sets `workerEvent` as the selected event for both admin and member, so
 * every test here operates against that shared worker event.
 */
import { expect, test } from '../../fixtures.js'
import { api, clearAvailability, futureDate } from '../../helpers/api.js'
import { pickDate } from '../../helpers/ui.js'

// ── page structure ───────────────────────────────────────────────────────────

test.describe('Availability – page structure', () => {
  test.beforeEach(async ({ adminPage: page, workerEvent }) => {
    await clearAvailability(page, workerEvent.id).catch(() => {})
  })

  test('heading and My Availability section are visible', async ({ adminPage: page }) => {
    await page.goto('/app/availability')
    await expect(page.getByTestId('page-heading')).toBeVisible()
    await expect(page.getByTestId('section-my-availability')).toBeVisible()
  })

  test('admin sees the member availabilities section', async ({ adminPage: page }) => {
    await page.goto('/app/availability')
    await expect(page.getByTestId('section-admin-availabilities')).toBeVisible()
  })
})

// ── register fully available ─────────────────────────────────────────────────

test.describe('Availability – fully available', () => {
  test.beforeEach(async ({ adminPage: page, workerEvent }) => {
    await clearAvailability(page, workerEvent.id).catch(() => {})
  })

  test.afterEach(async ({ adminPage: page, workerEvent }) => {
    await clearAvailability(page, workerEvent.id).catch(() => {})
  })

  test('Register button is visible when no availability set', async ({ adminPage: page }) => {
    await page.goto('/app/availability')
    await expect(page.getByTestId('btn-availability')).toBeVisible()
  })

  test('Register button opens availability dialog', async ({ adminPage: page }) => {
    await page.goto('/app/availability')
    await page.getByTestId('btn-availability').click()
    await expect(page.getByTestId('dialog-availability')).toBeVisible()
  })

  test('dialog shows both availability type options', async ({ adminPage: page }) => {
    await page.goto('/app/availability')
    await page.getByTestId('btn-availability').click()
    await expect(page.getByTestId('dialog-availability')).toBeVisible()
    await expect(page.getByTestId('availability-type-fully_available')).toBeVisible()
    await expect(page.getByTestId('availability-type-specific_dates')).toBeVisible()
  })

  test('Cancel closes the dialog without saving', async ({ adminPage: page }) => {
    await page.goto('/app/availability')
    await page.getByTestId('btn-availability').click()
    await expect(page.getByTestId('dialog-availability')).toBeVisible()
    await page.getByTestId('btn-cancel').click()
    await expect(page.getByTestId('dialog-availability')).toBeHidden()
    await expect(page.getByTestId('btn-availability')).toBeVisible()
  })

  test('can register as fully available', async ({ adminPage: page }) => {
    await page.goto('/app/availability')
    await page.getByTestId('btn-availability').click()
    await page.getByTestId('availability-type-fully_available').click()
    await page.getByTestId('btn-save').click()

    await expect(page.getByTestId('dialog-availability')).toBeHidden()
    const myAvail = page.getByTestId('section-my-availability')
    await expect(myAvail.getByText(/fully.?available|voll.?verfügbar/i)).toBeVisible()
    await expect(page.getByTestId('btn-availability')).toBeVisible()
    await expect(page.getByTestId('btn-remove-availability')).toBeVisible()
  })

  test('can add a note when registering', async ({ adminPage: page }) => {
    await page.goto('/app/availability')
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

  test('can remove availability', async ({ adminPage: page, workerEvent }) => {
    await api(page, 'POST', `/events/${workerEvent.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })

    await page.goto('/app/availability')
    page.on('dialog', (d) => d.accept())
    await page.getByTestId('btn-remove-availability').click()

    await expect(page.getByTestId('btn-availability')).toBeVisible()
  })

  test('can update existing availability', async ({ adminPage: page, workerEvent }) => {
    await api(page, 'POST', `/events/${workerEvent.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })

    await page.goto('/app/availability')
    await page.getByTestId('btn-availability').click()
    await expect(page.getByTestId('dialog-availability')).toBeVisible()

    await page.getByTestId('availability-type-specific_dates').click()
    await page.getByTestId('btn-save').click()

    await expect(page.getByTestId('dialog-availability')).toBeHidden()
    await expect(
      page
        .getByTestId('section-my-availability')
        .getByText(/specific.?dates|bestimmte.?termine/i),
    ).toBeVisible()
  })
})

// ── specific dates ───────────────────────────────────────────────────────────

test.describe('Availability – specific dates', () => {
  test.beforeEach(async ({ adminPage: page, workerEvent }) => {
    await clearAvailability(page, workerEvent.id).catch(() => {})
  })

  test.afterEach(async ({ adminPage: page, workerEvent }) => {
    await clearAvailability(page, workerEvent.id).catch(() => {})
  })

  test('specific dates option reveals date builder', async ({ adminPage: page }) => {
    await page.goto('/app/availability')
    await page.getByTestId('btn-availability').click()
    await page.getByTestId('availability-type-specific_dates').click()
    await expect(page.getByTestId('btn-add-date')).toBeVisible()
  })

  test('can register availability with specific dates', async ({ adminPage: page }) => {
    await page.goto('/app/availability')
    await page.getByTestId('btn-availability').click()
    await page.getByTestId('availability-type-specific_dates').click()

    await page.getByTestId('btn-add-date').click()
    // Pick a date within the worker event's range (worker event spans day+1 to day+60)
    const dateInRange = futureDate(10)
    await pickDate(
      page.getByRole('button', { name: /pick a date|datum/i }).last(),
      dateInRange,
    )

    await page.getByTestId('btn-save').click()
    await expect(page.getByTestId('dialog-availability')).toBeHidden()
    await expect(
      page
        .getByTestId('section-my-availability')
        .getByText(/specific.?dates|bestimmte.?termine/i),
    ).toBeVisible()
  })

  test('registering specific dates via API shows them in UI', async ({
    adminPage: page,
    workerEvent,
  }) => {
    const date1 = futureDate(10)
    const date2 = futureDate(11)
    await api(page, 'POST', `/events/${workerEvent.id}/availability`, {
      availability_type: 'specific_dates',
      dates: [date1, date2],
    })

    await page.goto('/app/availability')
    await expect(
      page
        .getByTestId('section-my-availability')
        .getByText(/specific.?dates|bestimmte.?termine/i),
    ).toBeVisible()
    await expect(page.getByTestId(`date-${date1}`)).toBeVisible()
    await expect(page.getByTestId(`date-${date2}`)).toBeVisible()
  })
})

// ── admin: member availability table ─────────────────────────────────────────

test.describe('Admin – member availability table', () => {
  test.beforeEach(async ({ adminPage: page, workerEvent }) => {
    await clearAvailability(page, workerEvent.id).catch(() => {})
  })

  test.afterEach(async ({ adminPage: page, workerEvent }) => {
    await clearAvailability(page, workerEvent.id).catch(() => {})
  })

  test('empty state is shown when no members have registered', async ({ adminPage: page }) => {
    await page.goto('/app/availability')
    await expect(
      page
        .getByTestId('section-admin-availabilities')
        .getByText(/no members have registered|keine mitglieder.*verfügbarkeit/i),
    ).toBeVisible()
  })

  test('registered availability appears in admin table', async ({
    adminPage: page,
    workerEvent,
  }) => {
    await api(page, 'POST', `/events/${workerEvent.id}/availability`, {
      availability_type: 'fully_available',
      notes: 'E2E admin table test',
      dates: [],
    })

    await page.goto('/app/availability')
    await expect(
      page.getByText(/fully.?available|open to be requested|voll.?verfügbar/i).nth(1),
    ).toBeVisible()
  })
})
