/**
 * The organiser's track: describe a job, let wirksam cut it into shifts, watch
 * them fill, manage the people, and read the numbers afterwards.
 *
 * The four `task-create` steps walk the accordion top to bottom without filling
 * anything in. The sections are `AccordionItem`s, which stay in the DOM whether
 * open or closed, so each one is a stable anchor and the visitor can open the
 * one they are curious about while the popover is still pointing at it.
 */
import { defineTrack } from '@/tour/types'

const TASK_LIST = '[data-testid="task-list"]'
const PAGE_HEADING = '[data-testid="main-content"] [data-testid="page-heading"]'

/** People, invitations and join requests all live behind one tab of one route. */
const PEOPLE_TAB = { tab: 'people' }

export const managerTrack = defineTrack('manager', [
  {
    id: 'welcome',
    route: 'home',
    element: PAGE_HEADING,
    side: 'bottom',
  },
  {
    id: 'dashboard',
    route: 'home',
    element: '[data-testid="dashboard-calendar"]',
    side: 'top',
  },
  {
    id: 'tasks',
    route: 'tasks',
    element: TASK_LIST,
    waitFor: PAGE_HEADING,
    side: 'top',
  },
  {
    id: 'createTask',
    route: 'tasks',
    // The desktop button is `max-xl:hidden` and the floating action button is
    // `xl:hidden`; both are in the DOM at every width, and only one of them has
    // a box. Below `md` the engine tries the FAB first, but either selector
    // resolves to whichever is actually visible.
    element: '[data-testid="btn-create-task"]',
    mobileElement: '[data-testid="fab-create-task"]',
    side: 'bottom',
  },
  {
    id: 'taskDetails',
    route: 'task-create',
    element: '[data-testid="section-task-details"]',
    waitFor: PAGE_HEADING,
    side: 'bottom',
  },
  {
    id: 'taskDates',
    route: 'task-create',
    element: '[data-testid="section-task-dates"]',
    side: 'bottom',
  },
  {
    id: 'generateShifts',
    route: 'task-create',
    element: '[data-testid="section-schedule"]',
    side: 'bottom',
  },
  {
    id: 'shiftPreview',
    route: 'task-create',
    element: '[data-testid="section-preview"]',
    side: 'top',
  },
  {
    id: 'staffing',
    route: 'tasks',
    element: '[data-testid="task-row"]',
    waitFor: TASK_LIST,
    side: 'top',
  },
  {
    id: 'members',
    route: 'event-settings',
    query: PEOPLE_TAB,
    element: '[data-testid="section-event-members"]',
    waitFor: PAGE_HEADING,
    side: 'top',
  },
  {
    id: 'invitations',
    route: 'event-settings',
    query: PEOPLE_TAB,
    element: '[data-testid="section-event-invitations"]',
    side: 'top',
  },
  {
    id: 'reporting',
    route: 'reporting',
    element: '[data-testid="section-overview"]',
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
