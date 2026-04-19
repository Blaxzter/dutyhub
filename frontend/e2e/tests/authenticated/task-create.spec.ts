/**
 * E2E tests for Task Creation wizard.
 */
import { expect, test } from '../../fixtures.js'
import { api, deleteTask } from '../../helpers/api.js'

// ── page access ──────────────────────────────────────────────────────────────

test.describe('Task Create – page access', () => {
  test('can navigate to create page', async ({ adminPage: page }) => {
    await page.goto('/app/tasks/create')
    await expect(page).toHaveURL(/\/app\/tasks\/create/)
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })

  test('shows back button', async ({ adminPage: page }) => {
    await page.goto('/app/tasks/create')
    await expect(page.getByTestId('btn-back')).toBeVisible()
  })

  test('back button navigates to tasks', async ({ adminPage: page }) => {
    await page.goto('/app/tasks/create')
    await page.getByTestId('btn-back').click()
    await expect(page).toHaveURL(/\/app\/tasks$/)
  })
})

// ── form sections ────────────────────────────────────────────────────────────

test.describe('Task Create – form wizard', () => {
  test('shows accordion sections', async ({ adminPage: page }) => {
    await page.goto('/app/tasks/create')
    // The accordion sections are visible via test IDs
    await expect(page.getByTestId('section-task-details')).toBeVisible()
  })

  test('can fill task name in details section', async ({ adminPage: page }) => {
    await page.goto('/app/tasks/create')
    const nameInput = page.getByTestId('input-task-name')
    await nameInput.fill('E2E Create Test Task')
    await expect(nameInput).toHaveValue('E2E Create Test Task')
  })

  test('Next button advances to next section', async ({ adminPage: page }) => {
    await page.goto('/app/tasks/create')
    const nameInput = page.getByTestId('input-task-name')
    await nameInput.fill('Test Task')
    // Click the Next button inside the active (details) section (matches both EN "Next" and DE "Weiter")
    await page
      .getByTestId('section-task-details')
      .getByRole('button', { name: /next|weiter/i })
      .click()
    // Second section should now be visible (Task Group)
    await expect(page.getByTestId('section-event')).toBeVisible()
  })
})

// ── cleanup ──────────────────────────────────────────────────────────────────

test.afterEach(async ({ adminPage: page }) => {
  try {
    const tasks = await api<{ items: Array<{ id: string; name: string }> }>(
      page,
      'GET',
      '/tasks/?limit=100',
    )
    for (const task of tasks.items) {
      if (task.name.startsWith('E2E Create') || task.name.startsWith('E2E Full')) {
        await deleteTask(page, task.id).catch(() => {})
      }
    }
  } catch {
    // Best effort cleanup
  }
})
