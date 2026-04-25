<script setup lang="ts">
import { CalendarDays, ChevronDown, List } from '@respeak/lucide-motion-vue'
import { Info, Printer } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import Button from '@/components/ui/button/Button.vue'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

import StatusDropdown from '@/components/tasks/StatusDropdown.vue'

import type { EventRead } from '@/client/types.gen'
import { formatDate } from '@/lib/format'

const props = defineProps<{
  event: EventRead
  eventId: string
  canManage?: boolean
}>()

const emit = defineEmits<{
  statusChange: [status: 'draft' | 'published' | 'archived']
}>()

const { t } = useI18n()
const router = useRouter()
</script>

<template>
  <!-- Mobile header (<xl): stacked -->
  <div class="space-y-2 xl:hidden">
    <h1 class="text-2xl sm:text-3xl font-bold leading-tight">
      {{ props.event.name }}
    </h1>
    <div class="flex flex-wrap items-center gap-x-3 gap-y-1.5">
      <div class="flex items-center gap-1.5">
        <StatusDropdown
          :status="props.event.status"
          i18n-prefix="duties.events.statuses"
          :editable="props.canManage"
          @change="emit('statusChange', $event)"
        />
        <Popover v-if="props.event.status === 'draft'">
          <PopoverTrigger as-child>
            <button
              type="button"
              class="inline-flex h-6 w-6 items-center justify-center rounded-full text-amber-600 hover:bg-amber-100 dark:text-amber-400 dark:hover:bg-amber-950/50"
              :aria-label="t('duties.events.draftBanner')"
            >
              <Info class="h-4 w-4" />
            </button>
          </PopoverTrigger>
          <PopoverContent class="max-w-xs text-sm" side="bottom" align="start">
            {{ t('duties.events.draftBanner') }}
          </PopoverContent>
        </Popover>
      </div>
      <p class="text-sm text-muted-foreground">
        <CalendarDays class="mr-1 inline h-3.5 w-3.5" animateOnHover triggerTarget="parent" />
        {{ formatDate(props.event.start_date) }} – {{ formatDate(props.event.end_date) }}
      </p>
    </div>
    <p v-if="props.event.description" class="text-muted-foreground">
      {{ props.event.description }}
    </p>
  </div>

  <!-- Desktop header (xl+): title + badge inline, print on right -->
  <div class="hidden xl:flex flex-wrap items-start justify-between gap-4">
    <div class="space-y-1">
      <div class="flex items-center gap-3">
        <h1 data-testid="page-heading" class="text-3xl font-bold">{{ props.event.name }}</h1>
        <div class="flex items-center gap-1.5">
          <StatusDropdown
            data-testid="event-status"
            :status="props.event.status"
            i18n-prefix="duties.events.statuses"
            :editable="props.canManage"
            @change="emit('statusChange', $event)"
          />
          <Popover v-if="props.event.status === 'draft'">
            <PopoverTrigger as-child>
              <button
                type="button"
                class="inline-flex h-6 w-6 items-center justify-center rounded-full text-amber-600 hover:bg-amber-100 dark:text-amber-400 dark:hover:bg-amber-950/50"
                :aria-label="t('duties.events.draftBanner')"
              >
                <Info class="h-4 w-4" />
              </button>
            </PopoverTrigger>
            <PopoverContent class="max-w-xs text-sm" side="bottom" align="start">
              {{ t('duties.events.draftBanner') }}
            </PopoverContent>
          </Popover>
        </div>
      </div>
      <p v-if="props.event.description" class="text-muted-foreground">
        {{ props.event.description }}
      </p>
      <p class="text-sm text-muted-foreground">
        <CalendarDays class="mr-1 inline h-3.5 w-3.5" animateOnHover triggerTarget="parent" />
        {{ formatDate(props.event.start_date) }} – {{ formatDate(props.event.end_date) }}
      </p>
    </div>
    <DropdownMenu>
      <DropdownMenuTrigger as-child>
        <Button variant="outline" size="sm">
          <Printer class="mr-2 h-4 w-4" />
          {{ t('print.printButton') }}
          <ChevronDown class="ml-1 h-3 w-3" animateOnHover triggerTarget="parent" animation="default-loop" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem
          @click="
            router.push({
              name: 'print-event',
              params: { eventId: props.eventId },
              query: { mode: 'overview' },
            })
          "
        >
          <List class="mr-2 h-4 w-4" animateOnHover triggerTarget="parent" />
          {{ t('print.overview') }}
        </DropdownMenuItem>
        <DropdownMenuItem
          @click="
            router.push({
              name: 'print-event',
              params: { eventId: props.eventId },
              query: { mode: 'all' },
            })
          "
        >
          <Printer class="mr-2 h-4 w-4" />
          {{ t('print.allTasks') }}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
</template>
