<script setup lang="ts">
import { Plus } from '@respeak/lucide-motion-vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

import type { TaskRead } from '@/client/types.gen'
import { formatDate } from '@/lib/format'
import { statusVariant } from '@/lib/status'

defineProps<{
  tasks: TaskRead[]
  eventId: string
  canManage?: boolean
}>()

const { t } = useI18n()
const router = useRouter()

const navigateToTask = (task: TaskRead) => {
  router.push({ name: 'task-detail', params: { eventId: task.id } })
}
</script>

<template>
  <div data-testid="section-tasks" class="space-y-3">
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold">{{ t('duties.events.detail.tasks') }}</h2>
      <Button
        v-if="canManage"
        size="sm"
        class="max-xl:hidden"
        @click="router.push({ name: 'task-create', query: { eventId } })"
      >
        <Plus class="mr-1.5 h-4 w-4" animateOnHover triggerTarget="parent" />
        {{ t('duties.tasks.create') }}
      </Button>
    </div>
    <p v-if="tasks.length === 0" class="text-sm text-muted-foreground">
      {{ t('duties.events.detail.tasksEmpty') }}
    </p>
    <div v-else class="grid gap-3 sm:grid-cols-2">
      <Card
        v-for="task in tasks"
        :key="task.id"
        class="cursor-pointer transition-colors hover:bg-muted/50"
        @click="navigateToTask(task)"
      >
        <CardHeader class="pb-2">
          <div class="flex items-start justify-between">
            <CardTitle class="text-base">{{ task.name }}</CardTitle>
            <Badge :variant="statusVariant(task.status)">
              {{ t(`duties.tasks.statuses.${task.status ?? 'draft'}`) }}
            </Badge>
          </div>
          <CardDescription v-if="task.description">{{ task.description }}</CardDescription>
        </CardHeader>
        <CardContent>
          <p class="text-sm text-muted-foreground">
            {{ formatDate(task.start_date) }} – {{ formatDate(task.end_date) }}
          </p>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
