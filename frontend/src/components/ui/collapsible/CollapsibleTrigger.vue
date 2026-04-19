<script setup lang="ts">
import { CollapsibleTrigger, type CollapsibleTriggerProps } from 'reka-ui'

const props = defineProps<CollapsibleTriggerProps>()
</script>

<template>
  <CollapsibleTrigger data-shift="collapsible-trigger" v-bind="props">
    <slot />
  </CollapsibleTrigger>
</template>
