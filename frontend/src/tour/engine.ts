/**
 * The bit that draws a tour, and the reason it is written the way it is.
 *
 * ── Why nothing is cached ────────────────────────────────────────────────────
 * `PostAuthLayout` keys its `<RouterView>` on the full path, so a view is torn
 * down and rebuilt on every navigation — and, in `TasksView` and
 * `ReportingView`, on every filter change too, because both mirror their state
 * into the query string with `router.replace`. Any element reference held
 * across one of those is a detached node, and driver.js will cheerfully cut a
 * hole in the overlay around a rectangle that is no longer on screen. So the
 * anchor is re-queried from scratch for every render, and the driver instance
 * is destroyed before every navigation rather than being asked to follow.
 *
 * The durable half — track, step index, status — lives in `stores/tour.ts` and
 * in `sessionStorage`. This module holds nothing that matters.
 *
 * ── What happens when an anchor never appears ────────────────────────────────
 * The step still runs, as a **centred popover with no highlight**. It does not
 * skip forward: the copy explains what a screen is *for* rather than what a
 * button is called, so it still reads correctly with nothing pointed at, and
 * skipping would make the "step 4 of 9" counter lie about a tour that is one
 * anchor short. `waitForElement` gives up after `ANCHOR_TIMEOUT_MS` and the
 * tour carries on either way.
 *
 * ── Why Next goes dead between steps ─────────────────────────────────────────
 * Preparing a step is not instant — it can push a route, run a `before()` hook
 * that clicks a dialog open, and then wait for an anchor inside it. The popover
 * the visitor is looking at throughout still belongs to the step *before*, and
 * its Next button is live. So `preparing` holds from the first line of `show()`
 * to the last, `advance()` and `retreat()` drop anything that arrives while it
 * is set, and `syncNavigationButtons` greys the two buttons out so the refusal
 * is visible rather than a click that vanished. Only the close button stays
 * live: whatever else is going on, the visitor can leave.
 */
import { nextTick } from 'vue'

import { type DriveStep, type Driver, driver } from 'driver.js'
import type { RouteLocationNormalized, Router } from 'vue-router'

import { useTourStore } from '@/stores/tour'

import i18n from '@/locales/i18n'
import type { TourStep, TourTrackId } from '@/tour/types'

/**
 * Tailwind's `md`. The responsive twins this has to choose between switch at
 * `sm` or `xl` rather than `md`, which is exactly why the choice is a
 * *preference* and not a verdict — whichever selector wins, the engine still
 * takes the first match with a real box, and falls back to the other one.
 */
const DESKTOP_MEDIA_QUERY = '(min-width: 768px)'

/**
 * Long enough to cover a cold route chunk plus its first API call — the tour
 * can be resumed by a full page reload, where the popover is asked for before
 * the view has even been fetched.
 */
const ANCHOR_TIMEOUT_MS = 6000

/** The one class every popover carries, so `index.css` can theme it. */
const POPOVER_CLASS = 'wirksam-tour'

const t = (key: string, named?: Record<string, unknown>) =>
  named ? i18n.global.t(key, named) : i18n.global.t(key)

/**
 * First match with a non-zero box.
 *
 * Several `data-testid`s appear twice, once for each breakpoint, and the hidden
 * twin is still in the DOM — `display:none` gives it a zero-size rect rather
 * than removing it. Driver.js does not check, and would happily draw a 0×0
 * highlight somewhere in the top-left corner.
 */
export function firstVisible(selector: string): HTMLElement | null {
  for (const element of document.querySelectorAll<HTMLElement>(selector)) {
    const rect = element.getBoundingClientRect()
    if (rect.width > 0 && rect.height > 0) return element
  }
  return null
}

/**
 * Wait for `selector` to match something visible; resolve `null` on timeout.
 *
 * Two watchers, because they catch different things. The MutationObserver
 * covers the common case — a view mounting, a dialog teleporting itself into
 * `body`. The animation frame covers the case it cannot see: an element that
 * was in the DOM all along and only *became* measurable, which is what an
 * accordion panel finishing its height transition looks like.
 *
 * Never rejects. A tour that throws because a button was slow is worse than a
 * tour that shrugs.
 */
export function waitForElement(
  selector: string,
  { timeout = ANCHOR_TIMEOUT_MS }: { timeout?: number } = {},
): Promise<HTMLElement | null> {
  const immediate = firstVisible(selector)
  if (immediate) return Promise.resolve(immediate)

  return new Promise((resolve) => {
    let settled = false
    let frame = 0

    const settle = (element: HTMLElement | null) => {
      if (settled) return
      settled = true
      observer.disconnect()
      window.clearTimeout(timer)
      window.cancelAnimationFrame(frame)
      resolve(element)
    }

    const check = () => {
      const found = firstVisible(selector)
      if (found) settle(found)
    }

    const poll = () => {
      if (settled) return
      check()
      frame = window.requestAnimationFrame(poll)
    }

    const observer = new MutationObserver(check)
    const timer = window.setTimeout(() => settle(null), timeout)

    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
    })
    frame = window.requestAnimationFrame(poll)
  })
}

/**
 * The step's two candidate selectors, preferred one first.
 *
 * Returning both rather than picking one is deliberate: `matchMedia` answers
 * "is this a wide window", which is a good guess at which twin is showing and
 * not a promise — `availability-type-*` swaps at `sm` and `btn-create-task` at
 * `xl`. Trying the other one costs a `querySelectorAll`.
 */
function anchorSelectors(step: TourStep): string[] {
  const desktop = step.element ?? step.mobileElement
  const mobile = step.mobileElement ?? step.element
  if (!desktop || !mobile) return []

  const wantsDesktop = window.matchMedia(DESKTOP_MEDIA_QUERY).matches
  const preferred = wantsDesktop ? desktop : mobile
  const other = wantsDesktop ? mobile : desktop
  return preferred === other ? [preferred] : [preferred, other]
}

async function resolveAnchor(step: TourStep): Promise<HTMLElement | null> {
  if (step.waitFor) await waitForElement(step.waitFor)

  const selectors = anchorSelectors(step)
  if (selectors.length === 0) return null

  // Only the preferred selector is worth waiting on. The fallback is the twin
  // this viewport is not showing, so if the preferred one never turned up the
  // fallback is a synchronous long shot, not a second six-second wait.
  const found = await waitForElement(selectors[0])
  if (found) return found
  return selectors[1] ? firstVisible(selectors[1]) : null
}

export interface TourController {
  start: (track: TourTrackId) => void
  stop: () => void
  /**
   * Re-show, advance or hide the tour after the router has settled.
   *
   * Takes only the destination on purpose: every decision below is about where
   * the browser has landed, and reading `from` would invite the fullPath
   * comparison that this module exists to avoid.
   */
  handleRouteChange: (to: RouteLocationNormalized) => void
}

export function createTourController(router: Router): TourController {
  let instance: Driver | null = null
  /**
   * Route the live instance was built against. A driver that animates from an
   * element the previous view took with it draws the overlay from a phantom
   * rectangle, so instances never cross a route boundary.
   */
  let instanceRoute: string | null = null
  /**
   * Bumped by every render. An `await` that comes back to find it has been
   * superseded — because `afterEach` started a newer render while the old one
   * was waiting on a navigation or an anchor — drops what it was doing.
   */
  let renderToken = 0
  /**
   * Set for as long as a step is being *prepared* — navigating, running its
   * `before()` hook, waiting for the anchor to turn up.
   *
   * The popover on screen during all of that still belongs to the step before
   * it, and its Next button is a live control pointing at `advance()`. A step
   * whose `before()` has to click something open takes a second or two to
   * arrive, which is easily long enough for a second click, and each one walks
   * the store forward again — so the step being prepared is skipped without
   * ever having been shown. `syncNavigationButtons` greys the buttons out to
   * say the tour is busy; this flag is what makes that true rather than
   * cosmetic, because a click can still land in the frame before the styling
   * does, and Enter on a focused button never touches the styling at all.
   */
  let preparing = false

  const routeName = () => String(router.currentRoute.value.name ?? '')

  /**
   * Put the live popover's Next and Back buttons into the right state.
   *
   * Reaching into rendered DOM rather than going through driver's
   * `disableButtons`, because that option is only read when a popover is
   * *built*: the one that needs disabling here was built for the previous step
   * and driver has no idea a newer one is on its way. The class is driver's
   * own, so a button disabled from here looks exactly like the Back button
   * driver disables itself on step one.
   *
   * The close button is deliberately left alone. Whatever else is happening,
   * the visitor can always get out.
   */
  function syncNavigationButtons() {
    const popover = document.querySelector('.driver-popover')
    if (!popover) return

    const store = useTourStore()
    const states: [selector: string, disabled: boolean][] = [
      ['.driver-popover-next-btn', preparing],
      ['.driver-popover-prev-btn', preparing || store.isFirstStep],
    ]

    for (const [selector, disabled] of states) {
      const button = popover.querySelector<HTMLButtonElement>(selector)
      if (!button) continue
      button.disabled = disabled
      button.classList.toggle('driver-popover-btn-disabled', disabled)
      button.setAttribute('aria-disabled', String(disabled))
    }
  }

  function setPreparing(value: boolean) {
    if (preparing === value) return
    preparing = value
    syncNavigationButtons()
  }

  function teardown() {
    if (!instance) return
    const dying = instance
    instance = null
    instanceRoute = null
    // `destroy()` deliberately does not run driver's `onDestroyStarted`, so
    // tearing down for a navigation cannot be mistaken for the visitor
    // dismissing the tour.
    dying.destroy()
  }

  /**
   * Close the dialog the current step opened, when the tour ends inside one.
   *
   * An `inOverlay` step reaches its anchor by opening a modal, and reka-ui
   * holds `pointer-events: none` on `<body>` for as long as one is up — driver's
   * own stylesheet re-enables it for the popover, which is the only reason the
   * step works at all. End the tour there and the popover goes with it, leaving
   * a visitor behind a dialog they never opened themselves and every control
   * outside it inert. The demo banner is one of those controls, so "restart the
   * tour" did nothing: the click never reached the button.
   *
   * Escape is the dialog's own documented way out, so this closes it through
   * the component rather than reaching past it into somebody's `v-model`.
   */
  function dismissStepOverlay() {
    if (!useTourStore().currentStep?.inOverlay) return
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
  }

  function stop() {
    // Before the store forgets which step it was on.
    dismissStepOverlay()
    useTourStore().stop()
    teardown()
  }

  function finish() {
    dismissStepOverlay()
    useTourStore().finish()
    teardown()
  }

  async function advance() {
    // Dropped, not queued: the visitor pressed Next at a popover that is on its
    // way out, so the only honest reading of the click is the one they can
    // already see happening. Queueing it would turn an impatient double-click
    // into two steps, which is the thing this exists to stop.
    if (preparing) return

    const store = useTourStore()
    if (store.isLastStep) {
      finish()
      return
    }
    store.next()
    await show({ navigate: true })
  }

  async function retreat() {
    if (preparing) return

    const store = useTourStore()
    if (store.isFirstStep) return
    store.previous()
    await show({ navigate: true })
  }

  /**
   * Whether the step's own query keys are already on the URL.
   *
   * Only the step's keys, never the whole query: `TasksView` and
   * `ReportingView` add their filters to it, and demanding an exact match would
   * send the tour navigating after every keystroke in a search box.
   */
  function queryMatches(step: TourStep): boolean {
    if (!step.query) return true
    const current = router.currentRoute.value.query
    return Object.entries(step.query).every(([key, value]) => current[key] === value)
  }

  async function show({ navigate }: { navigate: boolean }): Promise<void> {
    const token = ++renderToken
    setPreparing(true)
    try {
      await prepare(token, navigate)
    } finally {
      // Only the newest render may put the buttons back. An older one returning
      // from an `await` it was superseded during would otherwise re-enable Next
      // in the middle of the render that overtook it — which is the same open
      // door, one layer down.
      if (token === renderToken) setPreparing(false)
    }
  }

  async function prepare(token: number, navigate: boolean): Promise<void> {
    const store = useTourStore()
    const step = store.currentStep

    if (!store.isRunning || !step) {
      teardown()
      return
    }

    const onRoute = !step.route || routeName() === step.route

    if (!onRoute) {
      // Never leave an overlay pointing at a view that is about to be unmounted.
      teardown()
      if (!navigate) return
      await router.push({ name: step.route, query: step.query }).catch(() => {})
      // The route *name* changed, so `afterEach` has already started a fresher
      // render than this one and there is nothing left to do here.
      if (token !== renderToken) return
      // …unless a guard sent the navigation somewhere else entirely — the
      // selected-event gate does exactly that to an account without one. Better
      // no popover than the step's copy pinned over a page it never meant.
      if (routeName() !== step.route) return
    } else if (!queryMatches(step) && navigate) {
      await router
        .replace({
          name: step.route,
          query: { ...router.currentRoute.value.query, ...step.query },
        })
        .catch(() => {})
      if (token !== renderToken) return
    }

    // Let the router's own render land before anything reads the DOM.
    //
    // `afterEach` runs the moment `currentRoute` changes, which is one Vue
    // flush *before* `RouterView` swaps its component — so the view being left
    // behind is still mounted, still visible, and still matches selectors that
    // were only ever meant for the one arriving. `firstVisible` rejects a
    // detached node, because its box is 0×0, but this one is not detached yet:
    // it measures fine, wins the anchor, and is unmounted a microsecond later,
    // leaving driver drawing a popover against a rectangle that no longer
    // exists. Every screen the tour visits carries a `page-heading` inside a
    // `main-content` — the landing page included — so the very first step of a
    // demo was reliably anchoring to the hero it had just navigated away from.
    await nextTick()
    if (token !== renderToken) return

    if (step.before) {
      try {
        await step.before({ waitFor: waitForElement })
      } catch {
        // A hook that could not open what it wanted leaves the step to fall
        // back to a centred popover, which is a worse step and not a dead tour.
      }
      if (token !== renderToken) return
    }

    const element = await resolveAnchor(step)
    if (token !== renderToken) return

    render(step, element)
  }

  function render(step: TourStep, element: HTMLElement | null) {
    const store = useTourStore()
    // The close button stays live while a step is being prepared, so the tour
    // can be dismissed halfway through resolving one. Without this, the render
    // that preparation was working towards would arrive a second later and put
    // the popover back on a visitor who had just closed it.
    if (!store.isRunning) return

    const route = routeName()

    if (instance && instanceRoute !== route) teardown()
    if (!instance) {
      instance = driver({
        animate: true,
        allowClose: true,
        overlayColor: '#000',
        overlayOpacity: 0.6,
        stagePadding: 8,
        stageRadius: 10,
        smoothScroll: true,
        popoverClass: POPOVER_CLASS,
        // Escape and a click on the backdrop both land here. `destroy()` does
        // not, which is what keeps a navigation from reading as a dismissal.
        onDestroyStarted: () => stop(),
      })
      instanceRoute = route
    }

    const driveStep: DriveStep = {
      popover: {
        title: t(step.titleKey),
        description: t(step.bodyKey),
        side: step.side ?? 'bottom',
        align: step.align ?? 'start',
        showButtons: ['next', 'previous', 'close'],
        disableButtons: store.isFirstStep ? ['previous'] : [],
        showProgress: true,
        // Rendered here rather than through driver's own `{{current}}`
        // substitution: the step index belongs to the store, and driver is
        // driven one step at a time and has no idea how many there are.
        progressText: t('tour.common.progress', {
          current: store.stepIndex + 1,
          total: store.stepCount,
        }),
        nextBtnText: store.isLastStep ? t('tour.common.done') : t('tour.common.next'),
        prevBtnText: t('tour.common.back'),
        popoverClass: POPOVER_CLASS,
        onNextClick: () => void advance(),
        onPrevClick: () => void retreat(),
        onCloseClick: () => stop(),
        onPopoverRender: (popover) => {
          const skipLabel = t('tour.common.skip')
          popover.closeButton.setAttribute('aria-label', skipLabel)
          popover.closeButton.title = skipLabel
          if (step.inOverlay && element) settleOverlayFocus(element)
        },
      },
    }

    // Left unset for a missing anchor: driver falls back to an invisible
    // element pinned to the middle of the viewport, which is exactly the
    // centred, un-highlighted popover that case wants.
    if (element) driveStep.element = element

    instance.highlight(driveStep)
  }

  function handleRouteChange(to: RouteLocationNormalized) {
    const store = useTourStore()
    if (!store.isRunning) return

    const step = store.currentStep
    if (!step) return

    const target = typeof to.name === 'string' ? to.name : ''

    if (!step.route || target === step.route) {
      // Same route, new URL — a filter mirrored into the query string. The step
      // has not moved, but the view under it has been remounted and the anchor
      // it was pointing at no longer exists, so this has to re-resolve rather
      // than sit still. `navigate: false` guarantees it cannot answer a
      // `replace` with a `push` and start a loop.
      void show({ navigate: false })
      return
    }

    // The visitor did what the step suggested and clicked the highlighted
    // control themselves. Following them is friendlier than making them press
    // Next as well for a page they are already looking at.
    if (store.nextStep?.route === target) {
      store.next()
      void show({ navigate: false })
      return
    }

    // Anywhere else — a sidebar link, the browser's Back button — the tour goes
    // quiet rather than either fighting the navigation or pasting a popover
    // over an unrelated page. It reappears the moment they land back on the
    // step's own screen.
    teardown()
  }

  function start(track: TourTrackId) {
    useTourStore().start(track)
    void show({ navigate: true })
  }

  return { start, stop, handleRouteChange }
}

/**
 * Stop driver.js and a modal's focus trap arguing over the caret.
 *
 * `ShiftDetailDialog` is a reka-ui `Dialog`: teleported to `body`, with a focus
 * scope that pulls focus back into the dialog whenever it lands outside. Driver
 * focuses the first control in its own popover as soon as it renders — the
 * popover is outside the dialog, so the scope takes it back, and if driver were
 * to insist the two would trade it for as long as the step is on screen.
 *
 * Settling focus on the highlighted control instead ends the argument on the
 * first frame, and costs nothing that matters: the control is inside the dialog
 * so the trap is satisfied, driver has already wired `aria-controls` and
 * `aria-describedby` from that control to the popover, and the popover's own
 * buttons stay clickable because driver's stylesheet re-enables pointer events
 * on them regardless of the `pointer-events: none` the modal puts on `body`.
 */
function settleOverlayFocus(element: HTMLElement) {
  window.requestAnimationFrame(() => element.focus({ preventScroll: true }))
}
