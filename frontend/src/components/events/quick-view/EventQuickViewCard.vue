<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { MapPin, Tag, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'
import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'

import type { FeedEventItem, FeedSlotEntry, SlotWindowResponse } from '@/client/types.gen'
import { toastApiError } from '@/lib/api-errors'
import { statusVariant } from '@/lib/status'

import WeekDayColumns from './WeekDayColumns.vue'
import type { DayColumn, DaySlotEntry } from './WeekDayColumns.vue'

const props = defineProps<{
  event: FeedEventItem
  visibleDays?: number
  hideFullSlots?: boolean
}>()

const emit = defineEmits<{
  navigate: [event: FeedEventItem]
  delete: [event: FeedEventItem]
  clickSlot: [slotId: string, event: FeedEventItem]
}>()

const { t } = useI18n()
const authStore = useAuthStore()
const { get } = useAuthenticatedClient()

const numDays = computed(() => props.visibleDays ?? 5)
const weekOffset = ref(0)
const expanded = ref(false)
const loadingWindow = ref(false)

// Cache of fetched slot windows keyed by "YYYY-MM-DD" start date
const slotCache = ref<Map<string, FeedSlotEntry[]>>(new Map())

// Window start date from feed (initial window)
const initialWindowStart = computed(() => {
  if (props.event.slot_window_start) {
    const [y, m, d] = props.event.slot_window_start.split('-').map(Number)
    return new Date(y, m - 1, d)
  }
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return today
})

const startDate = computed(() => {
  const d = new Date(initialWindowStart.value)
  d.setDate(d.getDate() + weekOffset.value * numDays.value)
  return d
})

function dateStr(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function feedSlotsToDay(slots: FeedSlotEntry[]): Map<string, DaySlotEntry[]> {
  const map = new Map<string, DaySlotEntry[]>()
  for (const slot of slots) {
    const key = slot.date
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push({
      slotId: slot.id,
      startTime: slot.start_time,
      endTime: slot.end_time,
      currentBookings: slot.current_bookings,
      maxBookings: slot.max_bookings,
      isBookedByMe: slot.is_booked_by_me,
    })
  }
  return map
}

// Get the active slots for the current window (from cache or initial feed)
const activeSlots = computed<FeedSlotEntry[]>(() => {
  const key = dateStr(startDate.value)
  // Check cache first
  if (slotCache.value.has(key)) {
    return slotCache.value.get(key)!
  }
  // If offset is 0, use the initial feed data
  if (weekOffset.value === 0) {
    return props.event.slots ?? []
  }
  // No data yet for this window
  return []
})

const days = computed<DayColumn[]>(() => {
  const slotsByDate = feedSlotsToDay(activeSlots.value)
  const result: DayColumn[] = []

  for (let i = 0; i < numDays.value; i++) {
    const date = new Date(startDate.value)
    date.setDate(date.getDate() + i)
    const ds = dateStr(date)
    const daySlots = slotsByDate.get(ds) ?? []
    daySlots.sort((a, b) => (a.startTime ?? '').localeCompare(b.startTime ?? ''))
    result.push({ date, dateStr: ds, slots: daySlots })
  }

  return result
})

const totalAvailableSlots = computed(() => {
  const slots = props.event.slots ?? []
  return slots.filter((s) => {
    if (!s.max_bookings) return true
    return (s.current_bookings ?? 0) < s.max_bookings
  }).length
})

// Fetch a slot window for a given start date
async function fetchSlotWindow(start: Date) {
  const key = dateStr(start)
  if (slotCache.value.has(key)) return
  loadingWindow.value = true
  try {
    const res = await get<{ data: SlotWindowResponse }>({
      url: `/events/${props.event.id}/slot-window`,
      query: { start_date: key, days: numDays.value },
    })
    const newCache = new Map(slotCache.value)
    newCache.set(key, res.data.slots)
    slotCache.value = newCache
  } catch (error) {
    toastApiError(error)
  } finally {
    loadingWindow.value = false
  }
}

// When weekOffset changes and we don't have data, fetch
watch(weekOffset, () => {
  if (weekOffset.value === 0) return // initial data from feed
  const key = dateStr(startDate.value)
  if (!slotCache.value.has(key)) {
    fetchSlotWindow(startDate.value)
  }
})

// Reset cache when the event changes (e.g. feed re-fetched)
watch(
  () => props.event.id,
  () => {
    slotCache.value = new Map()
    weekOffset.value = 0
  },
)
</script>

<template>
  <div class="overflow-hidden rounded-lg border bg-card transition-colors hover:bg-muted/30">
    <div class="flex flex-col md:flex-row md:min-h-[260px]">
      <!-- Top/Left: Event Info -->
      <div
        class="flex cursor-pointer flex-col justify-between border-b p-4 md:w-56 md:shrink-0 md:border-b-0 md:border-r"
        @click="emit('navigate', event)"
      >
        <div class="space-y-2">
          <div class="flex items-start justify-between gap-2">
            <h3 class="text-sm font-semibold leading-tight line-clamp-2 break-words">
              {{ event.name }}
            </h3>
            <Badge
              :variant="statusVariant(event.status)"
              class="shrink-0 text-[10px]"
              v-if="authStore.isAdmin"
            >
              {{ t(`duties.events.statuses.${event.status ?? 'draft'}`) }}
            </Badge>
          </div>

          <p
            v-if="event.description"
            class="text-xs text-muted-foreground line-clamp-2 break-words"
          >
            {{ event.description }}
          </p>

          <div class="space-y-1">
            <div
              v-if="event.location"
              class="flex items-center gap-1 text-xs text-muted-foreground"
            >
              <MapPin class="h-3 w-3 shrink-0" />
              <span class="truncate">{{ event.location }}</span>
            </div>
            <div
              v-if="event.category"
              class="flex items-center gap-1 text-xs text-muted-foreground"
            >
              <Tag class="h-3 w-3 shrink-0" />
              <span class="truncate">{{ event.category }}</span>
            </div>
          </div>
        </div>

        <div class="mt-3 flex items-center justify-between">
          <span class="text-xs text-muted-foreground">
            {{ t('duties.events.quickView.availableSlots', { count: totalAvailableSlots }) }}
          </span>
          <Button
            v-if="authStore.isAdmin"
            variant="ghost"
            size="icon"
            class="h-6 w-6"
            @click.stop="emit('delete', event)"
          >
            <Trash2 class="h-3.5 w-3.5 text-destructive" />
          </Button>
        </div>
      </div>

      <!-- Right: Week Day Columns -->
      <div class="flex min-h-0 flex-1 flex-col p-2">
        <WeekDayColumns
          ref="weekColumns"
          :days="days"
          :visible-days="numDays"
          :expanded="expanded"
          :hide-full-slots="hideFullSlots"
          @previous="weekOffset--"
          @next="weekOffset++"
          @click-slot="(slotId) => emit('clickSlot', slotId, event)"
          @toggle-expand="expanded = !expanded"
        />
      </div>
    </div>
  </div>
</template>
