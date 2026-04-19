/**
 * E2E tests for Task Edit and Add Shifts views.
 */
import { expect, test } from '../../fixtures.js'
import {
  type TaskWithShifts,
  createTaskWithShifts,
  deleteTask,
  uniqueName,
} from '../../helpers/api.js'

let created: TaskWithShifts

test.beforeEach(async ({ adminPage: page }) => {
  await page.goto('/app/tasks')
  created = await createTaskWithShifts(page, {
    name: uniqueName('E2E Edit Task'),
    status: 'published',
    startTime: '09:00',
    endTime: '17:00',
    slotDuration: 120,
    peoplePerShift: 2,
  })
})

test.afterEach(async ({ adminPage: page }) => {
  await deleteTask(page, created.task.id).catch(() => {})
})

test.describe('Task Edit – page access', () => {
  test('can navigate to edit page via URL', async ({ adminPage: page }) => {
    await page.goto(`/app/tasks/${created.task.id}/edit`)
    await expect(page).toHaveURL(new RegExp(`/app/tasks/${created.task.id}/edit`))
  })

  test('shows edit page heading', async ({ adminPage: page }) => {
    await page.goto(`/app/tasks/${created.task.id}/edit`)
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })

  test('shows back button', async ({ adminPage: page }) => {
    await page.goto(`/app/tasks/${created.task.id}/edit`)
    await expect(page.getByTestId('btn-back')).toBeVisible()
  })

  test('shows schedule configuration section', async ({ adminPage: page }) => {
    await page.goto(`/app/tasks/${created.task.id}/edit`)
    await expect(page.getByTestId('section-schedule')).toBeVisible()
  })
})

test.describe('Task Add Shifts – page access', () => {
  test('can navigate to add-shifts page via URL', async ({ adminPage: page }) => {
    await page.goto(`/app/tasks/${created.task.id}/add-shifts`)
    await expect(page).toHaveURL(new RegExp(`/app/tasks/${created.task.id}/add-shifts`))
  })

  test('shows add-shifts heading', async ({ adminPage: page }) => {
    await page.goto(`/app/tasks/${created.task.id}/add-shifts`)
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })

  test('shows back button', async ({ adminPage: page }) => {
    await page.goto(`/app/tasks/${created.task.id}/add-shifts`)
    await expect(page.getByTestId('btn-back')).toBeVisible()
  })
})

test.describe('Task Edit/Add Shifts – member RBAC', () => {
  test('member cannot access edit page', async ({ memberPage: member }) => {
    await member.goto(`/app/tasks/${created.task.id}/edit`)
    await expect(member).not.toHaveURL(/\/edit/)
  })

  test('member cannot access add-shifts page', async ({ memberPage: member }) => {
    await member.goto(`/app/tasks/${created.task.id}/add-shifts`)
    await expect(member).not.toHaveURL(/\/add-shifts/)
  })
})
