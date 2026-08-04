import { nextTick, ref } from 'vue'

import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import {
  type PreviewShift,
  type RemainderMode,
  type ScheduleConfig,
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
  specificDates: undefined,
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
    expect(fixtureCases.length).toBeGreaterThanOrEqual(12)
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
      ]),
    )
  })

  it.each(fixtureCases)('$name: $description', ({ config, expected }) => {
    const { previewShifts } = useShiftPreview(ref(fromFixture(config)))

    expect(previewShifts.value).toEqual(expected)
  })
})

// ---------------------------------------------------------------------------
// PART 2 — known divergence: "specific dates" mode
// ---------------------------------------------------------------------------

describe('specific-dates mode diverges from what the backend will create', () => {
  /**
   * KNOWN BUG — this block characterises current (wrong) behaviour.
   *
   * `TaskAddShiftsView.vue` previews only the hand-picked dates, but on submit
   * it sends `start_date = min(specificDates)`, `end_date = max(specificDates)`
   * and an `excluded_shifts` list containing ONLY the shifts the user manually
   * toggled off. The backend's `generate_shifts()` then walks every day in
   * [start_date, end_date], so every gap day between the picked dates is
   * created too — shifts the user was never shown.
   *
   * When this is fixed (either the view must exclude the gap days, or the API
   * must accept the date list), these assertions MUST be updated: the preview
   * and the backend output are then expected to agree.
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

  it('the backend generates every day of the submitted span, gaps included', () => {
    const backend = caseByName('specific-dates-as-submitted-span')

    expect(uniqueDates(backend.expected)).toEqual([
      '2026-03-02',
      '2026-03-03',
      '2026-03-04',
      '2026-03-05',
    ])
    expect(uniqueDates(backend.expected)).toHaveLength(4)
    expect(backend.expected).toHaveLength(8)
  })

  it('preview dates do NOT match the dates the backend will create (encodes the bug)', () => {
    const { previewShifts } = previewOnlyPicked()
    const backend = caseByName('specific-dates-as-submitted-span')

    const previewDates = uniqueDates(previewShifts.value)
    const backendDates = uniqueDates(backend.expected)

    // Deliberately asserting INEQUALITY: today the user is shown 2 days and
    // gets 4. Flip these to `toEqual` once the divergence is fixed.
    expect(previewDates).not.toEqual(backendDates)
    expect(backendDates).toContain('2026-03-03')
    expect(backendDates).toContain('2026-03-04')
    expect(previewDates).not.toContain('2026-03-03')
    expect(previewDates).not.toContain('2026-03-04')

    const unpreviewed = backend.expected.filter((s) => !previewDates.includes(s.date))
    expect(unpreviewed).toHaveLength(4)
  })

  it('manual exclusions are the only thing the view can subtract, and they never cover gap days', () => {
    const { previewShifts, toggleShiftExclusion, excludedShifts } = previewOnlyPicked()

    // The view builds `excluded_shifts` from exactly this set.
    toggleShiftExclusion(previewShifts.value[0])

    expect([...excludedShifts.value]).toEqual(['2026-03-02|09:00|10:00'])
    // Nothing in the exclusion set refers to 2026-03-03 / 2026-03-04, so the
    // backend has no way to learn those days were never wanted.
    expect([...excludedShifts.value].some((key) => key.startsWith('2026-03-03'))).toBe(false)
    expect([...excludedShifts.value].some((key) => key.startsWith('2026-03-04'))).toBe(false)
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
// A second, latent parity break: timezones behind UTC
// ---------------------------------------------------------------------------

describe('date parsing in a timezone behind UTC diverges from the backend', () => {
  /**
   * KNOWN BUG — this block characterises current (wrong) behaviour.
   *
   * `useShiftPreview` parses 'YYYY-MM-DD' with `new Date(str)`, which per spec
   * is UTC midnight, and then formats it back through the LOCAL `getFullYear` /
   * `getMonth` / `getDate` in `formatDate()`. Anywhere west of Greenwich that
   * lands on the previous calendar day, so every previewed date is shifted one
   * day earlier — while the backend receives the plain date strings and creates
   * the days the user actually picked.
   *
   * The rest of this suite therefore only passes at UTC+0 or east of it (CI and
   * this repo's dev machines). When the composable is fixed to parse calendar
   * dates (e.g. splitting on '-' and using `new Date(y, m - 1, d)`), delete this
   * block — the fixture parity cases will then hold in every timezone.
   */
  const systemTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone

  beforeEach(() => {
    process.env.TZ = 'America/New_York'
  })

  afterEach(() => {
    process.env.TZ = systemTimeZone
  })

  it('shifts every previewed date one day earlier than the backend will create', () => {
    const backend = caseByName('range-three-days')
    const { previewShifts } = useShiftPreview(ref(fromFixture(backend.config)))

    expect(uniqueDates(backend.expected)).toEqual(['2026-03-02', '2026-03-03', '2026-03-04'])
    expect(uniqueDates(previewShifts.value)).toEqual(['2026-03-01', '2026-03-02', '2026-03-03'])
    expect(previewShifts.value).not.toEqual(backend.expected)
  })

  it('drops the hand-picked dates entirely in specific-dates mode', () => {
    // The generated date strings no longer match the `specificDates` set, so
    // the preview silently shows nothing at all.
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

    expect(previewShifts.value).toEqual([])
  })
})
