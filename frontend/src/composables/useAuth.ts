import type { NavigationGuardReturn, RouteLocationNormalized, RouteLocationRaw } from 'vue-router'

import { authSession } from '@/lib/auth-session'

/**
 * The app-facing view of the session.
 *
 * Shaped to be a drop-in for the identity provider's composable it replaces, so
 * the store, the shell and the client wrapper keep the members they already
 * read. Everything reactive it hands back is a real `Ref` on purpose: the store
 * re-exposes this object through Pinia's `reactive()`, which unwraps nested refs
 * on property access — that is how `authStore.session.isLoading` works with no
 * `.value`. A plain boolean, or a `computed` without a setter, silently breaks
 * either that read or `stores/auth.ts` writing back to `user`.
 */

export interface LoginRedirectOptions {
  /** Where to send the visitor once signed in. Round-trips as `?redirect=`. */
  redirect?: string
}

export interface LogoutOptions {
  /** Where to land afterwards. Defaults to the landing page. */
  returnTo?: RouteLocationRaw
}

/**
 * Navigate without importing the router at module scope.
 *
 * `router/index.ts` imports `authGuard` from this module, so a static import
 * back would close a cycle — and a cycle that runs at module-evaluation time,
 * where one half is guaranteed to be half-initialised. By the time any of these
 * functions actually run, the router module is fully evaluated.
 */
async function navigate(to: RouteLocationRaw): Promise<void> {
  const { default: router } = await import('@/router')
  await router.push(to)
}

/**
 * The bearer token for the next request.
 *
 * Throws rather than returning null so the failure surfaces at the call site
 * that needed a token, keeping the contract the generated client's `auth`
 * callback was written against.
 */
async function getAccessTokenSilently(): Promise<string> {
  const token = await authSession.getAccessToken()
  if (!token) throw new Error('User is not authenticated')
  return token
}

/**
 * Send the visitor to the login page.
 *
 * Unlike the hosted login it replaces, the destination they were heading for
 * travels with them as `?redirect=` instead of being dropped.
 */
async function loginWithRedirect(options: LoginRedirectOptions = {}): Promise<void> {
  await navigate({
    name: 'login',
    query: options.redirect ? { redirect: options.redirect } : {},
  })
}

/** Revoke the session, clear it locally, and leave the authenticated area. */
async function logout(options: LogoutOptions = {}): Promise<void> {
  await authSession.logout()
  await navigate(options.returnTo ?? { name: 'landing' })
}

/**
 * Guard for the authenticated route trees.
 *
 * Awaits the one-shot session restore rather than polling a loading flag, so the
 * very first navigation — which routinely beats `bootstrap()` to the punch —
 * waits for an answer instead of being decided against a session that has not
 * been restored yet.
 */
export async function authGuard(to: RouteLocationNormalized): Promise<NavigationGuardReturn> {
  await authSession.bootstrap()
  if (authSession.isAuthenticated.value) return true
  return { name: 'login', query: { redirect: to.fullPath } }
}

export function useAuth() {
  return {
    isLoading: authSession.isLoading,
    isAuthenticated: authSession.isAuthenticated,
    user: authSession.user,
    accessToken: authSession.accessToken,
    getAccessTokenSilently,
    loginWithRedirect,
    logout,
    login: authSession.login,
    register: authSession.register,
    refresh: authSession.refresh,
    bootstrap: authSession.bootstrap,
  }
}

export type { AuthUser } from '@/lib/auth-session'
