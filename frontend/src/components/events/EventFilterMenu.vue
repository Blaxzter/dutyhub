<script setup lang="ts">
import { computed, ref } from 'vue'

import { Filter, RotateCcw } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { useEventFiltersStore } from '@/stores/eventFilters'

import { Badge } from '@/components/ui/badge'
import Button from '@/components/ui/button/Button.vue'
import { DateRangePicker } from '@/components/ui/date-range-picker'
import { Label } from '@/components/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'

const { t } = useI18n()
const { get } = useAuthenticatedClient()
const filters = useEventFiltersStore()

const showHideFullSlots = computed(() => filters.viewMode === 'list')

// Fetch active dates for the visible month in the date picker
const markedDays = ref<Set<string>>(new Set())

async function handleVisibleMonth(range: { from: string; to: string }) {
  try {
    const res = await get<{ data: string[] }>({
      url: '/events/active-dates',
      query: { date_from: range.from, date_to: range.to },
    })
    markedDays.value = new Set(res.data)
  } catch {
    // Non-critical
  }
}
</script>

<template>
  <div class="flex items-center gap-2">
    <!-- Date range picker -->
    <DateRangePicker
      :date-from="filters.dateFrom"
      :date-to="filters.dateTo"
      :marked-days="markedDays"
      @update:date-from="filters.dateFrom = $event"
      @update:date-to="filters.dateTo = $event"
      @update:visible-month="handleVisibleMonth"
    />

    <!-- Filter menu popover -->
    <Popover>
      <PopoverTrigger as-child>
        <Button variant="outline" size="sm">
          <Filter class="h-4 w-4" />
          <span class="hidden sm:inline">{{ t('duties.events.filters.title') }}</span>
          <Badge
            v-if="filters.activeFilterCount > 0"
            variant="secondary"
            class="ml-1 shrink-0 px-1.5 py-0 text-[10px] leading-4"
          >
            {{ filters.activeFilterCount }}
          </Badge>
        </Button>
      </PopoverTrigger>
      <PopoverContent class="w-72" align="end">
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <h4 class="text-sm font-medium">{{ t('duties.events.filters.title') }}</h4>
            <Button
              v-if="filters.activeFilterCount > 0"
              variant="ghost"
              size="sm"
              class="h-auto px-2 py-1 text-xs"
              @click="filters.resetFilters()"
            >
              <RotateCcw class="mr-1 h-3 w-3" />
              {{ t('duties.events.filters.reset') }}
            </Button>
          </div>

          <Separator />

          <div class="space-y-3">
            <!-- My Bookings Only -->
            <div class="flex items-center justify-between">
              <Label for="filter-my-bookings" class="text-sm font-normal cursor-pointer">
                {{ t('duties.events.myBookingsFilter') }}
              </Label>
              <Switch
                id="filter-my-bookings"
                :model-value="filters.myBookingsOnly"
                @update:model-value="filters.myBookingsOnly = $event"
              />
            </div>

            <!-- Hide Fully Booked (list view only) -->
            <div v-if="showHideFullSlots" class="flex items-center justify-between">
              <Label for="filter-hide-full" class="text-sm font-normal cursor-pointer">
                {{ t('duties.events.hideFullSlots') }}
              </Label>
              <Switch
                id="filter-hide-full"
                :model-value="filters.hideFullSlots"
                @update:model-value="filters.hideFullSlots = $event"
              />
            </div>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  </div>
</template>
