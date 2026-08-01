<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { AlertTriangle } from '@lucide/vue'
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
import type { EventStats } from '@/components/select-event/SelectableEventCard.vue'
import SelectEventHeroPane, {
  type SelectEventMode,
} from '@/components/select-event/SelectEventHeroPane.vue'
import SelectEventTopBar from '@/components/select-event/SelectEventTopBar.vue'

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

const onboarding = computed(() => selectMode.value === 'onboarding')

const step = ref<1 | 2>(1)
const phase = ref<'intro' | 'main'>('intro')

// Mobile strip layout: 4 panels [H1, M1, H2, M2] for onboarding (forward = always slide left)
// or 2 panels [Hero, Main] for switch/expired (hero offscreen, main shown).
const stripWidthClass = computed(() => (onboarding.value ? 'w-[400%]' : 'w-[200%]'))
const panelWidthClass = computed(() => (onboarding.value ? 'w-1/4' : 'w-1/2'))
const stripTranslateClass = computed(() => {
  if (!onboarding.value) return '-translate-x-1/2'
  if (step.value === 1) return phase.value === 'intro' ? 'translate-x-0' : '-translate-x-1/4'
  return phase.value === 'intro' ? '-translate-x-1/2' : '-translate-x-3/4'
})

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
      phase.value = 'intro'
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

function handleCancel() {
  router.push({ name: 'home' })
}

function handleHeroBackFromStep2() {
  step.value = 1
  phase.value = 'main'
}

function handleNotifBack() {
  step.value = 1
  phase.value = 'main'
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
  <div class="relative h-screen overflow-hidden">
    <div
      :class="[
        'flex h-full transition-transform duration-300 ease-out motion-reduce:transition-none',
        stripWidthClass,
        stripTranslateClass,
        'lg:grid lg:w-full lg:grid-cols-2 lg:translate-x-0 lg:transition-none',
      ]"
    >
      <!-- Hero step 1 -->
      <SelectEventHeroPane
        :class="[panelWidthClass, 'shrink-0 lg:w-auto', step === 1 ? '' : 'lg:hidden']"
        :step="1"
        :mode="selectMode"
        :show-mobile-continue="onboarding && step === 1 && phase === 'intro'"
        @mobile-continue="phase = 'main'"
      />

      <!-- Main step 1: picker -->
      <main
        :class="[
          'flex flex-col h-full overflow-hidden',
          panelWidthClass,
          'shrink-0 lg:w-auto',
          step === 1 ? '' : 'lg:hidden',
        ]"
      >
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
                {{ t('duties.selectEvent.pick.title') }}
              </h1>
              <p class="text-muted-foreground">{{ t('duties.selectEvent.pick.subtitle') }}</p>
              <div
                v-if="onboarding"
                class="flex flex-wrap items-center gap-x-2 gap-y-1 pt-2 text-xs text-muted-foreground"
              >
                <div class="flex items-center gap-2">
                  <Badge variant="default">1</Badge>
                  <span>{{ t('duties.selectEvent.pick.title') }}</span>
                </div>
                <span aria-hidden="true">/</span>
                <div class="flex items-center gap-2">
                  <Badge variant="secondary">2</Badge>
                  <span>{{ t('duties.selectEvent.notifications.title') }}</span>
                </div>
              </div>
            </div>

            <EventPickerList
              :events="events"
              :stats="eventStats"
              :loading="loading"
              :pending-selection-id="pendingSelectionId"
              :current-selected-id="authStore.selectedEventId"
              :can-create-events="isAdminOrManager"
              :submitting="submitting"
              :mode="selectMode"
              @stage="handleStageSelection"
              @commit="handleCommitSelection"
              @cancel="handleCancel"
              @back="phase = 'intro'"
              @open-create="showCreateDialog = true"
            />
          </div>
        </div>
      </main>

      <!-- Hero step 2 (onboarding only) -->
      <SelectEventHeroPane
        v-if="onboarding"
        :class="[panelWidthClass, 'shrink-0 lg:w-auto', step === 2 ? '' : 'lg:hidden']"
        :step="2"
        :mode="selectMode"
        :show-mobile-continue="step === 2 && phase === 'intro'"
        @mobile-continue="phase = 'main'"
        @mobile-back="handleHeroBackFromStep2"
      />

      <!-- Main step 2: notifications (onboarding only) -->
      <main
        v-if="onboarding"
        :class="[
          'flex flex-col h-full overflow-hidden',
          panelWidthClass,
          'shrink-0 lg:w-auto',
          step === 2 ? '' : 'lg:hidden',
        ]"
      >
        <SelectEventTopBar />
        <div class="flex-1 overflow-y-auto">
          <div
            class="mx-auto flex min-h-full w-full max-w-3xl flex-col justify-center space-y-6 px-4 py-6 sm:px-8"
          >
            <div class="space-y-2">
              <h1 class="text-2xl sm:text-3xl font-bold tracking-tight">
                {{ t('duties.selectEvent.notifications.title') }}
              </h1>
              <p class="text-muted-foreground">
                {{ t('duties.selectEvent.notifications.subtitle') }}
              </p>
              <div
                class="flex flex-wrap items-center gap-x-2 gap-y-1 pt-2 text-xs text-muted-foreground"
              >
                <div class="flex items-center gap-2">
                  <Badge variant="secondary">1</Badge>
                  <span>{{ t('duties.selectEvent.pick.title') }}</span>
                </div>
                <span aria-hidden="true">/</span>
                <div class="flex items-center gap-2">
                  <Badge variant="default">2</Badge>
                  <span>{{ t('duties.selectEvent.notifications.title') }}</span>
                </div>
              </div>
            </div>

            <NotificationSetupStep
              v-model:phone-number="phoneNumber"
              :saving-phone="savingPhone"
              @back="handleNotifBack"
              @finish="finishOnboarding"
            />
          </div>
        </div>
      </main>
    </div>

    <CreateEventDialog
      v-model:open="showCreateDialog"
      :submitting="submitting"
      @submit="handleCreate"
    />
  </div>
</template>
