<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { AlertTriangle } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { useAuthStore } from '@/stores/auth'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import Badge from '@/components/ui/badge/Badge.vue'

import CreateEventDialog, {
  type CreateEventPayload,
} from '@/components/select-event/CreateEventDialog.vue'
import EventPickerList from '@/components/select-event/EventPickerList.vue'
import NotificationSetupStep from '@/components/select-event/NotificationSetupStep.vue'
import SelectEventHeroPane, {
  type SelectEventMode,
} from '@/components/select-event/SelectEventHeroPane.vue'
import SelectEventTopBar from '@/components/select-event/SelectEventTopBar.vue'
import type { EventStats } from '@/components/select-event/SelectableEventCard.vue'

import type { EventListResponse, EventRead, TaskFeedResponse } from '@/client/types.gen'
import { toastApiError } from '@/lib/api-errors'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { get, post, patch } = useAuthenticatedClient()

const selectMode = computed<SelectEventMode>(() => {
  const raw = route.query.mode
  if (raw === 'switch' || raw === 'expired') return raw
  return 'onboarding'
})

const step = ref<1 | 2>(1)
const events = ref<EventRead[]>([])
const eventStats = ref<Record<string, EventStats>>({})
const loading = ref(true)
const showCreateDialog = ref(false)
const submitting = ref(false)
// Radio-style selection: clicking a card stages it; Continue commits it.
const pendingSelectionId = ref<string | null>(authStore.selectedEventId ?? null)

const phoneNumber = ref('')
const savingPhone = ref(false)

const isAdminOrManager = computed(() => authStore.isAdmin || authStore.isTaskManager)

async function loadEvents() {
  loading.value = true
  try {
    const res = await get<{ data: EventListResponse }>({
      url: '/events/',
      query: { limit: 100, date_from: new Date().toISOString().slice(0, 10), all_events: true },
    })
    events.value = res.data.items.filter((e) => !e.is_expired)

    const statsById: Record<string, EventStats> = {}
    await Promise.all(
      events.value.map(async (event) => {
        try {
          const feedRes = await get<{ data: TaskFeedResponse }>({
            url: '/tasks/feed',
            query: { view: 'cards', event_id: event.id, all_events: true, limit: 200 },
          })
          const items = feedRes.data.items
          statsById[event.id] = {
            taskCount: feedRes.data.total ?? items.length,
            totalShifts: items.reduce((s, t) => s + (t.total_shifts ?? 0), 0),
            openShifts: items.reduce((s, t) => s + (t.available_shifts ?? 0), 0),
          }
        } catch {
          statsById[event.id] = { taskCount: 0, totalShifts: 0, openShifts: 0 }
        }
      }),
    )
    eventStats.value = statsById
  } catch (error) {
    toastApiError(error)
  } finally {
    loading.value = false
  }
}

function handleStageSelection(event: EventRead) {
  pendingSelectionId.value = event.id
}

async function handleCommitSelection() {
  if (!pendingSelectionId.value) return
  submitting.value = true
  try {
    if (pendingSelectionId.value !== authStore.selectedEventId) {
      await authStore.setSelectedEvent(pendingSelectionId.value)
    }
    if (selectMode.value === 'onboarding') {
      step.value = 2
    } else {
      toast.success(t('duties.selectEvent.success'))
      router.push({ name: 'home' })
    }
  } catch (error) {
    toastApiError(error)
  } finally {
    submitting.value = false
  }
}

async function handleCreate(payload: CreateEventPayload) {
  submitting.value = true
  try {
    const res = await post<{ data: EventRead }>({
      url: '/events/',
      body: { ...payload, status: 'published' },
    })
    showCreateDialog.value = false
    // Refresh the list and stage the new event; user still presses Continue.
    await loadEvents()
    pendingSelectionId.value = res.data.id
  } catch (error) {
    toastApiError(error)
  } finally {
    submitting.value = false
  }
}

async function savePhone() {
  savingPhone.value = true
  try {
    await patch({
      url: '/users/me',
      body: { phone_number: phoneNumber.value || null },
    })
  } catch (error) {
    toastApiError(error)
  } finally {
    savingPhone.value = false
  }
}

async function finishOnboarding() {
  if (phoneNumber.value && phoneNumber.value !== (authStore.profile?.phone_number ?? '')) {
    await savePhone()
  }
  toast.success(t('duties.selectEvent.success'))
  router.push({ name: 'home' })
}

watch(
  () => authStore.profile?.phone_number,
  (value) => {
    phoneNumber.value = value ?? ''
  },
  { immediate: true },
)

onMounted(loadEvents)
</script>

<template>
  <div class="h-screen overflow-hidden grid lg:grid-cols-2">
    <SelectEventHeroPane :step="step" :mode="selectMode" />

    <main class="flex flex-col h-full overflow-hidden">
      <SelectEventTopBar />

      <div class="flex-1 overflow-y-auto">
        <div
          class="mx-auto flex min-h-full w-full max-w-3xl flex-col justify-center space-y-6 px-4 py-6 sm:px-8"
        >
          <div
            v-if="selectMode === 'expired'"
            class="rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive"
          >
            <div class="flex items-start gap-2">
              <AlertTriangle class="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <p class="font-semibold">{{ t('duties.selectEvent.expired.title') }}</p>
                <p>{{ t('duties.selectEvent.expired.body') }}</p>
              </div>
            </div>
          </div>

          <div class="space-y-2">
            <h1 data-testid="page-heading" class="text-2xl sm:text-3xl font-bold tracking-tight">
              {{
                step === 1
                  ? t('duties.selectEvent.pick.title')
                  : t('duties.selectEvent.notifications.title')
              }}
            </h1>
            <p class="text-muted-foreground">
              {{
                step === 1
                  ? t('duties.selectEvent.pick.subtitle')
                  : t('duties.selectEvent.notifications.subtitle')
              }}
            </p>
            <div
              v-if="selectMode === 'onboarding'"
              class="flex items-center gap-2 pt-2 text-xs text-muted-foreground"
            >
              <Badge :variant="step === 1 ? 'default' : 'secondary'">1</Badge>
              <span>{{ t('duties.selectEvent.pick.title') }}</span>
              <span class="mx-1">/</span>
              <Badge :variant="step === 2 ? 'default' : 'secondary'">2</Badge>
              <span>{{ t('duties.selectEvent.notifications.title') }}</span>
            </div>
          </div>

          <EventPickerList
            v-if="step === 1"
            :events="events"
            :stats="eventStats"
            :loading="loading"
            :pending-selection-id="pendingSelectionId"
            :current-selected-id="authStore.selectedEventId"
            :can-create-events="isAdminOrManager"
            :submitting="submitting"
            @stage="handleStageSelection"
            @commit="handleCommitSelection"
            @open-create="showCreateDialog = true"
          />

          <NotificationSetupStep
            v-else
            v-model:phone-number="phoneNumber"
            :saving-phone="savingPhone"
            @back="step = 1"
            @finish="finishOnboarding"
          />
        </div>
      </div>
    </main>

    <CreateEventDialog
      v-model:open="showCreateDialog"
      :submitting="submitting"
      @submit="handleCreate"
    />
  </div>
</template>
