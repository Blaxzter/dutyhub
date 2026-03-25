<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useI18n } from 'vue-i18n'

import { useChangelogStatus } from '@/composables/useChangelogStatus'

import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogScrollContent,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const { t, locale } = useI18n()
const { isNewVersion, markAsSeen } = useChangelogStatus()

onMounted(markAsSeen)

const lightboxSrc = ref('')
const lightboxAlt = ref('')
const lightboxOpen = ref(false)

function onContentClick(e: MouseEvent) {
  const img = (e.target as HTMLElement).closest('img')
  if (!img) return
  lightboxSrc.value = img.src
  lightboxAlt.value = img.alt || ''
  lightboxOpen.value = true
}

// Import pre-rendered changelog JSON per locale
import enChangelog from '../changelog/generated/en.json'
import deChangelog from '../changelog/generated/de.json'

const generatedEntries: Record<string, { title: string; version: string; date: string; html: string }[]> = {
  en: enChangelog,
  de: deChangelog,
}

// Import changelog images per locale so Vite resolves their asset URLs
const rawImages = import.meta.glob('../changelog/images/**/*', {
  eager: true,
  import: 'default',
}) as Record<string, string>

// Build a nested map: { locale: { filename: url } }
const imagesByLocale: Record<string, Record<string, string>> = {}
for (const [path, url] of Object.entries(rawImages)) {
  const parts = path.split('/')
  const filename = parts.pop()!
  const loc = parts.pop()!
  if (!imagesByLocale[loc]) imagesByLocale[loc] = {}
  imagesByLocale[loc][filename] = url
}

function resolveImagePaths(html: string, loc: string): string {
  const localeImages = imagesByLocale[loc] ?? {}
  const fallbackImages = imagesByLocale.de ?? {}
  // Resolve locale-aware image URLs and add accessibility attributes
  return html.replace(/<img\s+src="\.\/images\/([^"]+)"\s+alt="([^"]*)"/g, (_, filename, alt) => {
    const resolved = localeImages[filename] ?? fallbackImages[filename]
    const src = resolved ?? `./images/${filename}`
    return `<img src="${src}" alt="${alt}" role="img" aria-label="${alt}" loading="lazy"`
  })
}

interface ChangelogEntry {
  title: string
  version: string
  date: Date
  html: string
}

// Merge locale entries with English fallback, resolve images
const entries = computed<ChangelogEntry[]>(() => {
  const localized = generatedEntries[locale.value] ?? []
  const fallback = generatedEntries.en ?? []

  // Build map by version: English first, then overlay locale
  const byVersion = new Map<string, { title: string; version: string; date: string; html: string }>()
  for (const entry of fallback) byVersion.set(entry.version, entry)
  for (const entry of localized) byVersion.set(entry.version, entry)

  return Array.from(byVersion.values())
    .map((e) => ({
      title: e.title,
      version: e.version,
      date: new Date(e.date),
      html: resolveImagePaths(e.html, locale.value),
    }))
    .sort((a, b) => b.date.getTime() - a.date.getTime())
})

const selectedVersion = ref<string | undefined>(undefined)
const selected = computed(
  () => entries.value.find((e) => e.version === selectedVersion.value) ?? entries.value[0],
)

function formatDateLong(date: Date): string {
  return date.toLocaleString(locale.value, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div class="mx-auto max-w-7xl">
    <!-- Mobile: header + version select -->
    <div class="md:hidden space-y-4 mb-6">
      <div class="space-y-2">
        <h1 class="text-3xl font-bold">{{ t('changelog.title') }}</h1>
        <p class="text-muted-foreground">{{ t('changelog.subtitle') }}</p>
      </div>
      <Select v-model="selectedVersion">
        <SelectTrigger>
          <SelectValue :placeholder="selected ? `v${selected.version}` : ''" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem
            v-for="(entry, index) in entries"
            :key="entry.version"
            :value="entry.version"
          >
            v{{ entry.version }}
            <span v-if="index === 0" class="text-muted-foreground ml-1">
              ({{ t('changelog.latest') }})
            </span>
          </SelectItem>
        </SelectContent>
      </Select>
    </div>

    <!-- Header (desktop) — indented past the nav column -->
    <div class="hidden md:block space-y-2 mb-6" style="padding-left: calc(9rem + 2rem)">
      <h1 class="text-3xl font-bold">{{ t('changelog.title') }}</h1>
      <p class="text-muted-foreground">{{ t('changelog.subtitle') }}</p>
    </div>

    <!-- Two-column layout -->
    <div class="flex gap-8 items-start">
      <!-- Version nav (desktop) -->
      <nav class="hidden md:block w-36 shrink-0 self-start sticky top-4">
        <div class="rounded-lg border p-2 space-y-0.5">
          <button
            v-for="(entry, index) in entries"
            :key="entry.version"
            class="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-sm transition-colors"
            :class="
              selected?.version === entry.version
                ? 'bg-accent text-accent-foreground font-medium'
                : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
            "
            @click="selectedVersion = entry.version"
          >
            <span
              class="size-1.5 shrink-0 rounded-full"
              :class="index === 0 ? 'bg-primary' : 'bg-border'"
            />
            <span class="truncate flex-1">v{{ entry.version }}</span>
            <span
              v-if="isNewVersion(entry.version)"
              class="size-1.5 shrink-0 rounded-full bg-primary"
            />
          </button>
        </div>
      </nav>

      <!-- Content -->
      <div v-if="selected" class="min-w-0 flex-1">
        <div class="space-y-1 mb-4">
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="text-xl font-semibold">{{ selected.title }}</h2>
            <Badge
              v-if="selected.version === entries[0]?.version"
              variant="default"
              class="text-[10px]"
            >
              {{ t('changelog.latest') }}
            </Badge>
          </div>
          <div class="flex items-center gap-2 text-sm text-muted-foreground">
            <span>v{{ selected.version }}</span>
            <span>&middot;</span>
            <time>{{ formatDateLong(selected.date) }}</time>
          </div>
        </div>

        <div class="changelog-content" v-html="selected.html" @click="onContentClick" />
      </div>
    </div>

    <!-- Image lightbox -->
    <Dialog v-model:open="lightboxOpen">
      <DialogScrollContent class="max-w-4xl p-2">
        <DialogTitle class="sr-only">{{ lightboxAlt }}</DialogTitle>
        <img
          :src="lightboxSrc"
          :alt="lightboxAlt"
          class="w-full rounded-md"
        />
      </DialogScrollContent>
    </Dialog>
  </div>
</template>

<style scoped>
.changelog-content :deep(h2) {
  font-size: 1.125rem;
  font-weight: 600;
  margin-top: 1.5rem;
  margin-bottom: 0.5rem;
}

.changelog-content :deep(h3) {
  font-size: 1rem;
  font-weight: 600;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

.changelog-content :deep(p) {
  color: var(--muted-foreground);
  margin-bottom: 0.75rem;
  line-height: 1.625;
}

.changelog-content :deep(ul) {
  list-style-type: disc;
  padding-left: 1.25rem;
  margin-bottom: 0.75rem;
}

.changelog-content :deep(ul li) {
  color: var(--muted-foreground);
  margin-bottom: 0.25rem;
  line-height: 1.625;
}

.changelog-content :deep(img) {
  border-radius: var(--radius);
  border: 1px solid var(--border);
  margin-top: 1rem;
  margin-bottom: 1rem;
  max-width: 22rem;
  max-height: 20rem;
  width: 100%;
  object-fit: cover;
  object-position: top;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  cursor: zoom-in;
  transition: box-shadow 0.2s;
}

.changelog-content :deep(img:hover) {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.14);
}

.changelog-content :deep(a) {
  color: var(--primary);
  text-decoration: underline;
}

.changelog-content :deep(code) {
  font-size: 0.875rem;
  background: var(--muted);
  padding: 0.125rem 0.375rem;
  border-radius: var(--radius-sm);
}
</style>
