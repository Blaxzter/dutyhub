<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

import { useResponsiveDialog } from './utils'

const props = withDefaults(
  defineProps<{
    class?: HTMLAttributes['class']
    /**
     * `stack` — the default, and right for the two-button confirm footers that
     * most dialogs have. Full-width buttons on a phone, with the primary on top
     * the way an action sheet puts it; a right-aligned row on a desktop dialog.
     *
     * `row` — for a footer that is not just buttons (an icon menu beside a
     * call to action, say), which has to stay one line at every width.
     */
    layout?: 'stack' | 'row'
  }>(),
  { layout: 'stack' },
)

const { isMobile } = useResponsiveDialog()
</script>

<template>
  <div
    data-slot="responsive-dialog-footer"
    :class="
      cn(
        'flex shrink-0 gap-2',
        layout === 'row'
          ? 'flex-row items-center'
          : isMobile
            ? 'flex-col-reverse items-stretch'
            : 'flex-row items-center justify-end',
        isMobile
          ? // A rule to separate it from the scrolling body, and enough bottom
            // padding to clear the home indicator on a gesture-nav phone.
            'border-t px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]'
          : 'px-6 pt-4 pb-6',
        props.class,
      )
    "
  >
    <slot />
  </div>
</template>
