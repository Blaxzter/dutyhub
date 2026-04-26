<script setup lang="ts">
import { CalendarDays, Check } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import Badge from '@/components/ui/badge/Badge.vue'
import { Card, CardContent } from '@/components/ui/card'

import type { EventRead } from '@/client/types.gen'
import { formatDate } from '@/lib/format'

export type EventStats = { taskCount: number; totalShifts: number; openShifts: number }

const props = defineProps<{
  event: EventRead
  stats: EventStats | undefined
  isCurrent: boolean
  isPending: boolean
}>()

defineEmits<{ select: [event: EventRead] }>()

const { t } = useI18n()
</script>

<template>
  <Card
    data-testid="select-event-card"
    :data-selected="props.isPending ? 'true' : undefined"
    role="radio"
    :aria-checked="props.isPending"
    tabindex="0"
    class="cursor-pointer transition-colors hover:border-primary"
    :class="{ 'border-primary ring-2 ring-primary/30': props.isPending }"
    @click="$emit('select', props.event)"
    @keydown.enter.prevent="$emit('select', props.event)"
    @keydown.space.prevent="$emit('select', props.event)"
  >
    <CardContent class="flex items-center gap-4 p-5">
      <div class="min-w-0 flex-1 space-y-1.5">
        <div class="flex items-center gap-2">
          <h3 class="truncate text-lg font-semibold">{{ props.event.name }}</h3>
          <Badge v-if="props.isCurrent" variant="secondary">
            {{ t('duties.selectEvent.pick.current') }}
          </Badge>
        </div>
        <div class="flex items-center gap-2 text-sm text-muted-foreground">
          <CalendarDays class="h-4 w-4 shrink-0" />
          <span>
            {{ formatDate(props.event.start_date) }} – {{ formatDate(props.event.end_date) }}
          </span>
        </div>
        <p class="text-sm font-medium">
          {{
            t(
              'duties.selectEvent.pick.stats',
              {
                tasks: props.stats?.taskCount ?? 0,
                shifts: props.stats?.openShifts ?? 0,
              },
              props.stats?.taskCount ?? 0,
            )
          }}
        </p>
      </div>

      <!-- Radio-style indicator -->
      <div
        :class="[
          'flex size-11 shrink-0 items-center justify-center rounded-full transition-colors',
          props.isPending
            ? 'bg-primary text-primary-foreground'
            : 'border-2 border-muted-foreground/30',
        ]"
        aria-hidden="true"
      >
        <Check v-if="props.isPending" class="h-5 w-5" :stroke-width="2.5" />
      </div>
    </CardContent>
  </Card>
</template>
