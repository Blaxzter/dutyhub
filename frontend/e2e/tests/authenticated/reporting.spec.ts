/**
 * E2E tests for Admin Reporting page.
 */
import { expect, test } from '../../fixtures.js'
import {
  type TaskWithShifts,
  bookShift,
  createTaskWithShifts,
  deleteTask,
  listShifts,
  uniqueName,
} from '../../helpers/api.js'

test.describe('Reporting – navigation', () => {
  test('can navigate to reporting page via URL', async ({ adminPage: page }) => {
    await page.goto('/app/reporting')
    await expect(page).toHaveURL(/\/app\/reporting/)
  })

  test('sidebar shows reporting link for admin', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('sidebar-link-reporting')).toBeVisible()
  })
})

test.describe('Reporting – page structure', () => {
  let created: TaskWithShifts

  test.beforeEach(async ({ adminPage: page }) => {
    created = await createTaskWithShifts(page, { name: uniqueName('Report'), status: 'published' })
    const shifts = await listShifts(page, created.task.id)
    await bookShift(page, shifts[0].id)
  })

  test.afterEach(async ({ adminPage: page }) => {
    await deleteTask(page, created?.task?.id).catch(() => {})
  })

  test('shows page heading', async ({ adminPage: page }) => {
    await page.goto('/app/reporting')
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })

  test('shows overview section', async ({ adminPage: page }) => {
    await page.goto('/app/reporting')
    await expect(page.getByTestId('section-overview')).toBeVisible()
  })

  test('shows export button', async ({ adminPage: page }) => {
    await page.goto('/app/reporting')
    await expect(page.getByTestId('btn-export')).toBeVisible()
  })

  test('shows charts with booking data', async ({ adminPage: page }) => {
    await page.goto('/app/reporting')
    await expect(page.getByTestId('section-charts')).toBeVisible()
  })
})

test.describe('Reporting – member RBAC', () => {
  test('member cannot access reporting page', async ({ memberPage: member }) => {
    await member.goto('/app/reporting')
    // Should redirect away
    await expect(member).not.toHaveURL(/\/app\/admin\/reporting/)
  })
})
