/**
 * E2E tests for the scoped event manager feature.
 *
 * Covers:
 * 1. Admin UI: assign/remove event managers, visibility of management section
 * 2. Scoped API permissions: manager can create tasks only in their assigned event
 * 3. Full E2E: admin assigns via UI -> manager creates task -> admin sees it
 */
import { expect, test } from '../../fixtures.js'
import {
  type EventRead,
  api,
  createEvent,
  deleteEvent,
  futureDate,
  uniqueName,
} from '../../helpers/api.js'

/** Look up a test user's UUID by email (admin-only endpoint). */
async function getMemberId(
  adminPage: import('@playwright/test').Page,
  email: string,
): Promise<string> {
  const res = await api<{ items: { id: string; email: string }[] }>(
    adminPage,
    'GET',
    '/users/?limit=200',
  )
  const member = res.items.find((u) => u.email === email)
  if (!member) throw new Error(`User ${email} not found`)
  return member.id
}

/** Shared task payload for creating a test task in an event. */
function eventPayload(eventId: string, name: string) {
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

// ── Admin UI: manage event managers ──────────────────────────────────────────

test.describe('Event Managers – admin UI', () => {
  let event: EventRead

  test.beforeEach(async ({ adminPage }) => {
    await adminPage.goto('/app/events')
    event = await createEvent(adminPage, uniqueName('E2E Managers UI'))
  })

  test.afterEach(async ({ adminPage }) => {
    await deleteEvent(adminPage, event.id)
  })

  test('admin sees the Management section', async ({ adminPage }) => {
    await adminPage.goto(`/app/events/${event.id}/management`)
    const section = adminPage.getByTestId('section-management')
    await expect(section.getByTestId('section-event-managers')).toBeVisible()
  })

  test('shows empty state when no managers assigned', async ({ adminPage }) => {
    await adminPage.goto(`/app/events/${event.id}/management`)
    const section = adminPage.getByTestId('section-management')
    await expect(
      section.getByText(/no.*scoped.*managers|keine.*verwalter.*zugewiesen/i),
    ).toBeVisible()
  })

  test('admin can assign a member as event manager', async ({
    adminPage,
    memberUser,
  }) => {
    await adminPage.goto(`/app/events/${event.id}/management`)

    // Open the add manager panel
    await adminPage.getByRole('button', { name: /add manager|verwalter hinzufügen/i }).click()

    // Search for the member user
    await adminPage
      .getByPlaceholder(/search.*name.*email|benutzer.*suchen/i)
      .fill(memberUser.email)

    // Click the member in the results list
    await adminPage.getByText(memberUser.name).click()

    // Manager now appears in the list
    await expect(adminPage.getByText(memberUser.name)).toBeVisible()
  })

  test('admin can remove a event manager', async ({
    adminPage,
    memberUser,
  }) => {
    // Assign via API
    const memberId = await getMemberId(adminPage, memberUser.email)
    await api(adminPage, 'POST', `/events/${event.id}/managers/${memberId}`)

    await adminPage.goto(`/app/events/${event.id}/management`)
    const section = adminPage.getByTestId('section-management')

    // Wait for manager to appear, then click the remove (X) button
    await expect(section.getByText(memberUser.name)).toBeVisible()
    const managerRow = section.locator('.rounded-md.border').filter({ hasText: memberUser.name })
    await managerRow.getByRole('button').click()

    // Manager is removed from the list
    await expect(section.getByText(memberUser.name)).toBeHidden()
  })

  test('member does not see the Management section', async ({ memberPage }) => {
    await memberPage.goto(`/app/events/${event.id}`)
    await expect(memberPage.getByTestId('section-event-managers')).toBeHidden()
  })
})

// ── Scoped manager API permissions ───────────────────────────────────────────

test.describe('Event Managers – scoped permissions (API)', () => {
  let event: EventRead
  let memberId: string

  test.beforeEach(async ({ adminPage, memberUser }) => {
    await adminPage.goto('/app/events')
    event = await createEvent(adminPage, uniqueName('E2E Scoped Perms'))
    memberId = await getMemberId(adminPage, memberUser.email)
  })

  test.afterEach(async ({ adminPage }) => {
    await deleteEvent(adminPage, event.id)
  })

  test('member without assignment cannot create tasks in event', async ({
    memberPage,
  }) => {
    try {
      await api(memberPage, 'POST', '/tasks/with-shifts', eventPayload(event.id, 'Unauthorized'))
      expect(true, 'Expected 403 but request succeeded').toBe(false)
    } catch (e) {
      // eslint-disable-next-line playwright/no-conditional-expect
      expect(String(e)).toContain('403')
    }
  })

  test('assigned event manager can create tasks in the event', async ({
    adminPage,
    memberPage,
  }) => {
    await api(adminPage, 'POST', `/events/${event.id}/managers/${memberId}`)

    const result = await api<{ task: { id: string; name: string } }>(
      memberPage,
      'POST',
      '/tasks/with-shifts',
      eventPayload(event.id, 'Scoped Manager Task'),
    )
    expect(result.task.name).toBe('Scoped Manager Task')

    await api(adminPage, 'DELETE', `/tasks/${result.task.id}`)
  })

  test('assigned event manager cannot create tasks in a different event', async ({
    adminPage,
    memberPage,
  }) => {
    await api(adminPage, 'POST', `/events/${event.id}/managers/${memberId}`)
    const groupB = await createEvent(adminPage, uniqueName('E2E Other Event'))

    try {
      await api(memberPage, 'POST', '/tasks/with-shifts', eventPayload(groupB.id, 'Wrong Event'))
      expect(true, 'Expected 403 but request succeeded').toBe(false)
    } catch (e) {
      // eslint-disable-next-line playwright/no-conditional-expect
      expect(String(e)).toContain('403')
    } finally {
      await deleteEvent(adminPage, groupB.id)
    }
  })

  test('removing event manager revokes task creation access', async ({
    adminPage,
    memberPage,
  }) => {
    await api(adminPage, 'POST', `/events/${event.id}/managers/${memberId}`)
    await api(adminPage, 'DELETE', `/events/${event.id}/managers/${memberId}`)

    try {
      await api(memberPage, 'POST', '/tasks/with-shifts', eventPayload(event.id, 'Revoked'))
      expect(true, 'Expected 403 but request succeeded').toBe(false)
    } catch (e) {
      // eslint-disable-next-line playwright/no-conditional-expect
      expect(String(e)).toContain('403')
    }
  })
})

// ── Full E2E flow: UI assignment -> API action -> UI verification ────────────

test.describe('Event Managers – full E2E flow', () => {
  let event: EventRead

  test.beforeEach(async ({ adminPage }) => {
    await adminPage.goto('/app/events')
    event = await createEvent(adminPage, uniqueName('E2E Full Manager Flow'))
  })

  test.afterEach(async ({ adminPage }) => {
    await deleteEvent(adminPage, event.id)
  })

  test('admin assigns manager via UI, manager creates task, admin sees it', async ({
    adminPage,
    memberPage,
    memberUser,
  }) => {
    // Step 1: Admin assigns the member as event manager via UI
    await adminPage.goto(`/app/events/${event.id}/management`)
    await adminPage.getByRole('button', { name: /add manager|verwalter hinzufügen/i }).click()
    await adminPage
      .getByPlaceholder(/search.*name.*email|benutzer.*suchen/i)
      .fill(memberUser.email)
    await adminPage.getByText(memberUser.name).click()
    await expect(adminPage.getByText(memberUser.name)).toBeVisible()

    // Step 2: Scoped manager creates a task via API
    const result = await api<{ task: { id: string; name: string } }>(
      memberPage,
      'POST',
      '/tasks/with-shifts',
      eventPayload(event.id, 'Manager Created Task'),
    )

    // Step 3: Admin sees the task on the event detail page
    await adminPage.goto(`/app/events/${event.id}`)
    await expect(adminPage.getByRole('heading', { name: 'Manager Created Task' })).toBeVisible()

    await api(adminPage, 'DELETE', `/tasks/${result.task.id}`)
  })
})
