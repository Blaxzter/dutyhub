<template>
  <Card>
    <CardHeader>
      <div class="flex items-center justify-between">
        <CardTitle class="flex items-center gap-2">
          <CalendarIcon class="h-5 w-5" />
          {{ t('user.settings.calendarSync.title') }}
        </CardTitle>
        <Switch
          v-if="feedSettings"
          :model-value="feedSettings.is_enabled"
          @update:model-value="(v: boolean) => handleToggle(v)"
        />
      </div>
      <CardDescription>
        {{ t('user.settings.calendarSync.description') }}
      </CardDescription>
    </CardHeader>
    <CardContent>
      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-4">
        <LoaderIcon class="h-5 w-5 animate-spin text-muted-foreground" />
      </div>

      <!-- Never set up -->
      <div v-else-if="!feedSettings" class="space-y-3">
        <Button variant="outline" class="w-full sm:w-auto" @click="handleEnable">
          <CalendarIcon class="h-4 w-4 mr-2" />
          {{ t('user.settings.calendarSync.enableButton') }}
        </Button>
      </div>

      <!-- Exists but disabled -->
      <div v-else-if="!feedSettings.is_enabled" class="space-y-2">
        <p class="text-sm text-muted-foreground">
          {{ t('user.settings.calendarSync.disabledMessage') }}
        </p>
      </div>

      <!-- Enabled -->
      <div v-else class="space-y-5">
        <!-- 1. Easy path: one-click add buttons -->
        <div class="space-y-2">
          <label class="text-sm font-medium">
            {{ t('user.settings.calendarSync.addTo.title') }}
          </label>
          <div class="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" as-child>
              <a :href="googleCalendarUrl" target="_blank" rel="noopener">
                <SimpleIcon :icon-data="siGoogle" :color="'#' + siGoogle.hex" class-name="size-4" />
                {{ t('user.settings.calendarSync.addTo.google') }}
              </a>
            </Button>
            <Button variant="outline" size="sm" as-child>
              <a :href="webcalUrl">
                <SimpleIcon :icon-data="siApple" class-name="size-4" />
                {{ t('user.settings.calendarSync.addTo.apple') }}
              </a>
            </Button>
            <Button variant="outline" size="sm" as-child>
              <a :href="outlookUrl" target="_blank" rel="noopener">
                <MicrosoftIcon />
                {{ t('user.settings.calendarSync.addTo.outlook') }}
              </a>
            </Button>
          </div>
        </div>

        <!-- 2. Manual URL (collapsible) -->
        <Collapsible v-model:open="showManualUrl">
          <CollapsibleTrigger as-child>
            <Button variant="ghost" size="sm" class="gap-1 px-0">
              <ChevronRightIcon
                class="h-4 w-4 transition-transform"
                :class="{ 'rotate-90': showManualUrl }"
              />
              {{ t('user.settings.calendarSync.manual.title') }}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div class="mt-3 space-y-4">
              <!-- Feed URL -->
              <div class="space-y-2">
                <label class="text-sm font-medium">
                  {{ t('user.settings.calendarSync.feedUrl') }}
                </label>
                <div class="flex gap-2">
                  <Input :model-value="feedSettings.feed_url" readonly class="font-mono text-xs" />
                  <Button variant="outline" size="icon" class="shrink-0" @click="copyUrl">
                    <CheckIcon v-if="copied" class="h-4 w-4 text-green-600" />
                    <CopyIcon v-else class="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <!-- Instructions -->
              <div class="space-y-3 rounded-lg border p-4 text-sm">
                <div>
                  <p class="font-medium">
                    {{ t('user.settings.calendarSync.instructions.googleCalendar') }}
                  </p>
                  <p class="text-muted-foreground">
                    {{ t('user.settings.calendarSync.instructions.googleSteps') }}
                  </p>
                </div>
                <div>
                  <p class="font-medium">
                    {{ t('user.settings.calendarSync.instructions.appleCalendar') }}
                  </p>
                  <p class="text-muted-foreground">
                    {{ t('user.settings.calendarSync.instructions.appleSteps') }}
                  </p>
                </div>
                <div>
                  <p class="font-medium">
                    {{ t('user.settings.calendarSync.instructions.outlook') }}
                  </p>
                  <p class="text-muted-foreground">
                    {{ t('user.settings.calendarSync.instructions.outlookSteps') }}
                  </p>
                </div>
              </div>

              <!-- Regenerate + last synced -->
              <div class="flex flex-wrap items-center gap-3">
                <Dialog v-model:open="showRegenerateDialog">
                  <DialogTrigger as-child>
                    <Button variant="outline" size="sm">
                      <RefreshCwIcon class="h-4 w-4 mr-2" />
                      {{ t('user.settings.calendarSync.regenerate') }}
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>{{
                        t('user.settings.calendarSync.regenerateConfirmTitle')
                      }}</DialogTitle>
                      <DialogDescription>
                        {{ t('user.settings.calendarSync.regenerateConfirmDescription') }}
                      </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                      <Button variant="outline" @click="showRegenerateDialog = false">
                        {{ t('common.actions.cancel') }}
                      </Button>
                      <Button @click="handleRegenerate">
                        {{ t('user.settings.calendarSync.regenerateConfirmButton') }}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>

                <p class="text-xs text-muted-foreground">
                  <template v-if="feedSettings.last_accessed_at">
                    {{ t('user.settings.calendarSync.lastSynced') }}:
                    {{ new Date(feedSettings.last_accessed_at).toLocaleString() }}
                  </template>
                  <template v-else>
                    {{ t('user.settings.calendarSync.neverSynced') }}
                  </template>
                </p>
              </div>
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  CalendarIcon,
  CheckIcon,
  ChevronRightIcon,
  CopyIcon,
  LoaderIcon,
  RefreshCwIcon,
} from 'lucide-vue-next'
import { storeToRefs } from 'pinia'
import { siApple, siGoogle } from 'simple-icons'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import { useCalendarFeedStore } from '@/stores/calendarFeed'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'

import MicrosoftIcon from '@/components/icons/MicrosoftIcon.vue'
import SimpleIcon from '@/components/utils/SimpleIcon.vue'

const { t } = useI18n()
const store = useCalendarFeedStore()
const { feedSettings, loading } = storeToRefs(store)

const copied = ref(false)
const showRegenerateDialog = ref(false)
const showManualUrl = ref(false)

// Deep-link URLs for calendar providers
const webcalUrl = computed(() => {
  if (!feedSettings.value?.feed_url) return '#'
  return feedSettings.value.feed_url.replace(/^https?:\/\//, 'webcal://')
})

const googleCalendarUrl = computed(() => {
  if (!feedSettings.value?.feed_url) return '#'
  return `https://calendar.google.com/calendar/r?cid=${encodeURIComponent(webcalUrl.value)}`
})

const outlookUrl = computed(() => {
  if (!feedSettings.value?.feed_url) return '#'
  return `https://outlook.live.com/calendar/0/addfromweb?url=${encodeURIComponent(feedSettings.value.feed_url)}&name=${encodeURIComponent('WirkSam Bookings')}`
})

onMounted(() => {
  store.fetchFeedSettings()
})

async function handleEnable() {
  try {
    await store.enableFeed()
    toast.success(t('user.settings.calendarSync.enabled'))
  } catch {
    toast.error(t('user.settings.calendarSync.enableError'))
  }
}

async function handleToggle(checked: boolean) {
  try {
    if (checked) {
      await store.enableFeed()
      toast.success(t('user.settings.calendarSync.enabled'))
    } else {
      await store.disableFeed()
      toast.success(t('user.settings.calendarSync.disabled'))
    }
  } catch {
    toast.error(t('user.settings.calendarSync.enableError'))
  }
}

async function copyUrl() {
  if (!feedSettings.value?.feed_url) return
  try {
    await navigator.clipboard.writeText(feedSettings.value.feed_url)
    copied.value = true
    toast.success(t('user.settings.calendarSync.copied'))
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    toast.error(t('user.settings.calendarSync.copyFailed'))
  }
}

async function handleRegenerate() {
  try {
    await store.regenerateFeed()
    showRegenerateDialog.value = false
    toast.success(t('user.settings.calendarSync.regenerated'))
  } catch {
    toast.error(t('user.settings.calendarSync.regenerateError'))
  }
}
</script>
