import { nextTick, ref } from 'vue'

import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import {
  type PreviewShift,
  type RemainderMode,
  type ScheduleConfig,
  eachDateInRange,
  slotKey,
  useShiftPreview,
} from '@/composables/useShiftPreview'

import fixtureFile from './shift-generator-fixtures.json'

/**
 * `useShiftPreview` re-implements the backend's `app/logic/shift_generator.py`
 * in TypeScript. When the two drift apart the preview lies to the user about
 * what they are about to create (issue #132), so the first block below pins the
 * composable against golden fixtures produced by running the *real* Python
 * generator (`backend/scripts/dump_shift_generator_fixtures.py`).
 *
 * If a fixture case starts failing, the fix belongs in the composable (or the
 * generator) — never in the fixture.
 */

interface FixtureShift {
  date: string
  startTime: string
  endTime: string
  title: string
}

interface FixtureCase {
  name: string
  description: string
  config: {
    eventName: string
    startDate: string
    endDate: string
    specificDates: string[] | null
    defaultStartTime: string
    defaultEndTime: string
    shiftDurationMinutes: number
    remainderMode: RemainderMode
    overrides: Array<{ date: string; startTime: string; endTime: string }>
  }
  expected: FixtureShift[]
}

const fixtureCases = (fixtureFile as unknown as { cases: FixtureCase[] }).cases

const caseByName = (name: string): FixtureCase => {
  const found = fixtureCases.find((c) => c.name === name)
  if (!found)
    throw new Error(`Fixture case "${name}" is missing from shift-generator-fixtures.json`)
  return found
}

/** The composable takes fields the backend fixture does not carry. */
const fromFixture = (fixtureConfig: FixtureCase['config']): ScheduleConfig => ({
  eventName: fixtureConfig.eventName,
  startDate: fixtureConfig.startDate,
  endDate: fixtureConfig.endDate,
  specificDates: fixtureConfig.specificDates ?? undefined,
  defaultStartTime: fixtureConfig.defaultStartTime,
  defaultEndTime: fixtureConfig.defaultEndTime,
  shiftDurationMinutes: fixtureConfig.shiftDurationMinutes,
  peoplePerShift: 1,
  remainderMode: fixtureConfig.remainderMode,
  overrides: fixtureConfig.overrides,
})

const makeConfig = (patch: Partial<ScheduleConfig> = {}): ScheduleConfig => ({
  eventName: 'Cleanup',
  startDate: '2026-03-02',
  endDate: '2026-03-02',
  specificDates: undefined,
  defaultStartTime: '10:00',
  defaultEndTime: '12:00',
  shiftDurationMinutes: 30,
  peoplePerShift: 1,
  remainderMode: 'drop',
  overrides: [],
  ...patch,
})

const uniqueDates = (shifts: readonly PreviewShift[]): string[] => [
  ...new Set(shifts.map((s) => s.date)),
]

// ---------------------------------------------------------------------------
// PART 1 — parity with the backend shift_generator
// ---------------------------------------------------------------------------

describe('useShiftPreview parity with the backend shift_generator', () => {
  it('runs against every golden fixture case', () => {
    // Guards against a truncated/empty fixture file silently producing 0 tests.
    expect(fixtureCases.length).toBeGreaterThanOrEqual(16)
    expect(fixtureCases.map((c) => c.name)).toEqual(
      expect.arrayContaining([
        'single-day-exact',
        'single-day-remainder-drop',
        'single-day-remainder-short',
        'single-day-remainder-extend',
        'single-day-shorter-than-one-shift-drop',
        'single-day-shorter-than-one-shift-short',
        'range-three-days',
        'range-crossing-month-boundary',
        'range-with-override',
        'range-end-before-start',
        'day-window-inverted',
        'specific-dates-as-submitted-span',
        'specific-dates-honoured',
        'specific-dates-empty-list-is-no-filter',
        'specific-dates-outside-the-span-are-ignored',
        'specific-dates-with-override-on-a-skipped-day',
      ]),
    )
  })

  it.each(fixtureCases)('$name: $description', ({ config, expected }) => {
    const { previewShifts } = useShiftPreview(ref(fromFixture(config)))

    expect(previewShifts.value).toEqual(expected)
  })
})

// ---------------------------------------------------------------------------
// PART 2 — "specific dates" mode agrees with the backend
// ---------------------------------------------------------------------------

describe('specific-dates mode matches what the backend will create', () => {
  /**
   * This block used to characterise issue #144: the wizard previewed only the
   * hand-picked days but submitted `start_date = min`, `end_date = max` and an
   * `excluded_shifts` list holding only the user's manual toggles, so the
   * backend created every gap day in between — shifts nobody was shown.
   *
   * `ShiftGenerationConfig.specific_dates` now carries the date list, so the
   * two agree. The assertions below are the inverted form of the ones that
   * pinned the divergence; `specific-dates-as-submitted-span` is retained as
   * the counter-example (a span sent WITHOUT the list still means every day).
   */
  const specificDates = ['2026-03-02', '2026-03-05']

  const previewOnlyPicked = () => {
    const config = ref(
      makeConfig({
        startDate: '2026-03-02', // min(specificDates) — what the view submits
        endDate: '2026-03-05', // max(specificDates) — what the view submits
        specificDates,
        defaultStartTime: '09:00',
        defaultEndTime: '11:00',
        shiftDurationMinutes: 60,
      }),
    )
    return useShiftPreview(config)
  }

  it('previews only the hand-picked dates', () => {
    const { previewShifts } = previewOnlyPicked()

    expect(uniqueDates(previewShifts.value)).toEqual(['2026-03-02', '2026-03-05'])
    expect(previewShifts.value).toHaveLength(4)
  })

  it('the backend skips the gap days when it is given the date list', () => {
    const backend = caseByName('specific-dates-honoured')

    expect(backend.config.specificDates).toEqual(specificDates)
    expect(uniqueDates(backend.expected)).toEqual(['2026-03-02', '2026-03-05'])
    expect(backend.expected).toHaveLength(4)
  })

  it('preview shifts match the shifts the backend will create, exactly', () => {
    const { previewShifts } = previewOnlyPicked()
    const backend = caseByName('specific-dates-honoured')

    // The inversion of the old `not.toEqual`: the user is now shown 2 days and
    // gets 2 days, with the same slots and titles.
    expect(previewShifts.value).toEqual(backend.expected)
    expect(uniqueDates(previewShifts.value)).toEqual(uniqueDates(backend.expected))
    expect(uniqueDates(backend.expected)).not.toContain('2026-03-03')
    expect(uniqueDates(backend.expected)).not.toContain('2026-03-04')
  })

  it('the same span without the date list still fills in every day', () => {
    // The counter-example, and what the old submit payload produced.
    const backend = caseByName('specific-dates-as-submitted-span')

    expect(backend.config.specificDates).toBeNull()
    expect(uniqueDates(backend.expected)).toEqual([
      '2026-03-02',
      '2026-03-03',
      '2026-03-04',
      '2026-03-05',
    ])
    expect(backend.expected).toHaveLength(8)
  })

  it('manual exclusions still subtract individual slots from the picked days', () => {
    const { previewShifts, toggleShiftExclusion, excludedShifts } = previewOnlyPicked()

    // The view builds `excluded_shifts` from exactly this set. Gap days are no
    // longer its problem — `specific_dates` covers those.
    toggleShiftExclusion(previewShifts.value[0])

    expect([...excludedShifts.value]).toEqual(['2026-03-02|09:00|10:00'])
    expect([...excludedShifts.value].some((key) => key.startsWith('2026-03-03'))).toBe(false)
    expect([...excludedShifts.value].some((key) => key.startsWith('2026-03-04'))).toBe(false)
  })

  it('treats an empty list as "no restriction", like the backend', () => {
    // The trap: if `[]` meant "no days", a client always sending the field
    // would silently create nothing in range mode.
    const { previewShifts } = useShiftPreview(
      ref(
        makeConfig({
          startDate: '2026-03-02',
          endDate: '2026-03-04',
          specificDates: [],
          defaultStartTime: '09:00',
          defaultEndTime: '11:00',
          shiftDurationMinutes: 60,
        }),
      ),
    )

    expect(previewShifts.value).toEqual(
      caseByName('specific-dates-empty-list-is-no-filter').expected,
    )
  })
})

// ---------------------------------------------------------------------------
// PART 3 — the composable's own behaviour
// ---------------------------------------------------------------------------

describe('useShiftPreview guard clauses', () => {
  it.each([
    ['startDate', { startDate: '' }],
    ['endDate', { endDate: '' }],
    ['defaultStartTime', { defaultStartTime: '' }],
    ['defaultEndTime', { defaultEndTime: '' }],
    ['shiftDurationMinutes', { shiftDurationMinutes: 0 }],
  ])('returns no shifts when %s is missing', (_field, patch: Partial<ScheduleConfig>) => {
    const { previewShifts, totalShifts, totalDays, hasRemainder } = useShiftPreview(
      ref(makeConfig(patch)),
    )

    expect(previewShifts.value).toEqual([])
    expect(totalShifts.value).toBe(0)
    expect(totalDays.value).toBe(0)
    expect(hasRemainder.value).toBe(false)
  })

  it('returns no shifts when the shift duration is below one minute', () => {
    const { previewShifts, hasRemainder } = useShiftPreview(
      ref(makeConfig({ shiftDurationMinutes: -30 })),
    )

    expect(previewShifts.value).toEqual([])
    expect(hasRemainder.value).toBe(false)
  })

  it('accepts a one-minute duration as the smallest valid value', () => {
    const { previewShifts } = useShiftPreview(
      ref(
        makeConfig({ defaultStartTime: '10:00', defaultEndTime: '10:03', shiftDurationMinutes: 1 }),
      ),
    )

    expect(previewShifts.value.map((s) => `${s.startTime}-${s.endTime}`)).toEqual([
      '10:00-10:01',
      '10:01-10:02',
      '10:02-10:03',
    ])
  })

  it('generates nothing for a window shorter than one shift in extend mode', () => {
    // No golden fixture covers this combination (the generator script only dumps
    // the drop/short variants), so this is frontend-only. The backend agrees by
    // inspection: `_generate_shifts_for_day` guards `extend` with `and shifts`,
    // which is empty here. Worth adding to the fixture script.
    const { previewShifts } = useShiftPreview(
      ref(
        makeConfig({
          defaultStartTime: '10:00',
          defaultEndTime: '10:20',
          shiftDurationMinutes: 60,
          remainderMode: 'extend',
        }),
      ),
    )

    expect(previewShifts.value).toEqual([])
  })
})

describe('slotKey', () => {
  it('joins date, start and end with a pipe', () => {
    expect(
      slotKey({
        date: '2026-03-02',
        startTime: '09:00',
        endTime: '10:30',
        title: 'ignored by the key',
      }),
    ).toBe('2026-03-02|09:00|10:30')
  })

  it('ignores the title, so two shifts of the same slot share a key', () => {
    const base = { date: '2026-03-02', startTime: '09:00', endTime: '10:00' }

    expect(slotKey({ ...base, title: 'Cleanup 09:00-10:00' })).toBe(
      slotKey({ ...base, title: 'Something else entirely' }),
    )
  })
})

describe('exclusions', () => {
  const twoDayConfig = () =>
    makeConfig({
      startDate: '2026-03-02',
      endDate: '2026-03-03',
      defaultStartTime: '09:00',
      defaultEndTime: '11:00',
      shiftDurationMinutes: 60,
    })

  it('round-trips toggleShiftExclusion / isShiftExcluded', () => {
    const { previewShifts, toggleShiftExclusion, isShiftExcluded } = useShiftPreview(
      ref(twoDayConfig()),
    )
    const shift = previewShifts.value[0]

    expect(isShiftExcluded(shift)).toBe(false)

    toggleShiftExclusion(shift)
    expect(isShiftExcluded(shift)).toBe(true)

    toggleShiftExclusion(shift)
    expect(isShiftExcluded(shift)).toBe(false)
  })

  it('matches exclusions by slot, not by object identity', () => {
    const { previewShifts, toggleShiftExclusion, isShiftExcluded } = useShiftPreview(
      ref(twoDayConfig()),
    )
    const shift = previewShifts.value[0]

    toggleShiftExclusion({ ...shift, title: 'a different title' })

    expect(isShiftExcluded(shift)).toBe(true)
  })

  it('drops excluded shifts from activeShifts and keeps previewShifts intact', () => {
    const { previewShifts, activeShifts, toggleShiftExclusion } = useShiftPreview(
      ref(twoDayConfig()),
    )

    expect(previewShifts.value).toHaveLength(4)

    toggleShiftExclusion(previewShifts.value[0])

    expect(previewShifts.value).toHaveLength(4)
    expect(activeShifts.value).toHaveLength(3)
    expect(activeShifts.value.map(slotKey)).not.toContain('2026-03-02|09:00|10:00')
  })

  it('reports totalShifts and totalDays from activeShifts', () => {
    const { previewShifts, totalShifts, totalDays, toggleShiftExclusion } = useShiftPreview(
      ref(twoDayConfig()),
    )

    expect(totalShifts.value).toBe(4)
    expect(totalDays.value).toBe(2)

    // Exclude the whole first day.
    for (const shift of previewShifts.value.filter((s) => s.date === '2026-03-02')) {
      toggleShiftExclusion(shift)
    }

    expect(totalShifts.value).toBe(2)
    expect(totalDays.value).toBe(1)
  })

  it('exposes the raw exclusion keys used by the submit payload', () => {
    const { previewShifts, excludedShifts, toggleShiftExclusion } = useShiftPreview(
      ref(twoDayConfig()),
    )

    toggleShiftExclusion(previewShifts.value[0])
    toggleShiftExclusion(previewShifts.value[3])

    expect([...excludedShifts.value].sort()).toEqual([
      '2026-03-02|09:00|10:00',
      '2026-03-03|10:00|11:00',
    ])
  })
})

describe('shiftsByDate', () => {
  it('groups the shifts by date in generation order', () => {
    const { shiftsByDate } = useShiftPreview(
      ref(
        makeConfig({
          startDate: '2026-03-02',
          endDate: '2026-03-03',
          defaultStartTime: '09:00',
          defaultEndTime: '11:00',
          shiftDurationMinutes: 60,
        }),
      ),
    )

    expect([...shiftsByDate.value.keys()]).toEqual(['2026-03-02', '2026-03-03'])
    expect(shiftsByDate.value.get('2026-03-02')?.map((s) => s.startTime)).toEqual([
      '09:00',
      '10:00',
    ])
    expect(shiftsByDate.value.get('2026-03-03')?.map((s) => s.endTime)).toEqual(['10:00', '11:00'])
  })

  it('groups previewShifts, NOT activeShifts — excluded shifts stay in the grid', () => {
    // Intentional: the grid renders every slot and greys out the excluded ones
    // via `isShiftExcluded`. Asserting the actual behaviour, not the intuitive one.
    const { previewShifts, activeShifts, shiftsByDate, toggleShiftExclusion } = useShiftPreview(
      ref(
        makeConfig({
          startDate: '2026-03-02',
          endDate: '2026-03-03',
          defaultStartTime: '09:00',
          defaultEndTime: '11:00',
          shiftDurationMinutes: 60,
        }),
      ),
    )

    for (const shift of previewShifts.value.filter((s) => s.date === '2026-03-02')) {
      toggleShiftExclusion(shift)
    }

    expect(activeShifts.value.map((s) => s.date)).toEqual(['2026-03-03', '2026-03-03'])
    // The fully excluded day is still a key with both of its shifts.
    expect([...shiftsByDate.value.keys()]).toEqual(['2026-03-02', '2026-03-03'])
    expect(shiftsByDate.value.get('2026-03-02')).toHaveLength(2)
  })

  it('is empty when nothing is generated', () => {
    const { shiftsByDate } = useShiftPreview(ref(makeConfig({ startDate: '' })))

    expect(shiftsByDate.value.size).toBe(0)
  })
})

describe('stale exclusion pruning when the schedule is reconfigured', () => {
  it('drops exclusion keys that no longer match any generated slot', async () => {
    const config = ref(
      makeConfig({
        defaultStartTime: '09:00',
        defaultEndTime: '11:00',
        shiftDurationMinutes: 60,
      }),
    )
    const { previewShifts, excludedShifts, toggleShiftExclusion } = useShiftPreview(config)

    toggleShiftExclusion(previewShifts.value[0])
    expect([...excludedShifts.value]).toEqual(['2026-03-02|09:00|10:00'])

    // Move the schedule to a completely different day.
    config.value = makeConfig({
      startDate: '2026-03-09',
      endDate: '2026-03-09',
      defaultStartTime: '09:00',
      defaultEndTime: '11:00',
      shiftDurationMinutes: 60,
    })

    // The watcher is `flush: 'pre'` — the stale key survives until it runs.
    expect(excludedShifts.value.size).toBe(1)

    await nextTick()

    expect(excludedShifts.value.size).toBe(0)
    expect(previewShifts.value.map((s) => s.date)).toEqual(['2026-03-09', '2026-03-09'])
  })

  it('keeps exclusion keys whose slot still exists after reconfiguration', async () => {
    const config = ref(
      makeConfig({
        startDate: '2026-03-02',
        endDate: '2026-03-02',
        defaultStartTime: '09:00',
        defaultEndTime: '11:00',
        shiftDurationMinutes: 60,
      }),
    )
    const { previewShifts, excludedShifts, isShiftExcluded, toggleShiftExclusion } =
      useShiftPreview(config)
    const kept = previewShifts.value[0]

    toggleShiftExclusion(kept)

    // Extend the range — 2026-03-02 09:00-10:00 is still generated.
    config.value = makeConfig({
      startDate: '2026-03-02',
      endDate: '2026-03-04',
      defaultStartTime: '09:00',
      defaultEndTime: '11:00',
      shiftDurationMinutes: 60,
    })
    await nextTick()

    expect(previewShifts.value).toHaveLength(6)
    expect(excludedShifts.value.size).toBe(1)
    expect(isShiftExcluded(kept)).toBe(true)
  })
})

describe('hasRemainder', () => {
  it.each([['drop' as RemainderMode], ['short' as RemainderMode], ['extend' as RemainderMode]])(
    'is true for a %s schedule whose window does not divide evenly',
    (remainderMode) => {
      const { hasRemainder } = useShiftPreview(
        ref(
          makeConfig({
            defaultStartTime: '10:00',
            defaultEndTime: '12:20',
            shiftDurationMinutes: 60,
            remainderMode,
          }),
        ),
      )

      expect(hasRemainder.value).toBe(true)
    },
  )

  it('is false when the window divides exactly', () => {
    const { hasRemainder } = useShiftPreview(
      ref(
        makeConfig({
          defaultStartTime: '10:00',
          defaultEndTime: '12:00',
          shiftDurationMinutes: 30,
        }),
      ),
    )

    expect(hasRemainder.value).toBe(false)
  })

  it('is true when the window is shorter than a single shift', () => {
    const { previewShifts, hasRemainder } = useShiftPreview(
      ref(
        makeConfig({
          defaultStartTime: '10:00',
          defaultEndTime: '10:20',
          shiftDurationMinutes: 60,
        }),
      ),
    )

    expect(previewShifts.value).toEqual([])
    expect(hasRemainder.value).toBe(true)
  })

  it('is false for an inverted day window', () => {
    const { hasRemainder } = useShiftPreview(
      ref(
        makeConfig({
          defaultStartTime: '18:00',
          defaultEndTime: '10:00',
          shiftDurationMinutes: 60,
        }),
      ),
    )

    expect(hasRemainder.value).toBe(false)
  })

  it('is true when only an overridden day leaves a remainder', () => {
    const { hasRemainder } = useShiftPreview(
      ref(
        makeConfig({
          startDate: '2026-03-02',
          endDate: '2026-03-04',
          defaultStartTime: '09:00',
          defaultEndTime: '11:00',
          shiftDurationMinutes: 60,
          overrides: [{ date: '2026-03-03', startTime: '14:00', endTime: '17:30' }],
        }),
      ),
    )

    expect(hasRemainder.value).toBe(true)
  })

  it('only considers the hand-picked dates in specific-dates mode', () => {
    const { hasRemainder } = useShiftPreview(
      ref(
        makeConfig({
          startDate: '2026-03-02',
          endDate: '2026-03-04',
          specificDates: ['2026-03-02', '2026-03-04'],
          defaultStartTime: '09:00',
          defaultEndTime: '11:00',
          shiftDurationMinutes: 60,
          // The skipped 2026-03-03 is the only day with a ragged window.
          overrides: [{ date: '2026-03-03', startTime: '14:00', endTime: '17:30' }],
        }),
      ),
    )

    expect(hasRemainder.value).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Parity holds in every timezone, not just UTC and east of it
// ---------------------------------------------------------------------------

describe('date parsing in a timezone behind UTC', () => {
  /**
   * This block used to characterise issue #145. `useShiftPreview` parsed
   * 'YYYY-MM-DD' with `new Date(str)` — UTC midnight per spec — and then read it
   * back through the LOCAL `getFullYear`/`getMonth`/`getDate`. Anywhere west of
   * Greenwich that lands on the previous calendar day, so every previewed date
   * slid one day earlier while the backend created the days the user picked; in
   * specific-dates mode the shifted strings matched nothing in the set and the
   * preview rendered empty.
   *
   * Parsing and formatting now both work in UTC, so the assertions below are the
   * inverted form: the whole golden-fixture set is replayed in a negative-offset
   * zone and must produce byte-identical output.
   *
   * `delete process.env.TZ` does not restore the zone in Node 24 — hence the
   * captured `systemTimeZone`.
   */
  const systemTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone

  beforeEach(() => {
    process.env.TZ = 'America/New_York'
  })

  afterEach(() => {
    process.env.TZ = systemTimeZone
  })

  it('is actually running in a zone behind UTC', () => {
    // Without this the rest of the block would pass vacuously if the runtime
    // ever stopped honouring a mid-process TZ change.
    expect(Intl.DateTimeFormat().resolvedOptions().timeZone).toBe('America/New_York')
    expect(new Date('2026-03-02').getDate()).toBe(1)
  })

  it.each(fixtureCases)('$name still matches the backend exactly', ({ config, expected }) => {
    const { previewShifts } = useShiftPreview(ref(fromFixture(config)))

    expect(previewShifts.value).toEqual(expected)
  })

  it('keeps the hand-picked dates in specific-dates mode', () => {
    const { previewShifts } = useShiftPreview(
      ref(
        makeConfig({
          startDate: '2026-03-02',
          endDate: '2026-03-02',
          specificDates: ['2026-03-02'],
          defaultStartTime: '09:00',
          defaultEndTime: '11:00',
          shiftDurationMinutes: 60,
        }),
      ),
    )

    expect(uniqueDates(previewShifts.value)).toEqual(['2026-03-02'])
    expect(previewShifts.value).toHaveLength(2)
  })

  it('does not drop the last day of a range across a DST transition', () => {
    // 2026-03-08 is the US spring-forward. Stepping a *local*-midnight Date by
    // a day drifts past `end` in zones whose clocks change at midnight, which
    // is why the iteration stays in UTC.
    const { previewShifts } = useShiftPreview(
      ref(
        makeConfig({
          startDate: '2026-03-06',
          endDate: '2026-03-10',
          defaultStartTime: '09:00',
          defaultEndTime: '10:00',
          shiftDurationMinutes: 60,
        }),
      ),
    )

    expect(uniqueDates(previewShifts.value)).toEqual([
      '2026-03-06',
      '2026-03-07',
      '2026-03-08',
      '2026-03-09',
      '2026-03-10',
    ])
  })
})

describe('eachDateInRange', () => {
  it('is inclusive of both ends', () => {
    expect(eachDateInRange('2026-03-02', '2026-03-05')).toEqual([
      '2026-03-02',
      '2026-03-03',
      '2026-03-04',
      '2026-03-05',
    ])
  })

  it('returns the single day when start and end are equal', () => {
    expect(eachDateInRange('2026-03-02', '2026-03-02')).toEqual(['2026-03-02'])
  })

  it('returns nothing when end is before start', () => {
    expect(eachDateInRange('2026-03-05', '2026-03-02')).toEqual([])
  })

  it('crosses month and year boundaries', () => {
    expect(eachDateInRange('2026-12-30', '2027-01-02')).toEqual([
      '2026-12-30',
      '2026-12-31',
      '2027-01-01',
      '2027-01-02',
    ])
  })

  it('includes the leap day', () => {
    expect(eachDateInRange('2028-02-27', '2028-03-01')).toEqual([
      '2028-02-27',
      '2028-02-28',
      '2028-02-29',
      '2028-03-01',
    ])
  })

  it.each([
    ['both empty', '', ''],
    ['empty start', '', '2026-03-02'],
    ['empty end', '2026-03-02', ''],
    ['unparseable', 'not-a-date', '2026-03-02'],
  ])('returns nothing for %s', (_label, start, end) => {
    expect(eachDateInRange(start, end)).toEqual([])
  })

  it.each(['UTC', 'America/New_York', 'America/Santiago', 'Asia/Beirut', 'Pacific/Auckland'])(
    'produces the same days in %s',
    (timeZone) => {
      const systemTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
      process.env.TZ = timeZone
      try {
        // Santiago and Beirut change their clocks at midnight, which is what
        // broke the previous `toISOString()` + local `setDate()` loop: it
        // emitted a duplicate day and dropped the last one.
        expect(eachDateInRange('2026-03-06', '2026-03-10')).toEqual([
          '2026-03-06',
          '2026-03-07',
          '2026-03-08',
          '2026-03-09',
          '2026-03-10',
        ])
        expect(eachDateInRange('2026-09-04', '2026-09-08')).toHaveLength(5)
        expect(eachDateInRange('2026-11-01', '2026-11-04')).toHaveLength(4)
      } finally {
        process.env.TZ = systemTimeZone
      }
    },
  )
})
