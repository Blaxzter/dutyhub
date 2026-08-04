import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  NOTIFICATION_CLASSIFICATIONS,
  type NotificationItem,
  type NotificationSubscription,
  type NotificationType,
  type PushSubscriptionInfo,
  type TelegramBinding,
  useNotificationStore,
} from '@/stores/notification'

const api = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
  getAuthToken: vi.fn(),
}))

vi.mock('@/composables/useAuthenticatedClient', () => ({
  useAuthenticatedClient: () => ({
    get: api.get,
    post: api.post,
    put: api.put,
    patch: api.patch,
    delete: api.del,
    getAuthToken: api.getAuthToken,
  }),
}))

// ── Test doubles ─────────────────────────────────────────────────

type SseListener = (event: { data: string }) => void

/** Minimal stand-in for the browser EventSource the store opens. */
class FakeEventSource {
  static instances: FakeEventSource[] = []

  readonly url: string
  closed = false
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  private readonly listeners = new Map<string, SseListener[]>()

  constructor(url: string) {
    this.url = url
    FakeEventSource.instances.push(this)
  }

  addEventListener(type: string, listener: SseListener) {
    const forType = this.listeners.get(type) ?? []
    forType.push(listener)
    this.listeners.set(type, forType)
  }

  close() {
    this.closed = true
  }

  /** Test-only: deliver a server-sent event to the store's listener. */
  emit(type: string, data: string) {
    for (const listener of this.listeners.get(type) ?? []) listener({ data })
  }
}

function lastEventSource(): FakeEventSource {
  const instance = FakeEventSource.instances.at(-1)
  if (!instance) throw new Error('no EventSource was opened')
  return instance
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((res) => {
    resolve = res
  })
  return { promise, resolve }
}

// ── Fixtures ─────────────────────────────────────────────────────

function makeNotification(overrides: Partial<NotificationItem> = {}): NotificationItem {
  return {
    id: 'n1',
    recipient_id: 'u1',
    notification_type_code: 'shift.reminder',
    classification: 'reminder',
    title: 'Shift tomorrow',
    body: 'Bar, 18:00',
    data: null,
    is_read: false,
    read_at: null,
    channels_sent: ['email'],
    channels_failed: [],
    created_at: '2026-08-01T09:00:00Z',
    ...overrides,
  }
}

const notificationType: NotificationType = {
  id: 'nt1',
  code: 'shift.reminder',
  name: 'Shift reminder',
  description: null,
  category: 'shifts',
  classification: 'reminder',
  is_admin_only: false,
  default_channels: ['email'],
  is_active: true,
  is_user_configurable: true,
}

const subscription: NotificationSubscription = {
  id: 's1',
  user_id: 'u1',
  notification_type_id: 'nt1',
  email_enabled: true,
  push_enabled: false,
  telegram_enabled: false,
  scope_type: 'global',
  scope_id: null,
  is_muted: false,
  created_at: '2026-08-01T09:00:00Z',
  updated_at: '2026-08-01T09:00:00Z',
}

const binding: TelegramBinding = {
  id: 'tb1',
  telegram_chat_id: '4242',
  telegram_username: 'volunteer',
  is_verified: true,
  created_at: '2026-08-01T09:00:00Z',
}

const pushInfo: PushSubscriptionInfo = {
  id: 'ps1',
  endpoint: 'https://push.example.test/abc',
  user_agent: 'Firefox',
  created_at: '2026-08-01T09:00:00Z',
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.spyOn(console, 'error').mockImplementation(() => {})
  FakeEventSource.instances = []
  vi.stubGlobal('EventSource', FakeEventSource)
  vi.stubGlobal('navigator', { userAgent: 'vitest-agent' })
  vi.stubEnv('VITE_API_URL', 'http://api.test/api/v1')
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

describe('useNotificationStore', () => {
  describe('initial state and getters', () => {
    it('starts empty with every channel enabled', () => {
      const store = useNotificationStore()

      expect(store.notifications).toEqual([])
      expect(store.unreadCount).toBe(0)
      expect(store.total).toBe(0)
      expect(store.notificationTypes).toEqual([])
      expect(store.preferences).toEqual([])
      expect(store.telegramBinding).toBeNull()
      expect(store.pushSubscriptions).toEqual([])
      expect(store.globalChannelSettings).toEqual({
        notify_email: true,
        notify_push: true,
        notify_telegram: true,
      })
      expect(store.loading).toBe(false)
      expect(store.telegramBotUsername).toBeNull()
      expect(store.telegramConfigured).toBe(false)
    })

    it('exposes the four notification classifications', () => {
      expect(NOTIFICATION_CLASSIFICATIONS).toEqual(['reminder', 'change', 'match', 'announcement'])
    })

    it('derives hasUnread from the unread count', () => {
      const store = useNotificationStore()

      expect(store.hasUnread).toBe(false)

      store.unreadCount = 3

      expect(store.hasUnread).toBe(true)
    })

    it('derives hasMore from the loaded page versus the total', () => {
      const store = useNotificationStore()

      expect(store.hasMore).toBe(false)

      store.notifications = [makeNotification()]
      store.total = 5
      expect(store.hasMore).toBe(true)

      store.total = 1
      expect(store.hasMore).toBe(false)
    })
  })

  describe('fetchUnreadCount', () => {
    it('stores the count', async () => {
      api.get.mockResolvedValue({ data: { unread_count: 9 } })
      const store = useNotificationStore()

      await store.fetchUnreadCount()

      expect(api.get).toHaveBeenCalledWith({ url: '/notifications/unread-count' })
      expect(store.unreadCount).toBe(9)
    })

    it('swallows failures and keeps the previous count', async () => {
      const store = useNotificationStore()
      store.unreadCount = 4
      api.get.mockRejectedValue(new Error('offline'))

      await expect(store.fetchUnreadCount()).resolves.toBeUndefined()

      expect(console.error).toHaveBeenCalled()
      expect(store.unreadCount).toBe(4)
    })
  })

  describe('fetchNotifications', () => {
    const page = {
      items: [makeNotification({ id: 'n1' }), makeNotification({ id: 'n2' })],
      total: 5,
      unread_count: 2,
      skip: 0,
      limit: 20,
    }

    it('replaces the list and syncs the counters', async () => {
      api.get.mockResolvedValue({ data: page })
      const store = useNotificationStore()

      const result = await store.fetchNotifications()

      expect(api.get).toHaveBeenCalledWith({ url: '/notifications/', query: {} })
      expect(result).toEqual(page)
      expect(store.notifications).toEqual(page.items)
      expect(store.total).toBe(5)
      expect(store.unreadCount).toBe(2)
      expect(store.loading).toBe(false)
    })

    it('forwards the unread-only, skip and limit options as query params', async () => {
      api.get.mockResolvedValue({ data: { ...page, items: [] } })
      const store = useNotificationStore()

      await store.fetchNotifications({ unreadOnly: true, skip: 0, limit: 10 })

      expect(api.get).toHaveBeenCalledWith({
        url: '/notifications/',
        query: { unread_only: true, skip: 0, limit: 10 },
      })
    })

    it('appends instead of replacing when asked to', async () => {
      const store = useNotificationStore()
      store.notifications = [makeNotification({ id: 'n0' })]
      api.get.mockResolvedValue({ data: page })

      await store.fetchNotifications({ append: true })

      expect(store.notifications.map((n) => n.id)).toEqual(['n0', 'n1', 'n2'])
    })

    it('flips loading true while in flight and false afterwards', async () => {
      const d = deferred<{ data: typeof page }>()
      api.get.mockReturnValue(d.promise)
      const store = useNotificationStore()

      const pending = store.fetchNotifications()
      expect(store.loading).toBe(true)

      d.resolve({ data: page })
      await pending

      expect(store.loading).toBe(false)
    })

    it('rethrows and clears loading on failure', async () => {
      api.get.mockRejectedValue(new Error('500'))
      const store = useNotificationStore()

      await expect(store.fetchNotifications()).rejects.toThrow('500')

      expect(console.error).toHaveBeenCalled()
      expect(store.notifications).toEqual([])
      expect(store.loading).toBe(false)
    })

    it('handles an empty inbox', async () => {
      api.get.mockResolvedValue({
        data: { items: [], total: 0, unread_count: 0, skip: 0, limit: 20 },
      })
      const store = useNotificationStore()

      await store.fetchNotifications()

      expect(store.notifications).toEqual([])
      expect(store.hasMore).toBe(false)
    })
  })

  describe('loadMoreNotifications', () => {
    it('requests the next page and appends it', async () => {
      const store = useNotificationStore()
      store.notifications = [makeNotification({ id: 'n1' }), makeNotification({ id: 'n2' })]
      store.total = 5
      api.get.mockResolvedValue({
        data: {
          items: [makeNotification({ id: 'n3' })],
          total: 5,
          unread_count: 1,
          skip: 2,
          limit: 20,
        },
      })

      await store.loadMoreNotifications()

      expect(api.get).toHaveBeenCalledWith({
        url: '/notifications/',
        query: { skip: 2, limit: 20 },
      })
      expect(store.notifications.map((n) => n.id)).toEqual(['n1', 'n2', 'n3'])
    })

    it('does nothing when everything is already loaded', async () => {
      const store = useNotificationStore()
      store.notifications = [makeNotification()]
      store.total = 1

      await store.loadMoreNotifications()

      expect(api.get).not.toHaveBeenCalled()
    })

    it('does nothing while another request is in flight', async () => {
      const store = useNotificationStore()
      store.notifications = [makeNotification()]
      store.total = 5
      store.loading = true

      await store.loadMoreNotifications()

      expect(api.get).not.toHaveBeenCalled()
    })
  })

  describe('markAsRead', () => {
    it('replaces the item in place and decrements the unread count', async () => {
      const store = useNotificationStore()
      store.notifications = [makeNotification({ id: 'n1' }), makeNotification({ id: 'n2' })]
      store.unreadCount = 2
      const read = makeNotification({ id: 'n2', is_read: true, read_at: '2026-08-02T10:00:00Z' })
      api.patch.mockResolvedValue({ data: read })

      const result = await store.markAsRead('n2')

      expect(api.patch).toHaveBeenCalledWith({ url: '/notifications/n2/read' })
      expect(result).toEqual(read)
      expect(store.notifications[1]).toEqual(read)
      expect(store.notifications[0]?.is_read).toBe(false)
      expect(store.unreadCount).toBe(1)
    })

    it('never drives the unread count below zero', async () => {
      const store = useNotificationStore()
      store.notifications = [makeNotification({ id: 'n1' })]
      store.unreadCount = 0
      api.patch.mockResolvedValue({ data: makeNotification({ id: 'n1', is_read: true }) })

      await store.markAsRead('n1')

      expect(store.unreadCount).toBe(0)
    })

    it('leaves the list alone when the id is not loaded', async () => {
      const store = useNotificationStore()
      store.notifications = [makeNotification({ id: 'n1' })]
      store.unreadCount = 1
      api.patch.mockResolvedValue({ data: makeNotification({ id: 'ghost', is_read: true }) })

      await store.markAsRead('ghost')

      expect(store.notifications.map((n) => n.id)).toEqual(['n1'])
      expect(store.notifications[0]?.is_read).toBe(false)
      expect(store.unreadCount).toBe(0)
    })

    it('rethrows and keeps the item unread on failure', async () => {
      const store = useNotificationStore()
      store.notifications = [makeNotification({ id: 'n1' })]
      store.unreadCount = 1
      api.patch.mockRejectedValue(new Error('500'))

      await expect(store.markAsRead('n1')).rejects.toThrow('500')

      expect(console.error).toHaveBeenCalled()
      expect(store.notifications[0]?.is_read).toBe(false)
      expect(store.unreadCount).toBe(1)
    })
  })

  describe('markAllAsRead', () => {
    it('flags every loaded notification and zeroes the count', async () => {
      const store = useNotificationStore()
      store.notifications = [makeNotification({ id: 'n1' }), makeNotification({ id: 'n2' })]
      store.unreadCount = 2
      api.post.mockResolvedValue({ marked_count: 2 })

      await store.markAllAsRead()

      expect(api.post).toHaveBeenCalledWith({ url: '/notifications/mark-all-read' })
      expect(store.notifications.every((n) => n.is_read)).toBe(true)
      expect(store.unreadCount).toBe(0)
    })

    it('rethrows and leaves the list untouched on failure', async () => {
      const store = useNotificationStore()
      store.notifications = [makeNotification({ id: 'n1' })]
      store.unreadCount = 1
      api.post.mockRejectedValue(new Error('500'))

      await expect(store.markAllAsRead()).rejects.toThrow('500')

      expect(store.notifications[0]?.is_read).toBe(false)
      expect(store.unreadCount).toBe(1)
    })
  })

  describe('dismissNotification', () => {
    it('removes the notification from the list', async () => {
      const store = useNotificationStore()
      store.notifications = [makeNotification({ id: 'n1' }), makeNotification({ id: 'n2' })]
      api.del.mockResolvedValue(undefined)

      await store.dismissNotification('n1')

      expect(api.del).toHaveBeenCalledWith({ url: '/notifications/n1' })
      expect(store.notifications.map((n) => n.id)).toEqual(['n2'])
    })

    it('is a no-op for an id that is not loaded', async () => {
      const store = useNotificationStore()
      store.notifications = [makeNotification({ id: 'n1' })]
      api.del.mockResolvedValue(undefined)

      await store.dismissNotification('ghost')

      expect(store.notifications.map((n) => n.id)).toEqual(['n1'])
    })

    it('rethrows and keeps the notification on failure', async () => {
      const store = useNotificationStore()
      store.notifications = [makeNotification({ id: 'n1' })]
      api.del.mockRejectedValue(new Error('500'))

      await expect(store.dismissNotification('n1')).rejects.toThrow('500')

      expect(store.notifications).toHaveLength(1)
    })
  })

  describe('dismissAllNotifications', () => {
    it('clears the list and both counters', async () => {
      const store = useNotificationStore()
      store.notifications = [makeNotification({ id: 'n1' })]
      store.unreadCount = 1
      store.total = 1
      api.post.mockResolvedValue({ dismissed_count: 1 })

      await store.dismissAllNotifications()

      expect(api.post).toHaveBeenCalledWith({ url: '/notifications/dismiss-all' })
      expect(store.notifications).toEqual([])
      expect(store.unreadCount).toBe(0)
      expect(store.total).toBe(0)
    })

    it('rethrows and keeps everything on failure', async () => {
      const store = useNotificationStore()
      store.notifications = [makeNotification({ id: 'n1' })]
      store.total = 1
      api.post.mockRejectedValue(new Error('500'))

      await expect(store.dismissAllNotifications()).rejects.toThrow('500')

      expect(store.notifications).toHaveLength(1)
      expect(store.total).toBe(1)
    })
  })

  describe('fetchNotificationTypes', () => {
    it('caches the catalogue', async () => {
      api.get.mockResolvedValue({ data: [notificationType] })
      const store = useNotificationStore()

      const result = await store.fetchNotificationTypes()

      expect(api.get).toHaveBeenCalledWith({ url: '/notifications/types' })
      expect(result).toEqual([notificationType])
      expect(store.notificationTypes).toEqual([notificationType])
    })

    it('rethrows on failure and leaves the cache empty', async () => {
      api.get.mockRejectedValue(new Error('500'))
      const store = useNotificationStore()

      await expect(store.fetchNotificationTypes()).rejects.toThrow('500')

      expect(store.notificationTypes).toEqual([])
    })
  })

  describe('preferences', () => {
    it('fetches and caches subscriptions', async () => {
      api.get.mockResolvedValue({ data: [subscription] })
      const store = useNotificationStore()

      const result = await store.fetchPreferences()

      expect(api.get).toHaveBeenCalledWith({ url: '/notifications/preferences' })
      expect(result).toEqual([subscription])
      expect(store.preferences).toEqual([subscription])
    })

    it('rethrows when fetching preferences fails', async () => {
      api.get.mockRejectedValue(new Error('500'))
      const store = useNotificationStore()

      await expect(store.fetchPreferences()).rejects.toThrow('500')
      expect(store.preferences).toEqual([])
    })

    it('sends the updated preferences and caches the response', async () => {
      const updated = { ...subscription, push_enabled: true }
      api.put.mockResolvedValue({ data: [updated] })
      const store = useNotificationStore()

      const payload = [
        {
          notification_type_id: 'nt1',
          email_enabled: true,
          push_enabled: true,
          telegram_enabled: false,
        },
      ]
      const result = await store.updatePreferences(payload)

      expect(api.put).toHaveBeenCalledWith({
        url: '/notifications/preferences',
        body: { preferences: payload },
      })
      expect(result).toEqual([updated])
      expect(store.preferences).toEqual([updated])
    })

    it('rethrows when updating preferences fails', async () => {
      api.put.mockRejectedValue(new Error('422'))
      const store = useNotificationStore()

      await expect(
        store.updatePreferences([
          {
            notification_type_id: 'nt1',
            email_enabled: true,
            push_enabled: true,
            telegram_enabled: false,
          },
        ]),
      ).rejects.toThrow('422')
      expect(store.preferences).toEqual([])
    })
  })

  describe('global channel settings', () => {
    it('fetches and caches the settings', async () => {
      const settings = { notify_email: false, notify_push: true, notify_telegram: false }
      api.get.mockResolvedValue({ data: settings })
      const store = useNotificationStore()

      const result = await store.fetchGlobalChannelSettings()

      expect(api.get).toHaveBeenCalledWith({ url: '/notifications/channel-settings' })
      expect(result).toEqual(settings)
      expect(store.globalChannelSettings).toEqual(settings)
    })

    it('keeps the defaults when the fetch fails', async () => {
      api.get.mockRejectedValue(new Error('500'))
      const store = useNotificationStore()

      await expect(store.fetchGlobalChannelSettings()).rejects.toThrow('500')

      expect(store.globalChannelSettings).toEqual({
        notify_email: true,
        notify_push: true,
        notify_telegram: true,
      })
    })

    it('patches a partial update and caches the merged result', async () => {
      const merged = { notify_email: true, notify_push: false, notify_telegram: true }
      api.patch.mockResolvedValue({ data: merged })
      const store = useNotificationStore()

      const result = await store.updateGlobalChannelSettings({ notify_push: false })

      expect(api.patch).toHaveBeenCalledWith({
        url: '/notifications/channel-settings',
        body: { notify_push: false },
      })
      expect(result).toEqual(merged)
      expect(store.globalChannelSettings).toEqual(merged)
    })

    it('rethrows when the update fails', async () => {
      api.patch.mockRejectedValue(new Error('500'))
      const store = useNotificationStore()

      await expect(store.updateGlobalChannelSettings({ notify_push: false })).rejects.toThrow('500')
    })
  })

  describe('push subscriptions', () => {
    it('returns the VAPID public key', async () => {
      api.get.mockResolvedValue({ data: { vapid_public_key: 'BKey' } })
      const store = useNotificationStore()

      await expect(store.fetchVapidPublicKey()).resolves.toBe('BKey')
      expect(api.get).toHaveBeenCalledWith({ url: '/notifications/vapid-public-key' })
    })

    it('returns null when push is not configured server-side', async () => {
      api.get.mockRejectedValue(new Error('404'))
      const store = useNotificationStore()

      await expect(store.fetchVapidPublicKey()).resolves.toBeNull()
    })

    it('registers a browser subscription with its keys and user agent', async () => {
      api.post.mockResolvedValue(undefined)
      const store = useNotificationStore()
      const browserSubscription = {
        toJSON: () => ({
          endpoint: 'https://push.example.test/abc',
          keys: { p256dh: 'pub', auth: 'secret' },
        }),
      } as unknown as PushSubscription

      await store.registerPushSubscription(browserSubscription)

      expect(api.post).toHaveBeenCalledWith({
        url: '/notifications/push-subscriptions',
        body: {
          endpoint: 'https://push.example.test/abc',
          p256dh_key: 'pub',
          auth_key: 'secret',
          user_agent: 'vitest-agent',
        },
      })
    })

    it('falls back to empty key strings when the browser omits them', async () => {
      api.post.mockResolvedValue(undefined)
      const store = useNotificationStore()
      const browserSubscription = {
        toJSON: () => ({ endpoint: 'https://push.example.test/abc' }),
      } as unknown as PushSubscription

      await store.registerPushSubscription(browserSubscription)

      expect(api.post).toHaveBeenCalledWith({
        url: '/notifications/push-subscriptions',
        body: {
          endpoint: 'https://push.example.test/abc',
          p256dh_key: '',
          auth_key: '',
          user_agent: 'vitest-agent',
        },
      })
    })

    it('rethrows when registration fails', async () => {
      api.post.mockRejectedValue(new Error('500'))
      const store = useNotificationStore()
      const browserSubscription = {
        toJSON: () => ({ endpoint: 'e', keys: { p256dh: 'p', auth: 'a' } }),
      } as unknown as PushSubscription

      await expect(store.registerPushSubscription(browserSubscription)).rejects.toThrow('500')
      expect(console.error).toHaveBeenCalled()
    })

    it('reports whether the test push succeeded', async () => {
      api.post.mockResolvedValue({ data: { success: false } })
      const store = useNotificationStore()

      await expect(store.sendTestPush()).resolves.toBe(false)
      expect(api.post).toHaveBeenCalledWith({ url: '/notifications/test-push' })
    })

    it('lists the registered devices', async () => {
      api.get.mockResolvedValue({ data: [pushInfo] })
      const store = useNotificationStore()

      const result = await store.fetchPushSubscriptions()

      expect(api.get).toHaveBeenCalledWith({ url: '/notifications/push-subscriptions' })
      expect(result).toEqual([pushInfo])
      expect(store.pushSubscriptions).toEqual([pushInfo])
    })

    it('rethrows when listing devices fails', async () => {
      api.get.mockRejectedValue(new Error('500'))
      const store = useNotificationStore()

      await expect(store.fetchPushSubscriptions()).rejects.toThrow('500')
      expect(store.pushSubscriptions).toEqual([])
    })

    it('removes a device from the cached list', async () => {
      const store = useNotificationStore()
      store.pushSubscriptions = [pushInfo, { ...pushInfo, id: 'ps2' }]
      api.del.mockResolvedValue(undefined)

      await store.removePushSubscription('ps1')

      expect(api.del).toHaveBeenCalledWith({ url: '/notifications/push-subscriptions/ps1' })
      expect(store.pushSubscriptions.map((s) => s.id)).toEqual(['ps2'])
    })

    it('keeps the device listed when removal fails', async () => {
      const store = useNotificationStore()
      store.pushSubscriptions = [pushInfo]
      api.del.mockRejectedValue(new Error('500'))

      await expect(store.removePushSubscription('ps1')).rejects.toThrow('500')
      expect(store.pushSubscriptions).toHaveLength(1)
    })
  })

  describe('telegram', () => {
    it('reads the bot configuration', async () => {
      api.get.mockResolvedValue({ data: { bot_username: 'wirksam_bot', is_configured: true } })
      const store = useNotificationStore()

      const result = await store.fetchTelegramConfig()

      expect(api.get).toHaveBeenCalledWith({ url: '/notifications/telegram/config' })
      expect(result).toEqual({ bot_username: 'wirksam_bot', is_configured: true })
      expect(store.telegramBotUsername).toBe('wirksam_bot')
      expect(store.telegramConfigured).toBe(true)
    })

    it('treats a failed config lookup as "not configured"', async () => {
      api.get.mockRejectedValue(new Error('500'))
      const store = useNotificationStore()

      await expect(store.fetchTelegramConfig()).resolves.toBeNull()
      expect(store.telegramConfigured).toBe(false)
    })

    it('caches the current binding', async () => {
      api.get.mockResolvedValue({ data: binding })
      const store = useNotificationStore()

      const result = await store.fetchTelegramBinding()

      expect(api.get).toHaveBeenCalledWith({ url: '/notifications/telegram' })
      expect(result).toEqual(binding)
      expect(store.telegramBinding).toEqual(binding)
    })

    it('clears the binding when the lookup fails', async () => {
      const store = useNotificationStore()
      store.telegramBinding = binding
      api.get.mockRejectedValue(new Error('500'))

      await expect(store.fetchTelegramBinding()).resolves.toBeNull()
      expect(store.telegramBinding).toBeNull()
    })

    it('starts a binding and returns the verification code', async () => {
      const payload = {
        verification_code: '123456',
        bot_username: 'wirksam_bot',
        expires_at: '2026-08-04T12:00:00Z',
      }
      api.post.mockResolvedValue({ data: payload })
      const store = useNotificationStore()

      await expect(store.startTelegramBinding()).resolves.toEqual(payload)
      expect(api.post).toHaveBeenCalledWith({ url: '/notifications/telegram/bind' })
    })

    it('rethrows when starting a binding fails', async () => {
      api.post.mockRejectedValue(new Error('500'))
      const store = useNotificationStore()

      await expect(store.startTelegramBinding()).rejects.toThrow('500')
    })

    it('stores the binding returned by the Telegram login widget', async () => {
      api.post.mockResolvedValue({ data: binding })
      const store = useNotificationStore()
      const widgetData = { id: 42, username: 'volunteer', auth_date: 1754300000, hash: 'abc' }

      const result = await store.loginWithTelegram(widgetData)

      expect(api.post).toHaveBeenCalledWith({
        url: '/notifications/telegram/login',
        body: widgetData,
      })
      expect(result).toEqual(binding)
      expect(store.telegramBinding).toEqual(binding)
    })

    it('rethrows when the widget login is rejected', async () => {
      api.post.mockRejectedValue(new Error('bad hash'))
      const store = useNotificationStore()

      await expect(
        store.loginWithTelegram({ id: 42, auth_date: 1754300000, hash: 'nope' }),
      ).rejects.toThrow('bad hash')
      expect(store.telegramBinding).toBeNull()
    })

    it('verifies a code and stores the binding', async () => {
      api.post.mockResolvedValue({ data: binding })
      const store = useNotificationStore()

      const result = await store.verifyTelegramBinding('123456', '4242', 'volunteer')

      expect(api.post).toHaveBeenCalledWith({
        url: '/notifications/telegram/verify',
        body: {
          verification_code: '123456',
          telegram_chat_id: '4242',
          telegram_username: 'volunteer',
        },
      })
      expect(result).toEqual(binding)
      expect(store.telegramBinding).toEqual(binding)
    })

    it('sends an undefined username when none is known', async () => {
      api.post.mockResolvedValue({ data: binding })
      const store = useNotificationStore()

      await store.verifyTelegramBinding('123456', '4242')

      expect(api.post).toHaveBeenCalledWith({
        url: '/notifications/telegram/verify',
        body: {
          verification_code: '123456',
          telegram_chat_id: '4242',
          telegram_username: undefined,
        },
      })
    })

    it('rethrows an invalid verification code', async () => {
      api.post.mockRejectedValue(new Error('400'))
      const store = useNotificationStore()

      await expect(store.verifyTelegramBinding('000000', '4242')).rejects.toThrow('400')
      expect(store.telegramBinding).toBeNull()
    })

    it('clears the binding after unbinding', async () => {
      const store = useNotificationStore()
      store.telegramBinding = binding
      api.del.mockResolvedValue(undefined)

      await store.unbindTelegram()

      expect(api.del).toHaveBeenCalledWith({ url: '/notifications/telegram' })
      expect(store.telegramBinding).toBeNull()
    })

    it('keeps the binding when unbinding fails', async () => {
      const store = useNotificationStore()
      store.telegramBinding = binding
      api.del.mockRejectedValue(new Error('500'))

      await expect(store.unbindTelegram()).rejects.toThrow('500')
      expect(store.telegramBinding).toEqual(binding)
    })
  })

  describe('real-time stream', () => {
    beforeEach(() => {
      vi.useFakeTimers()
      api.getAuthToken.mockResolvedValue('tok en+/')
      api.get.mockResolvedValue({ data: { unread_count: 1 } })
    })

    afterEach(() => {
      vi.clearAllTimers()
      vi.useRealTimers()
    })

    it('opens an EventSource with the URL-encoded token', async () => {
      const store = useNotificationStore()

      await store.startStream()

      expect(FakeEventSource.instances).toHaveLength(1)
      expect(lastEventSource().url).toBe(
        `http://api.test/api/v1/notifications/stream?token=${encodeURIComponent('tok en+/')}`,
      )

      store.stopStream()
    })

    it('applies unread counts pushed over the stream', async () => {
      const store = useNotificationStore()
      await store.startStream()

      lastEventSource().emit('unread_count', JSON.stringify({ unread_count: 7 }))

      expect(store.unreadCount).toBe(7)

      store.stopStream()
    })

    it('logs and ignores a malformed stream payload', async () => {
      const store = useNotificationStore()
      await store.startStream()

      lastEventSource().emit('unread_count', 'definitely not json')

      expect(store.unreadCount).toBe(0)
      expect(console.error).toHaveBeenCalled()

      store.stopStream()
    })

    it('closes the previous connection when restarted', async () => {
      const store = useNotificationStore()
      await store.startStream()
      const first = lastEventSource()

      await store.startStream()

      expect(first.closed).toBe(true)
      expect(FakeEventSource.instances).toHaveLength(2)

      store.stopStream()
    })

    it('polls instead of streaming when no token is available', async () => {
      api.getAuthToken.mockRejectedValue(new Error('not authenticated'))
      const store = useNotificationStore()

      await store.startStream()
      await vi.advanceTimersByTimeAsync(0)

      expect(FakeEventSource.instances).toHaveLength(0)
      expect(api.get).toHaveBeenCalledWith({ url: '/notifications/unread-count' })
      expect(api.get).toHaveBeenCalledTimes(1)
      expect(store.unreadCount).toBe(1)

      await vi.advanceTimersByTimeAsync(30_000)
      expect(api.get).toHaveBeenCalledTimes(2)

      store.stopStream()
    })

    it('starts polling immediately after a connection error', async () => {
      const store = useNotificationStore()
      await store.startStream()
      const first = lastEventSource()

      first.onerror?.()
      await vi.advanceTimersByTimeAsync(0)

      expect(first.closed).toBe(true)
      expect(api.get).toHaveBeenCalledWith({ url: '/notifications/unread-count' })

      store.stopStream()
    })

    it('reconnects after the backoff delay', async () => {
      const store = useNotificationStore()
      await store.startStream()

      lastEventSource().onerror?.()
      await vi.advanceTimersByTimeAsync(999)
      expect(FakeEventSource.instances).toHaveLength(1)

      await vi.advanceTimersByTimeAsync(1)
      expect(FakeEventSource.instances).toHaveLength(2)

      store.stopStream()
    })

    it('doubles the retry delay while a single outage keeps erroring', async () => {
      const store = useNotificationStore()
      await store.startStream()
      const first = lastEventSource()

      // Two errors on the same connection: the first schedules a retry at +1s,
      // the second at +2s because the backoff has already doubled.
      first.onerror?.()
      first.onerror?.()

      await vi.advanceTimersByTimeAsync(1000)
      expect(FakeEventSource.instances).toHaveLength(2)

      await vi.advanceTimersByTimeAsync(999)
      expect(FakeEventSource.instances).toHaveLength(2)

      await vi.advanceTimersByTimeAsync(1)
      expect(FakeEventSource.instances).toHaveLength(3)

      store.stopStream()
    })

    it('restarts the backoff window on every reconnect attempt', async () => {
      const store = useNotificationStore()
      await store.startStream()

      lastEventSource().onerror?.()
      await vi.advanceTimersByTimeAsync(1000)
      expect(FakeEventSource.instances).toHaveLength(2)

      // `startStream` begins with `stopStream`, which resets the delay — so the
      // next outage is retried after 1s again rather than after 2s.
      lastEventSource().onerror?.()
      await vi.advanceTimersByTimeAsync(1000)

      expect(FakeEventSource.instances).toHaveLength(3)

      store.stopStream()
    })

    it('stops polling once the stream is back up', async () => {
      const store = useNotificationStore()
      await store.startStream()

      lastEventSource().onerror?.()
      await vi.advanceTimersByTimeAsync(1000)
      lastEventSource().onopen?.()
      api.get.mockClear()

      await vi.advanceTimersByTimeAsync(60_000)

      expect(api.get).not.toHaveBeenCalled()

      store.stopStream()
    })

    it('closes the connection and cancels the pending reconnect', async () => {
      const store = useNotificationStore()
      await store.startStream()
      const first = lastEventSource()

      first.onerror?.()
      store.stopStream()
      api.get.mockClear()

      await vi.advanceTimersByTimeAsync(60_000)

      expect(FakeEventSource.instances).toHaveLength(1)
      expect(api.get).not.toHaveBeenCalled()
    })

    it('is safe to stop a stream that was never started', () => {
      const store = useNotificationStore()

      expect(() => store.stopStream()).not.toThrow()
    })
  })
})
