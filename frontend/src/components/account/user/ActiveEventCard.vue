<script setup lang="ts">
import { ref } from 'vue'

import { CalendarRange } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import Switch from '@/components/ui/switch/Switch.vue'

import EventSwitcherMenu from '@/components/navigation/EventSwitcherMenu.vue'

const { t } = useI18n()
const authStore = useAuthStore()
const { patch } = useAuthenticatedClient()

const togglePending = ref(false)

async function toggleSidebarSwitcher(value: boolean) {
  if (!authStore.profile) return
  const previous = authStore.profile.show_event_switcher_in_nav
  authStore.profile.show_event_switcher_in_nav = value
  togglePending.value = true
  try {
    await patch({ url: '/users/me', body: { show_event_switcher_in_nav: value } })
  } catch {
    authStore.profile.show_event_switcher_in_nav = previous
    toast.error(t('user.settings.activeEvent.toggleError'))
  } finally {
    togglePending.value = false
  }
}
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <CalendarRange class="h-5 w-5" />
        {{ t('user.settings.activeEvent.title') }}
      </CardTitle>
      <CardDescription>
        {{ t('user.settings.activeEvent.description') }}
      </CardDescription>
    </CardHeader>
    <CardContent class="space-y-6">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="min-w-0 space-y-1">
          <p class="text-sm font-medium">{{ t('user.settings.activeEvent.currentLabel') }}</p>
          <p
            v-if="authStore.selectedEvent"
            class="truncate text-sm text-muted-foreground"
            data-testid="settings-active-event-name"
          >
            {{ authStore.selectedEvent.name }}
          </p>
          <p v-else class="text-sm text-muted-foreground">
            {{ t('user.settings.activeEvent.none') }}
          </p>
        </div>
        <EventSwitcherMenu>
          <template #default>
            <Button variant="outline" size="sm" data-testid="settings-active-event-change">
              {{ t('user.settings.activeEvent.change') }}
            </Button>
          </template>
        </EventSwitcherMenu>
      </div>

      <div class="flex items-start justify-between gap-4 rounded-md border bg-muted/30 p-3">
        <div class="space-y-1">
          <p class="text-sm font-medium">
            {{ t('user.settings.activeEvent.sidebarToggle.label') }}
          </p>
          <p class="text-sm text-muted-foreground">
            {{ t('user.settings.activeEvent.sidebarToggle.description') }}
          </p>
        </div>
        <Switch
          :model-value="authStore.profile?.show_event_switcher_in_nav ?? false"
          :disabled="togglePending"
          data-testid="settings-active-event-sidebar-toggle"
          @update:model-value="(v: boolean) => toggleSidebarSwitcher(v)"
        />
      </div>
    </CardContent>
  </Card>
</template>
