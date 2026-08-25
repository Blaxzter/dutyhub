<script setup lang="ts">
/**
 * The one thing somebody opens this page to find out: where they are due next.
 *
 * It is deliberately the largest thing on the dashboard, and the start time is
 * the largest thing in it, because that is the fact you are checking. When
 * there is nothing to show it turns into the offer instead — a page that says
 * "nothing booked" and stops there has wasted the best slot on the screen.
 */
import { computed } from 'vue'

import { ArrowRight, CalendarCheck, MapPin, Search, Users } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { useFormatters } from '@/composables/useFormatters'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

import type { DashboardShift } from '@/client'

const props = defineProps<{
  shift: DashboardShift | null
  /** Places going begging in the event in view, for the empty state's offer. */
  openPlaces: number
}>()

const emit = defineEmits<{ open: [shift: DashboardShift]; browse: [] }>()

const { t } = useI18n()
const { formatTimeRange, formatRelativeDay, formatDateLabel } = useFormatters()

const relativeDay = computed(() => (props.shift ? formatRelativeDay(props.shift.date) : ''))
const fullDate = computed(() =>
  props.shift
    ? formatDateLabel(props.shift.date, { weekday: 'long', day: 'numeric', month: 'long' })
    : '',
)
const times = computed(() =>
  props.shift ? formatTimeRange(props.shift.start_time, props.shift.end_time) : '',
)
/** Everybody on the shift except you — "who else will be there". */
const others = computed(() => Math.max((props.shift?.taken ?? 1) - 1, 0))

/**
 * Generated shifts are titled "{job} HH:MM-HH:MM", so the job would otherwise
 * appear twice within three lines. Only worth saying when the title is
 * somebody's own wording and does not already carry it.
 */
const showTaskName = computed(
  () => !!props.shift && !props.shift.title.includes(props.shift.task_name),
)
</script>

<template>
  <Card data-testid="dashboard-next-shift" class="overflow-hidden">
    <CardContent v-if="shift" class="flex flex-col gap-4 sm:flex-row sm:items-center">
      <div class="min-w-0 flex-1 space-y-1">
        <p class="flex flex-wrap items-center gap-2 text-xs font-medium uppercase tracking-wide">
          <span class="text-muted-foreground">{{ t('dashboard.home.next.eyebrow') }}</span>
          <!--
            No text-transform of its own: the label arrives from
            `Intl.RelativeTimeFormat` as a sentence ("in 6 days"), and it reads
            as one small caps label with the eyebrow beside it. `capitalize`
            here would give "In 6 Days", which is neither.
          -->
          <span class="rounded-full bg-primary/10 px-2 py-0.5 text-primary">
            {{ relativeDay }}
          </span>
        </p>

        <p class="text-3xl font-semibold tracking-tight sm:text-4xl">
          {{ times || fullDate }}
        </p>
        <p v-if="times" class="text-sm text-muted-foreground">{{ fullDate }}</p>
        <p class="truncate pt-1 text-lg font-medium">{{ shift.title }}</p>

        <p class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
          <span v-if="showTaskName" class="truncate">{{ shift.task_name }}</span>
          <span v-if="shift.location" class="inline-flex min-w-0 items-center gap-1">
            <MapPin class="h-3.5 w-3.5 shrink-0" />
            <span class="truncate">{{ shift.location }}</span>
          </span>
          <span class="inline-flex items-center gap-1">
            <Users class="h-3.5 w-3.5 shrink-0" />
            {{ t('dashboard.home.next.withOthers', { count: others }, others) }}
          </span>
        </p>
      </div>

      <div class="shrink-0">
        <Button data-testid="btn-open-next-shift" @click="emit('open', shift)">
          {{ t('dashboard.home.next.open') }}
          <ArrowRight class="ml-2 h-4 w-4" />
        </Button>
      </div>
    </CardContent>

    <CardContent v-else class="flex flex-col gap-4 sm:flex-row sm:items-center">
      <div class="flex size-12 shrink-0 items-center justify-center rounded-full bg-muted">
        <CalendarCheck class="h-6 w-6 text-muted-foreground" />
      </div>
      <div class="min-w-0 flex-1 space-y-1">
        <p class="text-lg font-semibold">{{ t('dashboard.home.next.empty.title') }}</p>
        <p class="text-sm text-muted-foreground">
          {{
            openPlaces > 0
              ? t('dashboard.home.next.empty.bodyOpen', { count: openPlaces }, openPlaces)
              : t('dashboard.home.next.empty.bodyNone')
          }}
        </p>
      </div>
      <div v-if="openPlaces > 0" class="shrink-0">
        <Button data-testid="btn-find-shift" @click="emit('browse')">
          <Search class="mr-2 h-4 w-4" />
          {{ t('dashboard.home.next.empty.action') }}
        </Button>
      </div>
    </CardContent>
  </Card>
</template>
