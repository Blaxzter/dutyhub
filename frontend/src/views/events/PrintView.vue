<script setup lang="ts">
import { computed } from 'vue'

import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'

import EventPrint from '@/components/events/EventPrint.vue'

const { t } = useI18n()
const authStore = useAuthStore()

const eventId = computed(() => authStore.selectedEventId ?? null)
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-6">
    <div class="space-y-2">
      <h1 data-testid="page-heading" class="text-2xl sm:text-3xl font-bold">
        {{ t('duties.events.detail.nav.print') }}
      </h1>
      <p class="text-muted-foreground">
        {{ authStore.selectedEvent?.name ?? '' }}
      </p>
    </div>

    <EventPrint v-if="eventId" :event-id="eventId" />
  </div>
</template>
