<script setup lang="ts">
import { ShiftCalendar } from '@/components/tasks/shift-calendar'
import type {
  CalendarTask,
  CalendarEvent,
  DateRange,
  ViewMode,
} from '@/components/tasks/shift-calendar'

import type { EventRead, TaskRead } from '@/client/types.gen'

defineProps<{
  tasks: TaskRead[]
  events?: EventRead[]
  calendarViewMode?: ViewMode
  calendarDate?: string
}>()

const emit = defineEmits<{
  navigate: [task: CalendarTask]
  navigateGroup: [group: CalendarEvent]
  'update:dateRange': [range: DateRange]
  'update:calendarViewMode': [mode: ViewMode]
  'update:calendarDate': [date: string]
}>()
</script>

<template>
  <ShiftCalendar
    :tasks="tasks"
    :events="events"
    :show-bookings="false"
    :calendar-view-mode="calendarViewMode"
    :calendar-date="calendarDate"
    @navigate-task="emit('navigate', $event)"
    @navigate-group="emit('navigateGroup', $event)"
    @update:date-range="emit('update:dateRange', $event)"
    @update:calendar-view-mode="emit('update:calendarViewMode', $event)"
    @update:calendar-date="emit('update:calendarDate', $event)"
  />
</template>
