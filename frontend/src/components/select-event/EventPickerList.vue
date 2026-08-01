<script setup lang="ts">
import { ArrowRight, Plus } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent } from '@/components/ui/card'

import type { SelectEventMode } from '@/components/select-event/SelectEventHeroPane.vue'
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
  mode: SelectEventMode
}>()

defineEmits<{
  stage: [event: EventRead]
  commit: []
  cancel: []
  back: []
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
        <CardContent class="flex items-center justify-center gap-2 p-5 text-muted-foreground">
          <Plus class="h-5 w-5" />
          <span class="text-sm font-medium">
            {{ t('duties.selectEvent.pick.createNew') }}
          </span>
        </CardContent>
      </Card>

      <div class="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:items-center sm:justify-end">
        <Button
          v-if="props.mode === 'onboarding'"
          variant="ghost"
          class="w-full sm:mr-auto sm:w-auto lg:hidden"
          data-testid="btn-back-select-event"
          @click="$emit('back')"
        >
          {{ t('duties.selectEvent.pick.back') }}
        </Button>
        <Button
          v-if="props.mode === 'switch'"
          variant="ghost"
          class="w-full sm:w-auto"
          data-testid="btn-cancel-select-event"
          :disabled="props.submitting"
          @click="$emit('cancel')"
        >
          {{ t('duties.selectEvent.pick.cancel') }}
        </Button>
        <Button
          class="w-full sm:w-auto"
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
