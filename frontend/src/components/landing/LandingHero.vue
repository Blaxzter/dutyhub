<script setup lang="ts">
import { ArrowRightIcon, MailOpenIcon } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { Button } from '@/components/ui/button'

import ShiftBoardConcept from './ShiftBoardConcept.vue'

defineProps<{ isAuthenticated: boolean }>()
const emit = defineEmits<{ signIn: []; dashboard: [] }>()

const { t } = useI18n()

const proofPoints = ['free', 'noInstall', 'privacy'] as const
</script>

<template>
  <section class="relative overflow-hidden border-b">
    <!-- Warm wash behind the hero; decorative only. -->
    <div
      aria-hidden="true"
      class="absolute inset-0"
      style="
        background:
          radial-gradient(
            ellipse 70% 60% at 15% 0%,
            color-mix(in oklab, var(--primary) 12%, transparent) 0%,
            transparent 60%
          ),
          radial-gradient(
            ellipse 60% 55% at 95% 20%,
            color-mix(in oklab, var(--hero-speck) 24%, transparent) 0%,
            transparent 65%
          );
      "
    />

    <!-- Two columns from `lg`, so the pitch and the picture share the fold. -->
    <div
      class="relative mx-auto grid max-w-6xl items-center gap-10 px-4 pb-16 pt-14 sm:px-6 sm:pb-20 sm:pt-16 lg:grid-cols-[1.05fr_1fr] lg:gap-14 lg:pb-24"
    >
      <div class="max-w-xl text-center lg:text-left">
        <p
          class="inline-flex items-center rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-medium text-primary"
        >
          {{ t('preauth.landing.hero.eyebrow') }}
        </p>

        <h1
          data-testid="page-heading"
          class="mt-5 text-balance text-4xl font-bold leading-[1.1] tracking-tight sm:text-5xl"
        >
          {{ t('preauth.landing.hero.title') }}
        </h1>

        <p class="mt-5 text-pretty text-lg leading-relaxed text-muted-foreground">
          {{ t('preauth.landing.hero.subtitle') }}
        </p>

        <div
          class="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center lg:justify-start"
        >
          <Button
            v-if="isAuthenticated"
            data-testid="btn-cta-primary"
            size="lg"
            class="w-full gap-2 sm:w-auto"
            @click="emit('dashboard')"
          >
            {{ t('preauth.layout.navigation.goToDashboard') }}
            <ArrowRightIcon class="size-4" />
          </Button>

          <template v-else>
            <Button
              data-testid="btn-cta-primary"
              size="lg"
              class="w-full gap-2 sm:w-auto"
              @click="emit('signIn')"
            >
              {{ t('preauth.landing.hero.ctaPrimary') }}
              <ArrowRightIcon class="size-4" />
            </Button>
            <Button
              data-testid="btn-cta-secondary"
              variant="outline"
              size="lg"
              class="w-full gap-2 sm:w-auto"
              @click="emit('signIn')"
            >
              <MailOpenIcon class="size-4" />
              {{ t('preauth.landing.hero.ctaSecondary') }}
            </Button>
          </template>
        </div>

        <ul
          class="mt-6 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm text-muted-foreground lg:justify-start"
        >
          <li v-for="point in proofPoints" :key="point" class="flex items-center gap-2">
            <span aria-hidden="true" class="size-1.5 rounded-full bg-primary" />
            {{ t(`preauth.landing.hero.proof.${point}`) }}
          </li>
        </ul>
      </div>

      <ShiftBoardConcept class="mx-auto w-full max-w-md lg:max-w-none" />
    </div>
  </section>
</template>
