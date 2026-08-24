/**
 * Wiring the guided tour into the running app.
 *
 * Three jobs, all of them about *when* a tour starts and restarts:
 *
 *  1. `router.afterEach` hands every settled navigation to the engine, which is
 *     what makes a step survive a route change, a view remount and a full page
 *     reload — the step index itself is in `sessionStorage`, so a reload
 *     arrives here with the tour already restored and only needs re-drawing.
 *  2. A `wirksam:restart-tour` window event, dispatched by the demo banner,
 *     starts a named track from the beginning.
 *  3. First arrival at the dashboard in a demo session starts the matching
 *     track by itself, exactly once per sitting.
 *
 * Installed from `main.ts` after Pinia, the router and i18n, and before mount.
 * Nothing here touches a store at install time: `stores/auth.ts` calls
 * `useI18n()` in its setup, which throws outside a component, so it may only be
 * reached from a handler that runs after `App.vue` has already created it.
 */
import type { RouteLocationNormalized, Router } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { useTourStore } from '@/stores/tour'

import { useChangelogStatus } from '@/composables/useChangelogStatus'

import { type TourController, createTourController } from '@/tour/engine'
import type { TourTrackId } from '@/tour/types'

/**
 * Dispatched on `window` by the demo banner's "show me around" control, as
 * `new CustomEvent(TOUR_RESTART_EVENT, { detail: { track: 'helper' } })`.
 */
export const TOUR_RESTART_EVENT = 'wirksam:restart-tour'

/**
 * Remembers that the automatic start has already happened. Per *sitting*, like
 * the tour state itself — a visitor who reloads mid-demo should not be sent
 * back to step one, and one who opens the demo again tomorrow should be
 * welcomed again.
 */
const AUTOSTART_KEY = 'wirksam:tour:autostarted'

/** The screen a demo session lands on, and the only place a tour starts itself. */
const DASHBOARD_ROUTE = 'home'

function hasAutoStarted(): boolean {
  try {
    return sessionStorage.getItem(AUTOSTART_KEY) === '1'
  } catch {
    // A browser that refuses storage would restart the tour on every
    // navigation, which is far worse than never starting it automatically.
    return true
  }
}

function markAutoStarted(): void {
  try {
    sessionStorage.setItem(AUTOSTART_KEY, '1')
  } catch {
    // Nothing to do: `hasAutoStarted()` answers `true` in the same conditions.
  }
}

/**
 * Keep the "What's New" dialog off a running tour.
 *
 * `PostAuthLayout` opens it from `onMounted` the first time a browser sees a
 * new release, and a modal that takes focus and dims the page is the one thing
 * that can break a tour outright. The lever is the same one
 * `testing/fake-session.ts` pulls for the same reason — the
 * `wirksam-last-seen-changelog` key — reached through `markAsSeen()` so that it
 * writes the *real* latest version rather than an unreachable one: a visitor
 * who signs up after the demo still gets the dialog for the next release.
 */
function suppressWhatsNew(): void {
  useChangelogStatus().markAsSeen()
}

function beginTour(controller: TourController, track: TourTrackId): void {
  suppressWhatsNew()
  controller.start(track)
}

/**
 * Start the track that matches who the demo signed the visitor in as, once.
 *
 * The role is read off the profile rather than remembered from the request that
 * created the session, so it survives a reload: a demo `manager` owns their
 * seeded event, a demo `helper` is only a member of it.
 */
function maybeAutoStart(controller: TourController, to: RouteLocationNormalized): boolean {
  if (to.name !== DASHBOARD_ROUTE) return false
  if (hasAutoStarted()) return false
  // A tour restored from `sessionStorage` is mid-flight; starting a second one
  // over the top of it would throw away the visitor's place.
  if (useTourStore().status === 'running') return false

  const auth = useAuthStore()
  if (!auth.profile?.is_sandbox) return false

  markAutoStarted()
  beginTour(controller, auth.canManageEvent(auth.selectedEventId) ? 'manager' : 'helper')
  return true
}

export function installTour(router: Router): void {
  const controller = createTourController(router)

  window.addEventListener(TOUR_RESTART_EVENT, (event) => {
    const detail = (event as CustomEvent<{ track?: TourTrackId }>).detail
    // Anything that is not the manager track is the helper track: the volunteer
    // path is the one that makes sense to somebody who cannot manage anything.
    beginTour(controller, detail?.track === 'manager' ? 'manager' : 'helper')
  })

  router.afterEach((to) => {
    // An automatic start already renders its own first step, so letting the
    // route handler run as well would only race it.
    if (maybeAutoStart(controller, to)) return
    controller.handleRouteChange(to)
  })
}
