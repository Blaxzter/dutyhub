<script setup lang="ts">
import type { EventGroupRead, EventRead } from '@/client/types.gen'

import { DutyCalendar } from '@/components/events/duty-calendar'
import type { CalendarEvent, CalendarEventGroup, DateRange, ViewMode } from '@/components/events/duty-calendar'

defineProps<{
  events: EventRead[]
  eventGroups?: EventGroupRead[]
  calendarViewMode?: ViewMode
  calendarDate?: string
}>()

const emit = defineEmits<{
  navigate: [event: CalendarEvent]
  navigateGroup: [group: CalendarEventGroup]
  'update:dateRange': [range: DateRange]
  'update:calendarViewMode': [mode: ViewMode]
  'update:calendarDate': [date: string]
}>()
</script>

<template>
  <DutyCalendar
    :events="events"
    :event-groups="eventGroups"
    :show-bookings="false"
    :calendar-view-mode="calendarViewMode"
    :calendar-date="calendarDate"
    @navigate-event="emit('navigate', $event)"
    @navigate-group="emit('navigateGroup', $event)"
    @update:date-range="emit('update:dateRange', $event)"
    @update:calendar-view-mode="emit('update:calendarViewMode', $event)"
    @update:calendar-date="emit('update:calendarDate', $event)"
  />
</template>
