<script setup lang="ts">
import { ref } from 'vue'

import { useColorMode } from '@vueuse/core'
import { MoonIcon, SunIcon, UserIcon } from 'lucide-vue-next'
import { RouterView, useRoute, useRouter } from 'vue-router'

import logo from '@/assets/logo/logo.svg'

import { useAuthStore } from '@/stores/auth'

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'

import ErrorBoundary from '@/components/utils/ErrorBoundary.vue'
import LanguageSwitch from '@/components/utils/LanguageSwitch.vue'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()
const mode = useColorMode()

// Toggle between fixed header with scrollable content vs full-height layout
const useFixedHeader = ref(true)

const navigateToAbout = () => {
  router.push({ name: 'about' })
}

const navigateToLanding = () => {
  router.push({ name: 'landing' })
}

const handleGetStarted = () => {
  const redirectUri = import.meta.env.VITE_AUTH0_CALLBACK_URL || `${window.location.origin}/app/home`
  authStore.auth0.loginWithRedirect({
    authorizationParams: {
      redirect_uri: redirectUri,
    },
  })
}
</script>

<template>
  <div
    :class="useFixedHeader ? 'h-screen flex flex-col' : 'min-h-screen bg-background flex flex-col'"
  >
    <!-- Header for unauthenticated users -->
    <header :class="useFixedHeader ? 'border-b flex-shrink-0' : 'border-b'">
      <div class="max-w-7xl w-full mx-auto px-4 py-3 flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <button
            @click="navigateToLanding"
            class="flex items-center gap-2 text-2xl font-bold hover:opacity-80 transition-opacity"
          >
            <img
              :src="logo"
              alt="Logo"
              class="h-16 w-16"
            />
            {{ $t('preauth.layout.appName') }}
          </button>
        </div>

        <nav class="flex items-center space-x-2">
          <!-- Language Switch -->
          <LanguageSwitch variant="ghost" size="sm" :show-text="false" />

          <!-- Theme Toggle -->
          <Button
            variant="ghost"
            size="sm"
            @click="mode = mode === 'dark' ? 'light' : 'dark'"
            :aria-label="mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
          >
            <SunIcon v-if="mode === 'dark'" class="h-4 w-4" />
            <MoonIcon v-else class="h-4 w-4" />
          </Button>

          <!-- Navigation buttons -->
          <Button
            variant="ghost"
            @click="navigateToAbout"
            :class="{ 'bg-muted': route.name === 'about' }"
          >
            {{ $t('preauth.layout.navigation.about') }}
          </Button>

          <!-- User section - show if authenticated -->
          <div v-if="authStore.isAuthenticated" class="border-l">
            <div
              class="flex items-center space-x-3 ml-4 p-1 cursor-pointer hover:bg-muted rounded"
              @click="router.push({ name: 'home' })"
            >
              <Avatar class="h-8 w-8">
                <AvatarImage
                  :src="authStore.user?.picture || ''"
                  :alt="authStore.user?.name || authStore.user?.email || 'User'"
                />
                <AvatarFallback>
                  <UserIcon class="h-4 w-4" />
                </AvatarFallback>
              </Avatar>
              <div class="flex flex-col">
                <span class="text-sm font-medium">{{
                  authStore.user?.name || authStore.user?.email
                }}</span>
                <div class="text-xs p-0 h-auto justify-start">
                  {{ $t('preauth.layout.navigation.goToDashboard') }}
                </div>
              </div>
            </div>
          </div>

          <!-- Sign in button - show if not authenticated -->
          <Button v-else @click="handleGetStarted">{{
            $t('preauth.layout.navigation.signIn')
          }}</Button>
        </nav>
      </div>
    </header>

    <!-- Main content area for unauthenticated views -->
    <main :class="useFixedHeader ? 'flex-1 overflow-auto flex flex-col' : 'flex-1 flex flex-col'">
      <div class="max-w-7xl w-full mx-auto px-4 py-8 flex-1">
        <ErrorBoundary>
          <RouterView />
        </ErrorBoundary>
      </div>

      <!-- Footer for unauthenticated users -->
      <footer class="border-t mt-auto flex-shrink-0">
        <div class="max-w-7xl w-full mx-auto px-4 py-6 text-center text-muted-foreground">
          <p>{{ $t('preauth.layout.footer.copyright') }}</p>
        </div>
      </footer>
    </main>
  </div>
</template>

<style scoped></style>
