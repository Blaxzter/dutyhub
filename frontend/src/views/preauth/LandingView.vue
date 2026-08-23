<script setup lang="ts">
import { computed } from 'vue'

import { InfoIcon, LayoutGridIcon, UsersIcon, WorkflowIcon } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

import LandingAbout from '@/components/landing/LandingAbout.vue'
import LandingAudience from '@/components/landing/LandingAudience.vue'
import LandingCta from '@/components/landing/LandingCta.vue'
import LandingFeatures from '@/components/landing/LandingFeatures.vue'
import LandingHero from '@/components/landing/LandingHero.vue'
import LandingJourney from '@/components/landing/LandingJourney.vue'
import LandingSectionNav from '@/components/landing/LandingSectionNav.vue'

/**
 * The single pre-auth marketing page.
 *
 * `/about` and `/how-it-works` used to be separate views that each repeated a
 * slice of this content; they now redirect to the `#about` and `#how-it-works`
 * sections below, so there is one story in one place.
 */
const authStore = useAuthStore()
const router = useRouter()
const { t } = useI18n()

const sections = computed(() => [
  { id: 'audience', label: t('preauth.landing.nav.audience'), icon: UsersIcon },
  { id: 'how-it-works', label: t('preauth.landing.nav.howItWorks'), icon: WorkflowIcon },
  { id: 'features', label: t('preauth.landing.nav.features'), icon: LayoutGridIcon },
  { id: 'about', label: t('preauth.landing.nav.about'), icon: InfoIcon },
])

function signIn() {
  router.push({ name: 'login' })
}

function goToDashboard() {
  router.push({ name: 'home' })
}
</script>

<template>
  <div>
    <LandingHero
      :is-authenticated="authStore.isAuthenticated"
      @sign-in="signIn"
      @dashboard="goToDashboard"
    />

    <LandingSectionNav :items="sections" />

    <LandingAudience />
    <LandingJourney />
    <LandingFeatures />
    <LandingAbout />

    <LandingCta
      :is-authenticated="authStore.isAuthenticated"
      @sign-in="signIn"
      @dashboard="goToDashboard"
    />
  </div>
</template>
