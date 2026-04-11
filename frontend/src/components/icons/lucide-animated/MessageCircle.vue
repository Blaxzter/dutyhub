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
      normal: { scale: 1, rotate: 0 },
      animate: { scale: [1, 1.08, 1], rotate: [0, -5, 5, 0] },
    }"
    :animate="currentState"
    :transition="{ duration: 0.5, ease: 'easeInOut' }"
    @mouseenter="startAnimation"
    @mouseleave="stopAnimation"
  >
    <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
  </motion.svg>
</template>
