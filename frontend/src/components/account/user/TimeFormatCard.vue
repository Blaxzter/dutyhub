<script setup lang="ts">
import { computed } from 'vue'

import { Clock } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { useFormatters } from '@/composables/useFormatters'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'

const { t } = useI18n()
const authStore = useAuthStore()
const { patch } = useAuthenticatedClient()
const { formatTime } = useFormatters()

type TimeFormat = 'locale' | 'h24' | 'h12'

const timeFormat = computed<TimeFormat>(
  () => (authStore.profile?.time_format as TimeFormat | undefined) ?? 'locale',
)

const sampleTime = '14:30'

const options: { value: TimeFormat; labelKey: string }[] = [
  { value: 'locale', labelKey: 'user.settings.timeFormat.locale' },
  { value: 'h24', labelKey: 'user.settings.timeFormat.h24' },
  { value: 'h12', labelKey: 'user.settings.timeFormat.h12' },
]

async function setTimeFormat(value: TimeFormat | undefined) {
  if (!value || !authStore.profile) return
  const previous = authStore.profile.time_format
  authStore.profile.time_format = value
  try {
    await patch({ url: '/users/me', body: { time_format: value } })
  } catch {
    authStore.profile.time_format = previous
    toast.error(t('user.settings.timeFormat.error'))
  }
}
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <Clock class="h-5 w-5" />
        {{ t('user.settings.timeFormat.title') }}
      </CardTitle>
      <CardDescription>
        {{ t('user.settings.timeFormat.description') }}
      </CardDescription>
    </CardHeader>
    <CardContent>
      <div class="flex items-start justify-between gap-4">
        <div class="space-y-1">
          <p class="text-sm font-medium">{{ t('user.settings.timeFormat.label') }}</p>
          <p class="text-sm text-muted-foreground">
            {{ t('user.settings.timeFormat.preview', { time: formatTime(sampleTime) }) }}
          </p>
        </div>
        <ToggleGroup
          type="single"
          variant="outline"
          :model-value="timeFormat"
          @update:model-value="(v) => setTimeFormat(v as TimeFormat | undefined)"
        >
          <ToggleGroupItem
            v-for="opt in options"
            :key="opt.value"
            :value="opt.value"
            :data-testid="`time-format-${opt.value}`"
          >
            {{ t(opt.labelKey) }}
          </ToggleGroupItem>
        </ToggleGroup>
      </div>
    </CardContent>
  </Card>
</template>
