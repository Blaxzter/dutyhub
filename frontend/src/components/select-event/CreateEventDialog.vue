<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { DateValue } from '@internationalized/date'
import { Globe, Lock } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import Button from '@/components/ui/button/Button.vue'
import { DatePicker } from '@/components/ui/date-picker'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import Input from '@/components/ui/input/Input.vue'
import Label from '@/components/ui/label/Label.vue'
import Textarea from '@/components/ui/textarea/Textarea.vue'
import { TimePicker } from '@/components/ui/time-picker'

import type { EventVisibility } from '@/lib/event-roles'

export type CreateEventPayload = {
  name: string
  description: string | undefined
  start_date: string
  end_date: string
  visibility: EventVisibility
  default_start_time?: string
  default_end_time?: string
}

const props = defineProps<{
  open: boolean
  submitting: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  submit: [payload: CreateEventPayload]
}>()

const { t } = useI18n()

const form = ref({ name: '', description: '' })
// Private by default: an event should not be discoverable until its owner
// decides it should be.
const visibility = ref<EventVisibility>('private')
const startDate = ref<DateValue>()
const endDate = ref<DateValue>()
const startTime = ref('')
const endTime = ref('')

const defaultTimesError = computed<string | null>(() => {
  if (!startTime.value || !endTime.value) return null
  if (endTime.value <= startTime.value) {
    return t('duties.events.fields.defaultTimesInvalid')
  }
  return null
})

// Reset form state whenever the dialog closes.
watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) {
      form.value = { name: '', description: '' }
      visibility.value = 'private'
      startDate.value = undefined
      endDate.value = undefined
      startTime.value = ''
      endTime.value = ''
    }
  },
)

function handleSubmit() {
  if (!startDate.value || !endDate.value || !form.value.name) return
  if (defaultTimesError.value) return
  emit('submit', {
    name: form.value.name,
    description: form.value.description || undefined,
    start_date: startDate.value.toString(),
    end_date: endDate.value.toString(),
    visibility: visibility.value,
    default_start_time: startTime.value ? `${startTime.value}:00` : undefined,
    default_end_time: endTime.value ? `${endTime.value}:00` : undefined,
  })
}
</script>

<template>
  <Dialog :open="props.open" @update:open="(v: boolean) => emit('update:open', v)">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{{ t('duties.events.create') }}</DialogTitle>
        <DialogDescription>{{ t('duties.events.subtitle') }}</DialogDescription>
      </DialogHeader>
      <form class="space-y-4" @submit.prevent="handleSubmit">
        <div class="space-y-2">
          <Label>{{ t('duties.events.fields.name') }}</Label>
          <Input v-model="form.name" required />
        </div>
        <div class="space-y-2">
          <Label>{{ t('duties.events.fields.description') }}</Label>
          <Textarea v-model="form.description" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label>{{ t('duties.events.fields.startDate') }}</Label>
            <DatePicker v-model="startDate" :placeholder="t('duties.events.pickDate')" />
          </div>
          <div class="space-y-2">
            <Label>{{ t('duties.events.fields.endDate') }}</Label>
            <DatePicker v-model="endDate" :placeholder="t('duties.events.pickDate')" />
          </div>
        </div>
        <div class="space-y-2">
          <Label class="text-sm">{{ t('duties.events.fields.visibility') }}</Label>
          <div class="grid gap-2 sm:grid-cols-2">
            <button
              v-for="option in ['private', 'public'] as const"
              :key="option"
              type="button"
              :data-testid="`btn-visibility-${option}`"
              :aria-pressed="visibility === option"
              :class="[
                'rounded-lg border p-3 text-left transition-colors',
                visibility === option
                  ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                  : 'hover:border-primary/50',
              ]"
              @click="visibility = option"
            >
              <span class="flex items-center gap-2 text-sm font-medium">
                <component :is="option === 'public' ? Globe : Lock" class="h-4 w-4" />
                {{ t(`duties.events.visibility.${option}.label`) }}
              </span>
              <span class="mt-1 block text-xs text-muted-foreground">
                {{ t(`duties.events.visibility.${option}.hint`) }}
              </span>
            </button>
          </div>
        </div>

        <div class="space-y-2">
          <Label class="text-sm">{{ t('duties.events.fields.defaultTimes') }}</Label>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-1">
              <Label class="text-muted-foreground text-xs">{{
                t('duties.events.fields.startTime')
              }}</Label>
              <TimePicker
                v-model="startTime"
                class="w-full"
                :class="defaultTimesError ? 'border-destructive' : ''"
                :placeholder="t('duties.events.fields.timeOptional')"
              />
            </div>
            <div class="space-y-1">
              <Label class="text-muted-foreground text-xs">{{
                t('duties.events.fields.endTime')
              }}</Label>
              <TimePicker
                v-model="endTime"
                class="w-full"
                :class="defaultTimesError ? 'border-destructive' : ''"
                :placeholder="t('duties.events.fields.timeOptional')"
              />
            </div>
          </div>
          <p v-if="defaultTimesError" class="text-destructive text-xs">
            {{ defaultTimesError }}
          </p>
          <p class="text-muted-foreground text-xs">
            {{ t('duties.events.fields.defaultTimesHint') }}
          </p>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" @click="emit('update:open', false)">
            {{ t('common.actions.cancel') }}
          </Button>
          <Button type="submit" :disabled="props.submitting">
            {{ t('common.actions.create') }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
