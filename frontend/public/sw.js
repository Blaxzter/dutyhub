
/**
 * Service Worker for Web Push Notifications
 */

self.addEventListener('push', (task) => {
  if (!task.data) return

  let data
  try {
    data = task.data.json()
  } catch {
    data = { title: 'Notification', body: task.data.text() }
  }

  const options = {
    body: data.body || '',
    icon: data.icon || '/favicon.ico',
    badge: '/favicon.ico',
    data: data.data || {},
    tag: data.data?.notification_type_code || 'default',
    renotify: true,
  }

  task.waitUntil(self.registration.showNotification(data.title || 'WirkSam', options))
})

self.addEventListener('notificationclick', (task) => {
  task.notification.close()

  const data = task.notification.data || {}
  let url = '/app/home'

  if (data.task_id) {
    url = `/app/tasks/${data.task_id}`
  } else if (data.event_id) {
    url = `/app/events/${data.event_id}`
  } else if (data.booking_id) {
    url = '/app/bookings'
  }

  task.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes('/app') && 'focus' in client) {
          client.navigate(url)
          return client.focus()
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(url)
      }
    }),
  )
})
