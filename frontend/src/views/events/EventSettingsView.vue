<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { ShieldCheck } from '@respeak/lucide-motion-vue'
import { Pencil } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import Button from '@/components/ui/button/Button.vue'

import EventEditForm from '@/components/events/EventEditForm.vue'
import EventManagers from '@/components/events/EventManagers.vue'

import type { EventRead, TaskListResponse, TaskRead, UserRead } from '@/client/types.gen'
import { toastApiError } from '@/lib/api-errors'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { get } = useAuthenticatedClient()

const targetEventId = computed<string | null>(() => {
  const q = route.query.eventId
  if (typeof q === 'string' && q) return q
  return authStore.selectedEventId ?? null
})

type Tab = 'details' | 'managers'
const activeTab = ref<Tab>('details')

function readTabFromQuery() {
  const qTab = route.query.tab
  if (qTab === 'managers') activeTab.value = 'managers'
  else activeTab.value = 'details'
}
readTabFromQuery()
watch(() => route.query.tab, readTabFromQuery)

function setTab(tab: Tab) {
  activeTab.value = tab
  router.replace({
    query: {
      ...route.query,
      tab: tab === 'details' ? undefined : tab,
    },
  })
}

const event = ref<EventRead | null>(null)
const tasks = ref<TaskRead[]>([])
const managers = ref<UserRead[]>([])
const loading = ref(false)

const canManage = computed(() =>
  targetEventId.value ? authStore.canManageEvent(targetEventId.value) : false,
)

async function loadManagers() {
  if (!targetEventId.value) return
  try {
    const res = await get<{ data: UserRead[] }>({
      url: `/events/${targetEventId.value}/managers`,
    })
    managers.value = res.data
  } catch {
    managers.value = []
  }
}

async function loadEvent() {
  if (!targetEventId.value) return
  loading.value = true
  try {
    const [eventRes, tasksRes] = await Promise.all([
      get<{ data: EventRead }>({ url: `/events/${targetEventId.value}` }),
      get<{ data: TaskListResponse }>({
        url: '/tasks/',
        query: { limit: 200, event_id: targetEventId.value, all_events: true },
      }),
    ])
    event.value = eventRes.data
    tasks.value = tasksRes.data.items
    if (canManage.value) await loadManagers()
  } catch (error) {
    toastApiError(error)
  } finally {
    loading.value = false
  }
}

function handleUpdated(updated: EventRead) {
  event.value = updated
}

watch(targetEventId, () => {
  event.value = null
  managers.value = []
  tasks.value = []
  loadEvent()
})

onMounted(loadEvent)
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-6">
    <div class="space-y-2">
      <h1 data-testid="page-heading" class="text-2xl sm:text-3xl font-bold">
        {{ t('duties.events.detail.title') }}
      </h1>
      <p v-if="event" class="text-muted-foreground">{{ event.name }}</p>
    </div>

    <div class="flex items-center gap-2 border-b">
      <Button
        variant="ghost"
        :class="[
          'rounded-none border-b-2 -mb-px',
          activeTab === 'details' ? 'border-primary text-primary' : 'border-transparent',
        ]"
        data-testid="tab-details"
        @click="setTab('details')"
      >
        <Pencil class="mr-2 h-4 w-4" />
        {{ t('duties.events.detail.nav.details') }}
      </Button>
      <Button
        v-if="authStore.isAdmin"
        variant="ghost"
        :class="[
          'rounded-none border-b-2 -mb-px',
          activeTab === 'managers' ? 'border-primary text-primary' : 'border-transparent',
        ]"
        data-testid="tab-managers"
        @click="setTab('managers')"
      >
        <ShieldCheck class="mr-2 h-4 w-4" animateOnHover triggerTarget="parent" />
        {{ t('duties.events.detail.nav.management') }}
      </Button>
    </div>

    <div v-if="loading" class="py-12 text-center text-muted-foreground">
      {{ t('common.states.loading') }}
    </div>

    <template v-else-if="event && targetEventId">
      <EventEditForm
        v-if="activeTab === 'details'"
        :event="event"
        :event-id="targetEventId"
        :tasks="tasks"
        @updated="handleUpdated"
        @cancel="router.back()"
      />
      <EventManagers
        v-else-if="activeTab === 'managers'"
        :event-id="targetEventId"
        :managers="managers"
        :can-edit="authStore.isAdmin"
        @updated="loadManagers"
      />
    </template>
  </div>
</template>
