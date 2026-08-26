<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { DialogDescription } from '@/components/ui/dialog'
import { DrawerDescription } from '@/components/ui/drawer'

import { cn } from '@/lib/utils'

import { useResponsiveDialog } from './utils'

const props = defineProps<{ class?: HTMLAttributes['class'] }>()

const { isMobile } = useResponsiveDialog()
</script>

<template>
  <DrawerDescription v-if="isMobile" :class="cn('text-muted-foreground text-sm', props.class)">
    <slot />
  </DrawerDescription>
  <DialogDescription v-else :class="cn('text-muted-foreground text-sm', props.class)">
    <slot />
  </DialogDescription>
</template>
