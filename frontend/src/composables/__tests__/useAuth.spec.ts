import { isRef } from 'vue'

import { describe, expect, it, vi } from 'vitest'
import type { RouteLocationNormalized } from 'vue-router'

/**
 * `useAuth` is a thin façade over the `auth-session` singleton, and the thing
 * worth testing is exactly that thinness: that it hands back the *same* refs
 * rather than copies or computeds, and that navigation goes through the router
 * without importing it at module scope.
 *
 * So the session module is left real (only the generated HTTP client is
 * stubbed) and the router is replaced with a spy. Both modules are re-imported
 * after `vi.resetModules()` in the same generation, so the composable and the
 * session the test asserts against are the same instance.
 */

const post = vi.hoisted(() => vi.fn())
const push = vi.hoisted(() => vi.fn())

vi.mock('../../client/client.gen', () => ({ client: { post } }))
vi.mock('@/router', () => ({ default: { push } }))

async function load() {
  vi.resetModules()
  post.mockReset()
  push.mockReset()
  push.mockResolvedValue(undefined)
  const composable = await import('../useAuth')
  const { authSession } = await import('@/lib/auth-session')
  return { ...composable, authSession }
}

function tokenResponse(accessToken: string) {
  return { data: { access_token: accessToken, token_type: 'bearer', expires_in: 900 } }
}

function unauthorized() {
  return Object.assign(new Error('Request failed with status code 401'), {
    response: { status: 401 },
  })
}

/** Only `fullPath` is read by the guard. */
function destination(fullPath: string) {
  return { fullPath } as unknown as RouteLocationNormalized
}

describe('useAuth', () => {
  describe('the reactive surface', () => {
    it('exposes the session refs themselves', async () => {
      const { useAuth, authSession } = await load()
      const auth = useAuth()

      // Pinia's `reactive()` unwraps nested refs on access, which is what lets
      // the router read `authStore.session.isLoading` with no `.value`. A plain
      // boolean here makes that read a constant.
      expect(isRef(auth.isLoading)).toBe(true)
      expect(isRef(auth.isAuthenticated)).toBe(true)
      expect(isRef(auth.user)).toBe(true)
      expect(auth.isLoading).toBe(authSession.isLoading)
      expect(auth.isAuthenticated).toBe(authSession.isAuthenticated)
    })

    it('tracks the session as it changes', async () => {
      const { useAuth, authSession } = await load()
      const auth = useAuth()

      expect(auth.isAuthenticated.value).toBe(false)
      authSession.setSession({ access_token: 'minted', expires_in: 900, user: { name: 'Ada' } })

      expect(auth.isAuthenticated.value).toBe(true)
      expect(auth.accessToken.value).toBe('minted')
      expect(auth.user.value?.name).toBe('Ada')
    })

    it('lets the store write the identity back', async () => {
      const { useAuth, authSession } = await load()
      const auth = useAuth()
      authSession.setSession({ access_token: 'minted', expires_in: 900, user: { name: 'Ada' } })

      // `stores/auth.ts` patches this after a profile save; a computed without a
      // setter would throw in dev and quietly do nothing in production.
      auth.user.value = { ...auth.user.value, name: 'Ada Lovelace' }

      expect(authSession.user.value?.name).toBe('Ada Lovelace')
    })

    it('forwards the session actions untouched', async () => {
      const { useAuth, authSession } = await load()
      const auth = useAuth()

      expect(auth.login).toBe(authSession.login)
      expect(auth.register).toBe(authSession.register)
      expect(auth.refresh).toBe(authSession.refresh)
      expect(auth.bootstrap).toBe(authSession.bootstrap)
    })
  })

  describe('getAccessTokenSilently', () => {
    it('returns the current token', async () => {
      const { useAuth, authSession } = await load()
      authSession.setSession({ access_token: 'minted', expires_in: 900 })

      await expect(useAuth().getAccessTokenSilently()).resolves.toBe('minted')
    })

    it('throws when nobody is signed in, rather than returning nothing', async () => {
      const { useAuth } = await load()

      await expect(useAuth().getAccessTokenSilently()).rejects.toThrow('User is not authenticated')
    })
  })

  describe('loginWithRedirect', () => {
    it('sends the visitor to the login page', async () => {
      const { useAuth } = await load()

      await useAuth().loginWithRedirect()

      expect(push).toHaveBeenCalledWith({ name: 'login', query: {} })
    })

    it('carries the intended destination along as ?redirect', async () => {
      const { useAuth } = await load()

      await useAuth().loginWithRedirect({ redirect: '/app/events/42' })

      expect(push).toHaveBeenCalledWith({
        name: 'login',
        query: { redirect: '/app/events/42' },
      })
    })
  })

  describe('logout', () => {
    it('revokes the session and returns to the landing page', async () => {
      const { useAuth, authSession } = await load()
      authSession.setSession({ access_token: 'minted', expires_in: 900, user: { name: 'Ada' } })
      post.mockResolvedValue({ data: undefined })

      await useAuth().logout()

      expect(post).toHaveBeenCalledWith(
        expect.objectContaining({ url: '/auth/logout', withCredentials: true }),
      )
      expect(authSession.isAuthenticated.value).toBe(false)
      expect(push).toHaveBeenCalledWith({ name: 'landing' })
    })

    it('honours an explicit destination', async () => {
      const { useAuth } = await load()
      post.mockResolvedValue({ data: undefined })

      await useAuth().logout({ returnTo: '/goodbye' })

      expect(push).toHaveBeenCalledWith('/goodbye')
    })
  })

  describe('authGuard', () => {
    it('lets a signed-in visitor through', async () => {
      const { authGuard } = await load()
      post.mockResolvedValue(tokenResponse('restored'))

      await expect(authGuard(destination('/app/home'))).resolves.toBe(true)
      expect(post).toHaveBeenCalledWith(
        expect.objectContaining({ url: '/auth/refresh', withCredentials: true }),
      )
    })

    it('sends everyone else to login, keeping where they were headed', async () => {
      const { authGuard } = await load()
      post.mockRejectedValue(unauthorized())

      // The provider-hosted guard this replaces dropped the destination
      // entirely, landing every interrupted visitor on the dashboard.
      await expect(authGuard(destination('/app/events/42?tab=shifts'))).resolves.toEqual({
        name: 'login',
        query: { redirect: '/app/events/42?tab=shifts' },
      })
    })

    it('waits for the session restore before deciding', async () => {
      const { authGuard, authSession } = await load()
      post.mockResolvedValue(tokenResponse('restored'))

      const [guarded] = await Promise.all([
        authGuard(destination('/app/home')),
        authSession.bootstrap(),
      ])

      expect(guarded).toBe(true)
      expect(post).toHaveBeenCalledTimes(1)
    })
  })
})
