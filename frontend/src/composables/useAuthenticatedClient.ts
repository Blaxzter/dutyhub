import { useAuth0 } from '@auth0/auth0-vue'

import { client } from '@/client/client.gen'
import type { Auth } from '@/client/core/auth'

/**
 * Composable for making authenticated API calls
 * Uses the built-in security mechanism of the generated client
 */
export function useAuthenticatedClient() {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0()

  /**
   * Get the current auth token
   */
  const getAuthToken = async () => {
    if (!isAuthenticated.value) {
      throw new Error('User is not authenticated')
    }
    return await getAccessTokenSilently()
  }

  /**
   * Auth configuration for Bearer token
   */
  const bearerAuth: Auth = {
    type: 'http',
    scheme: 'bearer',
    in: 'header',
    name: 'Authorization',
  }

  /**
   * Auth callback that returns the token
   */
  const authCallback = async () => {
    return await getAuthToken()
  }

  /**
   * Generic authenticated request function
   */
  const makeAuthenticatedRequest = async <T>(
    method: keyof typeof client,
    options: Parameters<(typeof client)[typeof method]>[0],
  ): Promise<T> => {
    type ClientMethodOptions = Parameters<(typeof client)[typeof method]>[0]
    type ClientMethod = (opts: ClientMethodOptions) => Promise<T>
    const clientMethod = client[method] as ClientMethod

    // Handle the case where options might be a string (URL) or an object
    const requestOptions: ClientMethodOptions =
      typeof options === 'string'
        ? ({ url: options, security: [bearerAuth], auth: authCallback } as ClientMethodOptions)
        : ({ ...options, security: [bearerAuth], auth: authCallback } as ClientMethodOptions)

    return await clientMethod(requestOptions)
  }

  /**
   * HTTP method shortcuts with proper generic type support
   * Usage: await get<{ data: UserProfile[] }>({ url: '/users/' })
   */
  const get = async <T>(options: Parameters<typeof client.get>[0]): Promise<T> =>
    makeAuthenticatedRequest<T>('get', options)

  const post = async <T>(options: Parameters<typeof client.post>[0]): Promise<T> =>
    makeAuthenticatedRequest<T>('post', options)

  const put = async <T>(options: Parameters<typeof client.put>[0]): Promise<T> =>
    makeAuthenticatedRequest<T>('put', options)

  const del = async <T = void>(options: Parameters<typeof client.delete>[0]): Promise<T> =>
    makeAuthenticatedRequest<T>('delete', options)

  const patch = async <T>(options: Parameters<typeof client.patch>[0]): Promise<T> =>
    makeAuthenticatedRequest<T>('patch', options)

  return {
    getAuthToken,
    makeAuthenticatedRequest,
    get,
    post,
    put,
    delete: del,
    patch,
  }
}
