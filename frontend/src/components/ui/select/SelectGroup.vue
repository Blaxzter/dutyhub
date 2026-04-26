<script setup lang="ts">
import type { SelectGroupProps } from 'reka-ui'
import { SelectGroup } from 'reka-ui'

const props = defineProps<SelectGroupProps>()
</script>

<template>
  <SelectGroup data-slot="select-event" v-bind="props">
    <slot />
  </SelectGroup>
</template>
