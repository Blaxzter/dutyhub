/**
 * Member-perspective E2E tests for the new event-scoped flows:
 *   - no admin-only pages/controls
 *   - availability lives at /app/availability (scoped to selected event)
 *   - event picker lives at /app/select-event?mode=switch
 *
 * The fixture seeds a workerEvent and sets it as the member's selected_event_id,
 * so the availability tests operate on that shared worker event.
 */
import { expect, test } from '../../fixtures.js'
import { api, clearAvailability, futureDate } from '../../helpers/api.js'
import { pickDate } from '../../helpers/ui.js'

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
  test('settings change action lists the selected worker event in the switcher', async ({
    memberPage: member,
    workerEvent,
  }) => {
    await member.goto('/app/settings/event')
    await member.getByTestId('settings-active-event-change').click()
    await expect(member.getByTestId(`event-switcher-option-${workerEvent.id}`)).toBeVisible()
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

  test('sees Register button when none set', async ({ memberPage: member }) => {
    await member.goto('/app/availability')
    const section = member.getByTestId('section-my-availability')
    await expect(section.getByTestId('btn-availability')).toBeVisible()
  })

  test('can register as fully available', async ({ memberPage: member }) => {
    await member.goto('/app/availability')
    const section = member.getByTestId('section-my-availability')
    await section.getByTestId('btn-availability').click()
    await member.getByTestId('availability-type-fully_available').click()
    await member.getByTestId('btn-save').click()

    await expect(member.getByTestId('dialog-availability')).toBeHidden()
    await expect(section.getByText(/open to be requested|fully.?available/i)).toBeVisible()
    await expect(section.getByTestId('btn-availability')).toBeVisible()
    await expect(section.getByTestId('btn-remove-availability')).toBeVisible()
  })

  test('can register availability for specific dates', async ({ memberPage: member }) => {
    await member.goto('/app/availability')
    const section = member.getByTestId('section-my-availability')
    await section.getByTestId('btn-availability').click()
    await member.getByTestId('availability-type-specific_dates').click()
    await member.getByTestId('btn-add-date').click()
    await pickDate(
      member.getByRole('button', { name: /pick a date|datum/i }).last(),
      futureDate(10),
    )
    await member.getByTestId('btn-save').click()

    await expect(member.getByTestId('dialog-availability')).toBeHidden()
    await expect(section.getByText(/specific dates/i)).toBeVisible()
  })

  test('can update existing availability', async ({ memberPage: member, workerEvent }) => {
    await api(member, 'POST', `/events/${workerEvent.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })

    await member.goto('/app/availability')
    const section = member.getByTestId('section-my-availability')
    await section.getByTestId('btn-availability').click()
    await member.getByTestId('availability-type-specific_dates').click()
    await member.getByTestId('btn-save').click()

    await expect(member.getByTestId('dialog-availability')).toBeHidden()
    await expect(section.getByText(/specific dates/i)).toBeVisible()
  })

  test('can remove availability', async ({ memberPage: member, workerEvent }) => {
    await api(member, 'POST', `/events/${workerEvent.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })

    await member.goto('/app/availability')
    const section = member.getByTestId('section-my-availability')
    member.on('dialog', (d) => d.accept())
    await section.getByTestId('btn-remove-availability').click()

    await expect(section.getByTestId('btn-availability')).toBeVisible()
  })
})
