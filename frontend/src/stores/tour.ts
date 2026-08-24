/**
 * Where a running guided tour actually lives.
 *
 * The driver.js instance is disposable — `tour/engine.ts` destroys it before
 * every navigation and builds a new one on the other side — so nothing durable
 * may be kept inside it. Which track is running, which step it is on and
 * whether it is running at all are held here, and mirrored into `sessionStorage`
 * so a reload, a browser Back or a view remount picks the tour up mid-sentence
 * instead of dropping it.
 *
 * `sessionStorage` rather than `localStorage`: a tour belongs to one sitting.
 * A visitor who comes back next week should meet the app, not step 7 of a tour
 * they abandoned.
 */
import { computed, ref, watch } from 'vue'

import { defineStore } from 'pinia'

import { helperTrack } from '@/tour/tracks/helper'
import { managerTrack } from '@/tour/tracks/manager'
import type { TourStep, TourTrack, TourTrackId } from '@/tour/types'

/**
 * The registry lives next to the store rather than in the engine because the
 * store is the thing that needs it: `stepCount` is what decides that a tour has
 * run out of steps, and that decision must be testable without a DOM.
 */
export const TOUR_TRACKS: Record<TourTrackId, TourTrack> = {
  helper: helperTrack,
  manager: managerTrack,
}

export type TourStatus = 'idle' | 'running' | 'finished'

const STORAGE_KEY = 'wirksam:tour'

interface PersistedTour {
  track: TourTrackId
  stepIndex: number
}

function isTrackId(value: unknown): value is TourTrackId {
  return value === 'helper' || value === 'manager'
}

/**
 * Read a resumable tour back, or `null` for anything that cannot be trusted.
 *
 * Validated field by field rather than cast: the stored index outlives the
 * release that wrote it, and a track that lost two steps in the meantime would
 * otherwise resume past its own end and show nothing at all.
 */
function loadFromStorage(): PersistedTour | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<PersistedTour>
    if (!isTrackId(parsed.track)) return null
    const stepIndex = parsed.stepIndex
    if (typeof stepIndex !== 'number' || !Number.isInteger(stepIndex)) return null
    if (stepIndex < 0 || stepIndex >= TOUR_TRACKS[parsed.track].steps.length) return null
    return { track: parsed.track, stepIndex }
  } catch {
    // Malformed JSON, or a browser that refuses storage outright. Either way
    // there is no tour to resume, which is a perfectly good answer.
    return null
  }
}

export const useTourStore = defineStore('tour', () => {
  const resumed = loadFromStorage()

  const activeTrack = ref<TourTrackId | null>(resumed?.track ?? null)
  const stepIndex = ref(resumed?.stepIndex ?? 0)
  const status = ref<TourStatus>(resumed ? 'running' : 'idle')

  const steps = computed<TourStep[]>(() =>
    activeTrack.value ? TOUR_TRACKS[activeTrack.value].steps : [],
  )
  const stepCount = computed(() => steps.value.length)
  const currentStep = computed<TourStep | null>(() => steps.value[stepIndex.value] ?? null)
  const nextStep = computed<TourStep | null>(() => steps.value[stepIndex.value + 1] ?? null)
  const isRunning = computed(() => status.value === 'running' && currentStep.value !== null)
  const isFirstStep = computed(() => stepIndex.value === 0)
  const isLastStep = computed(
    () => stepCount.value > 0 && stepIndex.value === stepCount.value - 1,
  )

  /**
   * `null` means "nothing to resume" and clears the key, so an ended tour
   * cannot be revived by a reload.
   */
  const persistable = computed(() =>
    status.value === 'running' && activeTrack.value
      ? JSON.stringify({ track: activeTrack.value, stepIndex: stepIndex.value })
      : null,
  )

  // Not `immediate`: the first value is whatever was just read back, and
  // writing it again would be pure noise.
  watch(persistable, (value) => {
    try {
      if (value === null) sessionStorage.removeItem(STORAGE_KEY)
      else sessionStorage.setItem(STORAGE_KEY, value)
    } catch {
      // Private browsing, or a quota that a JSON object this small cannot
      // plausibly have exhausted. The tour still runs; it just will not survive
      // a reload.
    }
  })

  function start(track: TourTrackId) {
    activeTrack.value = track
    stepIndex.value = 0
    status.value = 'running'
  }

  /** Ends the tour the way reaching the last step does. */
  function finish() {
    activeTrack.value = null
    stepIndex.value = 0
    status.value = 'finished'
  }

  /** Ends the tour the way the visitor dismissing it does. */
  function stop() {
    activeTrack.value = null
    stepIndex.value = 0
    status.value = 'idle'
  }

  function goTo(index: number) {
    if (!activeTrack.value) return
    if (index < 0) {
      stepIndex.value = 0
      return
    }
    // Walking off the end is how a tour ends when the visitor presses Next on
    // the last step, so it is a completion rather than an out-of-range guard.
    if (index >= stepCount.value) {
      finish()
      return
    }
    stepIndex.value = index
    status.value = 'running'
  }

  function next() {
    goTo(stepIndex.value + 1)
  }

  function previous() {
    goTo(stepIndex.value - 1)
  }

  return {
    activeTrack,
    stepIndex,
    status,
    steps,
    stepCount,
    currentStep,
    nextStep,
    isRunning,
    isFirstStep,
    isLastStep,
    start,
    stop,
    finish,
    goTo,
    next,
    previous,
  }
})
