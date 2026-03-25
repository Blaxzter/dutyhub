import { computed } from 'vue'

import { useLocalStorage } from '@vueuse/core'

import enChangelog from '../changelog/generated/en.json'

const lastSeenVersion = useLocalStorage<string | null>('wirksam-last-seen-changelog', null)

// All versions sorted newest first (use English as source of truth for version list)
const allVersions = enChangelog
  .map((e) => ({ version: e.version, date: e.date, title: e.title }))
  .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())

const latestVersion = allVersions[0]?.version ?? null
const latestTitle = allVersions[0]?.title ?? null

function compareVersions(a: string, b: string): number {
  const pa = a.split('.').map(Number)
  const pb = b.split('.').map(Number)
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const diff = (pa[i] ?? 0) - (pb[i] ?? 0)
    if (diff !== 0) return diff
  }
  return 0
}

export function useChangelogStatus() {
  const hasNewVersions = computed(() => {
    if (!latestVersion) return false
    if (!lastSeenVersion.value) return true
    return compareVersions(latestVersion, lastSeenVersion.value) > 0
  })

  const newVersionCount = computed(() => {
    if (!lastSeenVersion.value) return allVersions.length
    return allVersions.filter((v) => compareVersions(v.version, lastSeenVersion.value!) > 0).length
  })

  function isNewVersion(version: string): boolean {
    if (!lastSeenVersion.value) return true
    return compareVersions(version, lastSeenVersion.value) > 0
  }

  function markAsSeen() {
    if (latestVersion) {
      lastSeenVersion.value = latestVersion
    }
  }

  return {
    hasNewVersions,
    newVersionCount,
    isNewVersion,
    markAsSeen,
    latestVersion,
    latestTitle,
  }
}
