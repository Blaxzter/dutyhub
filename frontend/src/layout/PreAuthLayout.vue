<script setup lang="ts">
import { computed } from 'vue'

import { RouterView, useRoute } from 'vue-router'

import CookieNotice from '@/components/CookieNotice.vue'
import PreAuthFooter from '@/components/layout/preauth/PreAuthFooter.vue'
import PreAuthHeader from '@/components/layout/preauth/PreAuthHeader.vue'
import ErrorBoundary from '@/components/utils/ErrorBoundary.vue'

/**
 * The pre-auth shell used to be a fixed header over an inner scroll container.
 * That broke everything the landing page now relies on — `position: sticky`,
 * anchor links between sections, and the browser's own scroll restoration — so
 * the document scrolls normally and the header sticks to the top instead.
 */
const route = useRoute()

/** Full-bleed routes lay out their own sections and skip the page container. */
const fullBleed = computed(() => route.meta.fullBleed === true)
</script>

<template>
  <div class="flex min-h-screen flex-col bg-background">
    <PreAuthHeader />

    <main class="flex flex-1 flex-col" data-testid="main-content">
      <ErrorBoundary>
        <RouterView v-if="fullBleed" />
        <div v-else class="mx-auto w-full max-w-7xl flex-1 px-4 py-8">
          <RouterView />
        </div>
      </ErrorBoundary>
    </main>

    <PreAuthFooter />
    <CookieNotice />
  </div>
</template>
