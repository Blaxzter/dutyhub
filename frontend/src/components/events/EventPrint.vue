<script setup lang="ts">
import { List } from '@respeak/lucide-motion-vue'
import { Printer } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const props = defineProps<{
  eventId: string
}>()

const { t } = useI18n()
const router = useRouter()
</script>

<template>
  <div data-testid="section-print" class="space-y-3">
    <Card>
      <CardHeader>
        <CardTitle class="flex items-center gap-2">
          <Printer class="h-5 w-5" />
          {{ t('print.printButton') }}
        </CardTitle>
        <CardDescription>
          {{ t('duties.events.detail.printDescription') }}
        </CardDescription>
      </CardHeader>
      <CardContent class="flex flex-col gap-2">
        <Button
          variant="outline"
          class="justify-start"
          @click="
            router.push({
              name: 'print-event',
              params: { eventId: props.eventId },
              query: { mode: 'overview' },
            })
          "
        >
          <List class="mr-2 h-4 w-4" animateOnHover triggerTarget="parent" />
          {{ t('print.overview') }}
        </Button>
        <Button
          variant="outline"
          class="justify-start"
          @click="
            router.push({
              name: 'print-event',
              params: { eventId: props.eventId },
              query: { mode: 'all' },
            })
          "
        >
          <Printer class="mr-2 h-4 w-4" />
          {{ t('print.allTasks') }}
        </Button>
      </CardContent>
    </Card>
  </div>
</template>
