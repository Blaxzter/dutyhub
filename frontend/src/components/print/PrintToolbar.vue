<script setup lang="ts">
import { ref } from 'vue'

import { Printer, Settings, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import Button from '@/components/ui/button/Button.vue'

const { t } = useI18n()

defineProps<{
  /** Disable print button (e.g. while loading) */
  disabled?: boolean
}>()

const emit = defineEmits<{
  print: []
}>()

const expanded = ref(true)
</script>

<template>
  <!-- Floating toolbar — hidden when printing -->
  <div
    class="no-print fixed z-50 right-4 top-1/2 -translate-y-1/2 max-sm:top-auto max-sm:bottom-4 max-sm:right-4 max-sm:translate-y-0"
  >
    <!-- Collapsed: small button -->
    <Button
      v-if="!expanded"
      size="icon"
      variant="outline"
      class="shadow-lg"
      @click="expanded = true"
    >
      <Settings class="h-4 w-4" />
    </Button>

    <!-- Expanded: options panel -->
    <div
      v-else
      class="bg-card border rounded-lg shadow-lg p-3 space-y-3 w-64 max-h-[80vh] flex flex-col"
    >
      <div class="flex items-center justify-between shrink-0">
        <span class="text-sm font-semibold">{{ t('print.toolbar.title') }}</span>
        <button
          class="h-5 w-5 flex items-center justify-center rounded hover:bg-muted"
          @click="expanded = false"
        >
          <X class="h-3.5 w-3.5" />
        </button>
      </div>

      <!-- Scrollable options area -->
      <div class="space-y-2 overflow-y-auto min-h-0">
        <slot />
      </div>

      <Button class="w-full shrink-0" :disabled="disabled" @click="emit('print')">
        <Printer class="mr-2 h-4 w-4" />
        {{ t('print.printButton') }}
      </Button>
    </div>
  </div>
</template>
