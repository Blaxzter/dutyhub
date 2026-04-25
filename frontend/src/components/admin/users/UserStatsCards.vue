<script setup lang="ts">
import { UserCheck, Users } from '@respeak/lucide-motion-vue'
import { UserRoundX, UserX } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

defineProps<{
  total: number
  active: number
  pending: number
  rejected: number
}>()

const { t } = useI18n()
</script>

<template>
  <div data-testid="section-stats" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <Card data-testid="stat-total">
      <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle class="text-sm font-medium">{{ t('admin.users.statsTotal') }}</CardTitle>
        <Users class="h-4 w-4 text-muted-foreground" animateOnHover triggerTarget="parent" />
      </CardHeader>
      <CardContent>
        <div class="text-2xl font-bold">{{ total }}</div>
      </CardContent>
    </Card>
    <Card data-testid="stat-active">
      <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle class="text-sm font-medium">{{ t('admin.users.active') }}</CardTitle>
        <UserCheck class="h-4 w-4 text-muted-foreground" animateOnHover triggerTarget="parent" />
      </CardHeader>
      <CardContent>
        <div class="text-2xl font-bold">{{ active }}</div>
      </CardContent>
    </Card>
    <Card data-testid="stat-pending">
      <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle class="text-sm font-medium">{{ t('admin.users.pending') }}</CardTitle>
        <UserX class="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div class="text-2xl font-bold">{{ pending }}</div>
      </CardContent>
    </Card>
    <Card data-testid="stat-rejected">
      <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle class="text-sm font-medium">{{ t('admin.users.rejected') }}</CardTitle>
        <UserRoundX class="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div class="text-2xl font-bold">{{ rejected }}</div>
      </CardContent>
    </Card>
  </div>
</template>
