<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import type { DateValue } from '@internationalized/date'
import { parseDate } from '@internationalized/date'
import { ArrowLeft, CalendarDays, Check, Pencil, Trash2, UserCheck, Users } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import type {
  EventGroupRead,
  EventListResponse,
  EventRead,
  UserAvailabilityRead,
  UserAvailabilityWithUser,
} from '@/client/types.gen'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import { DatePicker } from '@/components/ui/date-picker'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import Input from '@/components/ui/input/Input.vue'
import Label from '@/components/ui/label/Label.vue'
import Separator from '@/components/ui/separator/Separator.vue'
import Textarea from '@/components/ui/textarea/Textarea.vue'
import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { useDialog } from '@/composables/useDialog'
import { toastApiError } from '@/lib/api-errors'
import { useAuthStore } from '@/stores/auth'
import { useBreadcrumbStore } from '@/stores/breadcrumb'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const breadcrumbStore = useBreadcrumbStore()
const { get, post, delete: del } = useAuthenticatedClient()
const { confirmDestructive } = useDialog()

const groupId = computed(() => route.params.groupId as string)
const group = ref<EventGroupRead | null>(null)
const groupEvents = ref<EventRead[]>([])
const myAvailability = ref<UserAvailabilityRead | null>(null)
const allAvailabilities = ref<UserAvailabilityWithUser[]>([])
const loading = ref(false)

// Availability form
const showAvailabilityDialog = ref(false)
const availabilityForm = ref({
  availability_type: 'fully_available' as 'fully_available' | 'specific_dates',
  notes: '',
})
const availabilityDateValues = ref<(DateValue | undefined)[]>([])

const formatDate = (dateStr: string) => new Date(dateStr).toLocaleDateString()

const statusVariant = (status?: string) => {
  switch (status) {
    case 'published':
      return 'default'
    case 'draft':
      return 'secondary'
    case 'archived':
      return 'outline'
    default:
      return 'secondary'
  }
}

const loadGroup = async () => {
  loading.value = true
  try {
    const [groupRes, eventsRes] = await Promise.all([
      get<{ data: EventGroupRead }>({ url: `/event-groups/${groupId.value}` }),
      get<{ data: EventListResponse }>({ url: '/events/', query: { limit: 200 } }),
    ])
    group.value = groupRes.data
    // Filter events that belong to this group
    groupEvents.value = eventsRes.data.items.filter(
      (e: EventRead) => e.event_group_id === groupId.value,
    )

    breadcrumbStore.setDynamicTitle(group.value.name)

    // Load my availability (may 404 if not registered)
    try {
      const availRes = await get<{ data: UserAvailabilityRead }>({
        url: `/event-groups/${groupId.value}/availability/me`,
      })
      myAvailability.value = availRes.data
    } catch {
      myAvailability.value = null
    }

    // Admin: load all availabilities
    if (authStore.isAdmin) {
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

const openAvailabilityDialog = () => {
  if (myAvailability.value) {
    availabilityForm.value = {
      availability_type: myAvailability.value.availability_type as
        | 'fully_available'
        | 'specific_dates',
      notes: myAvailability.value.notes ?? '',
    }
    availabilityDateValues.value = myAvailability.value.available_dates.map((d) =>
      parseDate(d.slot_date),
    )
  } else {
    availabilityForm.value = { availability_type: 'fully_available', notes: '' }
    availabilityDateValues.value = []
  }
  showAvailabilityDialog.value = true
}

const handleSaveAvailability = async () => {
  try {
    const res = await post<{ data: UserAvailabilityRead }>({
      url: `/event-groups/${groupId.value}/availability`,
      body: {
        availability_type: availabilityForm.value.availability_type,
        notes: availabilityForm.value.notes || undefined,
        dates:
          availabilityForm.value.availability_type === 'specific_dates'
            ? availabilityDateValues.value.filter(Boolean).map((d) => d!.toString())
            : [],
      },
    })
    myAvailability.value = res.data
    showAvailabilityDialog.value = false
    toast.success(t('duties.availability.update'))
    // Refresh admin list too
    if (authStore.isAdmin) {
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
    if (authStore.isAdmin) {
      const adminRes = await get<{ data: UserAvailabilityWithUser[] }>({
        url: `/event-groups/${groupId.value}/availabilities`,
      })
      allAvailabilities.value = adminRes.data
    }
  } catch (error) {
    toastApiError(error)
  }
}

const addDateField = () => {
  availabilityDateValues.value.push(undefined)
}

const removeDateField = (idx: number) => {
  availabilityDateValues.value.splice(idx, 1)
}

const navigateToEvent = (event: EventRead) => {
  router.push({ name: 'event-detail', params: { eventId: event.id } })
}

onMounted(loadGroup)
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-6">
    <!-- Back -->
    <Button variant="ghost" size="sm" @click="router.push({ name: 'event-groups' })">
      <ArrowLeft class="mr-2 h-4 w-4" />
      {{ t('duties.eventGroups.title') }}
    </Button>

    <div v-if="loading" class="py-12 text-center text-muted-foreground">
      {{ t('common.states.loading') }}
    </div>

    <template v-else-if="group">
      <!-- Group Header -->
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-1">
          <div class="flex items-center gap-3">
            <h1 class="text-3xl font-bold">{{ group.name }}</h1>
            <Badge :variant="statusVariant(group.status)">
              {{ t(`duties.eventGroups.statuses.${group.status ?? 'draft'}`) }}
            </Badge>
          </div>
          <p v-if="group.description" class="text-muted-foreground">{{ group.description }}</p>
          <p class="text-sm text-muted-foreground">
            <CalendarDays class="mr-1 inline h-3.5 w-3.5" />
            {{ formatDate(group.start_date) }} – {{ formatDate(group.end_date) }}
          </p>
        </div>
      </div>

      <Separator />

      <!-- My Availability -->
      <Card>
        <CardHeader>
          <div class="flex items-center justify-between">
            <div class="space-y-1">
              <CardTitle class="flex items-center gap-2">
                <UserCheck class="h-5 w-5" />
                {{ t('duties.availability.title') }}
              </CardTitle>
              <CardDescription>{{ t('duties.availability.subtitle') }}</CardDescription>
            </div>
            <div class="flex gap-2">
              <Button v-if="myAvailability" variant="outline" size="sm" @click="openAvailabilityDialog">
                <Pencil class="mr-2 h-4 w-4" />
                {{ t('duties.availability.update') }}
              </Button>
              <Button v-if="myAvailability" variant="ghost" size="sm" class="text-destructive" @click="handleRemoveAvailability">
                <Trash2 class="mr-1.5 h-4 w-4" />
                {{ t('duties.availability.remove') }}
              </Button>
              <Button v-if="!myAvailability" @click="openAvailabilityDialog">
                <Check class="mr-2 h-4 w-4" />
                {{ t('duties.availability.register') }}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div v-if="myAvailability" class="space-y-2">
            <div class="flex items-center gap-2">
              <Badge variant="secondary">
                {{ t(`duties.availability.types.${myAvailability.availability_type}`) }}
              </Badge>
            </div>
            <div
              v-if="myAvailability.availability_type === 'specific_dates' && myAvailability.available_dates.length"
              class="flex flex-wrap gap-1"
            >
              <Badge
                v-for="d in myAvailability.available_dates"
                :key="d.id"
                variant="outline"
                class="text-xs"
              >
                {{ formatDate(d.slot_date) }}
              </Badge>
            </div>
            <p v-if="myAvailability.notes" class="text-sm text-muted-foreground">
              {{ myAvailability.notes }}
            </p>
          </div>
          <p v-else class="text-sm text-muted-foreground">
            {{ t('duties.availability.notRegistered') }}
          </p>
        </CardContent>
      </Card>

      <!-- Events in group -->
      <div class="space-y-3">
        <h2 class="text-xl font-semibold">{{ t('duties.eventGroups.detail.events') }}</h2>
        <p v-if="groupEvents.length === 0" class="text-sm text-muted-foreground">
          {{ t('duties.eventGroups.detail.eventsEmpty') }}
        </p>
        <div v-else class="grid gap-3 sm:grid-cols-2">
          <Card
            v-for="event in groupEvents"
            :key="event.id"
            class="cursor-pointer transition-colors hover:bg-muted/50"
            @click="navigateToEvent(event)"
          >
            <CardHeader class="pb-2">
              <div class="flex items-start justify-between">
                <CardTitle class="text-base">{{ event.name }}</CardTitle>
                <Badge :variant="statusVariant(event.status)">
                  {{ t(`duties.events.statuses.${event.status ?? 'draft'}`) }}
                </Badge>
              </div>
              <CardDescription v-if="event.description">{{ event.description }}</CardDescription>
            </CardHeader>
            <CardContent>
              <p class="text-sm text-muted-foreground">
                {{ formatDate(event.start_date) }} – {{ formatDate(event.end_date) }}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      <!-- Admin: all member availabilities -->
      <template v-if="authStore.isAdmin">
        <Separator />
        <div class="space-y-3">
          <h2 class="flex items-center gap-2 text-xl font-semibold">
            <Users class="h-5 w-5" />
            {{ t('duties.availability.adminTitle') }}
          </h2>
          <p v-if="allAvailabilities.length === 0" class="text-sm text-muted-foreground">
            {{ t('duties.availability.adminEmpty') }}
          </p>
          <div v-else class="overflow-hidden rounded-lg border">
            <table class="w-full text-sm">
              <thead class="bg-muted/50">
                <tr>
                  <th class="px-4 py-2 text-left font-medium">User</th>
                  <th class="px-4 py-2 text-left font-medium">
                    {{ t('duties.availability.fields.type') }}
                  </th>
                  <th class="px-4 py-2 text-left font-medium">
                    {{ t('duties.availability.fields.dates') }}
                  </th>
                  <th class="px-4 py-2 text-left font-medium">
                    {{ t('duties.availability.fields.notes') }}
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y">
                <tr v-for="avail in allAvailabilities" :key="avail.id" class="hover:bg-muted/30">
                  <td class="px-4 py-2">
                    <div>{{ avail.user_full_name ?? '—' }}</div>
                    <div class="text-xs text-muted-foreground">{{ avail.user_email ?? '' }}</div>
                  </td>
                  <td class="px-4 py-2">
                    <Badge variant="secondary">
                      {{ t(`duties.availability.types.${avail.availability_type}`) }}
                    </Badge>
                  </td>
                  <td class="px-4 py-2">
                    <span
                      v-if="avail.availability_type === 'specific_dates' && avail.available_dates?.length"
                    >
                      <span class="text-xs">
                        {{ avail.available_dates.map((d) => formatDate(d.slot_date)).join(', ') }}
                      </span>
                    </span>
                    <span v-else class="text-muted-foreground">—</span>
                  </td>
                  <td class="px-4 py-2 text-muted-foreground">{{ avail.notes ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </template>

    <!-- Availability Dialog -->
    <Dialog v-model:open="showAvailabilityDialog">
      <DialogContent class="max-w-md">
        <DialogHeader>
          <DialogTitle>{{ t('duties.availability.title') }}</DialogTitle>
          <DialogDescription>{{ t('duties.availability.subtitle') }}</DialogDescription>
        </DialogHeader>
        <form class="space-y-4" @submit.prevent="handleSaveAvailability">
          <!-- Type selection -->
          <div class="space-y-2">
            <Label>{{ t('duties.availability.fields.type') }}</Label>
            <div class="grid grid-cols-2 gap-2">
              <button
                type="button"
                class="rounded-lg border-2 p-3 text-left text-sm transition-colors"
                :class="
                  availabilityForm.availability_type === 'fully_available'
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-muted-foreground'
                "
                @click="availabilityForm.availability_type = 'fully_available'"
              >
                <div class="font-medium">
                  {{ t('duties.availability.types.fully_available') }}
                </div>
              </button>
              <button
                type="button"
                class="rounded-lg border-2 p-3 text-left text-sm transition-colors"
                :class="
                  availabilityForm.availability_type === 'specific_dates'
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-muted-foreground'
                "
                @click="availabilityForm.availability_type = 'specific_dates'"
              >
                <div class="font-medium">
                  {{ t('duties.availability.types.specific_dates') }}
                </div>
              </button>
            </div>
          </div>

          <!-- Specific dates -->
          <div v-if="availabilityForm.availability_type === 'specific_dates'" class="space-y-2">
            <Label>{{ t('duties.availability.fields.dates') }}</Label>
            <div class="space-y-2">
              <div
                v-for="(_, idx) in availabilityDateValues"
                :key="idx"
                class="flex items-center gap-2"
              >
                <DatePicker
                  :model-value="availabilityDateValues[idx]"
                  :placeholder="t('duties.eventGroups.pickDate')"
                  class="flex-1"
                  @update:model-value="(val) => availabilityDateValues[idx] = val"
                />
                <Button type="button" variant="ghost" size="icon" @click="removeDateField(idx)">
                  <Trash2 class="h-4 w-4 text-destructive" />
                </Button>
              </div>
              <Button type="button" variant="outline" size="sm" @click="addDateField">
                + {{ t('duties.availability.fields.dates') }}
              </Button>
            </div>
          </div>

          <!-- Notes -->
          <div class="space-y-2">
            <Label>{{ t('duties.availability.fields.notes') }}</Label>
            <Textarea v-model="availabilityForm.notes" rows="2" />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" @click="showAvailabilityDialog = false">
              {{ t('common.actions.cancel') }}
            </Button>
            <Button type="submit">{{ t('common.actions.save') }}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  </div>
</template>
