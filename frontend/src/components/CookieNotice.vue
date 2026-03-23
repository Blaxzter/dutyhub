<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { XIcon } from 'lucide-vue-next'

import { Button } from '@/components/ui/button'

const STORAGE_KEY = 'wirksam-cookie-notice-dismissed'

const visible = ref(false)

onMounted(() => {
  if (!localStorage.getItem(STORAGE_KEY)) {
    visible.value = true
  }
})

const dismiss = () => {
  localStorage.setItem(STORAGE_KEY, '1')
  visible.value = false
}
</script>

<template>
  <Transition
    enter-from-class="translate-y-full opacity-0"
    enter-active-class="transition duration-300 ease-out"
    enter-to-class="translate-y-0 opacity-100"
    leave-from-class="translate-y-0 opacity-100"
    leave-active-class="transition duration-200 ease-in"
    leave-to-class="translate-y-full opacity-0"
  >
    <div v-if="visible" class="fixed bottom-0 inset-x-0 z-50 p-4 pointer-events-none">
      <div
        class="max-w-lg mx-auto bg-card border rounded-lg shadow-lg p-4 flex items-center gap-3 pointer-events-auto"
      >
        <p class="text-sm text-muted-foreground flex-1">
          {{ $t('preauth.cookieNotice.message') }}
          <router-link :to="{ name: 'privacy' }" class="underline hover:text-foreground">
            {{ $t('preauth.cookieNotice.learnMore') }}
          </router-link>
        </p>
        <Button variant="outline" size="sm" @click="dismiss">
          {{ $t('preauth.cookieNotice.dismiss') }}
        </Button>
        <Button variant="ghost" size="icon" class="h-8 w-8 shrink-0" @click="dismiss">
          <XIcon class="h-4 w-4" />
        </Button>
      </div>
    </div>
  </Transition>
</template>
