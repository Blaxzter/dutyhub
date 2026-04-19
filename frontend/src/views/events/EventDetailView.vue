<script setup lang="ts">
import { type Component, computed, onMounted, ref, watch } from 'vue'

import { createReusableTemplate, useMediaQuery } from '@vueuse/core'
import {
  ArrowLeft,
  CalendarCheck,
  ListTodo,
  Pencil,
  Plus,
  Printer,
  ShieldCheck,
} from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { useAuthStore } from '@/stores/auth'
import { useBreadcrumbStore } from '@/stores/breadcrumb'

import { useAdaptiveCarouselHeight } from '@/composables/useAdaptiveCarouselHeight'
import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { useDialog } from '@/composables/useDialog'

import Button from '@/components/ui/button/Button.vue'
import { Carousel, CarouselContent, CarouselItem } from '@/components/ui/carousel'
import type { UnwrapRefCarouselApi } from '@/components/ui/carousel/interface'

import EventAvailability from '@/components/events/EventAvailability.vue'
import EventEditForm from '@/components/events/EventEditForm.vue'
import EventTasks from '@/components/events/EventTasks.vue'
import EventHeader from '@/components/events/EventHeader.vue'
import EventManagers from '@/components/events/EventManagers.vue'
import EventPrint from '@/components/events/EventPrint.vue'
import AvailabilityDialog from '@/components/tasks/AvailabilityDialog.vue'
import ChipNav from '@/components/utils/ChipNav.vue'

import type {
  EventRead,
  TaskListResponse,
  TaskRead,
  UserAvailabilityRead,
  UserAvailabilityWithUser,
  UserRead,
} from '@/client/types.gen'
import { toastApiError } from '@/lib/api-errors'

interface NavItem {
  id: string
  label: string
  icon: Component
  adminOnly?: boolean
  mobileOnly?: boolean
}

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const breadcrumbStore = useBreadcrumbStore()
const { get, post, patch, delete: del } = useAuthenticatedClient()
const { confirmDestructive } = useDialog()

const isDesktop = useMediaQuery('(min-width: 1280px)')

const [DefineSectionContent, SectionContent] = createReusableTemplate<{ id: string }>()

const groupId = computed(() => route.params.groupId as string)

const canManageEvent = computed(() => authStore.canManageEvent(groupId.value))

const group = ref<EventRead | null>(null)
const groupTasks = ref<TaskRead[]>([])
const myAvailability = ref<UserAvailabilityRead | null>(null)
const allAvailabilities = ref<UserAvailabilityWithUser[]>([])
const loading = ref(false)
const showAvailabilityDialog = ref(false)
const groupManagers = ref<UserRead[]>([])

// ── Navigation ──
const navItems = computed<NavItem[]>(() => [
  { id: 'tasks', label: t('duties.events.detail.nav.tasks'), icon: ListTodo },
  {
    id: 'availability',
    label: t('duties.events.detail.nav.availability'),
    icon: CalendarCheck,
  },
  {
    id: 'print',
    label: t('duties.events.detail.nav.print'),
    icon: Printer,
    mobileOnly: true,
  },
  {
    id: 'details',
    label: t('duties.events.detail.nav.details'),
    icon: Pencil,
    adminOnly: true,
  },
  {
    id: 'management',
    label: t('duties.events.detail.nav.management'),
    icon: ShieldCheck,
    adminOnly: true,
  },
])

const visibleNavItems = computed(() =>
  navItems.value.filter(
    (item) =>
      (!item.adminOnly || canManageEvent.value) && (!item.mobileOnly || !isDesktop.value),
  ),
)

const chipItems = computed(() =>
  visibleNavItems.value.map((item) => ({ label: item.label, icon: item.icon })),
)

const validSectionIds = computed(() => visibleNavItems.value.map((item) => item.id))

const activeSection = computed({
  get: () => {
    const param = route.params.section as string | undefined
    if (param && validSectionIds.value.includes(param)) return param
    return 'tasks'
  },
  set: (id: string) => {
    router.replace({
      name: 'event-detail',
      params: {
        groupId: groupId.value,
        section: id === 'tasks' ? undefined : id,
      },
    })
  },
})

// ── Mobile carousel ──
const mobileSlide = ref(validSectionIds.value.indexOf(activeSection.value))
const carouselApi = ref<UnwrapRefCarouselApi>()
useAdaptiveCarouselHeight(carouselApi)

function onCarouselInit(api: UnwrapRefCarouselApi) {
  carouselApi.value = api
  if (!api) return
  if (mobileSlide.value > 0) {
    api.scrollTo(mobileSlide.value, true)
  }
  api.on('select', () => {
    const index = api.selectedScrollSnap()
    mobileSlide.value = index
    const sectionId = visibleNavItems.value[index]?.id
    if (sectionId && sectionId !== activeSection.value) {
      activeSection.value = sectionId
    }
  })
}

watch(mobileSlide, (index) => {
  carouselApi.value?.scrollTo(index)
  const sectionId = visibleNavItems.value[index]?.id
  if (sectionId && sectionId !== activeSection.value) {
    activeSection.value = sectionId
  }
})

watch(activeSection, (id) => {
  const index = validSectionIds.value.indexOf(id)
  if (index !== -1 && index !== mobileSlide.value) {
    mobileSlide.value = index
  }
})

// ── Breadcrumbs ──
// Drive a 3-element trail ("Task Groups > Group Name > Section") reactively.
// The group crumb is marked mobileSkip so mobile back-link walks past it
// to "Task Groups" instead of self-linking the same page.
// Published synchronously with an ellipsis placeholder so the structure
// doesn't flicker against the 2-element meta.breadcrumbs while the group loads.
const breadcrumbItems = computed(() => [
  {
    title: 'Task Groups',
    titleKey: 'duties.events.title',
    to: { name: 'events' },
  },
  {
    title: group.value?.name ?? '…',
    mobileSkip: true,
    to: { name: 'event-detail', params: { groupId: groupId.value } },
  },
  {
    title: '',
    titleKey: `duties.events.detail.nav.${activeSection.value}`,
  },
])

watch(
  breadcrumbItems,
  (items) => {
    breadcrumbStore.setBreadcrumbs(items)
  },
  { immediate: true },
)

// ── Data loading ──
const handleGroupUpdated = (updated: EventRead) => {
  group.value = updated
  activeSection.value = 'tasks'
}

const handleStatusChange = async (status: 'draft' | 'published' | 'archived') => {
  if (!group.value || group.value.status === status) return
  try {
    const res = await patch<{ data: EventRead }>({
      url: `/events/${groupId.value}`,
      body: { status },
    })
    group.value = res.data
    toast.success(t(`duties.events.statuses.${status}`))
  } catch (error) {
    toastApiError(error)
  }
}

const loadManagers = async () => {
  try {
    const res = await get<{ data: UserRead[] }>({
      url: `/events/${groupId.value}/managers`,
    })
    groupManagers.value = res.data
  } catch {
    groupManagers.value = []
  }
}

const loadGroup = async () => {
  if (!groupId.value) return
  loading.value = true
  try {
    const [groupRes, tasksRes] = await Promise.all([
      get<{ data: EventRead }>({ url: `/events/${groupId.value}` }),
      get<{ data: TaskListResponse }>({
        url: '/tasks/',
        query: { limit: 200, event_id: groupId.value },
      }),
    ])
    group.value = groupRes.data
    groupTasks.value = tasksRes.data.items


    try {
      const availRes = await get<{ data: UserAvailabilityRead }>({
        url: `/events/${groupId.value}/availability/me`,
      })
      myAvailability.value = availRes.data
    } catch {
      myAvailability.value = null
    }

    if (canManageEvent.value) {
      await loadManagers()
    }

    if (canManageEvent.value) {
      try {
        const adminRes = await get<{ data: UserAvailabilityWithUser[] }>({
          url: `/events/${groupId.value}/availabilities`,
        })
        allAvailabilities.value = adminRes.data
      } catch {
        allAvailabilities.value = []
      }
    }
  } catch (error) {
    toastApiError(error)
  } finally {
    loading.value = false
  }
}

const handleSaveAvailability = async (payload: {
  availability_type: 'fully_available' | 'specific_dates' | 'time_range'
  notes?: string
  default_start_time?: string
  default_end_time?: string
  dates: { date: string; start_time?: string; end_time?: string }[]
}) => {
  try {
    const res = await post<{ data: UserAvailabilityRead }>({
      url: `/events/${groupId.value}/availability`,
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
    if (canManageEvent.value) {
      const adminRes = await get<{ data: UserAvailabilityWithUser[] }>({
        url: `/events/${groupId.value}/availabilities`,
      })
      allAvailabilities.value = adminRes.data
    }
  } catch (error) {
    toastApiError(error)
  }
}

const handleRemoveAvailability = async () => {
  const confirmed = await confirmDestructive(t('duties.availability.removeConfirm'))
  if (!confirmed) return

  try {
    await del({ url: `/events/${groupId.value}/availability/me` })
    myAvailability.value = null
    toast.success(t('duties.availability.remove'))
    if (canManageEvent.value) {
      const adminRes = await get<{ data: UserAvailabilityWithUser[] }>({
        url: `/events/${groupId.value}/availabilities`,
      })
      allAvailabilities.value = adminRes.data
    }
  } catch (error) {
    toastApiError(error)
  }
}

onMounted(loadGroup)
</script>

<template>
  <!-- Define section content once, reuse in both mobile and desktop layouts -->
  <DefineSectionContent v-slot="{ id }">
    <div
      class="space-y-6"
      :data-testid="id === 'management' ? 'section-management' : id === 'availability' ? 'section-availability' : undefined"
    >
      <EventTasks
        v-if="id === 'tasks'"
        :tasks="groupTasks"
        :group-id="groupId"
        :can-manage="canManageEvent"
      />

      <EventAvailability
        v-if="id === 'availability'"
        :my-availability="myAvailability"
        :all-availabilities="allAvailabilities"
        :can-manage="canManageEvent"
        @edit="showAvailabilityDialog = true"
        @remove="handleRemoveAvailability"
      />

      <EventPrint v-if="id === 'print'" :group-id="groupId" />

      <EventEditForm
        v-if="id === 'details'"
        :group="group!"
        :group-id="groupId"
        :tasks="groupTasks"
        @updated="handleGroupUpdated"
        @cancel="activeSection = 'tasks'"
      />

      <EventManagers
        v-if="id === 'management'"
        :group-id="groupId"
        :managers="groupManagers"
        :can-edit="authStore.isAdmin"
        @updated="loadManagers"
      />
    </div>
  </DefineSectionContent>

  <div :class="{ 'grid grid-cols-[1fr_56rem_1fr]': isDesktop }">
    <!-- Back + header -->
    <div :class="isDesktop ? 'col-start-2 space-y-6 pb-6' : 'mx-auto max-w-4xl space-y-6 pb-6'">
      <Button
        v-if="isDesktop"
        variant="ghost"
        size="sm"
        data-testid="btn-back"
        @click="router.push({ name: 'events' })"
      >
        <ArrowLeft class="mr-2 h-4 w-4" />
        {{ t('duties.events.title') }}
      </Button>

      <div v-if="loading" class="py-12 text-center text-muted-foreground">
        {{ t('common.states.loading') }}
      </div>

      <template v-else-if="group">
        <EventHeader
          :group="group"
          :group-id="groupId"
          :can-manage="canManageEvent"
          @status-change="handleStatusChange"
        />
      </template>
    </div>

    <!-- ==================== MOBILE / TABLET (<xl) ==================== -->
    <div v-if="!loading && group && !isDesktop" class="mx-auto max-w-4xl space-y-4">
      <ChipNav v-model="mobileSlide" :items="chipItems" />

      <Carousel class="w-full" @init-api="onCarouselInit" :opts="{ watchDrag: true }">
        <CarouselContent class="items-start">
          <CarouselItem v-for="item in visibleNavItems" :key="item.id" class="basis-full">
            <SectionContent :id="item.id" />
          </CarouselItem>
        </CarouselContent>
      </Carousel>
    </div>

    <!-- Mobile FAB: create task (tasks section only) -->
    <Button
      v-if="!loading && group && !isDesktop && canManageEvent && activeSection === 'tasks'"
      size="icon"
      class="fixed bottom-24 md:bottom-6 right-6 z-40 h-14 w-14 rounded-full shadow-lg"
      data-testid="fab-create-task"
      :aria-label="t('duties.tasks.create')"
      @click="router.push({ name: 'task-create', query: { groupId } })"
    >
      <Plus class="size-7" :stroke-width="2.5" />
    </Button>

    <!-- ==================== DESKTOP (xl+) ==================== -->
    <template v-if="!loading && group && isDesktop">
      <!-- Nav in left gutter -->
      <div class="row-start-2 flex justify-end pr-8">
        <nav class="w-44 sticky top-8 self-start space-y-1">
          <button
            v-for="item in visibleNavItems"
            :key="item.id"
            @click="activeSection = item.id"
            class="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors text-left"
            :class="[
              activeSection === item.id
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground',
            ]"
          >
            <component :is="item.icon" class="h-4 w-4 shrink-0" />
            {{ item.label }}
          </button>
        </nav>
      </div>

      <!-- Content -->
      <div class="row-start-2">
        <SectionContent :id="activeSection" />
      </div>

      <!-- Right spacer for symmetry -->
      <div class="row-start-2" aria-hidden="true" />
    </template>

    <!-- Availability Dialog -->
    <AvailabilityDialog
      v-if="group"
      v-model:open="showAvailabilityDialog"
      :group="group"
      :existing-availability="myAvailability"
      @save="handleSaveAvailability"
    />
  </div>
</template>
