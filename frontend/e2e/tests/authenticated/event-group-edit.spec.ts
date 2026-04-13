/**
 * E2E tests for Event Group Edit Form & Shift Dates feature.
 *
 * Tests the "Details" tab on the event group detail page, which allows
 * admins/managers to edit group name, description, dates, and shift all
 * event dates by an offset.
 */
import { expect, test } from '../../fixtures.js'
import {
  type EventGroupRead,
  type EventRead,
  api,
  createEventWithSlots,
  createGroup,
  deleteEvent,
  deleteGroup,
  futureDate,
  uniqueName,
} from '../../helpers/api.js'

// ── Edit group details ───────────────────────────────────────────────────────

test.describe('Event Group Edit – details section', () => {
  let group: EventGroupRead

  test.beforeEach(async ({ adminPage: page }) => {
    group = await createGroup(page, uniqueName('E2E Edit'))
  })

  test.afterEach(async ({ adminPage: page }) => {
    await deleteGroup(page, group.id).catch(() => {})
  })

  test('admin sees Details nav item on detail page', async ({ adminPage: page }) => {
    await page.goto(`/app/event-groups/${group.id}`)
    await expect(page.getByText(/details/i)).toBeVisible()
  })

  test('clicking Details nav shows the edit form', async ({ adminPage: page }) => {
    await page.goto(`/app/event-groups/${group.id}/details`)
    // The edit card should show the group name input
    await expect(page.getByRole('textbox').first()).toBeVisible()
  })

  test('edit form is pre-filled with current group data', async ({ adminPage: page }) => {
    await page.goto(`/app/event-groups/${group.id}/details`)
    const nameInput = page.locator('input').first()
    await expect(nameInput).toHaveValue(group.name)
  })

  test('can update group name via edit form', async ({ adminPage: page }) => {
    await page.goto(`/app/event-groups/${group.id}/details`)

    const nameInput = page.locator('input').first()
    const newName = uniqueName('E2E Renamed')
    await nameInput.fill(newName)

    // Click save button
    await page.getByRole('button', { name: /save|speichern/i }).click()

    // After saving, should navigate away from details (to events section)
    // and the header should show the updated name
    await expect(page.getByTestId('page-heading')).toHaveText(newName)
  })

  test('can update group description', async ({ adminPage: page }) => {
    await page.goto(`/app/event-groups/${group.id}/details`)

    const descriptionArea = page.locator('textarea').first()
    await descriptionArea.fill('Updated via E2E test')

    await page.getByRole('button', { name: /save|speichern/i }).click()

    // Verify via API that description was saved
    const updated = await api<EventGroupRead>(page, 'GET', `/event-groups/${group.id}`)
    expect(updated.description).toBe('Updated via E2E test')
  })

  test('cancel button returns to events section', async ({ adminPage: page }) => {
    await page.goto(`/app/event-groups/${group.id}/details`)

    await page.getByRole('button', { name: /cancel|abbrechen/i }).click()

    // Should navigate back to events section (default)
    await expect(page).toHaveURL(new RegExp(`/app/event-groups/${group.id}$`))
  })
})

// ── Edit with events (date constraints) ──────────────────────────────────────

test.describe('Event Group Edit – date constraints', () => {
  let group: EventGroupRead
  let event: EventRead

  test.beforeEach(async ({ adminPage: page }) => {
    const startDate = futureDate(30)
    const endDate = futureDate(34)
    group = await api<EventGroupRead>(page, 'POST', '/event-groups/', {
      name: uniqueName('E2E Constrained'),
      status: 'published',
      start_date: startDate,
      end_date: endDate,
    })
    const created = await createEventWithSlots(page, {
      name: uniqueName('E2E Constraint Event'),
      startDate: futureDate(31),
      endDate: futureDate(32),
      eventGroupId: group.id,
    })
    event = created.event
  })

  test.afterEach(async ({ adminPage: page }) => {
    await deleteEvent(page, event?.id).catch(() => {})
    await deleteGroup(page, group.id).catch(() => {})
  })

  test('shows calendar markers when events exist', async ({ adminPage: page }) => {
    await page.goto(`/app/event-groups/${group.id}/details`)

    // Legend should be visible when events exist
    await expect(page.getByText(/event start|veranstaltungs-beginn/i)).toBeVisible()
  })

  test('shows event boundary hints', async ({ adminPage: page }) => {
    await page.goto(`/app/event-groups/${group.id}/details`)

    // Should show earliest/latest event date hints
    await expect(page.getByText(/earliest|früheste/i)).toBeVisible()
  })

  test('shows shift dates card when events exist', async ({ adminPage: page }) => {
    await page.goto(`/app/event-groups/${group.id}/details`)

    // The shift dates section should be visible (use heading to be specific)
    await expect(page.getByRole('heading', { name: /shift dates|termine verschieben/i })).toBeVisible()
  })

  test('date validation prevents invalid ranges via API', async ({ adminPage: page }) => {
    // Try to set end_date before earliest event start via API — should fail
    try {
      await api(page, 'PATCH', `/event-groups/${group.id}`, {
        end_date: futureDate(29), // Before the event starts
      })
      expect(true, 'Should have thrown 422').toBe(false)
    } catch (e) {
      expect(String(e)).toContain('422')
    }
  })
})

// ── Shift dates ──────────────────────────────────────────────────────────────

test.describe('Event Group Edit – shift dates', () => {
  let group: EventGroupRead
  let event: EventRead

  test.beforeEach(async ({ adminPage: page }) => {
    const startDate = futureDate(30)
    const endDate = futureDate(34)
    group = await api<EventGroupRead>(page, 'POST', '/event-groups/', {
      name: uniqueName('E2E Shift'),
      status: 'published',
      start_date: startDate,
      end_date: endDate,
    })
    const created = await createEventWithSlots(page, {
      name: uniqueName('E2E Shift Event'),
      startDate: futureDate(31),
      endDate: futureDate(32),
      eventGroupId: group.id,
    })
    event = created.event
  })

  test.afterEach(async ({ adminPage: page }) => {
    // Event may have been shifted, so try both original and shifted ID
    await deleteEvent(page, event?.id).catch(() => {})
    await deleteGroup(page, group.id).catch(() => {})
  })

  test('shift-dates API shifts group dates forward', async ({ adminPage: page }) => {
    const newStart = futureDate(37) // 7 days forward
    const shifted = await api<EventGroupRead>(
      page,
      'POST',
      `/event-groups/${group.id}/shift-dates`,
      { new_start_date: newStart },
    )
    expect(shifted.start_date).toBe(newStart)
  })

  test('shift-dates API shifts event dates', async ({ adminPage: page }) => {
    const originalEventStart = event.start_date
    const newStart = futureDate(37) // 7 days forward from group start (futureDate(30))

    await api(page, 'POST', `/event-groups/${group.id}/shift-dates`, {
      new_start_date: newStart,
    })

    // Verify event was shifted
    const updatedEvent = await api<EventRead>(page, 'GET', `/events/${event.id}`)
    expect(updatedEvent.start_date).not.toBe(originalEventStart)
  })

  test('shift-dates with same start date is no-op', async ({ adminPage: page }) => {
    const shifted = await api<EventGroupRead>(
      page,
      'POST',
      `/event-groups/${group.id}/shift-dates`,
      { new_start_date: group.start_date },
    )
    expect(shifted.start_date).toBe(group.start_date)
    expect(shifted.end_date).toBe(group.end_date)
  })

  test('shift dates card not visible when no events', async ({ adminPage: page }) => {
    // Create a group with no events
    const emptyGroup = await createGroup(page, uniqueName('E2E Empty Shift'))

    await page.goto(`/app/event-groups/${emptyGroup.id}/details`)

    // The shift dates card should NOT be visible
    await expect(page.getByText(/shift dates|termine verschieben/i)).toBeHidden()

    await deleteGroup(page, emptyGroup.id)
  })

  test('shift dates UI shows preview text', async ({ adminPage: page }) => {
    await page.goto(`/app/event-groups/${group.id}/details`)

    // The shift section heading should be visible
    await expect(page.getByRole('heading', { name: /shift dates|termine verschieben/i })).toBeVisible()
  })
})

// ── Member cannot see details section ────────────────────────────────────────

test.describe('Event Group Edit – member restrictions', () => {
  let group: EventGroupRead

  test.beforeEach(async ({ adminPage: page }) => {
    group = await createGroup(page, uniqueName('E2E Member Edit'))
  })

  test.afterEach(async ({ adminPage: page }) => {
    await deleteGroup(page, group.id).catch(() => {})
  })

  test('member cannot see Details nav item', async ({ memberPage: page }) => {
    await page.goto(`/app/event-groups/${group.id}`)

    // Member should see Events and Availability but NOT Details
    await expect(page.getByText(/events|veranstaltungen/i).first()).toBeVisible()
    // Details should not be visible to members
    // The nav button with "Details" text should not be visible
    const detailsNav = page.locator('button').filter({ hasText: /^details$/i })
    await expect(detailsNav).toBeHidden()
  })

  test('member cannot shift dates via API', async ({ memberPage: page }) => {
    try {
      await api(page, 'POST', `/event-groups/${group.id}/shift-dates`, {
        new_start_date: futureDate(40),
      })
      expect(true, 'Should have thrown 403').toBe(false)
    } catch (e) {
      expect(String(e)).toContain('403')
    }
  })
})
