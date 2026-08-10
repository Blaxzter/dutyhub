// Deliberately NOT jsdom — see below.
import { describe, expect, it } from 'vitest'

/**
 * `usePalette` runs a `watchEffect` at module scope that writes the palette
 * class onto `<html>`. That side effect fires on import, so the module has to
 * survive being evaluated where there is no DOM at all — a server-side render,
 * a prerender step, or simply a unit test that has not opted into jsdom.
 *
 * The guard that makes that true is `if (typeof document === 'undefined') return`,
 * and it is unreachable from `usePalette.spec.ts`, which runs under jsdom where
 * `document` always exists. This file is the other half: the default `node`
 * environment, where the guard is the branch that gets taken.
 */
describe('usePalette without a DOM', () => {
  it('imports and reads the palette without touching document', async () => {
    expect(typeof document).toBe('undefined')

    const { usePalette } = await import('../usePalette')
    const palette = usePalette()

    expect(palette.value).toBe('default')
  })

  it('still accepts a write, it just cannot mirror it onto <html>', async () => {
    const { usePalette } = await import('../usePalette')
    const palette = usePalette()

    palette.value = 'classic'

    expect(palette.value).toBe('classic')
  })
})
