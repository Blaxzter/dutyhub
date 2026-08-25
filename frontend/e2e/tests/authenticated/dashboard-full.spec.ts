/**
 * E2E tests for the Dashboard — next shift, the two lists and quick actions.
 *
 * The page used to be a month calendar; it is now "what you have said yes to"
 * and "where people are still missing", so these specs follow a shift from
 * being on offer to being on the hero card.
 */
import { expect, test } from '../../fixtures.js'
import {
  type ShiftRead,
  type TaskWithShifts,
  bookShift,
  cancelBooking,
  createTaskWithShifts,
  deleteTask,
  listShifts,
  uniqueName,
} from '../../helpers/api.js'

let created: TaskWithShifts
let shifts: ShiftRead[]
let taskName: string

test.beforeEach(async ({ adminPage: page }) => {
  taskName = uniqueName('E2E Dashboard Task')
  created = await createTaskWithShifts(page, {
    name: taskName,
    location: 'Main Gate',
    status: 'published',
    // Earlier than the 10:00 default every other spec uses, so this task's
    // shifts are unambiguously the soonest thing the worker's admin is on and
    // the headline card cannot be won by a stray booking from elsewhere.
    startTime: '08:00',
    endTime: '10:00',
    slotDuration: 60,
    peoplePerShift: 3,
  })
  shifts = await listShifts(page, created.task.id)
})

test.afterEach(async ({ adminPage: page }) => {
  await deleteTask(page, created.task.id).catch(() => {})
})

test.describe('Dashboard – page structure', () => {
  test('leads with the next-shift card', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('dashboard-next-shift')).toBeVisible()
  })

  test('shows the shifts that still need people', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('dashboard-open-shifts')).toBeVisible()
  })

  test('shows Quick Actions section', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('dashboard-quick-actions')).toBeVisible()
  })
})

test.describe('Dashboard – shifts that need people', () => {
  test('lists a shift from a freshly published job', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(
      page.getByTestId('dashboard-open-shifts').getByText(taskName).first(),
    ).toBeVisible()
  })

  test('a shift nobody has taken is marked as such', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    const row = page
      .getByTestId('dashboard-open-shifts')
      .getByTestId('shift-row')
      .filter({ hasText: taskName })
      .first()
    await expect(row).toContainText('Nobody yet')
  })

  test('pressing a row opens the shift', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page
      .getByTestId('dashboard-open-shifts')
      .getByTestId('shift-row')
      .filter({ hasText: taskName })
      .first()
      .click()
    await expect(page.getByTestId('dialog-shift-detail')).toBeVisible()
  })

  test('Browse shifts goes to the task list', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('btn-browse-open-shifts').click()
    await expect(page).toHaveURL(/\/app\/tasks/)
  })
})

test.describe('Dashboard – what you have said yes to', () => {
  test('a booked shift becomes the headline and leaves the offer list', async ({
    adminPage: page,
  }) => {
    const booking = await bookShift(page, shifts[0].id)
    try {
      await page.goto('/app/home')
      const hero = page.getByTestId('dashboard-next-shift')
      await expect(hero).toContainText(taskName)
      await expect(hero).toContainText('Main Gate')
      await expect(
        page
          .getByTestId('dashboard-open-shifts')
          .getByTestId('shift-row')
          .filter({ hasText: shifts[0].title }),
      ).toHaveCount(0)
    } finally {
      await cancelBooking(page, booking.id).catch(() => {})
    }
  })

  test('the headline opens the shift it names', async ({ adminPage: page }) => {
    const booking = await bookShift(page, shifts[0].id)
    try {
      await page.goto('/app/home')
      await page.getByTestId('btn-open-next-shift').click()
      await expect(page.getByTestId('dialog-shift-detail')).toBeVisible()
    } finally {
      await cancelBooking(page, booking.id).catch(() => {})
    }
  })

  test('a second booking lands in the list under the headline', async ({ adminPage: page }) => {
    const first = await bookShift(page, shifts[0].id)
    const second = await bookShift(page, shifts[1].id)
    try {
      await page.goto('/app/home')
      await expect(page.getByTestId('dashboard-my-shifts')).toBeVisible()
      await expect(page.getByTestId('dashboard-my-shifts')).toContainText(taskName)
    } finally {
      await cancelBooking(page, first.id).catch(() => {})
      await cancelBooking(page, second.id).catch(() => {})
    }
  })
})

test.describe('Dashboard – the organiser view', () => {
  test('an organiser is told which shifts have nobody on them', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('dashboard-attention')).toBeVisible()
    await expect(page.getByTestId('attention-empty')).toBeVisible()
  })

  test('the gap link leads to the task list', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('attention-empty').click()
    await expect(page).toHaveURL(/\/app\/tasks/)
  })

  test('somebody who only helps out sees none of it', async ({ memberPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('dashboard-open-shifts')).toBeVisible()
    await expect(page.getByTestId('dashboard-attention')).toHaveCount(0)
  })
})

test.describe('Dashboard – quick actions', () => {
  test('shows Browse Tasks button', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('btn-browse-tasks')).toBeVisible()
  })

  test('shows My Bookings button', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await expect(page.getByTestId('btn-my-bookings')).toBeVisible()
  })

  test('Browse Tasks navigates to tasks page', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('btn-browse-tasks').click()
    await expect(page).toHaveURL(/\/app\/tasks/)
  })

  test('My Bookings quick action navigates to bookings', async ({ adminPage: page }) => {
    await page.goto('/app/home')
    await page.getByTestId('btn-my-bookings').click()
    await expect(page).toHaveURL(/\/app\/bookings/)
  })
})
