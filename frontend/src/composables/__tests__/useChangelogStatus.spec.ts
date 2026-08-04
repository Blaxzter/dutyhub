// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'

/**
 * `useChangelogStatus` is module-scoped state: the version list is derived from
 * `src/changelog/generated/en.json` at import time and the "last seen" marker is
 * a single `useLocalStorage` ref created at import time too. Both are therefore
 * fixed the moment the module is first evaluated.
 *
 * So each scenario seeds `localStorage`, swaps in a hand-built changelog via
 * `vi.mock`, calls `vi.resetModules()` and re-imports — giving a genuinely fresh
 * module instance per test. jsdom is used (rather than stubbing
 * `globalThis.localStorage`) so `useLocalStorage` exercises a real Storage
 * implementation including its `storage`-event wiring.
 */
type ChangelogEntry = { title: string; version: string; date: string; html: string }

/**
 * Vitest caches the factory's return value, so the array *identity* handed to
 * the mocked module has to stay stable — each scenario refills it in place
 * rather than assigning a new array.
 */
const changelog = vi.hoisted(() => ({ entries: [] as ChangelogEntry[] }))

vi.mock('../../changelog/generated/en.json', () => ({ default: changelog.entries }))

const STORAGE_KEY = 'wirksam-last-seen-changelog'

function entry(version: string, date: string, title = `Release ${version}`): ChangelogEntry {
  return { version, date, title, html: `<p>${title}</p>` }
}

async function loadModule(entries: ChangelogEntry[], lastSeen: string | null) {
  changelog.entries.splice(0, changelog.entries.length, ...entries)
  localStorage.clear()
  if (lastSeen !== null) localStorage.setItem(STORAGE_KEY, lastSeen)
  vi.resetModules()
  return await import('../useChangelogStatus')
}

async function load(entries: ChangelogEntry[], lastSeen: string | null = null) {
  const { useChangelogStatus } = await loadModule(entries, lastSeen)
  // `useLocalStorage` writes through a `flush: 'pre'` watcher, so persistence
  // only lands on the next tick — and it must be the tick of the *freshly
  // re-imported* Vue, since `resetModules()` swapped the scheduler out too.
  const { nextTick } = await import('vue')
  return { ...useChangelogStatus(), nextTick }
}

beforeEach(() => {
  localStorage.clear()
})

describe('useChangelogStatus', () => {
  describe('latest version selection', () => {
    it('picks the entry with the newest date, not the first in the file', async () => {
      const status = await load([
        entry('0.9.0', '2026-01-01T12:00:00'),
        entry('0.10.0', '2026-05-01T12:00:00', 'Newest'),
        entry('0.8.0', '2025-12-01T12:00:00'),
      ])
      expect(status.latestVersion).toBe('0.10.0')
      expect(status.latestTitle).toBe('Newest')
    })

    it('sorts strictly by date even when that yields a lower version number', async () => {
      const status = await load([
        entry('2.0.0', '2026-01-01T12:00:00'),
        entry('1.0.0', '2026-06-01T12:00:00', 'Late hotfix'),
      ])
      expect(status.latestVersion).toBe('1.0.0')
      expect(status.latestTitle).toBe('Late hotfix')
    })

    it('reports no latest version for an empty changelog', async () => {
      const status = await load([])
      expect(status.latestVersion).toBeNull()
      expect(status.latestTitle).toBeNull()
      expect(status.hasNewVersions.value).toBe(false)
      expect(status.newVersionCount.value).toBe(0)
    })
  })

  describe('with nothing seen yet', () => {
    it('flags every version as new', async () => {
      const status = await load([
        entry('1.0.0', '2026-01-01T12:00:00'),
        entry('1.1.0', '2026-02-01T12:00:00'),
        entry('1.2.0', '2026-03-01T12:00:00'),
      ])
      expect(status.hasNewVersions.value).toBe(true)
      expect(status.newVersionCount.value).toBe(3)
      expect(status.isNewVersion('1.0.0')).toBe(true)
      expect(status.isNewVersion('0.0.1')).toBe(true)
    })
  })

  describe('numeric segment comparison', () => {
    it('treats 0.2.10 as newer than 0.2.9 (a plain string compare would not)', async () => {
      const status = await load(
        [entry('0.2.9', '2026-01-01T12:00:00'), entry('0.2.10', '2026-02-01T12:00:00')],
        '0.2.9',
      )
      expect('0.2.10' > '0.2.9').toBe(false) // the bug this guards against
      expect(status.isNewVersion('0.2.10')).toBe(true)
      expect(status.hasNewVersions.value).toBe(true)
      expect(status.newVersionCount.value).toBe(1)
    })

    it('treats 0.2.9 as older than 0.2.10', async () => {
      const status = await load(
        [entry('0.2.9', '2026-02-01T12:00:00'), entry('0.2.10', '2026-01-01T12:00:00')],
        '0.2.10',
      )
      expect(status.isNewVersion('0.2.9')).toBe(false)
      expect(status.hasNewVersions.value).toBe(false)
      expect(status.newVersionCount.value).toBe(0)
    })

    it('compares multi-digit minor segments numerically', async () => {
      const status = await load([entry('0.10.0', '2026-02-01T12:00:00')], '0.9.0')
      expect(status.isNewVersion('0.10.0')).toBe(true)
      expect(status.isNewVersion('0.9.1')).toBe(true)
      expect(status.isNewVersion('0.9.0')).toBe(false)
      expect(status.isNewVersion('0.8.99')).toBe(false)
      expect(status.hasNewVersions.value).toBe(true)
    })

    it('compares multi-digit major segments numerically', async () => {
      const status = await load([entry('10.0.0', '2026-02-01T12:00:00')], '9.0.0')
      expect(status.isNewVersion('10.0.0')).toBe(true)
      expect(status.hasNewVersions.value).toBe(true)
    })
  })

  describe('equal and differently-shaped versions', () => {
    it('does not flag the exact same version as new', async () => {
      const status = await load([entry('1.2.3', '2026-02-01T12:00:00')], '1.2.3')
      expect(status.isNewVersion('1.2.3')).toBe(false)
      expect(status.hasNewVersions.value).toBe(false)
      expect(status.newVersionCount.value).toBe(0)
    })

    it('pads a missing segment with zero, so 1.0 equals 1.0.0', async () => {
      const status = await load([entry('1.0', '2026-02-01T12:00:00')], '1.0.0')
      expect(status.isNewVersion('1.0')).toBe(false)
      expect(status.hasNewVersions.value).toBe(false)
    })

    it('still detects a bump against a two-segment baseline', async () => {
      const status = await load([entry('1.0.1', '2026-02-01T12:00:00')], '1.0')
      expect(status.isNewVersion('1.0.1')).toBe(true)
      expect(status.isNewVersion('1.1')).toBe(true)
      expect(status.hasNewVersions.value).toBe(true)
    })
  })

  describe('pre-release suffixes', () => {
    it('never flags a pre-release version as new (NaN comparison falls through)', async () => {
      const status = await load([entry('1.0.1-rc.1', '2026-02-01T12:00:00')], '1.0.0')
      expect(status.isNewVersion('1.0.1-rc.1')).toBe(false)
      expect(status.hasNewVersions.value).toBe(false)
      expect(status.newVersionCount.value).toBe(0)
    })

    it('suppresses a patch bump while the last seen marker is a pre-release', async () => {
      const status = await load([entry('1.0.1', '2026-02-01T12:00:00')], '1.0.0-beta')
      expect(status.isNewVersion('1.0.1')).toBe(false)
      expect(status.hasNewVersions.value).toBe(false)
      expect(status.newVersionCount.value).toBe(0)
    })

    it('still detects a bump that differs before the pre-release segment', async () => {
      const status = await load([entry('2.0.0', '2026-02-01T12:00:00')], '1.0.0-beta')
      expect(status.isNewVersion('2.0.0')).toBe(true)
      expect(status.hasNewVersions.value).toBe(true)
    })
  })

  describe('newVersionCount', () => {
    it('counts only the entries strictly newer than the last seen version', async () => {
      const status = await load(
        [
          entry('1.0.0', '2026-01-01T12:00:00'),
          entry('1.1.0', '2026-02-01T12:00:00'),
          entry('1.2.0', '2026-03-01T12:00:00'),
          entry('1.10.0', '2026-04-01T12:00:00'),
        ],
        '1.1.0',
      )
      expect(status.newVersionCount.value).toBe(2)
      expect(status.hasNewVersions.value).toBe(true)
    })

    it('is zero once the last seen version is the highest one', async () => {
      const status = await load(
        [entry('1.0.0', '2026-01-01T12:00:00'), entry('1.1.0', '2026-02-01T12:00:00')],
        '1.1.0',
      )
      expect(status.newVersionCount.value).toBe(0)
    })
  })

  describe('markAsSeen', () => {
    it('persists the latest version and clears the new-version flags', async () => {
      const status = await load([
        entry('1.0.0', '2026-01-01T12:00:00'),
        entry('1.1.0', '2026-02-01T12:00:00'),
      ])
      expect(status.hasNewVersions.value).toBe(true)
      expect(status.newVersionCount.value).toBe(2)

      status.markAsSeen()
      await status.nextTick()

      expect(localStorage.getItem(STORAGE_KEY)).toBe('1.1.0')
      expect(status.hasNewVersions.value).toBe(false)
      expect(status.newVersionCount.value).toBe(0)
      expect(status.isNewVersion('1.1.0')).toBe(false)
      expect(status.isNewVersion('1.0.0')).toBe(false)
    })

    it('is a no-op when the changelog is empty', async () => {
      const status = await load([])
      status.markAsSeen()
      await status.nextTick()
      expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
    })

    it('shares the last seen marker across every call site', async () => {
      const { useChangelogStatus } = await loadModule([entry('3.0.0', '2026-02-01T12:00:00')], null)
      const a = useChangelogStatus()
      const b = useChangelogStatus()

      expect(b.hasNewVersions.value).toBe(true)
      a.markAsSeen()
      expect(b.hasNewVersions.value).toBe(false)
      expect(b.isNewVersion('3.0.0')).toBe(false)
    })
  })

  describe('localStorage seeding', () => {
    it('reads a pre-existing marker written by an earlier session', async () => {
      const status = await load(
        [entry('1.0.0', '2026-01-01T12:00:00'), entry('2.0.0', '2026-02-01T12:00:00')],
        '2.0.0',
      )
      expect(status.hasNewVersions.value).toBe(false)
      expect(status.newVersionCount.value).toBe(0)
    })

    it('treats an empty-string marker as never seen', async () => {
      const status = await load([entry('1.0.0', '2026-01-01T12:00:00')], '')
      expect(status.hasNewVersions.value).toBe(true)
      expect(status.newVersionCount.value).toBe(1)
      expect(status.isNewVersion('0.0.1')).toBe(true)
    })
  })
})
