<script setup lang="ts">
import { computed } from 'vue'

import { ArrowLeftIcon } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { useAppConfig } from '@/composables/useAppConfig'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

const router = useRouter()
const { t } = useI18n()
const config = useAppConfig()

const goBackToHome = () => {
  router.push({ name: 'landing' })
}

const responsibleBlock = computed(() => {
  return [
    config.LEGAL_NAME,
    config.LEGAL_ADDRESS,
    config.LEGAL_CITY,
    t('preauth.impressum.country'),
  ]
    .filter(Boolean)
    .join('\n')
})

const contactBlock = computed(() => {
  const lines: string[] = []
  if (config.LEGAL_EMAIL)
    lines.push(`${t('preauth.impressum.contact.emailLabel')}: ${config.LEGAL_EMAIL}`)
  if (config.LEGAL_PHONE)
    lines.push(`${t('preauth.impressum.contact.phoneLabel')}: ${config.LEGAL_PHONE}`)
  return lines.join('\n')
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col md:flex-row md:items-center md:justify-between">
      <div class="space-y-2">
        <h1 class="text-3xl font-bold">{{ $t('preauth.impressum.title') }}</h1>
        <p class="text-muted-foreground">
          {{ $t('preauth.impressum.subtitle') }}
        </p>
      </div>
      <Button @click="goBackToHome" variant="ghost" size="sm" class="gap-2">
        <ArrowLeftIcon class="h-4 w-4" />
        {{ $t('preauth.impressum.backToHome') }}
      </Button>
    </div>

    <div class="space-y-8 max-w-prose">
      <!-- Responsible person -->
      <section class="space-y-3">
        <h2 class="text-2xl font-semibold">{{ $t('preauth.impressum.responsible.title') }}</h2>
        <Card>
          <CardContent class="text-muted-foreground whitespace-pre-line">
            {{ responsibleBlock }}
          </CardContent>
        </Card>
      </section>

      <!-- Contact -->
      <section class="space-y-3">
        <h2 class="text-2xl font-semibold">{{ $t('preauth.impressum.contact.title') }}</h2>
        <Card>
          <CardContent class="text-muted-foreground whitespace-pre-line">
            {{ contactBlock }}
          </CardContent>
        </Card>
      </section>

      <!-- Disclaimer -->
      <section class="space-y-3">
        <h2 class="text-2xl font-semibold">{{ $t('preauth.impressum.disclaimer.title') }}</h2>
        <p class="text-muted-foreground">{{ $t('preauth.impressum.disclaimer.content') }}</p>
      </section>

      <!-- Liability for content -->
      <section class="space-y-3">
        <h2 class="text-2xl font-semibold">{{ $t('preauth.impressum.liability.title') }}</h2>
        <p class="text-muted-foreground">{{ $t('preauth.impressum.liability.content') }}</p>
      </section>

      <!-- Liability for links -->
      <section class="space-y-3">
        <h2 class="text-2xl font-semibold">{{ $t('preauth.impressum.links.title') }}</h2>
        <p class="text-muted-foreground">{{ $t('preauth.impressum.links.content') }}</p>
      </section>

      <!-- Copyright -->
      <section class="space-y-3">
        <h2 class="text-2xl font-semibold">{{ $t('preauth.impressum.copyright.title') }}</h2>
        <p class="text-muted-foreground">{{ $t('preauth.impressum.copyright.content') }}</p>
      </section>
    </div>
  </div>
</template>

<style scoped></style>
