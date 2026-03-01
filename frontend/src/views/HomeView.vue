<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { useAuthStore } from '@/stores/auth'
import { toastApiError } from '@/lib/api-errors'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CalendarDays, BookCheck, ClipboardList } from 'lucide-vue-next'
import type { EventListResponse, BookingListResponse } from '@/client'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const { get } = useAuthenticatedClient()

const eventCount = ref(0)
const myBookingCount = ref(0)
const loading = ref(true)

async function loadStats() {
  loading.value = true
  try {
    const [eventsRes, bookingsRes] = await Promise.all([
      get<{ data: EventListResponse }>({ url: '/events/', query: { limit: 1 } }),
      get<{ data: BookingListResponse }>({
        url: '/bookings/me',
        query: { status: 'confirmed', limit: 1 },
      }),
    ])
    eventCount.value = eventsRes.data.total
    myBookingCount.value = bookingsRes.data.total
  } catch (error) {
    toastApiError(error)
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
</script>

<template>
  <div class="mx-auto max-w-7xl space-y-6">
    <div class="space-y-2">
      <h1 class="text-3xl font-bold">{{ t('dashboard.home.title') }}</h1>
      <p class="text-muted-foreground">
        {{ t('dashboard.home.subtitle') }}
      </p>
    </div>

    <!-- Stats Cards -->
    <div class="grid auto-rows-min gap-4 md:grid-cols-3">
      <Card
        class="cursor-pointer hover:shadow-md transition-shadow"
        @click="router.push({ name: 'events' })"
      >
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium">{{ t('dashboard.home.stats.events.title') }}</CardTitle>
          <CalendarDays class="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold">{{ eventCount }}</div>
          <p class="text-xs text-muted-foreground">{{ t('dashboard.home.stats.events.description') }}</p>
        </CardContent>
      </Card>

      <Card
        class="cursor-pointer hover:shadow-md transition-shadow"
        @click="router.push({ name: 'my-bookings' })"
      >
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium">{{ t('dashboard.home.stats.bookings.title') }}</CardTitle>
          <BookCheck class="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold">{{ myBookingCount }}</div>
          <p class="text-xs text-muted-foreground">{{ t('dashboard.home.stats.bookings.description') }}</p>
        </CardContent>
      </Card>

      <Card v-if="authStore.isAdmin">
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium">{{ t('dashboard.home.stats.admin.title') }}</CardTitle>
          <ClipboardList class="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <p class="text-xs text-muted-foreground">{{ t('dashboard.home.stats.admin.description') }}</p>
          <Button size="sm" class="mt-2" @click="router.push({ name: 'events' })">
            {{ t('dashboard.home.stats.admin.action') }}
          </Button>
        </CardContent>
      </Card>
    </div>

    <!-- Quick Actions -->
    <div class="rounded-xl bg-muted/50 p-6">
      <h2 class="text-xl font-semibold mb-4">{{ t('dashboard.home.quickActions.title') }}</h2>
      <div class="flex flex-wrap gap-3">
        <Button variant="outline" @click="router.push({ name: 'events' })">
          <CalendarDays class="mr-2 h-4 w-4" />
          {{ t('dashboard.home.quickActions.browseEvents') }}
        </Button>
        <Button variant="outline" @click="router.push({ name: 'my-bookings' })">
          <BookCheck class="mr-2 h-4 w-4" />
          {{ t('dashboard.home.quickActions.myBookings') }}
        </Button>
      </div>
    </div>
  </div>
</template>
