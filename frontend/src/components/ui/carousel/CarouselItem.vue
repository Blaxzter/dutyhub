<script setup lang="ts">
import { cn } from '@/lib/utils'

import type { WithClassAsProps } from './interface'
import { useCarousel } from './useCarousel'

const props = defineProps<WithClassAsProps>()

const { orientation } = useCarousel()
</script>

<template>
  <!-- `role="group"` is the shadcn-vue default and a real ARIA role. The
       terminology rename in d28ba80 blanket-replaced "group" with "event",
       leaving `role="event"` — not a valid ARIA role at all, which axe flags as
       a critical `aria-roles` violation on every slide. -->
  <div
    data-slot="carousel-item"
    role="group"
    aria-roledescription="slide"
    :class="
      cn(
        'min-w-0 shrink-0 grow-0 basis-full',
        orientation === 'horizontal' ? 'pl-4' : 'pt-4',
        props.class,
      )
    "
  >
    <slot />
  </div>
</template>
