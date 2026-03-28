<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'

import { ExternalLink, TriangleAlert } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import { useNotificationStore } from '@/stores/notification'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'

import TelegramLoginWidget from '@/components/account/TelegramLoginWidget.vue'
import AnimatedTelegram from '@/components/icons/lucide-animated/Telegram.vue'

defineProps<{
  enabled: boolean
}>()

const emit = defineEmits<{
  toggle: [value: boolean]
}>()

const { t } = useI18n()
const notificationStore = useNotificationStore()

const iconRef = ref<InstanceType<typeof AnimatedTelegram>>()
const connectingTelegram = ref(false)

const telegramBinding = computed(() => notificationStore.telegramBinding)
const telegramBotUsername = computed(() => notificationStore.telegramBotUsername)
const telegramConfigured = computed(() => notificationStore.telegramConfigured)

const showWarning = computed(() => {
  if (telegramBinding.value?.is_verified) return false
  return notificationStore.globalChannelSettings.notify_telegram
})

// Manual code fallback
const telegramCode = ref<string | null>(null)
const manualBotUsername = ref<string | null>(null)
const bindingTelegram = ref(false)
let telegramPollTimer: ReturnType<typeof setInterval> | null = null

const telegramDeepLink = computed(() => {
  if (!telegramCode.value || !manualBotUsername.value) return null
  return `https://t.me/${manualBotUsername.value}?start=${telegramCode.value}`
})

const botStartLink = computed(() => {
  if (!telegramBotUsername.value) return null
  return `https://t.me/${telegramBotUsername.value}`
})

function handleToggle(value: boolean) {
  emit('toggle', value)
  if (value) iconRef.value?.startAnimation()
}

async function onTelegramAuth(data: {
  id: number
  first_name?: string
  last_name?: string
  username?: string
  photo_url?: string
  auth_date: number
  hash: string
}) {
  connectingTelegram.value = true
  try {
    await notificationStore.loginWithTelegram(data)
    toast.success(t('notifications.telegram.connected'))
  } catch {
    toast.error(t('notifications.telegram.authFailed'))
  } finally {
    connectingTelegram.value = false
  }
}

function startTelegramPolling() {
  stopTelegramPolling()
  telegramPollTimer = setInterval(async () => {
    await notificationStore.fetchTelegramBinding()
    if (telegramBinding.value?.is_verified) {
      stopTelegramPolling()
      telegramCode.value = null
      toast.success(t('notifications.telegram.connected'))
    }
  }, 3000)
}

function stopTelegramPolling() {
  if (telegramPollTimer) {
    clearInterval(telegramPollTimer)
    telegramPollTimer = null
  }
}

async function startManualTelegramBinding() {
  bindingTelegram.value = true
  try {
    const result = await notificationStore.startTelegramBinding()
    telegramCode.value = result.verification_code
    manualBotUsername.value = result.bot_username
    startTelegramPolling()
  } catch {
    toast.error(t('notifications.telegram.bindFailed'))
  } finally {
    bindingTelegram.value = false
  }
}

async function unbindTelegram() {
  try {
    await notificationStore.unbindTelegram()
    telegramCode.value = null
    stopTelegramPolling()
    toast.success(t('notifications.telegram.unbound'))
  } catch {
    toast.error(t('notifications.telegram.unbindFailed'))
  }
}

onUnmounted(() => stopTelegramPolling())
</script>

<template>
  <Card
    v-if="telegramConfigured"
    :class="[
      'transition-colors duration-300',
      enabled
        ? 'border-sky-200 bg-sky-50/50 dark:border-sky-900 dark:bg-sky-950/20'
        : '',
    ]"
  >
    <CardHeader>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <AnimatedTelegram
            ref="iconRef"
            :size="20"
            :use-color="enabled"
            :class="[
              'transition-colors duration-300',
              enabled ? '' : 'text-muted-foreground',
            ]"
          />
          <CardTitle>{{ t('notifications.telegram.title') }}</CardTitle>
        </div>
        <Switch
          :model-value="enabled"
          @update:model-value="handleToggle"
        />
      </div>
      <CardDescription>
        {{ t('notifications.telegram.description') }}
      </CardDescription>
    </CardHeader>
    <CardContent>
      <!-- Warning: Telegram enabled but not connected -->
      <div
        v-if="showWarning && !telegramBinding?.is_verified"
        class="bg-amber-50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200 mb-4 flex items-start gap-2 rounded-lg border border-amber-200 dark:border-amber-800 p-3 text-sm"
      >
        <TriangleAlert class="mt-0.5 h-4 w-4 shrink-0" />
        <span>{{ t('notifications.telegram.notConnectedWarning') }}</span>
      </div>

      <!-- Connected state -->
      <div v-if="telegramBinding?.is_verified" class="space-y-3">
        <div class="flex items-center gap-2">
          <Badge variant="outline" class="text-green-600">
            {{ t('notifications.telegram.connected') }}
          </Badge>
          <span v-if="telegramBinding.telegram_username" class="text-muted-foreground text-sm">
            @{{ telegramBinding.telegram_username }}
          </span>
        </div>
        <p v-if="botStartLink" class="text-muted-foreground text-sm">
          {{ t('notifications.telegram.startBotHint') }}
          <a
            :href="botStartLink"
            target="_blank"
            rel="noopener noreferrer"
            class="text-primary underline underline-offset-2"
          >
            @{{ telegramBotUsername }}
          </a>
        </p>
        <Button variant="outline" size="sm" @click="unbindTelegram">
          {{ t('notifications.telegram.disconnect') }}
        </Button>
      </div>

      <!-- Not connected: show Login Widget or manual fallback -->
      <div v-else class="space-y-4">
        <div v-if="telegramBotUsername && !telegramCode">
          <p class="text-muted-foreground mb-3 text-sm">
            {{ t('notifications.telegram.loginDescription') }}
          </p>
          <TelegramLoginWidget :bot-username="telegramBotUsername" @auth="onTelegramAuth" />
          <div v-if="connectingTelegram" class="text-muted-foreground mt-2 text-sm">
            {{ t('notifications.telegram.connecting') }}
          </div>
        </div>

        <details class="text-sm">
          <summary class="text-muted-foreground cursor-pointer text-xs">
            {{ t('notifications.telegram.manualFallback') }}
          </summary>
          <div class="mt-3 space-y-3">
            <div v-if="telegramCode" class="space-y-3">
              <a
                v-if="telegramDeepLink"
                :href="telegramDeepLink"
                target="_blank"
                rel="noopener noreferrer"
                class="bg-primary text-primary-foreground hover:bg-primary/90 inline-flex items-center rounded-md px-4 py-2 text-sm font-medium"
              >
                <ExternalLink class="mr-2 h-4 w-4" />
                {{ t('notifications.telegram.openInTelegram') }}
              </a>
              <p class="text-muted-foreground text-sm">
                {{ t('notifications.telegram.waitingForVerification') }}
              </p>
              <div class="space-y-2">
                <p class="text-muted-foreground text-xs">
                  {{ t('notifications.telegram.sendCode') }}
                </p>
                <div class="bg-muted rounded-lg p-3 text-center">
                  <code class="text-sm font-bold">{{ telegramCode }}</code>
                </div>
                <p v-if="manualBotUsername" class="text-muted-foreground text-xs">
                  {{ t('notifications.telegram.sendTo') }}
                  <strong>@{{ manualBotUsername }}</strong>
                </p>
              </div>
            </div>
            <Button
              v-else
              variant="outline"
              size="sm"
              :disabled="bindingTelegram"
              @click="startManualTelegramBinding"
            >
              {{ t('notifications.telegram.connectManually') }}
            </Button>
          </div>
        </details>
      </div>
    </CardContent>
  </Card>
</template>
