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
      animate: { rotate: [0, -5, 5, -5, 5, 0] },
    }"
    :animate="currentState"
    :transition="{ duration: 0.5, ease: 'easeInOut' }"
    @mouseenter="startAnimation"
    @mouseleave="stopAnimation"
  >
    <rect width="14" height="20" x="5" y="2" rx="2" ry="2" />
    <path d="M12 18h.01" />
  </motion.svg>
</template>
