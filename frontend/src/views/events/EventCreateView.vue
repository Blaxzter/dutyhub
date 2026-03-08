<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import type { DateValue } from '@internationalized/date'
import { ArrowLeft, CalendarPlus, Clock, Plus, Trash2, Users } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import type { EventGroupListResponse, EventGroupRead } from '@/client/types.gen'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent } from '@/components/ui/card'
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
import Textarea from '@/components/ui/textarea/Textarea.vue'
import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { type ScheduleConfig, useSlotPreview } from '@/composables/useSlotPreview'
import { toastApiError } from '@/lib/api-errors'

const { t } = useI18n()
const router = useRouter()
const { get, post } = useAuthenticatedClient()

// --- Form state ---
const name = ref('')
const description = ref('')
const location = ref('')
const category = ref('')
const startDate = ref<DateValue>()
const endDate = ref<DateValue>()

// Event group
const eventGroupMode = ref<'none' | 'existing' | 'new'>('none')
const selectedEventGroupId = ref<string>('')
const eventGroups = ref<EventGroupRead[]>([])
const newGroupName = ref('')
const newGroupDescription = ref('')
const newGroupStartDate = ref<DateValue>()
const newGroupEndDate = ref<DateValue>()

// Schedule
const defaultStartTime = ref('10:00')
const defaultEndTime = ref('18:00')
const slotDurationMinutes = ref(30)
const peoplePerSlot = ref(2)
const overrides = ref<Array<{ date: string; startTime: string; endTime: string }>>([])

// UI state
const submitting = ref(false)
const expandedSections = ref(['details', 'schedule'])

// Duration options
const durationOptions = [15, 30, 45, 60, 90, 120]

// --- Slot preview ---
const scheduleConfig = computed<ScheduleConfig>(() => ({
  eventName: name.value || 'Event',
  startDate: startDate.value?.toString() ?? '',
  endDate: endDate.value?.toString() ?? '',
  defaultStartTime: defaultStartTime.value,
  defaultEndTime: defaultEndTime.value,
  slotDurationMinutes: slotDurationMinutes.value,
  peoplePerSlot: peoplePerSlot.value,
  overrides: overrides.value,
}))

const { totalSlots, totalDays, slotsByDate } = useSlotPreview(scheduleConfig)

// --- Date sync ---
watch(startDate, (val) => {
  if (val && endDate.value && endDate.value.compare(val) < 0) {
    endDate.value = undefined
  }
})

// --- Load event groups ---
const loadEventGroups = async () => {
  try {
    const response = await get<{ data: EventGroupListResponse }>({
      url: '/event-groups/',
      query: { limit: 100 },
    })
    eventGroups.value = response.data.items
  } catch {
    // Non-critical, just won't have groups to select from
  }
}

onMounted(loadEventGroups)

// --- Add/remove date exception ---
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

// --- Available dates for exceptions ---
const availableDates = computed(() => {
  if (!startDate.value || !endDate.value) return []
  const dates: string[] = []
  const start = new Date(startDate.value.toString())
  const end = new Date(endDate.value.toString())
  const current = new Date(start)
  while (current <= end) {
    const dateStr = current.toISOString().split('T')[0]
    // Exclude already overridden dates
    if (!overrides.value.some((o) => o.date === dateStr)) {
      dates.push(dateStr)
    }
    current.setDate(current.getDate() + 1)
  }
  return dates
})

// --- Form validation ---
const isValid = computed(() => {
  if (!name.value.trim()) return false
  if (!startDate.value || !endDate.value) return false
  if (!defaultStartTime.value || !defaultEndTime.value) return false
  if (slotDurationMinutes.value < 1) return false
  if (totalSlots.value === 0) return false

  if (eventGroupMode.value === 'existing' && !selectedEventGroupId.value) return false
  if (eventGroupMode.value === 'new') {
    if (!newGroupName.value.trim()) return false
    if (!newGroupStartDate.value || !newGroupEndDate.value) return false
  }

  return true
})

// --- Submit ---
const handleSubmit = async () => {
  if (!isValid.value || submitting.value) return
  submitting.value = true

  try {
    const body: Record<string, unknown> = {
      name: name.value,
      description: description.value || null,
      start_date: startDate.value!.toString(),
      end_date: endDate.value!.toString(),
      location: location.value || null,
      category: category.value || null,
      schedule: {
        default_start_time: defaultStartTime.value + ':00',
        default_end_time: defaultEndTime.value + ':00',
        slot_duration_minutes: slotDurationMinutes.value,
        people_per_slot: peoplePerSlot.value,
        overrides: overrides.value
          .filter((o) => o.date)
          .map((o) => ({
            date: o.date,
            start_time: o.startTime + ':00',
            end_time: o.endTime + ':00',
          })),
      },
    }

    if (eventGroupMode.value === 'existing' && selectedEventGroupId.value) {
      body.event_group_id = selectedEventGroupId.value
    } else if (eventGroupMode.value === 'new') {
      body.new_event_group = {
        name: newGroupName.value,
        description: newGroupDescription.value || null,
        start_date: newGroupStartDate.value!.toString(),
        end_date: newGroupEndDate.value!.toString(),
      }
    }

    const response = await post<{ data: { event: { id: string }; duty_slots_created: number } }>({
      url: '/events/with-slots',
      body,
    })

    toast.success(
      t('duties.events.createView.success', { count: response.data.duty_slots_created }),
    )
    router.push({ name: 'event-detail', params: { eventId: response.data.event.id } })
  } catch (error) {
    toastApiError(error)
  } finally {
    submitting.value = false
  }
}

const formatDateLabel = (dateStr: string) => {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
}
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-6 pb-24">
    <!-- Header -->
    <div class="space-y-2">
      <Button variant="ghost" size="sm" class="-ml-2" @click="router.push({ name: 'events' })">
        <ArrowLeft class="mr-1.5 h-4 w-4" />
        {{ t('common.actions.back') }}
      </Button>
      <h1 class="text-3xl font-bold">{{ t('duties.events.createView.title') }}</h1>
      <p class="text-muted-foreground">{{ t('duties.events.createView.subtitle') }}</p>
    </div>

    <Accordion v-model="expandedSections" type="multiple" class="space-y-4">
      <!-- Section 1: Event Details -->
      <AccordionItem value="details" class="rounded-lg border">
        <AccordionTrigger class="px-6 hover:no-underline">
          <div class="flex items-center gap-3">
            <CalendarPlus class="h-5 w-5 text-primary" />
            <div class="text-left">
              <p class="font-semibold">{{ t('duties.events.createView.sections.details') }}</p>
              <p class="text-sm text-muted-foreground">
                {{ t('duties.events.createView.sections.detailsDesc') }}
              </p>
            </div>
          </div>
        </AccordionTrigger>
        <AccordionContent class="px-6 pb-6">
          <div class="space-y-4">
            <div class="space-y-2">
              <Label>{{ t('duties.events.fields.name') }} *</Label>
              <Input v-model="name" />
            </div>
            <div class="space-y-2">
              <Label>{{ t('duties.events.fields.description') }}</Label>
              <Textarea v-model="description" :rows="3" />
            </div>
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
            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-2">
                <Label>{{ t('duties.events.fields.startDate') }} *</Label>
                <DatePicker v-model="startDate" :max-value="endDate" />
              </div>
              <div class="space-y-2">
                <Label>{{ t('duties.events.fields.endDate') }} *</Label>
                <DatePicker v-model="endDate" :min-value="startDate" :highlight="startDate" />
              </div>
            </div>
          </div>
        </AccordionContent>
      </AccordionItem>

      <!-- Section 2: Event Group -->
      <AccordionItem value="eventGroup" class="rounded-lg border">
        <AccordionTrigger class="px-6 hover:no-underline">
          <div class="flex items-center gap-3">
            <Users class="h-5 w-5 text-primary" />
            <div class="text-left">
              <p class="font-semibold">{{ t('duties.events.createView.sections.eventGroup') }}</p>
              <p class="text-sm text-muted-foreground">
                {{ t('duties.events.createView.sections.eventGroupDesc') }}
              </p>
            </div>
          </div>
        </AccordionTrigger>
        <AccordionContent class="px-6 pb-6">
          <RadioGroup v-model="eventGroupMode" class="space-y-3">
            <div class="flex items-center gap-2">
              <RadioGroupItem value="none" id="eg-none" />
              <Label for="eg-none">{{ t('duties.events.createView.eventGroupOption.none') }}</Label>
            </div>
            <div class="flex items-center gap-2">
              <RadioGroupItem value="existing" id="eg-existing" />
              <Label for="eg-existing">{{
                t('duties.events.createView.eventGroupOption.existing')
              }}</Label>
            </div>
            <div class="flex items-center gap-2">
              <RadioGroupItem value="new" id="eg-new" />
              <Label for="eg-new">{{ t('duties.events.createView.eventGroupOption.new') }}</Label>
            </div>
          </RadioGroup>

          <!-- Select existing group -->
          <div v-if="eventGroupMode === 'existing'" class="mt-4">
            <Select v-model="selectedEventGroupId">
              <SelectTrigger>
                <SelectValue :placeholder="t('duties.events.createView.eventGroupOption.existing')" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="group in eventGroups" :key="group.id" :value="group.id">
                  {{ group.name }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <!-- Create new group -->
          <div v-if="eventGroupMode === 'new'" class="mt-4 space-y-4 rounded-md border p-4">
            <div class="space-y-2">
              <Label>{{ t('duties.eventGroups.fields.name') }} *</Label>
              <Input v-model="newGroupName" />
            </div>
            <div class="space-y-2">
              <Label>{{ t('duties.eventGroups.fields.description') }}</Label>
              <Input v-model="newGroupDescription" />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-2">
                <Label>{{ t('duties.eventGroups.fields.startDate') }} *</Label>
                <DatePicker v-model="newGroupStartDate" :max-value="newGroupEndDate" />
              </div>
              <div class="space-y-2">
                <Label>{{ t('duties.eventGroups.fields.endDate') }} *</Label>
                <DatePicker
                  v-model="newGroupEndDate"
                  :min-value="newGroupStartDate"
                  :highlight="newGroupStartDate"
                />
              </div>
            </div>
          </div>
        </AccordionContent>
      </AccordionItem>

      <!-- Section 3: Schedule & Slots -->
      <AccordionItem value="schedule" class="rounded-lg border">
        <AccordionTrigger class="px-6 hover:no-underline">
          <div class="flex items-center gap-3">
            <Clock class="h-5 w-5 text-primary" />
            <div class="text-left">
              <p class="font-semibold">{{ t('duties.events.createView.sections.schedule') }}</p>
              <p class="text-sm text-muted-foreground">
                {{ t('duties.events.createView.sections.scheduleDesc') }}
              </p>
            </div>
          </div>
        </AccordionTrigger>
        <AccordionContent class="px-6 pb-6">
          <div class="space-y-6">
            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-2">
                <Label>{{ t('duties.events.createView.schedule.defaultStartTime') }}</Label>
                <Input v-model="defaultStartTime" type="time" />
              </div>
              <div class="space-y-2">
                <Label>{{ t('duties.events.createView.schedule.defaultEndTime') }}</Label>
                <Input v-model="defaultEndTime" type="time" />
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
                    <SelectItem
                      v-for="d in durationOptions"
                      :key="d"
                      :value="d"
                    >
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

            <!-- Date exceptions -->
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

              <div v-for="(override, index) in overrides" :key="index" class="flex items-end gap-3 rounded-md border p-3">
                <div class="flex-1 space-y-2">
                  <Label>{{ t('duties.dutySlots.fields.date') }}</Label>
                  <Select v-model="override.date">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem v-for="d in availableDates" :key="d" :value="d">
                        {{ formatDateLabel(d) }}
                      </SelectItem>
                      <!-- Keep selected date visible even if filtered -->
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
                  <Input v-model="override.startTime" type="time" class="w-32" />
                </div>
                <div class="space-y-2">
                  <Label>{{ t('duties.dutySlots.fields.endTime') }}</Label>
                  <Input v-model="override.endTime" type="time" class="w-32" />
                </div>
                <Button variant="ghost" size="icon" @click="removeOverride(index)">
                  <Trash2 class="h-4 w-4 text-destructive" />
                </Button>
              </div>
            </div>
          </div>
        </AccordionContent>
      </AccordionItem>

      <!-- Section 4: Preview -->
      <AccordionItem value="preview" class="rounded-lg border">
        <AccordionTrigger class="px-6 hover:no-underline">
          <div class="flex items-center gap-3">
            <CalendarPlus class="h-5 w-5 text-primary" />
            <div class="text-left">
              <p class="font-semibold">{{ t('duties.events.createView.sections.preview') }}</p>
              <p class="text-sm text-muted-foreground">
                {{ t('duties.events.createView.sections.previewDesc') }}
              </p>
            </div>
            <Badge v-if="totalSlots > 0" variant="secondary" class="ml-2">
              {{ t('duties.events.createView.preview.summary', { slots: totalSlots, days: totalDays }) }}
            </Badge>
          </div>
        </AccordionTrigger>
        <AccordionContent class="px-6 pb-6">
          <div v-if="totalSlots === 0" class="py-8 text-center text-muted-foreground">
            {{ t('duties.events.createView.preview.noSlots') }}
          </div>
          <div v-else class="space-y-4">
            <p class="text-sm font-medium text-muted-foreground">
              {{ t('duties.events.createView.preview.summary', { slots: totalSlots, days: totalDays }) }}
            </p>
            <div v-for="[dateStr, slots] in slotsByDate" :key="dateStr" class="space-y-2">
              <div class="flex items-center gap-2">
                <p class="font-medium">{{ formatDateLabel(dateStr) }}</p>
                <Badge variant="outline">
                  {{ t('duties.events.createView.preview.slotsOnDate', { count: slots.length }) }}
                </Badge>
              </div>
              <div class="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
                <Card v-for="slot in slots" :key="slot.startTime" class="p-2">
                  <CardContent class="p-0">
                    <p class="text-center text-sm font-mono">
                      {{ slot.startTime }} - {{ slot.endTime }}
                    </p>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>

    <!-- Sticky footer -->
    <div class="fixed inset-x-0 bottom-0 border-t bg-background p-4">
      <div class="mx-auto flex max-w-3xl items-center justify-between">
        <Button variant="outline" @click="router.push({ name: 'events' })">
          {{ t('common.actions.cancel') }}
        </Button>
        <Button :disabled="!isValid || submitting" @click="handleSubmit">
          <CalendarPlus class="mr-2 h-4 w-4" />
          {{ submitting ? t('common.states.saving') : t('duties.events.createView.submit') }}
        </Button>
      </div>
    </div>
  </div>
</template>
