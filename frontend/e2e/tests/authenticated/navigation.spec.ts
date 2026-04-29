/**
 * E2E tests for Navigation, Sidebar, Breadcrumbs, and 404 page.
 */

import { test, expect } from '../../fixtures.js'

// ── sidebar navigation ──────────────────────────────────────────────────────

test.describe('Sidebar – links', () => {
  test('shows Home link', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('sidebar-link-home')).toBeVisible()
  })

  test('shows Tasks link', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('sidebar-link-tasks')).toBeVisible()
  })

  test('shows My Bookings link', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('sidebar-link-my-bookings')).toBeVisible()
  })

  test('shows Availability link', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('sidebar-link-availability')).toBeVisible()
  })

  test('shows Manage Events link for admin', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('sidebar-link-admin-events')).toBeVisible()
  })

  test('shows User Management link for admin', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('sidebar-link-admin-users')).toBeVisible()
  })

  test('shows Demo Data link for admin', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('sidebar-link-admin-demo-data')).toBeVisible()
  })

  test('shows user profile button in sidebar', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('nav-user-menu')).toBeVisible()
  })
})

// ── sidebar navigation (clicking) ───────────────────────────────────────────

test.describe('Sidebar – navigation', () => {
  test('Home link navigates to dashboard', async ({ adminPage: page }) => {
    await page.goto('/app/tasks')
    await page.getByTestId('sidebar-link-home').click()
    await expect(page).toHaveURL(/\/app\/home/)
  })

  test('Manage Events link navigates to /app/admin/events', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('sidebar-link-admin-events').click()
    await expect(page).toHaveURL(/\/app\/admin\/events/)
  })

  test('Tasks link navigates correctly', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('sidebar-link-tasks').click()
    await expect(page).toHaveURL(/\/app\/tasks/)
  })

  test('My Bookings link navigates correctly', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('sidebar-link-my-bookings').click()
    await expect(page).toHaveURL(/\/app\/bookings/)
  })

  test('Availability link navigates correctly', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('sidebar-link-availability').click()
    await expect(page).toHaveURL(/\/app\/availability/)
  })

  test('User Management link navigates correctly', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('sidebar-link-admin-users').click()
    await expect(page).toHaveURL(/\/app\/admin\/users/)
  })

  test('Demo Data link navigates correctly', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('sidebar-link-admin-demo-data').click()
    await expect(page).toHaveURL(/\/app\/admin\/demo-data/)
  })
})

// ── breadcrumbs ──────────────────────────────────────────────────────────────

test.describe('Breadcrumbs', () => {
  test('dashboard shows breadcrumb navigation', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByRole('navigation', { name: /breadcrumb/i })).toBeVisible()
  })

  test('tasks page shows breadcrumbs', async ({ adminPage: page }) => {
    await page.goto('/app/tasks')
    await expect(page.getByRole('navigation', { name: /breadcrumb/i })).toBeVisible()
  })
})

// ── settings event switcher ─────────────────────────────────────────────────

test.describe('Settings – active event', () => {
  test('current event is shown on the active-event settings page', async ({
    adminPage: page,
  }) => {
    await page.goto('/app/settings/event')
    await expect(page.getByTestId('settings-active-event-name')).toBeVisible()
  })

  test('change button opens the event switcher menu', async ({ adminPage: page }) => {
    await page.goto('/app/settings/event')
    await page.getByTestId('settings-active-event-change').click()
    await expect(page.locator('[data-testid^="event-switcher-option-"]').first()).toBeVisible()
  })
})

// ── sidebar toggle ───────────────────────────────────────────────────────────

test.describe('Sidebar – toggle', () => {
  test('Toggle Sidebar button is visible', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    // SidebarTrigger in the header (data-sidebar="trigger")
    await expect(page.locator('[data-sidebar="trigger"]')).toBeVisible()
  })
})

// ── 404 page ─────────────────────────────────────────────────────────────────

test.describe('404 – not found', () => {
  test('navigating to non-existent route shows 404', async ({ adminPage: page }) => {
    await page.goto('/this-does-not-exist-at-all')
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })

  test('navigating to /404 directly shows not found page', async ({ adminPage: page }) => {
    await page.goto('/404')
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })

  test('404 page has go home button', async ({ adminPage: page }) => {
    await page.goto('/404')
    await expect(page.getByTestId('btn-go-home')).toBeVisible()
  })
})

// ── member sidebar ───────────────────────────────────────────────────────────

test.describe('Member sidebar – no admin links', () => {
  test('member does not see Manage Events link', async ({ memberPage: member }) => {
    await member.goto('/app/home')
    await expect(member.getByTestId('sidebar-link-admin-events')).toBeHidden()
  })

  test('member does not see User Management link', async ({ memberPage: member }) => {
    await member.goto('/app/home')
    await expect(member.getByTestId('sidebar-link-admin-users')).toBeHidden()
  })

  test('member does not see Demo Data link', async ({ memberPage: member }) => {
    await member.goto('/app/home')
    await expect(member.getByTestId('sidebar-link-admin-demo-data')).toBeHidden()
  })
})
