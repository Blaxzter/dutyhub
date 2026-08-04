import { describe, expect, it } from 'vitest'

import { statusVariant } from '@/lib/status'

describe('statusVariant', () => {
  it('maps "published" to the default badge variant', () => {
    expect(statusVariant('published')).toBe('default')
  })

  it('maps "draft" to the warning badge variant', () => {
    expect(statusVariant('draft')).toBe('warning')
  })

  it('maps "archived" to the outline badge variant', () => {
    expect(statusVariant('archived')).toBe('outline')
  })

  describe('default arm', () => {
    it.each([
      ['undefined', undefined],
      ['null', null],
      ['an empty string', ''],
      ['an unknown status', 'in_review'],
      // The switch matches case-sensitively, so a differently cased known value
      // still falls through to the default arm.
      ['a differently cased known status', 'Published'],
    ])('falls back to "secondary" for %s', (_label, status) => {
      expect(statusVariant(status)).toBe('secondary')
    })

    it('falls back to "secondary" when called without an argument', () => {
      expect(statusVariant()).toBe('secondary')
    })
  })

  it('never returns undefined for any of the known statuses', () => {
    for (const status of ['published', 'draft', 'archived']) {
      expect(statusVariant(status)).toBeTruthy()
    }
  })
})
