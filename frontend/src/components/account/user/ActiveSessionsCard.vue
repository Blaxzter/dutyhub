<script setup lang="ts">
/**
 * Every device currently signed in as this account.
 *
 * The point of the list is recognition: someone scanning it should be able to
 * say "that phone is mine, that laptop in another country is not". So each row
 * leads with a readable device name derived from the user agent rather than the
 * raw string, and the device asking the question is labelled instead of being
 * offered a sign-out button that would blank the page underneath it.
 *
 * The server sorts newest first and flags the current row, so neither is
 * recomputed here.
 */
import { onMounted, ref } from 'vue'

import { LoaderIcon, LogOutIcon, MonitorSmartphoneIcon } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { useDialog } from '@/composables/useDialog'
import { useFormatters } from '@/composables/useFormatters'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

import type { AuthSessionRead } from '@/client/types.gen'
import { normalizeApiError, toastApiError } from '@/lib/api-errors'

/**
 * Enough of a user-agent reading to name a device, and no more.
 *
 * Order is load-bearing in both lists: every Chromium agent also claims Safari,
 * Edge also claims Chrome, and an iPad reports a Macintosh — so the more
 * specific pattern has to be tested first.
 */
const BROWSERS: ReadonlyArray<readonly [RegExp, string]> = [
  [/\bedg(?:e|a|ios)?\//i, 'Edge'],
  [/\bopr\/|\bopera/i, 'Opera'],
  [/\b(?:chrome|crios)\//i, 'Chrome'],
  [/\b(?:firefox|fxios)\//i, 'Firefox'],
  [/\bsafari\//i, 'Safari'],
]

const PLATFORMS: ReadonlyArray<readonly [RegExp, string]> = [
  [/\bwindows\b/i, 'Windows'],
  [/\b(?:iphone|ipad|ipod)\b/i, 'iOS'],
  [/\bandroid\b/i, 'Android'],
  [/\bmac os x\b|\bmacintosh\b/i, 'macOS'],
  [/\blinux\b/i, 'Linux'],
]

const { t } = useI18n()
const { get, delete: del } = useAuthenticatedClient()
const { confirmDestructive } = useDialog()
const { formatDateTime } = useFormatters()

const sessions = ref<AuthSessionRead[]>([])
const loading = ref(true)
/** Id of the row whose sign-out is in flight, so only that button spins. */
const revokingId = ref<string | null>(null)

/**
 * Timestamps arrive as naive UTC — no offset, by house convention.
 *
 * JavaScript reads an offset-less date-time as *local* time, which would shift
 * every "signed in at" by the viewer's own offset. Marking it as UTC before
 * parsing is the whole fix.
 */
function asUtcIso(value: string): string {
  return /(?:Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`
}

function formatMoment(value: string): string {
  return formatDateTime(asUtcIso(value), { year: 'numeric', month: 'short', day: 'numeric' })
}

/** "Chrome on Windows" — or as much of it as the agent string gives up. */
function describeDevice(userAgent: string | null | undefined): string {
  if (!userAgent) return t('user.settings.sessions.fields.unknownDevice')
  const browser = BROWSERS.find(([pattern]) => pattern.test(userAgent))?.[1]
  const platform = PLATFORMS.find(([pattern]) => pattern.test(userAgent))?.[1]
  if (browser && platform) {
    return t('user.settings.sessions.fields.deviceOn', { browser, platform })
  }
  return browser ?? platform ?? t('user.settings.sessions.fields.unknownDevice')
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const response = await get<{ data: AuthSessionRead[] }>({ url: '/auth/sessions' })
    sessions.value = response.data
  } catch (error) {
    toastApiError(error)
  } finally {
    loading.value = false
  }
}

async function revoke(session: AuthSessionRead): Promise<void> {
  const confirmed = await confirmDestructive({
    title: t('user.settings.sessions.confirm.title'),
    text: t('user.settings.sessions.confirm.text', { device: describeDevice(session.user_agent) }),
    confirmText: t('user.settings.sessions.actions.revoke'),
  })
  if (!confirmed) return

  revokingId.value = session.id
  try {
    await del({ url: `/auth/sessions/${session.id}` })
    toast.success(t('user.settings.sessions.messages.revoked'))
  } catch (error) {
    // `auth.session_not_found` means it was already gone — signed out from
    // somewhere else, or simply lapsed while this list sat on screen. The
    // outcome asked for is the outcome there is, so reloading says it all.
    if (normalizeApiError(error).code !== 'auth.session_not_found') toastApiError(error)
  } finally {
    revokingId.value = null
    await load()
  }
}

onMounted(load)
</script>

<template>
  <Card data-testid="active-sessions-card">
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <MonitorSmartphoneIcon class="h-5 w-5" />
        {{ t('user.settings.sessions.title') }}
      </CardTitle>
      <CardDescription>{{ t('user.settings.sessions.subtitle') }}</CardDescription>
    </CardHeader>
    <CardContent>
      <div v-if="loading" class="space-y-3" data-testid="sessions-loading">
        <Skeleton v-for="row in 2" :key="row" class="h-16 w-full" />
      </div>

      <p
        v-else-if="sessions.length === 0"
        class="text-sm text-muted-foreground"
        data-testid="sessions-empty"
      >
        {{ t('user.settings.sessions.empty') }}
      </p>

      <ul v-else class="divide-y" data-testid="sessions-list">
        <li
          v-for="session in sessions"
          :key="session.id"
          class="flex flex-wrap items-start justify-between gap-3 py-3 first:pt-0 last:pb-0"
          :data-testid="`session-${session.id}`"
        >
          <div class="min-w-0 space-y-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-sm font-medium">{{ describeDevice(session.user_agent) }}</span>
              <Badge v-if="session.is_current" variant="secondary" data-testid="session-current">
                {{ t('user.settings.sessions.fields.current') }}
              </Badge>
            </div>
            <p class="text-xs text-muted-foreground">
              {{
                t('user.settings.sessions.fields.signedIn', {
                  time: formatMoment(session.created_at),
                })
              }}
            </p>
            <p v-if="session.last_used_at" class="text-xs text-muted-foreground">
              {{
                t('user.settings.sessions.fields.lastUsed', {
                  time: formatMoment(session.last_used_at),
                })
              }}
            </p>
            <p v-if="session.ip_address" class="text-xs text-muted-foreground">
              {{ t('user.settings.sessions.fields.ipAddress', { ip: session.ip_address }) }}
            </p>
          </div>

          <Button
            v-if="!session.is_current"
            variant="outline"
            size="sm"
            :disabled="revokingId === session.id"
            :data-testid="`btn-revoke-session-${session.id}`"
            @click="revoke(session)"
          >
            <LoaderIcon v-if="revokingId === session.id" class="h-4 w-4 animate-spin" />
            <LogOutIcon v-else class="h-4 w-4" />
            {{
              revokingId === session.id
                ? t('user.settings.sessions.actions.revoking')
                : t('user.settings.sessions.actions.revoke')
            }}
          </Button>
        </li>
      </ul>
    </CardContent>
  </Card>
</template>
