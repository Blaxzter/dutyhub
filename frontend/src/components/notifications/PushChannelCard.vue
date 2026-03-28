<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import { useNotificationStore } from '@/stores/notification'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'

import AnimatedSend from '@/components/icons/lucide-animated/Send.vue'
import AnimatedSmartphone from '@/components/icons/lucide-animated/Smartphone.vue'

defineProps<{
  enabled: boolean
}>()

const emit = defineEmits<{
  toggle: [value: boolean]
}>()

const { t } = useI18n()
const notificationStore = useNotificationStore()

const iconRef = ref<InstanceType<typeof AnimatedSmartphone>>()
const pushSupported = ref(false)
const pushPermission = ref<NotificationPermission>('default')
const pushActive = ref(false)
const sendingTestPush = ref(false)
const disablingPush = ref(false)

function handleToggle(value: boolean) {
  emit('toggle', value)
  if (value) iconRef.value?.startAnimation()
}

async function sendTestPush() {
  sendingTestPush.value = true
  try {
    if (pushPermission.value !== 'granted') {
      await requestPushPermission()
    }
    if (pushPermission.value !== 'granted') return

    let success = await notificationStore.sendTestPush()
    if (!success) {
      await requestPushPermission()
      success = await notificationStore.sendTestPush()
    }

    if (success) {
      toast.success(t('notifications.push.testSuccess'))
    } else {
      toast.error(t('notifications.push.testError'))
    }
  } catch {
    toast.error(t('notifications.push.testError'))
  } finally {
    sendingTestPush.value = false
  }
}

async function requestPushPermission() {
  try {
    const permission = await Notification.requestPermission()
    pushPermission.value = permission

    if (permission === 'granted') {
      const vapidKey = await notificationStore.fetchVapidPublicKey()
      if (!vapidKey) {
        toast.error(t('notifications.push.notConfigured'))
        return
      }

      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidKey),
      })

      await notificationStore.registerPushSubscription(subscription)
      pushActive.value = true
      toast.success(t('notifications.push.enabled'))
    }
  } catch (error) {
    console.error('Push registration failed:', error)
    toast.error(t('notifications.push.failed'))
  }
}

async function disablePush() {
  disablingPush.value = true
  try {
    const registration = await navigator.serviceWorker.ready
    const subscription = await registration.pushManager.getSubscription()
    if (subscription) {
      await subscription.unsubscribe()
    }

    const subs = await notificationStore.fetchPushSubscriptions()
    for (const sub of subs) {
      await notificationStore.removePushSubscription(sub.id)
    }

    pushActive.value = false
    toast.success(t('notifications.push.disabled'))
  } catch (error) {
    console.error('Failed to disable push:', error)
    toast.error(t('notifications.push.disableFailed'))
  } finally {
    disablingPush.value = false
  }
}

function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

onMounted(async () => {
  pushSupported.value = 'serviceWorker' in navigator && 'PushManager' in window
  if (pushSupported.value) {
    pushPermission.value = Notification.permission
    if (pushPermission.value === 'granted') {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      pushActive.value = !!subscription
    }
  }
})

defineExpose({ pushSupported })
</script>

<template>
  <Card
    v-if="pushSupported"
    :class="[
      'transition-colors duration-300',
      enabled
        ? 'border-violet-200 bg-violet-50/50 dark:border-violet-900 dark:bg-violet-950/20'
        : '',
    ]"
  >
    <CardHeader>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <AnimatedSmartphone
            ref="iconRef"
            :size="20"
            :class="[
              'transition-colors duration-300',
              enabled ? 'text-violet-600 dark:text-violet-400' : 'text-muted-foreground',
            ]"
          />
          <CardTitle>{{ t('notifications.push.title') }}</CardTitle>
        </div>
        <Switch
          :model-value="enabled"
          @update:model-value="handleToggle"
        />
      </div>
      <CardDescription>
        {{ t('notifications.push.description') }}
      </CardDescription>
    </CardHeader>
    <CardContent class="space-y-3">
      <div v-if="pushPermission === 'denied'" class="text-muted-foreground text-sm">
        {{ t('notifications.push.denied') }}
      </div>
      <template v-else-if="pushActive">
        <div class="flex items-center gap-2">
          <Badge variant="outline" class="text-green-600">
            {{ t('notifications.push.enabled') }}
          </Badge>
        </div>
        <div class="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            :disabled="sendingTestPush"
            @click="sendTestPush"
          >
            <AnimatedSend :size="16" class="mr-2" />
            {{
              sendingTestPush
                ? t('notifications.push.testSending')
                : t('notifications.push.testButton')
            }}
          </Button>
          <Button
            variant="outline"
            size="sm"
            :disabled="disablingPush"
            @click="disablePush"
          >
            {{ t('notifications.push.disable') }}
          </Button>
        </div>
      </template>
      <Button v-else variant="outline" @click="requestPushPermission">
        {{ t('notifications.push.enable') }}
      </Button>
    </CardContent>
  </Card>
</template>
