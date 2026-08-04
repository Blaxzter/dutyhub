// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Palette } from '../usePalette'

/**
 * `usePalette` is a module-level singleton: one `useLocalStorage` ref plus one
 * `watchEffect` that mirrors the ref onto `<html>` as the `palette-classic`
 * class. Both are created when the module is first evaluated, so the only way
 * to exercise a different starting point is to seed `localStorage`, call
 * `vi.resetModules()` and re-import.
 *
 * `resetModules()` also swaps out Vue itself, so the freshly imported
 * `nextTick` has to be used to flush the (pre-flush) watcher — a `nextTick`
 * imported statically at the top of this file would belong to a different
 * scheduler queue and would resolve without running anything.
 */
const STORAGE_KEY = 'wirksam-palette'
const CLASSIC_CLASS = 'palette-classic'

async function load(stored: string | null = null) {
  localStorage.clear()
  document.documentElement.className = ''
  if (stored !== null) localStorage.setItem(STORAGE_KEY, stored)
  vi.resetModules()
  const { usePalette } = await import('../usePalette')
  const { nextTick } = await import('vue')
  return { usePalette, palette: usePalette(), nextTick }
}

const hasClassicClass = () => document.documentElement.classList.contains(CLASSIC_CLASS)

beforeEach(() => {
  localStorage.clear()
  document.documentElement.className = ''
})

describe('usePalette', () => {
  describe('initial value', () => {
    it("defaults to 'default' when nothing is stored", async () => {
      const { palette } = await load()
      expect(palette.value).toBe('default')
    })

    it("restores 'classic' from localStorage", async () => {
      const { palette } = await load('classic')
      expect(palette.value).toBe('classic')
    })

    it("restores 'default' from localStorage", async () => {
      const { palette } = await load('default')
      expect(palette.value).toBe('default')
    })

    it('passes an unrecognised stored value straight through', async () => {
      const { palette } = await load('midnight-neon')
      expect(palette.value).toBe('midnight-neon')
    })
  })

  describe('class derivation on <html>', () => {
    it('adds no class for the default palette', async () => {
      await load()
      expect(hasClassicClass()).toBe(false)
      expect(document.documentElement.className).toBe('')
    })

    it('adds the classic class immediately when classic is restored', async () => {
      await load('classic')
      expect(hasClassicClass()).toBe(true)
    })

    it('falls back to the unstyled (non-classic) branch for an unknown palette', async () => {
      await load('midnight-neon')
      expect(hasClassicClass()).toBe(false)
    })

    it('adds the class when switching to classic', async () => {
      const { palette, nextTick } = await load()
      expect(hasClassicClass()).toBe(false)

      palette.value = 'classic'
      await nextTick()
      expect(hasClassicClass()).toBe(true)
    })

    it('removes the class when switching back to default', async () => {
      const { palette, nextTick } = await load('classic')
      expect(hasClassicClass()).toBe(true)

      palette.value = 'default'
      await nextTick()
      expect(hasClassicClass()).toBe(false)
    })

    it('is idempotent — repeated switches never duplicate the class', async () => {
      const { palette, nextTick } = await load()

      for (const next of ['classic', 'classic', 'default', 'classic'] as Palette[]) {
        palette.value = next
        await nextTick()
      }

      expect(hasClassicClass()).toBe(true)
      expect(document.documentElement.className.split(/\s+/).filter(Boolean)).toEqual([
        CLASSIC_CLASS,
      ])
    })

    it('leaves unrelated classes on <html> alone', async () => {
      const { palette, nextTick } = await load()
      document.documentElement.classList.add('dark')

      palette.value = 'classic'
      await nextTick()
      expect(document.documentElement.classList.contains('dark')).toBe(true)
      expect(hasClassicClass()).toBe(true)

      palette.value = 'default'
      await nextTick()
      expect(document.documentElement.classList.contains('dark')).toBe(true)
      expect(hasClassicClass()).toBe(false)
    })
  })

  describe('persistence', () => {
    it('writes the selected palette to localStorage', async () => {
      const { palette, nextTick } = await load()

      palette.value = 'classic'
      await nextTick()
      expect(localStorage.getItem(STORAGE_KEY)).toBe('classic')

      palette.value = 'default'
      await nextTick()
      expect(localStorage.getItem(STORAGE_KEY)).toBe('default')
    })

    it('survives a reload of the module', async () => {
      const first = await load()
      first.palette.value = 'classic'
      await first.nextTick()

      // Reload without clearing storage, the way a page refresh would.
      vi.resetModules()
      const { usePalette } = await import('../usePalette')
      expect(usePalette().value).toBe('classic')
    })
  })

  describe('singleton behaviour', () => {
    it('hands every caller the very same ref', async () => {
      const { usePalette, palette, nextTick } = await load()
      const other = usePalette()

      expect(other).toBe(palette)

      other.value = 'classic'
      await nextTick()
      expect(palette.value).toBe('classic')
      expect(hasClassicClass()).toBe(true)
    })

    it('is deterministic — the same stored value always yields the same result', async () => {
      const a = await load('classic')
      const first = { value: a.palette.value, classic: hasClassicClass() }
      const b = await load('classic')
      const second = { value: b.palette.value, classic: hasClassicClass() }

      expect(second).toEqual(first)
      expect(second).toEqual({ value: 'classic', classic: true })
    })
  })
})
