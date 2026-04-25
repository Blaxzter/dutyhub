<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { ChevronRight } from '@respeak/lucide-motion-vue'
import { reactiveOmit } from '@vueuse/core'
import { DropdownMenuSubTrigger, type DropdownMenuSubTriggerProps, useForwardProps } from 'reka-ui'

import { cn } from '@/lib/utils'

const props = defineProps<
  DropdownMenuSubTriggerProps & { class?: HTMLAttributes['class']; inset?: boolean }
>()

const delegatedProps = reactiveOmit(props, 'class', 'inset')
const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <DropdownMenuSubTrigger
    data-slot="dropdown-menu-sub-trigger"
    v-bind="forwardedProps"
    :class="
      cn(
        'focus:bg-accent focus:text-accent-foreground data-[state=open]:bg-accent data-[state=open]:text-accent-foreground flex cursor-default items-center rounded-sm px-2 py-1.5 text-sm outline-hidden select-none data-[inset]:pl-8',
        props.class,
      )
    "
  >
    <slot />
    <ChevronRight class="ml-auto size-4" animateOnHover triggerTarget="parent" animation="default-loop" />
  </DropdownMenuSubTrigger>
</template>
