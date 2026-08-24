import { describe, expect, it } from 'vitest'

import { millisUntil, parseServerDate } from '@/lib/server-time'

describe('parseServerDate', () => {
  it('reads an offset-less server timestamp as UTC, not as local time', () => {
    // The whole point of the helper. `new Date()` on this string would answer
    // 12:33 *local*; we want 12:33 UTC.
    const parsed = parseServerDate('2026-08-24T12:33:45.212583')
    expect(parsed?.toISOString()).toBe('2026-08-24T12:33:45.212Z')
  })

  it('leaves a timestamp that already carries Z alone', () => {
    expect(parseServerDate('2026-08-24T12:33:45Z')?.toISOString()).toBe('2026-08-24T12:33:45.000Z')
  })

  it('leaves a timestamp that already carries a numeric offset alone', () => {
    // 14:33 at +02:00 is 12:33 UTC — appending a Z here would shift it.
    expect(parseServerDate('2026-08-24T14:33:45+02:00')?.toISOString()).toBe(
      '2026-08-24T12:33:45.000Z',
    )
  })

  it('does not mistake the date half for an offset', () => {
    // `2026-08-24` ends in `-24`, which a careless offset regex matches.
    expect(parseServerDate('2026-08-24T00:00:00')?.toISOString()).toBe('2026-08-24T00:00:00.000Z')
  })

  it('returns null rather than an Invalid Date', () => {
    expect(parseServerDate('not a date')).toBeNull()
    expect(parseServerDate('')).toBeNull()
    expect(parseServerDate(null)).toBeNull()
    expect(parseServerDate(undefined)).toBeNull()
  })
})

describe('millisUntil', () => {
  const now = Date.UTC(2026, 7, 24, 12, 0, 0)

  it('measures against UTC, so a fresh deadline is not already past', () => {
    // The bug this exists to prevent: east of Greenwich, reading the naive
    // string as local time put a just-issued deadline hours in the past.
    expect(millisUntil('2026-08-24T13:00:00', now)).toBe(60 * 60 * 1000)
  })

  it('floors at zero for a deadline that has passed', () => {
    expect(millisUntil('2026-08-24T11:00:00', now)).toBe(0)
  })

  it('answers null when there is no deadline, which is not the same as expired', () => {
    expect(millisUntil(null, now)).toBeNull()
    expect(millisUntil('nonsense', now)).toBeNull()
  })
})
