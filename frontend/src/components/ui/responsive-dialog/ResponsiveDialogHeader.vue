<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

import { useResponsiveDialog } from './utils'

const props = defineProps<{ class?: HTMLAttributes['class'] }>()

const { isMobile } = useResponsiveDialog()
</script>

<template>
  <div
    data-slot="responsive-dialog-header"
    :class="
      cn(
        // Left-aligned in both shells. shadcn's DialogHeader centres below `sm`,
        // which reads as a toast rather than a screen once the drawer fills the
        // width of the phone.
        'flex flex-col gap-1.5 text-left',
        // The right gutter keeps the title clear of the close button both
        // shells park at `top-4 right-4`.
        isMobile ? 'px-4 pt-1 pb-3 pr-12' : 'px-6 pt-6 pb-4 pr-12',
        props.class,
      )
    "
  >
    <slot />
  </div>
</template>
