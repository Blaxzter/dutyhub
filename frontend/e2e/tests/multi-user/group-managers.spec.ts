/**
 * E2E tests for the scoped group manager feature.
 *
 * Covers:
 * 1. Admin UI: assign/remove group managers, visibility of management section
 * 2. Scoped API permissions: manager can create events only in their assigned group
 * 3. Full E2E: admin assigns via UI -> manager creates event -> admin sees it
 */
import { expect, test } from '../../fixtures.js'
import {
  type EventGroupRead,
  api,
  createGroup,
  deleteGroup,
  futureDate,
  uniqueName,
} from '../../helpers/api.js'

/** Look up a test user's UUID by email (admin-only endpoint). */
async function getMemberId(
  adminPage: import('@playwright/test').Page,
  email: string,
): Promise<string> {
  const users = await api<{ id: string; email: string }[]>(
    adminPage,
    'GET',
    '/users/?limit=200',
  )
  const member = users.find((u) => u.email === email)
  if (!member) throw new Error(`User ${email} not found`)
  return member.id
}

/** Shared event payload for creating a test event in a group. */
function eventPayload(groupId: string, name: string) {
  const date = futureDate(30)
  return {
    name,
    start_date: date,
    end_date: date,
    event_group_id: groupId,
    schedule: {
      default_start_time: '10:00:00',
      default_end_time: '12:00:00',
      slot_duration_minutes: 60,
      people_per_slot: 2,
      remainder_mode: 'drop',
      overrides: [],
      excluded_slots: [],
    },
  }
}

// ── Admin UI: manage group managers ──────────────────────────────────────────

test.describe('Group Managers – admin UI', () => {
  let group: EventGroupRead

  test.beforeEach(async ({ adminPage }) => {
    await adminPage.goto('/app/event-groups')
    group = await createGroup(adminPage, uniqueName('E2E Managers UI'))
  })

  test.afterEach(async ({ adminPage }) => {
    await deleteGroup(adminPage, group.id)
  })

  test('admin sees the Management section', async ({ adminPage }) => {
    await adminPage.goto(`/app/event-groups/${group.id}/management`)
    const section = adminPage.getByTestId('section-management')
    await expect(section.getByTestId('section-group-managers')).toBeVisible()
  })

  test('shows empty state when no managers assigned', async ({ adminPage }) => {
    await adminPage.goto(`/app/event-groups/${group.id}/management`)
    const section = adminPage.getByTestId('section-management')
    await expect(
      section.getByText(/no.*scoped.*managers|keine.*verwalter.*zugewiesen/i),
    ).toBeVisible()
  })

  test('admin can assign a member as group manager', async ({
    adminPage,
    memberUser,
  }) => {
    await adminPage.goto(`/app/event-groups/${group.id}/management`)

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

  test('admin can remove a group manager', async ({
    adminPage,
    memberUser,
  }) => {
    // Assign via API
    const memberId = await getMemberId(adminPage, memberUser.email)
    await api(adminPage, 'POST', `/event-groups/${group.id}/managers/${memberId}`)

    await adminPage.goto(`/app/event-groups/${group.id}/management`)
    const section = adminPage.getByTestId('section-management')

    // Wait for manager to appear, then click the remove (X) button
    await expect(section.getByText(memberUser.name)).toBeVisible()
    const managerRow = section.locator('.rounded-md.border').filter({ hasText: memberUser.name })
    await managerRow.getByRole('button').click()

    // Manager is removed from the list
    await expect(section.getByText(memberUser.name)).toBeHidden()
  })

  test('member does not see the Management section', async ({ memberPage }) => {
    await memberPage.goto(`/app/event-groups/${group.id}`)
    await expect(memberPage.getByTestId('section-group-managers')).toBeHidden()
  })
})

// ── Scoped manager API permissions ───────────────────────────────────────────

test.describe('Group Managers – scoped permissions (API)', () => {
  let group: EventGroupRead
  let memberId: string

  test.beforeEach(async ({ adminPage, memberUser }) => {
    await adminPage.goto('/app/event-groups')
    group = await createGroup(adminPage, uniqueName('E2E Scoped Perms'))
    memberId = await getMemberId(adminPage, memberUser.email)
  })

  test.afterEach(async ({ adminPage }) => {
    await deleteGroup(adminPage, group.id)
  })

  test('member without assignment cannot create events in group', async ({
    memberPage,
  }) => {
    try {
      await api(memberPage, 'POST', '/events/with-slots', eventPayload(group.id, 'Unauthorized'))
      expect(true, 'Expected 403 but request succeeded').toBe(false)
    } catch (e) {
      // eslint-disable-next-line playwright/no-conditional-expect
      expect(String(e)).toContain('403')
    }
  })

  test('assigned group manager can create events in the group', async ({
    adminPage,
    memberPage,
  }) => {
    await api(adminPage, 'POST', `/event-groups/${group.id}/managers/${memberId}`)

    const result = await api<{ event: { id: string; name: string } }>(
      memberPage,
      'POST',
      '/events/with-slots',
      eventPayload(group.id, 'Scoped Manager Event'),
    )
    expect(result.event.name).toBe('Scoped Manager Event')

    await api(adminPage, 'DELETE', `/events/${result.event.id}`)
  })

  test('assigned group manager cannot create events in a different group', async ({
    adminPage,
    memberPage,
  }) => {
    await api(adminPage, 'POST', `/event-groups/${group.id}/managers/${memberId}`)
    const groupB = await createGroup(adminPage, uniqueName('E2E Other Group'))

    try {
      await api(memberPage, 'POST', '/events/with-slots', eventPayload(groupB.id, 'Wrong Group'))
      expect(true, 'Expected 403 but request succeeded').toBe(false)
    } catch (e) {
      // eslint-disable-next-line playwright/no-conditional-expect
      expect(String(e)).toContain('403')
    } finally {
      await deleteGroup(adminPage, groupB.id)
    }
  })

  test('removing group manager revokes event creation access', async ({
    adminPage,
    memberPage,
  }) => {
    await api(adminPage, 'POST', `/event-groups/${group.id}/managers/${memberId}`)
    await api(adminPage, 'DELETE', `/event-groups/${group.id}/managers/${memberId}`)

    try {
      await api(memberPage, 'POST', '/events/with-slots', eventPayload(group.id, 'Revoked'))
      expect(true, 'Expected 403 but request succeeded').toBe(false)
    } catch (e) {
      // eslint-disable-next-line playwright/no-conditional-expect
      expect(String(e)).toContain('403')
    }
  })
})

// ── Full E2E flow: UI assignment -> API action -> UI verification ────────────

test.describe('Group Managers – full E2E flow', () => {
  let group: EventGroupRead

  test.beforeEach(async ({ adminPage }) => {
    await adminPage.goto('/app/event-groups')
    group = await createGroup(adminPage, uniqueName('E2E Full Manager Flow'))
  })

  test.afterEach(async ({ adminPage }) => {
    await deleteGroup(adminPage, group.id)
  })

  test('admin assigns manager via UI, manager creates event, admin sees it', async ({
    adminPage,
    memberPage,
    memberUser,
  }) => {
    // Step 1: Admin assigns the member as group manager via UI
    await adminPage.goto(`/app/event-groups/${group.id}/management`)
    await adminPage.getByRole('button', { name: /add manager|verwalter hinzufügen/i }).click()
    await adminPage
      .getByPlaceholder(/search.*name.*email|benutzer.*suchen/i)
      .fill(memberUser.email)
    await adminPage.getByText(memberUser.name).click()
    await expect(adminPage.getByText(memberUser.name)).toBeVisible()

    // Step 2: Scoped manager creates an event via API
    const result = await api<{ event: { id: string; name: string } }>(
      memberPage,
      'POST',
      '/events/with-slots',
      eventPayload(group.id, 'Manager Created Event'),
    )

    // Step 3: Admin sees the event on the group detail page
    await adminPage.goto(`/app/event-groups/${group.id}`)
    await expect(adminPage.getByRole('heading', { name: 'Manager Created Event' })).toBeVisible()

    await api(adminPage, 'DELETE', `/events/${result.event.id}`)
  })
})
