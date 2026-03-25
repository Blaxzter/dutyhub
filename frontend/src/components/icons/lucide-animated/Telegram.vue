<script setup lang="ts">
import { ref } from 'vue'
import { motion } from 'motion-v'
import { siTelegram } from 'simple-icons'

interface Props {
  size?: number
  class?: string | string[]
  useColor?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 24,
  class: '',
  useColor: false,
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
    :fill="props.useColor ? '#' + siTelegram.hex : 'currentColor'"
    role="img"
    :class="props.class"
    :variants="{
      normal: { scale: 1, rotate: 0 },
      animate: { scale: [1, 1.15, 1], rotate: [0, -8, 8, 0] },
    }"
    :animate="currentState"
    :transition="{ duration: 0.5, ease: 'easeInOut' }"
    @mouseenter="startAnimation"
    @mouseleave="stopAnimation"
  >
    <title>{{ siTelegram.title }}</title>
    <path :d="siTelegram.path" />
  </motion.svg>
</template>
