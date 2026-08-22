/**
 * Cross-user E2E tests for the event picker and availability flows.
 *
 * Replaces the old event-groups-cross-user.spec.ts which operated on the
 * removed /app/events/:id/availability route. Under the new scoped-UI model
 * the worker fixture points both users' selected_event_id at the same
 * `workerEvent`, so these tests exercise that shared event.
 *
 * Availability is now an inline editor and the admin team view renders a
 * heatmap with one row per member (commit 649a9f5).
 */
import { expect, test } from '../../fixtures.js'
import {
  addMember,
  api,
  clearAvailability,
  createEvent,
  deleteEvent,
  futureDate,
  uniqueName,
} from '../../helpers/api.js'

// ── Picker visibility (admin-published vs draft) ─────────────────────────────

test.describe('Cross-user – picker visibility', () => {
  test('an event the member joined appears in My events', async ({
    adminPage,
    memberPage,
    memberUser,
  }) => {
    const event = await createEvent(adminPage, uniqueName('E2E Cross Published'))
    try {
      await addMember(adminPage, memberPage, event.id, memberUser.email)
      await memberPage.goto('/app/select-event?mode=switch')
      await expect(memberPage.getByText(event.name).first()).toBeVisible()
    } finally {
      await deleteEvent(adminPage, event.id)
    }
  })

  test('a public event the member has not joined shows under Discover', async ({
    adminPage,
    memberPage,
  }) => {
    const event = await createEvent(adminPage, uniqueName('E2E Cross Discover'))
    try {
      await memberPage.goto('/app/select-event?mode=switch')
      // Not a member yet, so it must not be in the "My events" list…
      await expect(memberPage.getByText(event.name)).toBeHidden()
      // …but it is public, so Discover offers it.
      await memberPage.getByTestId('tab-discover').click()
      await expect(memberPage.getByText(event.name).first()).toBeVisible()
    } finally {
      await deleteEvent(adminPage, event.id)
    }
  })

  test('a private event the member is not in stays hidden everywhere', async ({
    adminPage,
    memberPage,
  }) => {
    const secret = await createEvent(
      adminPage,
      uniqueName('E2E Cross Private'),
      'published',
      'private',
    )
    try {
      await memberPage.goto('/app/select-event?mode=switch')
      await expect(memberPage.getByText(secret.name)).toBeHidden()
      await memberPage.getByTestId('tab-discover').click()
      await expect(memberPage.getByText(secret.name)).toBeHidden()
    } finally {
      await deleteEvent(adminPage, secret.id)
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

  test('member availability appears in admin team heatmap', async ({
    adminPage,
    memberPage,
    memberUser,
  }) => {
    await memberPage.goto('/app/availability')
    await memberPage.getByTestId('availability-type-fully_available').first().click()
    await memberPage.getByTestId('btn-save').click()
    await expect(memberPage.getByTestId('btn-remove-availability')).toBeVisible()

    // The admin page fetches the availabilities list once on mount; under
    // parallel worker load the backend write is occasionally not yet visible
    // to the follow-up GET. Re-navigate until the row surfaces.
    await expect(async () => {
      await adminPage.goto('/app/availability')
      const adminSection = adminPage.getByTestId('section-admin-availabilities')
      await expect(adminSection.getByText(memberUser.name).first()).toBeVisible({
        timeout: 2_000,
      })
    }).toPass({ timeout: 15_000 })
  })

  test('member removing availability is reflected in admin team view', async ({
    adminPage,
    memberPage,
    workerEvent,
  }) => {
    await api(memberPage, 'POST', `/events/${workerEvent.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })

    await memberPage.goto('/app/availability')
    await memberPage.getByTestId('btn-remove-availability').click()

    // App-level confirm-destructive dialog
    const confirmBtn = memberPage.getByRole('button', { name: /confirm|bestätigen/i })
    if (await confirmBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await confirmBtn.click()
    }
    await expect(memberPage.getByTestId('btn-remove-availability')).toBeHidden()

    await expect(async () => {
      await adminPage.goto('/app/availability')
      const adminSection = adminPage.getByTestId('section-admin-availabilities')
      await expect(
        adminSection.getByText(/no teammates have registered|noch keine teammitglieder/i),
      ).toBeVisible({ timeout: 2_000 })
    }).toPass({ timeout: 15_000 })
  })

  test('admin sees multiple members in the team heatmap', async ({
    adminPage,
    memberPage,
    workerEvent,
    adminUser,
    memberUser,
  }) => {
    await api(adminPage, 'POST', `/events/${workerEvent.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })
    await api(memberPage, 'POST', `/events/${workerEvent.id}/availability`, {
      availability_type: 'specific_dates',
      dates: [futureDate(10), futureDate(11)],
    })

    await expect(async () => {
      await adminPage.goto('/app/availability')
      const adminSection = adminPage.getByTestId('section-admin-availabilities')
      await expect(adminSection.getByText(adminUser.name).first()).toBeVisible({
        timeout: 2_000,
      })
      await expect(adminSection.getByText(memberUser.name).first()).toBeVisible({
        timeout: 2_000,
      })
    }).toPass({ timeout: 15_000 })
  })
})
