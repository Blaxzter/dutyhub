// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { scrollToSection } from '../scroll-to-section'

describe('scrollToSection', () => {
  let scrollIntoView: ReturnType<typeof vi.fn>
  let replaceState: ReturnType<typeof vi.spyOn>

  function addSection(id: string) {
    const el = document.createElement('section')
    el.id = id
    el.scrollIntoView = scrollIntoView as unknown as Element['scrollIntoView']
    document.body.append(el)
    return el
  }

  /** jsdom has no matchMedia; every test picks the motion preference it needs. */
  function setReducedMotion(matches: boolean) {
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockReturnValue({ matches }) as unknown as typeof window.matchMedia,
    )
  }

  beforeEach(() => {
    scrollIntoView = vi.fn()
    replaceState = vi.spyOn(window.history, 'replaceState')
    setReducedMotion(false)
  })

  afterEach(() => {
    document.body.innerHTML = ''
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('scrolls a known section smoothly and records the hash', () => {
    addSection('features')

    expect(scrollToSection('features')).toBe(true)
    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' })
  })

  it('updates the hash with replaceState so routing is not triggered', () => {
    addSection('about')

    scrollToSection('about')

    expect(replaceState).toHaveBeenCalledWith(window.history.state, '', '#about')
  })

  it('jumps instantly when the visitor asked for reduced motion', () => {
    setReducedMotion(true)
    addSection('how-it-works')

    scrollToSection('how-it-works')

    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'auto', block: 'start' })
  })

  it('reports failure and touches nothing when the section is absent', () => {
    expect(scrollToSection('nope')).toBe(false)
    expect(scrollIntoView).not.toHaveBeenCalled()
    expect(replaceState).not.toHaveBeenCalled()
  })
})
