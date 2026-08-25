<script setup lang="ts">
/**
 * One shift, as a row you can read in a glance and press.
 *
 * The date lives in a tile on the left rather than inside the sentence: a
 * column of tiles is scannable top to bottom, which is the whole reason this
 * replaced a month grid. Everything else — time, job, place — is one muted
 * line underneath the title, and the trailing slot is where each list puts
 * its own answer to "how full is it".
 */
import { computed } from 'vue'

import { Clock, MapPin } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { useFormatters } from '@/composables/useFormatters'

const props = defineProps<{
  date: string
  startTime?: string | null
  endTime?: string | null
  title: string
  taskName: string
  location?: string | null
  /** Shown only when the shift belongs to some event other than the one in view. */
  eventName?: string | null
  /** Lifts the date tile for something happening today. */
  highlight?: boolean
}>()

const emit = defineEmits<{ select: [] }>()

const { locale } = useI18n()
const { formatTimeRange } = useFormatters()

const day = computed(() => new Date(props.date + 'T00:00:00'))

const weekday = computed(() =>
  day.value.toLocaleDateString(locale.value, { weekday: 'short' }).replace('.', ''),
)
const dayNumber = computed(() => day.value.getDate())
const month = computed(() => day.value.toLocaleDateString(locale.value, { month: 'short' }))

const times = computed(() => formatTimeRange(props.startTime, props.endTime))

/**
 * Generated shifts are titled "{job} HH:MM-HH:MM", so naming the job again
 * underneath would print it twice in two lines. Hand-written titles ("Welcome
 * desk, early") do not contain it, and there the job is worth saying.
 */
const showTaskName = computed(() => !props.title.includes(props.taskName))
</script>

<template>
  <button
    type="button"
    data-testid="shift-row"
    class="flex w-full items-center gap-3 rounded-lg border border-transparent p-2 text-left transition-colors hover:border-border hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    @click="emit('select')"
  >
    <div
      class="flex w-12 shrink-0 flex-col items-center rounded-md border py-1.5 leading-none"
      :class="highlight ? 'border-primary/40 bg-primary/10 text-primary' : 'bg-muted/50'"
    >
      <span class="text-[10px] font-medium uppercase tracking-wide opacity-70">{{ weekday }}</span>
      <span class="text-lg font-semibold">{{ dayNumber }}</span>
      <span class="text-[10px] uppercase tracking-wide opacity-70">{{ month }}</span>
    </div>

    <div class="min-w-0 flex-1">
      <p class="truncate font-medium">{{ title }}</p>
      <p class="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
        <span v-if="times" class="inline-flex items-center gap-1">
          <Clock class="h-3 w-3 shrink-0" />
          {{ times }}
        </span>
        <span v-if="showTaskName" class="truncate">{{ taskName }}</span>
        <span v-if="location" class="inline-flex min-w-0 items-center gap-1">
          <MapPin class="h-3 w-3 shrink-0" />
          <span class="truncate">{{ location }}</span>
        </span>
      </p>
      <p v-if="eventName" class="mt-0.5 truncate text-xs text-muted-foreground/80">
        {{ eventName }}
      </p>
    </div>

    <div class="shrink-0">
      <slot name="trailing" />
    </div>
  </button>
</template>
