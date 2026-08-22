<script setup lang="ts">
import { type Component, onBeforeUnmount, onMounted, ref, useTemplateRef } from 'vue'

import { scrollToSection } from '@/lib/scroll-to-section'

/**
 * Floating dock for the landing page's sections.
 *
 * This replaces the header links that `/about` and `/how-it-works` used to be.
 * It was a full-width underlined bar, which read as a second row of browser
 * chrome bolted under the header; it is now a capsule that hovers over the
 * content, each section a bubble with its own icon and the current one filled
 * in.
 *
 * It stays hidden until the hero is scrolled past. Its resting position in the
 * document flow falls exactly on the seam between the hero and the first
 * section, and sitting half over each background made it look pinned to that
 * divider rather than floating. Hidden until it is genuinely stuck, it is only
 * ever seen hovering over a section.
 */
const props = defineProps<{ items: { id: string; label: string; icon: Component }[] }>()

const activeId = ref(props.items[0]?.id ?? '')
const stuck = ref(false)

const sentinel = useTemplateRef<HTMLElement>('sentinel')

let sectionObserver: IntersectionObserver | undefined
let sentinelObserver: IntersectionObserver | undefined

/** Matches the `top-20` the dock sticks at, in pixels. */
const STICK_OFFSET = 80

onMounted(() => {
  // Scroll position: the bands are offset for the sticky header and this dock;
  // the bottom one keeps the last (short) section from never winning.
  sectionObserver = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
      if (visible[0]?.target.id) activeId.value = visible[0].target.id
    },
    { rootMargin: '-30% 0px -55% 0px' },
  )

  for (const item of props.items) {
    const el = document.getElementById(item.id)
    if (el) sectionObserver.observe(el)
  }

  // Stuck-ness: shrink the root by the sticky offset, and the sentinel stops
  // intersecting at exactly the moment the dock would pin itself.
  if (sentinel.value) {
    sentinelObserver = new IntersectionObserver(
      ([entry]) => {
        stuck.value = !entry.isIntersecting && entry.boundingClientRect.top < STICK_OFFSET
      },
      { rootMargin: `-${STICK_OFFSET}px 0px 0px 0px` },
    )
    sentinelObserver.observe(sentinel.value)
  }
})

onBeforeUnmount(() => {
  sectionObserver?.disconnect()
  sentinelObserver?.disconnect()
})

/**
 * The `href` stays real so the links can be opened in a new tab and read by
 * assistive tech, but the default jump is replaced with a smooth scroll —
 * letting the browser handle it teleported the page and then fought with
 * vue-router's own hash scrolling.
 */
function onNavigate(event: MouseEvent, id: string) {
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return
  if (scrollToSection(id)) {
    event.preventDefault()
    activeId.value = id
  }
}
</script>

<template>
  <!-- Two roots on purpose. Wrapping these in a container broke the dock: a
       sticky element can only stick within its parent's box, and a zero-height
       wrapper gives it no range at all, so it scrolled away behind the header
       instead of pinning. As a fragment its parent is the page container. -->
  <div ref="sentinel" aria-hidden="true" class="h-0" />

  <!-- Zero-height: the dock hovers over the sections rather than reserving a
       band of its own between them. -->
  <div class="pointer-events-none sticky top-20 z-30 hidden h-0 md:block">
    <nav
      :aria-label="$t('preauth.landing.nav.label')"
      class="mx-auto w-fit px-4 transition-all duration-300"
      :class="stuck ? 'visible translate-y-0 opacity-100' : 'invisible -translate-y-3 opacity-0'"
    >
      <ul
        class="pointer-events-auto flex items-center gap-1 rounded-full border bg-card/95 p-1.5 shadow-xl ring-1 ring-black/5 backdrop-blur-md"
      >
        <li v-for="item in items" :key="item.id">
          <a
            :href="`#${item.id}`"
            :aria-current="activeId === item.id ? 'true' : undefined"
            class="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors"
            :class="
              activeId === item.id
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            "
            @click="onNavigate($event, item.id)"
          >
            <component :is="item.icon" class="size-4 shrink-0" aria-hidden="true" />
            {{ item.label }}
          </a>
        </li>
      </ul>
    </nav>
  </div>
</template>
