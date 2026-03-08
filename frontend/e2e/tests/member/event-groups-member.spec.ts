/**
 * E2E tests from a regular (non-admin) member's perspective.
 *
 * The default page context (from the chromium project) is the admin user.
 * Member actions use an explicit browser context with the member storage state.
 */

import { expect, test } from '@playwright/test'
import { api, clearAvailability, createGroup, deleteGroup } from '../../helpers/api'
import type { EventGroupRead } from '../../helpers/api'

const MEMBER_STATE = 'e2e/.auth/member.json'

// ── RBAC: member cannot create or delete ─────────────────────────────────────

test.describe('Member – RBAC', () => {
  let group: EventGroupRead

  test.beforeEach(async ({ page }) => {
    await page.goto('/app/event-groups')
    group = await createGroup(page, 'E2E RBAC Member Test Group')
  })

  test.afterEach(async ({ page }) => {
    await deleteGroup(page, group.id)
  })

  test('member does not see Create button', async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: MEMBER_STATE })
    const member = await ctx.newPage()
    try {
      await member.goto('/app/event-groups')
      await expect(member.getByRole('button', { name: /create/i })).toBeHidden()
    } finally {
      await ctx.close()
    }
  })

  test('member does not see Delete button on event group cards', async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: MEMBER_STATE })
    const member = await ctx.newPage()
    try {
      await member.goto('/app/event-groups')
      await expect(member.getByText(group.name)).toBeVisible()
      const card = member.locator('[class*="cursor-pointer"]').filter({ hasText: group.name })
      await expect(card.getByRole('button')).toBeHidden()
    } finally {
      await ctx.close()
    }
  })

  test('member does not see the member availabilities admin table', async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: MEMBER_STATE })
    const member = await ctx.newPage()
    try {
      await member.goto(`/app/event-groups/${group.id}`)
      await expect(member.getByText(/member availabilities|all members|registrations/i)).toBeHidden()
    } finally {
      await ctx.close()
    }
  })
})

// ── Member can view published groups but not drafts ───────────────────────────

test.describe('Member – list view', () => {
  let group: EventGroupRead

  test.beforeEach(async ({ page }) => {
    await page.goto('/app/event-groups')
    group = await createGroup(page, 'E2E Member Visible Group')
  })

  test.afterEach(async ({ page }) => {
    await deleteGroup(page, group.id)
  })

  test('member can see published event groups', async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: MEMBER_STATE })
    const member = await ctx.newPage()
    try {
      await member.goto('/app/event-groups')
      await expect(member.getByText(group.name)).toBeVisible()
    } finally {
      await ctx.close()
    }
  })

  test('member cannot see draft event groups', async ({ page, browser }) => {
    const draft = await createGroup(page, 'E2E Hidden Draft Group', 'draft')
    const ctx = await browser.newContext({ storageState: MEMBER_STATE })
    const member = await ctx.newPage()
    try {
      await member.goto('/app/event-groups')
      await expect(member.getByText(draft.name)).toBeHidden()
    } finally {
      await ctx.close()
      await deleteGroup(page, draft.id)
    }
  })

  test('member can navigate to event group detail page', async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: MEMBER_STATE })
    const member = await ctx.newPage()
    try {
      await member.goto('/app/event-groups')
      await member.getByText(group.name).click()
      await expect(member).toHaveURL(new RegExp(`/app/event-groups/${group.id}`))
      await expect(member.getByRole('heading', { name: group.name })).toBeVisible()
    } finally {
      await ctx.close()
    }
  })
})

// ── Member can manage their own availability ──────────────────────────────────

test.describe('Member – availability', () => {
  let group: EventGroupRead

  test.beforeEach(async ({ page }) => {
    await page.goto('/app/event-groups')
    group = await createGroup(page, 'E2E Member Availability Group')
  })

  test.afterEach(async ({ page }) => {
    await deleteGroup(page, group.id)
  })

  test('member sees Register Availability button when none set', async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: MEMBER_STATE })
    const member = await ctx.newPage()
    try {
      await member.goto(`/app/event-groups/${group.id}`)
      await clearAvailability(member, group.id).catch(() => {})
      await member.reload()
      await expect(member.getByRole('button', { name: /register availability/i })).toBeVisible()
    } finally {
      await clearAvailability(member, group.id).catch(() => {})
      await ctx.close()
    }
  })

  test('member can register as fully available', async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: MEMBER_STATE })
    const member = await ctx.newPage()
    try {
      await member.goto(`/app/event-groups/${group.id}`)
      await clearAvailability(member, group.id).catch(() => {})
      await member.reload()
      await member.getByRole('button', { name: /register availability/i }).click()
      await member.getByText(/open to be requested|fully.?available/i).click()
      await member.getByRole('button', { name: /save/i }).click()

      await expect(member.getByRole('dialog')).toBeHidden()
      await expect(member.getByText(/open to be requested|fully.?available/i)).toBeVisible()
      await expect(member.getByRole('button', { name: /update|change/i })).toBeVisible()
      await expect(member.getByRole('button', { name: /remove/i })).toBeVisible()
    } finally {
      await clearAvailability(member, group.id).catch(() => {})
      await ctx.close()
    }
  })

  test('member can register availability for specific dates', async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: MEMBER_STATE })
    const member = await ctx.newPage()
    try {
      await member.goto(`/app/event-groups/${group.id}`)
      await clearAvailability(member, group.id).catch(() => {})
      await member.reload()
      await member.getByRole('button', { name: /register availability/i }).click()
      await member.getByText(/specific dates/i).click()
      await member.getByRole('button', { name: /add date/i }).click()
      await member.locator('input[type="date"]').last().fill('2026-06-10')
      await member.getByRole('button', { name: /save/i }).click()

      await expect(member.getByRole('dialog')).toBeHidden()
      await expect(member.getByText(/specific dates/i)).toBeVisible()
    } finally {
      await clearAvailability(member, group.id).catch(() => {})
      await ctx.close()
    }
  })

  test('member can update their availability', async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: MEMBER_STATE })
    const member = await ctx.newPage()
    try {
      await member.goto(`/app/event-groups/${group.id}`)
      await api(member, 'POST', `/event-groups/${group.id}/availability`, {
        availability_type: 'fully_available',
        dates: [],
      })
      await member.reload()
      await member.getByRole('button', { name: /update|change/i }).click()
      await member.getByText(/specific dates/i).click()
      await member.getByRole('button', { name: /save/i }).click()

      await expect(member.getByRole('dialog')).toBeHidden()
      await expect(member.getByText(/specific dates/i)).toBeVisible()
    } finally {
      await clearAvailability(member, group.id).catch(() => {})
      await ctx.close()
    }
  })

  test('member can remove their availability', async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: MEMBER_STATE })
    const member = await ctx.newPage()
    try {
      await member.goto(`/app/event-groups/${group.id}`)
      await api(member, 'POST', `/event-groups/${group.id}/availability`, {
        availability_type: 'fully_available',
        dates: [],
      })
      await member.reload()
      member.on('dialog', (d) => d.accept())
      await member.getByRole('button', { name: /remove/i }).click()
      await expect(member.getByRole('button', { name: /register availability/i })).toBeVisible({
        timeout: 5000,
      })
    } finally {
      await clearAvailability(member, group.id).catch(() => {})
      await ctx.close()
    }
  })
})
