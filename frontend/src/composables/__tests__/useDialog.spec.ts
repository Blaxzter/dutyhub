import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useDialog } from '@/composables/useDialog'
import { useDialogStore } from '@/stores/dialog'

/**
 * The composable is a thin ergonomics layer over `useDialogStore`: it accepts a
 * bare string where the store wants a config object, and pre-applies the
 * `type` / `variant` each helper implies. These tests assert exactly that
 * translation — the store's own behaviour is covered in stores/__tests__.
 */
beforeEach(() => {
  setActivePinia(createPinia())
})

/** The store resolves through the handlers it stores on the dialog, not close(). */
const answer = (accept: boolean) => {
  const { dialog } = useDialogStore()
  if (accept) dialog.onConfirm?.()
  else dialog.onCancel?.()
}

describe('useDialog', () => {
  describe('confirm', () => {
    it('wraps a bare string into a config', async () => {
      const store = useDialogStore()
      const { confirm } = useDialog()

      const pending = confirm('Delete this shift?')

      expect(store.dialog.text).toBe('Delete this shift?')
      expect(store.dialog.type).toBe('confirm')
      expect(store.dialog.variant).toBe('default')
      expect(store.dialog.isOpen).toBe(true)

      answer(true)
      await expect(pending).resolves.toBe(true)
    })

    it('passes a config object through untouched', async () => {
      const store = useDialogStore()
      const { confirm } = useDialog()

      const pending = confirm({ title: 'Careful', text: 'Sure?' })

      expect(store.dialog.title).toBe('Careful')
      expect(store.dialog.text).toBe('Sure?')

      answer(false)
      await expect(pending).resolves.toBe(false)
    })
  })

  describe('alert', () => {
    it('wraps a bare string into a config', async () => {
      const store = useDialogStore()
      const { alert } = useDialog()

      const pending = alert('Saved.')

      expect(store.dialog.text).toBe('Saved.')
      expect(store.dialog.type).toBe('alert')
      expect(store.dialog.isOpen).toBe(true)

      answer(true)
      await expect(pending).resolves.toBeUndefined()
    })

    it('passes a config object through', async () => {
      const store = useDialogStore()
      const { alert } = useDialog()

      const pending = alert({ title: 'Done', text: 'Saved.' })

      expect(store.dialog.title).toBe('Done')

      answer(true)
      await expect(pending).resolves.toBeUndefined()
    })
  })

  describe('info', () => {
    /**
     * Asserting the actual behaviour, not the intuitive one: `info()` sets
     * `type: 'info'`, but it routes through the store's `alert()`, which spreads
     * the config and *then* hard-sets `type: 'alert'`. So the 'info' type never
     * survives, and nothing downstream can distinguish an info dialog from an
     * alert. Pinned here so a fix to either side shows up as a failing test
     * rather than a silent behaviour change.
     */
    it('is overwritten to type "alert" by the store', async () => {
      const store = useDialogStore()
      const { info } = useDialog()

      const pending = info('Heads up.')

      expect(store.dialog.text).toBe('Heads up.')
      expect(store.dialog.type).toBe('alert')

      answer(true)
      await expect(pending).resolves.toBeUndefined()
    })

    it('keeps the rest of the config', async () => {
      const store = useDialogStore()
      const { info } = useDialog()

      const pending = info({ text: 'Heads up.', title: 'FYI' })

      expect(store.dialog.title).toBe('FYI')
      expect(store.dialog.text).toBe('Heads up.')

      answer(true)
      await expect(pending).resolves.toBeUndefined()
    })
  })

  describe('confirmDestructive', () => {
    it('forces the destructive variant for a bare string', async () => {
      const store = useDialogStore()
      const { confirmDestructive } = useDialog()

      const pending = confirmDestructive('Delete the account?')

      expect(store.dialog.text).toBe('Delete the account?')
      expect(store.dialog.variant).toBe('destructive')
      expect(store.dialog.type).toBe('confirm')

      answer(true)
      await expect(pending).resolves.toBe(true)
    })

    it('overrides a variant supplied in the config', async () => {
      const store = useDialogStore()
      const { confirmDestructive } = useDialog()

      const pending = confirmDestructive({ text: 'Delete?', variant: 'default' })

      expect(store.dialog.variant).toBe('destructive')

      answer(false)
      await expect(pending).resolves.toBe(false)
    })
  })

  describe('close', () => {
    it('is the store action, so it shuts the dialog', () => {
      const store = useDialogStore()
      const { confirm, close } = useDialog()

      void confirm('Sure?')
      expect(store.dialog.isOpen).toBe(true)

      close()

      expect(store.dialog.isOpen).toBe(false)
    })
  })
})
