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
 * anchor short. `waitForElement` gives up after its timeout — `anchorTimeout`
 * shortens that for a step whose anchor may legitimately never come — and the
 * tour carries on either way.
 *
 * ── Why Next goes dead between steps ─────────────────────────────────────────
 * Preparing a step is not instant — it can push a route, run a `before()` hook
 * that clicks a dialog open, wait for an anchor inside it, and then glide the
 * page to it. The popover the visitor is looking at throughout still belongs to
 * the step *before*, and its Next button is live. So `preparing` holds from the
 * first line of `show()` to the last, `advance()` and `retreat()` drop anything
 * that arrives while it is set, and `syncNavigationButtons` greys the two
 * buttons out so the refusal is visible rather than a click that vanished. Only
 * the close button stays live: whatever else is going on, the visitor can leave.
 *
 * ── Who owns the scrolling and the placement ─────────────────────────────────
 * Not driver, in both cases. `tour/dom.ts` scrolls the anchor into place and
 * waits for it to stop *before* anything is highlighted, so driver's own
 * `bringInView` finds the work already done; `tour/placement.ts` clamps the
 * stage and measures the side, because driver's answer for an anchor taller
 * than the viewport is to pin the card over the hole it just cut. Both modules
 * carry the long version of why.
 */
import { nextTick } from 'vue'

import { type Alignment, type DriveStep, type Driver, type Side, driver } from 'driver.js'
import type { RouteLocationNormalized, Router } from 'vue-router'

import { useTourStore } from '@/stores/tour'

import i18n from '@/locales/i18n'
import {
  ANCHOR_CLASS,
  firstVisible,
  observeAnchorRemoval,
  openAccordionSection,
  prefersReducedMotion,
  scrollAnchorIntoView,
  waitForElement,
} from '@/tour/dom'
import {
  POPOVER_HEIGHT_ESTIMATE,
  STAGE_PADDING,
  acquireStageProxy,
  boxOf,
  chooseSide,
  computeStageBox,
  nudgePopover,
  releaseStageProxy,
} from '@/tour/placement'
import { setTourRunning } from '@/tour/quiet'
import type { TourStep, TourTrackId } from '@/tour/types'

/**
 * Both of these moved to `tour/dom.ts`, where `placement.ts` and a step's
 * `before()` hook can reach them without importing driver.js. Re-exported here
 * because the engine was their home for two releases and every caller outside
 * the tour still asks for them by this path.
 */
export { firstVisible, waitForElement }

/**
 * Tailwind's `md`. The responsive twins this has to choose between switch at
 * `sm` or `xl` rather than `md`, which is exactly why the choice is a
 * *preference* and not a verdict — whichever selector wins, the engine still
 * takes the first match with a real box, and falls back to the other one.
 */
const DESKTOP_MEDIA_QUERY = '(min-width: 768px)'

/** The one class every popover carries, so `index.css` can theme it. */
const POPOVER_CLASS = 'wirksam-tour'

/**
 * Added on top of `POPOVER_CLASS` for a step that resolved no anchor.
 *
 * That is the chapter card by design (`jobsIntro`, `formIntro` name no
 * `element` at all) and the degraded case by accident (an anchor that never
 * turned up, or one the visitor removed by pressing Book). Both end up as the
 * same object on screen — a centred card of prose with nothing highlighted
 * behind it — so both get the same slightly wider measure. `index.css` carries
 * the rule; driver takes the step's `popoverClass` in place of the instance's
 * rather than alongside it, which is why this string repeats the base class.
 */
const CHAPTER_CLASS = `${POPOVER_CLASS} wirksam-tour-chapter`

/**
 * Put on the outgoing popover at the top of `show()`, and never taken off —
 * every `highlight()` rebuilds the popover DOM, so the class leaves with the
 * node it was written on. `index.css` fades it.
 */
const LEAVING_CLASS = 'wirksam-tour-leaving'

const t = (key: string, named?: Record<string, unknown>) =>
  named ? i18n.global.t(key, named) : i18n.global.t(key)

/**
 * A step's own Next label, or the generic one.
 *
 * The label is *copy* — "Open this shift", "Schicht öffnen" — so it lives in
 * `locales/{en,de}/tour.json` under the step, and a step opts into one merely
 * by a translator writing it. `te()` asks the current locale;
 * `check_locale_parity.js` guarantees the two trees agree, so the second look
 * at `'en'` is belt and braces for a locale bundle loaded before a parity fix
 * landed.
 */
function stepLabel(key: string, fallbackKey: string): string {
  const te = i18n.global.te.bind(i18n.global)
  return te(key) || te(key, 'en') ? t(key) : t(fallbackKey)
}

/**
 * driver.js writes button labels with `innerHTML`.
 *
 * Nothing in `tour.json` is markup and it must stay that way, but the labels
 * are now translator-facing copy in two languages, and an `&` in a German
 * label is one bad edit away from being parsed as an entity.
 */
function escapeHtml(value: string): string {
  return value.replace(
    /[&<>"']/g,
    (character) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]!,
  )
}

/** Take the staged-anchor class off whatever is still wearing it. */
function clearAnchorClass(): void {
  for (const element of document.querySelectorAll<HTMLElement>(`.${ANCHOR_CLASS}`)) {
    element.classList.remove(ANCHOR_CLASS)
  }
}

/**
 * Boxes the popover must not sit on top of.
 *
 * The demo banner always, because it stays live during a tour — `index.css`
 * lifts it above the overlay and gives it its pointer events back — and a card
 * over a live control is worse than a card over a dead one. And, for a step
 * whose anchor is inside a modal, the modal itself: on a phone
 * `ShiftDetailDialog` is a bottom sheet, and driver's idea of "beside the
 * button" lands the card across the middle of the roster the copy is
 * describing.
 */
function avoidBoxesFor(step: TourStep, element: HTMLElement | null): DOMRect[] {
  const boxes: DOMRect[] = []

  const banner = document.querySelector<HTMLElement>('[data-testid="sandbox-banner"]')
  if (banner) boxes.push(banner.getBoundingClientRect())

  const avoidSelector = step.avoid ?? (step.inOverlay ? '[role="dialog"]' : null)
  // The anchor's own ancestor first: a dialog is teleported to `body`, so there
  // can be more than one `[role="dialog"]` in the document and only one of them
  // is the one this step opened.
  const avoided = avoidSelector
    ? (element?.closest<HTMLElement>(avoidSelector) ?? firstVisible(avoidSelector))
    : null
  if (avoided) boxes.push(avoided.getBoundingClientRect())

  return boxes
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
  const found = await waitForElement(selectors[0], { timeout: step.anchorTimeout })
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
   * `before()` hook, waiting for the anchor to turn up, gliding the page to it.
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
  /**
   * The step the popover on screen belongs to, or `null` when there is none.
   *
   * Read for exactly one thing: closing an `inOverlay` step's dialog *before*
   * the router leaves the view it was opened from. `store.currentStep` cannot
   * answer that — by the time the leaving matters the store has already moved
   * on to the step being prepared.
   */
  let lastRenderedStep: TourStep | null = null
  /** Disconnects the "did the anchor just leave the DOM?" observer. */
  let stopWatchingAnchor: (() => void) | null = null

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
    // Ahead of the `instance` guard, all of it: the proxy is appended to
    // `<body>` and the anchor class is written on somebody else's element, so
    // both outlive a driver that has already been destroyed, and both would
    // then be inherited by whatever the tour points at next.
    stopWatchingAnchor?.()
    stopWatchingAnchor = null
    lastRenderedStep = null
    releaseStageProxy()
    clearAnchorClass()

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
   * Close the dialog `step` opened, if it opened one.
   *
   * An `inOverlay` step reaches its anchor by opening a modal, and reka-ui
   * holds `pointer-events: none` on `<body>` for as long as one is up — driver's
   * own stylesheet re-enables it for the popover, which is the only reason the
   * step works at all. Leave the dialog behind and every control outside it is
   * inert: the demo banner is one of those, so "restart the tour" did nothing,
   * because the click never reached the button.
   *
   * Escape is the dialog's own documented way out, so this closes it through
   * the component rather than reaching past it into somebody's `v-model`. It is
   * a `keydown`, which reka-ui listens for and driver — which watches `keyup`
   * for Escape — does not, so this cannot be mistaken for a dismissal.
   */
  function dismissOverlay(step: TourStep | null) {
    if (!step?.inOverlay) return
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
  }

  function stop() {
    // Before the store forgets which step it was on.
    dismissOverlay(useTourStore().currentStep)
    useTourStore().stop()
    teardown()
    setTourRunning(false)
  }

  function finish() {
    dismissOverlay(useTourStore().currentStep)
    useTourStore().finish()
    teardown()
    setTourRunning(false)
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
    // A popover that vanishes the instant Next is pressed reads as a glitch;
    // one that fades reads as a hand-off. The fade is shorter than the route
    // push it covers, so it costs nothing but the perception of it.
    document.querySelector('.driver-popover')?.classList.add(LEAVING_CLASS)
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
      // Close the dialog *before* the push, not after the view unmounts.
      //
      // The unmount does eventually take the dialog with it, which is why this
      // looked like it worked — but reka-ui restores the `pointer-events: none`
      // it put on `<body>` from a watcher cleanup several ticks later, and in
      // between the visitor has a new screen they cannot click on. Asking the
      // dialog to close itself first, and giving it a frame to do it in, keeps
      // the two facts in the right order.
      if (lastRenderedStep?.inOverlay && lastRenderedStep.route !== step.route) {
        dismissOverlay(lastRenderedStep)
        await nextTick()
        await new Promise<void>((resolve) => window.requestAnimationFrame(() => resolve()))
        if (token !== renderToken) return
      }
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
        await step.before({ waitFor: waitForElement, openSection: openAccordionSection })
      } catch {
        // A hook that could not open what it wanted leaves the step to fall
        // back to a centred popover, which is a worse step and not a dead tour.
      }
      if (token !== renderToken) return
    }

    const element = await resolveAnchor(step)
    if (token !== renderToken) return

    // The pre-scroll, and the only place it can live: `render()` is synchronous
    // and driver's `onHighlightStarted` fires inside `highlight()`, so neither
    // can be awaited. Doing it here — with `preparing` still set, so Next stays
    // dead for the length of the glide — means the highlight appears on a page
    // that has already stopped moving, and driver's own `bringInView` finds the
    // anchor in view and does nothing.
    if (element) {
      clearAnchorClass()
      await scrollAnchorIntoView(element)
      if (token !== renderToken) return
    }

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
        // Same-route steps keep the instance, so `highlight()` runs driver's
        // stage tween from the old rectangle to the new one — the connective
        // motion this design wants, for free. A visitor who asked for less of
        // it gets none.
        animate: !prefersReducedMotion(),
        allowClose: true,
        overlayColor: '#000',
        overlayOpacity: 0.6,
        stagePadding: STAGE_PADDING,
        stageRadius: 10,
        // Always off. driver silently downgrades it to an instant jump for any
        // anchor whose parent scrolls, which is nearly every anchor here, so it
        // was never buying the smoothness its name promises;
        // `scrollAnchorIntoView` owns that now, and has already finished by the
        // time driver looks.
        smoothScroll: false,
        popoverClass: POPOVER_CLASS,
        // Escape and a click on the backdrop both land here. `destroy()` does
        // not, which is what keeps a navigation from reading as a dismissal.
        onDestroyStarted: () => stop(),
      })
      instanceRoute = route
    }

    // Measured against the popover that is still on screen — the previous
    // step's — because the one being placed does not exist yet. Both are the
    // same card at the same width, so the only case the estimate has to cover
    // is the first step of a tour.
    const popoverHeight =
      document.querySelector('.driver-popover')?.getBoundingClientRect().height ||
      POPOVER_HEIGHT_ESTIMATE

    releaseStageProxy()
    let stage = element
    let side: Side = step.side ?? 'bottom'
    let align: Alignment = step.align ?? 'start'

    if (element) {
      // `null` here means the anchor is small enough for driver to place around
      // unaided, which is the preferred answer: the real element keeps
      // `driver-active-element` and stays clickable.
      const box = computeStageBox(element, popoverHeight)
      if (box) stage = acquireStageProxy(box)
      const chosen = chooseSide(box ?? boxOf(element), side, align, popoverHeight)
      side = chosen.side
      align = chosen.align
    }

    const driveStep: DriveStep = {
      popover: {
        title: t(step.titleKey),
        description: t(step.bodyKey),
        side,
        align,
        showButtons: ['next', 'previous', 'close'],
        disableButtons: store.isFirstStep ? ['previous'] : [],
        showProgress: true,
        // Rendered here rather than through driver's own `{{current}}`
        // substitution: the step index belongs to the store, driver is driven
        // one step at a time and has no idea how many there are, and the
        // chapter is a third thing driver has never heard of.
        progressText: t('tour.common.progress', {
          chapter: t(step.chapterKey),
          current: store.stepIndex + 1,
          total: store.stepCount,
        }),
        nextBtnText: escapeHtml(
          store.isLastStep ? t('tour.common.done') : stepLabel(step.nextKey, 'tour.common.next'),
        ),
        prevBtnText: t('tour.common.back'),
        popoverClass: element ? POPOVER_CLASS : CHAPTER_CLASS,
        onNextClick: () => void advance(),
        onPrevClick: () => void retreat(),
        onCloseClick: () => stop(),
        onPopoverRender: (popover) => {
          const skipLabel = t('tour.common.skip')
          popover.closeButton.setAttribute('aria-label', skipLabel)
          popover.closeButton.title = skipLabel
          // The Next label is per-step copy now, so "is this the end?" can no
          // longer be read off the button text, and driver's own
          // `driver-popover-done-btn` is not an alternative: it only appears
          // when `doneButton` is set, which `highlight()` — as opposed to
          // `drive()` — never does. `e2e/tests/public/sandbox-tour.spec.ts`
          // reads both of these.
          popover.nextButton.dataset.tourLast = String(store.isLastStep)
          popover.nextButton.dataset.tourStep = step.id
          if (step.inOverlay && element) settleOverlayFocus(element)
        },
      },
    }

    // Left unset for a missing anchor: driver falls back to an invisible
    // element pinned to the middle of the viewport, which is exactly the
    // centred, un-highlighted popover that case wants.
    if (stage) driveStep.element = stage

    instance.highlight(driveStep)
    lastRenderedStep = step

    // After `highlight()`, because driver writes the popover's position *after*
    // `onPopoverRender` returns — anything written from inside that hook is
    // overwritten a line later. Not awaited: the render is done either way, and
    // the nudge is a correction to a card that is already readable.
    void nudgePopover(avoidBoxesFor(step, element))

    stopWatchingAnchor?.()
    stopWatchingAnchor = null
    if (element && step.inOverlay) {
      stopWatchingAnchor = observeAnchorRemoval(element, () => {
        // The visitor took the invitation and pressed Book, and `handleBook`
        // closed the dialog with the footer inside it. Re-render the *same*
        // step centred rather than leaving driver staging a rectangle that is
        // no longer in the document — and deliberately without re-running
        // `before()`, which would reopen a different chip and produce exactly
        // the sudden view change this design exists to remove.
        if (useTourStore().currentStep === step) render(step, null)
      })
    }
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
    // Before the store, so that anything the first screen fires while the tour
    // is being prepared — `notifyPendingJoinRequests` is the one that matters —
    // is held rather than dropped on top of step one.
    setTourRunning(true)
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
