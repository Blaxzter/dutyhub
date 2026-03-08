<script setup lang="ts">
import { computed } from 'vue'

import { BookCheck, CalendarDays, CalendarRange, House, Users } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import dutyhubLogo from '@/assets/logo/dutyhub.svg'

import { useAuthStore } from '@/stores/auth'

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
} from '@/components/ui/sidebar'

import NavMain from '@/components/navigation/NavMain.vue'
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

const navMain = [
  {
    title: 'Event Groups',
    titleKey: 'navigation.sidebar.items.eventGroups.label',
    icon: CalendarRange,
    routeName: 'event-groups',
  },
  {
    title: 'Events',
    titleKey: 'navigation.sidebar.items.events.label',
    icon: CalendarDays,
    routeName: 'events',
  },
  {
    title: 'My Bookings',
    titleKey: 'navigation.sidebar.items.myBookings.label',
    icon: BookCheck,
    routeName: 'my-bookings',
  },
]

const navAdmin = computed(() =>
  authStore.isAdmin
    ? [
        {
          title: 'User Management',
          titleKey: 'admin.users.title',
          icon: Users,
          routeName: 'admin-users',
        },
      ]
    : [],
)
</script>

<template>
  <Sidebar v-bind="props">
    <SidebarHeader>
      <RouterLink
        :to="{ name: 'home' }"
        class="flex items-center gap-2 px-2 py-3 hover:opacity-80 transition-opacity"
      >
        <img :src="dutyhubLogo" alt="DutyHub" class="w-auto" />
      </RouterLink>
    </SidebarHeader>
    <SidebarContent>
      <!-- Home link above the Platform section -->
      <SidebarMenu class="px-2 pt-1">
        <SidebarMenuItem>
          <SidebarMenuButton :tooltip="t('navigation.sidebar.items.home.label')" as-child>
            <RouterLink :to="{ name: 'home' }">
              <House />
              <span>{{ t('navigation.sidebar.items.home.label') }}</span>
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
      <NavMain :items="navMain" :open="props.open" />
      <NavMain
        v-if="navAdmin.length > 0"
        :items="navAdmin"
        :open="props.open"
        group-label-key="admin.sidebar.section"
      />
    </SidebarContent>
    <SidebarFooter>
      <NavUser />
    </SidebarFooter>
    <SidebarRail />
  </Sidebar>
</template>
