// @vitest-environment jsdom
/**
 * The engine's DOM-bound half: what a tour leaves behind when it ends.
 *
 * `tracks.spec.ts` walks the step data; nothing else stands the engine up
 * against a real dialog, which is where the two halves disagreed — a step that
 * opens a modal to reach its anchor left that modal open, and a reka-ui modal
 * takes `pointer-events` away from the whole document while it is up.
 */
import { mount } from '@vue/test-utils'
import { defineComponent, h, nextTick, ref } from 'vue'

import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { useTourStore } from '@/stores/tour'

import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'

import { createTourController } from '@/tour/engine'

const Blank = defineComponent({ render: () => h('div') })

/** The helper track's `bookShift` step — the only `inOverlay` one. */
const OVERLAY_STEP_INDEX = 4

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: Blank },
      { path: '/tasks', name: 'tasks', component: Blank },
      { path: '/availability', name: 'availability', component: Blank },
      { path: '/my-bookings', name: 'my-bookings', component: Blank },
    ],
  })
}

/** A modal dialog, mounted open, the way `ShiftDetailDialog` renders one. */
function mountOpenDialog() {
  return mount(
    defineComponent({
      // Registered under a different name because `Dialog` is a reserved HTML
      // element name, which `vue/no-reserved-component-names` rejects.
      components: { DialogRoot: Dialog, DialogContent, DialogDescription, DialogTitle },
      setup: () => ({ open: ref(true) }),
      template: `
        <DialogRoot v-model:open="open">
          <DialogContent data-testid="dialog-shift-detail">
            <DialogTitle>Shift</DialogTitle>
            <DialogDescription>Details</DialogDescription>
          </DialogContent>
        </DialogRoot>
      `,
    }),
    { attachTo: document.body },
  )
}

/**
 * Long enough for driver's own animation frame and for reka-ui to unmount a
 * dismissed dialog — the `pointer-events` it took off `<body>` comes back in a
 * watcher cleanup, several ticks after the key lands.
 */
const settle = () => new Promise((resolve) => setTimeout(resolve, 100))

describe('tour engine', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    document.body.innerHTML = ''
    document.body.style.pointerEvents = ''
    sessionStorage.clear()
    // jsdom measures everything at 0×0, and `firstVisible` rejects that.
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
      width: 120,
      height: 40,
      top: 0,
      left: 0,
      right: 120,
      bottom: 40,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    } as DOMRect)
    window.matchMedia = ((query: string) => ({
      matches: true,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia
  })

  it('hands the document back when a tour is dismissed inside a dialog', async () => {
    const dialog = mountOpenDialog()
    await nextTick()
    // The premise: a reka-ui modal takes pointer events off the whole body, so
    // everything outside it — the demo banner's "restart the tour" included —
    // stops receiving clicks.
    expect(document.body.style.pointerEvents).toBe('none')

    const router = makeRouter()
    await router.push('/tasks')
    await router.isReady()
    const controller = createTourController(router)

    const store = useTourStore()
    store.start('helper')
    store.goTo(OVERLAY_STEP_INDEX)
    expect(store.currentStep?.inOverlay).toBe(true)

    controller.stop()
    await settle()

    expect(document.body.style.pointerEvents).not.toBe('none')
    dialog.unmount()
  })

  it('draws a popover again after the visitor closes the tour', async () => {
    const router = makeRouter()
    await router.push('/')
    await router.isReady()
    const controller = createTourController(router)
    router.afterEach((to) => controller.handleRouteChange(to))

    document.body.innerHTML =
      '<div data-testid="main-content"><h1 data-testid="page-heading">Dashboard</h1></div>'

    controller.start('helper')
    await settle()
    expect(document.querySelector('.driver-popover')).not.toBeNull()

    document.querySelector<HTMLElement>('.driver-popover-close-btn')!.click()
    await settle()
    expect(document.querySelector('.driver-popover')).toBeNull()
    expect(useTourStore().status).toBe('idle')

    controller.start('helper')
    await settle()
    expect(useTourStore().status).toBe('running')
    expect(document.querySelector('.driver-popover')).not.toBeNull()
  })
})
