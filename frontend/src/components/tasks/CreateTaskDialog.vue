<script setup lang="ts">
import { ref, watch } from 'vue'

import type { DateValue } from '@internationalized/date'
import { useI18n } from 'vue-i18n'
import { z } from 'zod'

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

import { zTaskCreate } from '@/client/zod.gen'

const open = defineModel<boolean>('open', { required: true })

const emit = defineEmits<{
  create: [payload: { name: string; description?: string; startDate: string; endDate: string }]
}>()

const { t } = useI18n()

// Extend the generated schema: require non-empty name and enforce date ordering
const formSchema = zTaskCreate
  .extend({ name: z.string().min(1) })
  .refine((d) => !d.start_date || !d.end_date || d.end_date >= d.start_date, {
    message: 'endDateBeforeStart',
    path: ['end_date'],
  })

const form = ref({ name: '', description: '' })
const startDate = ref<DateValue>()
const endDate = ref<DateValue>()
const errors = ref<Record<string, string>>({})

watch(startDate, (val) => {
  if (val && endDate.value && endDate.value.compare(val) < 0) {
    endDate.value = undefined
  }
})

watch(open, (val) => {
  if (!val) {
    form.value = { name: '', description: '' }
    startDate.value = undefined
    endDate.value = undefined
    errors.value = {}
  }
})

function mapIssue(issue: z.ZodError['issues'][number]): string {
  if (issue.message === 'endDateBeforeStart') return t('common.validation.endDateBeforeStart')
  if (issue.code === 'too_small') return t('common.validation.required')
  return t('common.validation.invalidDate')
}

const handleSubmit = () => {
  errors.value = {}

  const result = formSchema.safeParse({
    name: form.value.name,
    description: form.value.description || null,
    start_date: startDate.value?.toString() ?? '',
    end_date: endDate.value?.toString() ?? '',
  })

  if (!result.success) {
    for (const issue of result.error.issues) {
      const field = String(issue.path[0] ?? 'form')
      if (!errors.value[field]) {
        errors.value[field] = mapIssue(issue)
      }
    }
    return
  }

  emit('create', {
    name: result.data.name,
    description: result.data.description ?? undefined,
    startDate: result.data.start_date,
    endDate: result.data.end_date,
  })
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{{ t('duties.tasks.create') }}</DialogTitle>
        <DialogDescription>{{ t('duties.tasks.subtitle') }}</DialogDescription>
      </DialogHeader>
      <form class="space-y-4" @submit.prevent="handleSubmit">
        <div class="space-y-2">
          <Label>{{ t('duties.tasks.fields.name') }}</Label>
          <Input v-model="form.name" @input="delete errors.name" />
          <p v-if="errors.name" class="text-destructive text-sm">{{ errors.name }}</p>
        </div>
        <div class="space-y-2">
          <Label>{{ t('duties.tasks.fields.description') }}</Label>
          <Input v-model="form.description" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label>{{ t('duties.tasks.fields.startDate') }}</Label>
            <DatePicker
              v-model="startDate"
              :max-value="endDate"
              @update:model-value="delete errors.start_date"
            />
            <p v-if="errors.start_date" class="text-destructive text-sm">{{ errors.start_date }}</p>
          </div>
          <div class="space-y-2">
            <Label>{{ t('duties.tasks.fields.endDate') }}</Label>
            <DatePicker
              v-model="endDate"
              :min-value="startDate"
              :highlight="startDate"
              @update:model-value="delete errors.end_date"
            />
            <p v-if="errors.end_date" class="text-destructive text-sm">{{ errors.end_date }}</p>
          </div>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" @click="open = false">
            {{ t('common.actions.cancel') }}
          </Button>
          <Button type="submit">{{ t('common.actions.create') }}</Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
