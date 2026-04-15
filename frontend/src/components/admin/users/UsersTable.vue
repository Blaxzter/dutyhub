<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import Badge from '@/components/ui/badge/Badge.vue'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

import UserRowActions from './UserRowActions.vue'

import type { UserRead } from '@/client/types.gen'

type UserStatus = 'active' | 'rejected' | 'pending'

defineProps<{
  users: UserRead[]
  updatingId: string | null
}>()

const emit = defineEmits<{
  toggleActive: [user: UserRead]
  reject: [user: UserRead]
  toggleAdmin: [user: UserRead]
  toggleEventManager: [user: UserRead]
  delete: [user: UserRead]
}>()

const { t } = useI18n()

const getUserStatus = (user: UserRead): UserStatus => {
  if (user.is_active) return 'active'
  if (user.rejection_reason) return 'rejected'
  return 'pending'
}

const getStatusVariant = (status: UserStatus) => {
  if (status === 'active') return 'default' as const
  if (status === 'rejected') return 'destructive' as const
  return 'secondary' as const
}

const getInitials = (user: UserRead) => {
  if (user.name) {
    return user.name
      .split(' ')
      .map((w) => w.replace(/[^a-zA-Z]/g, '')[0])
      .filter(Boolean)
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }
  return user.email?.[0]?.toUpperCase() ?? '?'
}

const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
</script>

<template>
  <div data-testid="users-table" class="rounded-lg border">
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{{ t('admin.users.columns.name') }}</TableHead>
          <TableHead>{{ t('admin.users.columns.email') }}</TableHead>
          <TableHead>{{ t('admin.users.columns.roles') }}</TableHead>
          <TableHead>{{ t('admin.users.columns.status') }}</TableHead>
          <TableHead>{{ t('admin.users.columns.memberSince') }}</TableHead>
          <TableHead class="w-10" />
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow v-for="user in users" :key="user.id">
          <TableCell>
            <div class="flex items-center gap-3">
              <Avatar class="h-8 w-8 rounded-sm">
                <AvatarImage v-if="user.picture" :src="user.picture" :alt="user.name ?? ''" />
                <AvatarFallback class="rounded-sm text-xs">{{
                  getInitials(user)
                }}</AvatarFallback>
              </Avatar>
              <span class="font-medium">{{ user.name ?? '—' }}</span>
            </div>
          </TableCell>
          <TableCell class="text-muted-foreground">{{ user.email ?? '—' }}</TableCell>
          <TableCell>
            <div class="flex flex-wrap gap-1">
              <Badge v-for="role in user.roles" :key="role" variant="secondary">
                {{ role }}
              </Badge>
              <span v-if="user.roles.length === 0" class="text-xs text-muted-foreground">—</span>
            </div>
          </TableCell>
          <TableCell>
            <Badge :variant="getStatusVariant(getUserStatus(user))">
              {{ t(`admin.users.${getUserStatus(user)}`) }}
            </Badge>
          </TableCell>
          <TableCell class="text-muted-foreground">
            {{ formatDate(user.created_at) }}
          </TableCell>
          <TableCell>
            <UserRowActions
              :user="user"
              :disabled="updatingId === user.id"
              @toggle-active="emit('toggleActive', $event)"
              @reject="emit('reject', $event)"
              @toggle-admin="emit('toggleAdmin', $event)"
              @toggle-event-manager="emit('toggleEventManager', $event)"
              @delete="emit('delete', $event)"
            />
          </TableCell>
        </TableRow>
        <TableRow v-if="users.length === 0">
          <TableCell colspan="6" class="py-12 text-center text-muted-foreground">
            {{ t('admin.users.empty') }}
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  </div>
</template>
