import { ref } from 'vue'
import type { Ref } from 'vue'

import { client } from '@/client/client.gen'
import type {
  LoginRequest,
  RefreshResponse,
  RegisterRequest,
  TokenResponse,
  UserProfile,
} from '@/client/types.gen'

/**
 * The signed-in session: one access token in memory, one identity, one refresh
 * in flight at a time.
 *
 * Deliberately a module-level singleton rather than a Pinia store. The store
 * (`stores/auth.ts`) constructs `useAuthenticatedClient()`, which needs a token
 * for every request — so a store-backed token source would import itself in a
 * circle. Being module-level also means the token survives anything that
 * re-creates the Pinia instance, and can be read from a router guard before the
 * first component exists.
 *
 * The access token never touches `localStorage`: it lives for fifteen minutes
 * and is re-minted from an httpOnly refresh cookie that JavaScript cannot read.
 * Persisting it would only widen the blast radius of an XSS bug for no gain.
 */

/**
 * Refresh this long before the access token actually expires.
 *
 * A token that is technically still valid but about to lapse would be handed to
 * a request that then travels, queues and gets processed — so the margin covers
 * clock skew between browser and server plus the flight time of the request the
 * token was fetched for.
 */
const REFRESH_LEEWAY_MS = 60_000

/**
 * Breadcrumb saying a demo session ended without being asked to.
 *
 * `SandboxExpiredDialog` on the landing page reads and removes it. Exported so
 * the two halves cannot drift apart over a typo in a string literal.
 */
export const SANDBOX_ENDED_KEY = 'wirksam-sandbox-expired'

/**
 * The identity the shell renders from — name, avatar, verification badge.
 *
 * It is the backend's `UserProfile` with every field optional, because the
 * session knows who you are before the full profile has been loaded, plus the
 * `picture` URL that external identities used to carry. Keeping it structurally
 * compatible with `UserProfile` is what lets `stores/auth.ts` hand the same
 * object to components written against the old provider's `User`.
 */
export interface AuthUser extends Partial<UserProfile> {
  /** Absolute avatar URL, when the identity carries one of its own. */
  picture?: string | null
}

/** The token half of a `/auth/login`, `/auth/register` or `/auth/refresh` body. */
interface AccessTokenPayload {
  access_token: string
  expires_in: number
}

/** A session handed in from outside — the E2E bypass and unit tests. */
interface SessionPayload extends AccessTokenPayload {
  user?: AuthUser
}

export interface ClearOptions {
  /**
   * True when the visitor asked for this — a sign-out, or leaving the demo.
   *
   * Only an *unasked-for* teardown leaves the demo breadcrumb behind. Somebody
   * who just pressed "Exit demo" does not need the landing page to tell them
   * their demo is over.
   */
  deliberate?: boolean
}

export interface AuthSession {
  /** The current access token, or null when nobody is signed in. */
  accessToken: Ref<string | null>
  /** Epoch milliseconds at which `accessToken` stops being accepted. */
  expiresAt: Ref<number | null>
  /** Who is signed in. Writable — `stores/auth.ts` patches it after a profile save. */
  user: Ref<AuthUser | undefined>
  isAuthenticated: Ref<boolean>
  /** True until `bootstrap()` has settled. `App.vue` hides the router outlet meanwhile. */
  isLoading: Ref<boolean>
  bootstrap: () => Promise<void>
  login: (credentials: LoginRequest) => Promise<UserProfile>
  register: (registration: RegisterRequest) => Promise<UserProfile>
  logout: () => Promise<void>
  refresh: () => Promise<string | null>
  getAccessToken: () => Promise<string | null>
  setSession: (payload: SessionPayload) => void
  clear: (options?: ClearOptions) => void
}

const accessToken = ref<string | null>(null)
const expiresAt = ref<number | null>(null)
const user = ref<AuthUser | undefined>(undefined)
const isAuthenticated = ref(false)
// Starts true: the app boots into a silent refresh, and rendering the signed-out
// shell first would flash the landing page at everyone who is already signed in.
const isLoading = ref(true)

/** The single in-flight refresh, shared by every caller that arrives while it runs. */
let refreshPromise: Promise<string | null> | null = null
/** The one-shot session restore, so guards can await it instead of polling a flag. */
let bootstrapPromise: Promise<void> | null = null
/**
 * Bumped whenever the session is replaced or torn down.
 *
 * A refresh that was already in flight when someone logs out (or logs in as
 * somebody else) must not resurrect the session it started under, so its result
 * is dropped when the epoch it captured is no longer current.
 */
let epoch = 0

function applyToken(payload: AccessTokenPayload): void {
  accessToken.value = payload.access_token
  expiresAt.value = Date.now() + payload.expires_in * 1000
  isAuthenticated.value = true
}

/**
 * Remember that a demo session ended on its own.
 *
 * The sweep that reaps expired guests deletes the user row; `auth_sessions`
 * cascades with it, the next `/auth/refresh` answers 401, and that 401 lands in
 * `clear()` below. With no note left behind, the visitor is simply dumped on
 * the landing page mid-click with no explanation — so `SandboxExpiredDialog`
 * reads this and offers them another demo or a real account.
 *
 * `sessionStorage` rather than `localStorage`: the note belongs to the tab that
 * lost the demo and should die with it, not resurface a week later somewhere
 * else. Guarded because this module is loaded in Node by the unit tests, where
 * there is no `sessionStorage` at all, and because a browser set to block site
 * data throws on access rather than answering null.
 */
function rememberSandboxEnded(): void {
  try {
    sessionStorage.setItem(SANDBOX_ENDED_KEY, '1')
  } catch {
    // Losing the note costs an explanatory dialog and nothing else.
  }
}

/** Forget the session locally. Says nothing to the server — see `logout()`. */
function clear(options: ClearOptions = {}): void {
  // Necessarily before the identity below is dropped: `user` is the only thing
  // that knows this was a demo. The stale-refresh guard in `requestRefresh()`
  // has already decided whether this teardown is the current session's, so
  // reaching here at all means the note is about a session that really ended.
  if (!options.deliberate && user.value?.is_sandbox) rememberSandboxEnded()

  epoch += 1
  accessToken.value = null
  expiresAt.value = null
  user.value = undefined
  isAuthenticated.value = false
}

/**
 * Install a session obtained elsewhere.
 *
 * The E2E bypass uses this to look signed in without a round trip; the login and
 * register flows below use it for the token they were just handed.
 *
 * It clears `isLoading` as well, because a caller who hands in a whole session
 * has answered the question `bootstrap()` exists to ask. Without that, a bypass
 * that installs a session instead of booting one would leave `App.vue` spinning
 * on a flag nothing else ever lowers.
 */
function setSession(payload: SessionPayload): void {
  epoch += 1
  applyToken(payload)
  if (payload.user) user.value = payload.user
  isLoading.value = false
}

/**
 * Trade the refresh cookie for a new access token.
 *
 * Never throws: a 401 here is the ordinary answer to "is anybody signed in?",
 * and every caller wants to carry on as an anonymous visitor rather than see an
 * error. A network failure is treated the same way — the next call tries again.
 */
async function requestRefresh(): Promise<string | null> {
  const generation = epoch
  try {
    const response = await client.post<{ data: RefreshResponse }, unknown, true>({
      url: '/auth/refresh',
      throwOnError: true,
      // The refresh cookie is httpOnly and, in development, cross-origin
      // (:5555 to :8787). Without this it is simply never sent.
      withCredentials: true,
    })
    if (generation !== epoch) return null
    applyToken(response.data)
    return response.data.access_token
  } catch {
    if (generation !== epoch) return null
    clear()
    return null
  }
}

/**
 * Refresh the access token, coalescing concurrent callers onto one request.
 *
 * This deduplication is load-bearing, not an optimisation. The app fires many
 * requests in parallel on load; each refresh **rotates** the cookie, so a second
 * concurrent refresh presents a token the first one already replaced. The
 * backend reads that as token reuse — theft — and revokes every session the user
 * has. Without one shared promise, ordinary use forces people back to the login
 * screen.
 */
function refresh(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = requestRefresh().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

/**
 * Restore the session at app start: one `POST /auth/refresh`.
 *
 * 200 means signed in, 401 means anonymous — and 401 is the *normal* answer for
 * a first-time visitor, not an error worth surfacing. Idempotent, so a guard
 * that awaits it during the very first navigation joins the same attempt.
 */
function bootstrap(): Promise<void> {
  if (!bootstrapPromise) {
    isLoading.value = true
    bootstrapPromise = (async () => {
      try {
        await refresh()
      } finally {
        // `App.vue` renders a spinner *instead of* the router outlet while this
        // is true. A bootstrap that never resolves it shows a spinner forever,
        // on every route, with no way out.
        isLoading.value = false
      }
    })()
  }
  return bootstrapPromise
}

/**
 * The token to put on the next request, refreshed when it is about to lapse.
 *
 * Returns null for an anonymous visitor rather than throwing, and without
 * spending a request: `useAuthenticatedClient` turns that into its own error.
 */
async function getAccessToken(): Promise<string | null> {
  // A call that lands mid-boot waits for the restore rather than racing it into
  // a second refresh with the same cookie.
  if (bootstrapPromise) await bootstrapPromise

  if (
    accessToken.value !== null &&
    expiresAt.value !== null &&
    Date.now() < expiresAt.value - REFRESH_LEEWAY_MS
  ) {
    return accessToken.value
  }

  if (!isAuthenticated.value) return null
  return await refresh()
}

/**
 * Sign in with a password.
 *
 * Errors propagate: `main.ts` sets `throwOnError`, so wrong credentials arrive
 * as a thrown `AxiosError` carrying the `auth.invalid_credentials` problem code
 * for the view to translate.
 */
async function login(credentials: LoginRequest): Promise<UserProfile> {
  const response = await client.post<{ data: TokenResponse }, unknown, true>({
    url: '/auth/login',
    body: credentials,
    throwOnError: true,
    withCredentials: true,
  })
  setSession(response.data)
  return response.data.user
}

/** Create an account and sign straight in on the same response. */
async function register(registration: RegisterRequest): Promise<UserProfile> {
  const response = await client.post<{ data: TokenResponse }, unknown, true>({
    url: '/auth/register',
    body: registration,
    throwOnError: true,
    withCredentials: true,
  })
  setSession(response.data)
  return response.data.user
}

/**
 * Revoke the session server-side and forget it locally.
 *
 * The local half runs even when the call fails: the cookie may already be gone
 * (expired, revoked from another device, account just deleted), and none of
 * those are reasons to leave someone looking signed in.
 */
async function logout(): Promise<void> {
  try {
    await client.post<unknown, unknown, true>({
      url: '/auth/logout',
      throwOnError: true,
      withCredentials: true,
    })
  } catch {
    // Deliberately swallowed — see above.
  } finally {
    clear({ deliberate: true })
  }
}

export const authSession: AuthSession = {
  accessToken,
  expiresAt,
  user,
  isAuthenticated,
  isLoading,
  bootstrap,
  login,
  register,
  logout,
  refresh,
  getAccessToken,
  setSession,
  clear,
}
