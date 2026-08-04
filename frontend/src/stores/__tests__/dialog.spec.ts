import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useDialogStore } from '@/stores/dialog'

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('useDialogStore', () => {
  describe('initial state', () => {
    it('is closed with confirm/default presets', () => {
      const store = useDialogStore()

      expect(store.dialog).toEqual({
        isOpen: false,
        title: '',
        text: '',
        type: 'confirm',
        variant: 'default',
      })
    })
  })

  describe('confirm', () => {
    it('opens the dialog and applies the confirm/default presets', () => {
      const store = useDialogStore()

      const pending = store.confirm({ text: 'Delete this shift?' })

      expect(store.dialog.isOpen).toBe(true)
      expect(store.dialog.text).toBe('Delete this shift?')
      expect(store.dialog.type).toBe('confirm')
      expect(store.dialog.variant).toBe('default')

      store.dialog.onConfirm?.()
      return expect(pending).resolves.toBe(true)
    })

    it('keeps every caller-supplied option', async () => {
      const store = useDialogStore()

      const pending = store.confirm({
        title: 'Danger',
        text: 'This cannot be undone.',
        confirmText: 'Delete',
        cancelText: 'Keep',
        confirmIcon: 'trash',
        cancelIcon: 'x',
        type: 'info',
        variant: 'destructive',
      })

      expect(store.dialog.title).toBe('Danger')
      expect(store.dialog.confirmText).toBe('Delete')
      expect(store.dialog.cancelText).toBe('Keep')
      expect(store.dialog.confirmIcon).toBe('trash')
      expect(store.dialog.cancelIcon).toBe('x')
      expect(store.dialog.type).toBe('info')
      expect(store.dialog.variant).toBe('destructive')

      store.dialog.onCancel?.()
      await expect(pending).resolves.toBe(false)
    })

    it('resolves true and closes when confirmed', async () => {
      const store = useDialogStore()
      const pending = store.confirm({ text: 'Sure?' })

      const onConfirm = store.dialog.onConfirm
      expect(onConfirm).toBeDefined()
      await onConfirm?.()

      await expect(pending).resolves.toBe(true)
      expect(store.dialog.isOpen).toBe(false)
    })

    it('resolves false and closes when cancelled', async () => {
      const store = useDialogStore()
      const pending = store.confirm({ text: 'Sure?' })

      const onCancel = store.dialog.onCancel
      expect(onCancel).toBeDefined()
      await onCancel?.()

      await expect(pending).resolves.toBe(false)
      expect(store.dialog.isOpen).toBe(false)
    })

    it('lets a second confirm replace the first without leaking handlers', async () => {
      const store = useDialogStore()
      const first = store.confirm({ text: 'First' })
      const firstCancel = store.dialog.onCancel

      const second = store.confirm({ text: 'Second' })

      expect(store.dialog.text).toBe('Second')
      store.dialog.onConfirm?.()
      await expect(second).resolves.toBe(true)

      firstCancel?.()
      await expect(first).resolves.toBe(false)
    })
  })

  describe('alert', () => {
    it('opens as an alert with no cancel handler', async () => {
      const store = useDialogStore()

      const pending = store.alert({ title: 'Heads up', text: 'Saved.' })

      expect(store.dialog.isOpen).toBe(true)
      expect(store.dialog.type).toBe('alert')
      expect(store.dialog.variant).toBe('default')
      expect(store.dialog.onCancel).toBeUndefined()

      const onConfirm = store.dialog.onConfirm
      expect(onConfirm).toBeDefined()
      await onConfirm?.()

      await expect(pending).resolves.toBeUndefined()
      expect(store.dialog.isOpen).toBe(false)
    })

    it('honours a custom variant', () => {
      const store = useDialogStore()

      const pending = store.alert({ text: 'Boom', variant: 'destructive' })

      expect(store.dialog.variant).toBe('destructive')

      store.dialog.onConfirm?.()
      return expect(pending).resolves.toBeUndefined()
    })
  })

  describe('close', () => {
    it('closes an open dialog', () => {
      const store = useDialogStore()
      const pending = store.confirm({ text: 'Sure?' })

      store.close()

      expect(store.dialog.isOpen).toBe(false)
      // The promise stays pending until a handler runs — resolve it so the
      // test does not leave a dangling promise behind.
      store.dialog.onCancel?.()
      return expect(pending).resolves.toBe(false)
    })

    it('is idempotent when nothing is open', () => {
      const store = useDialogStore()

      store.close()
      store.close()

      expect(store.dialog.isOpen).toBe(false)
    })
  })
})
