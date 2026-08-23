<script setup lang="ts">
/**
 * A frame that is nothing but an error boundary.
 *
 * The auth screens paint edge to edge — a coloured pane meeting the page
 * background with no gutter between them — so they cannot sit inside
 * `NoLayout`, whose `container mx-auto px-4 py-8` would inset the whole split
 * and cap it at the container width. What they still want from a layout is the
 * error boundary, so that is all this is.
 *
 * They still carry no navigation: a page asking for a password should not also
 * offer a bar full of places to go instead, and the only links each screen has
 * belong to the flow it is part of.
 */
import { RouterView } from 'vue-router'

import ErrorBoundary from '@/components/utils/ErrorBoundary.vue'
</script>

<template>
  <ErrorBoundary>
    <RouterView />
  </ErrorBoundary>
</template>
