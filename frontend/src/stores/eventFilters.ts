import { computed, ref, watch } from 'vue'

import { defineStore } from 'pinia'

export type ViewMode = 'list' | 'box' | 'calendar'
export type FocusMode = 'today' | 'first-available'

const STORAGE_KEY = 'wirksam:events:filters'

interface PersistedFilters {
  viewMode: ViewMode
  focusMode: FocusMode
  myBookingsOnly: boolean
  hideFullSlots: boolean
  dateFrom: string | null // YYYY-MM-DD or null (= today)
  dateTo: string | null   // YYYY-MM-DD or null (= no upper bound)
}

function loadFromStorage(): Partial<PersistedFilters> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

export const useEventFiltersStore = defineStore('eventFilters', () => {
  const saved = loadFromStorage()

  const searchQuery = ref('')
  const viewMode = ref<ViewMode>(saved.viewMode ?? 'list')
  const focusMode = ref<FocusMode>(saved.focusMode ?? 'today')
  const myBookingsOnly = ref(saved.myBookingsOnly ?? false)
  const hideFullSlots = ref(saved.hideFullSlots ?? false)
  /** Custom start date for event filtering. null = today (default). */
  const dateFrom = ref<string | null>(saved.dateFrom ?? null)
  /** Custom end date for event filtering. null = no upper bound. */
  const dateTo = ref<string | null>(saved.dateTo ?? null)

  // Persist filter state to localStorage
  const persistable = computed<PersistedFilters>(() => ({
    viewMode: viewMode.value,
    focusMode: focusMode.value,
    myBookingsOnly: myBookingsOnly.value,
    hideFullSlots: hideFullSlots.value,
    dateFrom: dateFrom.value,
    dateTo: dateTo.value,
  }))

  watch(persistable, (v) => localStorage.setItem(STORAGE_KEY, JSON.stringify(v)), { deep: true })

  /** Whether a custom (non-default) date range is active. */
  const hasCustomDateRange = computed(() => dateFrom.value !== null || dateTo.value !== null)

  /** Number of active content filters (excludes view/focus mode). */
  const activeFilterCount = computed(() => {
    let count = 0
    if (myBookingsOnly.value) count++
    if (hideFullSlots.value) count++
    if (hasCustomDateRange.value) count++
    if (searchQuery.value.trim()) count++
    return count
  })

  function resetFilters() {
    searchQuery.value = ''
    myBookingsOnly.value = false
    hideFullSlots.value = false
    dateFrom.value = null
    dateTo.value = null
  }

  function clearDateRange() {
    dateFrom.value = null
    dateTo.value = null
  }

  return {
    searchQuery,
    viewMode,
    focusMode,
    myBookingsOnly,
    hideFullSlots,
    dateFrom,
    dateTo,
    hasCustomDateRange,
    activeFilterCount,
    resetFilters,
    clearDateRange,
  }
})
