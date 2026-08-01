<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { Loader2 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { avatarUrlFor } from '@/composables/useAvatarUrl'

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import Button from '@/components/ui/button/Button.vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import Input from '@/components/ui/input/Input.vue'
import Label from '@/components/ui/label/Label.vue'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'

import type { UserOwnedContent, UserRead } from '@/client/types.gen'
import { toastApiError } from '@/lib/api-errors'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{
  open: boolean
  user: UserRead | null
  loading: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  confirm: [transferToUserId?: string]
}>()

const { t } = useI18n()
const { get } = useAuthenticatedClient()
const authStore = useAuthStore()

const ownedContent = ref<UserOwnedContent | null>(null)
const ownedLoading = ref(false)

const transferChoice = ref<'me' | 'other'>('me')
const allUsers = ref<UserRead[]>([])
const usersLoading = ref(false)
const userSearchQuery = ref('')
const selectedTargetId = ref<string | null>(null)

const needsTransfer = computed(() => (ownedContent.value?.total ?? 0) > 0)

const filteredUsers = computed(() => {
  const q = userSearchQuery.value.toLowerCase().trim()
  return allUsers.value
    .filter((u) => u.id !== props.user?.id && u.id !== authStore.profile?.id)
    .filter(
      (u) =>
        !q || (u.name ?? '').toLowerCase().includes(q) || (u.email ?? '').toLowerCase().includes(q),
    )
})

const canConfirm = computed(() => {
  if (props.loading || ownedLoading.value) return false
  if (!needsTransfer.value) return true
  if (transferChoice.value === 'me') return !!authStore.profile?.id
  return !!selectedTargetId.value
})

const loadOwnedContent = async (userId: string) => {
  ownedLoading.value = true
  ownedContent.value = null
  try {
    const response = await get<{ data: UserOwnedContent }>({
      url: `/users/${userId}/owned-content`,
    })
    ownedContent.value = response.data
  } catch (error) {
    toastApiError(error)
  } finally {
    ownedLoading.value = false
  }
}

const loadUsers = async () => {
  if (allUsers.value.length > 0) return
  usersLoading.value = true
  try {
    const response = await get<{ data: { items: UserRead[] } }>({
      url: '/users/',
      query: { status_filter: 'active', limit: 200 },
    })
    allUsers.value = response.data.items
  } catch (error) {
    toastApiError(error)
  } finally {
    usersLoading.value = false
  }
}

watch(
  () => props.open,
  (open) => {
    if (!open) return
    transferChoice.value = 'me'
    userSearchQuery.value = ''
    selectedTargetId.value = null
    allUsers.value = []
    if (props.user) void loadOwnedContent(props.user.id)
  },
)

watch(transferChoice, (choice) => {
  if (choice === 'other') void loadUsers()
})

const submit = () => {
  if (!canConfirm.value) return
  if (!needsTransfer.value) {
    emit('confirm')
    return
  }
  const targetId =
    transferChoice.value === 'me' ? authStore.profile?.id : (selectedTargetId.value ?? undefined)
  if (!targetId) return
  emit('confirm', targetId)
}
</script>

<template>
  <Dialog :open="props.open" @update:open="emit('update:open', $event)">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{{ t('admin.users.deleteDialogTitle') }}</DialogTitle>
        <DialogDescription>
          {{
            needsTransfer
              ? t('admin.users.deleteTransferDescription', {
                  name: props.user?.name ?? props.user?.email,
                })
              : t('admin.users.deleteDialogDescription', {
                  name: props.user?.name ?? props.user?.email,
                })
          }}
        </DialogDescription>
      </DialogHeader>

      <div
        v-if="ownedLoading"
        class="flex items-center gap-2 py-2 text-sm text-muted-foreground"
      >
        <Loader2 class="h-4 w-4 animate-spin" />
        {{ t('common.states.loading') }}
      </div>

      <div v-else-if="needsTransfer && ownedContent" class="space-y-4">
        <div class="flex flex-wrap gap-2 text-sm">
          <span
            v-if="ownedContent.events > 0"
            class="rounded-md border bg-muted/50 px-2 py-1"
            data-testid="owned-events-count"
          >
            {{ t('admin.users.ownedEvents', { count: ownedContent.events }) }}
          </span>
          <span
            v-if="ownedContent.tasks > 0"
            class="rounded-md border bg-muted/50 px-2 py-1"
            data-testid="owned-tasks-count"
          >
            {{ t('admin.users.ownedTasks', { count: ownedContent.tasks }) }}
          </span>
        </div>

        <RadioGroup v-model="transferChoice" class="gap-2">
          <div class="flex items-center gap-2">
            <RadioGroupItem id="transfer-me" value="me" />
            <Label for="transfer-me" class="font-normal">
              {{ t('admin.users.transferToMe') }}
            </Label>
          </div>
          <div class="flex items-center gap-2">
            <RadioGroupItem id="transfer-other" value="other" />
            <Label for="transfer-other" class="font-normal">
              {{ t('admin.users.transferToOther') }}
            </Label>
          </div>
        </RadioGroup>

        <div v-if="transferChoice === 'other'" class="space-y-2">
          <Input
            v-model="userSearchQuery"
            :placeholder="t('admin.users.searchPlaceholder')"
            data-testid="transfer-user-search"
          />
          <div
            v-if="usersLoading"
            class="flex items-center gap-2 py-2 text-sm text-muted-foreground"
          >
            <Loader2 class="h-4 w-4 animate-spin" />
            {{ t('common.states.loading') }}
          </div>
          <div
            v-else-if="filteredUsers.length > 0"
            class="max-h-48 divide-y overflow-y-auto rounded-md border"
          >
            <button
              v-for="candidate in filteredUsers"
              :key="candidate.id"
              type="button"
              class="flex w-full items-center gap-3 px-3 py-2 text-left transition-colors hover:bg-muted/50"
              :class="selectedTargetId === candidate.id ? 'bg-muted' : ''"
              :aria-pressed="selectedTargetId === candidate.id"
              @click="selectedTargetId = candidate.id"
            >
              <Avatar class="size-7 shrink-0">
                <AvatarImage v-if="avatarUrlFor(candidate)" :src="avatarUrlFor(candidate)!" />
                <AvatarFallback class="text-xs">
                  {{ (candidate.name ?? candidate.email ?? '?').slice(0, 2).toUpperCase() }}
                </AvatarFallback>
              </Avatar>
              <div class="min-w-0">
                <p class="truncate text-sm font-medium leading-none">
                  {{ candidate.name ?? candidate.email }}
                </p>
                <p v-if="candidate.name" class="truncate text-xs text-muted-foreground">
                  {{ candidate.email }}
                </p>
              </div>
            </button>
          </div>
          <p v-else class="text-sm text-muted-foreground">
            {{ t('admin.users.transferNoResults') }}
          </p>
        </div>
      </div>

      <DialogFooter>
        <Button variant="outline" @click="emit('update:open', false)">
          {{ t('common.actions.cancel') }}
        </Button>
        <Button
          variant="destructive"
          :disabled="!canConfirm"
          data-testid="confirm-delete-user"
          @click="submit"
        >
          <Loader2 v-if="props.loading" class="h-4 w-4 animate-spin" />
          {{ needsTransfer ? t('admin.users.transferAndDelete') : t('admin.users.delete') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
