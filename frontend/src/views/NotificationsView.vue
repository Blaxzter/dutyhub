<script setup lang="ts">
import { computed, onMounted } from 'vue'

import { CheckCheck, Settings, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { useNotificationStore } from '@/stores/notification'

import { useDialog } from '@/composables/useDialog'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

import NotificationList from '@/components/navigation/NotificationList.vue'

const { t } = useI18n()
const router = useRouter()
const notificationStore = useNotificationStore()
const { confirmDestructive } = useDialog()

const hasUnread = computed(() => notificationStore.hasUnread)
const hasAny = computed(() => notificationStore.notifications.length > 0)

async function handleMarkAllAsRead() {
  await notificationStore.markAllAsRead()
}

async function handleDismissAll() {
  const confirmed = await confirmDestructive({
    title: t('notifications.deleteAllTitle'),
    text: t('notifications.deleteAllConfirm'),
  })
  if (!confirmed) return
  try {
    await notificationStore.dismissAllNotifications()
    toast.success(t('notifications.deletedAll'))
  } catch {
    toast.error(t('notifications.deleteAllFailed'))
  }
}

function goToPreferences() {
  router.push({ name: 'notification-preferences' })
}

onMounted(() => {
  notificationStore.fetchNotifications({ limit: 20 })
})
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-4">
    <div class="flex flex-wrap items-start justify-between gap-3 pb-2">
      <h1 data-testid="page-heading" class="text-2xl sm:text-3xl font-bold tracking-tight">
        {{ t('notifications.title') }}
      </h1>
      <div class="flex flex-wrap items-center gap-2">
        <Button
          v-if="hasUnread"
          variant="outline"
          size="sm"
          :title="t('notifications.markAllRead')"
          :aria-label="t('notifications.markAllRead')"
          @click="handleMarkAllAsRead"
        >
          <CheckCheck class="h-4 w-4 sm:mr-2" />
          <span class="hidden sm:inline">{{ t('notifications.markAllRead') }}</span>
        </Button>
        <Button
          v-if="hasAny"
          variant="outline"
          size="sm"
          :title="t('notifications.deleteAll')"
          :aria-label="t('notifications.deleteAll')"
          @click="handleDismissAll"
        >
          <Trash2 class="h-4 w-4 sm:mr-2" />
          <span class="hidden sm:inline">{{ t('notifications.deleteAll') }}</span>
        </Button>
        <Button
          variant="outline"
          size="sm"
          :title="t('notifications.managePreferences')"
          :aria-label="t('notifications.managePreferences')"
          @click="goToPreferences"
        >
          <Settings class="h-4 w-4 sm:mr-2" />
          <span class="hidden sm:inline">{{ t('notifications.managePreferences') }}</span>
        </Button>
      </div>
    </div>

    <Card class="overflow-hidden">
      <NotificationList />
    </Card>
  </div>
</template>
