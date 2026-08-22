<script setup lang="ts">
import { ArrowRightIcon } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { Button } from '@/components/ui/button'

import LandingSection from './LandingSection.vue'
import SectionHeading from './SectionHeading.vue'

defineProps<{ isAuthenticated: boolean }>()
const emit = defineEmits<{ signIn: []; dashboard: [] }>()

const { t } = useI18n()
</script>

<template>
  <LandingSection id="get-started" tone="hero">
    <SectionHeading
      tone="hero"
      :eyebrow="t('preauth.landing.finalCta.eyebrow')"
      :title="t('preauth.landing.finalCta.title')"
      :lede="t('preauth.landing.finalCta.lede')"
    />

    <div class="mt-8 flex justify-center">
      <!-- `secondary` is a dark grey in dark mode, which vanishes against the
           green band. Invert the hero tokens instead so the button reads in
           both palettes and both modes. -->
      <Button
        data-testid="btn-cta-footer"
        size="lg"
        class="gap-2 bg-hero-foreground text-hero hover:bg-hero-foreground/90"
        @click="isAuthenticated ? emit('dashboard') : emit('signIn')"
      >
        {{
          isAuthenticated
            ? t('preauth.layout.navigation.goToDashboard')
            : t('preauth.landing.finalCta.button')
        }}
        <ArrowRightIcon class="size-4" />
      </Button>
    </div>
  </LandingSection>
</template>
