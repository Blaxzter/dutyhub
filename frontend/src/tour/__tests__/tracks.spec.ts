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

/**
 * Every chapter the two tracks between them name.
 *
 * Chapters live under `tour.common.chapters` rather than under a track, because
 * both tracks share `theJobs` and because the key-set check below holds
 * `tour.<track>` to exactly the step ids — a chapter parked there would read as
 * copy for a step that does not exist.
 */
function everyChapter(): string[] {
  return [...new Set(TRACKS.flatMap((track) => track.steps.map((step) => step.chapter)))].sort()
}

describe('tour tracks', () => {
  describe('shape', () => {
    it.each(TRACKS)('$id has steps with unique ids', (track) => {
      const ids = track.steps.map((step) => step.id)

      expect(ids.length).toBeGreaterThan(0)
      expect(new Set(ids).size).toBe(ids.length)
    })

    it.each(TRACKS)('$id derives all four translation keys from the step', (track) => {
      for (const step of track.steps) {
        expect(step.titleKey).toBe(`tour.${track.id}.${step.id}.title`)
        expect(step.bodyKey).toBe(`tour.${track.id}.${step.id}.body`)
        expect(step.nextKey).toBe(`tour.${track.id}.${step.id}.next`)
        expect(step.chapter, `${track.id}/${step.id}`).toBeTruthy()
        expect(step.chapterKey).toBe(`tour.common.chapters.${step.chapter}`)
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

    it.each(everyStep())('$track.id/$step.id names a chapter that has a label', ({ step }) => {
      // The chapter is the first thing on the progress line, so an unresolved
      // one does not degrade to a blank — it prints
      // `tour.common.chapters.theJobs` above every popover in the act.
      const label = resolve(messages, step.chapterKey)

      expect(typeof label, step.chapterKey).toBe('string')
      expect((label as string).trim(), step.chapterKey).not.toBe('')
      // `stepNumber()` in `e2e/tests/public/sandbox-tour.spec.ts` reads the
      // current step out of the rendered line with the first `\d+` in it, and
      // the chapter sits in front of the number.
      expect(label as string, step.chapterKey).not.toMatch(/\d/)
    })

    it.each(everyStep())('$track.id/$step.id renders safely if it labels Next', ({ step }) => {
      // The per-step Next label is *optional* copy: a step opts into a
      // verb-shaped button by a translator writing the string, and the engine
      // falls back to `tour.common.next` when there is none. So the assertion
      // is conditional — but only on presence, never on quality.
      const label = resolve(messages, step.nextKey)
      if (label === undefined) return

      expect(typeof label, step.nextKey).toBe('string')
      expect((label as string).trim(), step.nextKey).not.toBe('')
      // driver.js assigns this one with `innerHTML`. The engine escapes it, and
      // this is the other half of that: nothing in `tour.json` is markup.
      expect(label as string, step.nextKey).not.toContain('<')
      // Belt and braces behind the `data-tour-last` attribute the engine now
      // stamps: a label reading "Finish" on a step in the middle of a track
      // would have told the old e2e text probe the tour was over.
      expect(label as string, step.nextKey).not.toMatch(/done|finish|fertig/i)
    })

    it('has the shared button labels', () => {
      for (const key of ['back', 'done', 'next', 'progress', 'skip']) {
        expect(typeof resolve(messages, `tour.common.${key}`)).toBe('string')
      }
    })

    it('keeps all three placeholders in the progress label', () => {
      const progress = resolve(messages, 'tour.common.progress') as string

      expect(progress).toContain('{chapter}')
      expect(progress).toContain('{current}')
      expect(progress).toContain('{total}')
    })

    it('carries no chapter label no step uses', () => {
      // The same hygiene as the step check below, one level up. A chapter is
      // renamed by editing two track files and one locale key, and the locale
      // key is the one that can be forgotten without anything going wrong on
      // screen.
      const documented = Object.keys(
        ((messages.common as Record<string, unknown>)?.chapters ?? {}) as Record<string, unknown>,
      )

      expect(documented.sort()).toEqual(everyChapter())
    })

    it.each(TRACKS)('carries no copy for a step $id no longer has', (track) => {
      // The other direction: a renamed step leaves its old strings behind, and
      // orphaned copy is how a locale file grows a paragraph nobody can read.
      const documented = Object.keys((messages[track.id] ?? {}) as Record<string, unknown>)
      const known = track.steps.map((step) => step.id)

      expect(documented.sort()).toEqual([...known].sort())
    })
  })

  describe('across locales', () => {
    it.each(everyStep())('$track.id/$step.id opts into a Next label in all or none', ({ step }) => {
      // The per-locale blocks above cannot see this one: each is happy with a
      // label that is absent, so a step with English copy and no German copy
      // passes both of them and then renders "Next" to half its audience while
      // the other half is invited to "Open this shift".
      //
      // `check_locale_parity.js` catches it too, at commit time. This catches it
      // in the suite, which is where a translator working from a diff looks.
      const all = Object.keys(LOCALES)
      const written = all.filter((locale) => resolve(LOCALES[locale], step.nextKey) !== undefined)
      if (written.length === 0) return

      expect(written, step.nextKey).toEqual(all)
    })
  })
})
