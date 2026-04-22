import { authGuard as _authGuard } from '@auth0/auth0-vue'
import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import type { BreadcrumbItem } from '@/stores/breadcrumb'

// In E2E bypass mode, skip Auth0's authGuard entirely since the fake plugin
// doesn't set the module-level client ref that authGuard reads.
const authGuard =
  import.meta.env.VITE_E2E_AUTH_BYPASS === 'true' && document.cookie.includes('e2e_bypass=1')
    ? () => true
    : _authGuard

// Extend route meta to include breadcrumbs and layout
declare module 'vue-router' {
  interface RouteMeta {
    breadcrumbs?: BreadcrumbItem[]
    layout?: 'preauth' | 'postauth' | 'minimal'
    requiresRole?: string | string[]
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // Layout wrappers as parent routes
    {
      path: '/',
      name: 'preauth-layout',
      component: () => import('@/layout/PreAuthLayout.vue'),
      children: [
        {
          path: '',
          name: 'landing',
          component: () => import('@/views/preauth/LandingView.vue'),
        },
        {
          path: 'about',
          name: 'about',
          component: () => import('@/views/preauth/AboutView.vue'),
        },
        {
          path: 'how-it-works',
          name: 'how-it-works',
          component: () => import('@/views/preauth/HowItWorksView.vue'),
        },
        {
          path: 'privacy',
          name: 'privacy',
          component: () => import('@/views/preauth/PrivacyView.vue'),
        },
        {
          path: 'terms',
          name: 'terms',
          component: () => import('@/views/preauth/TermsView.vue'),
        },
        {
          path: 'impressum',
          name: 'impressum',
          component: () => import('@/views/preauth/ImpressumView.vue'),
        },
        {
          path: 'changelog/:version?',
          name: 'preauth-changelog',
          component: () => import('@/views/ChangelogView.vue'),
        },
      ],
    },
    {
      path: '/app',
      name: 'postauth-layout',
      redirect: { name: 'home' },
      component: () => import('@/layout/PostAuthLayout.vue'),
      beforeEnter: authGuard,
      children: [
        {
          path: 'home',
          name: 'home',
          component: () => import('@/views/HomeView.vue'),
          meta: {
            breadcrumbs: [{ title: 'Home', titleKey: 'navigation.breadcrumbs.home' }],
          },
        },
        {
          path: 'availability',
          name: 'availability',
          component: () => import('@/views/events/AvailabilityView.vue'),
          meta: {
            breadcrumbs: [{ title: 'Availability', titleKey: 'duties.availability.title' }],
          },
        },
        {
          path: 'print',
          name: 'event-print',
          component: () => import('@/views/events/PrintView.vue'),
          meta: {
            breadcrumbs: [{ title: 'Print', titleKey: 'duties.events.detail.nav.print' }],
          },
        },
        {
          path: 'event-settings',
          name: 'event-settings',
          component: () => import('@/views/events/EventSettingsView.vue'),
          meta: {
            requiresRole: ['admin', 'task_manager'],
            breadcrumbs: [
              { title: 'Event Details', titleKey: 'duties.events.detail.title' },
            ],
          },
        },
        {
          path: 'admin/events',
          name: 'admin-events',
          component: () => import('@/views/admin/AdminEventsView.vue'),
          meta: {
            requiresRole: ['admin', 'task_manager'],
            breadcrumbs: [
              { title: 'Home', titleKey: 'navigation.breadcrumbs.home', to: { name: 'home' } },
              { title: 'Manage Events', titleKey: 'admin.events.title' },
            ],
          },
        },
        {
          path: 'tasks',
          name: 'tasks',
          component: () => import('@/views/tasks/TasksView.vue'),
          meta: {
            breadcrumbs: [{ title: 'Tasks', titleKey: 'duties.tasks.title' }],
          },
        },
        {
          path: 'tasks/create',
          name: 'task-create',
          component: () => import('@/views/tasks/TaskCreateView.vue'),
          meta: {
            requiresRole: ['admin', 'task_manager'],
            breadcrumbs: [
              { title: 'Tasks', titleKey: 'duties.tasks.title', to: { name: 'tasks' } },
              { title: 'Create Task', titleKey: 'duties.tasks.createView.title' },
            ],
          },
        },
        {
          path: 'tasks/:eventId/edit',
          name: 'task-edit',
          component: () => import('@/views/tasks/TaskEditView.vue'),
          meta: {
            requiresRole: ['admin', 'task_manager'],
            breadcrumbs: [
              { title: 'Tasks', titleKey: 'duties.tasks.title', to: { name: 'tasks' } },
              { title: 'Edit Task', titleKey: 'duties.tasks.editView.title' },
            ],
          },
        },
        {
          path: 'tasks/:eventId/add-shifts',
          name: 'task-add-shifts',
          component: () => import('@/views/tasks/TaskAddShiftsView.vue'),
          meta: {
            requiresRole: ['admin', 'task_manager'],
            breadcrumbs: [
              { title: 'Tasks', titleKey: 'duties.tasks.title', to: { name: 'tasks' } },
              { title: 'Add Shifts', titleKey: 'duties.tasks.addShiftsView.title' },
            ],
          },
        },
        {
          path: 'tasks/:eventId',
          name: 'task-detail',
          component: () => import('@/views/tasks/TaskDetailView.vue'),
          meta: {
            breadcrumbs: [
              { title: 'Tasks', titleKey: 'duties.tasks.title', to: { name: 'tasks' } },
              { title: 'Task Details', titleKey: 'duties.tasks.detail.title' },
            ],
          },
        },
        {
          path: 'bookings',
          name: 'my-bookings',
          component: () => import('@/views/bookings/MyBookingsView.vue'),
          meta: {
            breadcrumbs: [{ title: 'My Bookings', titleKey: 'duties.bookings.title' }],
          },
        },
        {
          path: 'bookings/:bookingId',
          name: 'booking-detail',
          component: () => import('@/views/bookings/BookingDetailView.vue'),
          meta: {
            breadcrumbs: [
              {
                title: 'My Bookings',
                titleKey: 'duties.bookings.title',
                to: { name: 'my-bookings' },
              },
              { title: 'Booking Details', titleKey: 'duties.bookings.detail.title' },
            ],
          },
        },
        {
          path: 'changelog/:version?',
          name: 'changelog',
          component: () => import('@/views/ChangelogView.vue'),
          meta: {
            routerViewKey: 'changelog',
            breadcrumbs: [
              { title: 'Home', titleKey: 'navigation.breadcrumbs.home', to: { name: 'home' } },
              { title: "What's New", titleKey: 'changelog.title' },
            ],
          },
        },
        {
          path: 'notifications',
          name: 'notifications',
          component: () => import('@/views/NotificationsView.vue'),
          meta: {
            breadcrumbs: [
              { title: 'Home', titleKey: 'navigation.breadcrumbs.home', to: { name: 'home' } },
              { title: 'Notifications', titleKey: 'notifications.title' },
            ],
          },
        },
        {
          path: 'settings/notification-preferences',
          name: 'notification-preferences',
          component: () => import('@/views/NotificationPreferencesView.vue'),
          meta: {
            breadcrumbs: [
              { title: 'Home', titleKey: 'navigation.breadcrumbs.home', to: { name: 'home' } },
              {
                title: 'Settings',
                titleKey: 'navigation.breadcrumbs.settings',
                to: { name: 'settings' },
              },
              { title: 'Notifications', titleKey: 'notifications.preferences.title' },
            ],
          },
        },
        {
          path: 'settings/:section?',
          name: 'settings',
          component: () => import('@/views/UserSettingsView.vue'),
          meta: {
            routerViewKey: 'settings',
            breadcrumbs: [
              { title: 'Home', titleKey: 'navigation.breadcrumbs.home', to: { name: 'home' } },
              { title: 'Settings', titleKey: 'navigation.breadcrumbs.settings' },
            ],
          },
        },
        {
          path: 'reporting',
          name: 'reporting',
          component: () => import('@/views/admin/ReportingView.vue'),
          meta: {
            requiresRole: ['admin', 'task_manager'],
            breadcrumbs: [
              { title: 'Home', titleKey: 'navigation.breadcrumbs.home', to: { name: 'home' } },
              { title: 'Reports', titleKey: 'admin.reporting.title' },
            ],
          },
        },
        {
          path: 'admin/demo-data',
          name: 'admin-demo-data',
          component: () => import('@/views/admin/DemoDataView.vue'),
          meta: {
            requiresRole: 'admin',
            breadcrumbs: [
              { title: 'Home', titleKey: 'navigation.breadcrumbs.home', to: { name: 'home' } },
              { title: 'Demo Data', titleKey: 'admin.demoData.title' },
            ],
          },
        },
        {
          path: 'admin/users',
          name: 'admin-users',
          component: () => import('@/views/admin/UsersView.vue'),
          meta: {
            requiresRole: 'admin',
            breadcrumbs: [
              { title: 'Home', titleKey: 'navigation.breadcrumbs.home', to: { name: 'home' } },
              { title: 'User Management', titleKey: 'admin.users.title' },
            ],
          },
        },
      ],
    },
    {
      path: '/print',
      name: 'print-layout',
      component: () => import('@/layout/PrintLayout.vue'),
      beforeEnter: authGuard,
      children: [
        {
          path: 'tasks/:eventId',
          name: 'print-task',
          component: () => import('@/views/print/PrintTaskView.vue'),
        },
        {
          path: 'events/:eventId',
          name: 'print-event',
          component: () => import('@/views/print/PrintEventView.vue'),
        },
      ],
    },
    {
      path: '/',
      name: 'no-layout',
      redirect: { name: 'landing' },
      component: () => import('@/layout/NoLayout.vue'),
      children: [
        {
          path: '404',
          name: 'not-found',
          component: () => import('@/views/NotFoundView.vue'),
        },
        {
          path: 'pending-approval',
          name: 'pending-approval',
          component: () => import('@/views/PendingApprovalView.vue'),
        },
      ],
    },
    {
      path: '/app/select-event',
      name: 'select-event',
      component: () => import('@/views/events/SelectEventView.vue'),
      beforeEnter: authGuard,
    },

    // Catch-all route - redirect to 404 in no layout
    {
      path: '/:pathMatch(.*)*',
      redirect: { name: 'not-found' },
    },
  ],
})

const normalizeRoles = (roles: string | string[]) => (Array.isArray(roles) ? roles : [roles])

// Routes that bypass the "must have a selected event" guard
const SELECTED_EVENT_EXEMPT_ROUTES = new Set<string>([
  'select-event',
  'admin-events',
  'event-settings',
  'admin-users',
  'admin-demo-data',
  'settings',
  'notification-preferences',
  'pending-approval',
  'changelog',
  'preauth-changelog',
])

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  // Wait for Auth0 to finish loading before checking authentication
  while (authStore.auth0.isLoading) {
    await new Promise((resolve) => setTimeout(resolve, 100))
  }

  if (authStore.isAuthenticated) {
    try {
      await authStore.ensureProfile()
    } catch (error) {
      console.error('Failed to load user profile for role check:', error)
      if (to.meta.requiresRole) {
        return { name: 'home' }
      }
    }

    // Redirect inactive users to pending approval page
    if (!authStore.isActive && to.name !== 'pending-approval') {
      return { name: 'pending-approval' }
    }
    // Don't let active users visit the pending page
    if (authStore.isActive && to.name === 'pending-approval') {
      return { name: 'home' }
    }

    // Selected-event gate: force users without a valid selection into the picker
    const routeName = typeof to.name === 'string' ? to.name : ''
    const isExempt = SELECTED_EVENT_EXEMPT_ROUTES.has(routeName)
    if (authStore.isActive && !isExempt) {
      if (!authStore.selectedEventId) {
        return { name: 'select-event', query: { mode: 'onboarding' } }
      }
      if (authStore.selectedEvent?.is_expired) {
        return { name: 'select-event', query: { mode: 'expired' } }
      }
    }
  }

  if (!to.meta.requiresRole) return true
  if (!authStore.isAuthenticated) return true

  const requiredRoles = normalizeRoles(to.meta.requiresRole)
  const hasRole = requiredRoles.some((role) => authStore.roles.includes(role))
  // Scoped event managers are allowed on routes that accept task_manager
  const eventManagerAllowed =
    !hasRole && requiredRoles.includes('task_manager') && authStore.isEventManager
  if (!hasRole && !eventManagerAllowed) {
    return { name: 'home' }
  }

  return true
})

export default router
