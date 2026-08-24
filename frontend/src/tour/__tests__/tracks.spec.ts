import { describe, expect, it } from 'vitest'

import de from '@/locales/de/tour.json'
import en from '@/locales/en/tour.json'
import { helperTrack } from '@/tour/tracks/helper'
import { managerTrack } from '@/tour/tracks/manager'
import type { TourStep, TourTrack } from '@/tour/types'

/**
 * vue-i18n renders a key it cannot find as the raw dotted path, on screen, with
 * no warning anybody sees in production — and these particular strings are the
 * app's first impression. Nothing else in the suite walks the tracks, so this
 * is the only thing standing between a renamed step and `tour.helper.welcome.title`
 * printed inside a popover.
 */
const LOCALES = { en, de } as Record<string, Record<string, unknown>>

const TRACKS: TourTrack[] = [helperTrack, managerTrack]

/**
 * Follow a `tour.`-prefixed key into one locale file.
 *
 * The prefix is the namespace, which is the *filename* — `locales/i18n.ts`
 * glob-imports each file under its own name — so it is not part of the tree the
 * JSON actually holds.
 */
function resolve(locale: Record<string, unknown>, key: string): unknown {
  const path = key.split('.')
  expect(path.shift()).toBe('tour')

  let node: unknown = locale
  for (const segment of path) {
    if (typeof node !== 'object' || node === null) return undefined
    node = (node as Record<string, unknown>)[segment]
  }
  return node
}

function everyStep(): { track: TourTrack; step: TourStep }[] {
  return TRACKS.flatMap((track) => track.steps.map((step) => ({ track, step })))
}

describe('tour tracks', () => {
  describe('shape', () => {
    it.each(TRACKS)('$id has steps with unique ids', (track) => {
      const ids = track.steps.map((step) => step.id)

      expect(ids.length).toBeGreaterThan(0)
      expect(new Set(ids).size).toBe(ids.length)
    })

    it.each(TRACKS)('$id derives both translation keys from the step id', (track) => {
      for (const step of track.steps) {
        expect(step.titleKey).toBe(`tour.${track.id}.${step.id}.title`)
        expect(step.bodyKey).toBe(`tour.${track.id}.${step.id}.body`)
      }
    })

    it.each(TRACKS)('$id names a route for every step', (track) => {
      // A step with no route renders wherever the visitor happens to be, which
      // for these tracks would always be a mistake rather than a choice.
      for (const step of track.steps) {
        expect(step.route, `${track.id}/${step.id}`).toBeTruthy()
      }
    })
  })

  describe.each(Object.keys(LOCALES))('%s copy', (locale) => {
    const messages = LOCALES[locale]

    it.each(everyStep())('$track.id/$step.id has a title and a body', ({ step }) => {
      for (const key of [step.titleKey, step.bodyKey]) {
        const value = resolve(messages, key)
        expect(typeof value, key).toBe('string')
        expect((value as string).trim(), key).not.toBe('')
      }
    })

    it('has the shared button labels', () => {
      for (const key of ['back', 'done', 'next', 'progress', 'skip']) {
        expect(typeof resolve(messages, `tour.common.${key}`)).toBe('string')
      }
    })

    it('keeps both placeholders in the progress label', () => {
      const progress = resolve(messages, 'tour.common.progress') as string

      expect(progress).toContain('{current}')
      expect(progress).toContain('{total}')
    })

    it.each(TRACKS)('carries no copy for a step $id no longer has', (track) => {
      // The other direction: a renamed step leaves its old strings behind, and
      // orphaned copy is how a locale file grows a paragraph nobody can read.
      const documented = Object.keys((messages[track.id] ?? {}) as Record<string, unknown>)
      const known = track.steps.map((step) => step.id)

      expect(documented.sort()).toEqual([...known].sort())
    })
  })
})
