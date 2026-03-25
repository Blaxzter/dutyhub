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
      normal: { rotate: 0 },
      animate: { rotate: [0, -10, 10, -10, 0] },
    }"
    :animate="currentState"
    :transition="{ duration: 0.5, ease: 'easeInOut' }"
    @mouseenter="startAnimation"
    @mouseleave="stopAnimation"
  >
    <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
    <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
  </motion.svg>
</template>
