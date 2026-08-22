<script setup lang="ts">
import { computed } from 'vue'

import { useColorMode } from '@vueuse/core'
import { ArrowRight, Bell, CalendarRange, Megaphone, ShieldCheck, Users } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import wirksamDarkLogo from '@/assets/logo/wirksam-dark.svg'
import wirksamLightLogo from '@/assets/logo/wirksam-light.svg'

import Button from '@/components/ui/button/Button.vue'

export type SelectEventMode = 'onboarding' | 'switch' | 'expired'

const props = defineProps<{
  step: 1 | 2
  mode: SelectEventMode
  showMobileContinue?: boolean
}>()

defineEmits<{
  mobileContinue: []
  mobileBack: []
}>()

const { t } = useI18n()
const colorMode = useColorMode()

// Left pane sits on --hero (inverted vs page background) — flip the logo variant accordingly.
const visualLogo = computed(() =>
  colorMode.value === 'light' ? wirksamLightLogo : wirksamDarkLogo,
)

const headline = computed(() => {
  if (props.step === 2) return t('duties.selectEvent.visual.step2.headline')
  if (props.mode === 'expired') return t('duties.selectEvent.visual.expiredHeadline')
  if (props.mode === 'switch') return t('duties.selectEvent.visual.switchHeadline')
  return t('duties.selectEvent.visual.onboardingHeadline')
})

const subhead = computed(() =>
  props.step === 2
    ? t('duties.selectEvent.visual.step2.subhead')
    : t('duties.selectEvent.visual.subhead'),
)

const mobileContinueText = computed(() =>
  props.step === 2
    ? t('duties.selectEvent.visual.step2.mobileContinue')
    : t('duties.selectEvent.visual.mobileContinue'),
)
</script>

<template>
  <aside
    class="relative flex flex-col text-hero-foreground"
    :aria-hidden="props.showMobileContinue ? 'false' : 'true'"
  >
    <!-- Base hero fill -->
    <div class="absolute inset-0 -z-10 bg-hero" />
    <!-- Soft tonal glows driven by --hero-speck + --hero-speck-opacity. -->
    <div
      class="absolute inset-0 -z-10"
      style="
        background:
          radial-gradient(
            ellipse 90% 70% at 15% 10%,
            color-mix(in oklab, var(--hero-speck) var(--hero-speck-opacity), transparent) 0%,
            transparent 65%
          ),
          radial-gradient(
            ellipse 100% 80% at 100% 100%,
            color-mix(in oklab, var(--hero-speck) var(--hero-speck-opacity), transparent) 0%,
            transparent 70%
          );
      "
    />

    <div class="flex flex-1 min-h-0 flex-col overflow-y-auto overflow-x-hidden p-8 sm:p-12">
      <img :src="visualLogo" alt="WirkSam" class="h-10 w-auto self-start" />

      <div class="mx-auto mt-12 w-full max-w-md space-y-6 lg:mt-24">
        <h2 class="text-4xl xl:text-5xl font-bold leading-tight">{{ headline }}</h2>
        <p class="text-base text-hero-foreground/80">{{ subhead }}</p>

        <!-- Step 1: why scope to an event -->
        <div v-if="step === 1" class="grid grid-cols-2 gap-4 pt-4">
          <div class="flex items-start gap-3 rounded-xl bg-hero-foreground/10 p-4">
            <CalendarRange class="h-5 w-5 shrink-0" />
            <div class="text-sm">
              <p class="font-semibold">
                {{ t('duties.selectEvent.visual.features.scopedTitle') }}
              </p>
              <p class="text-hero-foreground/80">
                {{ t('duties.selectEvent.visual.features.scopedBody') }}
              </p>
            </div>
          </div>
          <div class="flex items-start gap-3 rounded-xl bg-hero-foreground/10 p-4">
            <Users class="h-5 w-5 shrink-0" />
            <div class="text-sm">
              <p class="font-semibold">
                {{ t('duties.selectEvent.visual.features.coordTitle') }}
              </p>
              <p class="text-hero-foreground/80">
                {{ t('duties.selectEvent.visual.features.coordBody') }}
              </p>
            </div>
          </div>
        </div>

        <!-- Step 2: what the notifications are for -->
        <div v-else class="space-y-3 pt-4">
          <div class="flex items-start gap-3 rounded-xl bg-hero-foreground/10 p-4">
            <Bell class="mt-0.5 h-5 w-5 shrink-0" />
            <div class="text-sm">
              <p class="font-semibold">
                {{ t('duties.selectEvent.visual.step2.features.remindersTitle') }}
              </p>
              <p class="text-hero-foreground/80">
                {{ t('duties.selectEvent.visual.step2.features.remindersBody') }}
              </p>
            </div>
          </div>
          <div class="flex items-start gap-3 rounded-xl bg-hero-foreground/10 p-4">
            <Megaphone class="mt-0.5 h-5 w-5 shrink-0" />
            <div class="text-sm">
              <p class="font-semibold">
                {{ t('duties.selectEvent.visual.step2.features.updatesTitle') }}
              </p>
              <p class="text-hero-foreground/80">
                {{ t('duties.selectEvent.visual.step2.features.updatesBody') }}
              </p>
            </div>
          </div>
          <div class="flex items-start gap-3 rounded-xl bg-hero-foreground/10 p-4">
            <ShieldCheck class="mt-0.5 h-5 w-5 shrink-0" />
            <div class="text-sm">
              <p class="font-semibold">
                {{ t('duties.selectEvent.visual.step2.features.controlTitle') }}
              </p>
              <p class="text-hero-foreground/80">
                {{ t('duties.selectEvent.visual.step2.features.controlBody') }}
              </p>
            </div>
          </div>
        </div>
        <div
          v-if="props.showMobileContinue"
          class="flex flex-col-reverse gap-2 pt-4 sm:flex-row lg:hidden"
        >
          <Button
            v-if="props.step === 2"
            variant="ghost"
            class="w-full text-hero-foreground hover:bg-hero-foreground/10 hover:text-hero-foreground sm:w-auto"
            data-testid="btn-mobile-intro-back"
            @click="$emit('mobileBack')"
          >
            {{ t('duties.selectEvent.pick.back') }}
          </Button>
          <Button
            size="lg"
            variant="secondary"
            class="w-full sm:flex-1"
            data-testid="btn-mobile-intro-continue"
            @click="$emit('mobileContinue')"
          >
            {{ mobileContinueText }}
            <ArrowRight class="ml-2 h-4 w-4" />
          </Button>
        </div>
      </div>

      <p class="mt-auto pt-10 text-xs text-hero-foreground/60">
        {{ t('duties.selectEvent.visual.footer') }}
      </p>
    </div>
  </aside>
</template>
