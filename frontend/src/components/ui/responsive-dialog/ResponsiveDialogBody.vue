<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { DrawerViewport } from 'reka-ui'

import { cn } from '@/lib/utils'

import { useResponsiveDialog } from './utils'

const props = defineProps<{ class?: HTMLAttributes['class'] }>()

const { isMobile } = useResponsiveDialog()
</script>

<template>
  <!--
    `DrawerViewport` rather than a plain scroll container: it is what tells the
    drawer that a downward drag starting mid-list is a scroll, and only a drag
    that begins with the list already at the top should dismiss the sheet.
    Without it the sheet closes every time somebody tries to scroll up.
  -->
  <DrawerViewport
    v-if="isMobile"
    data-slot="responsive-dialog-body"
    :class="cn('min-h-0 flex-1 overflow-y-auto overscroll-contain px-4', props.class)"
  >
    <slot />
  </DrawerViewport>
  <div
    v-else
    data-slot="responsive-dialog-body"
    :class="cn('min-h-0 flex-1 overflow-y-auto px-6', props.class)"
  >
    <slot />
  </div>
</template>
