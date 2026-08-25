/**
 * The volunteer's track: find a shift, take it, say when you are free, and see
 * what you have signed up for.
 *
 * Every selector here is a `data-testid` that exists in the app today — the
 * tour is not allowed to invent anchors, because a step whose anchor never
 * turns up degrades to a centred popover with no highlight (see
 * `tour/engine.ts`) and the visitor is quietly shown a worse first impression.
 */
import { useTaskFiltersStore } from '@/stores/eventFilters'

import { defineTrack } from '@/tour/types'

/** The rows and shift chips this track points at only exist in the list view. */
const TASK_LIST = '[data-testid="task-list"]'
const SHIFT_CHIP = '[data-testid^="shift-chip-"]'
const SHIFT_DIALOG = '[data-testid="dialog-shift-detail"]'

/**
 * `page-heading` is on the pre-auth shell, the auth shell and every routed view
 * at once, so it is only unambiguous when scoped to the content area.
 *
 * Note that `main-content` is *not* the post-auth shell's alone — `PreAuthLayout`
 * marks its `<main>` the same way, so this selector matches the landing page's
 * hero just as happily. What keeps the two apart is that only one shell is ever
 * mounted, which holds everywhere except in the single flush between a route
 * changing and `RouterView` catching up. `tour/engine.ts` waits that flush out
 * before it reads the DOM; without it, the first step of a demo anchored to the
 * landing page it had just left.
 */
const PAGE_HEADING = '[data-testid="main-content"] [data-testid="page-heading"]'

export const helperTrack = defineTrack('helper', [
  {
    id: 'welcome',
    route: 'home',
    element: PAGE_HEADING,
    side: 'bottom',
  },
  {
    id: 'navigation',
    route: 'home',
    // Below `md` the sidebar is a Sheet: its links are not in the DOM until the
    // toggle is pressed, and an existing `router.afterEach` closes it again on
    // the next navigation. The bottom nav is the same destination and is always
    // there, so the mobile half of this step points at that instead of trying
    // to hold a drawer open.
    element: '[data-testid="sidebar-link-tasks"]',
    mobileElement: '[data-testid="mobile-nav-tasks"]',
    side: 'right',
  },
  {
    id: 'taskList',
    route: 'tasks',
    element: TASK_LIST,
    waitFor: PAGE_HEADING,
    side: 'top',
    before: () => {
      // The view mode is remembered per browser, and the two steps after this
      // one point at shift chips, which only the list view draws. A visitor who
      // last left the calendar open would otherwise be walked through three
      // steps that all miss.
      useTaskFiltersStore().viewMode = 'list'
    },
  },
  {
    id: 'shiftChips',
    route: 'tasks',
    element: SHIFT_CHIP,
    waitFor: TASK_LIST,
    side: 'right',
  },
  {
    id: 'bookShift',
    route: 'tasks',
    element: '[data-testid="btn-book-shift"]',
    waitFor: SHIFT_DIALOG,
    inOverlay: true,
    side: 'top',
    before: async ({ waitFor }) => {
      // Idempotent on purpose: the engine re-runs `before()` whenever the view
      // remounts underneath the tour, and clicking a chip that is already
      // behind an open dialog would do nothing useful.
      if (document.querySelector(SHIFT_DIALOG)) return
      const chip = await waitFor(SHIFT_CHIP)
      chip?.click()
      await waitFor(SHIFT_DIALOG)
    },
  },
  {
    id: 'availability',
    route: 'availability',
    element: '[data-testid="section-my-availability"]',
    waitFor: PAGE_HEADING,
    side: 'top',
  },
  {
    id: 'availabilityModes',
    route: 'availability',
    // Rendered twice — a card row from `sm` up and a segmented control below it
    // — under the same testid, with the hidden twin still measurable at zero
    // size. The engine takes the first match that has a real box, so one
    // selector covers both.
    element: '[data-testid="availability-type-time_range"]',
    waitFor: '[data-testid="section-my-availability"]',
    side: 'bottom',
  },
  {
    id: 'myBookings',
    route: 'my-bookings',
    element: '[data-testid="booking-card"]',
    waitFor: PAGE_HEADING,
    side: 'top',
  },
  {
    id: 'finish',
    route: 'home',
    element: '[data-testid="dashboard-quick-actions"]',
    side: 'top',
  },
])
