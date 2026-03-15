<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'

const { t } = useI18n()
const error = ref<Error | null>(null)

onErrorCaptured((err: Error) => {
  error.value = err
  return false
})

const reset = () => {
  error.value = null
}
</script>

<template>
  <div v-if="error" class="flex-1 flex items-center justify-center p-8">
    <div class="text-center space-y-4 max-w-md">
      <div class="text-4xl">&#x26A0;</div>
      <h2 class="text-xl font-semibold">{{ t('common.errors.boundary.title') }}</h2>
      <p class="text-muted-foreground">{{ t('common.errors.boundary.description') }}</p>
      <pre
        v-if="error.message"
        class="text-xs text-left bg-muted p-3 rounded-md overflow-auto max-h-32"
      >{{ error.message }}</pre>
      <details v-if="error.stack" class="text-left">
        <summary class="text-xs text-muted-foreground cursor-pointer">Stack trace</summary>
        <pre class="text-xs bg-muted p-3 rounded-md overflow-auto max-h-64 mt-2">{{ error.stack }}</pre>
      </details>
      <div class="flex gap-2 justify-center">
        <Button variant="outline" @click="reset">{{ t('common.errors.boundary.tryAgain') }}</Button>
        <Button variant="outline" @click="$router.push({ name: 'home' })">{{
          t('common.errors.boundary.goHome')
        }}</Button>
      </div>
    </div>
  </div>
  <slot v-else />
</template>
