<script setup lang="ts">
import { computed, onMounted, ref, toRaw, watch } from 'vue'

import type { DateValue } from '@internationalized/date'
import { parseDate } from '@internationalized/date'
import { ArrowLeft, CalendarDays, CalendarPlus, Clock, Plus, Trash2, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import type { EventGroupRead, EventRead } from '@/client/types.gen'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent } from '@/components/ui/card'
import {
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { DatePicker } from '@/components/ui/date-picker'
import Input from '@/components/ui/input/Input.vue'
import Label from '@/components/ui/label/Label.vue'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import Separator from '@/components/ui/separator/Separator.vue'
import { TimePicker } from '@/components/ui/time-picker'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { type RemainderMode, type ScheduleConfig, useSlotPreview } from '@/composables/useSlotPreview'
import { toastApiError } from '@/lib/api-errors'
import { useBreadcrumbStore } from '@/stores/breadcrumb'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const breadcrumbStore = useBreadcrumbStore()
const { get, post } = useAuthenticatedClient()

const eventId = computed(() => route.params.eventId as string)
const loading = ref(true)
const submitting = ref(false)
const event = ref<EventRead | null>(null)
const eventGroup = ref<EventGroupRead | null>(null)

// --- Event group date constraints ---
const groupMinDate = computed(() => eventGroup.value ? parseDate(eventGroup.value.start_date) : undefined)
const groupMaxDate = computed(() => eventGroup.value ? parseDate(eventGroup.value.end_date) : undefined)

// --- Batch-specific fields ---
const location = ref('')
const category = ref('')

// --- Dates ---
const dateMode = ref<'single' | 'range' | 'specific'>('single')
const singleDate = ref<DateValue>()
const rangeStartDate = ref<DateValue>()
const rangeEndDate = ref<DateValue>()
const specificDates = ref<DateValue[]>([])
const specificDatePicker = ref<DateValue>()

const startDate = computed((): DateValue | undefined => {
  if (dateMode.value === 'single') return singleDate.value
  if (dateMode.value === 'range') return rangeStartDate.value
  if (dateMode.value === 'specific' && specificDates.value.length > 0) {
    const raw = specificDates.value.map((d) => toRaw(d))
    let min = raw[0]
    for (const d of raw) {
      if (d.compare(min) < 0) min = d
    }
    return min
  }
  return undefined
})

const endDate = computed((): DateValue | undefined => {
  if (dateMode.value === 'single') return singleDate.value
  if (dateMode.value === 'range') return rangeEndDate.value
  if (dateMode.value === 'specific' && specificDates.value.length > 0) {
    const raw = specificDates.value.map((d) => toRaw(d))
    let max = raw[0]
    for (const d of raw) {
      if (d.compare(max) > 0) max = d
    }
    return max
  }
  return undefined
})

const addSpecificDate = () => {
  if (!specificDatePicker.value) return
  const newDate = toRaw(specificDatePicker.value)
  const already = specificDates.value.some((d) => toRaw(d).compare(newDate) === 0)
  if (!already) {
    specificDates.value.push(newDate)
    specificDates.value.sort((a, b) => (toRaw(a) as DateValue).compare(toRaw(b) as DateValue))
  }
  specificDatePicker.value = undefined
}

const removeSpecificDate = (index: number) => {
  specificDates.value.splice(index, 1)
}

watch(dateMode, () => {
  singleDate.value = undefined
  rangeStartDate.value = undefined
  rangeEndDate.value = undefined
  specificDates.value = []
  specificDatePicker.value = undefined
  overrides.value = []
})

// --- Schedule ---
const defaultStartTime = ref('10:00')
const defaultEndTime = ref('18:00')
const slotDurationMinutes = ref(30)
const peoplePerSlot = ref(2)
const remainderMode = ref<RemainderMode>('drop')
const overrides = ref<Array<{ date: string; startTime: string; endTime: string }>>([])

const durationOptions = [15, 30, 45, 60, 90, 120]

// --- Slot preview ---
const scheduleConfig = computed<ScheduleConfig>(() => ({
  eventName: event.value?.name || 'Event',
  startDate: startDate.value?.toString() ?? '',
  endDate: endDate.value?.toString() ?? '',
  specificDates: dateMode.value === 'specific'
    ? specificDates.value.map((d) => d.toString())
    : undefined,
  defaultStartTime: defaultStartTime.value,
  defaultEndTime: defaultEndTime.value,
  slotDurationMinutes: slotDurationMinutes.value,
  peoplePerSlot: peoplePerSlot.value,
  remainderMode: remainderMode.value,
  overrides: overrides.value,
}))

const { totalSlots, totalDays, slotsByDate, hasRemainder, excludedSlots, toggleSlotExclusion, isSlotExcluded } = useSlotPreview(scheduleConfig)

watch(rangeStartDate, (val) => {
  if (val && rangeEndDate.value && rangeEndDate.value.compare(val) < 0) {
    rangeEndDate.value = undefined
  }
})

watch(hasRemainder, (val) => {
  if (!val) remainderMode.value = 'drop'
})

// --- Available dates for exceptions ---
const availableDates = computed(() => {
  if (!startDate.value || !endDate.value) return []

  if (dateMode.value === 'specific') {
    return specificDates.value
      .map((d) => d.toString())
      .filter((dateStr) => !overrides.value.some((o) => o.date === dateStr))
  }

  const dates: string[] = []
  const start = new Date(startDate.value.toString())
  const end = new Date(endDate.value.toString())
  const current = new Date(start)
  while (current <= end) {
    const dateStr = current.toISOString().split('T')[0]
    if (!overrides.value.some((o) => o.date === dateStr)) {
      dates.push(dateStr)
    }
    current.setDate(current.getDate() + 1)
  }
  return dates
})

const addOverride = () => {
  overrides.value.push({
    date: '',
    startTime: defaultStartTime.value,
    endTime: defaultEndTime.value,
  })
}

const removeOverride = (index: number) => {
  overrides.value.splice(index, 1)
}

// --- Validation ---
const isDatesValid = computed(() => {
  if (dateMode.value === 'single') return !!singleDate.value
  if (dateMode.value === 'range') return !!rangeStartDate.value && !!rangeEndDate.value
  if (dateMode.value === 'specific') return specificDates.value.length > 0
  return false
})

const isValid = computed(() => {
  return isDatesValid.value
    && !!defaultStartTime.value && !!defaultEndTime.value
    && slotDurationMinutes.value >= 1 && totalSlots.value > 0
})

// --- Load event ---
const loadEvent = async () => {
  loading.value = true
  try {
    const response = await get<{ data: EventRead }>({
      url: `/events/${eventId.value}`,
    })
    event.value = response.data
    const ev = response.data

    // Fetch event group for date constraints
    if (ev.event_group_id) {
      try {
        const groupResponse = await get<{ data: EventGroupRead }>({
          url: `/event-groups/${ev.event_group_id}`,
        })
        eventGroup.value = groupResponse.data
      } catch {
        // Non-critical — continue without constraints
      }
    }

    // Pre-fill from event defaults
    location.value = ev.location ?? ''
    category.value = ev.category ?? ''
    if (ev.default_start_time) defaultStartTime.value = formatTime(ev.default_start_time)
    if (ev.default_end_time) defaultEndTime.value = formatTime(ev.default_end_time)
    if (ev.slot_duration_minutes) slotDurationMinutes.value = ev.slot_duration_minutes
    if (ev.people_per_slot) peoplePerSlot.value = ev.people_per_slot

    breadcrumbStore.setBreadcrumbs([
      { title: 'Events', titleKey: 'duties.events.title', to: { name: 'events' } },
      { title: ev.name, to: { name: 'event-detail', params: { eventId: ev.id } } },
      { title: t('duties.events.addSlotsView.title') },
    ])
  } catch (error) {
    toastApiError(error)
    router.push({ name: 'events' })
  } finally {
    loading.value = false
  }
}

// --- Submit ---
const handleSubmit = async () => {
  if (!isValid.value || submitting.value) return
  submitting.value = true

  try {
    const response = await post<{ data: { slots_added: number } }>({
      url: `/events/${eventId.value}/add-slots`,
      body: {
        start_date: startDate.value!.toString(),
        end_date: endDate.value!.toString(),
        location: location.value || null,
        category: category.value || null,
        schedule: {
          default_start_time: defaultStartTime.value + ':00',
          default_end_time: defaultEndTime.value + ':00',
          slot_duration_minutes: slotDurationMinutes.value,
          people_per_slot: peoplePerSlot.value,
          remainder_mode: remainderMode.value,
          overrides: overrides.value
            .filter((o) => o.date)
            .map((o) => ({
              date: o.date,
              start_time: o.startTime + ':00',
              end_time: o.endTime + ':00',
            })),
          excluded_slots: [...excludedSlots.value].map((key) => {
            const [date, start_time, end_time] = key.split('|')
            return { date, start_time: start_time + ':00', end_time: end_time + ':00' }
          }),
        },
      },
    })

    toast.success(t('duties.events.addSlotsView.success', { count: response.data.slots_added }))
    router.push({ name: 'event-detail', params: { eventId: eventId.value } })
  } catch (error) {
    toastApiError(error)
  } finally {
    submitting.value = false
  }
}

const formatTime = (time: string | null | undefined): string => {
  if (!time) return ''
  return time.substring(0, 5)
}

const formatDateLabel = (dateStr: string) => {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString(locale.value, { weekday: 'short', month: 'short', day: 'numeric' })
}

onMounted(loadEvent)
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <!-- Loading -->
    <div v-if="loading" class="text-center py-12 text-muted-foreground">
      {{ t('common.states.loading') }}
    </div>

    <template v-else-if="event">
      <!-- Header -->
      <div class="space-y-2">
        <Button variant="ghost" size="sm" class="-ml-2" @click="router.push({ name: 'event-detail', params: { eventId: eventId } })">
          <ArrowLeft class="mr-1.5 h-4 w-4" />
          {{ t('common.actions.back') }}
        </Button>
        <h1 class="text-3xl font-bold">{{ t('duties.events.addSlotsView.title') }}</h1>
        <p class="text-muted-foreground">
          {{ t('duties.events.addSlotsView.subtitle') }}
          <span class="font-medium text-foreground">{{ event.name }}</span>
        </p>
      </div>

      <!-- Batch Details (location / category) -->
      <Card>
        <CardHeader>
          <CardTitle>{{ t('duties.events.addSlotsView.sections.batch') }}</CardTitle>
          <CardDescription>{{ t('duties.events.addSlotsView.sections.batchDesc') }}</CardDescription>
        </CardHeader>
        <CardContent>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>{{ t('duties.events.fields.location') }}</Label>
              <Input v-model="location" />
            </div>
            <div class="space-y-2">
              <Label>{{ t('duties.events.fields.category') }}</Label>
              <Input v-model="category" />
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Dates -->
      <Card>
        <CardHeader>
          <div class="flex items-center gap-3">
            <CalendarDays class="h-5 w-5 text-primary" />
            <div>
              <CardTitle>{{ t('duties.events.createView.sections.dates') }}</CardTitle>
              <CardDescription>{{ t('duties.events.createView.sections.datesDesc') }}</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent class="space-y-4">
          <RadioGroup v-model="dateMode" class="flex gap-4">
            <div class="flex items-center gap-2">
              <RadioGroupItem value="single" id="dm-single" />
              <Label for="dm-single">{{ t('duties.events.createView.dateMode.single') }}</Label>
            </div>
            <div class="flex items-center gap-2">
              <RadioGroupItem value="range" id="dm-range" />
              <Label for="dm-range">{{ t('duties.events.createView.dateMode.range') }}</Label>
            </div>
            <div class="flex items-center gap-2">
              <RadioGroupItem value="specific" id="dm-specific" />
              <Label for="dm-specific">{{ t('duties.events.createView.dateMode.specific') }}</Label>
            </div>
          </RadioGroup>

          <!-- Single date -->
          <div v-if="dateMode === 'single'" class="space-y-2">
            <Label>{{ t('duties.dutySlots.fields.date') }} *</Label>
            <DatePicker v-model="singleDate" :min-value="groupMinDate" :max-value="groupMaxDate" />
          </div>

          <!-- Date range -->
          <div v-if="dateMode === 'range'" class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>{{ t('duties.events.fields.startDate') }} *</Label>
              <DatePicker v-model="rangeStartDate" :min-value="groupMinDate" :max-value="rangeEndDate || groupMaxDate" />
            </div>
            <div class="space-y-2">
              <Label>{{ t('duties.events.fields.endDate') }} *</Label>
              <DatePicker v-model="rangeEndDate" :min-value="rangeStartDate || groupMinDate" :max-value="groupMaxDate" :highlight="rangeStartDate" />
            </div>
          </div>

          <!-- Specific dates -->
          <div v-if="dateMode === 'specific'" class="space-y-3">
            <div class="flex items-end gap-3">
              <div class="flex-1 space-y-2">
                <Label>{{ t('duties.events.createView.addDate') }}</Label>
                <DatePicker v-model="specificDatePicker" :min-value="groupMinDate" :max-value="groupMaxDate" />
              </div>
              <Button :disabled="!specificDatePicker" @click="addSpecificDate">
                <Plus class="mr-1.5 h-4 w-4" />
                {{ t('duties.events.createView.addDate') }}
              </Button>
            </div>
            <div v-if="specificDates.length === 0" class="py-4 text-center text-sm text-muted-foreground">
              {{ t('duties.events.createView.noDatesSelected') }}
            </div>
            <div v-else class="flex flex-wrap gap-2">
              <Badge
                v-for="(date, index) in specificDates"
                :key="date.toString()"
                variant="secondary"
                class="gap-1 py-1.5 pl-3 pr-1.5"
              >
                {{ formatDateLabel(date.toString()) }}
                <button class="ml-1 rounded-full p-0.5 hover:bg-muted" @click="removeSpecificDate(index)">
                  <X class="h-3 w-3" />
                </button>
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Schedule -->
      <Card>
        <CardHeader>
          <div class="flex items-center gap-3">
            <Clock class="h-5 w-5 text-primary" />
            <div>
              <CardTitle>{{ t('duties.events.createView.sections.schedule') }}</CardTitle>
              <CardDescription>{{ t('duties.events.createView.sections.scheduleDesc') }}</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent class="space-y-6">
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>{{ t('duties.events.createView.schedule.defaultStartTime') }}</Label>
              <TimePicker v-model="defaultStartTime" />
            </div>
            <div class="space-y-2">
              <Label>{{ t('duties.events.createView.schedule.defaultEndTime') }}</Label>
              <TimePicker v-model="defaultEndTime" />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>{{ t('duties.events.createView.schedule.slotDuration') }}</Label>
              <Select v-model="slotDurationMinutes">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="d in durationOptions" :key="d" :value="d">
                    {{ t('duties.events.createView.schedule.minutes', { n: d }) }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="space-y-2">
              <Label>{{ t('duties.events.createView.schedule.peoplePerSlot') }}</Label>
              <Input v-model.number="peoplePerSlot" type="number" min="1" />
            </div>
          </div>

          <!-- Remainder handling -->
          <Transition
            enter-active-class="grid transition-[grid-template-rows,opacity] duration-300 ease-out"
            enter-from-class="grid-rows-[0fr] opacity-0"
            enter-to-class="grid-rows-[1fr] opacity-100"
            leave-active-class="grid transition-[grid-template-rows,opacity] duration-200 ease-in"
            leave-from-class="grid-rows-[1fr] opacity-100"
            leave-to-class="grid-rows-[0fr] opacity-0"
          >
            <div v-if="hasRemainder">
              <div class="overflow-hidden">
                <div class="space-y-2">
                  <Label>{{ t('duties.events.createView.schedule.remainder') }}</Label>
                  <p class="text-sm text-muted-foreground">
                    {{ t('duties.events.createView.schedule.remainderDesc') }}
                  </p>
                  <RadioGroup v-model="remainderMode" class="flex gap-4 pt-1">
                    <div class="flex items-center gap-2">
                      <RadioGroupItem value="drop" id="rm-drop" />
                      <Label for="rm-drop">{{ t('duties.events.createView.schedule.remainderMode.drop') }}</Label>
                    </div>
                    <div class="flex items-center gap-2">
                      <RadioGroupItem value="short" id="rm-short" />
                      <Label for="rm-short">{{ t('duties.events.createView.schedule.remainderMode.short') }}</Label>
                    </div>
                    <div class="flex items-center gap-2">
                      <RadioGroupItem value="extend" id="rm-extend" />
                      <Label for="rm-extend">{{ t('duties.events.createView.schedule.remainderMode.extend') }}</Label>
                    </div>
                  </RadioGroup>
                </div>
              </div>
            </div>
          </Transition>

          <!-- Date exceptions -->
          <template v-if="dateMode !== 'single'">
            <Separator />
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <p class="font-medium">{{ t('duties.events.createView.schedule.overrides') }}</p>
                  <p class="text-sm text-muted-foreground">
                    {{ t('duties.events.createView.schedule.overridesDesc') }}
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  :disabled="availableDates.length === 0"
                  @click="addOverride"
                >
                  <Plus class="mr-1.5 h-4 w-4" />
                  {{ t('duties.events.createView.schedule.addException') }}
                </Button>
              </div>

              <div
                v-for="(override, index) in overrides"
                :key="index"
                class="flex items-end gap-3 rounded-md border p-3"
              >
                <div class="flex-1 space-y-2">
                  <Label>{{ t('duties.dutySlots.fields.date') }}</Label>
                  <Select v-model="override.date">
                    <SelectTrigger class="min-w-40">
                      <SelectValue :placeholder="t('duties.dutySlots.pickDate')" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem v-for="d in availableDates" :key="d" :value="d">
                        {{ formatDateLabel(d) }}
                      </SelectItem>
                      <SelectItem
                        v-if="override.date && !availableDates.includes(override.date)"
                        :value="override.date"
                      >
                        {{ formatDateLabel(override.date) }}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div class="space-y-2">
                  <Label>{{ t('duties.dutySlots.fields.startTime') }}</Label>
                  <TimePicker v-model="override.startTime" />
                </div>
                <div class="space-y-2">
                  <Label>{{ t('duties.dutySlots.fields.endTime') }}</Label>
                  <TimePicker v-model="override.endTime" />
                </div>
                <Button variant="ghost" size="icon" @click="removeOverride(index)">
                  <Trash2 class="h-4 w-4 text-destructive" />
                </Button>
              </div>
            </div>
          </template>
        </CardContent>
      </Card>

      <!-- Preview -->
      <Card>
        <CardHeader>
          <div class="flex items-center justify-between">
            <div>
              <CardTitle>{{ t('duties.events.createView.sections.preview') }}</CardTitle>
              <CardDescription>{{ t('duties.events.createView.sections.previewDesc') }}</CardDescription>
            </div>
            <Badge v-if="totalSlots > 0" variant="secondary">
              {{ t('duties.events.createView.preview.summary', { slots: totalSlots, days: totalDays }) }}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div v-if="totalSlots === 0" class="py-8 text-center text-muted-foreground">
            {{ t('duties.events.createView.preview.noSlots') }}
          </div>
          <div v-else class="space-y-4">
            <div v-for="[dateStr, slots] in slotsByDate" :key="dateStr" class="space-y-2">
              <div class="flex items-center gap-2">
                <p class="font-medium">{{ formatDateLabel(dateStr) }}</p>
                <Badge variant="outline">
                  {{ t('duties.events.createView.preview.slotsOnDate', { count: slots.filter(s => !isSlotExcluded(s)).length }) }}
                </Badge>
              </div>
              <div class="grid grid-cols-2 items-center gap-2 sm:grid-cols-3 md:grid-cols-4">
                <Card
                  v-for="slot in slots"
                  :key="slot.startTime"
                  class="cursor-pointer p-2 transition-opacity"
                  :class="isSlotExcluded(slot) ? 'opacity-30' : 'hover:ring-1 hover:ring-destructive/40'"
                  @click="toggleSlotExclusion(slot)"
                >
                  <CardContent class="p-0">
                    <p
                      class="text-center text-sm font-mono"
                      :class="isSlotExcluded(slot) ? 'line-through text-muted-foreground' : ''"
                    >
                      {{ slot.startTime }} - {{ slot.endTime }}
                    </p>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Actions -->
      <div class="flex justify-end gap-3">
        <Button variant="outline" @click="router.push({ name: 'event-detail', params: { eventId: eventId } })">
          {{ t('common.actions.cancel') }}
        </Button>
        <Button :disabled="!isValid || submitting" @click="handleSubmit">
          <CalendarPlus class="mr-2 h-4 w-4" />
          {{ submitting ? t('common.states.saving') : t('duties.events.addSlotsView.submit') }}
        </Button>
      </div>
    </template>
  </div>
</template>
