import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useSidebarStore } from '@/stores/sidebar'

import type { SidebarResponse } from '@/client/types.gen'

const api = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
}))

vi.mock('@/composables/useAuthenticatedClient', () => ({
  useAuthenticatedClient: () => ({
    get: api.get,
    post: api.post,
    put: api.put,
    patch: api.patch,
    delete: api.del,
  }),
}))

const payload: SidebarResponse = {
  events: [{ id: 'e1', name: 'Summer Festival', status: 'published' }],
  tasks: [{ id: 't1', name: 'Bar shift', status: 'open', open_shifts: 3 }],
  bookings: [
    {
      id: 'b1',
      slot_id: 's1',
      task_id: 't1',
      slot_title: 'Evening',
      slot_date: '2026-08-01',
      slot_start_time: '18:00:00',
    },
  ],
}

const emptyPayload: SidebarResponse = { events: [], tasks: [], bookings: [] }

beforeEach(() => {
  vi.resetAllMocks()
  vi.useFakeTimers()
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useSidebarStore', () => {
  describe('initial state', () => {
    it('starts empty and unloaded', () => {
      const store = useSidebarStore()

      expect(store.events).toEqual([])
      expect(store.tasks).toEqual([])
      expect(store.bookings).toEqual([])
      expect(store.loaded).toBe(false)
    })
  })

  describe('fetch', () => {
    it('fills every collection and flips `loaded`', async () => {
      api.get.mockResolvedValue({ data: payload })
      const store = useSidebarStore()

      await store.fetch()

      expect(api.get).toHaveBeenCalledWith({ url: '/dashboard/sidebar' })
      expect(store.events).toEqual(payload.events)
      expect(store.tasks).toEqual(payload.tasks)
      expect(store.bookings).toEqual(payload.bookings)
      expect(store.loaded).toBe(true)
    })

    it('marks itself loaded even when the backend returns nothing', async () => {
      api.get.mockResolvedValue({ data: emptyPayload })
      const store = useSidebarStore()

      await store.fetch()

      expect(store.events).toEqual([])
      expect(store.loaded).toBe(true)
    })

    it('swallows API errors and leaves the state untouched', async () => {
      api.get.mockRejectedValue(new Error('offline'))
      const store = useSidebarStore()

      await expect(store.fetch()).resolves.toBeUndefined()

      expect(store.events).toEqual([])
      expect(store.tasks).toEqual([])
      expect(store.bookings).toEqual([])
      expect(store.loaded).toBe(false)
    })

    it('keeps previously loaded data when a later fetch fails', async () => {
      api.get.mockResolvedValueOnce({ data: payload })
      const store = useSidebarStore()
      await store.fetch()

      api.get.mockRejectedValueOnce(new Error('offline'))
      await store.fetch()

      expect(store.events).toEqual(payload.events)
      expect(store.loaded).toBe(true)
    })
  })

  describe('refresh (debounced)', () => {
    it('does not hit the API before the debounce window elapses', async () => {
      api.get.mockResolvedValue({ data: payload })
      const store = useSidebarStore()

      store.refresh()
      await vi.advanceTimersByTimeAsync(249)

      expect(api.get).not.toHaveBeenCalled()
    })

    it('coalesces a burst of calls into a single fetch', async () => {
      api.get.mockResolvedValue({ data: payload })
      const store = useSidebarStore()

      store.refresh()
      await vi.advanceTimersByTimeAsync(100)
      store.refresh()
      await vi.advanceTimersByTimeAsync(100)
      store.refresh()
      await vi.advanceTimersByTimeAsync(250)

      expect(api.get).toHaveBeenCalledTimes(1)
      expect(store.loaded).toBe(true)
    })

    it('fetches again once a previous debounce has fired', async () => {
      api.get.mockResolvedValue({ data: payload })
      const store = useSidebarStore()

      store.refresh()
      await vi.advanceTimersByTimeAsync(250)
      store.refresh()
      await vi.advanceTimersByTimeAsync(250)

      expect(api.get).toHaveBeenCalledTimes(2)
    })
  })
})
