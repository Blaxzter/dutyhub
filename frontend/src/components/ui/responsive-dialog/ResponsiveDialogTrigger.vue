<script setup lang="ts">
import { DialogTrigger } from '@/components/ui/dialog'
import { DrawerTrigger } from '@/components/ui/drawer'

import { useResponsiveDialog } from './utils'

defineProps<{ asChild?: boolean }>()

const { isMobile } = useResponsiveDialog()
</script>

<template>
  <DrawerTrigger v-if="isMobile" :as-child="asChild">
    <slot />
  </DrawerTrigger>
  <DialogTrigger v-else :as-child="asChild">
    <slot />
  </DialogTrigger>
</template>
