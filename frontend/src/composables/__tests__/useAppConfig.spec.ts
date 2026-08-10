// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'

import { useAppConfig } from '@/composables/useAppConfig'

/**
 * `window.__APP_CONFIG__` is injected at deploy time, so it is absent in dev and
 * in every test run. The empty-string fallback is what stops the impressum
 * rendering "undefined" as a legal address, which makes it the branch worth
 * pinning.
 */
const EMPTY = {
  LEGAL_NAME: '',
  LEGAL_ADDRESS: '',
  LEGAL_CITY: '',
  LEGAL_EMAIL: '',
  LEGAL_PHONE: '',
}

afterEach(() => {
  delete window.__APP_CONFIG__
})

describe('useAppConfig', () => {
  it('falls back to empty strings when nothing was injected', () => {
    expect(useAppConfig()).toEqual(EMPTY)
  })

  it('returns the injected config when the deploy provided one', () => {
    const injected = {
      LEGAL_NAME: 'WirkSam e.V.',
      LEGAL_ADDRESS: 'Musterstraße 1',
      LEGAL_CITY: '12345 Musterstadt',
      LEGAL_EMAIL: 'kontakt@example.org',
      LEGAL_PHONE: '+49 123 456789',
    }
    window.__APP_CONFIG__ = injected

    expect(useAppConfig()).toEqual(injected)
  })

  it('reads the global on every call rather than caching it', () => {
    expect(useAppConfig().LEGAL_NAME).toBe('')

    window.__APP_CONFIG__ = { ...EMPTY, LEGAL_NAME: 'Set later' }

    expect(useAppConfig().LEGAL_NAME).toBe('Set later')
  })
})
