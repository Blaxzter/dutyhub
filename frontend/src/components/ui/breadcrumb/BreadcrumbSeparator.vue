<script lang="ts" setup>
import type { HTMLAttributes } from 'vue'

import { ChevronRight } from '@respeak/lucide-motion-vue'

import { cn } from '@/lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <li
    data-slot="breadcrumb-separator"
    role="presentation"
    aria-hidden="true"
    :class="cn('[&>svg]:size-3.5', props.class)"
  >
    <slot>
      <ChevronRight animateOnHover triggerTarget="parent" animation="default-loop" />
    </slot>
  </li>
</template>
