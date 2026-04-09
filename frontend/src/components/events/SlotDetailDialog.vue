<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import {
  Calendar,
  Clock,
  EllipsisVertical,
  ExternalLink,
  MapPin,
  Tag,
  Users,
} from 'lucide-vue-next'
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

import SlotBookingsTable from '@/components/events/SlotBookingsTable.vue'

import type { BookingRead, DutySlotRead, SlotBookingEntry } from '@/client/types.gen'
import { toastApiError } from '@/lib/api-errors'

const props = withDefaults(
  defineProps<{
    /** Pass a full slot object (from EventDetailView) */
    dutySlot?: DutySlotRead | null
    /** Or pass just an ID to fetch the slot (from MyBookingsView) */
    slotId?: string | null
    eventName?: string | null
    /** The current user's booking for this slot (enables booking link) */
    myBooking?: BookingRead | null
    /** Whether to show the "View Event" navigation link (hide when already on event page) */
    showEventLink?: boolean
    open: boolean
  }>(),
  { showEventLink: true },
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

const fetchedSlot = ref<DutySlotRead | null>(null)
const slotBookings = ref<SlotBookingEntry[]>([])
const loadingSlot = ref(false)
const loadingBookings = ref(false)

const dialogOpen = computed({
  get: () => props.open,
  set: (v) => emit('update:open', v),
})

/** The resolved slot — either from props or fetched by ID */
const resolvedSlot = computed(() => props.dutySlot ?? fetchedSlot.value)

/** The resolved booking — from props, or auto-detected from fetched slot bookings */
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
      fetchedSlot.value = null
      return
    }

    // If we only have a slotId, fetch the full slot
    const slotId = props.dutySlot?.id ?? props.slotId
    if (!props.dutySlot && props.slotId) {
      loadingSlot.value = true
      try {
        const response = await get<{ data: DutySlotRead }>({
          url: `/duty-slots/${props.slotId}`,
        })
        fetchedSlot.value = response.data
      } catch {
        fetchedSlot.value = null
      } finally {
        loadingSlot.value = false
      }
    }

    // Load bookings
    if (slotId) {
      loadingBookings.value = true
      try {
        const response = await get<{ data: SlotBookingEntry[] }>({
          url: `/duty-slots/${slotId}/bookings`,
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
  const s = resolvedSlot.value
  if (!s) return null
  const parts: string[] = []
  if (s.start_time) parts.push(formatTime(s.start_time))
  if (s.end_time) parts.push(formatTime(s.end_time))
  return parts.length > 0 ? parts.join(' – ') : null
})

const isSlotFull = computed(() => {
  const s = resolvedSlot.value
  if (!s) return true
  return (s.current_bookings ?? 0) >= (s.max_bookings ?? 1)
})

const canBook = computed(() => {
  return !resolvedMyBooking.value && !isSlotFull.value
})

const hasMenuItems = computed(() => {
  return (props.showEventLink && !!resolvedSlot.value?.event_id) || !!resolvedMyBooking.value
})

const bookingInProgress = ref(false)

const handleBook = async () => {
  const slot = resolvedSlot.value
  if (!slot || isSlotFull.value) return
  bookingInProgress.value = true
  try {
    await post({ url: '/bookings/', body: { duty_slot_id: slot.id } })
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

const navigateToEvent = () => {
  const eventId = resolvedSlot.value?.event_id
  if (eventId) {
    dialogOpen.value = false
    router.push({ name: 'event-detail', params: { eventId } })
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
          <DialogTitle>{{ t('duties.dutySlots.detail.title') }}</DialogTitle>
          <Badge v-if="resolvedSlot" variant="outline" class="text-xs shrink-0">
            {{ resolvedSlot.current_bookings ?? 0 }} / {{ resolvedSlot.max_bookings ?? 1 }}
          </Badge>
        </div>
        <DialogDescription v-if="eventName">
          {{ eventName }}
        </DialogDescription>
      </DialogHeader>

      <!-- Loading state when fetching slot by ID -->
      <div v-if="loadingSlot" class="text-center py-8 text-muted-foreground">
        {{ t('common.states.loading') }}
      </div>

      <template v-else-if="resolvedSlot">
        <!-- Slot info grid -->
        <div class="space-y-4">
          <!-- Date & Time -->
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="flex items-start gap-2.5">
              <Calendar class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              <div>
                <p class="text-xs text-muted-foreground">
                  {{ t('duties.dutySlots.detail.date') }}
                </p>
                <p class="text-sm font-medium">
                  {{
                    formatDateLabel(resolvedSlot.date, {
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
              <Clock class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              <div>
                <p class="text-xs text-muted-foreground">
                  {{ t('duties.dutySlots.detail.time') }}
                </p>
                <p class="text-sm font-medium font-mono">{{ timeDisplay }}</p>
              </div>
            </div>
          </div>

          <!-- Location & Category -->
          <div
            v-if="resolvedSlot.location || resolvedSlot.category"
            class="grid gap-3 sm:grid-cols-2"
          >
            <div v-if="resolvedSlot.location" class="flex items-start gap-2.5">
              <MapPin class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              <div>
                <p class="text-xs text-muted-foreground">
                  {{ t('duties.dutySlots.detail.location') }}
                </p>
                <p class="text-sm font-medium">{{ resolvedSlot.location }}</p>
              </div>
            </div>
            <div v-if="resolvedSlot.category" class="flex items-start gap-2.5">
              <Tag class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              <div>
                <p class="text-xs text-muted-foreground">
                  {{ t('duties.dutySlots.detail.category') }}
                </p>
                <p class="text-sm font-medium">{{ resolvedSlot.category }}</p>
              </div>
            </div>
          </div>

          <!-- Capacity -->
          <div class="flex items-start gap-2.5">
            <Users class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <div>
              <p class="text-xs text-muted-foreground">
                {{ t('duties.dutySlots.detail.capacity') }}
              </p>
              <p class="text-sm font-medium">
                {{
                  t('duties.dutySlots.detail.capacityValue', {
                    current: resolvedSlot.current_bookings ?? 0,
                    max: resolvedSlot.max_bookings ?? 1,
                  })
                }}
              </p>
            </div>
          </div>

          <!-- Description -->
          <div v-if="resolvedSlot.description">
            <p class="text-xs text-muted-foreground mb-1">
              {{ t('duties.dutySlots.detail.description') }}
            </p>
            <p class="text-sm whitespace-pre-line">{{ resolvedSlot.description }}</p>
          </div>

          <!-- Extensibility slot: future fields (materials, protection, etc.) go here -->
          <slot name="extra-details" />

          <Separator />

          <!-- Booked users table -->
          <div>
            <h3 class="text-sm font-semibold mb-2">
              {{ t('duties.dutySlots.detail.bookedUsers') }}
            </h3>
            <SlotBookingsTable :bookings="slotBookings" :loading="loadingBookings" />
          </div>

          <!-- Extensibility slot: additional sections below the table -->
          <slot name="extra-sections" />
        </div>

        <!-- Footer actions -->
        <div class="flex items-center justify-end gap-2 pt-2">
          <DropdownMenu v-if="hasMenuItems">
            <DropdownMenuTrigger as-child>
              <Button variant="outline" size="sm" class="h-8 w-8 p-0">
                <EllipsisVertical class="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuItem
                v-if="showEventLink && resolvedSlot?.event_id"
                @click="navigateToEvent"
              >
                <ExternalLink class="mr-2 h-4 w-4" />
                {{ t('duties.dutySlots.detail.viewEvent') }}
              </DropdownMenuItem>
              <DropdownMenuItem v-if="resolvedMyBooking" @click="navigateToBooking">
                <ExternalLink class="mr-2 h-4 w-4" />
                {{ t('duties.dutySlots.detail.openBookingDetails') }}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <div class="flex-1" />

          <Button v-if="canBook" size="sm" :disabled="bookingInProgress" @click="handleBook">
            {{ t('duties.dutySlots.book') }}
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
