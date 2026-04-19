<script setup lang="ts">
import type { PopoverTriggerProps } from 'reka-ui'
import { PopoverTrigger } from 'reka-ui'

const props = defineProps<PopoverTriggerProps>()
</script>

<template>
  <PopoverTrigger data-shift="popover-trigger" v-bind="props">
    <slot />
  </PopoverTrigger>
</template>
