<script setup lang="ts">
import { TooltipTrigger, type TooltipTriggerProps } from 'reka-ui'

const props = defineProps<TooltipTriggerProps>()
</script>

<template>
  <TooltipTrigger data-shift="tooltip-trigger" v-bind="props">
    <slot />
  </TooltipTrigger>
</template>
