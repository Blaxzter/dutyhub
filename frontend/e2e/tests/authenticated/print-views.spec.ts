/**
 * E2E smoke tests for Print views.
 */
import { expect, test } from '../../fixtures.js'
import {
  type EventRead,
  type TaskWithShifts,
  createTaskWithShifts,
  createEvent,
  deleteTask,
  deleteEvent,
  uniqueName,
} from '../../helpers/api.js'

let created: TaskWithShifts
let event: EventRead

test.beforeEach(async ({ adminPage: page }) => {
  await page.goto('/app/tasks')
  event = await createEvent(page, uniqueName('E2E Print Event'))
  created = await createTaskWithShifts(page, {
    name: uniqueName('E2E Print Task'),
    status: 'published',
    startTime: '09:00',
    endTime: '12:00',
    slotDuration: 60,
    peoplePerShift: 2,
    eventId: event.id,
  })
})

test.afterEach(async ({ adminPage: page }) => {
  await deleteTask(page, created.task.id).catch(() => {})
  await deleteEvent(page, event.id).catch(() => {})
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

test.describe('Print Task Event – smoke', () => {
  test('print event page loads', async ({ adminPage: page }) => {
    await page.goto(`/print/events/${event.id}`)
    await expect(page).toHaveURL(new RegExp(`/print/events/${event.id}`))
  })

  test('shows print toolbar for event', async ({ adminPage: page }) => {
    await page.goto(`/print/events/${event.id}`)
    await expect(page.getByTestId('print-toolbar')).toBeVisible()
  })

  test('shows event name in print content', async ({ adminPage: page }) => {
    await page.goto(`/print/events/${event.id}`)
    // Dynamic event name from fixture
    await expect(page.getByText(event.name)).toBeVisible()
  })
})
