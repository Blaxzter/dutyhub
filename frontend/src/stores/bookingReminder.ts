import { ref } from 'vue'

import { defineStore } from 'pinia'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

export interface BookingReminder {
  id: string
  booking_id: string
  offset_minutes: number
  channels: string[]
  remind_at: string
  status: 'pending' | 'sent' | 'cancelled' | 'expired'
  created_at: string
}

export interface ReminderOffsetEntry {
  offset_minutes: number
  channels: string[]
}

export interface DefaultReminderOffsets {
  default_reminder_offsets: ReminderOffsetEntry[]
}

export const ALLOWED_OFFSETS = [15, 30, 60, 120, 180, 360, 720, 1440, 2880] as const
export const ALLOWED_CHANNELS = ['email', 'push', 'telegram'] as const

export const useBookingReminderStore = defineStore('bookingReminder', () => {
  const { get, post, put, delete: del } = useAuthenticatedClient()

  const defaultOffsets = ref<ReminderOffsetEntry[]>([])

  // ── Default reminder offsets ────────────────────────────────────

  async function fetchDefaultOffsets(): Promise<ReminderOffsetEntry[]> {
    const res = await get<{ data: DefaultReminderOffsets }>({
      url: '/users/me/reminder-defaults',
    })
    defaultOffsets.value = res.data.default_reminder_offsets
    return defaultOffsets.value
  }

  async function updateDefaultOffsets(
    offsets: ReminderOffsetEntry[],
  ): Promise<ReminderOffsetEntry[]> {
    const res = await put<{ data: DefaultReminderOffsets }>({
      url: '/users/me/reminder-defaults',
      body: { default_reminder_offsets: offsets },
    })
    defaultOffsets.value = res.data.default_reminder_offsets
    return defaultOffsets.value
  }

  // ── Per-booking reminders ───────────────────────────────────────

  async function fetchBookingReminders(bookingId: string): Promise<BookingReminder[]> {
    const res = await get<{ data: { items: BookingReminder[] } }>({
      url: `/bookings/${bookingId}/reminders`,
    })
    return res.data.items
  }

  async function addBookingReminder(
    bookingId: string,
    offsetMinutes: number,
    channels: string[],
  ): Promise<BookingReminder> {
    const res = await post<{ data: BookingReminder }>({
      url: `/bookings/${bookingId}/reminders`,
      body: { offset_minutes: offsetMinutes, channels },
    })
    return res.data
  }

  async function deleteReminder(reminderId: string): Promise<void> {
    await del({ url: `/reminders/${reminderId}` })
  }

  return {
    defaultOffsets,
    fetchDefaultOffsets,
    updateDefaultOffsets,
    fetchBookingReminders,
    addBookingReminder,
    deleteReminder,
  }
})
