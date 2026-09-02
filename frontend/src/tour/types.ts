/**
 * The shape of a guided tour, and the one convention that binds a step to its
 * copy.
 *
 * A step is *data*, deliberately: it names a route, a selector and a handful of
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
  /**
   * Open the `TaskCreateView` accordion section with this `data-testid`, and
   * resolve once its content is open and measurable.
   *
   * `activeSection` is a component-local `ref` with no public handle, so the
   * only honest way in is the trigger the visitor would press themselves —
   * which is also what makes this idempotent, because it reads `data-state`
   * first and leaves an already-open section alone. `details` is the section
   * that starts open (`TaskCreateView.vue:182`), so a blind click would
   * *collapse* the one part of the form the copy can currently see.
   *
   * Resolves `null` when the section is not on this screen, which a track
   * treats as "carry on with a centred popover" rather than as an error.
   */
  openSection: (testId: string) => Promise<HTMLElement | null>
}

export interface TourStep {
  /** Stable across releases: it is half of the translation key. */
  id: string
  /**
   * Which act of the track this step belongs to; the key half of
   * `tour.common.chapters.<chapter>`.
   *
   * Required rather than optional, because the progress line reads
   * "{chapter} · Step n of m" — an absent chapter would not degrade, it would
   * print an empty gap with a stray separator in front of it. Making the field
   * mandatory means a step cannot silently fall out of the narrative.
   */
  chapter: string
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
  /**
   * A box the popover must be nudged clear of, as a selector.
   *
   * Staying off the *anchor* is driver.js's job; staying off the container the
   * anchor sits in is not, and that is the case that reads as broken: a popover
   * placed beside a button inside a dialog can still land on top of the dialog,
   * covering the very roster the copy is talking about. The engine resolves
   * this against the anchor's ancestors first and the document second, and
   * defaults it to the enclosing `[role="dialog"]` for an `inOverlay` step, so
   * only the unusual case has to say anything here.
   */
  avoid?: string
  /**
   * Override `ANCHOR_TIMEOUT_MS` for a step whose anchor is conditional.
   *
   * The default wait is generous because most anchors are merely late. An
   * anchor that may legitimately never arrive — a panel that hides itself when
   * it has nothing to report — should give up quickly instead, so the step
   * degrades to a centred popover in a second or two rather than freezing the
   * tour while the visitor watches a stage that is never coming.
   */
  anchorTimeout?: number
  side?: Side
  align?: Alignment
  /**
   * Async setup for a step whose anchor does not exist until something is
   * opened. Must be **idempotent**: the engine re-runs it whenever the view
   * remounts under it, which a filter change in `TasksView` does on every
   * keystroke.
   *
   * The return value is discarded, so a hook that forwards one of the context
   * helpers has to await it in a block body rather than returning it — the
   * engine needs the promise the hook itself returns, not the element the
   * helper resolves with.
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
  /**
   * `tour.<track>.<id>.next` — **optional copy**: the engine falls back to
   * `tour.common.next` when the key does not resolve.
   *
   * Derived for every step even though most steps will never have the copy,
   * because that is what lets a step opt into a verb-shaped label ("Open this
   * shift") purely by a translator adding the string. The wording stays in the
   * locale files rather than in TypeScript, one step can carry both locales,
   * and the extra key stays invisible to `tracks.spec.ts`'s exact key-set
   * assertion, which reads one level above the step id.
   */
  nextKey: string
  /** `tour.common.chapters.<chapter>` — filled in by `defineTrack`. */
  chapterKey: string
}

/** What a track file writes; the translation keys are derived. */
export type TourStepDefinition = Omit<TourStep, 'titleKey' | 'bodyKey' | 'nextKey' | 'chapterKey'>

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
 * own dotted path, on screen, in the app's first impression. `nextKey` is the
 * one exception the spec cannot make: it is allowed to miss, and the engine
 * reads it through a `te()` probe.
 */
export function defineTrack(id: TourTrackId, steps: TourStepDefinition[]): TourTrack {
  return {
    id,
    steps: steps.map((step) => ({
      ...step,
      titleKey: `tour.${id}.${step.id}.title`,
      bodyKey: `tour.${id}.${step.id}.body`,
      nextKey: `tour.${id}.${step.id}.next`,
      chapterKey: `tour.common.chapters.${step.chapter}`,
    })),
  }
}
