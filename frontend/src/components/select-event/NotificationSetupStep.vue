<script setup lang="ts">
import { computed, onMounted } from 'vue'

import { ArrowRight } from '@respeak/lucide-motion-vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import { useNotificationStore } from '@/stores/notification'

import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import Input from '@/components/ui/input/Input.vue'
import Label from '@/components/ui/label/Label.vue'
import { Switch } from '@/components/ui/switch'

import AnimatedMail from '@/components/icons/lucide-animated/Mail.vue'
import PushChannelCard from '@/components/notifications/PushChannelCard.vue'
import TelegramChannelCard from '@/components/notifications/TelegramChannelCard.vue'

const props = defineProps<{
  phoneNumber: string
  savingPhone: boolean
}>()

const emit = defineEmits<{
  'update:phoneNumber': [value: string]
  back: []
  finish: []
}>()

const { t } = useI18n()
const notificationStore = useNotificationStore()

const globalChannelSettings = computed(() => notificationStore.globalChannelSettings)

const phone = computed({
  get: () => props.phoneNumber,
  set: (v: string) => emit('update:phoneNumber', v),
})

async function toggleChannel(
  field: 'notify_email' | 'notify_push' | 'notify_telegram',
  enabled: boolean,
) {
  try {
    await notificationStore.updateGlobalChannelSettings({ [field]: enabled })
  } catch {
    toast.error(t('notifications.preferences.saveFailed'))
  }
}

onMounted(() => {
  void notificationStore.fetchGlobalChannelSettings()
  void notificationStore.fetchTelegramBinding()
  void notificationStore.fetchTelegramConfig()
})
</script>

<template>
  <div class="space-y-4">
    <Card data-testid="channel-email">
      <CardHeader>
        <div class="flex items-center justify-between gap-4">
          <div class="flex items-center gap-2">
            <AnimatedMail :size="20" />
            <CardTitle>{{ t('notifications.email.title') }}</CardTitle>
          </div>
          <Switch
            :model-value="globalChannelSettings.notify_email"
            @update:model-value="(v: boolean) => toggleChannel('notify_email', v)"
          />
        </div>
        <CardDescription>{{ t('notifications.email.description') }}</CardDescription>
      </CardHeader>
    </Card>

    <PushChannelCard
      data-testid="channel-push"
      :enabled="globalChannelSettings.notify_push"
      @toggle="(v) => toggleChannel('notify_push', v)"
    />

    <TelegramChannelCard
      data-testid="channel-telegram"
      :enabled="globalChannelSettings.notify_telegram"
      @toggle="(v) => toggleChannel('notify_telegram', v)"
    />

    <Card>
      <CardHeader>
        <CardTitle>{{ t('duties.selectEvent.notifications.phoneTitle') }}</CardTitle>
        <CardDescription>
          {{ t('duties.selectEvent.notifications.phoneHint') }}
        </CardDescription>
      </CardHeader>
      <CardContent class="space-y-2">
        <Label for="phone-onboard">
          {{ t('duties.selectEvent.notifications.phoneLabel') }}
        </Label>
        <Input
          id="phone-onboard"
          v-model="phone"
          :placeholder="t('duties.selectEvent.notifications.phonePlaceholder')"
          data-testid="input-phone"
        />
      </CardContent>
    </Card>
  </div>

  <div class="flex justify-between gap-2">
    <Button variant="outline" @click="$emit('back')">
      {{ t('common.actions.back') }}
    </Button>
    <Button
      data-testid="btn-finish-onboarding"
      :disabled="props.savingPhone"
      @click="$emit('finish')"
    >
      {{ t('duties.selectEvent.notifications.finish') }}
      <ArrowRight class="ml-2 h-4 w-4" animateOnHover triggerTarget="parent" />
    </Button>
  </div>
</template>
