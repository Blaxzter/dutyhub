/**
 * Member-perspective E2E tests for the new event-scoped flows:
 *   - no admin-only pages/controls
 *   - availability lives at /app/availability (scoped to selected event)
 *   - event picker lives at /app/select-event?mode=switch
 *
 * The fixture seeds a workerEvent and sets it as the member's selected_event_id,
 * so the availability tests operate on that shared worker event.
 *
 * Availability is now an inline editor (mode picker + Save), not a dialog —
 * see commit 649a9f5 (refactor: remove AvailabilityDialog/AvailabilityDisplay).
 */
import { expect, test } from '../../fixtures.js'
import { api, clearAvailability } from '../../helpers/api.js'

// ── RBAC: member cannot reach admin pages or see admin controls ──────────────

test.describe('Member – RBAC', () => {
  test('member does not see the Manage Events sidebar link', async ({ memberPage: member }) => {
    await member.goto('/app/home')
    await expect(member.getByTestId('sidebar-link-admin-events')).toBeHidden()
  })

  test('member is redirected home from /app/admin/events', async ({ memberPage: member }) => {
    await member.goto('/app/admin/events')
    await expect(member).toHaveURL(/\/app\/home/)
  })

  test('member is redirected home from /app/event-settings', async ({ memberPage: member }) => {
    await member.goto('/app/event-settings')
    await expect(member).toHaveURL(/\/app\/home/)
  })

  test('member does not see the Create Event button on the picker', async ({
    memberPage: member,
  }) => {
    await member.goto('/app/select-event?mode=switch')
    await expect(member.getByTestId('select-event-create-card')).toBeHidden()
  })

  test('member does not see the member availabilities admin section', async ({
    memberPage: member,
  }) => {
    await member.goto('/app/availability')
    await expect(member.getByTestId('section-admin-availabilities')).toBeHidden()
  })
})

// ── Event picker: member can change selected event ───────────────────────────

test.describe('Member – event picker', () => {
  test('settings change action navigates to the picker with the worker event listed', async ({
    memberPage: member,
    workerEvent,
  }) => {
    await member.goto('/app/settings/event')
    await member.getByTestId('settings-active-event-change').click()
    await expect(member).toHaveURL(/\/app\/select-event/)
    await expect(member.getByText(workerEvent.name).first()).toBeVisible()
  })
})

// ── Member availability lives under /app/availability ────────────────────────

test.describe('Member – availability', () => {
  test.beforeEach(async ({ memberPage: member, workerEvent }) => {
    await clearAvailability(member, workerEvent.id).catch(() => {})
  })

  test.afterEach(async ({ memberPage: member, workerEvent }) => {
    await clearAvailability(member, workerEvent.id).catch(() => {})
  })

  test('mode picker is visible when no availability is set', async ({ memberPage: member }) => {
    await member.goto('/app/availability')
    const section = member.getByTestId('section-my-availability')
    await expect(section).toBeVisible()
    await expect(member.getByTestId('availability-type-fully_available').first()).toBeVisible()
  })

  test('can register as fully available', async ({ memberPage: member }) => {
    await member.goto('/app/availability')
    await member.getByTestId('availability-type-fully_available').first().click()
    await member.getByTestId('btn-save').click()

    const section = member.getByTestId('section-my-availability')
    await expect(section.getByText(/fully.?available|voll.?verfügbar/i).first()).toBeVisible()
    await expect(member.getByTestId('btn-remove-availability')).toBeVisible()
  })

  test('switching availability type enables Save', async ({ memberPage: member }) => {
    await member.goto('/app/availability')
    // The default mode for an unregistered user is specific_dates, so picking
    // a different mode is what actually dirties the form.
    await member.getByTestId('availability-type-fully_available').first().click()
    await expect(member.getByTestId('btn-save')).toBeEnabled()
  })

  test('can update existing availability', async ({ memberPage: member, workerEvent }) => {
    await api(member, 'POST', `/events/${workerEvent.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })

    await member.goto('/app/availability')
    await member.getByTestId('availability-type-specific_dates').first().click()
    await member.getByTestId('btn-save').click()

    // After saving an empty specific_dates payload, the remove button stays
    // visible (a record still exists) but the fully-available banner is gone.
    await expect(member.getByTestId('btn-remove-availability')).toBeVisible()
  })

  test('can remove availability', async ({ memberPage: member, workerEvent }) => {
    await api(member, 'POST', `/events/${workerEvent.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })

    await member.goto('/app/availability')
    await member.getByTestId('btn-remove-availability').click()

    // App-level confirm-destructive dialog
    const confirmBtn = member.getByRole('button', { name: /confirm|bestätigen/i })
    if (await confirmBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await confirmBtn.click()
    }

    await expect(member.getByTestId('btn-remove-availability')).toBeHidden()
  })
})
