import { ref } from 'vue'

import { describe, expect, it } from 'vitest'

import { avatarUrlFor, useAvatarUrl } from '@/composables/useAvatarUrl'

/**
 * The etag in the query string is the whole point: it is what makes a new
 * upload produce a new URL and bust the browser cache. A test that only checked
 * the path would pass while avatars stayed stale forever.
 */
const API = import.meta.env.VITE_API_URL

describe('avatarUrlFor', () => {
  it('builds a URL carrying the etag as a cache buster', () => {
    expect(avatarUrlFor({ id: 'u1', avatar_etag: 'abc123' })).toBe(
      `${API}/users/u1/avatar?v=abc123`,
    )
  })

  it('changes when the etag changes, so a re-upload is not served from cache', () => {
    const before = avatarUrlFor({ id: 'u1', avatar_etag: 'abc123' })
    const after = avatarUrlFor({ id: 'u1', avatar_etag: 'def456' })

    expect(after).not.toBe(before)
  })

  it.each([
    ['null source', null],
    ['undefined source', undefined],
    ['no etag', { id: 'u1' }],
    ['null etag', { id: 'u1', avatar_etag: null }],
    ['undefined etag', { id: 'u1', avatar_etag: undefined }],
    ['empty etag', { id: 'u1', avatar_etag: '' }],
  ])('returns null for %s, so callers fall through to initials', (_label, source) => {
    expect(avatarUrlFor(source)).toBeNull()
  })
})

describe('useAvatarUrl', () => {
  it('accepts a plain object', () => {
    expect(useAvatarUrl({ id: 'u1', avatar_etag: 'abc123' }).value).toBe(
      `${API}/users/u1/avatar?v=abc123`,
    )
  })

  it('accepts a getter', () => {
    expect(useAvatarUrl(() => ({ id: 'u2', avatar_etag: 'xyz' })).value).toBe(
      `${API}/users/u2/avatar?v=xyz`,
    )
  })

  it('tracks a ref, so the avatar updates after an upload', () => {
    const user = ref<{ id: string; avatar_etag?: string | null }>({ id: 'u1', avatar_etag: null })
    const url = useAvatarUrl(user)

    expect(url.value).toBeNull()

    user.value = { id: 'u1', avatar_etag: 'fresh' }

    expect(url.value).toBe(`${API}/users/u1/avatar?v=fresh`)
  })

  it('returns null for a null source', () => {
    expect(useAvatarUrl(null).value).toBeNull()
  })
})
