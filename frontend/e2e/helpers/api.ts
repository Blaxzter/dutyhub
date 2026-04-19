/**
 * Shared E2E API helpers — used by both single-user and multi-user test files.
 */

import type { Page } from '@playwright/test'
import type {
  BookingRead,
  ShiftRead,
  TaskCreateWithShiftsResponse,
  EventRead,
  TaskRead,
} from '../../src/client/types.gen.js'

export type { BookingRead, ShiftRead, EventRead, TaskRead }
export type TaskWithShifts = TaskCreateWithShiftsResponse

export const API = process.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

/** Return a unique test name to avoid collisions between parallel workers. */
export function uniqueName(prefix: string): string {
  return `${prefix} ${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
}

/** Return an ISO date string (YYYY-MM-DD) offset from today by `daysFromNow`. */
export function futureDate(daysFromNow: number): string {
  const d = new Date()
  d.setDate(d.getDate() + daysFromNow)
  return d.toISOString().slice(0, 10)
}

/** Extract the Auth0 access token from localStorage. */
export async function getToken(page: Page): Promise<string> {
  return page.evaluate(() => {
    const key = Object.keys(localStorage).find((k) => k.startsWith('@@auth0spajs@@'))
    if (!key) return ''
    try {
      const raw = JSON.parse(localStorage.getItem(key) ?? '{}')
      return (raw as { body?: { access_token?: string } })?.body?.access_token ?? ''
    } catch {
      return ''
    }
  })
}

/** Make an authenticated API call inside the browser context. */
export async function api<T = unknown>(page: Page, method: string, path: string, body?: object): Promise<T> {
  const token = await getToken(page)
  const result = await page.evaluate(
    async ({ url, method, body, token }) => {
      const res = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: body ? JSON.stringify(body) : undefined,
      })
      if (res.status === 204) return { __status: 204, __ok: true, __body: null }
      const json = await res.json()
      return { __status: res.status, __ok: res.ok, __body: json }
    },
    { url: `${API}${path}`, method, body, token },
  )
  if (!result.__ok) {
    const detail = typeof result.__body === 'object' && result.__body !== null
      ? JSON.stringify(result.__body)
      : String(result.__body)
    throw new Error(`API ${method} ${path} failed with ${result.__status}: ${detail}`)
  }
  return result.__body as T
}

/** Create an event (draft or published). Admin token required. */
export async function createEvent(
  page: Page,
  name: string,
  status: 'draft' | 'published' = 'published',
): Promise<EventRead> {
  return api<EventRead>(page, 'POST', '/events/', {
    name,
    status,
    start_date: futureDate(30),
    end_date: futureDate(34),
  })
}

/** Delete an event. Admin token required. */
export async function deleteEvent(page: Page, id: string): Promise<void> {
  if (!id || id === 'undefined') return
  await api(page, 'DELETE', `/events/${id}`)
}

/** Remove the current user's availability for an event (best-effort). */
export async function clearAvailability(page: Page, eventId: string): Promise<void> {
  if (!eventId || eventId === 'undefined') return
  await api(page, 'DELETE', `/events/${eventId}/availability/me`)
}

// ── Task helpers ──────────────────────────────────────────────────────────────

/** Create a task with auto-generated shifts via the /tasks/with-shifts endpoint. */
export async function createTaskWithShifts(
  page: Page,
  opts: {
    name: string
    description?: string
    startDate?: string
    endDate?: string
    status?: 'draft' | 'published' | 'archived'
    location?: string
    category?: string
    eventId?: string
    startTime?: string
    endTime?: string
    slotDuration?: number
    peoplePerShift?: number
  },
): Promise<TaskCreateWithShiftsResponse> {
  // Use tomorrow to avoid the backend's future_shifts_cutoff filtering out past-time shifts
  const defaultDate = futureDate(1)
  const startDate = opts.startDate ?? defaultDate
  const endDate = opts.endDate ?? defaultDate
  return api<TaskCreateWithShiftsResponse>(page, 'POST', '/tasks/with-shifts', {
    name: opts.name,
    description: opts.description ?? null,
    start_date: startDate,
    end_date: endDate,
    status: opts.status ?? 'draft',
    location: opts.location ?? null,
    category: opts.category ?? null,
    event_id: opts.eventId ?? null,
    schedule: {
      default_start_time: (opts.startTime ?? '10:00') + ':00',
      default_end_time: (opts.endTime ?? '12:00') + ':00',
      shift_duration_minutes: opts.slotDuration ?? 60,
      people_per_shift: opts.peoplePerShift ?? 2,
      remainder_mode: 'drop',
      overrides: [],
      excluded_shifts: [],
    },
  })
}

/** Delete a task. Admin token required. */
export async function deleteTask(page: Page, id: string): Promise<void> {
  if (!id || id === 'undefined') return
  await api(page, 'DELETE', `/tasks/${id}`)
}

/** Publish a task (set status to published). */
export async function publishTask(page: Page, id: string): Promise<TaskRead> {
  return api<TaskRead>(page, 'PATCH', `/tasks/${id}`, { status: 'published' })
}

/** List duty shifts for a task. */
export async function listShifts(page: Page, eventId: string): Promise<ShiftRead[]> {
  const res = await api<{ items: ShiftRead[] }>(page, 'GET', `/shifts/?task_id=${eventId}&limit=200`)
  return res.items
}

/** Book a duty shift. */
export async function bookShift(page: Page, slotId: string): Promise<BookingRead> {
  return api<BookingRead>(page, 'POST', '/bookings/', { shift_id: slotId })
}

/** Cancel a booking. */
export async function cancelBooking(page: Page, bookingId: string): Promise<void> {
  await api(page, 'DELETE', `/bookings/${bookingId}`)
}
