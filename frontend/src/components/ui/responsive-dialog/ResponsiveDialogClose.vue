<script setup lang="ts">
import { DialogClose } from '@/components/ui/dialog'
import { DrawerClose } from '@/components/ui/drawer'

import { useResponsiveDialog } from './utils'

defineProps<{ asChild?: boolean }>()

const { isMobile } = useResponsiveDialog()
</script>

<template>
  <DrawerClose v-if="isMobile" :as-child="asChild">
    <slot />
  </DrawerClose>
  <DialogClose v-else :as-child="asChild">
    <slot />
  </DialogClose>
</template>
