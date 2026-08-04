import { nextTick, reactive } from 'vue'

import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { type BreadcrumbItem, useBreadcrumbStore } from '@/stores/breadcrumb'

/**
 * The store calls `useRoute()` during setup, so `vue-router` is replaced with a
 * reactive stub. The factory is lazy (it only runs when `breadcrumb.ts` imports
 * the module), and `useRoute` dereferences `route` at call time — by then the
 * module-scope `const` below is initialised.
 */
vi.mock('vue-router', () => ({
  useRoute: () => route,
}))

interface RouteStub {
  path: string
  name: string | undefined
  meta: { breadcrumbs?: BreadcrumbItem[] }
}

const route = reactive<RouteStub>({ path: '/', name: 'home', meta: {} })

function setRoute(patch: Partial<RouteStub>) {
  Object.assign(route, patch)
}

beforeEach(() => {
  setRoute({ path: '/', name: 'home', meta: {} })
  setActivePinia(createPinia())
})

describe('useBreadcrumbStore', () => {
  describe('initial state', () => {
    it('starts with no breadcrumbs on the root route', () => {
      const store = useBreadcrumbStore()

      expect(store.breadcrumbs).toEqual([])
    })
  })

  describe('breadcrumbs generated from the route path', () => {
    it('prepends Home and links every segment but the last', () => {
      setRoute({ path: '/events/shift-plan', name: 'shift-plan' })
      const store = useBreadcrumbStore()

      expect(store.breadcrumbs).toEqual([
        { title: 'Home', to: '/' },
        { title: 'Events', to: '/events' },
        { title: 'Shift plan', to: undefined },
      ])
    })

    it('title-cases segments and turns the first dash into a space', () => {
      setRoute({ path: '/my-bookings', name: 'my-bookings' })
      const store = useBreadcrumbStore()

      expect(store.breadcrumbs).toEqual([
        { title: 'Home', to: '/' },
        { title: 'My bookings', to: undefined },
      ])
    })

    it('skips raw `:param` segments', () => {
      setRoute({ path: '/events/:id', name: 'event-detail' })
      const store = useBreadcrumbStore()

      expect(store.breadcrumbs).toEqual([
        { title: 'Home', to: '/' },
        { title: 'Events', to: '/events' },
      ])
    })

    it('ignores empty segments produced by trailing slashes', () => {
      setRoute({ path: '/events/', name: 'events' })
      const store = useBreadcrumbStore()

      expect(store.breadcrumbs).toEqual([
        { title: 'Home', to: '/' },
        { title: 'Events', to: undefined },
      ])
    })
  })

  describe('breadcrumb sources and their precedence', () => {
    it('uses route.meta.breadcrumbs when present', () => {
      const meta: BreadcrumbItem[] = [{ title: 'Meta', titleKey: 'nav.meta', to: '/meta' }]
      setRoute({ path: '/anything/deep', name: 'anything', meta: { breadcrumbs: meta } })
      const store = useBreadcrumbStore()

      expect(store.breadcrumbs).toEqual(meta)
    })

    it('prefers dynamic breadcrumbs over route meta', () => {
      setRoute({
        path: '/anything',
        name: 'anything',
        meta: { breadcrumbs: [{ title: 'Meta' }] },
      })
      const store = useBreadcrumbStore()

      store.setBreadcrumbs([{ title: 'Dynamic' }])

      expect(store.breadcrumbs).toEqual([{ title: 'Dynamic' }])
    })
  })

  describe('setBreadcrumbs / addBreadcrumb / clearBreadcrumbs', () => {
    it('replaces the whole trail', () => {
      const store = useBreadcrumbStore()

      store.setBreadcrumbs([{ title: 'A' }, { title: 'B' }])

      expect(store.breadcrumbs).toEqual([{ title: 'A' }, { title: 'B' }])
    })

    it('appends a single crumb', () => {
      const store = useBreadcrumbStore()
      store.setBreadcrumbs([{ title: 'A' }])

      store.addBreadcrumb({ title: 'B', disabled: true })

      expect(store.breadcrumbs).toEqual([{ title: 'A' }, { title: 'B', disabled: true }])
    })

    it('appends onto an empty trail', () => {
      const store = useBreadcrumbStore()

      store.addBreadcrumb({ title: 'Solo' })

      expect(store.breadcrumbs).toEqual([{ title: 'Solo' }])
    })

    it('falls back to the generated trail after clearing', () => {
      setRoute({ path: '/events', name: 'events' })
      const store = useBreadcrumbStore()
      store.setBreadcrumbs([{ title: 'Dynamic' }])

      store.clearBreadcrumbs()

      expect(store.breadcrumbs).toEqual([
        { title: 'Home', to: '/' },
        { title: 'Events', to: undefined },
      ])
    })
  })

  describe('setDynamicTitle', () => {
    it('renames the last crumb and drops its translation key', () => {
      const store = useBreadcrumbStore()
      store.setBreadcrumbs([
        { title: 'Events', to: '/events' },
        { title: 'Loading…', titleKey: 'nav.loading' },
      ])

      store.setDynamicTitle('Summer Festival')

      expect(store.breadcrumbs).toEqual([
        { title: 'Events', to: '/events' },
        { title: 'Summer Festival', titleKey: undefined },
      ])
    })

    it('promotes a route-generated trail into the dynamic trail', () => {
      setRoute({ path: '/events/abc', name: 'event-detail' })
      const store = useBreadcrumbStore()

      store.setDynamicTitle('Summer Festival')

      expect(store.breadcrumbs).toEqual([
        { title: 'Home', to: '/' },
        { title: 'Events', to: '/events' },
        { title: 'Summer Festival', to: undefined, titleKey: undefined },
      ])
    })

    it('is a no-op when there are no breadcrumbs at all', () => {
      const store = useBreadcrumbStore()

      store.setDynamicTitle('Nothing to rename')

      expect(store.breadcrumbs).toEqual([])
    })
  })

  describe('route watcher', () => {
    it('clears dynamic breadcrumbs when the route name changes', async () => {
      setRoute({ path: '/events', name: 'events' })
      const store = useBreadcrumbStore()
      store.setBreadcrumbs([{ title: 'Dynamic' }])

      setRoute({ path: '/tasks', name: 'tasks' })
      await nextTick()

      expect(store.breadcrumbs).toEqual([
        { title: 'Home', to: '/' },
        { title: 'Tasks', to: undefined },
      ])
    })

    it('keeps dynamic breadcrumbs when only params change', async () => {
      setRoute({ path: '/events/a', name: 'event-detail' })
      const store = useBreadcrumbStore()
      store.setBreadcrumbs([{ title: 'Dynamic', mobileSkip: true }])

      setRoute({ path: '/events/b' })
      await nextTick()

      expect(store.breadcrumbs).toEqual([{ title: 'Dynamic', mobileSkip: true }])
    })

    it('leaves the fallback trail alone when nothing was set dynamically', async () => {
      setRoute({ path: '/events', name: 'events' })
      const store = useBreadcrumbStore()

      setRoute({ path: '/tasks', name: 'tasks', meta: { breadcrumbs: [{ title: 'Tasks meta' }] } })
      await nextTick()

      expect(store.breadcrumbs).toEqual([{ title: 'Tasks meta' }])
    })
  })
})
