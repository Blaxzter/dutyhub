<script setup lang="ts">
import { RouterView } from 'vue-router'

import ErrorBoundary from '@/components/utils/ErrorBoundary.vue'
</script>

<template>
  <div class="min-h-screen bg-background">
    <main class="mx-auto px-4 py-4">
      <ErrorBoundary>
        <RouterView />
      </ErrorBoundary>
    </main>
  </div>
</template>
