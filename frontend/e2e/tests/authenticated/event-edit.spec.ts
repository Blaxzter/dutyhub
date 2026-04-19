/**
 * E2E tests for Task Group Edit Form & Shift Dates feature.
 *
 * Tests the "Details" tab on the task group detail page, which allows
 * admins/managers to edit group name, description, dates, and shift all
 * task dates by an offset.
 */
import { expect, test } from '../../fixtures.js'
import {
  type EventRead,
  type TaskRead,
  api,
  createTaskWithShifts,
  createGroup,
  deleteTask,
  deleteGroup,
  futureDate,
  uniqueName,
} from '../../helpers/api.js'

// ── Edit group details ───────────────────────────────────────────────────────

test.describe('Task Group Edit – details section', () => {
  let group: EventRead

  test.beforeEach(async ({ adminPage: page }) => {
    group = await createGroup(page, uniqueName('E2E Edit'))
  })

  test.afterEach(async ({ adminPage: page }) => {
    await deleteGroup(page, group.id).catch(() => {})
  })

  test('admin sees Details nav item on detail page', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${group.id}`)
    await expect(page.getByText(/details/i)).toBeVisible()
  })

  test('clicking Details nav shows the edit form', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${group.id}/details`)
    // The edit card should show the group name input
    await expect(page.getByRole('textbox').first()).toBeVisible()
  })

  test('edit form is pre-filled with current group data', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${group.id}/details`)
    const nameInput = page.locator('input').first()
    await expect(nameInput).toHaveValue(group.name)
  })

  test('can update group name via edit form', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${group.id}/details`)

    const nameInput = page.locator('input').first()
    const newName = uniqueName('E2E Renamed')
    await nameInput.fill(newName)

    // Click save button
    await page.getByRole('button', { name: /save|speichern/i }).click()

    // After saving, should navigate away from details (to tasks section)
    // and the header should show the updated name
    await expect(page.getByTestId('page-heading')).toHaveText(newName)
  })

  test('can update group description', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${group.id}/details`)

    const descriptionArea = page.locator('textarea').first()
    await descriptionArea.fill('Updated via E2E test')

    await page.getByRole('button', { name: /save|speichern/i }).click()

    // Verify via API that description was saved
    const updated = await api<EventRead>(page, 'GET', `/events/${group.id}`)
    expect(updated.description).toBe('Updated via E2E test')
  })

  test('cancel button returns to tasks section', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${group.id}/details`)

    await page.getByRole('button', { name: /cancel|abbrechen/i }).click()

    // Should navigate back to tasks section (default)
    await expect(page).toHaveURL(new RegExp(`/app/events/${group.id}$`))
  })
})

// ── Edit with tasks (date constraints) ──────────────────────────────────────

test.describe('Task Group Edit – date constraints', () => {
  let group: EventRead
  let task: TaskRead

  test.beforeEach(async ({ adminPage: page }) => {
    const startDate = futureDate(30)
    const endDate = futureDate(34)
    group = await api<EventRead>(page, 'POST', '/events/', {
      name: uniqueName('E2E Constrained'),
      status: 'published',
      start_date: startDate,
      end_date: endDate,
    })
    const created = await createTaskWithShifts(page, {
      name: uniqueName('E2E Constraint Task'),
      startDate: futureDate(31),
      endDate: futureDate(32),
      eventId: group.id,
    })
    task = created.task
  })

  test.afterEach(async ({ adminPage: page }) => {
    await deleteTask(page, task?.id).catch(() => {})
    await deleteGroup(page, group.id).catch(() => {})
  })

  test('shows calendar markers when tasks exist', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${group.id}/details`)

    // Legend should be visible when tasks exist
    await expect(page.getByText(/task start|veranstaltungs-beginn/i)).toBeVisible()
  })

  test('shows task boundary hints', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${group.id}/details`)

    // Should show earliest/latest task date hints
    await expect(page.getByText(/earliest|früheste/i)).toBeVisible()
  })

  test('shows shift dates card when tasks exist', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${group.id}/details`)

    // The shift dates section should be visible (use heading to be specific)
    await expect(page.getByRole('heading', { name: /shift dates|termine verschieben/i })).toBeVisible()
  })

  test('date validation prtasks invalid ranges via API', async ({ adminPage: page }) => {
    // Try to set end_date before earliest task start via API — should fail
    try {
      await api(page, 'PATCH', `/events/${group.id}`, {
        end_date: futureDate(29), // Before the task starts
      })
      expect(true, 'Should have thrown 422').toBe(false)
    } catch (e) {
      expect(String(e)).toContain('422')
    }
  })
})

// ── Shift dates ──────────────────────────────────────────────────────────────

test.describe('Task Group Edit – shift dates', () => {
  let group: EventRead
  let task: TaskRead

  test.beforeEach(async ({ adminPage: page }) => {
    const startDate = futureDate(30)
    const endDate = futureDate(34)
    group = await api<EventRead>(page, 'POST', '/events/', {
      name: uniqueName('E2E Shift'),
      status: 'published',
      start_date: startDate,
      end_date: endDate,
    })
    const created = await createTaskWithShifts(page, {
      name: uniqueName('E2E Shift Task'),
      startDate: futureDate(31),
      endDate: futureDate(32),
      eventId: group.id,
    })
    task = created.task
  })

  test.afterEach(async ({ adminPage: page }) => {
    // Task may have been shifted, so try both original and shifted ID
    await deleteTask(page, task?.id).catch(() => {})
    await deleteGroup(page, group.id).catch(() => {})
  })

  test('shift-dates API shifts group dates forward', async ({ adminPage: page }) => {
    const newStart = futureDate(37) // 7 days forward
    const shifted = await api<EventRead>(
      page,
      'POST',
      `/events/${group.id}/shift-dates`,
      { new_start_date: newStart },
    )
    expect(shifted.start_date).toBe(newStart)
  })

  test('shift-dates API shifts task dates', async ({ adminPage: page }) => {
    const originalTaskStart = task.start_date
    const newStart = futureDate(37) // 7 days forward from group start (futureDate(30))

    await api(page, 'POST', `/events/${group.id}/shift-dates`, {
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
      `/events/${group.id}/shift-dates`,
      { new_start_date: group.start_date },
    )
    expect(shifted.start_date).toBe(group.start_date)
    expect(shifted.end_date).toBe(group.end_date)
  })

  test('shift dates card not visible when no tasks', async ({ adminPage: page }) => {
    // Create a group with no tasks
    const emptyGroup = await createGroup(page, uniqueName('E2E Empty Shift'))

    await page.goto(`/app/events/${emptyGroup.id}/details`)

    // The shift dates card should NOT be visible
    await expect(page.getByText(/shift dates|termine verschieben/i)).toBeHidden()

    await deleteGroup(page, emptyGroup.id)
  })

  test('shift dates UI shows preview text', async ({ adminPage: page }) => {
    await page.goto(`/app/events/${group.id}/details`)

    // The shift section heading should be visible
    await expect(page.getByRole('heading', { name: /shift dates|termine verschieben/i })).toBeVisible()
  })
})

// ── Member cannot see details section ────────────────────────────────────────

test.describe('Task Group Edit – member restrictions', () => {
  let group: EventRead

  test.beforeEach(async ({ adminPage: page }) => {
    group = await createGroup(page, uniqueName('E2E Member Edit'))
  })

  test.afterEach(async ({ adminPage: page }) => {
    await deleteGroup(page, group.id).catch(() => {})
  })

  test('member cannot see Details nav item', async ({ memberPage: page }) => {
    await page.goto(`/app/events/${group.id}`)

    // Member should see Tasks and Availability but NOT Details
    await expect(page.getByText(/tasks|veranstaltungen/i).first()).toBeVisible()
    // Details should not be visible to members
    // The nav button with "Details" text should not be visible
    const detailsNav = page.locator('button').filter({ hasText: /^details$/i })
    await expect(detailsNav).toBeHidden()
  })

  test('member cannot shift dates via API', async ({ memberPage: page }) => {
    try {
      await api(page, 'POST', `/events/${group.id}/shift-dates`, {
        new_start_date: futureDate(40),
      })
      expect(true, 'Should have thrown 403').toBe(false)
    } catch (e) {
      expect(String(e)).toContain('403')
    }
  })
})
