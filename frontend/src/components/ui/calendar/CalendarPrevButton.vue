<script lang="ts" setup>
import type { HTMLAttributes } from 'vue'

import { ChevronLeft } from '@respeak/lucide-motion-vue'
import { reactiveOmit } from '@vueuse/core'
import type { CalendarPrevProps } from 'reka-ui'
import { CalendarPrev, useForwardProps } from 'reka-ui'

import { buttonVariants } from '@/components/ui/button'

import { cn } from '@/lib/utils'

const props = defineProps<CalendarPrevProps & { class?: HTMLAttributes['class'] }>()

const delegatedProps = reactiveOmit(props, 'class')

const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <CalendarPrev
    data-slot="calendar-prev-button"
    :class="
      cn(
        buttonVariants({ variant: 'outline' }),
        'size-7 bg-transparent p-0 opacity-50 hover:opacity-100',
        props.class,
      )
    "
    v-bind="forwardedProps"
  >
    <slot>
      <ChevronLeft class="size-4" animateOnHover triggerTarget="parent" animation="default-loop" />
    </slot>
  </CalendarPrev>
</template>
