<script setup lang="ts">
import { Plus } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

import type { EventRead } from '@/client/types.gen'
import { formatDate } from '@/lib/format'
import { statusVariant } from '@/lib/status'

defineProps<{
  events: EventRead[]
  groupId: string
  canManage?: boolean
}>()

const { t } = useI18n()
const router = useRouter()

const navigateToEvent = (event: EventRead) => {
  router.push({ name: 'event-detail', params: { eventId: event.id } })
}
</script>

<template>
  <div data-testid="section-events" class="space-y-3">
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold">{{ t('duties.eventGroups.detail.events') }}</h2>
      <Button
        v-if="canManage"
        size="sm"
        @click="router.push({ name: 'event-create', query: { groupId } })"
      >
        <Plus class="mr-1.5 h-4 w-4" />
        {{ t('duties.events.create') }}
      </Button>
    </div>
    <p v-if="events.length === 0" class="text-sm text-muted-foreground">
      {{ t('duties.eventGroups.detail.eventsEmpty') }}
    </p>
    <div v-else class="grid gap-3 sm:grid-cols-2">
      <Card
        v-for="event in events"
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
</template>
