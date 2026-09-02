/**
 * "A tour is on screen — hold that thought."
 *
 * The offender is `notifyPendingJoinRequests` in `stores/auth.ts`: an
 * `ActionToast` with `duration: Infinity`, fired from `HomeView.loadFeed`, which
 * lands on the organiser dashboard at exactly the moment the tour's first step
 * does. It sits over the popover, and driver's own
 * `.driver-active * { pointer-events: none }` makes its two buttons dead — so
 * the visitor's first act inside the product is to click something that does
 * nothing at all.
 *
 * A flag the caller consults, rather than a `toast.dismiss()` sprayed from the
 * engine, because dismissing is the wrong verb: the toast is a real thing the
 * organiser needs to see. It is simply not competing for the same square inches
 * as the tour. Held, then released.
 *
 * Module-level rather than a store, and with **zero imports**: `stores/auth.ts`
 * is the reader, and a store reaching into another store at setup time is the
 * import cycle this codebase already works around twice.
 */
let running = false

/**
 * Work waiting for the tour to get out of the way.
 *
 * Not a queue that survives anything: it lives as long as the page does, and a
 * held callback that never runs because the visitor closed the tab is a toast
 * nobody needed.
 */
const held: (() => void)[] = []

export function setTourRunning(value: boolean): void {
  if (running === value) return
  running = value
  if (running) return

  // Spliced out before running any of them, so that a callback which itself
  // calls `whenTourIsOver` — nothing does today, but the shape invites it —
  // runs immediately instead of being appended to the array being iterated.
  const queued = held.splice(0, held.length)
  for (const run of queued) run()
}

export function isTourRunning(): boolean {
  return running
}

/**
 * Run `fn` now, or as soon as the tour is out of the way.
 *
 * Outside a tour — which is every visit but a demo's first — this is a plain
 * function call, and that is the point: the call site reads the same either
 * way and carries no branch of its own.
 */
export function whenTourIsOver(fn: () => void): void {
  if (running) held.push(fn)
  else fn()
}
