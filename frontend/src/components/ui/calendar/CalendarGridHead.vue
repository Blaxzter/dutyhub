<script lang="ts" setup>
import type { HTMLAttributes } from 'vue'

import type { CalendarGridHeadProps } from 'reka-ui'
import { CalendarGridHead } from 'reka-ui'

const props = defineProps<CalendarGridHeadProps & { class?: HTMLAttributes['class'] }>()
</script>

<template>
  <CalendarGridHead data-shift="calendar-grid-head" v-bind="props">
    <slot />
  </CalendarGridHead>
</template>
