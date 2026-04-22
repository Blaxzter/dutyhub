<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import { useAuthStore } from '@/stores/auth'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { useDialog } from '@/composables/useDialog'

import EventAvailability from '@/components/events/EventAvailability.vue'
import AvailabilityDialog from '@/components/tasks/AvailabilityDialog.vue'

import type { UserAvailabilityRead, UserAvailabilityWithUser } from '@/client/types.gen'
import { toastApiError } from '@/lib/api-errors'

const { t } = useI18n()
const authStore = useAuthStore()
const { get, post, delete: del } = useAuthenticatedClient()
const { confirmDestructive } = useDialog()

const eventId = computed(() => authStore.selectedEventId ?? null)
const canManage = computed(() => (eventId.value ? authStore.canManageEvent(eventId.value) : false))

const myAvailability = ref<UserAvailabilityRead | null>(null)
const allAvailabilities = ref<UserAvailabilityWithUser[]>([])
const showAvailabilityDialog = ref(false)

async function loadData() {
  if (!eventId.value) return
  try {
    const availRes = await get<{ data: UserAvailabilityRead }>({
      url: `/events/${eventId.value}/availability/me`,
    })
    myAvailability.value = availRes.data
  } catch {
    myAvailability.value = null
  }
  if (canManage.value) {
    try {
      const adminRes = await get<{ data: UserAvailabilityWithUser[] }>({
        url: `/events/${eventId.value}/availabilities`,
      })
      allAvailabilities.value = adminRes.data
    } catch {
      allAvailabilities.value = []
    }
  }
}

async function handleSave(payload: {
  availability_type: 'fully_available' | 'specific_dates' | 'time_range'
  notes?: string
  default_start_time?: string
  default_end_time?: string
  dates: { date: string; start_time?: string; end_time?: string }[]
}) {
  if (!eventId.value) return
  try {
    const res = await post<{ data: UserAvailabilityRead }>({
      url: `/events/${eventId.value}/availability`,
      body: {
        availability_type: payload.availability_type,
        notes: payload.notes,
        default_start_time: payload.default_start_time,
        default_end_time: payload.default_end_time,
        dates: payload.dates,
      },
    })
    myAvailability.value = res.data
    showAvailabilityDialog.value = false
    toast.success(t('duties.availability.update'))
    await loadData()
  } catch (error) {
    toastApiError(error)
  }
}

async function handleRemove() {
  if (!eventId.value) return
  const confirmed = await confirmDestructive(t('duties.availability.removeConfirm'))
  if (!confirmed) return
  try {
    await del({ url: `/events/${eventId.value}/availability/me` })
    myAvailability.value = null
    toast.success(t('duties.availability.remove'))
    await loadData()
  } catch (error) {
    toastApiError(error)
  }
}

onMounted(loadData)
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-6">
    <div class="space-y-2">
      <h1 data-testid="page-heading" class="text-2xl sm:text-3xl font-bold">
        {{ t('duties.availability.title') }}
      </h1>
      <p class="text-muted-foreground">
        {{ authStore.selectedEvent?.name ?? t('duties.availability.subtitle') }}
      </p>
    </div>

    <EventAvailability
      v-if="eventId"
      :my-availability="myAvailability"
      :all-availabilities="allAvailabilities"
      :can-manage="canManage"
      @edit="showAvailabilityDialog = true"
      @remove="handleRemove"
    />

    <AvailabilityDialog
      v-if="authStore.selectedEvent"
      v-model:open="showAvailabilityDialog"
      :event="authStore.selectedEvent"
      :existing-availability="myAvailability"
      @save="handleSave"
    />
  </div>
</template>
