<script setup lang="ts">
import { type Component, nextTick, onMounted, ref, watch } from 'vue'

export interface ChipNavItem {
  label: string
  icon?: Component
}

const props = withDefaults(
  defineProps<{
    items: ChipNavItem[]
    variant?: 'rounded' | 'square'
    stretch?: boolean
  }>(),
  { variant: 'square', stretch: false },
)

const activeIndex = defineModel<number>({ default: 0 })

const container = ref<HTMLElement>()
const itemRefs = ref<(HTMLElement | null)[]>([])
const showFadeLeft = ref(false)
const showFadeRight = ref(false)

function select(index: number) {
  activeIndex.value = index
}

const FADE_THRESHOLD = 0

function updateOverflow() {
  const el = container.value
  if (!el) return
  showFadeLeft.value = el.scrollLeft > FADE_THRESHOLD
  showFadeRight.value = el.scrollWidth - el.scrollLeft - el.clientWidth > FADE_THRESHOLD
}

onMounted(() => nextTick(updateOverflow))

watch(activeIndex, async () => {
  await nextTick()
  const pill = itemRefs.value[activeIndex.value]
  if (pill && container.value) {
    pill.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
  }
})
</script>

<template>
  <div class="relative overflow-hidden">
    <div
      class="pointer-events-none absolute inset-y-0 left-0 z-10 w-6 bg-gradient-to-r from-background to-transparent transition-opacity duration-200"
      :class="showFadeLeft ? 'opacity-100' : 'opacity-0'"
    />
    <div
      class="pointer-events-none absolute inset-y-0 right-0 z-10 w-6 bg-gradient-to-l from-background to-transparent transition-opacity duration-200"
      :class="showFadeRight ? 'opacity-100' : 'opacity-0'"
    />
    <div
      ref="container"
      class="flex gap-2 overflow-x-auto scroll-smooth no-scrollbar touch-pan-x"
      @scroll="updateOverflow"
    >
      <button
        v-for="(item, index) in props.items"
        :key="index"
        :ref="(el) => (itemRefs[index] = el as HTMLElement)"
        @click="select(index)"
        class="flex items-center justify-center gap-1.5 px-3.5 py-2 text-sm font-medium transition-all duration-200"
        :class="[
          stretch ? 'flex-1 min-w-0 whitespace-nowrap' : 'shrink-0',
          variant === 'rounded' ? 'rounded-full' : 'rounded-lg',
          activeIndex === index
            ? 'bg-primary text-primary-foreground shadow-sm'
            : 'bg-muted text-muted-foreground hover:bg-muted/80',
        ]"
      >
        <component v-if="item.icon" :is="item.icon" class="h-3.5 w-3.5" />
        {{ item.label }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
</style>
