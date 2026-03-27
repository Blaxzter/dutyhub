import { ref } from 'vue'

import { defineStore } from 'pinia'

import type { CalendarFeedRead } from '@/client/types.gen'
import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

export const useCalendarFeedStore = defineStore('calendarFeed', () => {
  const { get, post, delete: del } = useAuthenticatedClient()

  const feedSettings = ref<CalendarFeedRead | null>(null)
  const loading = ref(false)
  let fetched = false

  async function fetchFeedSettings() {
    if (fetched) return
    fetched = true
    loading.value = true
    try {
      const res = await get<{ data: CalendarFeedRead | null }>({
        url: '/calendar/feed-settings',
      })
      feedSettings.value = res.data
    } catch (error) {
      fetched = false
      console.error('Failed to fetch calendar feed settings:', error)
    } finally {
      loading.value = false
    }
  }

  async function enableFeed() {
    loading.value = true
    try {
      const res = await post<{ data: CalendarFeedRead }>({
        url: '/calendar/feed-settings',
      })
      feedSettings.value = res.data
    } catch (error) {
      console.error('Failed to enable calendar feed:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function regenerateFeed() {
    loading.value = true
    try {
      const res = await post<{ data: CalendarFeedRead }>({
        url: '/calendar/feed-settings/regenerate',
      })
      feedSettings.value = res.data
    } catch (error) {
      console.error('Failed to regenerate calendar feed:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function disableFeed() {
    loading.value = true
    try {
      await del({ url: '/calendar/feed-settings' })
      if (feedSettings.value) {
        feedSettings.value = { ...feedSettings.value, is_enabled: false }
      }
    } catch (error) {
      console.error('Failed to disable calendar feed:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  return {
    feedSettings,
    loading,
    fetchFeedSettings,
    enableFeed,
    regenerateFeed,
    disableFeed,
  }
})
