<script setup lang="ts">
import { computed } from 'vue'

import type { Palette } from '@/composables/usePalette'

const props = withDefaults(
  defineProps<{
    palette: Palette
    /** preview shows palette in this mode */
    mode: 'light' | 'dark'
    /** sm = ~64×48 (menu tile), lg = ~160×96 (settings card) */
    size?: 'sm' | 'lg'
    selected?: boolean
  }>(),
  {
    size: 'sm',
    selected: false,
  },
)

/** Hardcoded swatches (not CSS vars) so each tile shows its OWN palette,
    not whichever one is currently active. Keep in sync with index.css. */
const SWATCHES: Record<
  Palette,
  Record<
    'light' | 'dark',
    { bg: string; card: string; border: string; primary: string; accent: string; fg: string }
  >
> = {
  default: {
    light: {
      bg: 'oklch(0.945 0.018 80)',
      card: 'oklch(0.965 0.014 80)',
      border: 'oklch(0.87 0.025 80)',
      primary: 'oklch(0.40 0.072 145)',
      accent: 'oklch(0.62 0.135 45)',
      fg: 'oklch(0.27 0.012 60)',
    },
    dark: {
      bg: 'oklch(0.18 0.008 75)',
      card: 'oklch(0.22 0.010 75)',
      border: 'oklch(0.30 0.012 75)',
      primary: 'oklch(0.65 0.10 145)',
      accent: 'oklch(0.70 0.13 45)',
      fg: 'oklch(0.92 0.015 80)',
    },
  },
  classic: {
    light: {
      bg: 'oklch(1 0 0)',
      card: 'oklch(0.985 0 0)',
      border: 'oklch(0.922 0 0)',
      primary: 'oklch(0.205 0 0)',
      accent: 'oklch(0.97 0 0)',
      fg: 'oklch(0.145 0 0)',
    },
    dark: {
      bg: 'oklch(0.145 0 0)',
      card: 'oklch(0.205 0 0)',
      border: 'oklch(0.269 0 0)',
      primary: 'oklch(0.985 0 0)',
      accent: 'oklch(0.269 0 0)',
      fg: 'oklch(0.985 0 0)',
    },
  },
}

const swatch = computed(() => SWATCHES[props.palette][props.mode])
</script>

<template>
  <div
    class="rounded-md overflow-hidden border-2 transition-all"
    :class="[
      selected ? 'border-ring ring-2 ring-ring/30' : 'border-transparent',
      size === 'sm' ? 'h-12 w-16' : 'h-24 w-40',
    ]"
    :style="{ backgroundColor: swatch.bg, borderColor: selected ? undefined : swatch.border }"
    aria-hidden="true"
  >
    <!-- Mini "card" overlay -->
    <div
      class="m-1 rounded-sm flex items-center justify-between"
      :class="size === 'sm' ? 'h-6 px-1' : 'h-10 px-2'"
      :style="{ backgroundColor: swatch.card, border: `1px solid ${swatch.border}` }"
    >
      <span
        class="rounded-sm"
        :class="size === 'sm' ? 'h-1 w-3' : 'h-1.5 w-8'"
        :style="{ backgroundColor: swatch.fg, opacity: 0.6 }"
      />
      <span
        class="rounded-full"
        :class="size === 'sm' ? 'h-1.5 w-1.5' : 'h-2.5 w-2.5'"
        :style="{ backgroundColor: swatch.accent }"
      />
    </div>
    <div
      class="mx-1 rounded-sm"
      :class="size === 'sm' ? 'h-1.5' : 'h-3'"
      :style="{ backgroundColor: swatch.primary, width: size === 'sm' ? '60%' : '40%' }"
    />
  </div>
</template>
