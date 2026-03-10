<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { Calendar, List, Plus, Search, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { useAuthStore } from '@/stores/auth'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import Button from '@/components/ui/button/Button.vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import Input from '@/components/ui/input/Input.vue'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'

import EventCalendarView from '@/components/events/EventCalendarView.vue'
import EventListView from '@/components/events/EventListView.vue'

import type {
  EventGroupListResponse,
  EventGroupRead,
  EventListResponse,
  EventRead,
} from '@/client/types.gen'
import { toastApiError } from '@/lib/api-errors'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const { get, delete: del } = useAuthenticatedClient()

const events = ref<EventRead[]>([])
const eventGroups = ref<EventGroupRead[]>([])
const loading = ref(false)
const searchQuery = ref('')
const viewMode = ref<'list' | 'calendar'>('list')
const myBookingsOnly = ref(false)

// Delete dialog state
const showDeleteDialog = ref(false)
const deleteReason = ref('')
const deleteTarget = ref<EventRead | null>(null)

const filteredEvents = computed(() => {
  if (!searchQuery.value) return events.value
  const query = searchQuery.value.toLowerCase()
  return events.value.filter(
    (e) => e.name.toLowerCase().includes(query) || e.description?.toLowerCase().includes(query),
  )
})

const loadEvents = async () => {
  loading.value = true
  try {
    const query: Record<string, unknown> = { limit: 100 }
    if (myBookingsOnly.value) query.my_bookings = true

    const [eventsRes, groupsRes] = await Promise.all([
      get<{ data: EventListResponse }>({ url: '/events/', query }),
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

watch(myBookingsOnly, () => loadEvents())

const handleDelete = (event: EventRead) => {
  deleteTarget.value = event
  deleteReason.value = ''
  showDeleteDialog.value = true
}

const confirmDeleteEvent = async () => {
  if (!deleteTarget.value) return
  showDeleteDialog.value = false
  try {
    const query: Record<string, string> = {}
    if (deleteReason.value.trim()) query.cancellation_reason = deleteReason.value.trim()
    await del({ url: `/events/${deleteTarget.value.id}`, query })
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

    <!-- Search & Filter -->
    <div class="flex flex-wrap items-center gap-4">
      <div class="relative flex-1">
        <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input v-model="searchQuery" :placeholder="t('common.actions.search')" class="pl-10" />
      </div>
      <div class="flex items-center gap-2">
        <Switch id="my-bookings" v-model="myBookingsOnly" />
        <Label for="my-bookings" class="cursor-pointer text-sm whitespace-nowrap">
          {{ t('duties.events.myBookingsFilter') }}
        </Label>
      </div>
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

    <!-- Delete Event Dialog -->
    <Dialog v-model:open="showDeleteDialog">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle class="flex items-center gap-2">
            <Trash2 class="h-5 w-5 text-destructive" />
            {{ t('common.dialog.confirm.title') }}
          </DialogTitle>
          <DialogDescription class="text-left">
            {{ t('duties.events.deleteConfirm') }}
          </DialogDescription>
        </DialogHeader>

        <div class="space-y-3">
          <p class="text-sm text-muted-foreground">
            {{ t('duties.deleteDialog.activeBookingsWarning') }}
          </p>
          <div class="space-y-2">
            <Label>{{ t('duties.deleteDialog.reasonLabel') }}</Label>
            <Textarea
              v-model="deleteReason"
              :placeholder="t('duties.deleteDialog.reasonPlaceholder')"
              rows="3"
            />
            <p class="text-xs text-muted-foreground">
              {{ t('duties.deleteDialog.reasonHint') }}
            </p>
          </div>
        </div>

        <DialogFooter class="sm:justify-start">
          <Button variant="outline" @click="showDeleteDialog = false">
            {{ t('common.dialog.confirm.cancelText') }}
          </Button>
          <Button variant="destructive" @click="confirmDeleteEvent">
            {{ t('common.dialog.confirm.confirmText') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
