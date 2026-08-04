import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  ALLOWED_CHANNELS,
  ALLOWED_OFFSETS,
  type BookingReminder,
  type ReminderOffsetEntry,
  useBookingReminderStore,
} from '@/stores/bookingReminder'

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

const offsets: ReminderOffsetEntry[] = [
  { offset_minutes: 60, channels: ['email'] },
  { offset_minutes: 1440, channels: ['email', 'push'] },
]

const reminder: BookingReminder = {
  id: 'rem-1',
  booking_id: 'book-1',
  offset_minutes: 60,
  channels: ['email'],
  remind_at: '2026-08-04T17:00:00Z',
  status: 'pending',
  created_at: '2026-08-01T09:00:00Z',
}

beforeEach(() => {
  vi.resetAllMocks()
  setActivePinia(createPinia())
})

describe('useBookingReminderStore', () => {
  describe('constants', () => {
    it('exposes the offsets the backend accepts, ascending', () => {
      expect(ALLOWED_OFFSETS).toEqual([15, 30, 60, 120, 180, 360, 720, 1440, 2880])
      expect([...ALLOWED_OFFSETS]).toEqual([...ALLOWED_OFFSETS].sort((a, b) => a - b))
    })

    it('exposes the supported delivery channels', () => {
      expect(ALLOWED_CHANNELS).toEqual(['email', 'push', 'telegram'])
    })
  })

  describe('initial state', () => {
    it('has no default offsets', () => {
      const store = useBookingReminderStore()

      expect(store.defaultOffsets).toEqual([])
    })
  })

  describe('fetchDefaultOffsets', () => {
    it('stores and returns the user defaults', async () => {
      api.get.mockResolvedValue({ data: { default_reminder_offsets: offsets } })
      const store = useBookingReminderStore()

      const result = await store.fetchDefaultOffsets()

      expect(api.get).toHaveBeenCalledWith({ url: '/users/me/reminder-defaults' })
      expect(result).toEqual(offsets)
      expect(store.defaultOffsets).toEqual(offsets)
    })

    it('handles a user who has opted out of every reminder', async () => {
      api.get.mockResolvedValue({ data: { default_reminder_offsets: [] } })
      const store = useBookingReminderStore()

      await expect(store.fetchDefaultOffsets()).resolves.toEqual([])
      expect(store.defaultOffsets).toEqual([])
    })

    it('propagates API errors and leaves the cache untouched', async () => {
      api.get.mockResolvedValueOnce({ data: { default_reminder_offsets: offsets } })
      const store = useBookingReminderStore()
      await store.fetchDefaultOffsets()

      api.get.mockRejectedValueOnce(new Error('503'))

      await expect(store.fetchDefaultOffsets()).rejects.toThrow('503')
      expect(store.defaultOffsets).toEqual(offsets)
    })
  })

  describe('updateDefaultOffsets', () => {
    it('PUTs the new offsets and caches the server response', async () => {
      const next: ReminderOffsetEntry[] = [{ offset_minutes: 30, channels: ['push'] }]
      api.put.mockResolvedValue({ data: { default_reminder_offsets: next } })
      const store = useBookingReminderStore()

      const result = await store.updateDefaultOffsets(next)

      expect(api.put).toHaveBeenCalledWith({
        url: '/users/me/reminder-defaults',
        body: { default_reminder_offsets: next },
      })
      expect(result).toEqual(next)
      expect(store.defaultOffsets).toEqual(next)
    })

    it('supports clearing all defaults', async () => {
      api.put.mockResolvedValue({ data: { default_reminder_offsets: [] } })
      const store = useBookingReminderStore()

      await store.updateDefaultOffsets([])

      expect(api.put).toHaveBeenCalledWith({
        url: '/users/me/reminder-defaults',
        body: { default_reminder_offsets: [] },
      })
      expect(store.defaultOffsets).toEqual([])
    })

    it('propagates validation errors without touching the cache', async () => {
      api.put.mockRejectedValue(new Error('422'))
      const store = useBookingReminderStore()

      await expect(
        store.updateDefaultOffsets([{ offset_minutes: 7, channels: ['email'] }]),
      ).rejects.toThrow('422')
      expect(store.defaultOffsets).toEqual([])
    })
  })

  describe('fetchBookingReminders', () => {
    it('returns the reminders for the given booking', async () => {
      api.get.mockResolvedValue({ data: { items: [reminder] } })
      const store = useBookingReminderStore()

      const result = await store.fetchBookingReminders('book-1')

      expect(api.get).toHaveBeenCalledWith({ url: '/bookings/book-1/reminders' })
      expect(result).toEqual([reminder])
    })

    it('returns an empty list for a booking without reminders', async () => {
      api.get.mockResolvedValue({ data: { items: [] } })
      const store = useBookingReminderStore()

      await expect(store.fetchBookingReminders('book-2')).resolves.toEqual([])
    })

    it('propagates a 404 for an unknown booking', async () => {
      api.get.mockRejectedValue(new Error('404'))
      const store = useBookingReminderStore()

      await expect(store.fetchBookingReminders('missing')).rejects.toThrow('404')
    })
  })

  describe('addBookingReminder', () => {
    it('POSTs the offset and channels and returns the created reminder', async () => {
      api.post.mockResolvedValue({ data: reminder })
      const store = useBookingReminderStore()

      const result = await store.addBookingReminder('book-1', 60, ['email'])

      expect(api.post).toHaveBeenCalledWith({
        url: '/bookings/book-1/reminders',
        body: { offset_minutes: 60, channels: ['email'] },
      })
      expect(result).toEqual(reminder)
    })

    it('does not mutate the cached default offsets', async () => {
      api.get.mockResolvedValue({ data: { default_reminder_offsets: offsets } })
      api.post.mockResolvedValue({ data: reminder })
      const store = useBookingReminderStore()
      await store.fetchDefaultOffsets()

      await store.addBookingReminder('book-1', 60, ['email'])

      expect(store.defaultOffsets).toEqual(offsets)
    })

    it('propagates a rejected duplicate reminder', async () => {
      api.post.mockRejectedValue(new Error('409'))
      const store = useBookingReminderStore()

      await expect(store.addBookingReminder('book-1', 60, ['email'])).rejects.toThrow('409')
    })
  })

  describe('deleteReminder', () => {
    it('DELETEs the reminder by id', async () => {
      api.del.mockResolvedValue(undefined)
      const store = useBookingReminderStore()

      await expect(store.deleteReminder('rem-1')).resolves.toBeUndefined()
      expect(api.del).toHaveBeenCalledWith({ url: '/reminders/rem-1' })
    })

    it('propagates a 404 for an unknown reminder', async () => {
      api.del.mockRejectedValue(new Error('404'))
      const store = useBookingReminderStore()

      await expect(store.deleteReminder('missing')).rejects.toThrow('404')
    })
  })
})
