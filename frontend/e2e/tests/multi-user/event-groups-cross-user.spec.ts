/**
 * Cross-user E2E tests -- scenarios requiring both an admin and a member session.
 *
 * Uses adminPage/memberPage fixtures for isolated auth.
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
import type { EventRead } from '../../helpers/api.js'

// ── Admin creates event -> member sees it ─────────────────────────────────────

test.describe('Cross-user – visibility', () => {
  test('admin-published event is visible to member', async ({ adminPage, memberPage }) => {
    await adminPage.goto('/app/events')
    const event = await createEvent(adminPage, uniqueName('E2E Cross Published Event'))

    try {
      await memberPage.goto('/app/events')
      await expect(memberPage.getByRole('heading', { name: event.name })).toBeVisible()
    } finally {
      await deleteEvent(adminPage, event.id)
    }
  })

  test('admin draft event is hidden from member', async ({ adminPage, memberPage }) => {
    await adminPage.goto('/app/events')
    const draft = await createEvent(adminPage, uniqueName('E2E Cross Draft Event'), 'draft')

    try {
      await memberPage.goto('/app/events')
      await expect(memberPage.getByText(draft.name)).toBeHidden()
    } finally {
      await deleteEvent(adminPage, draft.id)
    }
  })
})

// ── Member registers availability -> admin sees it ────────────────────────────

test.describe('Cross-user – availability flow', () => {
  let event: EventRead

  test.beforeEach(async ({ adminPage }) => {
    await adminPage.goto('/app/events')
    event = await createEvent(adminPage, uniqueName('E2E Cross Availability Event'))
  })

  test.afterEach(async ({ adminPage }) => {
    await deleteEvent(adminPage, event.id)
  })

  test('member availability appears in admin member table', async ({ adminPage, memberPage }) => {
    // Member registers availability via UI
    await memberPage.goto(`/app/events/${event.id}/availability`)
    const memberSection = memberPage.getByTestId('section-availability')
    await memberSection.getByTestId('btn-availability').click()
    await memberPage.getByTestId('availability-type-fully_available').click()
    await memberPage.getByTestId('btn-save').click()
    await expect(memberSection.getByTestId('btn-availability')).toBeVisible()

    // Admin sees the entry in the member availability table
    await adminPage.goto(`/app/events/${event.id}/availability`)
    const adminSection = adminPage.getByTestId('section-availability')
    await expect(adminSection.getByTestId('section-admin-availabilities').getByText(/fully.?available|open to be requested/i)).toBeVisible()

    await clearAvailability(memberPage, event.id).catch(() => {})
  })

  test('member removing availability is reflected in admin table', async ({
    adminPage,
    memberPage,
  }) => {
    // Pre-seed availability as member via API
    await memberPage.goto(`/app/events/${event.id}/availability`)
    await api(memberPage, 'POST', `/events/${event.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })

    // Member removes it via UI
    await memberPage.reload()
    const memberSection = memberPage.getByTestId('section-availability')
    await memberSection.getByTestId('btn-remove-availability').click()

    // Handle app-level confirmation dialog
    await memberPage.getByTestId('btn-dialog-confirm').click()
    await expect(memberSection.getByTestId('btn-availability')).toBeVisible()

    // Admin table shows empty state
    await adminPage.goto(`/app/events/${event.id}/availability`)
    const adminSection2 = adminPage.getByTestId('section-availability')
    await expect(adminSection2.getByTestId('section-admin-availabilities').getByText(/no.*(members|registrations|availability)/i)).toBeVisible()
  })

  test('multiple members availability visible to admin', async ({ adminPage, memberPage }) => {
    // Admin registers as fully available
    await adminPage.goto(`/app/events/${event.id}/availability`)
    await api(adminPage, 'POST', `/events/${event.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })

    // Member registers with specific dates
    await memberPage.goto(`/app/events/${event.id}/availability`)
    await api(memberPage, 'POST', `/events/${event.id}/availability`, {
      availability_type: 'specific_dates',
      dates: [futureDate(30), futureDate(31)],
    })

    // Admin sees both entries in the table
    await adminPage.reload()
    const adminSection = adminPage.getByTestId('section-availability')
    const rows = adminSection.getByTestId('section-admin-availabilities').getByText(/fully.?available|specific.?dates/i)
    await expect(rows).toHaveCount(2)

    await clearAvailability(adminPage, event.id).catch(() => {})
    await clearAvailability(memberPage, event.id).catch(() => {})
  })
})
