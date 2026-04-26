import { computed, type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue'

interface AvatarSource {
  id: string
  avatar_etag?: string | null | undefined
}

/**
 * Build the URL to a user's locally-stored avatar.
 *
 * The backend serves bytes at `/users/{id}/avatar`. We append the etag as a
 * query string so a new upload changes the URL and busts browser caches.
 * Returns `null` when there is no avatar — callers should fall through to
 * the initials fallback in that case.
 */
export function useAvatarUrl(
  source: MaybeRefOrGetter<AvatarSource | null | undefined>,
): ComputedRef<string | null> {
  return computed(() => {
    const s = toValue(source)
    if (!s?.avatar_etag) return null
    return `${import.meta.env.VITE_API_URL}/users/${s.id}/avatar?v=${s.avatar_etag}`
  })
}

/**
 * Non-reactive variant for use in template expressions over arrays
 * (where each element is its own user).
 */
export function avatarUrlFor(source: AvatarSource | null | undefined): string | null {
  if (!source?.avatar_etag) return null
  return `${import.meta.env.VITE_API_URL}/users/${source.id}/avatar?v=${source.avatar_etag}`
}
