<template>
  <Card>
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <DownloadIcon class="h-5 w-5" animateOnHover triggerTarget="parent" />
        {{ $t('user.settings.dataExport.title') }}
      </CardTitle>
      <CardDescription>{{ $t('user.settings.dataExport.subtitle') }}</CardDescription>
    </CardHeader>
    <CardContent>
      <div class="space-y-4">
        <p class="text-sm text-muted-foreground">
          {{ $t('user.settings.dataExport.description') }}
        </p>
        <Button
          variant="outline"
          size="sm"
          class="w-full sm:w-auto"
          :disabled="isExporting"
          @click="handleExport"
        >
          <DownloadIcon class="h-4 w-4 mr-2" animateOnHover triggerTarget="parent" />
          {{
            isExporting
              ? $t('user.settings.dataExport.exporting')
              : $t('user.settings.dataExport.button')
          }}
        </Button>
        <div
          v-if="errorMessage"
          class="p-4 rounded-lg bg-red-50 border border-red-200 text-red-800"
        >
          <p class="text-sm">{{ errorMessage }}</p>
        </div>
      </div>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import { Download as DownloadIcon } from '@respeak/lucide-motion-vue'
import { useI18n } from 'vue-i18n'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const { t } = useI18n()
const { get } = useAuthenticatedClient()

const isExporting = ref(false)
const errorMessage = ref<string | null>(null)

const handleExport = async () => {
  isExporting.value = true
  errorMessage.value = null

  try {
    const data = await get<Record<string, unknown>>({ url: '/users/me/export' })

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `wirksam-data-export-${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Data export error:', error)
    errorMessage.value = t('user.settings.dataExport.error')
  } finally {
    isExporting.value = false
  }
}
</script>
