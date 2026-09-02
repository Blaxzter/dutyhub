/**
 * Everything the tour needs to say about the DOM, kept away from driver.js.
 *
 * `firstVisible` and `waitForElement` used to live in `engine.ts`, which was
 * fine while the engine was the only caller. It no longer is: `placement.ts`
 * waits on the popover's own box, a step's `before()` hook is handed
 * `waitForElement` through `TourStepContext`, and both of those importing the
 * engine would close the ring `types.ts` describes — tracks → engine → store →
 * tracks. So the measuring lives here, and the engine re-exports the two names
 * it used to own so that nothing outside had to be rewritten.
 *
 * The other reason this module exists is that the tour has taken *ownership of
 * scrolling*. driver.js has a `smoothScroll` option, but it silently downgrades
 * to an instant jump for any element whose parent scrolls — which is nearly
 * every anchor in this app — and its `bringInView` returns early whenever the
 * element is already fully visible. The result was a popover that appeared and
 * then had the page yanked out from under it. Doing the scroll here, first, and
 * waiting for it to stop, means driver's own attempt finds the anchor already
 * in place and does nothing.
 */

/**
 * Long enough to cover a cold route chunk plus its first API call — the tour
 * can be resumed by a full page reload, where the popover is asked for before
 * the view has even been fetched.
 */
const ANCHOR_TIMEOUT_MS = 6000

/**
 * The class the engine puts on the real anchor for as long as it is staged.
 *
 * `index.css` hangs two things off it: a `scroll-margin-top` that keeps the
 * anchor clear of the demo banner — `scrollIntoView` has no margin option and
 * driver has no `scrollMargin` — and the pointer events that a stage proxy
 * would otherwise have taken away from it.
 */
export const ANCHOR_CLASS = 'wirksam-tour-anchor'

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
 * Whether the visitor asked for less motion.
 *
 * Read per call rather than cached: the setting is a live media query, and the
 * tour outlives any one answer to it.
 */
export function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/**
 * Resolve once `element`'s box has stopped moving.
 *
 * Watches the *rect* rather than a scroller's `scrollTop`, because there is no
 * single scroller to watch: the app nests them — `SidebarInset` inside the
 * page, a dialog body inside that — and one `scrollIntoView` can move several
 * at once. The only signal that reliably means "the scroll is over" is the
 * thing being scrolled to standing still.
 *
 * Frames are the clock, deliberately. `stableFrames` consecutive frames with an
 * unchanged rounded top/left ends the wait; `maxFrames` ends it regardless, and
 * that cap is the whole safety story — an element with a looping animation on
 * it never settles, and without the cap it would hold `preparing` (and with it
 * the Next button) forever. 40 frames is ~660 ms at 60 Hz, comfortably longer
 * than Chrome's smooth-scroll animation.
 *
 * A backgrounded tab throttles `requestAnimationFrame` to nothing, so this can
 * sit unresolved while the visitor is elsewhere. That is the right behaviour
 * rather than a hang: it picks up where it left off when they come back,
 * whereas a timer-based escape hatch would resolve against a layout nobody has
 * seen and place the popover from it.
 *
 * In jsdom `getBoundingClientRect` answers a constant, so this settles in
 * `stableFrames` frames and no spec has to fake time.
 */
export function waitForRectSettled(
  element: HTMLElement,
  { maxFrames = 40, stableFrames = 3 }: { maxFrames?: number; stableFrames?: number } = {},
): Promise<void> {
  return new Promise((resolve) => {
    let lastTop = Number.NaN
    let lastLeft = Number.NaN
    let stable = 0
    let frames = 0

    const tick = () => {
      const rect = element.getBoundingClientRect()
      const top = Math.round(rect.top)
      const left = Math.round(rect.left)
      // `NaN === NaN` is false, so the first frame can never count as stable —
      // which is what makes an already-still element take `stableFrames` frames
      // rather than resolving before the scroll it was asked to wait for even
      // started.
      if (top === lastTop && left === lastLeft) stable += 1
      else stable = 0
      lastTop = top
      lastLeft = left
      frames += 1

      if (stable >= stableFrames || frames >= maxFrames) {
        resolve()
        return
      }
      window.requestAnimationFrame(tick)
    }

    window.requestAnimationFrame(tick)
  })
}

/**
 * Put the anchor where driver would have put it, before driver looks.
 *
 * The geometry is driver's own — centre the anchor, or align its top when it is
 * taller than the viewport — so that driver's `bringInView`, running a moment
 * later, finds nothing to do. That is the point: driver cannot be told to
 * scroll smoothly here (see the module comment), so the only way to get a calm
 * transition is to have already finished the scroll by the time it asks.
 */
export async function scrollAnchorIntoView(element: HTMLElement): Promise<void> {
  element.classList.add(ANCHOR_CLASS)

  const block = element.offsetHeight > window.innerHeight ? 'start' : 'center'
  const calm = prefersReducedMotion()

  // Optional-called because jsdom does not implement `scrollIntoView` at all,
  // and `engine.spec.ts` renders steps against jsdom. Short-circuited under
  // reduced motion because a settle loop after an *instant* scroll is a pure
  // delay — and because that spec stubs `matchMedia` to match every query,
  // which is what keeps it deterministic and fast.
  element.scrollIntoView?.({ behavior: calm ? 'auto' : 'smooth', block, inline: 'center' })
  if (calm) return

  await waitForRectSettled(element)
}

/**
 * Open one shadcn/reka accordion section, once.
 *
 * `TaskCreateView`'s `activeSection` is a component-local `ref` with no public
 * handle, so the only honest way in is the trigger the visitor would press
 * themselves. That makes idempotence the caller's problem, and it matters more
 * than it looks: `activeSection` starts on `'details'`, so a blind click on an
 * already-open section *collapses* the one part of the form the copy can see.
 * reka-ui writes `data-state` onto both the item and its trigger, which answers
 * "is it already open?" without touching the component's state at all.
 *
 * The wait is on the *content* rather than the trigger because the panel
 * animates its height: for a few frames after the click it is in the DOM with a
 * zero box — the shape `firstVisible` rejects, and the one driver would cut a
 * 0×0 hole around.
 *
 * Resolves `null` when the section is not on this screen, which a track treats
 * as "carry on with a centred popover" rather than as an error.
 */
export async function openAccordionSection(testId: string): Promise<HTMLElement | null> {
  const item = firstVisible(`[data-testid="${testId}"]`)
  if (!item) return null

  const trigger = item.querySelector<HTMLElement>('[data-slot="accordion-trigger"]')
  if (!trigger) return item

  const closed =
    item.getAttribute('data-state') === 'closed' || trigger.getAttribute('data-state') === 'closed'
  if (closed) trigger.click()

  // Two seconds rather than the anchor default: this panel is already on screen
  // and merely mid-transition, so a wait measured in seconds means it is never
  // coming and the step is better off degrading than stalling.
  await waitForElement(
    `[data-testid="${testId}"] [data-slot="accordion-content"][data-state="open"]`,
    { timeout: 2000 },
  )

  return item
}

/**
 * Tell the caller when `element` leaves the document.
 *
 * Only used for `inOverlay` steps, and only because the book step invites the
 * visitor to press the very button it is pointing at: `handleBook` sets
 * `dialogOpen.value = false`, which takes the whole dialog — footer, roster and
 * all — out of the DOM. Driver has no idea and carries on staging a rectangle
 * that no longer exists, so the popover ends up beside a hole in an empty
 * overlay. The caller re-renders the same step centred instead.
 *
 * Watching the document rather than the element's parent, because the removal
 * happens several levels up: reka-ui unmounts the teleported dialog root.
 */
export function observeAnchorRemoval(element: HTMLElement, onGone: () => void): () => void {
  const observer = new MutationObserver(() => {
    if (element.isConnected) return
    observer.disconnect()
    onGone()
  })

  observer.observe(document.documentElement, { childList: true, subtree: true })
  return () => observer.disconnect()
}
