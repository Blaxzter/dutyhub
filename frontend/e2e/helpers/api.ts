/**
 * Shared E2E API helpers — used by both single-user and multi-user test files.
 */

import type { Page } from '@playwright/test'

export const API = process.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

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
  return page.evaluate(
    async ({ url, method, body, token }) => {
      const res = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: body ? JSON.stringify(body) : undefined,
      })
      if (res.status === 204) return null
      return res.json()
    },
    { url: `${API}${path}`, method, body, token },
  ) as Promise<T>
}

export interface EventGroupRead {
  id: string
  name: string
  status: string
  start_date: string
  end_date: string
}

/** Create an event group (draft or published). Admin token required. */
export async function createGroup(
  page: Page,
  name: string,
  status: 'draft' | 'published' = 'published',
): Promise<EventGroupRead> {
  const draft = await api<EventGroupRead>(page, 'POST', '/event-groups/', {
    name,
    start_date: '2026-06-10',
    end_date: '2026-06-14',
  })
  if (status === 'draft') return draft
  return api<EventGroupRead>(page, 'PATCH', `/event-groups/${draft.id}`, { status: 'published' })
}

/** Delete an event group. Admin token required. */
export async function deleteGroup(page: Page, id: string): Promise<void> {
  await api(page, 'DELETE', `/event-groups/${id}`)
}

/** Remove the current user's availability for a group (best-effort). */
export async function clearAvailability(page: Page, groupId: string): Promise<void> {
  await api(page, 'DELETE', `/event-groups/${groupId}/availability/me`)
}
