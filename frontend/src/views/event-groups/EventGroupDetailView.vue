<script setup lang="ts">
import { type Component, computed, onMounted, ref, watch } from 'vue'

import { createReusableTemplate, useMediaQuery } from '@vueuse/core'
import { ArrowLeft, CalendarCheck, ListTodo, Pencil, ShieldCheck } from 'lucide-vue-next'
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

import EventGroupAvailability from '@/components/event-groups/EventGroupAvailability.vue'
import EventGroupEditForm from '@/components/event-groups/EventGroupEditForm.vue'
import EventGroupEvents from '@/components/event-groups/EventGroupEvents.vue'
import EventGroupHeader from '@/components/event-groups/EventGroupHeader.vue'
import EventGroupManagers from '@/components/event-groups/EventGroupManagers.vue'
import AvailabilityDialog from '@/components/events/AvailabilityDialog.vue'
import ChipNav from '@/components/utils/ChipNav.vue'

import type {
  EventGroupRead,
  EventListResponse,
  EventRead,
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

const canManageGroup = computed(() => authStore.canManageGroup(groupId.value))

const group = ref<EventGroupRead | null>(null)
const groupEvents = ref<EventRead[]>([])
const myAvailability = ref<UserAvailabilityRead | null>(null)
const allAvailabilities = ref<UserAvailabilityWithUser[]>([])
const loading = ref(false)
const showAvailabilityDialog = ref(false)
const groupManagers = ref<UserRead[]>([])

// ── Navigation ──
const navItems = computed<NavItem[]>(() => [
  { id: 'events', label: t('duties.eventGroups.detail.nav.events'), icon: ListTodo },
  {
    id: 'availability',
    label: t('duties.eventGroups.detail.nav.availability'),
    icon: CalendarCheck,
  },
  {
    id: 'details',
    label: t('duties.eventGroups.detail.nav.details'),
    icon: Pencil,
    adminOnly: true,
  },
  {
    id: 'management',
    label: t('duties.eventGroups.detail.nav.management'),
    icon: ShieldCheck,
    adminOnly: true,
  },
])

const visibleNavItems = computed(() =>
  navItems.value.filter((item) => !item.adminOnly || canManageGroup.value),
)

const chipItems = computed(() =>
  visibleNavItems.value.map((item) => ({ label: item.label, icon: item.icon })),
)

const validSectionIds = computed(() => visibleNavItems.value.map((item) => item.id))

const activeSection = computed({
  get: () => {
    const param = route.params.section as string | undefined
    if (param && validSectionIds.value.includes(param)) return param
    return 'events'
  },
  set: (id: string) => {
    router.replace({
      name: 'event-group-detail',
      params: {
        groupId: groupId.value,
        section: id === 'events' ? undefined : id,
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

// ── Data loading ──
const handleGroupUpdated = (updated: EventGroupRead) => {
  group.value = updated
  activeSection.value = 'events'
  breadcrumbStore.setDynamicTitle(updated.name)
}

const handleStatusChange = async (status: 'draft' | 'published' | 'archived') => {
  if (!group.value || group.value.status === status) return
  try {
    const res = await patch<{ data: EventGroupRead }>({
      url: `/event-groups/${groupId.value}`,
      body: { status },
    })
    group.value = res.data
    toast.success(t(`duties.eventGroups.statuses.${status}`))
  } catch (error) {
    toastApiError(error)
  }
}

const loadManagers = async () => {
  try {
    const res = await get<{ data: UserRead[] }>({
      url: `/event-groups/${groupId.value}/managers`,
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
    const [groupRes, eventsRes] = await Promise.all([
      get<{ data: EventGroupRead }>({ url: `/event-groups/${groupId.value}` }),
      get<{ data: EventListResponse }>({ url: '/events/', query: { limit: 200 } }),
    ])
    group.value = groupRes.data
    groupEvents.value = eventsRes.data.items.filter(
      (e: EventRead) => e.event_group_id === groupId.value,
    )

    breadcrumbStore.setDynamicTitle(group.value.name)

    try {
      const availRes = await get<{ data: UserAvailabilityRead }>({
        url: `/event-groups/${groupId.value}/availability/me`,
      })
      myAvailability.value = availRes.data
    } catch {
      myAvailability.value = null
    }

    if (canManageGroup.value) {
      await loadManagers()
    }

    if (canManageGroup.value) {
      try {
        const adminRes = await get<{ data: UserAvailabilityWithUser[] }>({
          url: `/event-groups/${groupId.value}/availabilities`,
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
      url: `/event-groups/${groupId.value}/availability`,
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
    if (canManageGroup.value) {
      const adminRes = await get<{ data: UserAvailabilityWithUser[] }>({
        url: `/event-groups/${groupId.value}/availabilities`,
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
    await del({ url: `/event-groups/${groupId.value}/availability/me` })
    myAvailability.value = null
    toast.success(t('duties.availability.remove'))
    if (canManageGroup.value) {
      const adminRes = await get<{ data: UserAvailabilityWithUser[] }>({
        url: `/event-groups/${groupId.value}/availabilities`,
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
      <EventGroupEvents
        v-if="id === 'events'"
        :events="groupEvents"
        :group-id="groupId"
        :can-manage="canManageGroup"
      />

      <EventGroupAvailability
        v-if="id === 'availability'"
        :my-availability="myAvailability"
        :all-availabilities="allAvailabilities"
        :can-manage="canManageGroup"
        @edit="showAvailabilityDialog = true"
        @remove="handleRemoveAvailability"
      />

      <EventGroupEditForm
        v-if="id === 'details'"
        :group="group!"
        :group-id="groupId"
        :events="groupEvents"
        @updated="handleGroupUpdated"
        @cancel="activeSection = 'events'"
      />

      <EventGroupManagers
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
        variant="ghost"
        size="sm"
        data-testid="btn-back"
        @click="router.push({ name: 'event-groups' })"
      >
        <ArrowLeft class="mr-2 h-4 w-4" />
        {{ t('duties.eventGroups.title') }}
      </Button>

      <div v-if="loading" class="py-12 text-center text-muted-foreground">
        {{ t('common.states.loading') }}
      </div>

      <template v-else-if="group">
        <EventGroupHeader
          :group="group"
          :group-id="groupId"
          :can-manage="canManageGroup"
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
