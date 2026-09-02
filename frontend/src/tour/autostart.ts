/**
 * Whether this sitting's automatic tour has already been offered.
 *
 * Split out of `tour/install.ts` so that `stores/sandbox.ts` can reset the flag
 * without importing the tour engine — and with it driver.js — into a code path
 * the landing page runs. `SandboxBanner.vue` goes to the same trouble for the
 * same reason, and asks for a restart through a `window` event rather than an
 * import. **Nothing in here imports anything**, and it should stay that way.
 *
 * Per *sitting* rather than per account, like the tour state itself: a visitor
 * who reloads mid-demo should not be sent back to step one, and one who opens
 * the demo again tomorrow should be welcomed again.
 */
const AUTOSTART_KEY = 'wirksam:tour:autostarted'

export function hasAutoStarted(): boolean {
  try {
    return sessionStorage.getItem(AUTOSTART_KEY) === '1'
  } catch {
    // A browser that refuses storage would restart the tour on every
    // navigation, which is far worse than never starting it automatically.
    return true
  }
}

export function markAutoStarted(): void {
  try {
    sessionStorage.setItem(AUTOSTART_KEY, '1')
  } catch {
    // Nothing to do: `hasAutoStarted()` answers `true` in the same conditions.
  }
}

/**
 * Forget it, so the next demo in this tab is welcomed too.
 *
 * A flag per sitting was right while a tab only ever held one demo. It no
 * longer does: a visitor who exits the helper demo to try the manager one, or
 * whose demo expires and who starts another from the landing page, got no tour
 * at all the second time and nothing on screen to explain why. `sandbox.start()`
 * is the exact moment the fact becomes true again — not `exit()`, which an
 * *expired* demo never reaches, and not `authSession.clear()`, which runs for
 * every real logout and every failed refresh as well.
 */
export function clearAutoStarted(): void {
  try {
    sessionStorage.removeItem(AUTOSTART_KEY)
  } catch {
    // Same condition as above: nothing was ever written, so nothing to remove.
  }
}
