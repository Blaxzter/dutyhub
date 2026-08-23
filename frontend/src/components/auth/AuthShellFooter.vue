<script setup lang="ts">
/**
 * The legal links and the two preference controls, on the form side.
 *
 * The auth screens sit outside the pre-auth shell, which is where these
 * normally live. `PreAuthFooter` itself is not reused: it centres a `max-w-6xl`
 * row and carries a copyright line, both of which fight a narrow column — but
 * the route names and the label keys are taken from it verbatim, so the two
 * footers can never drift apart on where "Impressum" points.
 *
 * The language switch in particular is not optional here. Somebody who cannot
 * read "Passwort vergessen?" has to be able to change the language *before*
 * signing in, not after.
 */
import { SparklesIcon } from '@lucide/vue'

import AppearanceMenu from '@/components/layout/AppearanceMenu.vue'
import LanguageSwitch from '@/components/utils/LanguageSwitch.vue'

const appVersion = __APP_VERSION__

const legal = [
  { name: 'privacy', label: 'preauth.layout.footer.privacy' },
  { name: 'terms', label: 'preauth.layout.footer.terms' },
  { name: 'impressum', label: 'preauth.layout.footer.impressum' },
] as const
</script>

<template>
  <footer class="shrink-0 border-t border-border/60">
    <!-- `flex-col-reverse` on a phone puts the controls above the links: the
         controls are the useful half, the links are the obligation. -->
    <div
      class="mx-auto flex w-full max-w-xl flex-col-reverse items-center gap-3 px-5 py-4 text-xs text-muted-foreground sm:flex-row sm:justify-between sm:px-8"
    >
      <!--
        `py-1` on each link, and a row gap to match, are what keep these
        tappable. At `text-xs` a bare link box is 16px tall, and on a 320px
        phone the German labels wrap onto two rows — "Nutzungsbedingungen" and
        the version link then end up 22px apart with overlapping x-ranges, so a
        thumb aimed at one lands on the other. 16 + 8 padding = 24px targets,
        clear of each other by the 8px row gap.
      -->
      <nav class="flex flex-wrap items-center justify-center gap-x-4 gap-y-2">
        <RouterLink
          v-for="item in legal"
          :key="item.name"
          :to="{ name: item.name }"
          class="inline-flex items-center py-1 transition-colors hover:text-foreground"
        >
          {{ $t(item.label) }}
        </RouterLink>
        <RouterLink
          :to="{ name: 'preauth-changelog' }"
          class="inline-flex items-center gap-1 py-1 transition-colors hover:text-foreground"
        >
          <SparklesIcon class="size-3 shrink-0" />
          <span>{{ appVersion }}</span>
        </RouterLink>
      </nav>

      <div class="flex items-center gap-1">
        <LanguageSwitch variant="ghost" size="sm" :show-text="false" />
        <AppearanceMenu />
      </div>
    </div>
  </footer>
</template>
