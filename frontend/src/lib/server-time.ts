/**
 * Reading the timestamps this API sends.
 *
 * The backend stores every datetime as `TIMESTAMP WITHOUT TIME ZONE` holding
 * UTC (see `backend/app/models/CLAUDE.md`), so what arrives on the wire looks
 * like `"2026-08-24T12:33:45.212583"` — no `Z`, no offset. ECMAScript says a
 * date-time string *without* an offset is local time, so `new Date(iso)` reads
 * that as 12:33 in whatever zone the reader happens to be in.
 *
 * For a "created 3 days ago" label that is a cosmetic wrongness nobody
 * notices. For a deadline it is not: in Berlin the value lands two hours in
 * the past, and a countdown built on it reports that a demo which has just
 * started is already over.
 *
 * Hence this. It is deliberately narrow — it fixes the reading, not the
 * protocol. The protocol would be better fixed at the source by serialising
 * with an explicit `Z`, but every existing `created_at` and `updated_at` in the
 * application is read the naive way today, and changing all of them at once is
 * a bigger and riskier change than the one that is actually needed here.
 */

/**
 * Parse a server timestamp as UTC, whether or not it carries an offset.
 *
 * Returns `null` for anything unparseable, so callers get one explicit branch
 * to handle rather than a silent `Invalid Date` propagating into arithmetic.
 */
export function parseServerDate(iso: string | null | undefined): Date | null {
  if (!iso) return null

  // Already unambiguous — a trailing `Z` or a numeric offset like `+02:00`.
  // Only look at the time half, or the `-` separators in the date would match.
  const timePart = iso.includes('T') ? iso.slice(iso.indexOf('T')) : ''
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(timePart)

  const parsed = new Date(hasZone ? iso : `${iso}Z`)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

/**
 * Milliseconds from `now` until a server timestamp, floored at zero.
 *
 * `null` when the timestamp is missing or unparseable — which a caller should
 * render as "no deadline", never as "expired".
 */
export function millisUntil(
  iso: string | null | undefined,
  now: number = Date.now(),
): number | null {
  const target = parseServerDate(iso)
  if (!target) return null
  return Math.max(0, target.getTime() - now)
}
