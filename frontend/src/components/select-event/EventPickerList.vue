<script setup lang="ts">
import { ArrowRight, Compass, Plus, Users } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent } from '@/components/ui/card'

import type { SelectEventMode } from '@/components/select-event/SelectEventHeroPane.vue'
import SelectableEventCard, {
  type EventStats,
} from '@/components/select-event/SelectableEventCard.vue'

import type { EventRead } from '@/client/types.gen'

export type PickerTab = 'mine' | 'discover'

const props = defineProps<{
  events: EventRead[]
  discoverEvents: EventRead[]
  stats: Record<string, EventStats>
  loading: boolean
  discoverLoading: boolean
  pendingSelectionId: string | null
  currentSelectedId: string | null
  submitting: boolean
  mode: SelectEventMode
  tab: PickerTab
  requestingId: string | null
}>()

const emit = defineEmits<{
  stage: [event: EventRead]
  commit: []
  cancel: []
  back: []
  openCreate: []
  requestJoin: [event: EventRead]
  'update:tab': [tab: PickerTab]
}>()

const { t } = useI18n()
</script>

<template>
  <div class="space-y-4">
    <!-- Anyone can run an event now, so both halves are always offered. -->
    <div class="flex gap-1 rounded-lg bg-muted p-1" role="tablist">
      <button
        type="button"
        role="tab"
        data-testid="tab-my-events"
        :aria-selected="props.tab === 'mine'"
        :class="[
          'flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
          props.tab === 'mine'
            ? 'bg-background shadow-sm'
            : 'text-muted-foreground hover:text-foreground',
        ]"
        @click="emit('update:tab', 'mine')"
      >
        <Users class="h-4 w-4" />
        {{ t('duties.selectEvent.tabs.mine') }}
      </button>
      <button
        type="button"
        role="tab"
        data-testid="tab-discover"
        :aria-selected="props.tab === 'discover'"
        :class="[
          'flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
          props.tab === 'discover'
            ? 'bg-background shadow-sm'
            : 'text-muted-foreground hover:text-foreground',
        ]"
        @click="emit('update:tab', 'discover')"
      >
        <Compass class="h-4 w-4" />
        {{ t('duties.selectEvent.tabs.discover') }}
      </button>
    </div>

    <!-- ── My events ────────────────────────────────────────────── -->
    <template v-if="props.tab === 'mine'">
      <div v-if="props.loading" class="py-12 text-center text-muted-foreground">
        {{ t('common.states.loading') }}
      </div>

      <div v-else class="space-y-3">
        <div
          v-if="props.events.length === 0"
          class="rounded-lg border border-dashed p-8 text-center"
          data-testid="my-events-empty"
        >
          <p class="font-medium">{{ t('duties.selectEvent.emptyMine.title') }}</p>
          <p class="mt-1 text-sm text-muted-foreground">
            {{ t('duties.selectEvent.emptyMine.body') }}
          </p>
          <div class="mt-4 flex flex-col justify-center gap-2 sm:flex-row">
            <Button data-testid="btn-empty-create" @click="emit('openCreate')">
              <Plus class="mr-2 h-4 w-4" />
              {{ t('duties.selectEvent.pick.createNew') }}
            </Button>
            <Button variant="outline" @click="emit('update:tab', 'discover')">
              <Compass class="mr-2 h-4 w-4" />
              {{ t('duties.selectEvent.tabs.discover') }}
            </Button>
          </div>
        </div>

        <template v-else>
          <SelectableEventCard
            v-for="event in props.events"
            :key="event.id"
            :event="event"
            :stats="props.stats[event.id]"
            :is-current="props.currentSelectedId === event.id"
            :is-pending="props.pendingSelectionId === event.id"
            @select="(e) => emit('stage', e)"
          />

          <Card
            data-testid="select-event-create-card"
            class="cursor-pointer border-dashed transition-colors hover:border-primary"
            @click="emit('openCreate')"
          >
            <CardContent class="flex items-center justify-center gap-2 p-5 text-muted-foreground">
              <Plus class="h-5 w-5" />
              <span class="text-sm font-medium">
                {{ t('duties.selectEvent.pick.createNew') }}
              </span>
            </CardContent>
          </Card>
        </template>

        <div
          v-if="props.events.length > 0"
          class="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:items-center sm:justify-end"
        >
          <Button
            v-if="props.mode === 'onboarding'"
            variant="ghost"
            class="w-full sm:mr-auto sm:w-auto lg:hidden"
            data-testid="btn-back-select-event"
            @click="emit('back')"
          >
            {{ t('duties.selectEvent.pick.back') }}
          </Button>
          <Button
            v-if="props.mode === 'switch'"
            variant="ghost"
            class="w-full sm:w-auto"
            data-testid="btn-cancel-select-event"
            :disabled="props.submitting"
            @click="emit('cancel')"
          >
            {{ t('duties.selectEvent.pick.cancel') }}
          </Button>
          <Button
            class="w-full sm:w-auto"
            data-testid="btn-continue-select-event"
            :disabled="!props.pendingSelectionId || props.submitting"
            @click="emit('commit')"
          >
            {{ t('duties.selectEvent.pick.continue') }}
            <ArrowRight class="ml-2 h-4 w-4" />
          </Button>
        </div>
      </div>
    </template>

    <!-- ── Discover ─────────────────────────────────────────────── -->
    <template v-else>
      <div v-if="props.discoverLoading" class="py-12 text-center text-muted-foreground">
        {{ t('common.states.loading') }}
      </div>

      <div v-else class="space-y-3">
        <p class="text-sm text-muted-foreground">
          {{ t('duties.selectEvent.discover.hint') }}
        </p>

        <div
          v-if="props.discoverEvents.length === 0"
          class="rounded-lg border border-dashed p-8 text-center"
          data-testid="discover-empty"
        >
          <p class="font-medium">{{ t('duties.selectEvent.discover.emptyTitle') }}</p>
          <p class="mt-1 text-sm text-muted-foreground">
            {{ t('duties.selectEvent.discover.emptyBody') }}
          </p>
          <Button class="mt-4" data-testid="btn-discover-create" @click="emit('openCreate')">
            <Plus class="mr-2 h-4 w-4" />
            {{ t('duties.selectEvent.pick.createNew') }}
          </Button>
        </div>

        <SelectableEventCard
          v-for="event in props.discoverEvents"
          :key="event.id"
          variant="discover"
          :event="event"
          :stats="undefined"
          :is-current="false"
          :is-pending="false"
          :requesting="props.requestingId === event.id"
          @request-join="(e) => emit('requestJoin', e)"
        />
      </div>
    </template>
  </div>
</template>
