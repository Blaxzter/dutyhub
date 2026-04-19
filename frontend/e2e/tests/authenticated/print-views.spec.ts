/**
 * E2E smoke tests for Print views.
 */
import { expect, test } from '../../fixtures.js'
import {
  type EventRead,
  type TaskWithShifts,
  createTaskWithShifts,
  createGroup,
  deleteTask,
  deleteGroup,
  uniqueName,
} from '../../helpers/api.js'

let created: TaskWithShifts
let group: EventRead

test.beforeEach(async ({ adminPage: page }) => {
  await page.goto('/app/tasks')
  group = await createGroup(page, uniqueName('E2E Print Group'))
  created = await createTaskWithShifts(page, {
    name: uniqueName('E2E Print Task'),
    status: 'published',
    startTime: '09:00',
    endTime: '12:00',
    slotDuration: 60,
    peoplePerShift: 2,
    eventId: group.id,
  })
})

test.afterEach(async ({ adminPage: page }) => {
  await deleteTask(page, created.task.id).catch(() => {})
  await deleteGroup(page, group.id).catch(() => {})
})

test.describe('Print Task – smoke', () => {
  test('print task page loads', async ({ adminPage: page }) => {
    await page.goto(`/print/tasks/${created.task.id}`)
    await expect(page).toHaveURL(new RegExp(`/print/tasks/${created.task.id}`))
  })

  test('shows print toolbar', async ({ adminPage: page }) => {
    await page.goto(`/print/tasks/${created.task.id}`)
    await expect(page.getByTestId('print-toolbar')).toBeVisible()
  })

  test('shows print content', async ({ adminPage: page }) => {
    await page.goto(`/print/tasks/${created.task.id}`)
    await expect(page.getByTestId('print-content')).toBeVisible()
  })

  test('shows task name in print content', async ({ adminPage: page }) => {
    await page.goto(`/print/tasks/${created.task.id}`)
    // Dynamic task name from fixture
    await expect(page.getByText(created.task.name).first()).toBeVisible()
  })
})

test.describe('Print Task Group – smoke', () => {
  test('print task group page loads', async ({ adminPage: page }) => {
    await page.goto(`/print/events/${group.id}`)
    await expect(page).toHaveURL(new RegExp(`/print/events/${group.id}`))
  })

  test('shows print toolbar for group', async ({ adminPage: page }) => {
    await page.goto(`/print/events/${group.id}`)
    await expect(page.getByTestId('print-toolbar')).toBeVisible()
  })

  test('shows group name in print content', async ({ adminPage: page }) => {
    await page.goto(`/print/events/${group.id}`)
    // Dynamic group name from fixture
    await expect(page.getByText(group.name)).toBeVisible()
  })
})
