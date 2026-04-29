import { ref } from 'vue'

import { defineStore } from 'pinia'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import type { SidebarResponse } from '@/client/types.gen'

const REFRESH_DEBOUNCE_MS = 250

export const useSidebarStore = defineStore('sidebar', () => {
  const { get } = useAuthenticatedClient()

  const events = ref<SidebarResponse['events']>([])
  const tasks = ref<SidebarResponse['tasks']>([])
  const bookings = ref<SidebarResponse['bookings']>([])
  const loaded = ref(false)
  let refreshTimer: ReturnType<typeof setTimeout> | null = null

  async function fetch() {
    try {
      const res = await get<{ data: SidebarResponse }>({ url: '/dashboard/sidebar' })
      events.value = res.data.events
      tasks.value = res.data.tasks
      bookings.value = res.data.bookings
      loaded.value = true
    } catch {
      // Sidebar is non-critical — fail silently
    }
  }

  // Coalesce bursts of mutations (e.g. delete-then-refetch flows) into one fetch.
  function refresh() {
    if (refreshTimer) clearTimeout(refreshTimer)
    refreshTimer = setTimeout(() => {
      refreshTimer = null
      void fetch()
    }, REFRESH_DEBOUNCE_MS)
  }

  return { events, tasks, bookings, loaded, fetch, refresh }
})
