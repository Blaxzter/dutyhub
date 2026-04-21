/**
 * Cross-user E2E tests for the event picker and availability flows.
 *
 * Replaces the old event-groups-cross-user.spec.ts which operated on the
 * removed /app/events/:id/availability route. Under the new scoped-UI model
 * the worker fixture points both users' selected_event_id at the same
 * `workerEvent`, so these tests exercise that shared event.
 */
import { expect, test } from '../../fixtures.js'
import {
  api,
  clearAvailability,
  createEvent,
  deleteEvent,
  futureDate,
  uniqueName,
} from '../../helpers/api.js'

// ── Picker visibility (admin-published vs draft) ─────────────────────────────

test.describe('Cross-user – picker visibility', () => {
  test('admin-published event appears in the member picker', async ({ adminPage, memberPage }) => {
    const event = await createEvent(adminPage, uniqueName('E2E Cross Published'))
    try {
      await memberPage.goto('/app/select-event?mode=switch')
      await expect(memberPage.getByText(event.name).first()).toBeVisible()
    } finally {
      await deleteEvent(adminPage, event.id)
    }
  })

  test('admin draft event is hidden from the member picker', async ({
    adminPage,
    memberPage,
  }) => {
    const draft = await createEvent(adminPage, uniqueName('E2E Cross Draft'), 'draft')
    try {
      await memberPage.goto('/app/select-event?mode=switch')
      await expect(memberPage.getByText(draft.name)).toBeHidden()
    } finally {
      await deleteEvent(adminPage, draft.id)
    }
  })
})

// ── Availability flow between member and admin ───────────────────────────────

test.describe('Cross-user – availability flow', () => {
  test.beforeEach(async ({ adminPage, memberPage, workerEvent }) => {
    await clearAvailability(adminPage, workerEvent.id).catch(() => {})
    await clearAvailability(memberPage, workerEvent.id).catch(() => {})
  })

  test.afterEach(async ({ adminPage, memberPage, workerEvent }) => {
    await clearAvailability(adminPage, workerEvent.id).catch(() => {})
    await clearAvailability(memberPage, workerEvent.id).catch(() => {})
  })

  test('member availability appears in admin member table', async ({ adminPage, memberPage }) => {
    await memberPage.goto('/app/availability')
    const memberSection = memberPage.getByTestId('section-my-availability')
    await memberSection.getByTestId('btn-availability').click()
    await memberPage.getByTestId('availability-type-fully_available').click()
    await memberPage.getByTestId('btn-save').click()
    await expect(memberSection.getByTestId('btn-availability')).toBeVisible()

    await adminPage.goto('/app/availability')
    const adminTable = adminPage.getByTestId('section-admin-availabilities')
    await expect(
      adminTable.getByText(/fully.?available|open to be requested/i),
    ).toBeVisible()
  })

  test('member removing availability is reflected in admin table', async ({
    adminPage,
    memberPage,
    workerEvent,
  }) => {
    await api(memberPage, 'POST', `/events/${workerEvent.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })

    await memberPage.goto('/app/availability')
    const memberSection = memberPage.getByTestId('section-my-availability')
    await memberSection.getByTestId('btn-remove-availability').click()

    // App-level confirm-destructive dialog
    await memberPage.getByTestId('btn-dialog-confirm').click()
    await expect(memberSection.getByTestId('btn-availability')).toBeVisible()

    await adminPage.goto('/app/availability')
    const adminTable = adminPage.getByTestId('section-admin-availabilities')
    await expect(
      adminTable.getByText(/no.*(members|registrations|availability)/i),
    ).toBeVisible()
  })

  test('admin sees multiple members in the availability table', async ({
    adminPage,
    memberPage,
    workerEvent,
  }) => {
    await api(adminPage, 'POST', `/events/${workerEvent.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })
    await api(memberPage, 'POST', `/events/${workerEvent.id}/availability`, {
      availability_type: 'specific_dates',
      dates: [futureDate(10), futureDate(11)],
    })

    await adminPage.goto('/app/availability')
    const adminTable = adminPage.getByTestId('section-admin-availabilities')
    const rows = adminTable.getByText(/fully.?available|specific.?dates/i)
    await expect(rows).toHaveCount(2)
  })
})
