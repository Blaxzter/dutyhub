<script setup lang="ts">
import { computed } from 'vue'

import { UserRoundPlus } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'

import { avatarUrlFor } from '@/composables/useAvatarUrl'
import { useFormatters } from '@/composables/useFormatters'

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'

import type { ShiftBookingEntry } from '@/client/types.gen'

const props = defineProps<{
  bookings: ShiftBookingEntry[]
  /** `max_bookings` — how many people the shift is asking for. */
  capacity: number
  loading?: boolean
}>()

const { t } = useI18n()
const authStore = useAuthStore()
const { formatDateTime } = useFormatters()

/**
 * One summary row rather than one row per empty place: a shift asking for
 * twelve people would otherwise push everything who actually signed up off the
 * screen behind eleven identical placeholders.
 */
const freeCount = computed(() => Math.max(0, props.capacity - props.bookings.length))

const initials = (name: string | null | undefined, email: string | null | undefined): string => {
  if (name) {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }
  if (email) return email[0].toUpperCase()
  return '?'
}

const entryAvatarUrl = (entry: ShiftBookingEntry): string | null =>
  avatarUrlFor({ id: entry.user_id, avatar_etag: entry.user_avatar_etag ?? null })
</script>

<template>
  <section data-testid="shift-roster">
    <div class="mb-2 flex items-baseline justify-between gap-2">
      <h3 class="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
        {{ t('duties.shifts.detail.booked') }}
      </h3>
      <p class="text-muted-foreground text-xs">
        {{
          t('duties.shifts.detail.capacityValue', {
            current: bookings.length,
            max: capacity,
          })
        }}
      </p>
    </div>

    <p v-if="loading" class="text-muted-foreground py-2 text-sm">
      {{ t('common.states.loading') }}
    </p>

    <ul v-else class="divide-y">
      <li
        v-for="entry in bookings"
        :key="entry.id"
        class="flex items-center gap-3 py-2"
        data-testid="shift-roster-entry"
      >
        <Avatar class="size-8 shrink-0">
          <AvatarImage v-if="entryAvatarUrl(entry)" :src="entryAvatarUrl(entry)!" />
          <AvatarFallback class="text-xs">
            {{ initials(entry.user_name, entry.user_email) }}
          </AvatarFallback>
        </Avatar>

        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-medium">{{ entry.user_name ?? '—' }}</p>
          <!--
            Only an event admin has any business seeing a co-volunteer's email
            or the note they left the organiser, so both stay behind the same
            check the table they replaced used.
          -->
          <p
            v-if="authStore.isAdmin && entry.user_email"
            class="text-muted-foreground truncate text-xs"
          >
            {{ entry.user_email }}
          </p>
          <p
            v-if="authStore.isAdmin && entry.notes"
            class="text-muted-foreground truncate text-xs italic"
          >
            {{ entry.notes }}
          </p>
        </div>

        <time class="text-muted-foreground shrink-0 text-xs whitespace-nowrap">
          {{ formatDateTime(entry.created_at) }}
        </time>
      </li>

      <li v-if="freeCount > 0" class="flex items-center gap-3 py-2" data-testid="shift-roster-free">
        <span
          class="text-muted-foreground/60 flex size-8 shrink-0 items-center justify-center rounded-full border border-dashed"
        >
          <UserRoundPlus class="size-4" />
        </span>
        <p class="text-muted-foreground flex-1 text-sm">
          {{ t('duties.shifts.detail.freeSlots', { count: freeCount }, freeCount) }}
        </p>
      </li>
    </ul>
  </section>
</template>
