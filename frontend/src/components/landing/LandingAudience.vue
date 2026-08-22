<script setup lang="ts">
import { CheckIcon, ClipboardListIcon, HandHeartIcon } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { getTranslationList } from '@/lib/utils'

import LandingSection from './LandingSection.vue'
import SectionHeading from './SectionHeading.vue'

const { t } = useI18n()

const roles = [
  { key: 'organiser', icon: ClipboardListIcon },
  { key: 'volunteer', icon: HandHeartIcon },
] as const

/** Bullet lists are authored as numbered keys — the convention in this repo. */
function points(role: string): string[] {
  return getTranslationList(t, `preauth.landing.audience.${role}.points`)
}
</script>

<template>
  <LandingSection id="audience" tone="tinted" width="wide">
    <SectionHeading
      :eyebrow="t('preauth.landing.audience.eyebrow')"
      :title="t('preauth.landing.audience.title')"
      :lede="t('preauth.landing.audience.lede')"
    />

    <div class="mt-12 grid gap-6 md:grid-cols-2">
      <div
        v-for="role in roles"
        :key="role.key"
        class="flex flex-col rounded-2xl border bg-card p-6 shadow-sm sm:p-8"
      >
        <div class="flex items-center gap-3">
          <span class="flex size-11 items-center justify-center rounded-xl bg-primary/10">
            <component :is="role.icon" class="size-5 text-primary" aria-hidden="true" />
          </span>
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
              {{ t(`preauth.landing.audience.${role.key}.label`) }}
            </p>
            <h3 class="text-xl font-semibold">
              {{ t(`preauth.landing.audience.${role.key}.title`) }}
            </h3>
          </div>
        </div>

        <p class="mt-4 leading-relaxed text-muted-foreground">
          {{ t(`preauth.landing.audience.${role.key}.description`) }}
        </p>

        <ul class="mt-6 space-y-3">
          <li v-for="point in points(role.key)" :key="point" class="flex gap-3">
            <CheckIcon class="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
            <span class="text-sm leading-relaxed">{{ point }}</span>
          </li>
        </ul>
      </div>
    </div>
  </LandingSection>
</template>
