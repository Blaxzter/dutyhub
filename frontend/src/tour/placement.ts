/**
 * Where the popover goes, when driver.js's own answer is "over the stage".
 *
 * driver picks a side by asking, four times, whether the popover fits *outside*
 * the anchor's rectangle. An anchor taller than the viewport answers no on all
 * four sides, and driver's response to that is documented and deterministic: it
 * pins the card to the bottom of the screen, centred, with the arrow removed —
 * on top of the very hole it just cut. Padding and offset cannot fix it; a
 * 1142 px list in a 900 px viewport does not fit anywhere.
 *
 * So this module does three things driver will not:
 *
 *  1. **Clamps the stage.** The rectangle handed to driver is the slice of the
 *     anchor that is on screen and still leaves a popover's worth of room, so
 *     driver's own arithmetic has an answer again. A one-node, click-through
 *     proxy stands in for the real element; `index.css` gives the real one its
 *     pointer events back, because `driver-active-element` lands on the proxy.
 *  2. **Measures the side.** The step's `side` is a preference, not a verdict.
 *     It wins whenever it has room, and loses to whichever side has the most
 *     when it does not — which is what stops a `side: 'top'` step on a short
 *     screen from being silently thrown to the bottom of the viewport.
 *  3. **Nudges afterwards.** driver positions the popover *after*
 *     `onPopoverRender` fires, so anything written from that hook is overwritten
 *     a line later. The nudge runs a frame after the card's own box stops
 *     moving, and keeps it clear of two things driver knows nothing about: the
 *     fixed demo banner, and whatever box the step said it must not cover.
 */
import type { Alignment, Side } from 'driver.js'

import { waitForRectSettled } from '@/tour/dom'

/** Must match the `stagePadding` handed to `driver()`. */
export const STAGE_PADDING = 8
/** driver's `popoverOffset` default, which this design never changes. */
const POPOVER_OFFSET = 10
/** The gap driver leaves between the stage edge and the card. */
const GAP = STAGE_PADDING + POPOVER_OFFSET
/** Breathing room against the viewport edges, and around an avoided box. */
const MARGIN = 8
/** Below this a clamped stage stops reading as a highlight and starts reading as a glitch. */
const MIN_STAGE = 56
/** `.driver-popover.wirksam-tour { max-width: 23rem }` — see `index.css`. */
const POPOVER_WIDTH = 368
/**
 * The height to assume before there is a popover on screen to measure.
 *
 * Worst case across both tracks: title, four lines of body, footer.
 */
export const POPOVER_HEIGHT_ESTIMATE = 236

const PROXY_ID = 'wirksam-tour-stage'

export interface Box {
  top: number
  left: number
  width: number
  height: number
}

/** Viewport-coordinate adapter, for the case where no clamping was needed. */
export function boxOf(element: HTMLElement): Box {
  const rect = element.getBoundingClientRect()
  return { top: rect.top, left: rect.left, width: rect.width, height: rect.height }
}

/**
 * How much of the top of the viewport the demo banner owns, right now.
 *
 * Measured rather than taken from the banner's own `h-11` constant, because it
 * is only there during a demo — every other visitor gets zero, and a hard-coded
 * inset would push every popover down by 44 px for no reason.
 */
export function topInset(): number {
  const banner = document.querySelector<HTMLElement>('[data-testid="sandbox-banner"]')
  return banner ? banner.getBoundingClientRect().height : 0
}

/**
 * The slice of `element` the tour will actually point at, or `null` for "use
 * the element itself".
 *
 * `null` is the common and preferred answer: an anchor small enough for driver
 * to place around unaided should stay the real element, so that
 * `driver-active-element` lands on it and the visitor can still click the thing
 * the copy is talking about. A box comes back only when clamping changed
 * something, and the visitor then sees the top of the list highlighted — which
 * is more than they see today.
 */
export function computeStageBox(element: HTMLElement, popoverHeight: number): Box | null {
  const vw = document.documentElement.clientWidth
  const vh = window.innerHeight
  const inset = topInset()
  const rect = element.getBoundingClientRect()

  const reserve = popoverHeight + GAP * 2 + MARGIN
  const top = Math.max(rect.top, inset + MARGIN)
  const left = Math.max(rect.left, MARGIN)
  const right = Math.min(rect.right, vw - MARGIN)
  let bottom = Math.min(rect.bottom, vh - MARGIN)

  // Entirely off screen, or a sliver of one. Nothing useful to clamp to, and a
  // stage the size of a scrollbar is worse than the real rectangle.
  if (bottom - top < MIN_STAGE || right - left < 8) return null

  const fitsBelow = vh - bottom >= reserve
  const fitsAbove = top - inset >= reserve
  if (!fitsBelow && !fitsAbove) {
    // Give the popover the bottom of the viewport by taking it off the stage.
    // This is the case that produced the bug: without it there is nowhere for
    // the card to go, and driver puts it on top of the highlight.
    bottom = Math.max(top + MIN_STAGE, vh - reserve)
  }

  const box = { top, left, width: right - left, height: bottom - top }
  const untouched =
    Math.abs(box.top - rect.top) < 1 &&
    Math.abs(box.left - rect.left) < 1 &&
    Math.abs(box.height - rect.height) < 1 &&
    Math.abs(box.width - rect.width) < 1
  return untouched ? null : box
}

/**
 * A zero-visual, click-through stand-in for an oversized anchor.
 *
 * One node, reused across steps rather than created and thrown away, and
 * positioned in *document* coordinates so that a scroll during the step does
 * not leave it behind. It carries no background and no border: everything the
 * visitor sees is driver's overlay cutting a hole around it.
 */
export function acquireStageProxy(box: Box): HTMLElement {
  let proxy = document.getElementById(PROXY_ID)
  if (!proxy) {
    proxy = document.createElement('div')
    proxy.id = PROXY_ID
    proxy.setAttribute('aria-hidden', 'true')
    proxy.style.position = 'absolute'
    proxy.style.pointerEvents = 'none'
    document.body.appendChild(proxy)
  }

  proxy.style.top = `${box.top + window.scrollY}px`
  proxy.style.left = `${box.left + window.scrollX}px`
  proxy.style.width = `${box.width}px`
  proxy.style.height = `${box.height}px`
  return proxy
}

export function releaseStageProxy(): void {
  document.getElementById(PROXY_ID)?.remove()
}

/**
 * Side and align, measured rather than declared.
 *
 * Room is computed against the *inset* viewport, so a step that would fit above
 * its anchor only by sliding under the demo banner is correctly told it does
 * not fit. The fallback order — bottom, top, right, left — is preference under
 * pressure rather than best fit: a card below the thing it describes reads as
 * an explanation of it, and one beside it reads as a footnote.
 *
 * Alignment is only chosen for the horizontal sides. For `left`/`right` the
 * step's own align is about vertical placement, which the measurement here says
 * nothing about, so it is passed through untouched.
 */
export function chooseSide(
  box: Box,
  preferred: Side,
  preferredAlign: Alignment,
  popoverHeight: number,
): { side: Side; align: Alignment } {
  const vw = document.documentElement.clientWidth
  const vh = window.innerHeight
  const inset = topInset()

  const room: Record<Side, number> = {
    top: box.top - inset - (popoverHeight + GAP),
    bottom: vh - (box.top + box.height) - (popoverHeight + GAP),
    left: box.left - (POPOVER_WIDTH + GAP),
    right: vw - (box.left + box.width) - (POPOVER_WIDTH + GAP),
  }

  const side: Side =
    room[preferred] >= 0
      ? preferred
      : ((['bottom', 'top', 'right', 'left'] as Side[]).find((candidate) => room[candidate] >= 0) ??
        'bottom')

  if (side === 'left' || side === 'right') return { side, align: preferredAlign }

  // Thirds rather than halves: an anchor near the middle of a wide screen looks
  // wrong with the card hanging off one end of it, and one near an edge looks
  // wrong centred, because the card would run off the screen and be clamped
  // back by `nudgePopover` into an arrow that points nowhere.
  const centre = box.left + box.width / 2
  const align: Alignment = centre < vw / 3 ? 'start' : centre > (vw * 2) / 3 ? 'end' : 'center'
  return { side, align }
}

function intersects(a: Box, b: DOMRect): boolean {
  return (
    a.left < b.right && a.left + a.width > b.left && a.top < b.bottom && a.top + a.height > b.top
  )
}

/**
 * The last word on where the popover sits.
 *
 * Waits for the card's own box to stop moving first, because driver writes the
 * position after `onPopoverRender` and then animates it: reading a rect mid-tween
 * and writing it back would freeze the card halfway. Two stable frames is
 * enough here — unlike a scroll, this animation is driver's own and short.
 *
 * Then two corrections, in order: back inside the inset viewport, and off every
 * box the step named. The arrow is dropped whenever anything moved, because it
 * was aimed at where the card used to be and an arrow pointing at nothing is
 * more confusing than no arrow at all.
 */
export async function nudgePopover(avoid: DOMRect[]): Promise<void> {
  const wrapper = document.querySelector<HTMLElement>('.driver-popover')
  if (!wrapper) return

  await waitForRectSettled(wrapper, { stableFrames: 2 })

  const rect = wrapper.getBoundingClientRect()
  const vw = document.documentElement.clientWidth
  const vh = window.innerHeight
  const ceiling = topInset() + MARGIN

  // The inner `Math.max` is what keeps a popover taller or wider than the
  // viewport pinned to the top-left corner rather than flipped inside out.
  const left = Math.min(Math.max(rect.left, MARGIN), Math.max(MARGIN, vw - rect.width - MARGIN))
  let top = Math.min(Math.max(rect.top, ceiling), Math.max(ceiling, vh - rect.height - MARGIN))

  for (const box of avoid) {
    if (!intersects({ top, left, width: rect.width, height: rect.height }, box)) continue
    const above = box.top - MARGIN - rect.height
    const below = box.bottom + MARGIN
    if (above >= ceiling) top = above
    else if (below + rect.height <= vh - MARGIN) top = below
    // Neither side has room: leave it where it is. A card half over a dialog is
    // still readable; one shoved off the bottom of the screen is not.
  }

  if (Math.abs(top - rect.top) < 1 && Math.abs(left - rect.left) < 1) return

  wrapper.style.top = `${top}px`
  wrapper.style.left = `${left}px`
  wrapper.style.bottom = 'auto'
  wrapper.style.right = 'auto'
  wrapper.querySelector('.driver-popover-arrow')?.classList.add('driver-popover-arrow-none')
}
