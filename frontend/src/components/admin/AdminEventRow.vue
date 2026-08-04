<script setup lang="ts">
import { CheckCircle2, Pencil, Trash2 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'

import type { EventRead } from '@/client/types.gen'
import { formatDate } from '@/lib/format'
import { statusVariant } from '@/lib/status'

defineProps<{
  event: EventRead
  selectedEventId: string | null
  muted?: boolean
}>()

defineEmits<{
  edit: [event: EventRead]
  delete: [event: EventRead]
}>()

const { t } = useI18n()
</script>

<template>
  <tr
    data-testid="admin-event-row"
    :data-current="event.id === selectedEventId ? 'true' : undefined"
    :class="[
      muted ? 'text-muted-foreground hover:bg-muted/30' : 'hover:bg-muted/30',
      event.id === selectedEventId ? 'bg-primary/5 border-l-2 border-l-primary' : '',
    ]"
  >
    <td class="px-4 py-2">
      <div class="flex items-center gap-2">
        <span class="font-medium" :class="muted ? 'text-foreground/80' : ''">{{ event.name }}</span>
        <Badge
          v-if="event.id === selectedEventId"
          variant="default"
          class="gap-1"
          data-testid="badge-current-event"
        >
          <CheckCircle2 class="size-3" />
          {{ t('duties.selectEvent.pick.current') }}
        </Badge>
      </div>
      <div
        v-if="event.description"
        class="truncate text-xs"
        :class="muted ? '' : 'text-muted-foreground'"
      >
        {{ event.description }}
      </div>
    </td>
    <td class="px-4 py-2">{{ formatDate(event.start_date) }}</td>
    <td class="px-4 py-2">{{ formatDate(event.end_date) }}</td>
    <td class="px-4 py-2">
      <Badge :variant="statusVariant(event.status)">
        {{ t(`duties.events.statuses.${event.status ?? 'draft'}`) }}
      </Badge>
    </td>
    <td class="px-4 py-2 text-right">
      <Button
        variant="ghost"
        size="icon"
        class="h-8 w-8"
        data-testid="btn-edit-event"
        :aria-label="t('admin.events.editEvent', { name: event.name })"
        @click="$emit('edit', event)"
      >
        <Pencil class="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        class="h-8 w-8"
        data-testid="btn-delete-event"
        :aria-label="t('admin.events.deleteEvent', { name: event.name })"
        @click="$emit('delete', event)"
      >
        <Trash2 class="h-4 w-4 text-destructive" />
      </Button>
    </td>
  </tr>
</template>
