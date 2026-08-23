/**
 * Playwright fixtures that sign a browser in without a password.
 *
 * Requires the backend to run with TESTING=true so that:
 * - POST /testing/seed creates test users directly in the DB
 * - POST /testing/reset cleans up test users
 * - the X-Test-User-Email header names the caller instead of a bearer token
 *
 * The bypass outlived Auth0 on purpose. In CI the browser origin and
 * `VITE_API_URL=http://backend:8787` are genuinely cross-site, so the
 * `SameSite=Lax` refresh cookie a real login depends on is silently dropped —
 * a suite built on real logins would pass on a developer's machine and fail in
 * CI. The real forms are exercised by `e2e/tests/auth/`, which signs in
 * anonymously and gets away with it because login and registration answer with
 * the access token in the body — only a *reload* would need the cookie, and
 * those specs never reload. Everything else takes the shortcut.
 *
 * Two halves, and neither works alone: the page believes it is signed in
 * because `src/testing/fake-session.ts` installs a session from the
 * `wirksam-e2e-user` localStorage entry seeded below, and the *server* believes
 * it because every `/api/v1/**` request carries the header injected by
 * `setupApiInterception`.
 *
 * Each parallel Playwright worker gets its own admin and member user,
 * so tests never interfere with each other.
 *
 * Those worker users are shared by every test the worker runs, so a test that
 * deletes or deactivates one would poison all the later ones. Destructive
 * flows therefore use the *disposable* fixtures further down: a fresh user per
 * test that is deleted again in teardown.
 */
import {
  type BrowserContext,
  type Page,
  type TestInfo,
  test as base,
  expect,
} from '@playwright/test'

const API = process.env.VITE_API_URL ?? 'http://localhost:8787/api/v1'

export interface TestUser {
  email: string
  name: string
  roles: string[]
}

/** A user seeded via POST /testing/seed, including its database id. */
export interface SeededUser extends TestUser {
  id: string
}

/** How a disposable user should be seeded. */
export interface DisposableUserOptions {
  /** Roles to grant, e.g. `['admin']`. Defaults to a plain member. */
  roles?: string[]
  /** `false` seeds a suspended (inactive) account. Defaults to `true`. */
  isActive?: boolean
  /**
   * `false` leaves the account in no event at all — the shape of a genuine
   * first sign-in. Such a user has no selected event, so the router sends
   * them to the picker instead of the dashboard. Defaults to `true`.
   */
  joinWorkerEvent?: boolean
}

/** A throwaway user that only lives for the duration of one test. */
export interface DisposableUser extends SeededUser {
  isActive: boolean
}

/** Seeds an extra disposable user; cleaned up with the rest at teardown. */
export type SeedDisposableUser = (options?: DisposableUserOptions) => Promise<DisposableUser>

export interface WorkerEvent {
  id: string
  name: string
  start_date: string
  end_date: string
}

/** ISO date (YYYY-MM-DD) offset from today. */
function isoDateOffset(daysFromNow: number): string {
  const d = new Date()
  d.setDate(d.getDate() + daysFromNow)
  return d.toISOString().slice(0, 10)
}

export interface RawApiResponse {
  status: number
  ok: boolean
  /** Parsed JSON when the response had a JSON body, otherwise the raw text. */
  body: unknown
}

/**
 * Node-side fetch helper that resolves for *any* status instead of throwing.
 * Destructive tests need to assert on 401/404 answers, which `serverApi` would
 * turn into an exception.
 */
export async function serverApiRaw(
  method: string,
  path: string,
  email: string,
  body?: object,
): Promise<RawApiResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (email) headers['X-Test-User-Email'] = email
  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  const text = await res.text()
  let parsed: unknown = text
  try {
    parsed = JSON.parse(text)
  } catch {
    // Empty or non-JSON body (204s, plain-text errors) — keep the raw text.
  }
  return { status: res.status, ok: res.ok, body: parsed }
}

/** Node-side fetch helper. Uses X-Test-User-Email bypass (TESTING=true backend). */
export async function serverApi<T>(
  method: string,
  path: string,
  email: string,
  body?: object,
): Promise<T> {
  const res = await serverApiRaw(method, path, email, body)
  if (!res.ok) {
    throw new Error(`API ${method} ${path} failed: ${res.status} ${JSON.stringify(res.body)}`)
  }
  if (res.status === 204) return null as T
  return res.body as T
}

/**
 * Put a user into an event, through the real invitation endpoints.
 *
 * Membership is what grants access now, so nearly every fixture needs it.
 * Deliberately uses the production API rather than a test-only shortcut, so
 * the invite → accept path is exercised on every run.
 */
export async function joinEvent(
  eventId: string,
  inviterEmail: string,
  inviteeEmail: string,
  role: 'admin' | 'member' = 'member',
): Promise<void> {
  const invitation = await serverApi<{ token: string }>(
    'POST',
    `/events/${eventId}/invitations`,
    inviterEmail,
    { email: inviteeEmail, role },
  )
  await serverApi('POST', `/invitations/${invitation.token}/accept`, inviteeEmail)
}

/**
 * Tell the SPA who it is signed in as, before any of its own code runs.
 *
 * `src/testing/fake-session.ts` reads this entry and installs a session from
 * it, so no token is minted and no request is made. Only `email` and `name` are
 * written — everything else on the identity is derived or defaulted there, and
 * the address is the only field that has to agree with the one the header
 * bypass sends, because that is what the server resolves the caller by.
 *
 * The other two keys decide whether the suite can see the app at all: the
 * "What's New" dialog opens over the whole UI the first time a browser meets a
 * new version and swallows every click behind it, and specs assert English copy
 * that a German-configured machine would otherwise never render.
 */
function setupAuthBypass(context: BrowserContext, user: TestUser) {
  return context.addInitScript(
    (userInfo) => {
      localStorage.setItem(
        'wirksam-e2e-user',
        JSON.stringify({ email: userInfo.email, name: userInfo.name }),
      )
      localStorage.setItem('wirksam-last-seen-changelog', '99.99.99')
      localStorage.setItem('locale', 'en')
    },
    { email: user.email, name: user.name },
  )
}

/**
 * Intercept all API requests on a page and add the X-Test-User-Email header.
 * Must be called on the page (not context) so cross-origin requests are caught.
 */
function setupApiInterception(page: Page, email: string) {
  return page.route('**/api/v1/**', (route) => {
    const headers = {
      ...route.request().headers(),
      'x-test-user-email': email,
    }
    return route.continue({ headers })
  })
}

/**
 * Seed a test user via the backend testing API (no auth required).
 *
 * Idempotent — re-seeding an existing address updates name/roles/is_active in
 * place and leaves everything else (notably `selected_event_id`) alone, which
 * is how destructive tests push a user back into the pending state.
 */
export async function seedUser(
  email: string,
  name: string,
  roles: string[],
  isActive = true,
): Promise<SeededUser> {
  const resp = await fetch(`${API}/testing/seed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, name, roles, is_active: isActive, preferred_language: 'en' }),
  })
  if (!resp.ok) {
    throw new Error(`Failed to seed user ${email}: ${resp.status} ${await resp.text()}`)
  }
  const seeded = (await resp.json()) as { id: string }
  return { id: seeded.id, email, name, roles }
}

/**
 * Point a test user's `selected_event_id` at an event, so the router guard
 * doesn't bounce authenticated pages to /select-event.
 *
 * Occasionally the first read-after-write 404s under parallel worker load;
 * a single short retry papers over it without masking real failures.
 */
async function setSelectedEvent(email: string, eventId: string): Promise<void> {
  const body = { selected_event_id: eventId }
  try {
    await serverApi('PUT', '/users/me/selected-event', email, body)
  } catch (err) {
    if (String(err).includes('404')) {
      await new Promise((r) => setTimeout(r, 250))
      await serverApi('PUT', '/users/me/selected-event', email, body)
    } else {
      throw err
    }
  }
}

/**
 * Build the address for a disposable user.
 *
 * `testInfo.testId` is a hex digest of project + file + title: unique per test,
 * stable across retries, and made only of characters an email local part
 * accepts. It is trimmed to its tail so the address stays comfortably inside
 * the 64-character limit `EmailStr` enforces on the backend. The worker index
 * keeps two workers running the same test (shards, retries) apart, and `seq`
 * separates several disposables seeded inside a single test.
 */
function disposableEmail(testInfo: TestInfo, seq: number): string {
  const id = testInfo.testId.replace(/[^a-z0-9]/gi, '').slice(-24)
  const suffix = seq > 1 ? `-${seq}` : ''
  return `disposable-${id}-w${testInfo.workerIndex}${suffix}@test.example.com`
}

// ── Fixtures ──────────────────────────────────────────────────────────────────

export const test = base.extend<
  // Test-scoped fixtures
  {
    adminPage: Page
    memberPage: Page
    disposableUserOptions: DisposableUserOptions
    seedDisposableUser: SeedDisposableUser
    disposableUser: DisposableUser
    disposablePage: Page
  },
  // Worker-scoped fixtures
  { adminUser: TestUser; memberUser: TestUser; workerEvent: WorkerEvent }
>({
  // Worker-scoped: each parallel worker seeds its own admin user
  adminUser: [
    async ({}, use, workerInfo) => {
      const email = `admin-worker-${workerInfo.workerIndex}@test.example.com`
      const name = `Test Admin ${workerInfo.workerIndex}`
      await seedUser(email, name, ['admin'])
      await use({ email, name, roles: ['admin'] })
    },
    { scope: 'worker' },
  ],

  // Worker-scoped: each parallel worker seeds its own member user
  memberUser: [
    async ({}, use, workerInfo) => {
      const email = `member-worker-${workerInfo.workerIndex}@test.example.com`
      const name = `Test Member ${workerInfo.workerIndex}`
      await seedUser(email, name, [])
      await use({ email, name, roles: [] })
    },
    { scope: 'worker' },
  ],

  // Worker-scoped: each parallel worker seeds its own published event and
  // points both the admin and member user at it as their selected_event_id,
  // so the router guard doesn't bounce authenticated pages to /select-event.
  workerEvent: [
    async ({ adminUser, memberUser }, use, workerInfo) => {
      // Public so the Discover tab has something to show, and so the event can
      // be featured. Creating it makes adminUser its owner automatically.
      const event = await serverApi<WorkerEvent>('POST', '/events/', adminUser.email, {
        name: `E2E Worker Event ${workerInfo.workerIndex}`,
        status: 'published',
        visibility: 'public',
        start_date: isoDateOffset(1),
        end_date: isoDateOffset(60),
      })
      await joinEvent(event.id, adminUser.email, memberUser.email, 'member')
      await setSelectedEvent(adminUser.email, event.id)
      await setSelectedEvent(memberUser.email, event.id)
      await use(event)
    },
    { scope: 'worker' },
  ],

  // Test-scoped: a page pre-configured as the admin user
  adminPage: async ({ browser, adminUser, workerEvent }, use) => {
    void workerEvent // ensure event + selected_event_id are set before the page boots
    const context = await browser.newContext()
    // The build flag alone does nothing: `main.ts` and the router both also
    // require this cookie before they stand the real session flow down.
    await context.addCookies([{ name: 'e2e_bypass', value: '1', domain: 'localhost', path: '/' }])
    await setupAuthBypass(context, adminUser)
    const page = await context.newPage()
    await setupApiInterception(page, adminUser.email)
    await page.goto('/app/home')
    await page.getByTestId('page-heading').waitFor({ timeout: 15_000 })
    await use(page)
    await context.close()
  },

  // Test-scoped: a page pre-configured as the member user
  memberPage: async ({ browser, memberUser, workerEvent }, use) => {
    void workerEvent
    const context = await browser.newContext()
    await context.addCookies([{ name: 'e2e_bypass', value: '1', domain: 'localhost', path: '/' }])
    await setupAuthBypass(context, memberUser)
    const page = await context.newPage()
    await setupApiInterception(page, memberUser.email)
    await page.goto('/app/home')
    await page.getByTestId('page-heading').waitFor({ timeout: 15_000 })
    await use(page)
    await context.close()
  },

  // ── Disposable users ────────────────────────────────────────────────────
  // Test-scoped throwaway accounts for flows that destroy the user they run
  // as (self-deletion, deactivation, role changes, approval). Never point a
  // destructive action at adminUser/memberUser — those are shared by every
  // test in the worker.

  /**
   * Shape of the `disposableUser` account. Override per file or describe block:
   *
   *   test.use({ disposableUserOptions: { roles: ['admin'], isActive: false } })
   *
   * This is an option fixture rather than an argument to a factory because
   * `disposablePage` has to build its browser context from the *same* account,
   * and a fixture can only depend on another fixture. `seedDisposableUser` is
   * still exposed for tests that need a second throwaway account.
   */
  disposableUserOptions: [{}, { option: true }],

  /** Factory for extra disposable users; all of them are deleted in teardown. */
  seedDisposableUser: async ({ adminUser, workerEvent }, use, testInfo) => {
    const created: DisposableUser[] = []
    let seq = 0

    const seed: SeedDisposableUser = async (options = {}) => {
      seq += 1
      const roles = options.roles ?? []
      const isActive = options.isActive ?? true
      const joinWorkerEvent = options.joinWorkerEvent ?? true
      const email = disposableEmail(testInfo, seq)
      const name = `Disposable User ${testInfo.workerIndex}-${seq}`
      // Always seed active first: PUT /users/me/selected-event rejects inactive
      // users, and without a selection the router bounces every authenticated
      // page to /select-event. Re-seeding flips is_active without touching the
      // selection, so suspended users still land where the test expects.
      const seeded = await seedUser(email, name, roles, true)
      if (joinWorkerEvent) {
        // Selecting an event requires membership in it.
        await joinEvent(workerEvent.id, adminUser.email, email, 'member')
        await setSelectedEvent(email, workerEvent.id)
      }
      if (!isActive) {
        await seedUser(email, name, roles, false)
      }
      const user: DisposableUser = { ...seeded, isActive }
      created.push(user)
      return user
    }

    await use(seed)

    // Teardown deletes each account as the worker admin. A 404 means the test
    // already deleted it — which is exactly what some of these tests do — so it
    // must be tolerated. POST /testing/reset is deliberately NOT used: it wipes
    // every test user and would destroy the other workers' fixtures.
    for (const user of created) {
      const res = await serverApiRaw('DELETE', `/users/${user.id}`, adminUser.email)
      if (!res.ok && res.status !== 404) {
        throw new Error(
          `Failed to clean up disposable user ${user.email}: ` +
            `${res.status} ${JSON.stringify(res.body)}`,
        )
      }
    }
  },

  /** Test-scoped: a freshly seeded user that this test may safely destroy. */
  disposableUser: async ({ seedDisposableUser, disposableUserOptions }, use) => {
    await use(await seedDisposableUser(disposableUserOptions))
  },

  /** Test-scoped: a page pre-configured as the disposable user. */
  disposablePage: async ({ browser, disposableUser }, use) => {
    const context = await browser.newContext()
    await context.addCookies([{ name: 'e2e_bypass', value: '1', domain: 'localhost', path: '/' }])
    await setupAuthBypass(context, disposableUser)
    const page = await context.newPage()
    await setupApiInterception(page, disposableUser.email)
    // An account in no event is redirected to the picker rather than the
    // dashboard; both render a `page-heading`, so one wait covers either.
    await page.goto('/app/home')
    await page.getByTestId('page-heading').waitFor({ timeout: 15_000 })
    await use(page)
    await context.close()
  },
})

export { expect }

// Re-export API helpers with test-user support
export { API }

/** Make an authenticated API call using X-Test-User-Email header. */
export async function testApi<T = unknown>(
  page: Page,
  method: string,
  path: string,
  body?: object,
  testEmail?: string,
): Promise<T> {
  const email = testEmail ?? ''
  return page.evaluate(
    async ({ url, method, body, email }) => {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }
      if (email) {
        headers['X-Test-User-Email'] = email
      }
      const res = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      })
      if (res.status === 204) return null
      return res.json()
    },
    { url: `${API}${path}`, method, body, email },
  ) as Promise<T>
}
