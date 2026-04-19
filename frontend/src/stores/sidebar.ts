import { ref } from 'vue'

import { defineStore } from 'pinia'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import type { SidebarResponse } from '@/client/types.gen'

export const useSidebarStore = defineStore('sidebar', () => {
  const { get } = useAuthenticatedClient()

  const events = ref<SidebarResponse['events']>([])
  const tasks = ref<SidebarResponse['tasks']>([])
  const bookings = ref<SidebarResponse['bookings']>([])
  const loaded = ref(false)

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

  return { events, tasks, bookings, loaded, fetch }
})
