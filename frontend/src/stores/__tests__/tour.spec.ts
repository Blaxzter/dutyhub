// @vitest-environment jsdom
import { nextTick } from 'vue'

import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TOUR_TRACKS, useTourStore } from '@/stores/tour'

const STORAGE_KEY = 'wirksam:tour'

const helperSteps = TOUR_TRACKS.helper.steps
const managerSteps = TOUR_TRACKS.manager.steps

/** The store reads storage during setup, so seed before instantiating. */
function seed(value: unknown) {
  sessionStorage.setItem(STORAGE_KEY, typeof value === 'string' ? value : JSON.stringify(value))
}

function readPersisted(): unknown {
  const raw = sessionStorage.getItem(STORAGE_KEY)
  return raw ? JSON.parse(raw) : null
}

beforeEach(() => {
  vi.restoreAllMocks()
  sessionStorage.clear()
  setActivePinia(createPinia())
})

describe('useTourStore', () => {
  describe('the track registry', () => {
    it('carries both tracks, each with steps', () => {
      expect(Object.keys(TOUR_TRACKS).sort()).toEqual(['helper', 'manager'])
      expect(helperSteps.length).toBeGreaterThan(0)
      expect(managerSteps.length).toBeGreaterThan(0)
    })
  })

  describe('initial state', () => {
    it('is idle with nothing stored', () => {
      const store = useTourStore()

      expect(store.status).toBe('idle')
      expect(store.activeTrack).toBeNull()
      expect(store.stepIndex).toBe(0)
      expect(store.currentStep).toBeNull()
      expect(store.nextStep).toBeNull()
      expect(store.isRunning).toBe(false)
      expect(store.stepCount).toBe(0)
    })

    it('reports no last step while no track is running', () => {
      const store = useTourStore()

      // Guards the `stepCount > 0` half of `isLastStep`: index 0 of an empty
      // track is not the end of anything.
      expect(store.isLastStep).toBe(false)
      expect(store.isFirstStep).toBe(true)
    })
  })

  describe('rehydration', () => {
    it('restores the track and step index of an interrupted tour', () => {
      seed({ track: 'manager', stepIndex: 3 })

      const store = useTourStore()

      expect(store.activeTrack).toBe('manager')
      expect(store.stepIndex).toBe(3)
      expect(store.status).toBe('running')
      expect(store.isRunning).toBe(true)
      expect(store.currentStep).toBe(managerSteps[3])
      expect(store.nextStep).toBe(managerSteps[4])
    })

    it('ignores an unknown track name', () => {
      seed({ track: 'accountant', stepIndex: 1 })

      expect(useTourStore().status).toBe('idle')
    })

    it('ignores a step index that is not a whole number', () => {
      seed({ track: 'helper', stepIndex: 1.5 })

      expect(useTourStore().status).toBe('idle')
    })

    it('ignores a step index the track no longer has', () => {
      // The release that wrote the entry may have had more steps than this one.
      seed({ track: 'helper', stepIndex: helperSteps.length })

      expect(useTourStore().status).toBe('idle')
    })

    it('ignores a negative step index', () => {
      seed({ track: 'helper', stepIndex: -1 })

      expect(useTourStore().status).toBe('idle')
    })

    it('ignores a malformed entry', () => {
      seed('not json at all')

      expect(useTourStore().status).toBe('idle')
    })

    it('survives a browser that refuses to hand storage over', () => {
      vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
        throw new Error('SecurityError')
      })

      expect(useTourStore().status).toBe('idle')
    })

    it('does not rewrite what it just read', () => {
      seed({ track: 'helper', stepIndex: 2 })
      const setItem = vi.spyOn(Storage.prototype, 'setItem')

      useTourStore()

      expect(setItem).not.toHaveBeenCalled()
    })
  })

  describe('start', () => {
    it('runs the named track from its first step', () => {
      const store = useTourStore()

      store.start('helper')

      expect(store.activeTrack).toBe('helper')
      expect(store.stepIndex).toBe(0)
      expect(store.status).toBe('running')
      expect(store.stepCount).toBe(helperSteps.length)
      expect(store.currentStep).toBe(helperSteps[0])
    })

    it('restarts a track that is already part-way through', () => {
      seed({ track: 'helper', stepIndex: 4 })
      const store = useTourStore()

      store.start('helper')

      expect(store.stepIndex).toBe(0)
    })
  })

  describe('moving between steps', () => {
    it('advances and rewinds one step at a time', () => {
      const store = useTourStore()
      store.start('helper')

      store.next()
      expect(store.stepIndex).toBe(1)
      expect(store.isFirstStep).toBe(false)

      store.previous()
      expect(store.stepIndex).toBe(0)
      expect(store.isFirstStep).toBe(true)
    })

    it('stays on the first step when rewound past the beginning', () => {
      const store = useTourStore()
      store.start('helper')

      store.previous()

      expect(store.stepIndex).toBe(0)
      expect(store.status).toBe('running')
    })

    it('ends the tour when advanced past the last step', () => {
      const store = useTourStore()
      store.start('helper')
      store.goTo(helperSteps.length - 1)

      expect(store.isLastStep).toBe(true)

      store.next()

      expect(store.status).toBe('finished')
      expect(store.activeTrack).toBeNull()
      expect(store.stepIndex).toBe(0)
      expect(store.isRunning).toBe(false)
    })

    it('does nothing when no track is running', () => {
      const store = useTourStore()

      store.next()
      store.goTo(2)

      expect(store.status).toBe('idle')
      expect(store.stepIndex).toBe(0)
    })

    it('re-enters a running state when jumped to from a finished one', () => {
      const store = useTourStore()
      store.start('manager')
      store.goTo(2)

      expect(store.stepIndex).toBe(2)
      expect(store.status).toBe('running')
    })
  })

  describe('ending', () => {
    it('stop() clears the tour and its stored place', async () => {
      const store = useTourStore()
      store.start('manager')
      store.next()
      await nextTick()
      expect(readPersisted()).not.toBeNull()

      store.stop()
      await nextTick()

      expect(store.status).toBe('idle')
      expect(store.activeTrack).toBeNull()
      expect(store.stepIndex).toBe(0)
      expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull()
    })

    it('finish() clears the stored place too, so a reload cannot revive it', async () => {
      const store = useTourStore()
      store.start('manager')
      await nextTick()

      store.finish()
      await nextTick()

      expect(store.status).toBe('finished')
      expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull()
    })
  })

  describe('persistence', () => {
    it('mirrors the place into sessionStorage on every move', async () => {
      const store = useTourStore()

      store.start('helper')
      await nextTick()
      expect(readPersisted()).toEqual({ track: 'helper', stepIndex: 0 })

      store.next()
      await nextTick()
      expect(readPersisted()).toEqual({ track: 'helper', stepIndex: 1 })
    })

    it('survives a route change: a fresh store picks the tour up mid-track', async () => {
      const store = useTourStore()
      store.start('manager')
      store.next()
      store.next()
      await nextTick()

      // A route change tears down and rebuilds the views, and a reload rebuilds
      // the whole app — either way the next reader is a brand-new store over
      // the same session storage.
      setActivePinia(createPinia())
      const resumed = useTourStore()

      expect(resumed.activeTrack).toBe('manager')
      expect(resumed.stepIndex).toBe(2)
      expect(resumed.isRunning).toBe(true)
      expect(resumed.currentStep).toBe(managerSteps[2])
    })

    it('keeps running when the browser refuses to store anything', async () => {
      const store = useTourStore()
      vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new Error('QuotaExceededError')
      })

      store.start('helper')
      await nextTick()

      expect(store.isRunning).toBe(true)
      expect(store.currentStep).toBe(helperSteps[0])
    })

    it('keeps running when the browser refuses to clear anything', async () => {
      const store = useTourStore()
      store.start('helper')
      await nextTick()

      vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
        throw new Error('SecurityError')
      })

      store.stop()
      await nextTick()

      expect(store.status).toBe('idle')
    })
  })
})
