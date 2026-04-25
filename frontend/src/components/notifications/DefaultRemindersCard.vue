<script setup lang="ts">
import { computed, ref } from 'vue'

import { Bell, Plus } from '@respeak/lucide-motion-vue'
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

import ReminderEntryRow from '@/components/notifications/ReminderEntryRow.vue'

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
  ALLOWED_OFFSETS.filter((o) => !props.entries.some((e) => e.offset_minutes === o)),
)

function getOffsetLabel(offset: number): string {
  return t(`notifications.reminders.offset.${offset}`)
}

const loadingOffset = ref<number | null>(null)

async function save(entries: ReminderOffsetEntry[], affectedOffset: number | null = null) {
  loadingOffset.value = affectedOffset
  emit('update:entries', entries)
  try {
    await reminderStore.updateDefaultOffsets(entries)
  } catch {
    toast.error(t('notifications.reminders.saveFailed'))
    const fresh = await reminderStore.fetchDefaultOffsets()
    emit('update:entries', fresh)
  } finally {
    loadingOffset.value = null
  }
}

function addOffset(offset: number) {
  const entry: ReminderOffsetEntry = { offset_minutes: offset, channels: ['push'] }
  const updated = [...props.entries, entry].sort((a, b) => a.offset_minutes - b.offset_minutes)
  save(updated)
}

function removeOffset(offset: number) {
  save(
    props.entries.filter((e) => e.offset_minutes !== offset),
    offset,
  )
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
      channels: has ? e.channels.filter((c) => c !== channel) : [...e.channels, channel],
    }
  })
  save(updated, offset)
}
</script>

<template>
  <Card>
    <CardHeader>
      <div class="flex items-center gap-2">
        <Bell
          :size="20"
          class="text-amber-600 dark:text-amber-400"
          animateOnHover
          triggerTarget="parent"
        />
        <CardTitle>{{ t('notifications.reminders.title') }}</CardTitle>
      </div>
      <CardDescription>
        {{ t('notifications.reminders.description') }}
      </CardDescription>
    </CardHeader>
    <CardContent class="space-y-3">
      <ReminderEntryRow
        v-for="entry in entries"
        :key="entry.offset_minutes"
        :offset-label="getOffsetLabel(entry.offset_minutes)"
        :channels="entry.channels"
        :available-channels="channels"
        :loading="loadingOffset === entry.offset_minutes"
        @toggle-channel="(ch) => toggleChannel(entry.offset_minutes, ch)"
        @remove="removeOffset(entry.offset_minutes)"
      />

      <DropdownMenu v-if="availableOffsets.length > 0">
        <DropdownMenuTrigger as-child>
          <Button variant="outline" size="sm" class="h-8 gap-1">
            <Plus :size="14" animateOnHover triggerTarget="parent" />
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

      <p v-if="entries.length === 0" class="text-muted-foreground text-sm">
        {{ t('notifications.reminders.noDefaults') }}
      </p>
    </CardContent>
  </Card>
</template>
