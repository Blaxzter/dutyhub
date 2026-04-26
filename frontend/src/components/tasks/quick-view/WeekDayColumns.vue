<script setup lang="ts">
import { computed } from 'vue'

import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { useFormatters } from '@/composables/useFormatters'

import Button from '@/components/ui/button/Button.vue'

export interface DayShiftEntry {
  slotId: string
  startTime?: string | null
  endTime?: string | null
  currentBookings?: number
  maxBookings?: number
  isBookedByMe?: boolean
}

export interface DayColumn {
  date: Date
  dateStr: string
  shifts: DayShiftEntry[]
}

const props = defineProps<{
  days: DayColumn[]
  visibleDays?: number
  expanded?: boolean
  hideFullShifts?: boolean
}>()

const emit = defineEmits<{
  previous: []
  next: []
  clickShift: [slotId: string]
  toggleExpand: []
}>()

const { t, locale } = useI18n()
const { formatTime } = useFormatters()

const COLLAPSED_LIMIT = 4

const cols = computed(() => props.visibleDays ?? 5)

const today = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
})

function filteredShifts(day: DayColumn): DayShiftEntry[] {
  if (!props.hideFullShifts) return day.shifts
  return day.shifts.filter((s) => slotHasCapacity(s))
}

const maxShiftCount = computed(() => {
  if (props.expanded) return Math.max(...props.days.map((d) => filteredShifts(d).length), 0)
  return Math.min(Math.max(...props.days.map((d) => filteredShifts(d).length), 0), COLLAPSED_LIMIT)
})

const totalHidden = computed(() => {
  if (props.expanded) return 0
  return props.days.reduce(
    (sum, d) => sum + Math.max(0, filteredShifts(d).length - COLLAPSED_LIMIT),
    0,
  )
})

function columnHidden(day: DayColumn): number {
  if (props.expanded) return 0
  return Math.max(0, filteredShifts(day).length - COLLAPSED_LIMIT)
}

function visibleShifts(day: DayColumn) {
  const shifts = filteredShifts(day)
  if (props.expanded) return shifts
  return shifts.slice(0, COLLAPSED_LIMIT)
}

function formatDayLabel(date: Date): string {
  return date.toLocaleDateString(locale.value, { weekday: 'short' })
}

function formatDayDate(date: Date): string {
  return date.toLocaleDateString(locale.value, { day: 'numeric', month: 'short' })
}

function slotHasCapacity(shift: DayShiftEntry): boolean {
  if (!shift.maxBookings) return true
  return (shift.currentBookings ?? 0) < shift.maxBookings
}

function slotClasses(shift: DayShiftEntry): string {
  if (shift.isBookedByMe) {
    return 'border-green-500/40 bg-green-500/15 text-green-700 dark:text-green-400 font-semibold hover:bg-green-500/25'
  }
  if (slotHasCapacity(shift)) {
    return 'border-primary/30 text-primary hover:bg-primary/10'
  }
  return 'border-muted text-muted-foreground opacity-60 hover:opacity-80 hover:bg-muted/50'
}

function slotCountClasses(shift: DayShiftEntry): string {
  if (shift.isBookedByMe) return 'text-green-600/70 dark:text-green-400/70'
  if (slotHasCapacity(shift)) return 'text-primary/60'
  return 'text-muted-foreground/60'
}

defineExpose({ totalHidden, maxShiftCount })
</script>

<template>
  <div class="flex h-full flex-col">
    <!-- Header row: arrows + day labels -->
    <div class="flex items-center">
      <button
        class="flex w-6 shrink-0 items-center justify-center text-muted-foreground hover:text-foreground"
        @click="emit('previous')"
      >
        <ChevronLeft class="h-4 w-4" />
      </button>

      <div class="grid flex-1" :style="{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }">
        <div
          v-for="day in days"
          :key="day.dateStr"
          class="px-1 py-1.5 text-center"
          :class="day.dateStr === today ? 'bg-primary/5 rounded-t-md' : ''"
        >
          <div
            class="text-xs font-medium"
            :class="day.dateStr === today ? 'text-primary' : 'text-muted-foreground'"
          >
            {{ formatDayLabel(day.date) }}
          </div>
          <div
            class="text-xs"
            :class="day.dateStr === today ? 'text-primary font-semibold' : 'text-muted-foreground'"
          >
            {{ formatDayDate(day.date) }}
          </div>
        </div>
      </div>

      <button
        class="flex w-6 shrink-0 items-center justify-center text-muted-foreground hover:text-foreground"
        @click="emit('next')"
      >
        <ChevronRight class="h-4 w-4" />
      </button>
    </div>

    <!-- Shift grid: no arrows, grows to fill -->
    <div class="flex min-h-0 flex-1">
      <!-- Spacer matching left arrow width -->
      <div class="w-6 shrink-0" />

      <div
        class="grid min-h-0 flex-1"
        :style="{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }"
      >
        <div
          v-for="day in days"
          :key="'shifts-' + day.dateStr"
          class="flex flex-col gap-1 px-1 py-1"
          :class="day.dateStr === today ? 'bg-primary/5 rounded-b-md' : ''"
        >
          <template v-if="filteredShifts(day).length > 0">
            <Button
              v-for="shift in visibleShifts(day)"
              :key="shift.slotId"
              variant="outline"
              size="sm"
              class="h-auto w-full px-1.5 py-1 text-xs"
              :class="slotClasses(shift)"
              @click="emit('clickShift', shift.slotId)"
            >
              <div class="flex w-full flex-col items-center gap-0.5">
                <span>{{ formatTime(shift.startTime) || '—' }}</span>
                <span class="text-[10px] leading-none" :class="slotCountClasses(shift)">
                  {{ shift.currentBookings ?? 0 }}/{{ shift.maxBookings ?? '—' }}
                </span>
              </div>
            </Button>
            <!-- Per-column show more -->
            <button
              v-if="columnHidden(day) > 0"
              class="mt-0.5 rounded px-1 py-1 text-center text-[10px] font-medium text-primary hover:bg-primary/10"
              @click="emit('toggleExpand')"
            >
              {{ t('duties.tasks.quickView.showMore', { count: columnHidden(day) }) }}
            </button>
          </template>
          <!-- Per-column show less -->
          <button
            v-if="expanded && filteredShifts(day).length > COLLAPSED_LIMIT"
            class="mt-0.5 rounded px-1 py-1 text-center text-[10px] font-medium text-muted-foreground hover:bg-muted/50"
            @click="emit('toggleExpand')"
          >
            {{ t('duties.tasks.quickView.showLess') }}
          </button>
          <!-- Empty day: show dash, flex-grow to fill height -->
          <div
            v-if="filteredShifts(day).length === 0"
            class="flex flex-1 items-center justify-center text-xs text-muted-foreground"
          >
            —
          </div>
        </div>
      </div>

      <!-- Spacer matching right arrow width -->
      <div class="w-6 shrink-0" />
    </div>
  </div>
</template>
