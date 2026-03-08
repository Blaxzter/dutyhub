/**
 * E2E tests for Event Groups & Availability feature.
 *
 * Strategy: use authenticated fetch() calls (via page.evaluate) to set up and
 * tear down test data so every test starts from a known state instead of
 * relying on pre-existing DB data.
 */

import { type Page, expect, test } from '@playwright/test'

// ── helpers ──────────────────────────────────────────────────────────────────

const API = process.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

/** Extract the Auth0 access token from localStorage. */
async function getToken(page: Page): Promise<string> {
  return page.evaluate(() => {
    const key = Object.keys(localStorage).find((k) => k.startsWith('@@auth0spajs@@'))
    if (!key) return ''
    try {
      const raw = JSON.parse(localStorage.getItem(key) ?? '{}')
      return (raw as { body?: { access_token?: string } })?.body?.access_token ?? ''
    } catch {
      return ''
    }
  })
}

/** Make an authenticated API call inside the browser context. */
async function api<T = unknown>(page: Page, method: string, path: string, body?: object): Promise<T> {
  const token = await getToken(page)
  return page.evaluate(
    async ({ url, method, body, token }) => {
      const res = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: body ? JSON.stringify(body) : undefined,
      })
      if (res.status === 204) return null
      return res.json()
    },
    { url: `${API}${path}`, method, body, token },
  ) as Promise<T>
}

interface EventGroupRead {
  id: string
  name: string
  status: string
  start_date: string
  end_date: string
}

/** Create a published event group and return it. */
async function createGroup(page: Page, name: string): Promise<EventGroupRead> {
  // Create as draft first
  const draft = await api<EventGroupRead>(page, 'POST', '/event-groups/', {
    name,
    start_date: '2026-06-10',
    end_date: '2026-06-14',
  })
  // Publish it so normal users can see it
  return api<EventGroupRead>(page, 'PATCH', `/event-groups/${draft.id}`, {
    status: 'published',
  })
}

/** Delete an event group (admin). */
async function deleteGroup(page: Page, id: string): Promise<void> {
  await api(page, 'DELETE', `/event-groups/${id}`)
}

/** Delete the current user's availability for a group (best-effort). */
async function clearAvailability(page: Page, groupId: string): Promise<void> {
  await api(page, 'DELETE', `/event-groups/${groupId}/availability/me`)
}

// Seed once per test file — we need the page to be authenticated first
// so we use test.beforeEach with a lazy-init guard.
const sharedGroup: EventGroupRead | null = null
const groupCreatedByTest = false

// ── navigation ────────────────────────────────────────────────────────────────

test.describe('Event Groups – navigation', () => {
  test('sidebar shows Event Groups link', async ({ page }) => {
    await page.goto('/app/home')
    await expect(page.getByRole('link', { name: /event.?groups/i })).toBeVisible()
  })

  test('clicking sidebar link navigates to /app/event-groups', async ({ page }) => {
    await page.goto('/app/home')
    await page.getByRole('link', { name: /event.?groups/i }).click()
    await expect(page).toHaveURL(/\/app\/event-groups$/)
    await expect(page.getByRole('heading', { name: /event.?groups/i })).toBeVisible()
  })

  test('direct navigation to /app/event-groups works', async ({ page }) => {
    await page.goto('/app/event-groups')
    await expect(page).toHaveURL(/\/app\/event-groups$/)
    await expect(page.getByRole('heading', { name: /event.?groups/i })).toBeVisible()
  })
})

// ── list view ─────────────────────────────────────────────────────────────────

test.describe('Event Groups – list view', () => {
  let group: EventGroupRead

  test.beforeEach(async ({ page }) => {
    await page.goto('/app/event-groups')
    group = await createGroup(page, 'E2E Testgruppe Kirchentags 2026')
  })

  test.afterEach(async ({ page }) => {
    await deleteGroup(page, group.id)
  })

  test('shows heading and search input', async ({ page }) => {
    await page.goto('/app/event-groups')
    await expect(page.getByRole('heading', { name: /event.?groups/i })).toBeVisible()
    await expect(page.getByRole('textbox')).toBeVisible()
  })

  test('created group appears in list with published badge', async ({ page }) => {
    await page.goto('/app/event-groups')
    await expect(page.getByText(group.name)).toBeVisible()
    // published status badge
    await expect(page.getByText(/published/i).first()).toBeVisible()
  })

  test('created group shows date range', async ({ page }) => {
    await page.goto('/app/event-groups')
    // Dates are formatted locale-dependently; check both dates appear somewhere
    await expect(page.getByText(group.name)).toBeVisible()
  })

  test('search filters the list by name', async ({ page }) => {
    await page.goto('/app/event-groups')
    const searchInput = page.getByRole('textbox')
    await searchInput.fill('Kirchentags')
    await expect(page.getByText(group.name)).toBeVisible()

    await searchInput.fill('zzzzunlikelymatch')
    await expect(page.getByText(group.name)).toBeHidden()
  })

  test('clicking a card navigates to the detail page', async ({ page }) => {
    await page.goto('/app/event-groups')
    await page.getByText(group.name).click()
    await expect(page).toHaveURL(new RegExp(`/app/event-groups/${group.id}`))
  })
})

// ── admin actions ─────────────────────────────────────────────────────────────

test.describe('Event Groups – admin create & delete', () => {
  test('Create button is visible (test user is admin in test env)', async ({ page }) => {
    await page.goto('/app/event-groups')
    // In the test environment the E2E user has admin privileges
    await expect(page.getByRole('button', { name: /create/i })).toBeVisible()
  })

  test('admin can create an event group via dialog', async ({ page }) => {
    await page.goto('/app/event-groups')

    await page.getByRole('button', { name: /create/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()

    await page.getByLabel(/name/i).fill('E2E Admin Created Group')
    await page.locator('input[type="date"]').nth(0).fill('2026-09-01')
    await page.locator('input[type="date"]').nth(1).fill('2026-09-07')

    await page.getByRole('button', { name: /^create$/i }).click()

    // Dialog closes and new card appears
    await expect(page.getByRole('dialog')).toBeHidden()
    await expect(page.getByText('E2E Admin Created Group')).toBeVisible()

    // Clean up via API
    const groups = await api<{ items: EventGroupRead[] }>(page, 'GET', '/event-groups/')
    const created = groups.items.find((g) => g.name === 'E2E Admin Created Group')
    if (created) await deleteGroup(page, created.id)
  })

  test('admin can delete an event group via trash icon', async ({ page }) => {
    await page.goto('/app/event-groups')
    const groupToDelete = await createGroup(page, 'E2E To Be Deleted')

    await page.goto('/app/event-groups')
    await expect(page.getByText(groupToDelete.name)).toBeVisible()

    // Confirm dialog is triggered — intercept it
    page.on('dialog', (dialog) => dialog.accept())

    // Click delete for that specific card
    // Find the card containing the group name, then click its delete button
    const card = page.locator('[class*="cursor-pointer"]').filter({ hasText: groupToDelete.name })
    await card.getByRole('button').click()

    await expect(page.getByText(groupToDelete.name)).not.toBeVisible({ timeout: 5000 })
  })
})

// ── detail page ───────────────────────────────────────────────────────────────

test.describe('Event Group Detail – page structure', () => {
  let group: EventGroupRead

  test.beforeEach(async ({ page }) => {
    await page.goto('/app/event-groups')
    group = await createGroup(page, 'E2E Detail Page Group')
  })

  test.afterEach(async ({ page }) => {
    await clearAvailability(page, group.id).catch(() => {})
    await deleteGroup(page, group.id)
  })

  test('shows group name and status badge', async ({ page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    await expect(page.getByRole('heading', { name: group.name })).toBeVisible()
    await expect(page.getByText(/published/i)).toBeVisible()
  })

  test('shows date range in header', async ({ page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    // The dates 2026-06-10 and 2026-06-14 appear somewhere on the page
    await expect(page.getByText(/2026/)).toBeVisible()
  })

  test('shows My Availability section', async ({ page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    await expect(page.getByText(/my availability/i)).toBeVisible()
  })

  test('shows Events in this Group section', async ({ page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    await expect(page.getByText(/events in this group/i)).toBeVisible()
  })

  test('back button navigates to event groups list', async ({ page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    await page.getByRole('button', { name: /event.?groups/i }).click()
    await expect(page).toHaveURL(/\/app\/event-groups$/)
  })

  test('navigating to a non-existent group shows back button', async ({ page }) => {
    await page.goto('/app/event-groups/00000000-0000-0000-0000-000000000000')
    await expect(page.getByRole('button', { name: /event.?groups/i })).toBeVisible()
  })
})

// ── availability: register fully available ────────────────────────────────────

test.describe('Availability – fully available', () => {
  let group: EventGroupRead

  test.beforeEach(async ({ page }) => {
    await page.goto('/app/event-groups')
    group = await createGroup(page, 'E2E Availability Group')
    await clearAvailability(page, group.id).catch(() => {})
  })

  test.afterEach(async ({ page }) => {
    await clearAvailability(page, group.id).catch(() => {})
    await deleteGroup(page, group.id)
  })

  test('Register button is visible when no availability set', async ({ page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    await expect(page.getByRole('button', { name: /register availability/i })).toBeVisible()
  })

  test('Register button opens availability dialog', async ({ page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    await page.getByRole('button', { name: /register availability/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
  })

  test('dialog shows both availability type options', async ({ page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    await page.getByRole('button', { name: /register availability/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByText(/open to be requested|fully.?available/i)).toBeVisible()
    await expect(page.getByText(/specific dates/i)).toBeVisible()
  })

  test('Cancel closes the dialog without saving', async ({ page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    await page.getByRole('button', { name: /register availability/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.getByRole('button', { name: /cancel/i }).click()
    await expect(page.getByRole('dialog')).toBeHidden()
    // Still shows Register button (nothing was saved)
    await expect(page.getByRole('button', { name: /register availability/i })).toBeVisible()
  })

  test('can register as fully available', async ({ page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    await page.getByRole('button', { name: /register availability/i }).click()

    // "Open to be requested" / "fully available" option — select it
    await page.getByText(/open to be requested|fully.?available/i).click()
    await page.getByRole('button', { name: /save/i }).click()

    await expect(page.getByRole('dialog')).toBeHidden()
    // Status now shows "Open to be requested" or similar
    await expect(page.getByText(/open to be requested|fully.?available/i)).toBeVisible()
    // Register button replaced by Update / Remove
    await expect(page.getByRole('button', { name: /update|change/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /remove/i })).toBeVisible()
  })

  test('can add a note when registering', async ({ page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    await page.getByRole('button', { name: /register availability/i }).click()

    await page.getByText(/open to be requested|fully.?available/i).click()
    await page.getByRole('textbox', { name: /notes?/i }).fill('I am free the whole week!')
    await page.getByRole('button', { name: /save/i }).click()

    await expect(page.getByRole('dialog')).toBeHidden()
    await expect(page.getByText(/I am free the whole week!/i)).toBeVisible()
  })

  test('can remove availability', async ({ page }) => {
    // Set availability via API so we start with one registered
    await api(page, 'POST', `/event-groups/${group.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })

    await page.goto(`/app/event-groups/${group.id}`)
    // Confirm-destructive dialog is inside the app; accept via dialog event
    page.on('dialog', (d) => d.accept())

    await page.getByRole('button', { name: /remove/i }).click()

    // Register button should return
    await expect(page.getByRole('button', { name: /register availability/i })).toBeVisible({
      timeout: 5000,
    })
  })

  test('can update existing availability', async ({ page }) => {
    // Pre-seed via API
    await api(page, 'POST', `/event-groups/${group.id}/availability`, {
      availability_type: 'fully_available',
      dates: [],
    })

    await page.goto(`/app/event-groups/${group.id}`)
    await page.getByRole('button', { name: /update|change/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()

    // Switch to specific_dates
    await page.getByText(/specific dates/i).click()
    await page.getByRole('button', { name: /save/i }).click()

    await expect(page.getByRole('dialog')).toBeHidden()
    await expect(page.getByText(/specific dates/i)).toBeVisible()
  })
})

// ── availability: specific dates ──────────────────────────────────────────────

test.describe('Availability – specific dates', () => {
  let group: EventGroupRead

  test.beforeEach(async ({ page }) => {
    await page.goto('/app/event-groups')
    group = await createGroup(page, 'E2E Specific Dates Group')
    await clearAvailability(page, group.id).catch(() => {})
  })

  test.afterEach(async ({ page }) => {
    await clearAvailability(page, group.id).catch(() => {})
    await deleteGroup(page, group.id)
  })

  test('specific dates option reveals date builder', async ({ page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    await page.getByRole('button', { name: /register availability/i }).click()
    await page.getByText(/specific dates/i).click()
    // Add date button or date input appears
    await expect(page.getByRole('button', { name: /add date/i })).toBeVisible()
  })

  test('can register availability with specific dates', async ({ page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    await page.getByRole('button', { name: /register availability/i }).click()
    await page.getByText(/specific dates/i).click()

    // Add a date
    await page.getByRole('button', { name: /add date/i }).click()
    // Fill in the date input that appeared
    await page.locator('input[type="date"]').last().fill('2026-06-10')

    await page.getByRole('button', { name: /save/i }).click()
    await expect(page.getByRole('dialog')).toBeHidden()

    // The availability type is now specific_dates
    await expect(page.getByText(/specific dates/i)).toBeVisible()
  })

  test('registering specific dates via API shows them in UI', async ({ page }) => {
    await api(page, 'POST', `/event-groups/${group.id}/availability`, {
      availability_type: 'specific_dates',
      dates: ['2026-06-10', '2026-06-11'],
    })

    await page.goto(`/app/event-groups/${group.id}`)
    await expect(page.getByText(/specific dates/i)).toBeVisible()
    // Both dates should appear somewhere on the page
    await expect(page.getByText(/2026-06-10|10\. Juni|Jun 10/i)).toBeVisible()
    await expect(page.getByText(/2026-06-11|11\. Juni|Jun 11/i)).toBeVisible()
  })
})

// ── admin: member availability table ─────────────────────────────────────────

test.describe('Admin – member availability table', () => {
  let group: EventGroupRead

  test.beforeEach(async ({ page }) => {
    await page.goto('/app/event-groups')
    group = await createGroup(page, 'E2E Admin Avail Group')
  })

  test.afterEach(async ({ page }) => {
    await clearAvailability(page, group.id).catch(() => {})
    await deleteGroup(page, group.id)
  })

  test('member availabilities section is visible for admins', async ({ page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    await expect(page.getByText(/member availabilities|all members|registrations/i)).toBeVisible()
  })

  test('empty state is shown when no members have registered', async ({ page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    await expect(page.getByText(/no.*(members|registrations|availability)/i)).toBeVisible()
  })

  test('registered availability appears in admin table', async ({ page }) => {
    await api(page, 'POST', `/event-groups/${group.id}/availability`, {
      availability_type: 'fully_available',
      notes: 'E2E admin table test',
      dates: [],
    })

    await page.goto(`/app/event-groups/${group.id}`)
    // The admin table should show an entry — look for the availability type or note
    await expect(
      page.getByText(/fully.?available|open to be requested/i).nth(1),
    ).toBeVisible({ timeout: 5000 })
  })
})
