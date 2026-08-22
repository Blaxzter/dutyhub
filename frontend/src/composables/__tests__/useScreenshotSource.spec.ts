// @vitest-environment jsdom
import { defineComponent, nextTick } from 'vue'

import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useScreenshotSource } from '../useScreenshotSource'

/**
 * `useScreenshotSource` reads the active locale from `vue-i18n` (which needs a
 * live component instance) and watches the `dark` class on `<html>` through a
 * MutationObserver, so it is exercised through a mounted host component with
 * the smallest possible i18n stand-in.
 */
const state = vi.hoisted(() => ({ locale: 'en' as 'en' | 'de' }))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    locale: {
      get value() {
        return state.locale
      },
    },
  }),
}))

type Api = ReturnType<typeof useScreenshotSource>

function mountWith(name = 'tasks') {
  let api!: Api
  const wrapper = mount(
    defineComponent({
      setup() {
        api = useScreenshotSource(() => name)
        return () => null
      },
    }),
  )
  return { api, wrapper }
}

function setDark(on: boolean) {
  document.documentElement.classList.toggle('dark', on)
}

beforeEach(() => {
  state.locale = 'en'
  setDark(false)
})

afterEach(() => {
  setDark(false)
  vi.restoreAllMocks()
})

describe('useScreenshotSource', () => {
  it('serves the light capture for the active locale', () => {
    state.locale = 'de'
    const { api } = mountWith('my-bookings')

    expect(api.src.value).toBe('/screenshots/de/my-bookings-light.png')
    expect(api.failed.value).toBe(false)
  })

  it('picks the dark capture when the dark class is already on <html>', () => {
    setDark(true)
    const { api } = mountWith('tasks')

    expect(api.src.value).toBe('/screenshots/en/tasks-dark.png')
  })

  it('follows the theme when the class is toggled after mount', async () => {
    const { api } = mountWith('tasks')
    expect(api.src.value).toBe('/screenshots/en/tasks-light.png')

    setDark(true)
    // MutationObserver callbacks are delivered as a microtask.
    await nextTick()
    await nextTick()

    expect(api.src.value).toBe('/screenshots/en/tasks-dark.png')
  })

  it('falls back to the English capture when a locale is missing one', () => {
    state.locale = 'de'
    const { api } = mountWith('tasks')

    api.onError()

    expect(api.src.value).toBe('/screenshots/en/tasks-light.png')
    expect(api.failed.value).toBe(false)
  })

  it('gives up once the English capture fails too', () => {
    state.locale = 'de'
    const { api } = mountWith('tasks')

    api.onError()
    api.onError()

    expect(api.failed.value).toBe(true)
  })

  it('gives up immediately for English, which has no further fallback', () => {
    const { api } = mountWith('tasks')

    api.onError()

    expect(api.failed.value).toBe(true)
  })

  it('retries the localised capture when the theme changes after a failure', async () => {
    state.locale = 'de'
    const { api } = mountWith('tasks')

    api.onError()
    expect(api.src.value).toBe('/screenshots/en/tasks-light.png')

    setDark(true)
    await nextTick()
    await nextTick()

    expect(api.src.value).toBe('/screenshots/de/tasks-dark.png')
  })

  it('stops observing the document once unmounted', () => {
    const disconnect = vi.fn()
    // Stubbed as a class: the composable calls `new MutationObserver(...)`, so a
    // plain mock function returning an object does not stand in for it.
    class FakeObserver {
      observe = vi.fn()
      disconnect = disconnect
      takeRecords = vi.fn()
    }
    vi.stubGlobal('MutationObserver', FakeObserver)

    const { wrapper } = mountWith()
    wrapper.unmount()

    expect(disconnect).toHaveBeenCalled()
    vi.unstubAllGlobals()
  })
})
