<script setup lang="ts">
import { Check, Trash2, UserCheck, Users } from '@respeak/lucide-motion-vue'
import { Pencil } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

import AvailabilityDisplay from '@/components/tasks/AvailabilityDisplay.vue'

import type { UserAvailabilityRead, UserAvailabilityWithUser } from '@/client/types.gen'
import { formatDateWithTime } from '@/lib/format'

defineProps<{
  myAvailability: UserAvailabilityRead | null
  allAvailabilities: UserAvailabilityWithUser[]
  canManage?: boolean
}>()

const emit = defineEmits<{
  edit: []
  remove: []
}>()

const { t } = useI18n()
</script>

<template>
  <!-- My Availability -->
  <Card data-testid="section-my-availability">
    <CardHeader>
      <div class="flex items-center justify-between gap-2">
        <div class="min-w-0 space-y-1">
          <CardTitle class="flex items-center gap-2">
            <UserCheck class="h-5 w-5 shrink-0" animateOnHover triggerTarget="parent" />
            {{ t('duties.availability.title') }}
          </CardTitle>
          <CardDescription>{{ t('duties.availability.subtitle') }}</CardDescription>
        </div>
        <div class="flex gap-2 shrink-0">
          <Button
            v-if="myAvailability"
            data-testid="btn-availability"
            variant="outline"
            size="sm"
            @click="emit('edit')"
          >
            <Pencil class="sm:mr-2 h-4 w-4" />
            <span class="hidden sm:inline">{{ t('duties.availability.update') }}</span>
          </Button>
          <Button
            v-if="myAvailability"
            data-testid="btn-remove-availability"
            variant="ghost"
            size="sm"
            class="text-destructive"
            @click="emit('remove')"
          >
            <Trash2 class="sm:mr-1.5 h-4 w-4" animateOnHover triggerTarget="parent" />
            <span class="hidden sm:inline">{{ t('duties.availability.remove') }}</span>
          </Button>
          <Button
            v-if="!myAvailability"
            data-testid="btn-availability"
            size="sm"
            @click="emit('edit')"
          >
            <Check class="sm:mr-2 h-4 w-4" animateOnHover triggerTarget="parent" />
            <span class="hidden sm:inline">{{ t('duties.availability.register') }}</span>
          </Button>
        </div>
      </div>
    </CardHeader>
    <CardContent>
      <AvailabilityDisplay v-if="myAvailability" :availability="myAvailability" />
      <p v-else class="text-sm text-muted-foreground">
        {{ t('duties.availability.notRegistered') }}
      </p>
    </CardContent>
  </Card>

  <!-- Member Availabilities (manager view) -->
  <div v-if="canManage" data-testid="section-admin-availabilities" class="space-y-3">
    <h2 class="flex items-center gap-2 text-xl font-semibold">
      <Users class="h-5 w-5" animateOnHover triggerTarget="parent" />
      {{ t('duties.availability.adminTitle') }}
    </h2>
    <p v-if="allAvailabilities.length === 0" class="text-sm text-muted-foreground">
      {{ t('duties.availability.adminEmpty') }}
    </p>
    <div v-else class="overflow-hidden rounded-lg border">
      <table class="w-full text-sm">
        <thead class="bg-muted/50">
          <tr>
            <th class="px-4 py-2 text-left font-medium">User</th>
            <th class="px-4 py-2 text-left font-medium">
              {{ t('duties.availability.fields.type') }}
            </th>
            <th class="px-4 py-2 text-left font-medium">
              {{ t('duties.availability.fields.dates') }}
            </th>
            <th class="px-4 py-2 text-left font-medium">
              {{ t('duties.availability.fields.notes') }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y">
          <tr v-for="avail in allAvailabilities" :key="avail.id" class="hover:bg-muted/30">
            <td class="px-4 py-2">
              <div>{{ avail.user_full_name ?? '—' }}</div>
              <div class="text-xs text-muted-foreground">{{ avail.user_email ?? '' }}</div>
            </td>
            <td class="px-4 py-2">
              <div class="flex flex-wrap items-center gap-1.5">
                <Badge variant="secondary">
                  {{ t(`duties.availability.types.${avail.availability_type}`) }}
                </Badge>
                <span
                  v-if="avail.default_start_time || avail.default_end_time"
                  class="text-xs text-muted-foreground"
                >
                  {{
                    [avail.default_start_time, avail.default_end_time].filter(Boolean).join(' – ')
                  }}
                </span>
              </div>
            </td>
            <td class="px-4 py-2">
              <span v-if="avail.available_dates?.length">
                <span class="text-xs">
                  {{ avail.available_dates.map((d) => formatDateWithTime(d)).join(', ') }}
                </span>
              </span>
              <span v-else class="text-muted-foreground">—</span>
            </td>
            <td class="max-w-48 px-4 py-2 text-muted-foreground">
              <p class="line-clamp-3" :title="avail.notes ?? undefined">
                {{ avail.notes ?? '—' }}
              </p>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
