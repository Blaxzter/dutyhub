<script setup lang="ts">
import { EyeOffIcon, HeartIcon, LockIcon, ShieldCheckIcon } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import logo from '@/assets/logo/logo.svg'

import LandingSection from './LandingSection.vue'
import SectionHeading from './SectionHeading.vue'

const { t } = useI18n()

const cards = [
  { key: 'private', icon: LockIcon },
  { key: 'data', icon: EyeOffIcon },
  { key: 'gdpr', icon: ShieldCheckIcon },
  { key: 'free', icon: HeartIcon },
] as const

const legalLinks = [
  { name: 'privacy', label: 'preauth.layout.footer.privacy' },
  { name: 'terms', label: 'preauth.layout.footer.terms' },
  { name: 'impressum', label: 'preauth.layout.footer.impressum' },
] as const
</script>

<template>
  <LandingSection id="about" width="wide">
    <SectionHeading
      :eyebrow="t('preauth.landing.about.eyebrow')"
      :title="t('preauth.landing.about.title')"
      :lede="t('preauth.landing.about.lede')"
    />

    <!-- The name is a German pun that nobody guesses, so it gets explained. -->
    <div
      class="mx-auto mt-10 flex max-w-2xl flex-col items-center gap-4 rounded-2xl border bg-card p-6 text-center shadow-sm sm:flex-row sm:gap-6 sm:p-8 sm:text-left"
    >
      <img :src="logo" alt="" class="size-16 shrink-0 rounded-xl" />
      <p class="text-pretty leading-relaxed text-muted-foreground">
        {{ t('preauth.landing.about.nameExplainer') }}
      </p>
    </div>

    <ul class="mt-12 grid gap-6 sm:grid-cols-2">
      <li v-for="card in cards" :key="card.key" class="rounded-2xl border bg-card p-6 shadow-sm">
        <span
          class="flex size-10 items-center justify-center rounded-lg bg-primary/10"
          aria-hidden="true"
        >
          <component :is="card.icon" class="size-5 text-primary" />
        </span>
        <h3 class="mt-4 text-lg font-semibold">
          {{ t(`preauth.landing.about.cards.${card.key}.title`) }}
        </h3>
        <p class="mt-2 text-pretty text-sm leading-relaxed text-muted-foreground">
          {{ t(`preauth.landing.about.cards.${card.key}.description`) }}
        </p>
      </li>
    </ul>

    <p class="mt-10 text-center text-sm text-muted-foreground">
      {{ t('preauth.landing.about.legalIntro') }}
      <span class="mt-3 flex flex-wrap items-center justify-center gap-x-4 gap-y-2">
        <RouterLink
          v-for="link in legalLinks"
          :key="link.name"
          :to="{ name: link.name }"
          class="font-medium text-foreground underline underline-offset-4 hover:text-primary"
        >
          {{ t(link.label) }}
        </RouterLink>
      </span>
    </p>
  </LandingSection>
</template>
