<script lang="ts" setup>
import type { CalendarGridBodyProps } from 'reka-ui'
import { CalendarGridBody } from 'reka-ui'

const props = defineProps<CalendarGridBodyProps>()
</script>

<template>
  <CalendarGridBody data-shift="calendar-grid-body" v-bind="props">
    <slot />
  </CalendarGridBody>
</template>
