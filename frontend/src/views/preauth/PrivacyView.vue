<script setup lang="ts">
import { computed } from 'vue'

import { ArrowLeftIcon } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

import { useAppConfig } from '@/composables/useAppConfig'

import { Button } from '@/components/ui/button'

const router = useRouter()
const config = useAppConfig()

const goBackToHome = () => {
  router.push({ name: 'landing' })
}

const controllerBlock = computed(() => {
  const lines = [config.LEGAL_NAME, config.LEGAL_ADDRESS, config.LEGAL_CITY, 'Germany'].filter(
    Boolean,
  )
  if (config.LEGAL_EMAIL) lines.push('', `Email: ${config.LEGAL_EMAIL}`)
  return lines.join('\n')
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col md:flex-row md:items-center md:justify-between">
      <div class="space-y-2">
        <h1 class="text-3xl font-bold">{{ $t('preauth.privacy.title') }}</h1>
        <p class="text-muted-foreground">
          {{ $t('preauth.privacy.lastUpdated') }}
        </p>
      </div>
      <Button @click="goBackToHome" variant="ghost" size="sm" class="gap-2">
        <ArrowLeftIcon class="h-4 w-4" />
        {{ $t('preauth.privacy.backToHome') }}
      </Button>
    </div>

    <div class="space-y-8 max-w-prose">
      <!-- Introduction -->
      <section class="space-y-3">
        <p class="text-muted-foreground">
          {{ $t('preauth.privacy.intro') }}
        </p>
      </section>

      <!-- Controller -->
      <section class="space-y-3">
        <h2 class="text-2xl font-semibold">{{ $t('preauth.privacy.controller.title') }}</h2>
        <div class="p-4 border rounded-lg text-muted-foreground whitespace-pre-line">
          {{ controllerBlock }}
        </div>
      </section>

      <!-- Data we collect -->
      <section class="space-y-3">
        <h2 class="text-2xl font-semibold">{{ $t('preauth.privacy.dataCollected.title') }}</h2>
        <p class="text-muted-foreground">{{ $t('preauth.privacy.dataCollected.intro') }}</p>
        <ul class="list-disc pl-6 space-y-1 text-muted-foreground">
          <li>{{ $t('preauth.privacy.dataCollected.items.name') }}</li>
          <li>{{ $t('preauth.privacy.dataCollected.items.email') }}</li>
          <li>{{ $t('preauth.privacy.dataCollected.items.picture') }}</li>
          <li>{{ $t('preauth.privacy.dataCollected.items.bookings') }}</li>
        </ul>
      </section>

      <!-- Purpose -->
      <section class="space-y-3">
        <h2 class="text-2xl font-semibold">{{ $t('preauth.privacy.purpose.title') }}</h2>
        <ul class="list-disc pl-6 space-y-1 text-muted-foreground">
          <li>{{ $t('preauth.privacy.purpose.items.account') }}</li>
          <li>{{ $t('preauth.privacy.purpose.items.scheduling') }}</li>
          <li>{{ $t('preauth.privacy.purpose.items.notifications') }}</li>
          <li>{{ $t('preauth.privacy.purpose.items.security') }}</li>
        </ul>
      </section>

      <!-- Legal basis -->
      <section class="space-y-3">
        <h2 class="text-2xl font-semibold">{{ $t('preauth.privacy.legalBasis.title') }}</h2>
        <p class="text-muted-foreground">{{ $t('preauth.privacy.legalBasis.description') }}</p>
      </section>

      <!-- Third-party services -->
      <section class="space-y-3">
        <h2 class="text-2xl font-semibold">{{ $t('preauth.privacy.thirdParty.title') }}</h2>
        <div class="space-y-4">
          <div class="p-4 border rounded-lg">
            <h3 class="font-semibold mb-1">{{ $t('preauth.privacy.thirdParty.auth0.title') }}</h3>
            <p class="text-sm text-muted-foreground">
              {{ $t('preauth.privacy.thirdParty.auth0.description') }}
            </p>
          </div>
          <div class="p-4 border rounded-lg">
            <h3 class="font-semibold mb-1">{{ $t('preauth.privacy.thirdParty.email.title') }}</h3>
            <p class="text-sm text-muted-foreground">
              {{ $t('preauth.privacy.thirdParty.email.description') }}
            </p>
          </div>
        </div>
      </section>

      <!-- Data retention -->
      <section class="space-y-3">
        <h2 class="text-2xl font-semibold">{{ $t('preauth.privacy.retention.title') }}</h2>
        <p class="text-muted-foreground">{{ $t('preauth.privacy.retention.description') }}</p>
      </section>

      <!-- Your rights -->
      <section class="space-y-3">
        <h2 class="text-2xl font-semibold">{{ $t('preauth.privacy.rights.title') }}</h2>
        <p class="text-muted-foreground">{{ $t('preauth.privacy.rights.intro') }}</p>
        <ul class="list-disc pl-6 space-y-1 text-muted-foreground">
          <li>{{ $t('preauth.privacy.rights.items.access') }}</li>
          <li>{{ $t('preauth.privacy.rights.items.rectification') }}</li>
          <li>{{ $t('preauth.privacy.rights.items.erasure') }}</li>
          <li>{{ $t('preauth.privacy.rights.items.restriction') }}</li>
          <li>{{ $t('preauth.privacy.rights.items.portability') }}</li>
          <li>{{ $t('preauth.privacy.rights.items.objection') }}</li>
        </ul>
        <p class="text-muted-foreground">{{ $t('preauth.privacy.rights.contact') }}</p>
      </section>

      <!-- Cookies -->
      <section class="space-y-3">
        <h2 class="text-2xl font-semibold">{{ $t('preauth.privacy.cookies.title') }}</h2>
        <p class="text-muted-foreground">{{ $t('preauth.privacy.cookies.description') }}</p>
      </section>

      <!-- Changes -->
      <section class="space-y-3">
        <h2 class="text-2xl font-semibold">{{ $t('preauth.privacy.changes.title') }}</h2>
        <p class="text-muted-foreground">{{ $t('preauth.privacy.changes.description') }}</p>
      </section>
    </div>
  </div>
</template>

<style scoped></style>
