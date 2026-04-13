<script setup lang="ts">
import { CalendarDays, ChevronDown, Info, List, Printer } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { Alert, AlertDescription } from '@/components/ui/alert'
import Button from '@/components/ui/button/Button.vue'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

import StatusDropdown from '@/components/events/StatusDropdown.vue'

import type { EventGroupRead } from '@/client/types.gen'
import { formatDate } from '@/lib/format'

const props = defineProps<{
  group: EventGroupRead
  groupId: string
  canManage?: boolean
}>()

const emit = defineEmits<{
  statusChange: [status: 'draft' | 'published' | 'archived']
}>()

const { t } = useI18n()
const router = useRouter()
</script>

<template>
  <!-- Draft banner -->
  <Alert
    v-if="props.group.status === 'draft'"
    variant="default"
    class="border-amber-500/50 bg-amber-50 text-amber-900 dark:bg-amber-950/30 dark:text-amber-200 dark:border-amber-500/30"
  >
    <Info class="h-4 w-4 text-amber-600 dark:text-amber-400" />
    <AlertDescription>
      {{ t('duties.eventGroups.draftBanner') }}
    </AlertDescription>
  </Alert>

  <!-- Mobile header (<xl): stacked -->
  <div class="space-y-2 xl:hidden">
    <h1 class="text-2xl sm:text-3xl font-bold leading-tight">
      {{ props.group.name }}
    </h1>
    <div class="flex flex-wrap items-center gap-x-3 gap-y-1.5">
      <StatusDropdown
        :status="props.group.status"
        i18n-prefix="duties.eventGroups.statuses"
        :editable="props.canManage"
        @change="emit('statusChange', $event)"
      />
      <p class="text-sm text-muted-foreground">
        <CalendarDays class="mr-1 inline h-3.5 w-3.5" />
        {{ formatDate(props.group.start_date) }} – {{ formatDate(props.group.end_date) }}
      </p>
    </div>
    <p v-if="props.group.description" class="text-muted-foreground">
      {{ props.group.description }}
    </p>
  </div>

  <!-- Desktop header (xl+): title + badge inline, print on right -->
  <div class="hidden xl:flex flex-wrap items-start justify-between gap-4">
    <div class="space-y-1">
      <div class="flex items-center gap-3">
        <h1 data-testid="page-heading" class="text-3xl font-bold">{{ props.group.name }}</h1>
        <StatusDropdown
          data-testid="group-status"
          :status="props.group.status"
          i18n-prefix="duties.eventGroups.statuses"
          :editable="props.canManage"
          @change="emit('statusChange', $event)"
        />
      </div>
      <p v-if="props.group.description" class="text-muted-foreground">
        {{ props.group.description }}
      </p>
      <p class="text-sm text-muted-foreground">
        <CalendarDays class="mr-1 inline h-3.5 w-3.5" />
        {{ formatDate(props.group.start_date) }} – {{ formatDate(props.group.end_date) }}
      </p>
    </div>
    <DropdownMenu>
      <DropdownMenuTrigger as-child>
        <Button variant="outline" size="sm">
          <Printer class="mr-2 h-4 w-4" />
          {{ t('print.printButton') }}
          <ChevronDown class="ml-1 h-3 w-3" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem
          @click="
            router.push({
              name: 'print-event-group',
              params: { groupId: props.groupId },
              query: { mode: 'overview' },
            })
          "
        >
          <List class="mr-2 h-4 w-4" />
          {{ t('print.overview') }}
        </DropdownMenuItem>
        <DropdownMenuItem
          @click="
            router.push({
              name: 'print-event-group',
              params: { groupId: props.groupId },
              query: { mode: 'all' },
            })
          "
        >
          <Printer class="mr-2 h-4 w-4" />
          {{ t('print.allEvents') }}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
</template>
