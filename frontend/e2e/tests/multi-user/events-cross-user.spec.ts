/**
 * Cross-user E2E tests for Tasks & Bookings.
 *
 * Admin creates task with shifts -> member books a shift -> admin sees booking count.
 */
import { expect, test } from '../../fixtures.js'
import {
  type TaskWithShifts,
  createTaskWithShifts,
  deleteTask,
  uniqueName,
} from '../../helpers/api.js'

test.describe('Cross-user – task booking flow', () => {
  let created: TaskWithShifts

  test.beforeEach(async ({ adminPage }) => {
    await adminPage.goto('/app/tasks')
    created = await createTaskWithShifts(adminPage, {
      name: uniqueName('E2E Cross-User Booking Task'),
      status: 'published',
      startTime: '10:00',
      endTime: '12:00',
      slotDuration: 60,
      peoplePerShift: 3,
    })
  })

  test.afterEach(async ({ adminPage }) => {
    await deleteTask(adminPage, created.task.id).catch(() => {})
  })

  test('member books shift, admin sees updated count', async ({ adminPage, memberPage }) => {
    // Member navigates to task and books first shift (dynamic shift counts)
    await memberPage.goto(`/app/tasks/${created.task.id}`)
    await expect(memberPage.getByText(/0\/3/).first()).toBeVisible()
    await memberPage.getByText(/0\/3/).first().click()
    await memberPage.getByTestId('btn-dialog-confirm').click()
    await expect(memberPage.getByText(/1\/3/).first()).toBeVisible()

    // Admin sees the updated booking count (dynamic shift counts)
    await adminPage.goto(`/app/tasks/${created.task.id}`)
    await expect(adminPage.getByText(/1\/3/).first()).toBeVisible()
  })

  test('admin-created task visible to member in tasks list', async ({ memberPage }) => {
    await memberPage.goto('/app/tasks')
    // Use search to find the task (list is paginated)
    await memberPage.getByTestId('input-search').fill(created.task.name)
    await expect(memberPage.getByRole('heading', { name: created.task.name })).toBeVisible()
  })
})
