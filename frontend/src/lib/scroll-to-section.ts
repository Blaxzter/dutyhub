/**
 * Scroll a landing-page section into view without the hash teleport.
 *
 * A bare `<a href="#features">` makes the browser jump instantly *and* changes
 * the hash, which vue-router then treats as a navigation and scrolls again —
 * so the page lurched twice and read as a reload. Callers prevent the default
 * and come here instead: one smooth scroll, and the hash updated with
 * `replaceState` so it stays linkable and copyable without triggering routing.
 *
 * Honours `prefers-reduced-motion`, where an instant jump is the correct
 * behaviour rather than a shortcoming.
 */
export function scrollToSection(id: string): boolean {
  const target = document.getElementById(id)
  if (!target) return false

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' })

  // `replaceState` rather than assigning `location.hash`, which would scroll again.
  window.history.replaceState(window.history.state, '', `#${id}`)
  return true
}
