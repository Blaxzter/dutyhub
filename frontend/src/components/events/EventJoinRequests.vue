<script setup lang="ts">
import { ref } from 'vue'

import { Check, UserCheck, X } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { avatarUrlFor } from '@/composables/useAvatarUrl'

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

import type { EventJoinRequestRead } from '@/client/types.gen'
import { toastApiError } from '@/lib/api-errors'

const props = defineProps<{
  eventId: string
  requests: EventJoinRequestRead[]
}>()

const emit = defineEmits<{ updated: [] }>()

const { t } = useI18n()
const { post } = useAuthenticatedClient()

const busyId = ref<string | null>(null)

function initials(request: EventJoinRequestRead): string {
  return (request.user_name ?? request.user_email ?? '?').slice(0, 2).toUpperCase()
}

function avatarSrc(request: EventJoinRequestRead): string | undefined {
  return avatarUrlFor({ id: request.user_id, avatar_etag: request.user_avatar_etag }) ?? undefined
}

async function decide(request: EventJoinRequestRead, approve: boolean) {
  busyId.value = request.id
  try {
    await post({
      url: `/events/${props.eventId}/join-requests/${request.id}/decide`,
      body: { approve, role: 'member' },
    })
    emit('updated')
    toast.success(
      approve
        ? t('duties.events.joinRequests.approved', {
            name: request.user_name ?? request.user_email,
          })
        : t('duties.events.joinRequests.declined'),
    )
  } catch (error) {
    toastApiError(error)
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <Card data-testid="section-join-requests">
    <CardHeader>
      <div class="flex items-center justify-between gap-2">
        <div class="space-y-1">
          <CardTitle class="flex items-center gap-2">
            <UserCheck class="h-5 w-5 shrink-0" />
            {{ t('duties.events.joinRequests.title') }}
          </CardTitle>
          <CardDescription>{{ t('duties.events.joinRequests.subtitle') }}</CardDescription>
        </div>
        <Badge v-if="requests.length > 0" variant="secondary" data-testid="join-requests-count">
          {{ requests.length }}
        </Badge>
      </div>
    </CardHeader>

    <CardContent class="space-y-1.5">
      <p
        v-if="requests.length === 0"
        class="text-sm text-muted-foreground"
        data-testid="join-requests-empty"
      >
        {{ t('duties.events.joinRequests.empty') }}
      </p>

      <div
        v-for="request in requests"
        :key="request.id"
        class="flex flex-wrap items-center justify-between gap-3 rounded-md border px-3 py-2"
        data-testid="join-request-row"
      >
        <div class="flex min-w-0 items-center gap-3">
          <Avatar class="size-7">
            <AvatarImage v-if="avatarSrc(request)" :src="avatarSrc(request)!" />
            <AvatarFallback class="text-xs">{{ initials(request) }}</AvatarFallback>
          </Avatar>
          <div class="min-w-0">
            <p class="truncate text-sm font-medium leading-none">
              {{ request.user_name ?? request.user_email }}
            </p>
            <p v-if="request.user_name" class="truncate text-xs text-muted-foreground">
              {{ request.user_email }}
            </p>
            <p v-if="request.message" class="truncate text-xs italic text-muted-foreground">
              {{ request.message }}
            </p>
          </div>
        </div>

        <div class="flex shrink-0 items-center gap-2">
          <Button
            size="sm"
            data-testid="btn-approve-request"
            :disabled="busyId === request.id"
            @click="decide(request, true)"
          >
            <Check class="mr-1.5 h-3.5 w-3.5" />
            {{ t('duties.events.joinRequests.approve') }}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            class="text-muted-foreground hover:text-destructive"
            data-testid="btn-decline-request"
            :disabled="busyId === request.id"
            @click="decide(request, false)"
          >
            <X class="mr-1.5 h-3.5 w-3.5" />
            {{ t('duties.events.joinRequests.decline') }}
          </Button>
        </div>
      </div>
    </CardContent>
  </Card>
</template>
