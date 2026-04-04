/**
 * E2E tests for Admin Reporting page.
 */

import { test, expect } from '../../fixtures.js'

test.describe('Reporting – navigation', () => {
  test('can navigate to reporting page via URL', async ({ adminPage: page }) => {
    await page.goto('/app/admin/reporting')
    await expect(page).toHaveURL(/\/app\/admin\/reporting/)
  })

  test('sidebar shows reporting link for admin', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('sidebar-link-admin-reporting')).toBeVisible()
  })
})

test.describe('Reporting – page structure', () => {
  test('shows page heading', async ({ adminPage: page }) => {
    await page.goto('/app/admin/reporting')
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })

  test('shows overview section', async ({ adminPage: page }) => {
    await page.goto('/app/admin/reporting')
    await expect(page.getByTestId('section-overview')).toBeVisible()
  })

  test('shows export button', async ({ adminPage: page }) => {
    await page.goto('/app/admin/reporting')
    await expect(page.getByTestId('btn-export')).toBeVisible()
  })

  test('shows charts or no-data state', async ({ adminPage: page }) => {
    await page.goto('/app/admin/reporting')
    // With no bookings the charts div is empty (hidden); the no-data card shows instead
    await expect(
      page.getByTestId('section-charts').or(page.getByText(/no data|keine daten/i)),
    ).toBeVisible()
  })
})

test.describe('Reporting – member RBAC', () => {
  test('member cannot access reporting page', async ({ memberPage: member }) => {
    await member.goto('/app/admin/reporting')
    // Should redirect away
    await expect(member).not.toHaveURL(/\/app\/admin\/reporting/)
  })
})
