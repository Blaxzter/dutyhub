<script setup lang="ts">
/**
 * Redeem an email-verification link.
 *
 * There is nothing to fill in, so the request goes out on mount and the screen
 * reports what came back. Four outcomes, and each one gets its own words:
 * confirming, confirmed, expired, and spent-or-unknown.
 *
 * The server cannot tell "already used" apart from "never existed" without
 * leaking which links it has issued, so both arrive as `auth.invalid_token` and
 * share a panel — whose copy names the likely case, since a link opened twice is
 * far more common than a forged one, and in that case the address is already
 * confirmed and nothing is wrong.
 *
 * Verification is a nudge, not a gate (login is never blocked on it), so every
 * outcome offers a way onwards rather than leaving the visitor stranded.
 */
import { computed, onMounted, ref } from 'vue'

import { CircleCheckBigIcon, LoaderIcon, MailWarningIcon } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

import { useAuth } from '@/composables/useAuth'

import AuthShell from '@/components/auth/AuthShell.vue'
import { Button } from '@/components/ui/button'

import { client } from '@/client/client.gen'
import { normalizeApiError } from '@/lib/api-errors'

type VerificationState = 'pending' | 'success' | 'expired' | 'invalid'

const { t } = useI18n()
const route = useRoute()
const authStore = useAuthStore()
const { isAuthenticated } = useAuth()

const state = ref<VerificationState>('pending')

const heading = computed(() => t(`auth.verifyEmail.${state.value}.title`))
const description = computed(() => t(`auth.verifyEmail.${state.value}.description`))

/** A dead link is not a moment to open with "now we can reach you". */
const isProblem = computed(() => state.value === 'expired' || state.value === 'invalid')

const stateIcon = computed(() => {
  if (state.value === 'pending') return LoaderIcon
  if (state.value === 'success') return CircleCheckBigIcon
  return MailWarningIcon
})

onMounted(async () => {
  const token = typeof route.query.token === 'string' ? route.query.token : ''
  if (!token) {
    state.value = 'invalid'
    return
  }

  try {
    // Public endpoint — the link has to work in whichever browser the mail was
    // opened in, signed in or not.
    await client.post<unknown, unknown, true>({
      url: '/auth/verify-email',
      body: { token },
      throwOnError: true,
    })
    state.value = 'success'

    // Someone who verified in the browser they are already signed in to should
    // not keep seeing the "unverified" badge until their next reload.
    if (isAuthenticated.value) {
      try {
        await authStore.loadProfile()
      } catch {
        // Cosmetic only: the address is verified either way.
      }
    }
  } catch (error) {
    state.value = normalizeApiError(error).code === 'auth.token_expired' ? 'expired' : 'invalid'
  }
})
</script>

<template>
  <AuthShell
    hero="verifyEmail"
    :hero-problem="isProblem"
    :icon="stateIcon"
    :busy="state === 'pending'"
    :tone="isProblem ? 'destructive' : 'primary'"
    :title="heading"
    :description="description"
    :description-testid="`verify-email-${state}`"
  >
    <div v-if="state !== 'pending'">
      <Button v-if="isAuthenticated" class="w-full" as-child data-testid="link-continue">
        <RouterLink :to="{ name: 'home' }">
          {{ t('auth.verifyEmail.actions.continue') }}
        </RouterLink>
      </Button>
      <Button v-else class="w-full" as-child data-testid="link-sign-in">
        <RouterLink :to="{ name: 'login' }">
          {{ t('auth.verifyEmail.actions.signIn') }}
        </RouterLink>
      </Button>
    </div>
  </AuthShell>
</template>
