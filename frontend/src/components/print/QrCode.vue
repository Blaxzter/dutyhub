<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import QRCode from 'qrcode'

const props = withDefaults(
  defineProps<{
    value: string
    size?: number
  }>(),
  { size: 128 },
)

const emit = defineEmits<{
  ready: []
}>()

const dataUrl = ref('')

const generate = async () => {
  if (!props.value) return
  dataUrl.value = await QRCode.toDataURL(props.value, {
    width: props.size,
    margin: 0,
    color: { dark: '#000000', light: '#ffffff' },
  })
  emit('ready')
}

onMounted(generate)
watch(() => props.value, generate)
</script>

<template>
  <img v-if="dataUrl" :src="dataUrl" :width="size" :height="size" alt="QR Code" />
</template>
