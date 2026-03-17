<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { Loader2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import type { FeedEventItem } from '@/client/types.gen'

import EventQuickViewCard from './EventQuickViewCard.vue'

const PAGE_SIZE = 8

const props = defineProps<{
  events: FeedEventItem[]
  focusMode?: 'today' | 'first-available'
  hideFullSlots?: boolean
}>()

const emit = defineEmits<{
  navigate: [event: FeedEventItem]
  delete: [event: FeedEventItem]
  clickSlot: [slotId: string, event: FeedEventItem]
}>()

const { t } = useI18n()

const visibleCount = ref(PAGE_SIZE)
const loadingMore = ref(false)
const sentinelRef = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

const sortedEvents = computed(() => {
  const todayStr = new Date().toISOString().slice(0, 10)
  return [...props.events].sort((a, b) => {
    const nextA = a.slot_window_start ?? a.start_date
    const nextB = b.slot_window_start ?? b.start_date
    const diffA = nextA >= todayStr ? 0 : 1
    const diffB = nextB >= todayStr ? 0 : 1
    if (diffA !== diffB) return diffA - diffB
    return nextA.localeCompare(nextB)
  })
})

const visibleEvents = computed(() => {
  return sortedEvents.value.slice(0, visibleCount.value)
})

const hasMore = computed(() => {
  return visibleCount.value < props.events.length
})

function loadMoreEvents() {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  visibleCount.value = Math.min(visibleCount.value + PAGE_SIZE, props.events.length)
  loadingMore.value = false
}

function setupObserver() {
  if (observer) observer.disconnect()
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting && hasMore.value && !loadingMore.value) {
        loadMoreEvents()
      }
    },
    { rootMargin: '200px' },
  )
  if (sentinelRef.value) observer.observe(sentinelRef.value)
}

watch(
  () => props.events,
  async () => {
    visibleCount.value = PAGE_SIZE
    await nextTick()
    setupObserver()
  },
)

onMounted(async () => {
  await nextTick()
  setupObserver()
})

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>

<template>
  <div v-if="events.length === 0" class="py-12 text-center text-muted-foreground">
    {{ t('duties.events.empty') }}
  </div>

  <div v-else class="space-y-3">
    <EventQuickViewCard
      v-for="item in visibleEvents"
      :key="item.id"
      :event="item"
      :visible-days="5"
      :hide-full-slots="hideFullSlots"
      @navigate="emit('navigate', $event)"
      @delete="emit('delete', $event)"
      @click-slot="(slotId, ev) => emit('clickSlot', slotId, ev)"
    />

    <!-- Infinite scroll sentinel -->
    <div v-if="hasMore" ref="sentinelRef" class="flex items-center justify-center py-4">
      <Loader2 v-if="loadingMore" class="h-5 w-5 animate-spin text-muted-foreground" />
    </div>

    <!-- End of list -->
    <p v-else class="py-4 text-center text-xs text-muted-foreground">
      {{ t('duties.events.quickView.noMore') }}
    </p>
  </div>
</template>
