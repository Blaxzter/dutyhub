<script setup lang="ts">
import { computed } from 'vue'

import { Bell, BookCheck, CalendarDays } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'

import { useNotificationStore } from '@/stores/notification'

const { t } = useI18n()
const route = useRoute()
const notificationStore = useNotificationStore()

const EVENT_ROUTES = new Set([
  'events',
  'event-create',
  'event-edit',
  'event-detail',
  'event-add-slots',
])
const BOOKING_ROUTES = new Set(['my-bookings', 'booking-detail'])
const INBOX_ROUTES = new Set(['notifications'])

const activeTab = computed<'events' | 'bookings' | 'inbox' | null>(() => {
  const name = typeof route.name === 'string' ? route.name : ''
  if (EVENT_ROUTES.has(name)) return 'events'
  if (BOOKING_ROUTES.has(name)) return 'bookings'
  if (INBOX_ROUTES.has(name)) return 'inbox'
  return null
})

const notificationDisplayCount = computed(() => {
  if (notificationStore.unreadCount > 99) return '99+'
  return notificationStore.unreadCount.toString()
})
</script>

<template>
  <nav
    data-testid="mobile-bottom-nav"
    class="fixed inset-x-0 bottom-0 z-40 flex items-stretch border-t bg-background pb-[env(safe-area-inset-bottom)] md:hidden"
  >
    <RouterLink
      :to="{ name: 'events' }"
      data-testid="mobile-nav-events"
      class="flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-xs"
      :class="
        activeTab === 'events' ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
      "
    >
      <CalendarDays class="size-5" />
      <span>{{ t('navigation.mobileBottomNav.events') }}</span>
    </RouterLink>

    <RouterLink
      :to="{ name: 'my-bookings' }"
      data-testid="mobile-nav-bookings"
      class="flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-xs"
      :class="
        activeTab === 'bookings' ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
      "
    >
      <BookCheck class="size-5" />
      <span>{{ t('navigation.mobileBottomNav.bookings') }}</span>
    </RouterLink>

    <RouterLink
      :to="{ name: 'notifications' }"
      data-testid="mobile-nav-inbox"
      class="relative flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-xs"
      :class="
        activeTab === 'inbox' ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
      "
    >
      <div class="relative">
        <Bell class="size-5" />
        <span
          v-if="notificationStore.hasUnread"
          class="absolute -top-1 -right-2 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-700 px-1 text-[10px] font-bold text-white"
        >
          {{ notificationDisplayCount }}
        </span>
      </div>
      <span>{{ t('navigation.mobileBottomNav.inbox') }}</span>
    </RouterLink>
  </nav>
</template>
