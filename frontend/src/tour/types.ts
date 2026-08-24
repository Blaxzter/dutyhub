/**
 * The shape of a guided tour, and the one convention that binds a step to its
 * copy.
 *
 * A step is *data*, deliberately: it names a route, a selector and two
 * translation keys, and it holds no element reference and no driver.js object.
 * That is what lets `tour/engine.ts` throw its driver away before every
 * navigation and rebuild it from the store afterwards — see the module comment
 * there for why a cached anchor is never safe in this app.
 */
import type { Alignment, Side } from 'driver.js'

export type TourTrackId = 'helper' | 'manager'

/**
 * Helpers a step's `before()` hook is handed, rather than importing.
 *
 * `stores/tour.ts` imports the tracks (it needs their length to know when a
 * tour has run out of steps), and the engine imports the store. A track that
 * reached back into the engine for `waitForElement` would close that ring;
 * passing the helper in keeps the tracks free of every dependency but Vue.
 */
export interface TourStepContext {
  /**
   * Resolve when `selector` matches an element with a non-zero box, or with
   * `null` once the timeout runs out. Never rejects.
   */
  waitFor: (selector: string, options?: { timeout?: number }) => Promise<HTMLElement | null>
}

export interface TourStep {
  /** Stable across releases: it is half of the translation key. */
  id: string
  /**
   * Route *name* the step belongs to. The engine navigates here when the step
   * is entered, and hides the popover whenever the browser is somewhere else.
   * Names, never paths — `TasksView` and `ReportingView` rewrite their own
   * query string on every filter change, and a path comparison would read each
   * of those as a new page.
   */
  route?: string
  /** Query the route needs to show the right thing, e.g. `{ tab: 'people' }`. */
  query?: Record<string, string>
  /** CSS selector for the anchor. Omit for a step that is only prose. */
  element?: string
  /**
   * Anchor to prefer below `md`.
   *
   * Several controls exist twice — `btn-create-task` and `fab-create-task`, the
   * sidebar link and the bottom-nav tab — with the hidden twin still in the DOM
   * at zero size, which driver.js will happily draw a box around. The engine
   * picks by `matchMedia`, then falls back to the other selector if the
   * preferred one has no visible match.
   */
  mobileElement?: string
  /**
   * Selector to settle first, when the anchor only appears inside something
   * else that has to render — a list before its rows, a dialog before its
   * buttons.
   */
  waitFor?: string
  side?: Side
  align?: Alignment
  /**
   * Async setup for a step whose anchor does not exist until something is
   * opened. Must be **idempotent**: the engine re-runs it whenever the view
   * remounts under it, which a filter change in `TasksView` does on every
   * keystroke.
   */
  before?: (ctx: TourStepContext) => Promise<void> | void
  /**
   * The anchor lives inside a modal dialog with a focus trap. See
   * `settleOverlayFocus` in the engine for what this changes.
   */
  inOverlay?: boolean
  /** `tour.<track>.<id>.title` — filled in by `defineTrack`. */
  titleKey: string
  /** `tour.<track>.<id>.body` — filled in by `defineTrack`. */
  bodyKey: string
}

/** What a track file writes; the two translation keys are derived. */
export type TourStepDefinition = Omit<TourStep, 'titleKey' | 'bodyKey'>

export interface TourTrack {
  id: TourTrackId
  steps: TourStep[]
}

/**
 * Build a track, deriving each step's translation keys from its id.
 *
 * The keys end up as real fields on the step rather than being computed at
 * render time so that `tour/__tests__/tracks.spec.ts` can walk them and assert
 * every one resolves in both locales — vue-i18n renders a missing key as its
 * own dotted path, on screen, in the app's first impression.
 */
export function defineTrack(id: TourTrackId, steps: TourStepDefinition[]): TourTrack {
  return {
    id,
    steps: steps.map((step) => ({
      ...step,
      titleKey: `tour.${id}.${step.id}.title`,
      bodyKey: `tour.${id}.${step.id}.body`,
    })),
  }
}
