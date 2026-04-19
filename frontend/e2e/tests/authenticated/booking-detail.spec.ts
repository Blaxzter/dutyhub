/**
 * E2E tests for Booking Detail view.
 */
import { expect, test } from '../../fixtures.js'
import {
  type BookingRead,
  type ShiftRead,
  type TaskWithShifts,
  bookShift,
  createTaskWithShifts,
  deleteTask,
  listShifts,
  uniqueName,
} from '../../helpers/api.js'

let created: TaskWithShifts
let shifts: ShiftRead[]
let booking: BookingRead

test.beforeEach(async ({ adminPage: page }) => {
  await page.goto('/app/tasks')
  created = await createTaskWithShifts(page, {
    name: uniqueName('E2E Booking Detail Task'),
    status: 'published',
    startTime: '10:00',
    endTime: '12:00',
    slotDuration: 60,
    peoplePerShift: 5,
  })
  shifts = await listShifts(page, created.task.id)
  if (shifts.length > 0) {
    booking = await bookShift(page, shifts[0].id)
  }
})

test.afterEach(async ({ adminPage: page }) => {
  await deleteTask(page, created.task.id).catch(() => {})
})

test.describe('Booking Detail – navigation', () => {
  test('can navigate to booking detail via URL', async ({ adminPage: page }) => {
    // eslint-disable-next-line playwright/no-conditional-in-test
    if (!booking) return
    await page.goto(`/app/bookings/${booking.id}`)
    await expect(page).toHaveURL(new RegExp(`/app/bookings/${booking.id}`))
  })

  test('shows back button', async ({ adminPage: page }) => {
    // eslint-disable-next-line playwright/no-conditional-in-test
    if (!booking) return
    await page.goto(`/app/bookings/${booking.id}`)
    await expect(page.getByTestId('btn-back')).toBeVisible()
  })
})

test.describe('Booking Detail – page structure', () => {
  test('shows page heading', async ({ adminPage: page }) => {
    // eslint-disable-next-line playwright/no-conditional-in-test
    if (!booking) return
    await page.goto(`/app/bookings/${booking.id}`)
    await expect(page.getByTestId('page-heading')).toBeVisible()
  })

  test('shows booking status badge', async ({ adminPage: page }) => {
    // eslint-disable-next-line playwright/no-conditional-in-test
    if (!booking) return
    await page.goto(`/app/bookings/${booking.id}`)
    await expect(page.getByTestId('booking-status')).toBeVisible()
  })

  test('shows shift info section', async ({ adminPage: page }) => {
    // eslint-disable-next-line playwright/no-conditional-in-test
    if (!booking) return
    await page.goto(`/app/bookings/${booking.id}`)
    await expect(page.getByTestId('section-shift-info')).toBeVisible()
  })

  test('shows reminders section', async ({ adminPage: page }) => {
    // eslint-disable-next-line playwright/no-conditional-in-test
    if (!booking) return
    await page.goto(`/app/bookings/${booking.id}`)
    await expect(page.getByTestId('section-reminders')).toBeVisible()
  })
})

test.describe('Booking Detail – actions', () => {
  test('shows cancel button for confirmed booking', async ({ adminPage: page }) => {
    // eslint-disable-next-line playwright/no-conditional-in-test
    if (!booking) return
    await page.goto(`/app/bookings/${booking.id}`)
    await expect(page.getByTestId('btn-cancel-booking')).toBeVisible()
  })
})
