import { computed, markRaw, ref, watch } from 'vue'

import { useAuth0 } from '@auth0/auth0-vue'
import type { User } from '@auth0/auth0-vue'
import { defineStore } from 'pinia'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { type Palette, usePalette } from '@/composables/usePalette'

import ActionToast from '@/components/ui/sonner/ActionToast.vue'

import type { EventRead, UserProfile, UserRead } from '@/client/types.gen'
import i18n from '@/locales/i18n'

export type { User }

export const useAuthStore = defineStore('auth', () => {
  const auth0 = useAuth0()
  const { post, get, put } = useAuthenticatedClient()
  const { t } = useI18n()
  const router = useRouter()
  const loading = ref(false)
  const profileLoading = ref(false)
  const pendingUserCount = ref(0)

  const isAuthenticated = computed(() => auth0.isAuthenticated.value)
  const user = computed(() => auth0.user.value)
  const profile = ref<UserProfile | null>(null)
  const roles = computed(() => profile.value?.roles ?? [])
  const isAdmin = computed(() => profile.value?.is_admin ?? false)
  const isTaskManager = computed(() => profile.value?.is_task_manager ?? false)
  const managedEventIds = computed(() => profile.value?.managed_event_ids ?? [])
  const isEventManager = computed(() => managedEventIds.value.length > 0)
  const isManager = computed(() => isAdmin.value || isTaskManager.value || isEventManager.value)
  const isActive = computed(() => profile.value?.is_active ?? true)
  const selectedEventId = computed(() => profile.value?.selected_event_id ?? null)
  const selectedEvent = ref<EventRead | null>(null)

  /** Check if current user can manage a task/event by its event_id. */
  function canManageEvent(eventId: string | null | undefined): boolean {
    if (isAdmin.value || isTaskManager.value) return true
    return !!eventId && managedEventIds.value.includes(eventId)
  }

  let profilePromise: Promise<UserProfile | null> | null = null

  const logout = () => {
    profile.value = null
    auth0.logout({
      logoutParams: {
        returnTo: window.location.origin,
      },
    })
  }

  const getAccessToken = async () => {
    try {
      return await auth0.getAccessTokenSilently()
    } catch (error) {
      console.error('Error getting access token:', error)
      throw error
    }
  }

  const updateUser = (userData: Partial<User>) => {
    console.log('Updating user with data:', userData)

    if (!isAuthenticated.value || !auth0.user.value) return

    auth0.user.value = {
      ...auth0.user.value,
      ...userData,
    }
  }

  const loadSelectedEvent = async (eventId: string | null) => {
    if (!eventId) {
      selectedEvent.value = null
      return
    }
    try {
      const res = await get<{ data: EventRead }>({ url: `/events/${eventId}` })
      selectedEvent.value = res.data
    } catch {
      selectedEvent.value = null
    }
  }

  const setSelectedEvent = async (id: string | null) => {
    const response = await put<{ data: UserProfile }>({
      url: '/users/me/selected-event',
      body: { selected_event_id: id },
    })
    profile.value = response.data
    await loadSelectedEvent(response.data.selected_event_id ?? null)
    return response.data
  }

  const loadProfile = async () => {
    if (!isAuthenticated.value) return null
    if (profilePromise) return await profilePromise

    profileLoading.value = true
    profilePromise = (async () => {
      // Send profile data from Auth0 ID token to backend for user initialization
      const profileInit =
        auth0.user.value && (auth0.user.value.email || auth0.user.value.name)
          ? {
              email: auth0.user.value.email,
              name: auth0.user.value.name,
              nickname: auth0.user.value.nickname,
              picture: auth0.user.value.picture,
              email_verified: auth0.user.value.email_verified,
              preferred_language: i18n.global.locale.value,
            }
          : null

      const response = await post<{ data: UserProfile }>({
        url: '/users/me',
        body: profileInit,
      })
      profile.value = response.data

      // Apply server-side language preference
      if (response.data.preferred_language) {
        i18n.global.locale.value = response.data.preferred_language as 'en' | 'de'
        localStorage.setItem('locale', response.data.preferred_language)
      }

      // Apply server-side theme preference
      if (response.data.theme) {
        usePalette().value = response.data.theme as Palette
      }

      // Check for pending users once per session (admin only)
      if (response.data.is_admin) {
        checkPendingUsers()
      }

      // Resolve the selected event (best-effort, non-blocking)
      void loadSelectedEvent(response.data.selected_event_id ?? null)

      return response.data
    })()

    try {
      return await profilePromise
    } catch (error) {
      console.error('Error loading user profile:', error)
      throw error
    } finally {
      profileLoading.value = false
      profilePromise = null
    }
  }

  const ensureProfile = async () => {
    if (profile.value) return profile.value
    return await loadProfile()
  }

  const callProtectedAPI = async (endpoint: string, options: RequestInit = {}) => {
    try {
      const token = await getAccessToken()
      return await fetch(`${import.meta.env.VITE_API_URL}${endpoint}`, {
        ...options,
        headers: {
          ...options.headers,
          Authorization: `Bearer ${token}`,
        },
      })
    } catch (error) {
      console.error('Error calling protected API:', error)
      throw error
    }
  }

  const checkPendingUsers = async () => {
    try {
      const usersRes = await get<{ data: { items: UserRead[] } }>({ url: '/users/' })
      const pending = usersRes.data.items.filter((u) => !u.is_active && !u.rejection_reason)
      pendingUserCount.value = pending.length
      if (pending.length > 0) {
        toast.custom(markRaw(ActionToast), {
          duration: Infinity,
          componentProps: {
            message: t(
              'dashboard.home.stats.users.pendingToast',
              { count: pending.length },
              pending.length,
            ),
            actionLabel: t('dashboard.home.stats.users.pendingAction'),
            dismissLabel: t('dashboard.home.stats.users.pendingDismiss'),
            onAction: () => router.push({ name: 'admin-users' }),
          },
        })
      }
    } catch {
      // Non-critical, ignore
    }
  }

  watch(isAuthenticated, (next) => {
    if (!next) {
      profile.value = null
      selectedEvent.value = null
    }
  })

  return {
    auth0,
    isAuthenticated,
    user,
    profile,
    roles,
    isActive,
    isAdmin,
    isTaskManager,
    isEventManager,
    managedEventIds,
    isManager,
    canManageEvent,
    pendingUserCount,
    loading,
    profileLoading,
    selectedEventId,
    selectedEvent,
    logout,
    getAccessToken,
    updateUser,
    loadProfile,
    ensureProfile,
    setSelectedEvent,
    callProtectedAPI,
  }
})
