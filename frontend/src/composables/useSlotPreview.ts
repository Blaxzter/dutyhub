import { computed, type Ref } from 'vue'

export interface ScheduleConfig {
  eventName: string
  startDate: string // YYYY-MM-DD
  endDate: string // YYYY-MM-DD
  defaultStartTime: string // HH:MM
  defaultEndTime: string // HH:MM
  slotDurationMinutes: number
  peoplePerSlot: number
  overrides: Array<{
    date: string // YYYY-MM-DD
    startTime: string // HH:MM
    endTime: string // HH:MM
  }>
}

export interface PreviewSlot {
  date: string
  startTime: string
  endTime: string
  title: string
}

/**
 * Composable that generates a client-side preview of duty slots
 * from a schedule configuration. Mirrors the backend slot_generator logic.
 */
export function useSlotPreview(config: Ref<ScheduleConfig>) {
  const previewSlots = computed<PreviewSlot[]>(() => {
    const { eventName, startDate, endDate, defaultStartTime, defaultEndTime, slotDurationMinutes } =
      config.value

    if (!startDate || !endDate || !defaultStartTime || !defaultEndTime || !slotDurationMinutes) {
      return []
    }

    if (slotDurationMinutes < 1) return []

    const overrideMap = new Map<string, { startTime: string; endTime: string }>()
    for (const o of config.value.overrides) {
      overrideMap.set(o.date, { startTime: o.startTime, endTime: o.endTime })
    }

    const slots: PreviewSlot[] = []
    const current = new Date(startDate)
    const end = new Date(endDate)

    while (current <= end) {
      const dateStr = formatDate(current)
      const override = overrideMap.get(dateStr)
      const dayStart = override ? override.startTime : defaultStartTime
      const dayEnd = override ? override.endTime : defaultEndTime

      const daySlots = generateSlotsForDay(eventName, dateStr, dayStart, dayEnd, slotDurationMinutes)
      slots.push(...daySlots)

      current.setDate(current.getDate() + 1)
    }

    return slots
  })

  const totalSlots = computed(() => previewSlots.value.length)

  const totalDays = computed(() => new Set(previewSlots.value.map((s) => s.date)).size)

  const slotsByDate = computed(() => {
    const grouped = new Map<string, PreviewSlot[]>()
    for (const slot of previewSlots.value) {
      const existing = grouped.get(slot.date) ?? []
      existing.push(slot)
      grouped.set(slot.date, existing)
    }
    return grouped
  })

  return { previewSlots, totalSlots, totalDays, slotsByDate }
}

function formatDate(d: Date): string {
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function generateSlotsForDay(
  eventName: string,
  dateStr: string,
  startTime: string,
  endTime: string,
  durationMinutes: number,
): PreviewSlot[] {
  const slots: PreviewSlot[] = []
  const startMinutes = timeToMinutes(startTime)
  const endMinutes = timeToMinutes(endTime)

  if (startMinutes >= endMinutes) return []

  let current = startMinutes
  while (current + durationMinutes <= endMinutes) {
    const slotStart = minutesToTime(current)
    const slotEnd = minutesToTime(current + durationMinutes)
    slots.push({
      date: dateStr,
      startTime: slotStart,
      endTime: slotEnd,
      title: `${eventName} ${slotStart}-${slotEnd}`,
    })
    current += durationMinutes
  }

  return slots
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
