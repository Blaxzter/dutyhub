/**
 * E2E tests from a regular (non-admin) member's perspective.
 *
 * Uses adminPage/memberPage fixtures for isolated auth.
 */
import { expect, test } from '../../fixtures.js'
import {
  api,
  clearAvailability,
  createGroup,
  deleteGroup,
  futureDate,
  uniqueName,
} from '../../helpers/api.js'
import type { EventRead } from '../../helpers/api.js'
import { pickDate } from '../../helpers/ui.js'

// ── RBAC: member cannot create or delete ─────────────────────────────────────

test.describe('Member – RBAC', () => {
  let group: EventRead

  test.beforeEach(async ({ adminPage }) => {
    await adminPage.goto('/app/events')
    group = await createGroup(adminPage, uniqueName('E2E RBAC Member Test Group'))
  })

  test.afterEach(async ({ adminPage }) => {
    await deleteGroup(adminPage, group.id)
  })

  test('member does not see Create button', async ({ memberPage: member }) => {
    await member.goto('/app/events')
    await expect(member.getByTestId('btn-create-group')).toBeHidden()
  })

  test('member does not see Delete button on task group cards', async ({ memberPage: member }) => {
    await member.goto('/app/events')
    await expect(member.getByText(group.name).first()).toBeVisible()
    const card = member.locator('[class*="cursor-pointer"]').filter({ hasText: group.name })
    await expect(card.getByRole('button')).toBeHidden()
  })

  test('member does not see the member availabilities admin table', async ({
    memberPage: member,
  }) => {
    await member.goto(`/app/events/${group.id}`)
    await expect(member.getByTestId('section-admin-availabilities')).toBeHidden()
  })
})

// ── Member can view published groups but not drafts ───────────────────────────

test.describe('Member – list view', () => {
  let group: EventRead

  test.beforeEach(async ({ adminPage }) => {
    await adminPage.goto('/app/events')
    group = await createGroup(adminPage, uniqueName('E2E Member Visible Group'))
  })

  test.afterEach(async ({ adminPage }) => {
    await deleteGroup(adminPage, group.id)
  })

  test('member can see published task groups', async ({ memberPage: member }) => {
    await member.goto('/app/events')
    await expect(member.getByText(group.name).first()).toBeVisible()
  })

  test('member cannot see draft task groups', async ({ adminPage, memberPage: member }) => {
    const draft = await createGroup(adminPage, uniqueName('E2E Hidden Draft Group'), 'draft')
    try {
      await member.goto('/app/events')
      await expect(member.getByText(draft.name)).toBeHidden()
    } finally {
      await deleteGroup(adminPage, draft.id)
    }
  })

  test('member can navigate to task group detail page', async ({ memberPage: member }) => {
    await member.goto('/app/events')
    await member.getByText(group.name).first().click()
    await expect(member).toHaveURL(new RegExp(`/app/events/${group.id}`))
    await expect(member.getByRole('heading', { name: group.name })).toBeVisible()
  })
})

// ── Member can manage their own availability ──────────────────────────────────

test.describe('Member – availability', () => {
  let group: EventRead

  test.beforeEach(async ({ adminPage }) => {
    await adminPage.goto('/app/events')
    group = await createGroup(adminPage, uniqueName('E2E Member Availability Group'))
  })

  test.afterEach(async ({ adminPage }) => {
    await deleteGroup(adminPage, group.id)
  })

  test('member sees Register Availability button when none set', async ({ memberPage: member }) => {
    await member.goto(`/app/events/${group.id}/availability`)
    await clearAvailability(member, group.id).catch(() => {})
    await member.reload()
    const section = member.getByTestId('section-availability')
    await expect(section.getByTestId('btn-availability')).toBeVisible()
  })

  test('member can register as fully available', async ({ memberPage: member }) => {
    await member.goto(`/app/events/${group.id}/availability`)
    await clearAvailability(member, group.id).catch(() => {})
    await member.reload()
    const section = member.getByTestId('section-availability')
    await section.getByTestId('btn-availability').click()
    await member.getByTestId('availability-type-fully_available').click()
    await member.getByTestId('btn-save').click()

    await expect(member.getByTestId('dialog-availability')).toBeHidden()
    await expect(section.getByText(/open to be requested|fully.?available/i)).toBeVisible()
    await expect(section.getByTestId('btn-availability')).toBeVisible()
    await expect(section.getByTestId('btn-remove-availability')).toBeVisible()
    await clearAvailability(member, group.id).catch(() => {})
  })

  test('member can register availability for specific dates', async ({ memberPage: member }) => {
    await member.goto(`/app/events/${group.id}/availability`)
    await clearAvailability(member, group.id).catch(() => {})
    await member.reload()
    const section = member.getByTestId('section-availability')
    await section.getByTestId('btn-availability').click()
    await member.getByTestId('availability-type-specific_dates').click()
    await member.getByTestId('btn-add-date').click()
    await pickDate(
      member.getByRole('button', { name: /pick a date|datum/i }).last(),
      futureDate(30),
    )
    await member.getByTestId('btn-save').click()

    await expect(member.getByTestId('dialog-availability')).toBeHidden()
    await expect(section.getByText(/specific dates/i)).toBeVisible()
    await clearAvailability(member, group.id).catch(() => {})
  })

  test('member can update their availability', async ({ memberPage: member }) => {
    await member.goto(`/app/events/${group.id}/availability`)
    await api(member, 'POST', `/events/${group.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })
    await member.reload()
    const section = member.getByTestId('section-availability')
    await section.getByTestId('btn-availability').click()
    await member.getByTestId('availability-type-specific_dates').click()
    await member.getByTestId('btn-save').click()

    await expect(member.getByTestId('dialog-availability')).toBeHidden()
    await expect(section.getByText(/specific dates/i)).toBeVisible()
    await clearAvailability(member, group.id).catch(() => {})
  })

  test('member can remove their availability', async ({ memberPage: member }) => {
    await member.goto(`/app/events/${group.id}/availability`)
    await api(member, 'POST', `/events/${group.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })
    await member.reload()
    const section = member.getByTestId('section-availability')
    member.on('dialog', (d) => d.accept())
    await section.getByTestId('btn-remove-availability').click()
    await expect(section.getByTestId('btn-availability')).toBeVisible()
  })
})
