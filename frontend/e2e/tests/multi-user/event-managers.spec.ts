/**
 * E2E tests for the scoped event manager feature.
 *
 * Covers:
 * 1. Admin UI: assign/remove event managers on /app/event-settings?tab=managers
 * 2. Scoped API permissions: manager can create tasks only in their assigned event
 * 3. Full E2E: admin assigns via UI → manager creates task → admin sees it
 */
import { expect, test } from '../../fixtures.js'
import {
  type EventRead,
  api,
  createEvent,
  deleteEvent,
  futureDate,
  getUserIdByEmail,
  uniqueName,
} from '../../helpers/api.js'

/** Shared task payload for creating a test task in an event. */
function taskPayload(eventId: string, name: string) {
  const date = futureDate(30)
  return {
    name,
    start_date: date,
    end_date: date,
    event_id: eventId,
    schedule: {
      default_start_time: '10:00:00',
      default_end_time: '12:00:00',
      shift_duration_minutes: 60,
      people_per_shift: 2,
      remainder_mode: 'drop',
      overrides: [],
      excluded_shifts: [],
    },
  }
}

function settingsManagersUrl(eventId: string): string {
  return `/app/event-settings?eventId=${eventId}&tab=managers`
}

// ── Admin UI: manage event managers ──────────────────────────────────────────

test.describe('Event Managers – admin UI', () => {
  let event: EventRead

  test.beforeEach(async ({ adminPage }) => {
    event = await createEvent(adminPage, uniqueName('E2E Managers UI'))
  })

  test.afterEach(async ({ adminPage }) => {
    await deleteEvent(adminPage, event.id).catch(() => {})
  })

  test('admin sees the managers tab on /app/event-settings', async ({ adminPage }) => {
    await adminPage.goto(settingsManagersUrl(event.id))
    await expect(adminPage.getByTestId('tab-managers')).toBeVisible()
    await expect(adminPage.getByTestId('section-event-managers')).toBeVisible()
  })

  test('shows empty state when no managers assigned', async ({ adminPage }) => {
    await adminPage.goto(settingsManagersUrl(event.id))
    const section = adminPage.getByTestId('section-event-managers')
    await expect(
      section.getByText(/no.*managers|keine.*verwalter.*zugewiesen/i),
    ).toBeVisible()
  })

  test('admin can assign a member as event manager via UI', async ({ adminPage, memberUser }) => {
    await adminPage.goto(settingsManagersUrl(event.id))
    const section = adminPage.getByTestId('section-event-managers')

    await section.getByRole('button', { name: /add manager|verwalter hinzufügen/i }).click()
    await section
      .getByPlaceholder(/search.*name.*email|benutzer.*suchen/i)
      .fill(memberUser.email)
    await section.getByText(memberUser.name).click()

    await expect(section.getByText(memberUser.name)).toBeVisible()
  })

  test('admin can remove an event manager via UI', async ({ adminPage, memberUser }) => {
    const memberId = await getUserIdByEmail(adminPage, memberUser.email)
    await api(adminPage, 'POST', `/events/${event.id}/managers/${memberId}`)

    await adminPage.goto(settingsManagersUrl(event.id))
    const section = adminPage.getByTestId('section-event-managers')

    await expect(section.getByText(memberUser.name)).toBeVisible()
    const managerRow = section.locator('.rounded-md.border').filter({ hasText: memberUser.name })
    await managerRow.getByRole('button').click()

    await expect(section.getByText(memberUser.name)).toBeHidden()
  })

  test('member is redirected home from the managers tab', async ({ memberPage }) => {
    await memberPage.goto(settingsManagersUrl(event.id))
    await expect(memberPage).toHaveURL(/\/app\/home/)
  })
})

// ── Scoped manager API permissions ───────────────────────────────────────────

test.describe('Event Managers – scoped permissions (API)', () => {
  let event: EventRead
  let memberId: string

  test.beforeEach(async ({ adminPage, memberUser }) => {
    event = await createEvent(adminPage, uniqueName('E2E Scoped Perms'))
    memberId = await getUserIdByEmail(adminPage, memberUser.email)
  })

  test.afterEach(async ({ adminPage }) => {
    await deleteEvent(adminPage, event.id).catch(() => {})
  })

  test('member without assignment cannot create tasks in the event', async ({ memberPage }) => {
    try {
      await api(memberPage, 'POST', '/tasks/with-shifts', taskPayload(event.id, 'Unauthorized'))
      expect(true, 'Expected 403 but request succeeded').toBe(false)
    } catch (e) {
      // eslint-disable-next-line playwright/no-conditional-expect
      expect(String(e)).toContain('403')
    }
  })

  test('assigned manager can create tasks in their event', async ({ adminPage, memberPage }) => {
    await api(adminPage, 'POST', `/events/${event.id}/managers/${memberId}`)

    const result = await api<{ task: { id: string; name: string } }>(
      memberPage,
      'POST',
      '/tasks/with-shifts',
      taskPayload(event.id, 'Scoped Manager Task'),
    )
    expect(result.task.name).toBe('Scoped Manager Task')

    await api(adminPage, 'DELETE', `/tasks/${result.task.id}`)
  })

  test('assigned manager cannot create tasks in a different event', async ({
    adminPage,
    memberPage,
  }) => {
    await api(adminPage, 'POST', `/events/${event.id}/managers/${memberId}`)
    const other = await createEvent(adminPage, uniqueName('E2E Other Event'))

    try {
      await api(memberPage, 'POST', '/tasks/with-shifts', taskPayload(other.id, 'Wrong Event'))
      expect(true, 'Expected 403 but request succeeded').toBe(false)
    } catch (e) {
      // eslint-disable-next-line playwright/no-conditional-expect
      expect(String(e)).toContain('403')
    } finally {
      await deleteEvent(adminPage, other.id)
    }
  })

  test('removing manager revokes task creation access', async ({ adminPage, memberPage }) => {
    await api(adminPage, 'POST', `/events/${event.id}/managers/${memberId}`)
    await api(adminPage, 'DELETE', `/events/${event.id}/managers/${memberId}`)

    try {
      await api(memberPage, 'POST', '/tasks/with-shifts', taskPayload(event.id, 'Revoked'))
      expect(true, 'Expected 403 but request succeeded').toBe(false)
    } catch (e) {
      // eslint-disable-next-line playwright/no-conditional-expect
      expect(String(e)).toContain('403')
    }
  })
})

// ── Full flow: UI assign → API action → UI verification ──────────────────────

test.describe('Event Managers – full E2E flow', () => {
  let event: EventRead

  test.beforeEach(async ({ adminPage }) => {
    event = await createEvent(adminPage, uniqueName('E2E Full Manager Flow'))
  })

  test.afterEach(async ({ adminPage }) => {
    await deleteEvent(adminPage, event.id).catch(() => {})
  })

  test('admin assigns manager via UI, manager creates task, admin sees it', async ({
    adminPage,
    memberPage,
    memberUser,
  }) => {
    // Step 1: admin assigns the member via UI
    await adminPage.goto(settingsManagersUrl(event.id))
    const section = adminPage.getByTestId('section-event-managers')
    await section.getByRole('button', { name: /add manager|verwalter hinzufügen/i }).click()
    await section
      .getByPlaceholder(/search.*name.*email|benutzer.*suchen/i)
      .fill(memberUser.email)
    await section.getByText(memberUser.name).click()
    await expect(section.getByText(memberUser.name)).toBeVisible()

    // Step 2: scoped manager creates a task via API
    const result = await api<{ task: { id: string; name: string } }>(
      memberPage,
      'POST',
      '/tasks/with-shifts',
      taskPayload(event.id, 'Manager Created Task'),
    )

    // Step 3: admin can fetch the manager-created task via API. Verifying via
    // API (instead of the /app/tasks UI, which is scoped to selected_event_id)
    // avoids mutating the admin's selected event — switching it and then
    // deleting this event in afterEach leaves admin.selected_event_id = NULL,
    // which corrupts state for any admin-availability test that runs later.
    const fetched = await api<{ id: string; name: string }>(
      adminPage,
      'GET',
      `/tasks/${result.task.id}`,
    )
    expect(fetched.name).toBe('Manager Created Task')

    await api(adminPage, 'DELETE', `/tasks/${result.task.id}`)
  })
})
