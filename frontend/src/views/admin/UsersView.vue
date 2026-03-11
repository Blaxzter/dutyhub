<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { Shield, ShieldOff, UserCheck, UserX } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import type { UserRead } from '@/client/types.gen'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { toastApiError } from '@/lib/api-errors'

const { t } = useI18n()
const { get, patch } = useAuthenticatedClient()

const users = ref<UserRead[]>([])
const loading = ref(false)
const updatingId = ref<string | null>(null)

const loadUsers = async () => {
  loading.value = true
  try {
    const response = await get<{ data: UserRead[] }>({ url: '/users/' })
    users.value = response.data
  } catch (error) {
    toastApiError(error)
  } finally {
    loading.value = false
  }
}

const toggleAdmin = async (user: UserRead) => {
  updatingId.value = user.id
  const hasAdmin = user.roles.includes('admin')
  const newRoles = hasAdmin ? user.roles.filter((r) => r !== 'admin') : [...user.roles, 'admin']
  try {
    const response = await patch<{ data: UserRead }>({
      url: `/users/${user.id}`,
      body: { roles: newRoles },
    })
    const idx = users.value.findIndex((u) => u.id === user.id)
    if (idx !== -1) users.value[idx] = response.data
    toast.success(
      hasAdmin ? t('admin.users.removedAdmin', { name: user.name ?? user.email }) : t('admin.users.grantedAdmin', { name: user.name ?? user.email }),
    )
  } catch (error) {
    toastApiError(error)
  } finally {
    updatingId.value = null
  }
}

const toggleActive = async (user: UserRead) => {
  updatingId.value = user.id
  try {
    const response = await patch<{ data: UserRead }>({
      url: `/users/${user.id}`,
      body: { is_active: !user.is_active },
    })
    const idx = users.value.findIndex((u) => u.id === user.id)
    if (idx !== -1) users.value[idx] = response.data
    toast.success(
      user.is_active
        ? t('admin.users.deactivated', { name: user.name ?? user.email })
        : t('admin.users.activated', { name: user.name ?? user.email }),
    )
  } catch (error) {
    toastApiError(error)
  } finally {
    updatingId.value = null
  }
}

onMounted(loadUsers)
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-6">
    <div class="space-y-2">
      <h1 class="text-3xl font-bold">{{ t('admin.users.title') }}</h1>
      <p class="text-muted-foreground">{{ t('admin.users.subtitle') }}</p>
    </div>

    <div v-if="loading" class="py-12 text-center text-muted-foreground">
      {{ t('common.states.loading') }}
    </div>

    <div v-else class="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{{ t('admin.users.columns.name') }}</TableHead>
            <TableHead>{{ t('admin.users.columns.email') }}</TableHead>
            <TableHead>{{ t('admin.users.columns.roles') }}</TableHead>
            <TableHead>{{ t('admin.users.columns.status') }}</TableHead>
            <TableHead class="text-right">{{ t('admin.users.columns.actions') }}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="user in users" :key="user.id">
            <TableCell class="font-medium">{{ user.name ?? '—' }}</TableCell>
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
              <Badge :variant="user.is_active ? 'default' : 'destructive'">
                {{ user.is_active ? t('admin.users.active') : t('admin.users.pending') }}
              </Badge>
            </TableCell>
            <TableCell class="text-right">
              <div class="flex items-center justify-end gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  :disabled="updatingId === user.id"
                  @click="toggleActive(user)"
                >
                  <UserX v-if="user.is_active" class="mr-1.5 h-4 w-4 text-destructive" />
                  <UserCheck v-else class="mr-1.5 h-4 w-4 text-primary" />
                  {{ user.is_active ? t('admin.users.deactivate') : t('admin.users.activate') }}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  :disabled="updatingId === user.id"
                  @click="toggleAdmin(user)"
                >
                  <ShieldOff v-if="user.roles.includes('admin')" class="mr-1.5 h-4 w-4 text-destructive" />
                  <Shield v-else class="mr-1.5 h-4 w-4 text-primary" />
                  {{ user.roles.includes('admin') ? t('admin.users.removeAdmin') : t('admin.users.makeAdmin') }}
                </Button>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>
  </div>
</template>
