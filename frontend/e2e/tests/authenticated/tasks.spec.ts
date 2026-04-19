/**
 * E2E tests for Tasks list view.
 */
import { expect, test } from '../../fixtures.js'
import {
  type TaskWithShifts,
  createTaskWithShifts,
  deleteTask,
  uniqueName,
} from '../../helpers/api.js'

// ── navigation ───────────────────────────────────────────────────────────────

test.describe('Tasks – navigation', () => {
  test('sidebar shows Tasks link', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('sidebar-link-tasks')).toBeVisible()
  })

  test('clicking sidebar link navigates to /app/tasks', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('sidebar-link-tasks').click()
    await expect(page).toHaveURL(/\/app\/tasks$/)
  })

  test('direct navigation to /app/tasks works', async ({ adminPage: page }) => {
    await page.goto('/app/tasks')
    await expect(page).toHaveURL(/\/app\/tasks$/)
  })
})

// ── list view ────────────────────────────────────────────────────────────────

test.describe('Tasks – list view', () => {
  let created: TaskWithShifts

  test.beforeEach(async ({ adminPage: page }) => {
    await page.goto('/app/tasks')
    created = await createTaskWithShifts(page, { name: uniqueName('E2E Test Task List'), status: 'published' })
  })

  test.afterEach(async ({ adminPage: page }) => {
    await deleteTask(page, created.task.id).catch(() => {})
  })

  test('shows heading and search input', async ({ adminPage: page }) => {
    await page.goto('/app/tasks')
    await expect(page.getByTestId('page-heading')).toBeVisible()
    await expect(page.getByTestId('input-search')).toBeVisible()
  })

  test('created task appears in list after search', async ({ adminPage: page }) => {
    // Use search to find the task (list is paginated with infinite scroll)
    await page.reload()
    const content = page.getByTestId('main-content')
    await page.getByTestId('input-search').fill(created.task.name)
    await expect(content.getByText(created.task.name)).toBeVisible()
  })

  test('search filters tasks by name', async ({ adminPage: page }) => {
    const searchInput = page.getByTestId('input-search')
    const content = page.getByTestId('main-content')

    await searchInput.fill(created.task.name)
    await expect(content.getByText(created.task.name)).toBeVisible()

    await searchInput.fill('zzzznomatch')
    await expect(content.getByText(created.task.name)).toBeHidden()
  })

  test('clicking a task card navigates to detail', async ({ adminPage: page }) => {
    const content = page.getByTestId('main-content')
    // Search to find the task in the paginated list
    await page.getByTestId('input-search').fill(created.task.name)
    await expect(content.getByText(created.task.name)).toBeVisible()
    await content.getByText(created.task.name).click()
    await expect(page).toHaveURL(new RegExp(`/app/tasks/${created.task.id}`))
  })
})

// ── view mode toggles ────────────────────────────────────────────────────────

test.describe('Tasks – view modes', () => {
  test('can switch to cards view', async ({ adminPage: page }) => {
    await page.goto('/app/tasks')
    await page.getByTestId('btn-view-cards').click()
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })

  test('can switch to calendar view', async ({ adminPage: page }) => {
    await page.goto('/app/tasks')
    await page.getByTestId('btn-view-calendar').click()
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })

  test('can switch back to list view', async ({ adminPage: page }) => {
    await page.goto('/app/tasks')
    await page.getByTestId('btn-view-calendar').click()
    await page.getByTestId('btn-view-list').click()
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })
})

// ── admin actions ────────────────────────────────────────────────────────────

test.describe('Tasks – admin', () => {
  test('Create button is visible for admin', async ({ adminPage: page }) => {
    await page.goto('/app/tasks')
    await expect(page.getByTestId('btn-create-task')).toBeVisible()
  })

  test('Create button navigates to create page', async ({ adminPage: page }) => {
    await page.goto('/app/tasks')
    await page.getByTestId('btn-create-task').click()
    await expect(page).toHaveURL(/\/app\/tasks\/create/)
  })
})
