/**
 * Helpers for the handful of specs that sign in for real.
 *
 * The rest of the suite takes the `X-Test-User-Email` shortcut (see
 * `e2e/fixtures.ts` for why it has to). These helpers exist for the specs that
 * must not: the sign-in, registration and password-recovery screens are the
 * first thing a new volunteer meets, and a bypass that skips them would leave
 * them untested everywhere.
 *
 * Accounts created here are *not* cleaned up by `POST /testing/reset`. That
 * endpoint deletes users whose subject starts with `test|`, and an account that
 * registered with a password gets `local|…` like any real one — which is the
 * point, since these specs want the real path. Every spec therefore deletes
 * what it made, and derives its address from `testInfo` so the deletion can be
 * repeated on the next run if a crash ever stops it happening.
 */
import type { Page, TestInfo } from '@playwright/test'

import { serverApi, serverApiRaw } from '../fixtures.js'

/**
 * The password every registered test account is given.
 *
 * Long enough for `PASSWORD_MIN_LENGTH` (8) and unremarkable otherwise — it
 * guards nothing, on accounts that live for one test against a database that is
 * wiped between runs.
 */
export const AUTH_TEST_PASSWORD = 'e2e-Passw0rd'

/** A password that is valid in shape but belongs to nobody. */
export const AUTH_WRONG_PASSWORD = 'e2e-Wr0ngPass'

/** The shape `GET /users/` answers with, narrowed to the field we use. */
interface UserSearchResponse {
  items: { id: string; email: string | null }[]
}

/** What `POST /auth/register` and `POST /auth/login` answer with. */
interface TokenResponse {
  access_token: string
  user: { id: string; email: string | null }
}

/**
 * A unique, *reproducible* address for one test.
 *
 * `testInfo.testId` is a hex digest of project + file + title: unique per test
 * and stable across retries, so teardown after a failed attempt clears the way
 * for the retry that follows. The worker index keeps two workers running the
 * same test (shards, retries) apart. Trimmed to its tail so the local part
 * stays comfortably inside the 64 characters `EmailStr` allows.
 */
export function authTestEmail(testInfo: TestInfo, seq = 1): string {
  const id = testInfo.testId.replace(/[^a-z0-9]/gi, '').slice(-24)
  const suffix = seq > 1 ? `-${seq}` : ''
  return `authtest-${id}-w${testInfo.workerIndex}${suffix}@test.example.com`
}

/**
 * Two browser preferences the fixtures normally plant, for pages that have no
 * fixture because nobody is signed in.
 *
 * Without the locale pin a German-configured machine renders a German UI and
 * every assertion on English copy fails; without the changelog pin the "What's
 * New" dialog can open over the form. Must be called before the first `goto`.
 */
export async function pinBrowserPreferences(page: Page): Promise<void> {
  await page.addInitScript(() => {
    localStorage.setItem('locale', 'en')
    localStorage.setItem('wirksam-last-seen-changelog', '99.99.99')
  })
}

/**
 * Create an account through the real endpoint, with a real password.
 *
 * Node-side rather than through the browser, so the specs that need an existing
 * account to sign in *as* do not have to register one through the UI first.
 * The refresh cookie the response sets is discarded with the `fetch` that
 * received it — only the account matters here.
 */
export async function registerAccount(
  email: string,
  name: string,
  password: string = AUTH_TEST_PASSWORD,
): Promise<string> {
  const created = await serverApi<TokenResponse>('POST', '/auth/register', '', {
    email,
    name,
    password,
    preferred_language: 'en',
  })
  return created.user.id
}

/**
 * Delete the account with this address, if there still is one.
 *
 * Runs as the worker's admin, who is a platform superadmin. A missing account
 * is the expected outcome of a test that deleted its own, so it is not an
 * error — and neither is a teardown that runs twice.
 */
export async function deleteAccount(adminEmail: string, email: string): Promise<void> {
  const found = await serverApiRaw('GET', `/users/?q=${encodeURIComponent(email)}`, adminEmail)
  if (!found.ok) return

  const items = (found.body as UserSearchResponse).items ?? []
  // `q` is a search, not a lookup: it matches on name as well, and on
  // substrings. Only an exact address is ours to delete.
  const match = items.find((item) => item.email?.toLowerCase() === email.toLowerCase())
  if (!match) return

  await serverApiRaw('DELETE', `/users/${match.id}`, adminEmail)
}
