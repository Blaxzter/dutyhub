/**
 * The bottom-drawer half of `ResponsiveDialog`, at a phone viewport.
 *
 * Every other project in `playwright.config.ts` runs at 1280x720, so all of
 * them render the `Dialog` branch and none of them would notice the drawer
 * breaking. This file is the only place `ResponsiveDialogContent` takes its
 * `isMobile` path, so it asserts the layout *contract* rather than the content
 * — which shell rendered, that the body is reka's swipe-aware viewport, and
 * that the body is the only thing that scrolls. Those are the properties a
 * refactor silently breaks; the wording and the spacing are covered upstairs by
 * `authenticated/shift-detail.spec.ts` and would only make this file brittle.
 *
 * The drawer sizes itself to its content and caps at 80vh, so the scroll test
 * has to *earn* an overflow by giving the shift a long description first. A
 * test that asserted "the body scrolls" against content that happens to fit
 * would pass no matter what the CSS said.
 */
import type { Page } from '@playwright/test'

import { expect, test } from '../../fixtures.js'
import {
  type ShiftRead,
  type TaskWithShifts,
  api,
  bookShift,
  createTaskWithShifts,
  deleteTask,
  listShifts,
  uniqueName,
} from '../../helpers/api.js'

let created: TaskWithShifts
let shifts: ShiftRead[]
let taskName: string

test.beforeEach(async ({ adminPage: page }) => {
  taskName = uniqueName('E2E Mobile Drawer Task')
  created = await createTaskWithShifts(page, {
    name: taskName,
    location: 'Side Entrance',
    category: 'Welcome',
    status: 'published',
    peoplePerShift: 2,
  })
  shifts = await listShifts(page, created.task.id)
})

test.afterEach(async ({ adminPage: page }) => {
  await deleteTask(page, created.task.id).catch(() => {})
})

/** Same route pinning as the desktop spec: the query beats remembered state. */
async function openShiftChip(page: Page, shiftId: string) {
  await page.goto(`/app/tasks?view=list&search=${encodeURIComponent(taskName)}`)
  const chip = page.getByTestId(`shift-chip-${shiftId}`)
  await expect(chip).toBeVisible()
  await chip.click()
}

const drawer = (page: Page) => page.getByTestId('dialog-shift-detail')

/**
 * Wait out the slide-up before measuring anything.
 *
 * The sheet starts below the fold and animates in over 500ms, so a `boundingBox`
 * taken the moment it appears reports it hanging off the bottom of the screen.
 * Polling on the resting position is the whole wait — once the bottom edge and
 * the viewport agree, the transform has finished.
 */
async function settled(page: Page, locator = drawer(page)) {
  await expect
    .poll(async () => {
      const box = await locator.boundingBox()
      return box ? Math.round(box.y + box.height) : null
    })
    .toBe(page.viewportSize()!.height)
}

test.describe('Shift details – as a bottom sheet', () => {
  test('the viewport really is a phone', async ({ adminPage: page }) => {
    // `adminPage` builds its own browser context, so if it ever stops passing
    // the project's `contextOptions` through, every assertion below would go on
    // passing against the desktop dialog. This one fails loudly instead.
    const size = page.viewportSize()
    expect(size?.width).toBeLessThan(768)
  })

  test('a shift opens as a drawer anchored to the bottom edge', async ({ adminPage: page }) => {
    await openShiftChip(page, shifts[0].id)

    // `data-slot` is set by the shadcn wrapper each branch renders, so it names
    // the shell without depending on any class the styling might rename.
    await expect(drawer(page)).toHaveAttribute('data-slot', 'drawer-content')
    await settled(page)

    // Full-bleed and flush with the bottom edge — the two things that make it a
    // sheet rather than a centred modal that happens to be near the bottom.
    const box = (await drawer(page).boundingBox())!
    const viewport = page.viewportSize()!
    expect(Math.round(box.x)).toBe(0)
    expect(Math.round(box.width)).toBe(viewport.width)
  })

  test('the body is the swipe-aware viewport, not a plain scroller', async ({
    adminPage: page,
  }) => {
    await openShiftChip(page, shifts[0].id)

    // Without `DrawerViewport`, a drag that starts inside the list dismisses
    // the sheet instead of scrolling it. The attribute is reka's own marker.
    await expect(drawer(page).locator('[data-slot="responsive-dialog-body"]')).toHaveAttribute(
      'data-drawer-viewport',
      /.*/,
    )
  })

  test('only the body scrolls; the footer stays on the bottom edge', async ({
    adminPage: page,
  }) => {
    // Long enough to overflow 80vh on any phone the project might be pointed at.
    await api(page, 'PATCH', `/shifts/${shifts[0].id}`, {
      description: Array.from(
        { length: 40 },
        (_, i) => `Line ${i + 1}: what to bring, where to stand, who to ask.`,
      ).join('\n'),
    })

    await openShiftChip(page, shifts[0].id)
    await settled(page)

    const body = drawer(page).locator('[data-slot="responsive-dialog-body"]')
    const footer = drawer(page).locator('[data-slot="responsive-dialog-footer"]')

    const overflows = await body.evaluate((el) => el.scrollHeight > el.clientHeight + 1)
    expect(overflows, 'the description should have made the body overflow').toBe(true)

    const footerBefore = (await footer.boundingBox())!
    await body.evaluate((el) => el.scrollTo(0, el.scrollHeight))
    await expect.poll(() => body.evaluate((el) => el.scrollTop)).toBeGreaterThan(0)

    // The footer holds the only way to take the shift, so it has to survive
    // the body being scrolled to the end.
    const footerAfter = (await footer.boundingBox())!
    expect(Math.round(footerAfter.y)).toBe(Math.round(footerBefore.y))
    expect(Math.round(footerAfter.y + footerAfter.height)).toBe(page.viewportSize()!.height)
    await expect(page.getByTestId('btn-book-shift')).toBeVisible()
  })

  test('booking from the drawer takes the shift', async ({ adminPage: page }) => {
    await openShiftChip(page, shifts[0].id)
    await page.getByTestId('btn-book-shift').click()

    await expect(drawer(page)).toBeHidden()
    await expect(page.getByTestId(`shift-chip-${shifts[0].id}`)).toContainText('1/2')
  })
})

test.describe('Confirm prompts – as an action sheet', () => {
  test('a destructive confirm opens over the drawer and can be dismissed', async ({
    adminPage: page,
  }) => {
    const booking = await bookShift(page, shifts[0].id)
    try {
      await openShiftChip(page, shifts[0].id)
      await page.getByTestId('btn-cancel-shift-booking').click()

      // `GlobalDialog` is mounted at the app root, so this is a second sheet
      // opening while the first is still up — the case where two overlays and
      // two focus traps could fight.
      const confirm = page.getByRole('dialog').filter({ hasText: 'Confirm Action' })
      await expect(confirm).toBeVisible()
      await expect(confirm).toHaveAttribute('data-slot', 'drawer-content')
      await settled(page, confirm)
      await expect(page.getByTestId('btn-dialog-confirm')).toBeVisible()

      // Backing out of the confirm must leave the booking alone.
      await page.getByTestId('btn-dialog-cancel').click()
      await expect(confirm).toBeHidden()
      await expect(page.getByTestId('btn-cancel-shift-booking')).toBeVisible()
    } finally {
      await api(page, 'DELETE', `/bookings/${booking.id}`).catch(() => {})
    }
  })
})
