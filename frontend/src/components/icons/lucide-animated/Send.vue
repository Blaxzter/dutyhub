<script setup lang="ts">
import { ref } from 'vue'

import { motion } from 'motion-v'

interface Props {
  size?: number
  class?: string | string[]
}

const props = withDefaults(defineProps<Props>(), {
  size: 24,
  class: '',
})

const currentState = ref('normal')

const startAnimation = () => {
  currentState.value = 'animate'
}

const stopAnimation = () => {
  currentState.value = 'normal'
}

defineExpose({ startAnimation, stopAnimation })
</script>

<template>
  <motion.svg
    xmlns="http://www.w3.org/2000/svg"
    :width="props.size"
    :height="props.size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="props.class"
    :variants="{
      normal: { x: 0, y: 0 },
      animate: { x: [0, 3, 0], y: [0, -3, 0] },
    }"
    :animate="currentState"
    :transition="{ duration: 0.4, ease: 'easeInOut' }"
    @mouseenter="startAnimation"
    @mouseleave="stopAnimation"
  >
    <path
      d="M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z"
    />
    <path d="m21.854 2.147-10.94 10.939" />
  </motion.svg>
</template>
