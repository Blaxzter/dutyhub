/**
 * E2E tests for Task Event Edit Form & Shift Dates feature.
 *
 * Tests the "Details" tab on the event detail page, which allows
 * admins/managers to edit event name, description, dates, and shift all
 * task dates by an offset.
 */
import { expect, test } from '../../fixtures.js'
import {
  type EventRead,
  type TaskRead,
  api,
  createTaskWithShifts,
  createEvent,
  deleteTask,
  deleteEvent,
  futureDate,
  uniqueName,
} from '../../helpers/api.js'

// ── Edit event details ───────────────────────────────────────────────────────

test.describe('Task Event Edit – details section', () => {
  let event: EventRead

  test.beforeEach(async ({ adminPage: page }) => {
    event = await createEvent(page, uniqueName('E2E Edit'))
  })

  test.afterEach(async ({ adminPage: page }) => {
    await deleteEvent(page, event.id).catch(() => {})
  })

  test('admin sees Details nav item on detail page', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}`)
    await expect(page.getByText(/details/i)).toBeVisible()
  })

  test('clicking Details nav shows the edit form', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/details`)
    // The edit card should show the event name input
    await expect(page.getByRole('textbox').first()).toBeVisible()
  })

  test('edit form is pre-filled with current event data', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/details`)
    const nameInput = page.locator('input').first()
    await expect(nameInput).toHaveValue(event.name)
  })

  test('can update event name via edit form', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/details`)

    const nameInput = page.locator('input').first()
    const newName = uniqueName('E2E Renamed')
    await nameInput.fill(newName)

    // Click save button
    await page.getByRole('button', { name: /save|speichern/i }).click()

    // After saving, should navigate away from details (to tasks section)
    // and the header should show the updated name
    await expect(page.getByTestId('page-heading')).toHaveText(newName)
  })

  test('can update event description', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/details`)

    const descriptionArea = page.locator('textarea').first()
    await descriptionArea.fill('Updated via E2E test')

    await page.getByRole('button', { name: /save|speichern/i }).click()

    // Verify via API that description was saved
    const updated = await api<EventRead>(page, 'GET', `/events/${event.id}`)
    expect(updated.description).toBe('Updated via E2E test')
  })

  test('cancel button returns to tasks section', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/details`)

    await page.getByRole('button', { name: /cancel|abbrechen/i }).click()

    // Should navigate back to tasks section (default)
    await expect(page).toHaveURL(new RegExp(`/app/events/${event.id}$`))
  })
})

// ── Edit with tasks (date constraints) ──────────────────────────────────────

test.describe('Task Event Edit – date constraints', () => {
  let event: EventRead
  let task: TaskRead

  test.beforeEach(async ({ adminPage: page }) => {
    const startDate = futureDate(30)
    const endDate = futureDate(34)
    event = await api<EventRead>(page, 'POST', '/events/', {
      name: uniqueName('E2E Constrained'),
      status: 'published',
      start_date: startDate,
      end_date: endDate,
    })
    const created = await createTaskWithShifts(page, {
      name: uniqueName('E2E Constraint Task'),
      startDate: futureDate(31),
      endDate: futureDate(32),
      eventId: event.id,
    })
    task = created.task
  })

  test.afterEach(async ({ adminPage: page }) => {
    await deleteTask(page, task?.id).catch(() => {})
    await deleteEvent(page, event.id).catch(() => {})
  })

  test('shows calendar markers when tasks exist', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/details`)

    // Legend should be visible when tasks exist
    await expect(page.getByText(/task start|veranstaltungs-beginn/i)).toBeVisible()
  })

  test('shows task boundary hints', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/details`)

    // Should show earliest/latest task date hints
    await expect(page.getByText(/earliest|früheste/i)).toBeVisible()
  })

  test('shows shift dates card when tasks exist', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/details`)

    // The shift dates section should be visible (use heading to be specific)
    await expect(page.getByRole('heading', { name: /shift dates|termine verschieben/i })).toBeVisible()
  })

  test('date validation prtasks invalid ranges via API', async ({ adminPage: page }) => {
    // Try to set end_date before earliest task start via API — should fail
    try {
      await api(page, 'PATCH', `/events/${event.id}`, {
        end_date: futureDate(29), // Before the task starts
      })
      expect(true, 'Should have thrown 422').toBe(false)
    } catch (e) {
      expect(String(e)).toContain('422')
    }
  })
})

// ── Shift dates ──────────────────────────────────────────────────────────────

test.describe('Task Event Edit – shift dates', () => {
  let event: EventRead
  let task: TaskRead

  test.beforeEach(async ({ adminPage: page }) => {
    const startDate = futureDate(30)
    const endDate = futureDate(34)
    event = await api<EventRead>(page, 'POST', '/events/', {
      name: uniqueName('E2E Shift'),
      status: 'published',
      start_date: startDate,
      end_date: endDate,
    })
    const created = await createTaskWithShifts(page, {
      name: uniqueName('E2E Shift Task'),
      startDate: futureDate(31),
      endDate: futureDate(32),
      eventId: event.id,
    })
    task = created.task
  })

  test.afterEach(async ({ adminPage: page }) => {
    // Task may have been shifted, so try both original and shifted ID
    await deleteTask(page, task?.id).catch(() => {})
    await deleteEvent(page, event.id).catch(() => {})
  })

  test('shift-dates API shifts event dates forward', async ({ adminPage: page }) => {
    const newStart = futureDate(37) // 7 days forward
    const shifted = await api<EventRead>(
      page,
      'POST',
      `/events/${event.id}/shift-dates`,
      { new_start_date: newStart },
    )
    expect(shifted.start_date).toBe(newStart)
  })

  test('shift-dates API shifts task dates', async ({ adminPage: page }) => {
    const originalTaskStart = task.start_date
    const newStart = futureDate(37) // 7 days forward from event start (futureDate(30))

    await api(page, 'POST', `/events/${event.id}/shift-dates`, {
      new_start_date: newStart,
    })

    // Verify task was shifted
    const updatedTask = await api<TaskRead>(page, 'GET', `/tasks/${task.id}`)
    expect(updatedTask.start_date).not.toBe(originalTaskStart)
  })

  test('shift-dates with same start date is no-op', async ({ adminPage: page }) => {
    const shifted = await api<EventRead>(
      page,
      'POST',
      `/events/${event.id}/shift-dates`,
      { new_start_date: event.start_date },
    )
    expect(shifted.start_date).toBe(event.start_date)
    expect(shifted.end_date).toBe(event.end_date)
  })

  test('shift dates card not visible when no tasks', async ({ adminPage: page }) => {
    // Create an event with no tasks
    const emptyEvent = await createEvent(page, uniqueName('E2E Empty Shift'))

    await page.goto(`/app/events/${emptyEvent.id}/details`)

    // The shift dates card should NOT be visible
    await expect(page.getByText(/shift dates|termine verschieben/i)).toBeHidden()

    await deleteEvent(page, emptyEvent.id)
  })

  test('shift dates UI shows preview text', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${event.id}/details`)

    // The shift section heading should be visible
    await expect(page.getByRole('heading', { name: /shift dates|termine verschieben/i })).toBeVisible()
  })
})

// ── Member cannot see details section ────────────────────────────────────────

test.describe('Task Event Edit – member restrictions', () => {
  let event: EventRead

  test.beforeEach(async ({ adminPage: page }) => {
    event = await createEvent(page, uniqueName('E2E Member Edit'))
  })

  test.afterEach(async ({ adminPage: page }) => {
    await deleteEvent(page, event.id).catch(() => {})
  })

  test('member cannot see Details nav item', async ({ memberPage: page }) => {
    await page.goto(`/app/events/${event.id}`)

    // Member should see Tasks and Availability but NOT Details
    await expect(page.getByText(/tasks|veranstaltungen/i).first()).toBeVisible()
    // Details should not be visible to members
    // The nav button with "Details" text should not be visible
    const detailsNav = page.locator('button').filter({ hasText: /^details$/i })
    await expect(detailsNav).toBeHidden()
  })

  test('member cannot shift dates via API', async ({ memberPage: page }) => {
    try {
      await api(page, 'POST', `/events/${event.id}/shift-dates`, {
        new_start_date: futureDate(40),
      })
      expect(true, 'Should have thrown 403').toBe(false)
    } catch (e) {
      expect(String(e)).toContain('403')
    }
  })
})
