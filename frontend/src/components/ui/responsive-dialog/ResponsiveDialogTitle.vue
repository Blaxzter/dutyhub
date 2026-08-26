<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { DialogTitle } from '@/components/ui/dialog'
import { DrawerTitle } from '@/components/ui/drawer'

import { cn } from '@/lib/utils'

import { useResponsiveDialog } from './utils'

const props = defineProps<{ class?: HTMLAttributes['class'] }>()

const { isMobile } = useResponsiveDialog()
</script>

<template>
  <DrawerTitle v-if="isMobile" :class="cn('text-lg leading-tight font-semibold', props.class)">
    <slot />
  </DrawerTitle>
  <DialogTitle v-else :class="cn('text-lg leading-tight font-semibold', props.class)">
    <slot />
  </DialogTitle>
</template>
