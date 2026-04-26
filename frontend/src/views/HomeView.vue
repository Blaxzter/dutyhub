<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useLocalStorage } from '@vueuse/core'
import { BookCheck, CalendarDays, HelpCircle, SlidersHorizontal, Users } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import Label from '@/components/ui/label/Label.vue'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Switch } from '@/components/ui/switch'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

import ShiftDetailDialog from '@/components/tasks/ShiftDetailDialog.vue'
import { ShiftCalendar } from '@/components/tasks/shift-calendar'
import type { BookingCalendarItem } from '@/components/tasks/shift-calendar'

import type { DashboardTask, DashboardEvent, DashboardFeedResponse } from '@/client'
import { toastApiError } from '@/lib/api-errors'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

const { get } = useAuthenticatedClient()

const eventCount = ref(0)
const myBookingCount = ref(0)
const loading = ref(true)

const tasks = ref<DashboardTask[]>([])
const events = ref<DashboardEvent[]>([])
const bookings = ref<BookingCalendarItem[]>([])

// Shift detail dialog
const showShiftDetail = ref(false)
const detailShiftId = ref<string | null>(null)

// Map booking ID → shift ID for dialog
const bookingShiftMap = ref<Map<string, string>>(new Map())

const openBookingDetail = (calendarItem: BookingCalendarItem) => {
  const slotId = bookingShiftMap.value.get(calendarItem.id)
  if (!slotId) return
  detailShiftId.value = slotId
  showShiftDetail.value = true
}

const showTasks = useLocalStorage('wirksam-calendar-show-tasks', true)
const showGroups = useLocalStorage('wirksam-calendar-show-events', true)
const showBookings = useLocalStorage('wirksam-calendar-show-bookings', true)

const hiddenFilterCount = computed(
  () => [showTasks, showGroups, showBookings].filter((f) => !f.value).length,
)

async function loadStats() {
  loading.value = true
  try {
    const res = await get<{ data: DashboardFeedResponse }>({ url: '/dashboard/feed' })
    const feed = res.data

    tasks.value = feed.tasks
    eventCount.value = feed.task_count
    events.value = feed.events
    myBookingCount.value = feed.booking_count

    // Update pending user count for admin badge
    if (feed.pending_user_count != null) {
      authStore.pendingUserCount = feed.pending_user_count
    }

    // Map feed bookings to calendar items
    const newMap = new Map<string, string>()
    bookings.value = feed.bookings.map((b) => {
      newMap.set(b.id, b.slot_id)
      return {
        id: b.id,
        slotId: b.slot_id,
        date: b.date,
        title: b.title,
        startTime: b.start_time,
        endTime: b.end_time,
      }
    })
    bookingShiftMap.value = newMap
  } catch (error) {
    toastApiError(error)
  } finally {
    loading.value = false
  }
}

const navigateToTask = (task: { id: string }) => {
  router.push({ name: 'task-detail', params: { eventId: task.id } })
}

const navigateToEvent = (event: { id: string }) => {
  if (authStore.isAdmin || authStore.isTaskManager || authStore.canManageEvent(event.id)) {
    router.push({ name: 'event-settings', query: { eventId: event.id } })
  }
}

onMounted(loadStats)
</script>

<template>
  <div class="mx-auto max-w-7xl space-y-6">
    <div class="space-y-2">
      <h1 data-testid="page-heading" class="text-2xl sm:text-3xl font-bold">{{ t('dashboard.home.title') }}</h1>
      <p class="text-muted-foreground">
        {{ t('dashboard.home.subtitle') }}
      </p>
    </div>

    <!-- Stats Cards -->
    <div class="grid auto-rows-min gap-4 md:grid-cols-3">
      <Card
        data-testid="stat-card-tasks"
        class="cursor-pointer hover:shadow-md transition-shadow"
        @click="router.push({ name: 'tasks' })"
      >
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium">{{
            t('dashboard.home.stats.tasks.title')
          }}</CardTitle>
          <CalendarDays class="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold">{{ eventCount }}</div>
          <p class="text-xs text-muted-foreground">
            {{ t('dashboard.home.stats.tasks.description') }}
          </p>
        </CardContent>
      </Card>

      <Card
        data-testid="stat-card-bookings"
        class="cursor-pointer hover:shadow-md transition-shadow"
        @click="router.push({ name: 'my-bookings' })"
      >
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium">{{
            t('dashboard.home.stats.bookings.title')
          }}</CardTitle>
          <BookCheck class="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold">{{ myBookingCount }}</div>
          <p class="text-xs text-muted-foreground">
            {{ t('dashboard.home.stats.bookings.description') }}
          </p>
        </CardContent>
      </Card>

      <Card
        v-if="authStore.isManager"
        data-testid="stat-card-users"
        class="cursor-pointer hover:shadow-md transition-shadow"
        @click="router.push({ name: 'admin-users' })"
      >
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium">{{
            t('dashboard.home.stats.users.title')
          }}</CardTitle>
          <Users class="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold">{{ authStore.pendingUserCount }}</div>
          <p class="text-xs text-muted-foreground">
            {{ t('dashboard.home.stats.users.description') }}
          </p>
        </CardContent>
      </Card>
    </div>

    <!-- Calendar Section -->
    <div data-testid="dashboard-calendar" class="space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h2 class="text-xl font-semibold">{{ t('dashboard.home.calendar.title') }}</h2>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger as="span" class="inline-flex">
              <Popover>
                <PopoverTrigger as-child>
                  <Button
                    data-testid="btn-calendar-filter"
                    variant="outline"
                    size="sm"
                    class="relative"
                  >
                    <SlidersHorizontal class="mr-2 h-4 w-4" />
                    {{ t('dashboard.home.calendar.filter') }}
                    <span
                      v-if="hiddenFilterCount > 0"
                      class="absolute -right-1.5 -top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground"
                    >
                      {{ hiddenFilterCount }}
                    </span>
                  </Button>
                </PopoverTrigger>
                <PopoverContent align="end" class="w-56">
                  <div class="space-y-4">
                    <div class="flex items-center justify-between">
                      <Label for="filter-tasks">{{
                        t('dashboard.home.calendar.filters.tasks')
                      }}</Label>
                      <Switch id="filter-tasks" v-model="showTasks" />
                    </div>
                    <div class="flex items-center justify-between">
                      <Label for="filter-events">{{
                        t('dashboard.home.calendar.filters.events')
                      }}</Label>
                      <Switch id="filter-events" v-model="showGroups" />
                    </div>
                    <div class="flex items-center justify-between">
                      <Label for="filter-bookings">{{
                        t('dashboard.home.calendar.filters.bookings')
                      }}</Label>
                      <Switch id="filter-bookings" v-model="showBookings" />
                    </div>
                    <p
                      v-if="hiddenFilterCount > 0"
                      class="text-xs text-muted-foreground border-t pt-3"
                    >
                      {{
                        t(
                          'dashboard.home.calendar.hiddenCount',
                          { count: hiddenFilterCount },
                          hiddenFilterCount,
                        )
                      }}
                    </p>
                  </div>
                </PopoverContent>
              </Popover>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <p v-if="hiddenFilterCount > 0">
                {{
                  t(
                    'dashboard.home.calendar.filterTooltip',
                    { count: hiddenFilterCount },
                    hiddenFilterCount,
                  )
                }}
              </p>
              <p v-else>
                {{ t('dashboard.home.calendar.filterTooltipNone') }}
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      <div v-if="loading" class="py-12 text-center text-muted-foreground">
        {{ t('common.states.loading') }}
      </div>
      <ShiftCalendar
        v-else
        :tasks="tasks"
        :events="events"
        :bookings="bookings"
        :show-tasks="showTasks"
        :show-events="showGroups"
        :show-bookings="showBookings"
        @navigate-task="navigateToTask"
        @navigate-event="navigateToEvent"
        @navigate-booking="openBookingDetail"
      />
    </div>

    <!-- Quick Actions -->
    <div data-testid="dashboard-quick-actions" class="rounded-xl bg-muted/50 p-6">
      <h2 class="text-xl font-semibold mb-4">{{ t('dashboard.home.quickActions.title') }}</h2>
      <div class="flex flex-wrap gap-3">
        <Button
          data-testid="btn-browse-tasks"
          variant="outline"
          @click="router.push({ name: 'tasks' })"
        >
          <CalendarDays class="mr-2 h-4 w-4" />
          {{ t('dashboard.home.quickActions.browseTasks') }}
        </Button>
        <Button
          data-testid="btn-my-bookings"
          variant="outline"
          @click="router.push({ name: 'my-bookings' })"
        >
          <BookCheck class="mr-2 h-4 w-4" />
          {{ t('dashboard.home.quickActions.myBookings') }}
        </Button>
        <Button variant="outline" @click="router.push({ name: 'how-it-works' })">
          <HelpCircle class="mr-2 h-4 w-4" />
          {{ t('dashboard.home.quickActions.howItWorks') }}
        </Button>
      </div>
    </div>

    <!-- Shift Detail Dialog -->
    <ShiftDetailDialog
      v-model:open="showShiftDetail"
      :shift-id="detailShiftId"
      @booking-updated="loadStats"
    />
  </div>
</template>
