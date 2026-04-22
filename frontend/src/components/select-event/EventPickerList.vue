<script setup lang="ts">
import { ArrowRight, Plus } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent } from '@/components/ui/card'

import SelectableEventCard, {
  type EventStats,
} from '@/components/select-event/SelectableEventCard.vue'

import type { EventRead } from '@/client/types.gen'

const props = defineProps<{
  events: EventRead[]
  stats: Record<string, EventStats>
  loading: boolean
  pendingSelectionId: string | null
  currentSelectedId: string | null
  canCreateEvents: boolean
  submitting: boolean
}>()

defineEmits<{
  stage: [event: EventRead]
  commit: []
  openCreate: []
}>()

const { t } = useI18n()
</script>

<template>
  <div v-if="props.loading" class="py-12 text-center text-muted-foreground">
    {{ t('common.states.loading') }}
  </div>

  <template v-else>
    <div
      v-if="props.events.length === 0 && !props.canCreateEvents"
      class="rounded-lg border border-dashed p-10 text-center text-muted-foreground"
    >
      {{ t('duties.selectEvent.empty') }}
    </div>

    <div v-else class="space-y-3">
      <SelectableEventCard
        v-for="event in props.events"
        :key="event.id"
        :event="event"
        :stats="props.stats[event.id]"
        :is-current="props.currentSelectedId === event.id"
        :is-pending="props.pendingSelectionId === event.id"
        @select="(e) => $emit('stage', e)"
      />

      <Card
        v-if="props.canCreateEvents"
        data-testid="select-event-create-card"
        class="cursor-pointer border-dashed transition-colors hover:border-primary"
        @click="$emit('openCreate')"
      >
        <CardContent
          class="flex items-center justify-center gap-2 p-5 text-muted-foreground"
        >
          <Plus class="h-5 w-5" />
          <span class="text-sm font-medium">
            {{ t('duties.selectEvent.pick.createNew') }}
          </span>
        </CardContent>
      </Card>

      <div class="flex justify-end pt-2">
        <Button
          data-testid="btn-continue-select-event"
          :disabled="!props.pendingSelectionId || props.submitting"
          @click="$emit('commit')"
        >
          {{ t('duties.selectEvent.pick.continue') }}
          <ArrowRight class="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  </template>
</template>
