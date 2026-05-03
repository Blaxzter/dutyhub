<script setup lang="ts">
import { computed } from 'vue'

import { useAuth0 } from '@auth0/auth0-vue'
import { useColorMode } from '@vueuse/core'
import { RouterView } from 'vue-router'
import 'vue-sonner/style.css'

import { usePalette } from '@/composables/usePalette'

import { useAuthStore } from '@/stores/auth'

import { Toaster } from '@/components/ui/sonner'

import GlobalDialog from '@/components/utils/GlobalDialog.vue'

const auth0 = useAuth0()
const authStore = useAuthStore()

// Show loading when either Auth0 is loading OR profile is being loaded
const isLoading = computed(() => auth0.isLoading.value || authStore.profileLoading)

// Initialize color mode + palette early so the right classes are on <html>
// before the first render.
useColorMode()
usePalette()
</script>

<template>
  <Toaster />
  <GlobalDialog />

  <!-- Loading state -->
  <div v-if="isLoading" class="min-h-screen flex items-center justify-center bg-background">
    <div class="text-center space-y-4">
      <div
        class="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto"
      ></div>
      <p class="text-muted-foreground">{{ $t('utils.loading') }}</p>
    </div>
  </div>

  <!-- Router outlet - layouts will be handled by nested routes -->
  <RouterView v-else />
</template>

<style scoped></style>
