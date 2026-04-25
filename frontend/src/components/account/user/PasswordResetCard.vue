<template>
  <Card>
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <KeyIcon class="h-5 w-5" animateOnHover triggerTarget="parent" />
        {{ $t('user.settings.password.title') }}
      </CardTitle>
      <CardDescription>{{ $t('user.settings.password.subtitle') }}</CardDescription>
    </CardHeader>
    <CardContent>
      <div class="space-y-4">
        <div class="p-4 bg-muted rounded-lg">
          <h4 class="font-medium mb-2">{{ $t('user.settings.password.section.title') }}</h4>
          <p class="text-sm text-muted-foreground mb-3">
            {{ $t('user.settings.password.section.description') }}
          </p>
          <Button
            @click="handlePasswordReset"
            :disabled="isLoading"
            variant="outline"
            size="sm"
            class="w-full sm:w-auto"
          >
            <MailIcon class="h-4 w-4 mr-2" />
            {{
              isLoading
                ? $t('user.settings.password.section.sending')
                : $t('user.settings.password.section.button')
            }}
          </Button>
        </div>

        <!-- Success/Error Messages -->
        <div v-if="message" :class="messageClass" class="p-4 rounded-lg">
          <h4 class="font-medium mb-2">{{ message.title }}</h4>
          <p class="text-sm">{{ message.description }}</p>
        </div>
      </div>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import { Key as KeyIcon } from '@respeak/lucide-motion-vue'
import axios from 'axios'
import { MailIcon } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

// Store
const authStore = useAuthStore()
const { t } = useI18n()

// Reactive state
const isLoading = ref(false)
const message = ref<{
  title: string
  description: string
  type: 'success' | 'error'
} | null>(null)

// Computed properties
const user = computed(() => authStore.user)

const messageClass = computed(() => {
  if (!message.value) return ''

  return message.value.type === 'success'
    ? 'bg-green-50 border border-green-200 text-green-800'
    : 'bg-red-50 border border-red-200 text-red-800'
})

// Handle password reset
const handlePasswordReset = async () => {
  if (!user.value?.email) {
    message.value = {
      title: t('user.settings.password.messages.error.title'),
      description: t('user.settings.password.messages.error.emailNotFound'),
      type: 'error',
    }
    return
  }

  isLoading.value = true
  message.value = null

  try {
    const options = {
      method: 'POST',
      url: `https://${import.meta.env.VITE_AUTH0_DOMAIN}/dbconnections/change_password`,
      headers: { 'content-type': 'application/json' },
      data: {
        client_id: import.meta.env.VITE_AUTH0_CLIENT_ID,
        email: user.value.email,
        connection: 'Username-Password-Authentication',
      },
    }

    await axios.request(options)

    message.value = {
      title: t('user.settings.password.messages.success.title'),
      description: t('user.settings.password.messages.success.description'),
      type: 'success',
    }
  } catch (error) {
    console.error('Password reset error:', error)

    message.value = {
      title: t('user.settings.password.messages.error.title'),
      description: t('user.settings.password.messages.error.sendFailed'),
      type: 'error',
    }
  } finally {
    isLoading.value = false
  }
}
</script>
