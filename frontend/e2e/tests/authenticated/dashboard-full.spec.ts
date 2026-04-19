/**
 * E2E tests for Dashboard page — stats cards, calendar, quick actions.
 */

import { test, expect } from '../../fixtures.js'

test.describe('Dashboard – stats cards', () => {
  test('shows Tasks stat card', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('stat-card-tasks')).toBeVisible()
  })

  test('shows My Bookings stat card', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('stat-card-bookings')).toBeVisible()
  })

  test('shows Pending Users stat card for admin', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('stat-card-users')).toBeVisible()
  })

  test('Tasks card navigates to tasks', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('stat-card-tasks').click()
    await expect(page).toHaveURL(/\/app\/tasks/)
  })

  test('My Bookings card navigates to bookings', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('stat-card-bookings').click()
    await expect(page).toHaveURL(/\/app\/bookings/)
  })
})

test.describe('Dashboard – calendar', () => {
  test('shows calendar section', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('dashboard-calendar')).toBeVisible()
  })

  test('Filter button is visible', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('btn-calendar-filter')).toBeVisible()
  })
})

test.describe('Dashboard – quick actions', () => {
  test('shows Quick Actions section', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('dashboard-quick-actions')).toBeVisible()
  })

  test('shows Browse Tasks button', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('btn-browse-tasks')).toBeVisible()
  })

  test('shows My Bookings button', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('btn-my-bookings')).toBeVisible()
  })

  test('Browse Tasks navigates to tasks page', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('btn-browse-tasks').click()
    await expect(page).toHaveURL(/\/app\/tasks/)
  })

  test('My Bookings quick action navigates to bookings', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('btn-my-bookings').click()
    await expect(page).toHaveURL(/\/app\/bookings/)
  })
})
