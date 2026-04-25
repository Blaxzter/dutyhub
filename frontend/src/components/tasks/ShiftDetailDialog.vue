<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { Clock, EllipsisVertical, ExternalLink, MapPin, Users } from '@respeak/lucide-motion-vue'
import { Calendar, Tag } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { useAuthStore } from '@/stores/auth'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { useDialog } from '@/composables/useDialog'
import { useFormatters } from '@/composables/useFormatters'

import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import Separator from '@/components/ui/separator/Separator.vue'

import ShiftBookingsTable from '@/components/tasks/ShiftBookingsTable.vue'

import type { BookingRead, ShiftBookingEntry, ShiftRead } from '@/client/types.gen'
import { toastApiError } from '@/lib/api-errors'

const props = withDefaults(
  defineProps<{
    /** Pass a full shift object (from TaskDetailView) */
    shift?: ShiftRead | null
    /** Or pass just an ID to fetch the shift (from MyBookingsView) */
    slotId?: string | null
    eventName?: string | null
    /** The current user's booking for this shift (enables booking link) */
    myBooking?: BookingRead | null
    /** Whether to show the "View Task" navigation link (hide when already on task page) */
    showTaskLink?: boolean
    open: boolean
  }>(),
  { showTaskLink: true },
)

const emit = defineEmits<{
  'update:open': [value: boolean]
  'booking-updated': []
}>()

const { t } = useI18n()
const { formatTime, formatDateLabel } = useFormatters()
const router = useRouter()
const { get, post, delete: del } = useAuthenticatedClient()
const { confirmDestructive } = useDialog()
const authStore = useAuthStore()

const fetchedShift = ref<ShiftRead | null>(null)
const slotBookings = ref<ShiftBookingEntry[]>([])
const loadingShift = ref(false)
const loadingBookings = ref(false)

const dialogOpen = computed({
  get: () => props.open,
  set: (v) => emit('update:open', v),
})

/** The resolved shift — either from props or fetched by ID */
const resolvedShift = computed(() => props.shift ?? fetchedShift.value)

/** The resolved booking — from props, or auto-detected from fetched shift bookings */
const resolvedMyBooking = computed(() => {
  if (props.myBooking) return props.myBooking
  const email = authStore.user?.email
  if (!email || slotBookings.value.length === 0) return null
  const entry = slotBookings.value.find((b) => b.user_email === email)
  if (!entry) return null
  return { id: entry.id, notes: entry.notes ?? null } as { id: string; notes: string | null }
})

// Load data when dialog opens
watch(
  () => props.open,
  async (isOpen) => {
    if (!isOpen) {
      slotBookings.value = []
      fetchedShift.value = null
      return
    }

    // If we only have a slotId, fetch the full shift
    const slotId = props.shift?.id ?? props.slotId
    if (!props.shift && props.slotId) {
      loadingShift.value = true
      try {
        const response = await get<{ data: ShiftRead }>({
          url: `/shifts/${props.slotId}`,
        })
        fetchedShift.value = response.data
      } catch {
        fetchedShift.value = null
      } finally {
        loadingShift.value = false
      }
    }

    // Load bookings
    if (slotId) {
      loadingBookings.value = true
      try {
        const response = await get<{ data: ShiftBookingEntry[] }>({
          url: `/shifts/${slotId}/bookings`,
        })
        slotBookings.value = response.data
      } catch {
        slotBookings.value = []
      } finally {
        loadingBookings.value = false
      }
    }
  },
)

const timeDisplay = computed(() => {
  const s = resolvedShift.value
  if (!s) return null
  const parts: string[] = []
  if (s.start_time) parts.push(formatTime(s.start_time))
  if (s.end_time) parts.push(formatTime(s.end_time))
  return parts.length > 0 ? parts.join(' – ') : null
})

const isShiftFull = computed(() => {
  const s = resolvedShift.value
  if (!s) return true
  return (s.current_bookings ?? 0) >= (s.max_bookings ?? 1)
})

const canBook = computed(() => {
  return !resolvedMyBooking.value && !isShiftFull.value
})

const hasMenuItems = computed(() => {
  return (props.showTaskLink && !!resolvedShift.value?.task_id) || !!resolvedMyBooking.value
})

const bookingInProgress = ref(false)

const handleBook = async () => {
  const shift = resolvedShift.value
  if (!shift || isShiftFull.value) return
  bookingInProgress.value = true
  try {
    await post({ url: '/bookings/', body: { shift_id: shift.id } })
    toast.success(t('duties.bookings.bookSuccess'))
    emit('booking-updated')
    dialogOpen.value = false
  } catch (error) {
    toastApiError(error)
  } finally {
    bookingInProgress.value = false
  }
}

const handleCancelBooking = async () => {
  if (!resolvedMyBooking.value) return
  const confirmed = await confirmDestructive(t('duties.bookings.cancelConfirm'))
  if (!confirmed) return
  bookingInProgress.value = true
  try {
    await del({ url: `/bookings/${resolvedMyBooking.value.id}` })
    toast.success(t('duties.bookings.cancelSuccess'))
    emit('booking-updated')
    dialogOpen.value = false
  } catch (error) {
    toastApiError(error)
  } finally {
    bookingInProgress.value = false
  }
}

const navigateToTask = () => {
  const eventId = resolvedShift.value?.task_id
  if (eventId) {
    dialogOpen.value = false
    router.push({ name: 'task-detail', params: { eventId } })
  }
}

const navigateToBooking = () => {
  const booking = resolvedMyBooking.value
  if (booking) {
    dialogOpen.value = false
    router.push({ name: 'booking-detail', params: { bookingId: booking.id } })
  }
}
</script>

<template>
  <Dialog v-model:open="dialogOpen">
    <DialogContent class="sm:max-w-lg max-h-[85vh] overflow-y-auto">
      <DialogHeader>
        <div class="flex items-center justify-between gap-2 pr-6">
          <DialogTitle>{{ t('duties.shifts.detail.title') }}</DialogTitle>
          <Badge v-if="resolvedShift" variant="outline" class="text-xs shrink-0">
            {{ resolvedShift.current_bookings ?? 0 }} / {{ resolvedShift.max_bookings ?? 1 }}
          </Badge>
        </div>
        <DialogDescription v-if="eventName">
          {{ eventName }}
        </DialogDescription>
      </DialogHeader>

      <!-- Loading state when fetching shift by ID -->
      <div v-if="loadingShift" class="text-center py-8 text-muted-foreground">
        {{ t('common.states.loading') }}
      </div>

      <template v-else-if="resolvedShift">
        <!-- Shift info grid -->
        <div class="space-y-4">
          <!-- Date & Time -->
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="flex items-start gap-2.5">
              <Calendar class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              <div>
                <p class="text-xs text-muted-foreground">
                  {{ t('duties.shifts.detail.date') }}
                </p>
                <p class="text-sm font-medium">
                  {{
                    formatDateLabel(resolvedShift.date, {
                      weekday: 'long',
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })
                  }}
                </p>
              </div>
            </div>
            <div v-if="timeDisplay" class="flex items-start gap-2.5">
              <Clock
                class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
                animateOnHover
                triggerTarget="parent"
              />
              <div>
                <p class="text-xs text-muted-foreground">
                  {{ t('duties.shifts.detail.time') }}
                </p>
                <p class="text-sm font-medium font-mono">{{ timeDisplay }}</p>
              </div>
            </div>
          </div>

          <!-- Location & Category -->
          <div
            v-if="resolvedShift.location || resolvedShift.category"
            class="grid gap-3 sm:grid-cols-2"
          >
            <div v-if="resolvedShift.location" class="flex items-start gap-2.5">
              <MapPin
                class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
                animateOnHover
                triggerTarget="parent"
              />
              <div>
                <p class="text-xs text-muted-foreground">
                  {{ t('duties.shifts.detail.location') }}
                </p>
                <p class="text-sm font-medium">{{ resolvedShift.location }}</p>
              </div>
            </div>
            <div v-if="resolvedShift.category" class="flex items-start gap-2.5">
              <Tag class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              <div>
                <p class="text-xs text-muted-foreground">
                  {{ t('duties.shifts.detail.category') }}
                </p>
                <p class="text-sm font-medium">{{ resolvedShift.category }}</p>
              </div>
            </div>
          </div>

          <!-- Capacity -->
          <div class="flex items-start gap-2.5">
            <Users
              class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
              animateOnHover
              triggerTarget="parent"
            />
            <div>
              <p class="text-xs text-muted-foreground">
                {{ t('duties.shifts.detail.capacity') }}
              </p>
              <p class="text-sm font-medium">
                {{
                  t('duties.shifts.detail.capacityValue', {
                    current: resolvedShift.current_bookings ?? 0,
                    max: resolvedShift.max_bookings ?? 1,
                  })
                }}
              </p>
            </div>
          </div>

          <!-- Description -->
          <div v-if="resolvedShift.description">
            <p class="text-xs text-muted-foreground mb-1">
              {{ t('duties.shifts.detail.description') }}
            </p>
            <p class="text-sm whitespace-pre-line">{{ resolvedShift.description }}</p>
          </div>

          <!-- Extensibility shift: future fields (materials, protection, etc.) go here -->
          <slot name="extra-details" />

          <Separator />

          <!-- Booked users table -->
          <div>
            <h3 class="text-sm font-semibold mb-2">
              {{ t('duties.shifts.detail.bookedUsers') }}
            </h3>
            <ShiftBookingsTable :bookings="slotBookings" :loading="loadingBookings" />
          </div>

          <!-- Extensibility shift: additional sections below the table -->
          <slot name="extra-sections" />
        </div>

        <!-- Footer actions -->
        <div class="flex items-center justify-end gap-2 pt-2">
          <DropdownMenu v-if="hasMenuItems">
            <DropdownMenuTrigger as-child>
              <Button variant="outline" size="sm" class="h-8 w-8 p-0">
                <EllipsisVertical class="h-4 w-4" animateOnHover triggerTarget="parent" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuItem
                v-if="showTaskLink && resolvedShift?.task_id"
                @click="navigateToTask"
              >
                <ExternalLink class="mr-2 h-4 w-4" animateOnHover triggerTarget="parent" />
                {{ t('duties.shifts.detail.viewTask') }}
              </DropdownMenuItem>
              <DropdownMenuItem v-if="resolvedMyBooking" @click="navigateToBooking">
                <ExternalLink class="mr-2 h-4 w-4" animateOnHover triggerTarget="parent" />
                {{ t('duties.shifts.detail.openBookingDetails') }}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <div class="flex-1" />

          <Button v-if="canBook" size="sm" :disabled="bookingInProgress" @click="handleBook">
            {{ t('duties.shifts.book') }}
          </Button>
          <Button
            v-if="resolvedMyBooking"
            variant="destructive"
            size="sm"
            :disabled="bookingInProgress"
            @click="handleCancelBooking"
          >
            {{ t('duties.bookings.cancel') }}
          </Button>
        </div>
      </template>
    </DialogContent>
  </Dialog>
</template>
