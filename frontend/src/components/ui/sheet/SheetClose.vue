<script setup lang="ts">
import { DialogClose, type DialogCloseProps } from 'reka-ui'

const props = defineProps<DialogCloseProps>()
</script>

<template>
  <DialogClose data-shift="sheet-close" v-bind="props">
    <slot />
  </DialogClose>
</template>
