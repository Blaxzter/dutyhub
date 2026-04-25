<script setup lang="ts">
import { type Component, computed, onMounted } from 'vue'

import { Bell, CalendarCheck, CalendarDays, ChartColumn, Users } from '@respeak/lucide-motion-vue'
import { useColorMode } from '@vueuse/core'
import { BookCheck, CalendarRange, Database, House } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import logoIcon from '@/assets/logo/logo.svg'
import wirksamDarkLogo from '@/assets/logo/wirksam-dark.svg'
import wirksamLightLogo from '@/assets/logo/wirksam-light.svg'

import { useAuthStore } from '@/stores/auth'
import { useNotificationStore } from '@/stores/notification'
import { useSidebarStore } from '@/stores/sidebar'

import { useChangelogStatus } from '@/composables/useChangelogStatus'

import type { SidebarProps } from '@/components/ui/sidebar'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from '@/components/ui/sidebar'

import NavMain from '@/components/navigation/NavMain.vue'
import type { NavSubItem } from '@/components/navigation/NavMain.vue'
import NavUser from '@/components/navigation/NavUser.vue'

interface AppSidebarProps extends SidebarProps {
  open?: boolean
}

const props = withDefaults(defineProps<AppSidebarProps>(), {
  collapsible: 'icon',
  open: true,
})

const { t } = useI18n()
const authStore = useAuthStore()
const sidebarStore = useSidebarStore()
const notificationStore = useNotificationStore()

const notificationDisplayCount = computed(() => {
  if (notificationStore.unreadCount > 99) return '99+'
  return notificationStore.unreadCount.toString()
})
const { isMobile, setOpenMobile, state } = useSidebar()
const router = useRouter()
const route = useRoute()
const mode = useColorMode()
const currentLogo = computed(() => (mode.value === 'light' ? wirksamDarkLogo : wirksamLightLogo))
const appVersion = __APP_VERSION__
const { hasNewVersions } = useChangelogStatus()

onMounted(() => {
  sidebarStore.fetch()
})

router.afterEach(() => {
  if (isMobile.value) {
    setOpenMobile(false)
  }
})

/**
 * Compute urgency badge variant for a task based on its next open shift.
 * - Within 15 min → destructive (red)
 * - Today → default (primary)
 * - Otherwise → secondary (neutral)
 */
function statusBadge(status: string): NavSubItem['badge'] {
  return {
    text: t(`duties.tasks.statuses.${status}`),
    tooltip: t('navigation.sidebar.badges.managersOnly'),
    variant: 'secondary',
  }
}

function eventBadge(
  openShifts: number,
  nextDate: string | null,
  nextTime: string | null,
): NavSubItem['badge'] | undefined {
  if (openShifts <= 0) return undefined

  const label = `${openShifts}`
  const tooltip = t('navigation.sidebar.badges.openShifts', { count: openShifts })
  if (!nextDate) return { text: label, tooltip, variant: 'outline' }

  const now = new Date()
  const slotDateTime = nextTime
    ? new Date(`${nextDate}T${nextTime}`)
    : new Date(`${nextDate}T23:59:59`)

  const diffMs = slotDateTime.getTime() - now.getTime()
  const diffMin = diffMs / 60_000

  if (diffMin <= 15 && diffMin > -60) return { text: label, tooltip, variant: 'destructive' }
  return { text: label, tooltip, variant: 'outline' }
}

function formatBookingTitle(slotDate: string, slotTitle: string): string {
  const d = new Date(slotDate + 'T00:00:00')
  const formatted = d.toLocaleDateString(undefined, {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
  })
  return `${formatted} — ${slotTitle}`
}

const navMain = computed(() => {
  const eventItems: NavSubItem[] = sidebarStore.tasks.map((e) => ({
    title: e.name,
    routeName: 'task-detail',
    routeParams: { eventId: e.id },
    badge:
      e.status && e.status !== 'published'
        ? statusBadge(e.status)
        : eventBadge(e.open_shifts, e.next_shift_date ?? null, e.next_shift_start_time ?? null),
  }))

  const bookingItems: NavSubItem[] = sidebarStore.bookings.map((b) => ({
    title: formatBookingTitle(b.slot_date, b.slot_title),
    routeName: 'task-detail',
    routeParams: { eventId: b.task_id },
  }))

  return [
    {
      title: 'Tasks',
      titleKey: 'navigation.sidebar.items.tasks.label',
      icon: CalendarDays,
      routeName: 'tasks',
      isActive: eventItems.length > 0,
      items: eventItems,
    },
    {
      title: 'My Bookings',
      titleKey: 'navigation.sidebar.items.myBookings.label',
      icon: BookCheck,
      routeName: 'my-bookings',
      isActive: bookingItems.length > 0,
      items: bookingItems,
    },
    {
      title: 'Availability',
      titleKey: 'navigation.sidebar.items.availability.label',
      icon: CalendarCheck,
      routeName: 'availability',
    },
  ]
})

const navManager = computed(() => {
  const items = []
  if (authStore.isManager) {
    items.push({
      title: 'Reports',
      titleKey: 'admin.reporting.title',
      icon: ChartColumn,
      animation: 'default-loop',
      routeName: 'reporting',
    })
  }
  return items
})

const navAdmin = computed(() => {
  const items: {
    title: string
    titleKey: string
    icon: Component
    routeName: string
  }[] = []
  if (authStore.isAdmin || authStore.isTaskManager) {
    items.push({
      title: 'Manage Events',
      titleKey: 'admin.events.title',
      icon: CalendarRange,
      routeName: 'admin-events',
    })
  }
  if (authStore.isAdmin) {
    items.push(
      {
        title: 'User Management',
        titleKey: 'admin.users.title',
        icon: Users,
        routeName: 'admin-users',
      },
      {
        title: 'Demo Data',
        titleKey: 'admin.demoData.title',
        icon: Database,
        routeName: 'admin-demo-data',
      },
    )
  }
  return items
})
</script>

<template>
  <Sidebar
    :side="props.side"
    :variant="props.variant"
    :collapsible="props.collapsible"
    :class="props.class"
  >
    <SidebarHeader>
      <RouterLink
        :to="{ name: 'home' }"
        class="flex items-center gap-2 px-2 py-3 hover:opacity-80 transition-opacity"
        :class="{ 'px-0!': state === 'collapsed' }"
      >
        <img v-if="state === 'collapsed'" :src="logoIcon" alt="WirkSam" class="size-8" />
        <img v-else :src="currentLogo" alt="WirkSam" class="w-auto" />
      </RouterLink>
    </SidebarHeader>
    <SidebarContent>
      <!-- Home link above the Platform section -->
      <SidebarMenu class="px-2 pt-1">
        <SidebarMenuItem>
          <SidebarMenuButton
            :tooltip="t('navigation.sidebar.items.home.label')"
            :is-active="route.name === 'home'"
            as-child
          >
            <RouterLink :to="{ name: 'home' }" data-testid="sidebar-link-home">
              <House />
              <span>{{ t('navigation.sidebar.items.home.label') }}</span>
              <span
                v-if="route.name === 'home'"
                class="ml-auto size-1.5 rounded-full bg-foreground"
              />
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem>
          <SidebarMenuButton
            :tooltip="t('notifications.title')"
            :is-active="route.name === 'notifications'"
            as-child
          >
            <RouterLink :to="{ name: 'notifications' }" data-testid="sidebar-link-notifications">
              <Bell animateOnHover triggerTarget="parent" />
              <span>{{ t('notifications.title') }}</span>
              <span
                v-if="notificationStore.hasUnread"
                class="ml-auto flex h-4 min-w-4 items-center justify-center rounded-full bg-red-700 px-1 text-[10px] font-bold text-white"
              >
                {{ notificationDisplayCount }}
              </span>
              <span
                v-else-if="route.name === 'notifications'"
                class="ml-auto size-1.5 rounded-full bg-foreground"
              />
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
      <NavMain :items="navMain" :open="props.open" />
    </SidebarContent>
    <NavMain
      v-if="navManager.length > 0"
      :items="navManager"
      :open="props.open"
      event-label-key="navigation.sidebar.items.management.label"
      class="shrink-0 px-2 pb-2"
    />
    <NavMain
      v-if="navAdmin.length > 0"
      :items="navAdmin"
      :open="props.open"
      event-label-key="admin.sidebar.section"
      class="shrink-0 px-2 pb-2"
    />
    <SidebarFooter class="flex flex-col gap-1 p-2 pb-1">
      <NavUser />
      <RouterLink
        :to="{ name: 'changelog' }"
        data-testid="sidebar-version-link"
        class="inline-flex items-center justify-center gap-1 w-full text-[10px] text-muted-foreground/50 hover:text-muted-foreground transition-colors pb-1 event-data-[collapsible=icon]:hidden"
      >
        <span>WirkSam {{ appVersion }}</span>
        <span v-if="hasNewVersions" class="size-1.5 rounded-full bg-primary" />
      </RouterLink>
    </SidebarFooter>
    <SidebarRail />
  </Sidebar>
</template>
