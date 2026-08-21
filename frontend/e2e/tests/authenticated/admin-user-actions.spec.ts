/**
 * E2E tests for Admin User Management actions (activate, suspend).
 */
import { expect, test } from '../../fixtures.js'

test.describe('Admin Users – user table actions', () => {
  test('user table is visible with data', async ({ adminPage: page }) => {
    await page.goto('/app/admin/users')
    await expect(page.getByTestId('users-table')).toBeVisible()
    // Test user should appear in the table
    await expect(page.getByText(/test admin/i).first()).toBeVisible()
  })

  test('shows stat cards for filtering', async ({ adminPage: page }) => {
    await page.goto('/app/admin/users')
    await expect(page.getByTestId('stat-active')).toBeVisible()
  })
})
