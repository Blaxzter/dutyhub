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
  TURNSTILE_SITE_KEY: '',
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
      TURNSTILE_SITE_KEY: '0x4AAAAAAA',
    }
    window.__APP_CONFIG__ = injected

    expect(useAppConfig()).toEqual(injected)
  })

  it('fills in keys an older config.js predates', () => {
    // The realistic shape of a stale deploy: a config written before Turnstile
    // existed. Every field it does carry has to survive, and the one it does
    // not has to read as "switched off" rather than as `undefined` — which
    // would render a widget against a broken key and wedge the register form.
    window.__APP_CONFIG__ = { LEGAL_NAME: 'WirkSam e.V.' }

    expect(useAppConfig()).toEqual({ ...EMPTY, LEGAL_NAME: 'WirkSam e.V.' })
  })

  it('reads the global on every call rather than caching it', () => {
    expect(useAppConfig().LEGAL_NAME).toBe('')

    window.__APP_CONFIG__ = { ...EMPTY, LEGAL_NAME: 'Set later' }

    expect(useAppConfig().LEGAL_NAME).toBe('Set later')
  })
})
