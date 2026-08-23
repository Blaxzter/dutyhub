<script setup lang="ts">
/**
 * A roster filling up — the idea behind the product, drawn rather than
 * screenshotted.
 *
 * `ShiftBoardConcept` on the landing page does this properly: a real grid, an
 * IntersectionObserver, and places taken in round-robin passes so it reads as a
 * team signing up rather than a progress bar. This is the same gesture at a
 * fraction of the weight, because here it is decoration beside a login form
 * rather than the argument for using the app at all. It is always above the
 * fold when it renders, so it simply plays once on mount.
 *
 * Each place is its own dot, and an empty one keeps a dashed outline — without
 * that the grid reads as a loading skeleton rather than as a plan. Only
 * `opacity` and `transform` animate, so nothing here can reflow the pane.
 */

/** Days across, shifts down — the same axes as the real board. */
const DAYS = ['Fr', 'Sa', 'So'] as const
const TIMES = ['09:00', '11:30', '14:00', '16:30'] as const

/**
 * Places taken on each shift, out of two — one entry per cell, in the order the
 * grid renders them: left to right, then down. So the first three are Friday,
 * Saturday and Sunday at 09:00, and the time comes from the *row*.
 */
const TAKEN = [2, 2, 1, 2, 2, 2, 2, 0, 1, 2, 0, 2] as const
const PLACES = 2

/** The place presented as the visitor's own. It lands after everything else. */
const MINE = { cell: 4, place: 1 }

/** Covers the pane's own entrance before the first place is taken. */
const SETTLE_MS = 520
const STEP_MS = 55

const cells = TAKEN.map((taken, index) => ({
  index,
  taken,
  // The row, not the index: every column of a roster runs the same times down.
  time: TIMES[Math.floor(index / DAYS.length)],
}))

/** Order the dots fill in: one pass across every shift, then the next. */
function delayFor(cell: number, place: number): string {
  return `${SETTLE_MS + (place * TAKEN.length + cell) * STEP_MS}ms`
}
</script>

<template>
  <div aria-hidden="true">
    <div class="grid grid-cols-3 gap-2">
      <p
        v-for="day in DAYS"
        :key="day"
        class="text-[0.6875rem] font-semibold tracking-wide text-hero-foreground/70 uppercase"
      >
        {{ day }}
      </p>
    </div>

    <div class="mt-1.5 grid grid-cols-3 gap-2">
      <div
        v-for="cell in cells"
        :key="cell.index"
        class="flex items-center justify-between gap-1 rounded-lg bg-hero-foreground/10 px-2 py-1.5 ring-1 ring-hero-foreground/10 ring-inset"
      >
        <span class="text-[0.625rem] tabular-nums text-hero-foreground/70">{{ cell.time }}</span>
        <span class="flex items-center gap-1">
          <span
            v-for="place in PLACES"
            :key="place"
            class="size-2 rounded-full"
            :class="
              place <= cell.taken
                ? [
                    'animate-shift-pop motion-reduce:animate-none',
                    cell.index === MINE.cell && place === MINE.place
                      ? 'bg-hero-foreground ring-2 ring-hero-foreground/35'
                      : 'bg-hero-foreground/70',
                  ]
                : 'border border-dashed border-hero-foreground/40'
            "
            :style="
              place <= cell.taken ? { animationDelay: delayFor(cell.index, place - 1) } : undefined
            "
          />
        </span>
      </div>
    </div>
  </div>
</template>
