<script setup lang="ts">
import { ref } from 'vue'
import { watch } from 'vue'

import { ShieldCheck, UserPlus, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import Input from '@/components/ui/input/Input.vue'
import Separator from '@/components/ui/separator/Separator.vue'

import type { UserRead } from '@/client/types.gen'
import { toastApiError } from '@/lib/api-errors'

const props = defineProps<{
  groupId: string
  managers: UserRead[]
}>()

const emit = defineEmits<{
  updated: []
}>()

const { t } = useI18n()
const { get, post, delete: del } = useAuthenticatedClient()

const allUsers = ref<UserRead[]>([])
const userSearchQuery = ref('')
const showAddManager = ref(false)
const removingManagerId = ref<string | null>(null)
const assigningUserId = ref<string | null>(null)

const filteredUsers = ref<UserRead[]>([])

const updateFilteredUsers = () => {
  const ids = new Set(props.managers.map((m) => m.id))
  const q = userSearchQuery.value.toLowerCase().trim()
  filteredUsers.value = allUsers.value
    .filter((u) => !ids.has(u.id))
    .filter((u) => !u.roles.includes('admin') && !u.roles.includes('event_manager'))
    .filter(
      (u) =>
        !q || (u.name ?? '').toLowerCase().includes(q) || (u.email ?? '').toLowerCase().includes(q),
    )
}

watch([() => props.managers, userSearchQuery], updateFilteredUsers, { deep: true })

const openAddManager = async () => {
  showAddManager.value = true
  userSearchQuery.value = ''
  if (allUsers.value.length === 0) {
    try {
      const res = await get<{ data: UserRead[] }>({ url: '/users/', query: { limit: 200 } })
      allUsers.value = res.data
      updateFilteredUsers()
    } catch {
      allUsers.value = []
    }
  }
}

const closeAddManager = () => {
  showAddManager.value = false
  userSearchQuery.value = ''
}

const assignManager = async (userId: string) => {
  assigningUserId.value = userId
  try {
    await post<{ data: UserRead }>({
      url: `/event-groups/${props.groupId}/managers/${userId}`,
    })
    emit('updated')
    toast.success(t('duties.eventGroups.detail.managerAdded'))
  } catch (error) {
    toastApiError(error)
  } finally {
    assigningUserId.value = null
  }
}

const removeManager = async (userId: string) => {
  removingManagerId.value = userId
  try {
    await del({ url: `/event-groups/${props.groupId}/managers/${userId}` })
    emit('updated')
    toast.success(t('duties.eventGroups.detail.managerRemoved'))
  } catch (error) {
    toastApiError(error)
  } finally {
    removingManagerId.value = null
  }
}
</script>

<template>
  <Card data-testid="section-group-managers">
    <CardHeader>
      <div class="flex items-center justify-between gap-2">
        <div class="space-y-1">
          <CardTitle class="flex items-center gap-2">
            <ShieldCheck class="h-5 w-5 shrink-0" />
            {{ t('duties.eventGroups.detail.managers') }}
          </CardTitle>
          <CardDescription>{{ t('duties.eventGroups.detail.managersSubtitle') }}</CardDescription>
        </div>
        <Button v-if="!showAddManager" size="sm" variant="outline" @click="openAddManager">
          <UserPlus class="mr-1.5 h-4 w-4" />
          {{ t('duties.eventGroups.detail.addManager') }}
        </Button>
      </div>
    </CardHeader>
    <CardContent class="space-y-3">
      <p v-if="managers.length === 0 && !showAddManager" class="text-sm text-muted-foreground">
        {{ t('duties.eventGroups.detail.managersEmpty') }}
      </p>
      <div v-if="managers.length > 0" class="space-y-1.5">
        <div
          v-for="manager in managers"
          :key="manager.id"
          class="flex items-center justify-between gap-2 rounded-md border px-3 py-2"
        >
          <div class="flex min-w-0 items-center gap-3">
            <Avatar class="size-7">
              <AvatarImage v-if="manager.picture" :src="manager.picture" />
              <AvatarFallback class="text-xs">
                {{ (manager.name ?? manager.email ?? '?').slice(0, 2).toUpperCase() }}
              </AvatarFallback>
            </Avatar>
            <div class="min-w-0">
              <p class="truncate text-sm font-medium leading-none">
                {{ manager.name ?? manager.email }}
              </p>
              <p v-if="manager.name" class="truncate text-xs text-muted-foreground">
                {{ manager.email }}
              </p>
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <Badge
              v-if="manager.roles.includes('event_manager')"
              variant="outline"
              class="border-amber-300 bg-amber-50 text-amber-600 dark:border-amber-700 dark:bg-amber-950/30"
            >
              {{ t('duties.eventGroups.detail.roleEventManager') }}
            </Badge>
            <Button
              variant="ghost"
              size="icon"
              class="size-7 text-muted-foreground hover:text-destructive"
              :disabled="removingManagerId === manager.id"
              @click="removeManager(manager.id)"
            >
              <X class="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </div>

      <!-- Add Manager panel -->
      <template v-if="showAddManager">
        <Separator v-if="managers.length > 0" />
        <div class="space-y-2">
          <Input
            v-model="userSearchQuery"
            :placeholder="t('duties.eventGroups.detail.managersSearch')"
            autofocus
          />
          <div
            v-if="filteredUsers.length > 0"
            class="max-h-48 divide-y overflow-y-auto rounded-md border"
          >
            <button
              v-for="user in filteredUsers"
              :key="user.id"
              type="button"
              class="flex w-full items-center gap-3 px-3 py-2 text-left transition-colors hover:bg-muted/50 disabled:opacity-50"
              :disabled="assigningUserId === user.id"
              @click="assignManager(user.id)"
            >
              <Avatar class="size-7 shrink-0">
                <AvatarImage v-if="user.picture" :src="user.picture" />
                <AvatarFallback class="text-xs">
                  {{ (user.name ?? user.email ?? '?').slice(0, 2).toUpperCase() }}
                </AvatarFallback>
              </Avatar>
              <div class="min-w-0">
                <p class="text-sm font-medium leading-none">{{ user.name ?? user.email }}</p>
                <p v-if="user.name" class="text-xs text-muted-foreground">{{ user.email }}</p>
              </div>
            </button>
          </div>
          <p v-else-if="userSearchQuery" class="text-sm text-muted-foreground">
            {{ t('duties.eventGroups.detail.managersNoResults') }}
          </p>
          <div class="flex justify-end">
            <Button variant="ghost" size="sm" @click="closeAddManager">
              {{ t('common.actions.cancel') }}
            </Button>
          </div>
        </div>
      </template>
    </CardContent>
  </Card>
</template>
