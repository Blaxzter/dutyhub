<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { DateValue } from '@internationalized/date'
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

export type CreateEventPayload = {
  name: string
  description: string | undefined
  start_date: string
  end_date: string
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
          <Label class="text-sm">{{ t('duties.events.fields.defaultTimes') }}</Label>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-1">
              <Label class="text-muted-foreground text-xs">{{ t('duties.events.fields.startTime') }}</Label>
              <TimePicker
                v-model="startTime"
                class="w-full"
                :class="defaultTimesError ? 'border-destructive' : ''"
                :placeholder="t('duties.events.fields.timeOptional')"
              />
            </div>
            <div class="space-y-1">
              <Label class="text-muted-foreground text-xs">{{ t('duties.events.fields.endTime') }}</Label>
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
