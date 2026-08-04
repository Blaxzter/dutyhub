import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useCalendarFeedStore } from '@/stores/calendarFeed'

import type { CalendarFeedRead } from '@/client/types.gen'

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

const feed: CalendarFeedRead = {
  id: 'feed-1',
  feed_url: 'https://wirksam.test/calendar/feed/abc.ics',
  is_enabled: true,
  last_accessed_at: null,
  created_at: '2026-08-01T10:00:00Z',
}

/** A promise plus its resolver, for observing `loading` mid-flight. */
function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.spyOn(console, 'error').mockImplementation(() => {})
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useCalendarFeedStore', () => {
  describe('initial state', () => {
    it('has no feed settings and is not loading', () => {
      const store = useCalendarFeedStore()

      expect(store.feedSettings).toBeNull()
      expect(store.loading).toBe(false)
    })
  })

  describe('fetchFeedSettings', () => {
    it('stores the returned settings', async () => {
      api.get.mockResolvedValue({ data: feed })
      const store = useCalendarFeedStore()

      await store.fetchFeedSettings()

      expect(api.get).toHaveBeenCalledWith({ url: '/calendar/feed-settings' })
      expect(store.feedSettings).toEqual(feed)
      expect(store.loading).toBe(false)
    })

    it('accepts a null payload for users without a feed', async () => {
      api.get.mockResolvedValue({ data: null })
      const store = useCalendarFeedStore()

      await store.fetchFeedSettings()

      expect(store.feedSettings).toBeNull()
    })

    it('flips loading true while in flight and false afterwards', async () => {
      const d = deferred<{ data: CalendarFeedRead }>()
      api.get.mockReturnValue(d.promise)
      const store = useCalendarFeedStore()

      const pending = store.fetchFeedSettings()
      expect(store.loading).toBe(true)

      d.resolve({ data: feed })
      await pending

      expect(store.loading).toBe(false)
    })

    it('only calls the API once for repeated requests', async () => {
      api.get.mockResolvedValue({ data: feed })
      const store = useCalendarFeedStore()

      await store.fetchFeedSettings()
      await store.fetchFeedSettings()

      expect(api.get).toHaveBeenCalledTimes(1)
    })

    it('logs the failure, keeps state null and allows a retry', async () => {
      api.get.mockRejectedValueOnce(new Error('boom'))
      const store = useCalendarFeedStore()

      await expect(store.fetchFeedSettings()).resolves.toBeUndefined()

      expect(console.error).toHaveBeenCalled()
      expect(store.feedSettings).toBeNull()
      expect(store.loading).toBe(false)

      api.get.mockResolvedValueOnce({ data: feed })
      await store.fetchFeedSettings()

      expect(api.get).toHaveBeenCalledTimes(2)
      expect(store.feedSettings).toEqual(feed)
    })
  })

  describe('enableFeed', () => {
    it('stores the newly created feed', async () => {
      api.post.mockResolvedValue({ data: feed })
      const store = useCalendarFeedStore()

      await store.enableFeed()

      expect(api.post).toHaveBeenCalledWith({ url: '/calendar/feed-settings' })
      expect(store.feedSettings).toEqual(feed)
      expect(store.loading).toBe(false)
    })

    it('rethrows and resets loading on failure', async () => {
      api.post.mockRejectedValue(new Error('nope'))
      const store = useCalendarFeedStore()

      await expect(store.enableFeed()).rejects.toThrow('nope')

      expect(console.error).toHaveBeenCalled()
      expect(store.feedSettings).toBeNull()
      expect(store.loading).toBe(false)
    })
  })

  describe('regenerateFeed', () => {
    it('replaces the settings with the regenerated feed', async () => {
      api.get.mockResolvedValue({ data: feed })
      const store = useCalendarFeedStore()
      await store.fetchFeedSettings()

      const rotated: CalendarFeedRead = { ...feed, feed_url: 'https://wirksam.test/new.ics' }
      api.post.mockResolvedValue({ data: rotated })

      await store.regenerateFeed()

      expect(api.post).toHaveBeenCalledWith({ url: '/calendar/feed-settings/regenerate' })
      expect(store.feedSettings).toEqual(rotated)
      expect(store.loading).toBe(false)
    })

    it('rethrows, keeps the old URL and resets loading on failure', async () => {
      api.get.mockResolvedValue({ data: feed })
      const store = useCalendarFeedStore()
      await store.fetchFeedSettings()

      api.post.mockRejectedValue(new Error('rotate failed'))

      await expect(store.regenerateFeed()).rejects.toThrow('rotate failed')

      expect(store.feedSettings).toEqual(feed)
      expect(store.loading).toBe(false)
    })
  })

  describe('disableFeed', () => {
    it('marks the cached feed as disabled', async () => {
      api.get.mockResolvedValue({ data: feed })
      api.del.mockResolvedValue(undefined)
      const store = useCalendarFeedStore()
      await store.fetchFeedSettings()

      await store.disableFeed()

      expect(api.del).toHaveBeenCalledWith({ url: '/calendar/feed-settings' })
      expect(store.feedSettings).toEqual({ ...feed, is_enabled: false })
      expect(store.loading).toBe(false)
    })

    it('leaves state null when there was nothing cached', async () => {
      api.del.mockResolvedValue(undefined)
      const store = useCalendarFeedStore()

      await store.disableFeed()

      expect(api.del).toHaveBeenCalledTimes(1)
      expect(store.feedSettings).toBeNull()
      expect(store.loading).toBe(false)
    })

    it('rethrows, keeps the feed enabled and resets loading on failure', async () => {
      api.get.mockResolvedValue({ data: feed })
      api.del.mockRejectedValue(new Error('still enabled'))
      const store = useCalendarFeedStore()
      await store.fetchFeedSettings()

      await expect(store.disableFeed()).rejects.toThrow('still enabled')

      expect(console.error).toHaveBeenCalled()
      expect(store.feedSettings).toEqual(feed)
      expect(store.loading).toBe(false)
    })
  })
})
