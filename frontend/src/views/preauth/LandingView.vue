<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

import { Button } from '@/components/ui/button'

import logo from '@/assets/logo/logo.svg'

const authStore = useAuthStore()
const router = useRouter()
useI18n()

const handleGetStarted = () => {
  if (authStore.isAuthenticated) {
    router.push({ name: 'home' })
    return
  }
  const redirectUri = import.meta.env.VITE_AUTH0_CALLBACK_URL || `${window.location.origin}/app/home`
  authStore.auth0.loginWithRedirect({
    authorizationParams: {
      redirect_uri: redirectUri,
    },
  })
}

const navigateToAbout = () => {
  router.push({ name: 'about' })
}
</script>

<template>
  <div class="text-center space-y-8">
    <div class="space-y-4">
      <img :src="logo" alt="Logo" class="h-24 w-24 mx-auto rounded-xl" />
      <h1 class="text-4xl font-bold tracking-tight">{{ $t('preauth.landing.welcome') }}</h1>
      <p class="text-xl text-muted-foreground max-w-2xl mx-auto">
        {{ $t('preauth.landing.subtitle') }}
      </p>
    </div>

    <div class="space-y-4">
      <div class="flex flex-col sm:flex-row gap-4 justify-center items-center">
        <Button @click="handleGetStarted" size="lg" class="px-8 py-3 text-lg font-medium">
          {{ authStore.isAuthenticated ? $t('preauth.layout.navigation.goToDashboard') : $t('preauth.landing.getStarted') }}
        </Button>
        <Button
          @click="navigateToAbout"
          variant="outline"
          size="lg"
          class="px-8 py-3 text-lg font-medium"
        >
          {{ $t('preauth.landing.learnMore') }}
        </Button>
      </div>
      <p class="text-sm text-muted-foreground">{{ $t('preauth.landing.authNote') }}</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16">
      <div class="p-6 border rounded-lg">
        <h3 class="text-lg font-semibold mb-2">
          {{ $t('preauth.landing.features.fastSecure.title') }}
        </h3>
        <p class="text-muted-foreground">
          {{ $t('preauth.landing.features.fastSecure.description') }}
        </p>
      </div>
      <div class="p-6 border rounded-lg">
        <h3 class="text-lg font-semibold mb-2">
          {{ $t('preauth.landing.features.easyToUse.title') }}
        </h3>
        <p class="text-muted-foreground">
          {{ $t('preauth.landing.features.easyToUse.description') }}
        </p>
      </div>
      <div class="p-6 border rounded-lg">
        <h3 class="text-lg font-semibold mb-2">
          {{ $t('preauth.landing.features.scalable.title') }}
        </h3>
        <p class="text-muted-foreground">
          {{ $t('preauth.landing.features.scalable.description') }}
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
