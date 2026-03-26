import { nextTick, watch, type Ref } from 'vue'

import type { UnwrapRefCarouselApi } from '@/components/ui/carousel/interface'

/**
 * Dynamically adjusts the carousel container height to match the active slide,
 * preventing tall slides from leaving empty space below shorter ones.
 *
 * Requires `items-start` on CarouselContent so slides don't stretch.
 */
export function useAdaptiveCarouselHeight(api: Ref<UnwrapRefCarouselApi | undefined>) {
  function sync() {
    const a = api.value
    if (!a) return
    const root = a.rootNode()
    const active = a.slideNodes()[a.selectedScrollSnap()]
    if (!root || !active) return
    const remaining = window.innerHeight - root.getBoundingClientRect().top - 48
    root.style.height = `${Math.max(active.offsetHeight, remaining)}px`
  }

  watch(api, (a) => {
    if (!a) return
    a.rootNode().style.transition = 'height 300ms ease'
    a.on('select', sync)
    a.on('resize', sync)
    nextTick(sync)
  })

  return { syncHeight: sync }
}
