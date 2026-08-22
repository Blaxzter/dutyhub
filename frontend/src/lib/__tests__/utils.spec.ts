import { describe, expect, it, vi } from 'vitest'

import { cn, getTranslationList } from '@/lib/utils'

describe('cn', () => {
  it('joins plain class strings', () => {
    expect(cn('px-2', 'py-1')).toBe('px-2 py-1')
  })

  it('lets a later tailwind utility win over an earlier conflicting one', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4')
    expect(cn('text-sm', 'text-lg')).toBe('text-lg')
    expect(cn('bg-red-500', 'bg-blue-500')).toBe('bg-blue-500')
  })

  it('keeps non-conflicting utilities from the same family', () => {
    expect(cn('px-2', 'py-4')).toBe('px-2 py-4')
  })

  it('drops falsy and conditional values', () => {
    expect(cn('base', false, null, undefined, '', 0)).toBe('base')
    expect(cn('base', false && 'hidden', true && 'block')).toBe('base block')
  })

  it('handles object syntax', () => {
    expect(cn('base', { active: true, disabled: false })).toBe('base active')
  })

  it('handles arrays, including nested ones', () => {
    expect(cn(['flex', ['items-center', { 'gap-2': true, 'gap-4': false }]])).toBe(
      'flex items-center gap-2',
    )
  })

  it('resolves conflicts across arrays and objects too', () => {
    expect(cn(['text-sm'], { 'text-lg': true })).toBe('text-lg')
  })

  it('returns an empty string when given nothing', () => {
    expect(cn()).toBe('')
    expect(cn(undefined, null, false)).toBe('')
  })

  it('preserves unknown (non-tailwind) classes in order', () => {
    expect(cn('custom-a', 'custom-b')).toBe('custom-a custom-b')
  })
})

describe('getTranslationList', () => {
  /**
   * Builds a `t()` stand-in that mimics vue-i18n: a known key resolves to its
   * translation, an unknown key echoes the key back. That echo is the sentinel
   * `getTranslationList` relies on to stop iterating.
   */
  const fakeT = (translations: Record<string, string>) =>
    vi.fn((key: string) => translations[key] ?? key)

  it('returns an empty array when index 0 is missing', () => {
    const t = fakeT({})

    expect(getTranslationList(t, 'items')).toEqual([])
    expect(t).toHaveBeenCalledTimes(1)
    expect(t).toHaveBeenCalledWith('items.0')
  })

  it('collects a list of three entries', () => {
    const t = fakeT({
      'tech.items.0': 'Vue.js',
      'tech.items.1': 'TypeScript',
      'tech.items.2': 'Tailwind',
    })

    expect(getTranslationList(t, 'tech.items')).toEqual(['Vue.js', 'TypeScript', 'Tailwind'])
  })

  it('queries numbered keys built from the base key', () => {
    const t = fakeT({ 'a.b.c.0': 'first', 'a.b.c.1': 'second' })

    getTranslationList(t, 'a.b.c')

    expect(t.mock.calls.map(([key]) => key)).toEqual(['a.b.c.0', 'a.b.c.1', 'a.b.c.2'])
  })

  it('stops at the first gap and ignores entries beyond it', () => {
    const t = fakeT({
      'items.0': 'one',
      'items.1': 'two',
      // 'items.2' deliberately missing
      'items.3': 'four',
    })

    expect(getTranslationList(t, 'items')).toEqual(['one', 'two'])
  })

  it('keeps falsy translations such as an empty string', () => {
    const t = fakeT({ 'items.0': '', 'items.1': 'second' })

    expect(getTranslationList(t, 'items')).toEqual(['', 'second'])
  })

  it('keeps values that merely contain the key rather than equal it', () => {
    const t = fakeT({ 'items.0': 'items.0 — annotated' })

    expect(getTranslationList(t, 'items')).toEqual(['items.0 — annotated'])
  })

  it('terminates on the sentinel instead of looping forever', () => {
    const size = 100
    const t = vi.fn((key: string) => {
      const index = Number(key.slice('items.'.length))
      return index < size ? `entry ${index}` : key
    })

    const result = getTranslationList(t, 'items')

    expect(result).toHaveLength(size)
    expect(result[0]).toBe('entry 0')
    expect(result[size - 1]).toBe(`entry ${size - 1}`)
    // Exactly one extra call: the one that hit the sentinel and broke the loop.
    expect(t).toHaveBeenCalledTimes(size + 1)
  })
})
