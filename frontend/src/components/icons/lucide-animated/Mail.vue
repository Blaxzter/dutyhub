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
  <svg
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
    @mouseenter="startAnimation"
    @mouseleave="stopAnimation"
  >
    <rect width="20" height="16" x="2" y="4" rx="2" />
    <motion.path
      d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"
      :variants="{
        normal: { d: 'm22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7' },
        animate: { d: 'm22 4-8.97 8.7a1.94 1.94 0 0 1-2.06 0L2 4' },
      }"
      :animate="currentState"
      :transition="{ duration: 0.3, ease: 'easeInOut' }"
    />
  </svg>
</template>
