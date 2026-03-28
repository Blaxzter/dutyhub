<script setup lang="ts">
import { computed } from 'vue'

import { Bell, Mail, MessageCircle, Plus, Smartphone, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import type { ReminderOffsetEntry } from '@/stores/bookingReminder'
import { ALLOWED_OFFSETS, useBookingReminderStore } from '@/stores/bookingReminder'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

const props = defineProps<{
  entries: ReminderOffsetEntry[]
  availableChannels?: string[]
}>()

const emit = defineEmits<{
  'update:entries': [value: ReminderOffsetEntry[]]
}>()

const { t } = useI18n()
const reminderStore = useBookingReminderStore()

const channels = computed(() => props.availableChannels ?? ['email', 'push', 'telegram'])

const availableOffsets = computed(() =>
  ALLOWED_OFFSETS.filter(
    (o) => !props.entries.some((e) => e.offset_minutes === o),
  ),
)

function getOffsetLabel(offset: number): string {
  return t(`notifications.reminders.offset.${offset}`)
}

async function save(entries: ReminderOffsetEntry[]) {
  emit('update:entries', entries)
  try {
    await reminderStore.updateDefaultOffsets(entries)
  } catch {
    toast.error(t('notifications.reminders.saveFailed'))
    const fresh = await reminderStore.fetchDefaultOffsets()
    emit('update:entries', fresh)
  }
}

function addOffset(offset: number) {
  const entry: ReminderOffsetEntry = { offset_minutes: offset, channels: ['push'] }
  const updated = [...props.entries, entry].sort(
    (a, b) => a.offset_minutes - b.offset_minutes,
  )
  save(updated)
}

function removeOffset(offset: number) {
  save(props.entries.filter((e) => e.offset_minutes !== offset))
}

function toggleChannel(offset: number, channel: string) {
  const entry = props.entries.find((e) => e.offset_minutes === offset)
  if (!entry) return
  const has = entry.channels.includes(channel)
  if (has && entry.channels.length === 1) return
  const updated = props.entries.map((e) => {
    if (e.offset_minutes !== offset) return e
    return {
      ...e,
      channels: has
        ? e.channels.filter((c) => c !== channel)
        : [...e.channels, channel],
    }
  })
  save(updated)
}
</script>

<template>
  <Card>
    <CardHeader>
      <div class="flex items-center gap-2">
        <Bell :size="20" class="text-amber-600 dark:text-amber-400" />
        <CardTitle>{{ t('notifications.reminders.title') }}</CardTitle>
      </div>
      <CardDescription>
        {{ t('notifications.reminders.description') }}
      </CardDescription>
    </CardHeader>
    <CardContent class="space-y-3">
      <div
        v-for="entry in entries"
        :key="entry.offset_minutes"
        class="flex items-center gap-3 rounded-lg border p-3"
      >
        <div class="flex-1 text-sm font-medium">
          {{ getOffsetLabel(entry.offset_minutes) }}
        </div>
        <div class="flex items-center gap-1.5">
          <button
            v-for="ch in channels"
            :key="ch"
            :class="[
              'rounded-md px-2 py-1 text-xs font-medium transition-colors',
              entry.channels.includes(ch)
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80',
            ]"
            :title="t(`notifications.channels.${ch}`)"
            @click="toggleChannel(entry.offset_minutes, ch)"
          >
            <Mail v-if="ch === 'email'" :size="14" />
            <Smartphone v-else-if="ch === 'push'" :size="14" />
            <MessageCircle v-else :size="14" />
          </button>
        </div>
        <button
          class="text-muted-foreground hover:text-foreground transition-colors"
          @click="removeOffset(entry.offset_minutes)"
        >
          <X :size="16" />
        </button>
      </div>

      <DropdownMenu v-if="availableOffsets.length > 0">
        <DropdownMenuTrigger as-child>
          <Button variant="outline" size="sm" class="h-8 gap-1">
            <Plus :size="14" />
            {{ t('notifications.reminders.addReminder') }}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuItem
            v-for="offset in availableOffsets"
            :key="offset"
            @click="addOffset(offset)"
          >
            {{ getOffsetLabel(offset) }}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <p
        v-if="entries.length === 0"
        class="text-muted-foreground text-sm"
      >
        {{ t('notifications.reminders.noDefaults') }}
      </p>
    </CardContent>
  </Card>
</template>
