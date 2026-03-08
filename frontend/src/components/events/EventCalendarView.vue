<script setup lang="ts">
import { computed, ref } from 'vue'

import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import type { EventGroupRead, EventRead } from '@/client/types.gen'
import Button from '@/components/ui/button/Button.vue'

const props = defineProps<{
  events: EventRead[]
  eventGroups?: EventGroupRead[]
}>()

const emit = defineEmits<{
  navigate: [event: EventRead]
  navigateGroup: [group: EventGroupRead]
}>()

const { t, locale } = useI18n()

const calendarDate = ref(new Date())

const calendarTitle = computed(() =>
  calendarDate.value.toLocaleDateString(locale.value, { month: 'long', year: 'numeric' }),
)

const weekdayNames = computed(() => {
  const fmt = new Intl.DateTimeFormat(locale.value, { weekday: 'short' })
  return Array.from({ length: 7 }, (_, i) => fmt.format(new Date(2024, 0, i + 1)))
})

const toDateStr = (year: number, month: number, day: number) =>
  `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`

interface CalendarDay {
  date: Date | null
  dateStr: string | null
  events: EventRead[]
  groups: EventGroupRead[]
}

interface GroupBar {
  group: EventGroupRead
  startCol: number
  span: number
  lane: number
  isStart: boolean
  isEnd: boolean
}

interface CalendarWeek {
  days: CalendarDay[]
  groupBars: GroupBar[]
  barLaneCount: number
}

const calendarWeeks = computed<CalendarWeek[]>(() => {
  const year = calendarDate.value.getFullYear()
  const month = calendarDate.value.getMonth()

  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)

  let startDow = firstDay.getDay()
  startDow = startDow === 0 ? 6 : startDow - 1

  const allDays: CalendarDay[] = []

  for (let i = 0; i < startDow; i++) {
    allDays.push({ date: null, dateStr: null, events: [], groups: [] })
  }

  for (let d = 1; d <= lastDay.getDate(); d++) {
    const date = new Date(year, month, d)
    const dateStr = toDateStr(year, month, d)
    const dayEvents = props.events.filter(
      (e) => e.start_date <= dateStr && e.end_date >= dateStr,
    )
    const dayGroups = (props.eventGroups ?? []).filter(
      (g) => g.start_date <= dateStr && g.end_date >= dateStr,
    )
    allDays.push({ date, dateStr, events: dayEvents, groups: dayGroups })
  }

  while (allDays.length % 7 !== 0) {
    allDays.push({ date: null, dateStr: null, events: [], groups: [] })
  }

  // Split into weeks and compute group bars
  const weeks: CalendarWeek[] = []

  for (let i = 0; i < allDays.length; i += 7) {
    const weekDays = allDays.slice(i, i + 7)

    // Collect unique groups in this week (preserve order)
    const seen = new Set<string>()
    const groupsInWeek: EventGroupRead[] = []
    for (const day of weekDays) {
      for (const g of day.groups) {
        if (!seen.has(g.id)) {
          seen.add(g.id)
          groupsInWeek.push(g)
        }
      }
    }

    // Compute bar positions per group
    const groupBars: GroupBar[] = groupsInWeek.map((group, lane) => {
      let startCol = -1
      let endCol = -1
      for (let col = 0; col < 7; col++) {
        if (weekDays[col].groups.some((g) => g.id === group.id)) {
          if (startCol === -1) startCol = col
          endCol = col
        }
      }

      const startDay = weekDays[startCol]
      const endDay = weekDays[endCol]
      const isStart = startDay.dateStr === group.start_date
      const isEnd = endDay.dateStr === group.end_date

      return { group, startCol, span: endCol - startCol + 1, lane, isStart, isEnd }
    })

    weeks.push({ days: weekDays, groupBars, barLaneCount: groupBars.length })
  }

  return weeks
})

const prevMonth = () => {
  const d = new Date(calendarDate.value)
  d.setMonth(d.getMonth() - 1)
  calendarDate.value = d
}

const nextMonth = () => {
  const d = new Date(calendarDate.value)
  d.setMonth(d.getMonth() + 1)
  calendarDate.value = d
}

const todayStr = toDateStr(
  new Date().getFullYear(),
  new Date().getMonth(),
  new Date().getDate(),
)
const isToday = (date: Date | null) =>
  date !== null &&
  toDateStr(date.getFullYear(), date.getMonth(), date.getDate()) === todayStr
</script>

<template>
  <!-- Month navigation -->
  <div class="flex items-center justify-between">
    <Button variant="outline" size="icon" @click="prevMonth">
      <ChevronLeft class="h-4 w-4" />
    </Button>
    <h2 class="text-base font-semibold capitalize sm:text-lg">{{ calendarTitle }}</h2>
    <Button variant="outline" size="icon" @click="nextMonth">
      <ChevronRight class="h-4 w-4" />
    </Button>
  </div>

  <!-- Calendar grid -->
  <div class="overflow-hidden rounded-lg border">
    <!-- Weekday headers -->
    <div class="grid grid-cols-7 border-b bg-muted/50">
      <div
        v-for="name in weekdayNames"
        :key="name"
        class="py-2 text-center text-xs font-medium text-muted-foreground"
      >
        {{ name }}
      </div>
    </div>

    <!-- Week rows -->
    <div
      v-for="(week, weekIdx) in calendarWeeks"
      :key="weekIdx"
      class="relative"
      :class="weekIdx > 0 ? 'border-t border-border' : ''"
    >
      <!-- Group bars overlay -->
      <div
        v-for="bar in week.groupBars"
        :key="'bar-' + bar.group.id"
        class="absolute z-10 hidden sm:block"
        :style="{
          top: `${28 + bar.lane * 22}px`,
          left: `calc(${bar.startCol} / 7 * 100% + 4px)`,
          width: `calc(${bar.span} / 7 * 100% - 8px)`,
          height: '20px',
        }"
      >
        <button
          class="flex h-full w-full items-center truncate px-1.5 text-left text-xs font-medium bg-amber-500/15 text-amber-700 dark:text-amber-400 hover:bg-amber-500/25 transition-colors"
          :class="[
            bar.isStart && bar.isEnd ? 'rounded' :
            bar.isStart ? 'rounded-l' :
            bar.isEnd ? 'rounded-r' :
            '',
          ]"
          :style="{
            marginLeft: bar.isStart ? '0' : '-4px',
            paddingLeft: bar.isStart ? undefined : '0',
            width: !bar.isStart && !bar.isEnd ? 'calc(100% + 8px)' :
                   !bar.isStart ? 'calc(100% + 4px)' :
                   !bar.isEnd ? 'calc(100% + 4px)' :
                   undefined,
          }"
          @click="emit('navigateGroup', bar.group)"
        >
          <span v-if="bar.isStart || bar.startCol === 0" class="truncate">{{ bar.group.name }}</span>
        </button>
      </div>

      <!-- Day cells -->
      <div class="grid grid-cols-7">
        <div
          v-for="(day, dayIdx) in week.days"
          :key="dayIdx"
          class="min-h-[72px] p-1 sm:min-h-[100px] sm:p-1.5"
          :class="[
            day.date ? 'bg-background' : 'bg-muted/30',
            dayIdx < 6 ? 'border-r border-border' : '',
          ]"
        >
          <template v-if="day.date">
            <!-- Day number -->
            <div
              class="mb-1 flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium"
              :class="
                isToday(day.date)
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground'
              "
            >
              {{ day.date.getDate() }}
            </div>

            <!-- Spacer for group bar lanes (desktop) -->
            <div
              v-if="week.barLaneCount > 0"
              class="hidden sm:block"
              :style="{ height: `${week.barLaneCount * 22}px` }"
            />

            <!-- Mobile: group dots -->
            <template v-if="day.groups.length > 0">
              <div
                v-for="group in day.groups.slice(0, 2)"
                :key="'mg-' + group.id"
                class="flex items-center sm:hidden"
                @click="emit('navigateGroup', group)"
              >
                <span class="h-1.5 w-1.5 rounded-full bg-amber-500" />
              </div>
            </template>

            <!-- Event chips -->
            <div class="space-y-0.5">
              <template v-for="event in day.events.slice(0, 3)" :key="event.id">
                <!-- Mobile: dot only -->
                <div
                  class="flex items-center sm:hidden"
                  @click="emit('navigate', event)"
                >
                  <span
                    class="h-1.5 w-1.5 rounded-full"
                    :class="
                      event.status === 'published' ? 'bg-primary' : 'bg-muted-foreground'
                    "
                  />
                </div>
                <!-- sm+: text chip -->
                <button
                  class="hidden w-full truncate rounded px-1 py-0.5 text-left text-xs font-medium transition-opacity hover:opacity-75 sm:block"
                  :class="
                    event.status === 'published'
                      ? 'bg-primary/15 text-primary'
                      : 'bg-muted text-muted-foreground'
                  "
                  @click="emit('navigate', event)"
                >
                  {{ event.name }}
                </button>
              </template>

              <!-- Overflow indicator -->
              <div
                v-if="day.events.length > 3"
                class="px-1 text-xs text-muted-foreground"
              >
                +{{ day.events.length - 3 }} {{ t('duties.events.calendar.more') }}
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
