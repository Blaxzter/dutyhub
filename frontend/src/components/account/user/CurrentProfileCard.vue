<script setup lang="ts">
/**
 * The account as it stands, read-only.
 *
 * The "signed in with Auth0 / Google / GitHub" badge is gone with the provider
 * it described — there is one way in now, and naming it would tell nobody
 * anything. Its place goes to the one piece of account state a person can still
 * act on from here: an unconfirmed email address, with the button that sends a
 * fresh link. The verify-email copy promises exactly that ("ask for a new one
 * from your profile"), and this is the profile it means.
 */
import { computed, ref } from 'vue'

import { LoaderIcon, MailCheckIcon, UserIcon } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import { useAuthStore } from '@/stores/auth'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { useAvatarUrl } from '@/composables/useAvatarUrl'

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'

import { toastApiError } from '@/lib/api-errors'
import type { AuthUser } from '@/lib/auth-session'

interface Props {
  user: AuthUser | undefined
}

const props = defineProps<Props>()
const { t } = useI18n()
const authStore = useAuthStore()
const { post } = useAuthenticatedClient()

// Avatar bytes are served by our backend; the etag lives on UserProfile.
const avatarUrl = useAvatarUrl(() => authStore.profile)

const resending = ref(false)

// Computed properties
const displayName = computed(
  () => props.user?.name || props.user?.nickname || props.user?.email || 'User',
)

const initials = computed(() => {
  if (props.user?.name) {
    return props.user.name
      .split(' ')
      .map((n: string) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }
  if (props.user?.email) {
    return props.user.email[0].toUpperCase()
  }
  return 'U'
})

/**
 * Ask for another confirmation link.
 *
 * The endpoint answers 202 whatever happens, so the message is about what we
 * sent rather than about what arrived; a rate limit is the one thing that comes
 * back as an error, and `toastApiError` already has the words for it.
 */
const resendVerification = async () => {
  resending.value = true
  try {
    await post<void>({ url: '/auth/resend-verification' })
    toast.success(
      t('user.settings.profile.current.messages.verificationSent', {
        email: props.user?.email ?? '',
      }),
    )
  } catch (error) {
    toastApiError(error)
  } finally {
    resending.value = false
  }
}
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <UserIcon class="h-5 w-5" />
        {{ t('user.settings.profile.current.title') }}
      </CardTitle>
      <CardDescription>{{ t('user.settings.profile.current.subtitle') }}</CardDescription>
    </CardHeader>
    <CardContent>
      <div class="flex items-start gap-6">
        <!-- Avatar -->
        <div class="flex flex-col items-center gap-4">
          <Avatar class="h-24 w-24">
            <AvatarImage v-if="avatarUrl" :src="avatarUrl" :alt="displayName" />
            <AvatarFallback class="text-xl">
              {{ initials }}
            </AvatarFallback>
          </Avatar>
        </div>

        <!-- User Info -->
        <div class="flex-1 grid gap-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label class="text-sm font-medium text-muted-foreground">{{
                t('user.settings.profile.current.fields.name')
              }}</Label>
              <p class="text-sm">
                {{ user?.name || t('user.settings.profile.current.fields.notProvided') }}
              </p>
            </div>
            <div>
              <div class="flex items-center gap-2">
                <Label class="text-sm font-medium text-muted-foreground">{{
                  t('user.settings.profile.current.fields.email')
                }}</Label>
                <Badge :variant="user?.email_verified ? 'outline' : 'secondary'">
                  {{
                    user?.email_verified
                      ? t('user.settings.profile.current.fields.verified')
                      : t('user.settings.profile.current.fields.unverified')
                  }}
                </Badge>
              </div>
              <p class="text-sm">
                {{ user?.email || t('user.settings.profile.current.fields.notProvided') }}
              </p>
              <Button
                v-if="user?.email && !user.email_verified"
                variant="link"
                size="sm"
                class="mt-1 h-auto p-0"
                :disabled="resending"
                data-testid="btn-resend-verification"
                @click="resendVerification"
              >
                <LoaderIcon v-if="resending" class="h-3 w-3 animate-spin" />
                <MailCheckIcon v-else class="h-3 w-3" />
                {{
                  resending
                    ? t('user.settings.profile.current.actions.resendingVerification')
                    : t('user.settings.profile.current.actions.resendVerification')
                }}
              </Button>
            </div>
            <div>
              <Label class="text-sm font-medium text-muted-foreground">{{
                t('user.settings.profile.current.fields.nickname')
              }}</Label>
              <p class="text-sm">
                {{ user?.nickname || t('user.settings.profile.current.fields.notProvided') }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>
