<script setup lang="ts">
import { Clock } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import Button from '@/components/ui/button/Button.vue'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const authStore = useAuthStore()
</script>

<template>
  <div class="flex min-h-screen items-center justify-center">
    <div class="mx-auto max-w-md text-center">
      <div class="mb-6 flex justify-center">
        <div class="rounded-full bg-muted p-4">
          <Clock class="h-12 w-12 text-muted-foreground" />
        </div>
      </div>
      <h1 class="text-3xl font-bold">
        {{ t('common.pendingApproval.title') }}
      </h1>
      <p class="mt-3 text-muted-foreground">
        {{ t('common.pendingApproval.description') }}
      </p>
      <p class="mt-2 text-sm text-muted-foreground">
        {{ t('common.pendingApproval.hint') }}
      </p>
      <Button class="mt-8" variant="outline" @click="authStore.logout()">
        {{ t('common.pendingApproval.logout') }}
      </Button>
    </div>
  </div>
</template>
