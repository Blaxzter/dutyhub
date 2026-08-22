<script setup lang="ts">
/**
 * One full-bleed band of the landing page.
 *
 * The page scrolls as a single document, so every section owns its own
 * background and its own inner container. `scroll-mt-*` keeps the sticky
 * header from covering a heading when an anchor link jumps here.
 */
withDefaults(
  defineProps<{
    id: string
    /** Background band. Alternating `plain`/`tinted` gives the page rhythm. */
    tone?: 'plain' | 'tinted' | 'hero'
    /** Inner container width. `wide` suits screenshot rows, `full` the step chain. */
    width?: 'default' | 'wide' | 'full'
  }>(),
  { tone: 'plain', width: 'default' },
)
</script>

<template>
  <section
    :id="id"
    class="scroll-mt-36 py-16 sm:py-24"
    :class="{
      'bg-background': tone === 'plain',
      'bg-muted/40': tone === 'tinted',
      'relative overflow-hidden bg-hero text-hero-foreground': tone === 'hero',
    }"
  >
    <!-- Soft tonal glows, matching the select-event hero pane. -->
    <div
      v-if="tone === 'hero'"
      aria-hidden="true"
      class="absolute inset-0"
      style="
        background:
          radial-gradient(
            ellipse 90% 70% at 15% 0%,
            color-mix(in oklab, var(--hero-speck) var(--hero-speck-opacity), transparent) 0%,
            transparent 65%
          ),
          radial-gradient(
            ellipse 100% 80% at 100% 100%,
            color-mix(in oklab, var(--hero-speck) var(--hero-speck-opacity), transparent) 0%,
            transparent 70%
          );
      "
    />

    <div
      class="relative mx-auto w-full px-4 sm:px-6"
      :class="{
        'max-w-5xl': width === 'default',
        'max-w-6xl': width === 'wide',
        'max-w-7xl': width === 'full',
      }"
    >
      <slot />
    </div>
  </section>
</template>
