<script setup lang="ts">
import { computed } from 'vue'

import { useColorMode } from '@vueuse/core'
import { Monitor, Moon, Palette as PaletteIcon, Sun } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { type Palette, usePalette } from '@/composables/usePalette'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

import ThemePreview from '@/components/layout/ThemePreview.vue'

const { t } = useI18n()
const mode = useColorMode()
const palette = usePalette()
const authStore = useAuthStore()
const { patch } = useAuthenticatedClient()

async function selectPalette(next: Palette) {
  const previous = palette.value
  palette.value = next
  if (!authStore.isAuthenticated || !authStore.profile) return
  try {
    await patch({ url: '/users/me', body: { theme: next } })
    authStore.profile.theme = next
  } catch {
    palette.value = previous
    toast.error(t('user.settings.appearance.theme.error'))
  }
}

const palettes: { id: Palette; label: string; description: string }[] = [
  {
    id: 'default',
    label: t('user.settings.appearance.theme.default'),
    description: t('user.settings.appearance.theme.defaultDescription'),
  },
  {
    id: 'classic',
    label: t('user.settings.appearance.theme.classic'),
    description: t('user.settings.appearance.theme.classicDescription'),
  },
]

const modes = [
  { id: 'light' as const, label: t('user.settings.appearance.mode.light'), icon: Sun },
  { id: 'dark' as const, label: t('user.settings.appearance.mode.dark'), icon: Moon },
  { id: 'auto' as const, label: t('user.settings.appearance.mode.system'), icon: Monitor },
]

const previewMode = computed<'light' | 'dark'>(() => {
  if (mode.value === 'dark') return 'dark'
  if (mode.value === 'light') return 'light'
  return typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
})
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <PaletteIcon class="h-5 w-5" />
        {{ t('user.settings.appearance.title') }}
      </CardTitle>
      <CardDescription>
        {{ t('user.settings.appearance.description') }}
      </CardDescription>
    </CardHeader>
    <CardContent class="space-y-6">
      <!-- Theme tiles -->
      <section>
        <h3 class="text-sm font-medium mb-3">{{ t('user.settings.appearance.theme.title') }}</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button
            v-for="p in palettes"
            :key="p.id"
            type="button"
            class="group flex items-center gap-4 rounded-lg border p-3 text-left transition-colors hover:bg-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            :class="palette === p.id ? 'border-ring bg-accent/50' : 'border-border'"
            :data-testid="`appearance-theme-${p.id}`"
            :aria-pressed="palette === p.id"
            @click="selectPalette(p.id)"
          >
            <ThemePreview
              :palette="p.id"
              :mode="previewMode"
              size="lg"
              :selected="palette === p.id"
            />
            <div class="flex-1 min-w-0">
              <p class="font-medium text-sm">{{ p.label }}</p>
              <p class="text-xs text-muted-foreground mt-0.5">{{ p.description }}</p>
            </div>
          </button>
        </div>
      </section>

      <!-- Mode picker -->
      <section>
        <h3 class="text-sm font-medium mb-3">{{ t('user.settings.appearance.mode.title') }}</h3>
        <div class="grid grid-cols-3 gap-2 rounded-md bg-muted p-1">
          <button
            v-for="m in modes"
            :key="m.id"
            type="button"
            class="flex items-center justify-center gap-2 rounded-sm py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            :class="
              mode === m.id
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            "
            :data-testid="`appearance-mode-${m.id}`"
            :aria-pressed="mode === m.id"
            @click="mode = m.id"
          >
            <component :is="m.icon" class="h-4 w-4" />
            {{ m.label }}
          </button>
        </div>
      </section>
    </CardContent>
  </Card>
</template>
