<script setup lang="ts">
import { computed } from 'vue'

import { useMediaQuery } from '@vueuse/core'

import { Dialog } from '@/components/ui/dialog'
import { Drawer } from '@/components/ui/drawer'

import { RESPONSIVE_DIALOG_MOBILE_QUERY, provideResponsiveDialogContext } from './utils'

const props = defineProps<{
  open?: boolean
  defaultOpen?: boolean
}>()

const emits = defineEmits<{ 'update:open': [value: boolean] }>()

const mediaMatches = useMediaQuery(RESPONSIVE_DIALOG_MOBILE_QUERY)
const isMobile = computed(() => mediaMatches.value)

provideResponsiveDialogContext({ isMobile })

const openModel = computed({
  get: () => props.open ?? false,
  set: (value: boolean) => emits('update:open', value),
})
</script>

<template>
  <!--
    Only ever one branch in the DOM. Rendering both and hiding one with CSS
    would double every `data-testid` inside, which is what the E2E suite and the
    tour anchor on — and would put two focus traps on the page at once.
  -->
  <Drawer v-if="isMobile" v-model:open="openModel" :default-open="defaultOpen">
    <slot />
  </Drawer>
  <Dialog v-else v-model:open="openModel" :default-open="defaultOpen">
    <slot />
  </Dialog>
</template>
