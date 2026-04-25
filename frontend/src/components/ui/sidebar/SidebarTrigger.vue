<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { PanelLeft } from '@respeak/lucide-motion-vue'

import { Button } from '@/components/ui/button'

import { cn } from '@/lib/utils'

import { useSidebar } from './utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()

const { toggleSidebar } = useSidebar()
</script>

<template>
  <Button
    data-sidebar="trigger"
    data-slot="sidebar-trigger"
    variant="ghost"
    size="icon"
    :class="cn('h-7 w-7', props.class)"
    @click="toggleSidebar"
  >
    <PanelLeft animateOnHover triggerTarget="parent" />
    <span class="sr-only">Toggle Sidebar</span>
  </Button>
</template>
