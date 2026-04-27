<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import type { DateValue } from '@internationalized/date'
import { Pencil, Plus, Search, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { useDialog } from '@/composables/useDialog'

import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import { DatePicker } from '@/components/ui/date-picker'
import { DateRangePicker } from '@/components/ui/date-range-picker'
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
import Textarea from '@/components/ui/textarea/Textarea.vue'

import type { EventListResponse, EventRead } from '@/client/types.gen'
import { toastApiError } from '@/lib/api-errors'
import { formatDate } from '@/lib/format'
import { statusVariant } from '@/lib/status'

const { t } = useI18n()
const router = useRouter()
const { get, post, delete: del } = useAuthenticatedClient()
const { confirmDestructive } = useDialog()

const events = ref<EventRead[]>([])
const loading = ref(false)
const searchQuery = ref('')
const showCreateDialog = ref(false)

const dateFrom = ref<string | null>(null)
const dateTo = ref<string | null>(null)
const markedDays = ref<Set<string>>(new Set())

async function handleVisibleMonth(range: { from: string; to: string }) {
  try {
    const res = await get<{ data: string[] }>({
      url: '/tasks/active-dates',
      query: { date_from: range.from, date_to: range.to, all_events: true },
    })
    markedDays.value = new Set(res.data)
  } catch {
    // non-critical
  }
}

const createForm = ref({ name: '', description: '' })
const startDate = ref<DateValue>()
const endDate = ref<DateValue>()

const filteredEvents = computed(() => {
  if (!searchQuery.value) return events.value
  const query = searchQuery.value.toLowerCase()
  return events.value.filter(
    (g) => g.name.toLowerCase().includes(query) || g.description?.toLowerCase().includes(query),
  )
})

const loadEvents = async () => {
  loading.value = true
  try {
    const query: Record<string, unknown> = { limit: 200 }
    if (dateFrom.value) query.date_from = dateFrom.value
    if (dateTo.value) query.date_to = dateTo.value

    const response = await get<{ data: EventListResponse }>({
      url: '/events/',
      query,
    })
    events.value = response.data.items
  } catch (error) {
    toastApiError(error)
  } finally {
    loading.value = false
  }
}

watch([dateFrom, dateTo], () => loadEvents())

const handleCreate = async () => {
  if (!startDate.value || !endDate.value) return
  try {
    await post({
      url: '/events/',
      body: {
        name: createForm.value.name,
        description: createForm.value.description || undefined,
        start_date: startDate.value.toString(),
        end_date: endDate.value.toString(),
      },
    })
    showCreateDialog.value = false
    createForm.value = { name: '', description: '' }
    startDate.value = undefined
    endDate.value = undefined
    toast.success(t('duties.events.create'))
    await loadEvents()
  } catch (error) {
    toastApiError(error)
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

const handleEdit = (event: EventRead) => {
  router.push({ name: 'event-settings', query: { eventId: event.id } })
}

onMounted(loadEvents)
</script>

<template>
  <div class="mx-auto max-w-7xl space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="space-y-2">
        <h1 data-testid="page-heading" class="text-2xl sm:text-3xl font-bold">
          {{ t('admin.events.title') }}
        </h1>
        <p class="text-muted-foreground">{{ t('admin.events.subtitle') }}</p>
      </div>
      <Button data-testid="btn-create-event" class="max-xl:hidden" @click="showCreateDialog = true">
        <Plus class="mr-2 h-4 w-4" />
        {{ t('duties.events.create') }}
      </Button>
    </div>

    <div class="flex flex-wrap items-center gap-4">
      <div class="relative flex-1">
        <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          v-model="searchQuery"
          data-testid="input-search"
          :placeholder="t('common.actions.search')"
          class="pl-10"
        />
      </div>
      <DateRangePicker
        :date-from="dateFrom"
        :date-to="dateTo"
        :marked-days="markedDays"
        @update:date-from="dateFrom = $event"
        @update:date-to="dateTo = $event"
        @update:visible-month="handleVisibleMonth"
      />
    </div>

    <div v-if="loading" class="py-12 text-center text-muted-foreground">
      {{ t('common.states.loading') }}
    </div>

    <template v-else>
      <div v-if="filteredEvents.length === 0" class="py-12 text-center text-muted-foreground">
        {{ t('duties.events.empty') }}
      </div>

      <div v-else class="overflow-hidden rounded-lg border bg-card">
        <table class="w-full text-sm">
          <thead class="bg-muted/50">
            <tr>
              <th class="px-4 py-2 text-left font-medium">{{ t('duties.events.fields.name') }}</th>
              <th class="px-4 py-2 text-left font-medium">{{ t('duties.events.fields.startDate') }}</th>
              <th class="px-4 py-2 text-left font-medium">{{ t('duties.events.fields.endDate') }}</th>
              <th class="px-4 py-2 text-left font-medium">{{ t('duties.events.fields.status') }}</th>
              <th class="px-4 py-2 text-right font-medium"></th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr
              v-for="event in filteredEvents"
              :key="event.id"
              data-testid="admin-event-row"
              class="hover:bg-muted/30"
            >
              <td class="px-4 py-2">
                <div class="font-medium">{{ event.name }}</div>
                <div v-if="event.description" class="truncate text-xs text-muted-foreground">
                  {{ event.description }}
                </div>
              </td>
              <td class="px-4 py-2">{{ formatDate(event.start_date) }}</td>
              <td class="px-4 py-2">{{ formatDate(event.end_date) }}</td>
              <td class="px-4 py-2">
                <Badge :variant="statusVariant(event.status)">
                  {{ t(`duties.events.statuses.${event.status ?? 'draft'}`) }}
                </Badge>
                <Badge v-if="event.is_expired" variant="outline" class="ml-1">
                  {{ t('duties.events.expired') }}
                </Badge>
              </td>
              <td class="px-4 py-2 text-right">
                <Button
                  variant="ghost"
                  size="icon"
                  class="h-8 w-8"
                  data-testid="btn-edit-event"
                  @click="handleEdit(event)"
                >
                  <Pencil class="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  class="h-8 w-8"
                  data-testid="btn-delete-event"
                  @click="handleDelete(event)"
                >
                  <Trash2 class="h-4 w-4 text-destructive" />
                </Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <Dialog v-model:open="showCreateDialog">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ t('duties.events.create') }}</DialogTitle>
          <DialogDescription>{{ t('duties.events.subtitle') }}</DialogDescription>
        </DialogHeader>
        <form class="space-y-4" @submit.prevent="handleCreate">
          <div class="space-y-2">
            <Label>{{ t('duties.events.fields.name') }}</Label>
            <Input v-model="createForm.name" required />
          </div>
          <div class="space-y-2">
            <Label>{{ t('duties.events.fields.description') }}</Label>
            <Textarea v-model="createForm.description" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>{{ t('duties.events.fields.startDate') }}</Label>
              <DatePicker v-model="startDate" :placeholder="t('duties.events.pickDate')" />
            </div>
            <div class="space-y-2">
              <Label>{{ t('duties.events.fields.endDate') }}</Label>
              <DatePicker v-model="endDate" :placeholder="t('duties.events.pickDate')" />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" @click="showCreateDialog = false">
              {{ t('common.actions.cancel') }}
            </Button>
            <Button type="submit">{{ t('common.actions.create') }}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>

    <Button
      size="icon"
      class="xl:hidden fixed bottom-24 md:bottom-6 right-6 z-40 h-14 w-14 rounded-full shadow-lg"
      data-testid="fab-create-event"
      :aria-label="t('duties.events.create')"
      @click="showCreateDialog = true"
    >
      <Plus class="size-7" :stroke-width="2.5" />
    </Button>
  </div>
</template>
