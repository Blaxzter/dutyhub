<script lang="ts" setup>
import type { HTMLAttributes } from 'vue'

import { reactiveOmit } from '@vueuse/core'
import type { CalendarGridProps } from 'reka-ui'
import { CalendarGrid, useForwardProps } from 'reka-ui'

import { cn } from '@/lib/utils'

const props = defineProps<CalendarGridProps & { class?: HTMLAttributes['class'] }>()

const delegatedProps = reactiveOmit(props, 'class')

const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <CalendarGrid
    data-shift="calendar-grid"
    :class="cn('w-full border-collapse space-x-1', props.class)"
    v-bind="forwardedProps"
  >
    <slot />
  </CalendarGrid>
</template>
