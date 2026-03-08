<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { Calendar, List, Plus, Search } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import type {
  EventGroupListResponse,
  EventGroupRead,
  EventListResponse,
  EventRead,
} from '@/client/types.gen'
import Button from '@/components/ui/button/Button.vue'
import Input from '@/components/ui/input/Input.vue'
import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { useDialog } from '@/composables/useDialog'
import { toastApiError } from '@/lib/api-errors'
import { useAuthStore } from '@/stores/auth'

import EventCalendarView from '@/components/events/EventCalendarView.vue'
import EventListView from '@/components/events/EventListView.vue'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const { get, delete: del } = useAuthenticatedClient()
const { confirmDestructive } = useDialog()

const events = ref<EventRead[]>([])
const eventGroups = ref<EventGroupRead[]>([])
const loading = ref(false)
const searchQuery = ref('')
const viewMode = ref<'list' | 'calendar'>('list')

const filteredEvents = computed(() => {
  if (!searchQuery.value) return events.value
  const query = searchQuery.value.toLowerCase()
  return events.value.filter(
    (e) =>
      e.name.toLowerCase().includes(query) ||
      e.description?.toLowerCase().includes(query),
  )
})

const loadEvents = async () => {
  loading.value = true
  try {
    const [eventsRes, groupsRes] = await Promise.all([
      get<{ data: EventListResponse }>({ url: '/events/', query: { limit: 100 } }),
      get<{ data: EventGroupListResponse }>({ url: '/event-groups/', query: { limit: 100 } }),
    ])
    events.value = eventsRes.data.items
    eventGroups.value = groupsRes.data.items
  } catch (error) {
    toastApiError(error)
  } finally {
    loading.value = false
  }
}

const handleDelete = async (event: EventRead) => {
  const confirmed = await confirmDestructive(t('duties.events.deleteConfirm'))
  if (!confirmed) return

  try {
    await del({ url: `/events/${event.id}` })
    toast.success(t('duties.events.delete'))
    await loadEvents()
  } catch (error) {
    toastApiError(error)
  }
}

const navigateToEvent = (event: EventRead) => {
  router.push({ name: 'event-detail', params: { eventId: event.id } })
}

const navigateToGroup = (group: EventGroupRead) => {
  router.push({ name: 'event-group-detail', params: { groupId: group.id } })
}

onMounted(loadEvents)
</script>

<template>
  <div class="mx-auto max-w-7xl space-y-6">
    <!-- Header -->
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="space-y-2">
        <h1 class="text-3xl font-bold">{{ t('duties.events.title') }}</h1>
        <p class="text-muted-foreground">{{ t('duties.events.subtitle') }}</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <!-- View Toggle -->
        <div class="flex overflow-hidden rounded-md border">
          <Button
            :variant="viewMode === 'list' ? 'default' : 'ghost'"
            size="sm"
            class="rounded-none border-0"
            @click="viewMode = 'list'"
          >
            <List class="mr-1.5 h-4 w-4" />
            <span class="hidden sm:inline">{{ t('duties.events.views.list') }}</span>
          </Button>
          <Button
            :variant="viewMode === 'calendar' ? 'default' : 'ghost'"
            size="sm"
            class="rounded-none border-0 border-l"
            @click="viewMode = 'calendar'"
          >
            <Calendar class="mr-1.5 h-4 w-4" />
            <span class="hidden sm:inline">{{ t('duties.events.views.calendar') }}</span>
          </Button>
        </div>

        <Button v-if="authStore.isAdmin" @click="router.push({ name: 'event-create' })">
          <Plus class="mr-2 h-4 w-4" />
          {{ t('duties.events.create') }}
        </Button>
      </div>
    </div>

    <!-- Search -->
    <div class="relative">
      <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input v-model="searchQuery" :placeholder="t('common.actions.search')" class="pl-10" />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="py-12 text-center text-muted-foreground">
      {{ t('common.states.loading') }}
    </div>

    <template v-else>
      <EventListView
        v-if="viewMode === 'list'"
        :events="filteredEvents"
        @navigate="navigateToEvent"
        @delete="handleDelete"
      />
      <EventCalendarView
        v-else
        :events="filteredEvents"
        :event-groups="eventGroups"
        @navigate="navigateToEvent"
        @navigate-group="navigateToGroup"
      />
    </template>

  </div>
</template>
