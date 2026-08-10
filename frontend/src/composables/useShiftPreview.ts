import { type Ref, computed, ref, watch } from 'vue'

export type RemainderMode = 'drop' | 'short' | 'extend'

export interface ScheduleConfig {
  eventName: string
  startDate: string // YYYY-MM-DD
  endDate: string // YYYY-MM-DD
  specificDates?: string[] // YYYY-MM-DD — when set, only these dates get shifts
  defaultStartTime: string // HH:MM
  defaultEndTime: string // HH:MM
  shiftDurationMinutes: number
  peoplePerShift: number
  remainderMode: RemainderMode
  overrides: Array<{
    date: string // YYYY-MM-DD
    startTime: string // HH:MM
    endTime: string // HH:MM
  }>
}

export interface PreviewShift {
  date: string
  startTime: string
  endTime: string
  title: string
}

export function slotKey(shift: PreviewShift): string {
  return `${shift.date}|${shift.startTime}|${shift.endTime}`
}

/**
 * Every calendar date from `startDate` to `endDate` inclusive, as 'YYYY-MM-DD'.
 *
 * The backend counterpart is `while current_date <= end_date: … += timedelta(days=1)`
 * over `datetime.date`, which has no timezone at all. The equivalent in JS is to
 * stay in UTC end to end: `new Date('2026-03-02')` is UTC midnight per spec, so
 * reading it back with the *local* getFullYear/getMonth/getDate slid every
 * generated date one day earlier anywhere west of Greenwich (#145).
 *
 * UTC rather than local parsing, because local midnight is not DST-safe: in
 * zones whose clocks change at midnight (America/Santiago, Asia/Beirut, …) a
 * local-midnight Date stepped by `setDate` drifts to 01:00 and then compares
 * past `end`, dropping the last day of the range. UTC has no such transitions.
 *
 * Exported because the per-date override pickers in the task create / edit /
 * add-shifts views each had their own copy of this loop.
 */
export function eachDateInRange(startDate: string, endDate: string): string[] {
  const current = parseCalendarDate(startDate)
  const end = parseCalendarDate(endDate)
  if (Number.isNaN(current.getTime()) || Number.isNaN(end.getTime())) return []

  const dates: string[] = []
  while (current <= end) {
    dates.push(formatDate(current))
    current.setUTCDate(current.getUTCDate() + 1)
  }
  return dates
}

/**
 * Composable that generates a client-side preview of duty shifts
 * from a schedule configuration. Mirrors the backend shift_generator logic.
 */
export function useShiftPreview(config: Ref<ScheduleConfig>) {
  const previewShifts = computed<PreviewShift[]>(() => {
    const { eventName, startDate, endDate, defaultStartTime, defaultEndTime, shiftDurationMinutes } =
      config.value

    if (!startDate || !endDate || !defaultStartTime || !defaultEndTime || !shiftDurationMinutes) {
      return []
    }

    if (shiftDurationMinutes < 1) return []

    const overrideMap = new Map<string, { startTime: string; endTime: string }>()
    for (const o of config.value.overrides) {
      overrideMap.set(o.date, { startTime: o.startTime, endTime: o.endTime })
    }

    const shifts: PreviewShift[] = []
    const specificDatesSet = config.value.specificDates?.length
      ? new Set(config.value.specificDates)
      : null

    for (const dateStr of eachDateInRange(startDate, endDate)) {
      // If specific dates are set, skip dates not in the list
      if (specificDatesSet && !specificDatesSet.has(dateStr)) continue

      const override = overrideMap.get(dateStr)
      const dayStart = override ? override.startTime : defaultStartTime
      const dayEnd = override ? override.endTime : defaultEndTime

      const dayShifts = generateShiftsForDay(
        eventName,
        dateStr,
        dayStart,
        dayEnd,
        shiftDurationMinutes,
        config.value.remainderMode,
      )
      shifts.push(...dayShifts)
    }

    return shifts
  })

  // Excluded shifts tracking
  const excludedShifts = ref(new Set<string>())

  // Clear exclusions when the generated shifts change (schedule reconfigured)
  watch(previewShifts, () => {
    const validKeys = new Set(previewShifts.value.map(slotKey))
    for (const key of excludedShifts.value) {
      if (!validKeys.has(key)) excludedShifts.value.delete(key)
    }
  })

  const toggleShiftExclusion = (shift: PreviewShift) => {
    const key = slotKey(shift)
    if (excludedShifts.value.has(key)) {
      excludedShifts.value.delete(key)
    } else {
      excludedShifts.value.add(key)
    }
    // Trigger reactivity
    excludedShifts.value = new Set(excludedShifts.value)
  }

  const isShiftExcluded = (shift: PreviewShift) => excludedShifts.value.has(slotKey(shift))

  const activeShifts = computed(() =>
    previewShifts.value.filter((s) => !excludedShifts.value.has(slotKey(s))),
  )

  const totalShifts = computed(() => activeShifts.value.length)

  const totalDays = computed(() => new Set(activeShifts.value.map((s) => s.date)).size)

  const shiftsByDate = computed(() => {
    const grouped = new Map<string, PreviewShift[]>()
    for (const shift of previewShifts.value) {
      const existing = grouped.get(shift.date) ?? []
      existing.push(shift)
      grouped.set(shift.date, existing)
    }
    return grouped
  })

  const hasRemainder = computed(() => {
    const { startDate, endDate, defaultStartTime, defaultEndTime, shiftDurationMinutes } =
      config.value

    if (!startDate || !endDate || !defaultStartTime || !defaultEndTime || !shiftDurationMinutes) {
      return false
    }
    if (shiftDurationMinutes < 1) return false

    const overrideMap = new Map<string, { startTime: string; endTime: string }>()
    for (const o of config.value.overrides) {
      overrideMap.set(o.date, { startTime: o.startTime, endTime: o.endTime })
    }

    const specificDatesSet = config.value.specificDates?.length
      ? new Set(config.value.specificDates)
      : null

    for (const dateStr of eachDateInRange(startDate, endDate)) {
      if (specificDatesSet && !specificDatesSet.has(dateStr)) continue

      const override = overrideMap.get(dateStr)
      const dayStart = override ? override.startTime : defaultStartTime
      const dayEnd = override ? override.endTime : defaultEndTime
      const totalMinutes = timeToMinutes(dayEnd) - timeToMinutes(dayStart)
      if (totalMinutes > 0 && totalMinutes % shiftDurationMinutes !== 0) {
        return true
      }
    }

    return false
  })

  return {
    previewShifts,
    activeShifts,
    totalShifts,
    totalDays,
    shiftsByDate,
    hasRemainder,
    excludedShifts,
    toggleShiftExclusion,
    isShiftExcluded,
  }
}

/** 'YYYY-MM-DD' → a Date pinned to UTC midnight. See {@link eachDateInRange}. */
function parseCalendarDate(value: string): Date {
  return new Date(`${value}T00:00:00Z`)
}

/** The inverse of {@link parseCalendarDate}; the two must agree on UTC. */
function formatDate(d: Date): string {
  const year = d.getUTCFullYear()
  const month = String(d.getUTCMonth() + 1).padStart(2, '0')
  const day = String(d.getUTCDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function generateShiftsForDay(
  eventName: string,
  dateStr: string,
  startTime: string,
  endTime: string,
  durationMinutes: number,
  remainderMode: RemainderMode = 'drop',
): PreviewShift[] {
  const shifts: PreviewShift[] = []
  const startMinutes = timeToMinutes(startTime)
  const endMinutes = timeToMinutes(endTime)

  if (startMinutes >= endMinutes) return []

  let current = startMinutes
  while (current + durationMinutes <= endMinutes) {
    const slotStart = minutesToTime(current)
    const slotEnd = minutesToTime(current + durationMinutes)
    shifts.push({
      date: dateStr,
      startTime: slotStart,
      endTime: slotEnd,
      title: `${eventName} ${slotStart}-${slotEnd}`,
    })
    current += durationMinutes
  }

  // Handle remaining time that doesn't fill a full shift
  const remainder = endMinutes - current
  if (remainder > 0 && shifts.length > 0) {
    if (remainderMode === 'short') {
      const slotStart = minutesToTime(current)
      const slotEnd = minutesToTime(endMinutes)
      shifts.push({
        date: dateStr,
        startTime: slotStart,
        endTime: slotEnd,
        title: `${eventName} ${slotStart}-${slotEnd}`,
      })
    } else if (remainderMode === 'extend') {
      const last = shifts[shifts.length - 1]
      last.endTime = minutesToTime(endMinutes)
      last.title = `${eventName} ${last.startTime}-${last.endTime}`
    }
  } else if (remainder > 0 && shifts.length === 0 && remainderMode === 'short') {
    // No full shifts fit but there's time — create a short shift
    const slotStart = minutesToTime(startMinutes)
    const slotEnd = minutesToTime(endMinutes)
    shifts.push({
      date: dateStr,
      startTime: slotStart,
      endTime: slotEnd,
      title: `${eventName} ${slotStart}-${slotEnd}`,
    })
  }

  return shifts
}

function timeToMinutes(time: string): number {
  const [h, m] = time.split(':').map(Number)
  return h * 60 + m
}

function minutesToTime(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}
