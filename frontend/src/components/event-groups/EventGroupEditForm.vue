<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import type { DateValue } from '@internationalized/date'
import { parseDate } from '@internationalized/date'
import { CalendarClock, Check, MoveRight, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { MarkerVariant } from '@/components/ui/calendar'
import { DatePicker } from '@/components/ui/date-picker'
import Input from '@/components/ui/input/Input.vue'
import Label from '@/components/ui/label/Label.vue'
import Separator from '@/components/ui/separator/Separator.vue'
import Textarea from '@/components/ui/textarea/Textarea.vue'

import type { EventGroupRead, EventRead } from '@/client/types.gen'
import { toastApiError } from '@/lib/api-errors'
import { formatDate } from '@/lib/format'

const props = defineProps<{
  group: EventGroupRead
  groupId: string
  events: EventRead[]
}>()

const emit = defineEmits<{
  updated: [group: EventGroupRead]
  cancel: []
}>()

const { t } = useI18n()
const { get, patch, post } = useAuthenticatedClient()

// ── Edit form state ──
const name = ref(props.group.name)
const description = ref(props.group.description ?? '')
const startDate = ref<DateValue>()
const endDate = ref<DateValue>()
const saving = ref(false)

// Event date bounds for constraining pickers
const earliestEventDate = ref<DateValue>()
const latestEventDate = ref<DateValue>()
const hasEvents = computed(() => !!earliestEventDate.value)

function toLocalIso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// Markers: event start dates (green), end dates (red), other event days (default dot), today (blue)
const eventMarkers = computed(() => {
  const markers = new Map<string, MarkerVariant>()
  const todayIso = toLocalIso(new Date())
  for (const ev of props.events) {
    const isSingleDay = ev.start_date === ev.end_date
    // Fill range with default dots
    const start = new Date(ev.start_date + 'T00:00:00')
    const end = new Date(ev.end_date + 'T00:00:00')
    for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
      if (!markers.has(toLocalIso(d))) markers.set(toLocalIso(d), 'default')
    }
    // Multi-day events get colored start/end dots
    if (!isSingleDay) {
      markers.set(ev.start_date, 'start')
      markers.set(ev.end_date, 'end')
    }
  }
  if (!markers.has(todayIso)) markers.set(todayIso, 'today')
  return markers
})

// ── Shift dates state ──
const shiftTargetDate = ref<DateValue>()
const shifting = ref(false)

const shiftDays = computed(() => {
  if (!shiftTargetDate.value || !startDate.value) return 0
  return shiftTargetDate.value.compare(parseDate(props.group.start_date))
})

async function loadEventDateBounds() {
  try {
    const res = await get<{ data: { earliest_start: string | null; latest_end: string | null } }>({
      url: `/event-groups/${props.groupId}/event-date-bounds`,
    })
    earliestEventDate.value = res.data.earliest_start
      ? parseDate(res.data.earliest_start)
      : undefined
    latestEventDate.value = res.data.latest_end ? parseDate(res.data.latest_end) : undefined
  } catch {
    // Non-critical
  }
}

async function handleSubmit() {
  if (!startDate.value || !endDate.value || !name.value.trim()) return
  saving.value = true
  try {
    const res = await patch<{ data: EventGroupRead }>({
      url: `/event-groups/${props.groupId}`,
      body: {
        name: name.value.trim(),
        description: description.value.trim() || null,
        start_date: startDate.value.toString(),
        end_date: endDate.value.toString(),
      },
    })
    emit('updated', res.data)
    toast.success(t('duties.eventGroups.detail.updated'))
  } catch (error) {
    toastApiError(error)
  } finally {
    saving.value = false
  }
}

async function handleShiftDates() {
  if (!shiftTargetDate.value || shiftDays.value === 0) return
  shifting.value = true
  try {
    const res = await post<{ data: EventGroupRead }>({
      url: `/event-groups/${props.groupId}/shift-dates`,
      body: { new_start_date: shiftTargetDate.value.toString() },
    })
    emit('updated', res.data)
    toast.success(t('duties.eventGroups.detail.shiftSuccess'))
  } catch (error) {
    toastApiError(error)
  } finally {
    shifting.value = false
  }
}

onMounted(() => {
  startDate.value = parseDate(props.group.start_date)
  endDate.value = parseDate(props.group.end_date)
  loadEventDateBounds()
})
</script>

<template>
  <!-- Edit group details -->
  <Card>
    <CardHeader>
      <CardTitle>{{ t('duties.eventGroups.edit') }}</CardTitle>
      <CardDescription>{{ t('duties.eventGroups.detail.editDescription') }}</CardDescription>
    </CardHeader>
    <CardContent>
      <form class="space-y-4" @submit.prevent="handleSubmit">
        <div class="space-y-2">
          <Label>{{ t('duties.eventGroups.fields.name') }}</Label>
          <Input v-model="name" required />
        </div>
        <div class="space-y-2">
          <Label>{{ t('duties.eventGroups.fields.description') }}</Label>
          <Textarea v-model="description" rows="2" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <Label>{{ t('duties.eventGroups.fields.startDate') }}</Label>
            <DatePicker
              v-model="startDate"
              :max-value="latestEventDate"
              :markers="eventMarkers"
              :placeholder="t('duties.eventGroups.pickDate')"
            />
            <p v-if="earliestEventDate" class="text-xs text-muted-foreground">
              {{ t('duties.eventGroups.detail.earliestEvent', { date: formatDate(earliestEventDate.toString()) }) }}
            </p>
          </div>
          <div class="space-y-1.5">
            <Label>{{ t('duties.eventGroups.fields.endDate') }}</Label>
            <DatePicker
              v-model="endDate"
              :min-value="earliestEventDate"
              :markers="eventMarkers"
              :placeholder="t('duties.eventGroups.pickDate')"
            />
            <p v-if="latestEventDate" class="text-xs text-muted-foreground">
              {{ t('duties.eventGroups.detail.latestEvent', { date: formatDate(latestEventDate.toString()) }) }}
            </p>
          </div>
        </div>
        <div v-if="hasEvents" class="space-y-1.5">
          <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span class="flex items-center gap-1.5">
              <span class="size-2 rounded-full bg-green-500" />
              {{ t('duties.eventGroups.detail.legend.eventStart') }}
            </span>
            <span class="flex items-center gap-1.5">
              <span class="size-2 rounded-full bg-red-500" />
              {{ t('duties.eventGroups.detail.legend.eventEnd') }}
            </span>
            <span class="flex items-center gap-1.5">
              <span class="size-2 rounded-full bg-primary" />
              {{ t('duties.eventGroups.detail.legend.eventDay') }}
            </span>
            <span class="flex items-center gap-1.5">
              <span class="size-2 rounded-full bg-blue-500" />
              {{ t('duties.eventGroups.detail.legend.today') }}
            </span>
          </div>
          <p class="text-xs text-muted-foreground">
            {{ t('duties.eventGroups.detail.dateConstraintHint') }}
          </p>
        </div>
        <div class="flex items-center gap-2 pt-2">
          <Button type="submit" size="sm" :disabled="saving">
            <Check class="mr-2 h-4 w-4" />
            {{ t('common.actions.save') }}
          </Button>
          <Button type="button" variant="outline" size="sm" :disabled="saving" @click="emit('cancel')">
            <X class="mr-2 h-4 w-4" />
            {{ t('common.actions.cancel') }}
          </Button>
        </div>
      </form>
    </CardContent>
  </Card>

  <!-- Shift dates -->
  <Card v-if="hasEvents">
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <CalendarClock class="h-5 w-5" />
        {{ t('duties.eventGroups.detail.shiftDates') }}
      </CardTitle>
      <CardDescription>{{ t('duties.eventGroups.detail.shiftDescription') }}</CardDescription>
    </CardHeader>
    <CardContent>
      <div class="space-y-4">
        <div class="space-y-1.5">
          <Label>{{ t('duties.eventGroups.detail.shiftNewStart') }}</Label>
          <DatePicker
            v-model="shiftTargetDate"
            :placeholder="t('duties.eventGroups.pickDate')"
            :highlight="startDate"
            :markers="eventMarkers"
          />
        </div>
        <p v-if="shiftDays !== 0" class="text-sm text-muted-foreground">
          {{ t('duties.eventGroups.detail.shiftPreview', { days: Math.abs(shiftDays), direction: shiftDays > 0 ? t('duties.eventGroups.detail.shiftForward') : t('duties.eventGroups.detail.shiftBackward') }) }}
        </p>
        <Separator />
        <Button
          size="sm"
          :disabled="shifting || shiftDays === 0"
          @click="handleShiftDates"
        >
          <MoveRight class="mr-2 h-4 w-4" />
          {{ t('duties.eventGroups.detail.shiftApply') }}
        </Button>
      </div>
    </CardContent>
  </Card>
</template>
