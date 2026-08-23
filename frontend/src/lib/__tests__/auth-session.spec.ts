import { describe, expect, it, vi } from 'vitest'

import type { AuthSession } from '../auth-session'

/**
 * `auth-session` is a module-level singleton, so state leaks between cases
 * unless the module itself is thrown away. Every scenario therefore calls
 * `loadSession()`, which resets the module registry and re-imports — the same
 * approach `useChangelogStatus.spec.ts` takes for its module-scoped state.
 *
 * The only thing stubbed is the generated HTTP client. Everything else — the
 * refs, the in-flight-promise bookkeeping, the expiry arithmetic — is the real
 * implementation, because that bookkeeping *is* what these tests are about.
 */

const post = vi.hoisted(() => vi.fn())

vi.mock('../../client/client.gen', () => ({ client: { post } }))

async function loadSession(): Promise<AuthSession> {
  vi.resetModules()
  post.mockReset()
  const { authSession } = await import('../auth-session')
  return authSession
}

/** The body shape of `/auth/refresh`, as the axios client hands it over. */
function tokenResponse(accessToken: string, expiresIn = 900) {
  return { data: { access_token: accessToken, token_type: 'bearer', expires_in: expiresIn } }
}

function sessionResponse(accessToken: string, email = 'someone@example.com') {
  return {
    data: {
      access_token: accessToken,
      token_type: 'bearer',
      expires_in: 900,
      user: { id: 'user-1', sub: 'local|abc', email, name: 'Someone' },
    },
  }
}

/** A promise whose settlement this test controls, to hold a request open. */
function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

/** What the generated client throws for a 401 — only its rejection matters here. */
function unauthorized() {
  return Object.assign(new Error('Request failed with status code 401'), {
    response: { status: 401 },
  })
}

describe('auth-session', () => {
  describe('bootstrap', () => {
    it('signs the visitor in when the refresh cookie is still valid', async () => {
      const session = await loadSession()
      post.mockResolvedValue(tokenResponse('restored'))

      await session.bootstrap()

      expect(session.isAuthenticated.value).toBe(true)
      expect(session.accessToken.value).toBe('restored')
      expect(session.isLoading.value).toBe(false)
      expect(post).toHaveBeenCalledWith(
        expect.objectContaining({ url: '/auth/refresh', withCredentials: true }),
      )
    })

    it('leaves a first-time visitor anonymous rather than erroring', async () => {
      const session = await loadSession()
      post.mockRejectedValue(unauthorized())

      await expect(session.bootstrap()).resolves.toBeUndefined()

      expect(session.isAuthenticated.value).toBe(false)
      expect(session.accessToken.value).toBeNull()
      expect(session.user.value).toBeUndefined()
    })

    it('resolves the loading flag whichever way the refresh goes', async () => {
      const session = await loadSession()
      const pending = deferred<unknown>()
      post.mockReturnValue(pending.promise)

      expect(session.isLoading.value).toBe(true)
      const booting = session.bootstrap()
      expect(session.isLoading.value).toBe(true)

      pending.reject(unauthorized())
      await booting

      // App.vue renders a spinner instead of the router outlet while this is
      // true, so a bootstrap that fails to clear it renders no route at all.
      expect(session.isLoading.value).toBe(false)
    })

    it('restores the session once however many callers ask for it', async () => {
      const session = await loadSession()
      post.mockResolvedValue(tokenResponse('restored'))

      await Promise.all([session.bootstrap(), session.bootstrap(), session.bootstrap()])

      expect(post).toHaveBeenCalledTimes(1)
    })
  })

  describe('setSession', () => {
    it('installs a session without a round trip and stops the app waiting on one', async () => {
      const session = await loadSession()

      session.setSession({ access_token: 'handed-in', expires_in: 900, user: { name: 'Ada' } })

      expect(session.isAuthenticated.value).toBe(true)
      expect(session.user.value?.name).toBe('Ada')
      // The E2E bypass installs a session instead of booting one; leaving the
      // loading flag raised would spin App.vue forever.
      expect(session.isLoading.value).toBe(false)
      expect(post).not.toHaveBeenCalled()
    })
  })

  describe('getAccessToken', () => {
    it('hands back the token it already has while it is still fresh', async () => {
      const session = await loadSession()
      session.setSession({ access_token: 'fresh', expires_in: 900 })

      await expect(session.getAccessToken()).resolves.toBe('fresh')
      expect(post).not.toHaveBeenCalled()
    })

    it('refreshes a token that is inside the expiry margin but not yet expired', async () => {
      const session = await loadSession()
      // Still valid for 30s — and therefore already too close to the edge to
      // hand to a request that has to travel and queue before it is checked.
      session.setSession({ access_token: 'stale', expires_in: 30 })
      post.mockResolvedValue(tokenResponse('rotated'))

      await expect(session.getAccessToken()).resolves.toBe('rotated')
      expect(session.accessToken.value).toBe('rotated')
      expect(post).toHaveBeenCalledTimes(1)
    })

    it('makes exactly one refresh request for concurrent callers', async () => {
      const session = await loadSession()
      session.setSession({ access_token: 'stale', expires_in: 30 })
      const pending = deferred<unknown>()
      post.mockReturnValue(pending.promise)

      // The app fires many requests in parallel on load. Refreshing rotates the
      // cookie, so a second concurrent refresh would present a token the first
      // already replaced — which the backend reads as theft and answers by
      // revoking every session this user has.
      const tokens = Promise.all(Array.from({ length: 8 }, () => session.getAccessToken()))
      await Promise.resolve()
      pending.resolve(tokenResponse('rotated'))

      await expect(tokens).resolves.toEqual(Array.from({ length: 8 }, () => 'rotated'))
      expect(post).toHaveBeenCalledTimes(1)
    })

    it('waits for an in-flight bootstrap instead of racing it', async () => {
      const session = await loadSession()
      const pending = deferred<unknown>()
      post.mockReturnValue(pending.promise)

      const booting = session.bootstrap()
      const token = session.getAccessToken()
      pending.resolve(tokenResponse('restored'))
      await booting

      await expect(token).resolves.toBe('restored')
      expect(post).toHaveBeenCalledTimes(1)
    })

    it('returns null for an anonymous visitor without spending a request', async () => {
      const session = await loadSession()

      await expect(session.getAccessToken()).resolves.toBeNull()
      expect(post).not.toHaveBeenCalled()
    })

    it('clears the session when the refresh is refused', async () => {
      const session = await loadSession()
      session.setSession({ access_token: 'stale', expires_in: 30, user: { name: 'Someone' } })
      post.mockRejectedValue(unauthorized())

      await expect(session.getAccessToken()).resolves.toBeNull()

      expect(session.isAuthenticated.value).toBe(false)
      expect(session.accessToken.value).toBeNull()
      expect(session.expiresAt.value).toBeNull()
      expect(session.user.value).toBeUndefined()
    })

    it('refreshes again on the next call once the shared promise has settled', async () => {
      const session = await loadSession()
      session.setSession({ access_token: 'stale', expires_in: 30 })
      post.mockResolvedValue(tokenResponse('rotated', 30))

      await session.getAccessToken()
      await session.getAccessToken()

      expect(post).toHaveBeenCalledTimes(2)
    })
  })

  describe('login and register', () => {
    it('installs the session the login response carries', async () => {
      const session = await loadSession()
      post.mockResolvedValue(sessionResponse('minted', 'ada@example.com'))

      const profile = await session.login({ email: 'ada@example.com', password: 'hunter2hunter2' })

      expect(profile.email).toBe('ada@example.com')
      expect(session.isAuthenticated.value).toBe(true)
      expect(session.accessToken.value).toBe('minted')
      expect(session.user.value?.email).toBe('ada@example.com')
      expect(post).toHaveBeenCalledWith(
        expect.objectContaining({
          url: '/auth/login',
          body: { email: 'ada@example.com', password: 'hunter2hunter2' },
          withCredentials: true,
        }),
      )
    })

    it('lets bad credentials throw so the view can translate the problem code', async () => {
      const session = await loadSession()
      post.mockRejectedValue(unauthorized())

      await expect(
        session.login({ email: 'ada@example.com', password: 'wrong-password' }),
      ).rejects.toThrow()
      expect(session.isAuthenticated.value).toBe(false)
    })

    it('signs a new account straight in on the register response', async () => {
      const session = await loadSession()
      post.mockResolvedValue(sessionResponse('minted', 'new@example.com'))

      const profile = await session.register({
        email: 'new@example.com',
        password: 'hunter2hunter2',
        name: 'New Person',
      })

      expect(profile.email).toBe('new@example.com')
      expect(session.isAuthenticated.value).toBe(true)
      expect(post).toHaveBeenCalledWith(
        expect.objectContaining({ url: '/auth/register', withCredentials: true }),
      )
    })
  })

  describe('logout', () => {
    it('revokes the session server-side and forgets it locally', async () => {
      const session = await loadSession()
      post.mockResolvedValue(sessionResponse('minted'))
      await session.login({ email: 'ada@example.com', password: 'hunter2hunter2' })
      post.mockResolvedValue({ data: undefined })

      await session.logout()

      expect(post).toHaveBeenLastCalledWith(
        expect.objectContaining({ url: '/auth/logout', withCredentials: true }),
      )
      expect(session.isAuthenticated.value).toBe(false)
      expect(session.accessToken.value).toBeNull()
      expect(session.user.value).toBeUndefined()
    })

    it('signs out locally even when the server call fails', async () => {
      const session = await loadSession()
      session.setSession({ access_token: 'minted', expires_in: 900, user: { name: 'Someone' } })
      post.mockRejectedValue(new Error('network down'))

      await expect(session.logout()).resolves.toBeUndefined()

      expect(session.isAuthenticated.value).toBe(false)
      expect(session.accessToken.value).toBeNull()
    })
  })

  describe('a refresh that outlives the session it started under', () => {
    it('is discarded when the session was cleared while it was in flight', async () => {
      const session = await loadSession()
      session.setSession({ access_token: 'stale', expires_in: 30 })
      const pending = deferred<unknown>()
      post.mockReturnValue(pending.promise)

      const token = session.getAccessToken()
      session.clear()
      pending.resolve(tokenResponse('too-late'))

      await expect(token).resolves.toBeNull()
      expect(session.isAuthenticated.value).toBe(false)
      expect(session.accessToken.value).toBeNull()
    })

    it('does not tear down a newer session when it fails', async () => {
      const session = await loadSession()
      session.setSession({ access_token: 'stale', expires_in: 30 })
      const pending = deferred<unknown>()
      post.mockReturnValue(pending.promise)

      const token = session.getAccessToken()
      session.setSession({ access_token: 'newer', expires_in: 900 })
      pending.reject(unauthorized())

      await expect(token).resolves.toBeNull()
      expect(session.isAuthenticated.value).toBe(true)
      expect(session.accessToken.value).toBe('newer')
    })
  })
})
