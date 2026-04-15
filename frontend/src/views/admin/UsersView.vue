<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { useMediaQuery } from '@vueuse/core'
import { Search, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import ApprovalPasswordCard from '@/components/admin/users/ApprovalPasswordCard.vue'
import DeleteUserDialog from '@/components/admin/users/DeleteUserDialog.vue'
import RejectUserDialog from '@/components/admin/users/RejectUserDialog.vue'
import UsersGroupedList from '@/components/admin/users/UsersGroupedList.vue'
import UserStatsCards from '@/components/admin/users/UserStatsCards.vue'
import UsersTable from '@/components/admin/users/UsersTable.vue'
import Button from '@/components/ui/button/Button.vue'
import Input from '@/components/ui/input/Input.vue'
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationFirst,
  PaginationItem,
  PaginationLast,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'

import type { UserCounts, UserListResponse, UserRead } from '@/client/types.gen'
import { toastApiError } from '@/lib/api-errors'

type StatusFilter = 'all' | 'pending' | 'active' | 'rejected'

const PAGE_SIZE = 20
const SEARCH_DEBOUNCE_MS = 300

const { t } = useI18n()
const { get, patch, delete: del } = useAuthenticatedClient()

const isDesktop = useMediaQuery('(min-width: 768px)')

const users = ref<UserRead[]>([])
const counts = ref<UserCounts>({ all: 0, active: 0, pending: 0, rejected: 0 })
const loading = ref(false)
const updatingId = ref<string | null>(null)

const searchInput = ref('')
const searchQuery = ref('')
const statusFilter = ref<StatusFilter>('all')
const currentPage = ref(1)

const showRejectDialog = ref(false)
const rejectingUser = ref<UserRead | null>(null)
const isRejecting = ref(false)

const showDeleteDialog = ref(false)
const deletingUser = ref<UserRead | null>(null)
const isDeleting = ref(false)

const currentTotal = computed(() => counts.value[statusFilter.value])

const totalPages = computed(() => Math.max(1, Math.ceil(currentTotal.value / PAGE_SIZE)))

const currentSectionLabel = computed(() => {
  const keys: Record<StatusFilter, string> = {
    all: 'admin.users.sections.all',
    pending: 'admin.users.sections.pending',
    active: 'admin.users.sections.active',
    rejected: 'admin.users.sections.rejected',
  }
  return t(keys[statusFilter.value])
})

const statusOptions = computed<Array<{ value: StatusFilter; label: string; count: number }>>(
  () => [
    { value: 'all', label: t('admin.users.filters.all'), count: counts.value.all },
    {
      value: 'pending',
      label: t('admin.users.filters.pending'),
      count: counts.value.pending,
    },
    {
      value: 'active',
      label: t('admin.users.filters.active'),
      count: counts.value.active,
    },
    {
      value: 'rejected',
      label: t('admin.users.filters.rejected'),
      count: counts.value.rejected,
    },
  ],
)

const replaceUser = (updated: UserRead) => {
  const idx = users.value.findIndex((u) => u.id === updated.id)
  if (idx !== -1) users.value[idx] = updated
}

const loadUsers = async () => {
  loading.value = true
  try {
    const response = await get<{ data: UserListResponse }>({
      url: '/users/',
      query: {
        q: searchQuery.value || undefined,
        status_filter: statusFilter.value,
        skip: (currentPage.value - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
      },
    })
    users.value = response.data.items
    counts.value = response.data.counts
  } catch (error) {
    toastApiError(error)
  } finally {
    loading.value = false
  }
}

let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null
watch(searchInput, (value) => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    searchQuery.value = value.trim()
  }, SEARCH_DEBOUNCE_MS)
})

watch([searchQuery, statusFilter], () => {
  currentPage.value = 1
  void loadUsers()
})

watch(currentPage, () => {
  void loadUsers()
})

const clearSearch = () => {
  searchInput.value = ''
  searchQuery.value = ''
}

const setStatus = (value: StatusFilter) => {
  statusFilter.value = value
}

const patchUserRoles = async (user: UserRead, role: 'admin' | 'event_manager') => {
  updatingId.value = user.id
  const hasRole = user.roles.includes(role)
  const newRoles = hasRole ? user.roles.filter((r) => r !== role) : [...user.roles, role]
  try {
    const response = await patch<{ data: UserRead }>({
      url: `/users/${user.id}`,
      body: { roles: newRoles },
    })
    replaceUser(response.data)
    const name = user.name ?? user.email
    const messages = {
      admin: hasRole ? 'admin.users.removedAdmin' : 'admin.users.grantedAdmin',
      event_manager: hasRole
        ? 'admin.users.removedEventManager'
        : 'admin.users.grantedEventManager',
    } as const
    toast.success(t(messages[role], { name }))
  } catch (error) {
    toastApiError(error)
  } finally {
    updatingId.value = null
  }
}

const toggleAdmin = (user: UserRead) => patchUserRoles(user, 'admin')
const toggleEventManager = (user: UserRead) => patchUserRoles(user, 'event_manager')

const toggleActive = async (user: UserRead) => {
  updatingId.value = user.id
  try {
    const body: Record<string, unknown> = { is_active: !user.is_active }
    if (!user.is_active) body.rejection_reason = null
    const response = await patch<{ data: UserRead }>({ url: `/users/${user.id}`, body })
    replaceUser(response.data)
    toast.success(
      user.is_active
        ? t('admin.users.deactivated', { name: user.name ?? user.email })
        : t('admin.users.activated', { name: user.name ?? user.email }),
    )
    await loadUsers()
  } catch (error) {
    toastApiError(error)
  } finally {
    updatingId.value = null
  }
}

const openRejectDialog = (user: UserRead) => {
  rejectingUser.value = user
  showRejectDialog.value = true
}

const submitRejection = async (reason: string) => {
  if (!rejectingUser.value) return
  isRejecting.value = true
  try {
    const response = await patch<{ data: UserRead }>({
      url: `/users/${rejectingUser.value.id}`,
      body: { is_active: false, rejection_reason: reason || null },
    })
    replaceUser(response.data)
    toast.success(
      t('admin.users.rejectedToast', {
        name: rejectingUser.value.name ?? rejectingUser.value.email,
      }),
    )
    showRejectDialog.value = false
    await loadUsers()
  } catch (error) {
    toastApiError(error)
  } finally {
    isRejecting.value = false
  }
}

const openDeleteDialog = (user: UserRead) => {
  deletingUser.value = user
  showDeleteDialog.value = true
}

const submitDelete = async () => {
  if (!deletingUser.value) return
  isDeleting.value = true
  try {
    await del({ url: `/users/${deletingUser.value.id}` })
    toast.success(
      t('admin.users.deletedToast', {
        name: deletingUser.value.name ?? deletingUser.value.email,
      }),
    )
    showDeleteDialog.value = false
    await loadUsers()
  } catch (error) {
    toastApiError(error)
  } finally {
    isDeleting.value = false
  }
}

onMounted(loadUsers)
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-6">
    <div class="space-y-2">
      <h1 data-testid="page-heading" class="text-2xl sm:text-3xl font-bold">
        {{ t('admin.users.title') }}
      </h1>
      <p class="text-muted-foreground">{{ t('admin.users.subtitle') }}</p>
    </div>

    <UserStatsCards
      :total="counts.all"
      :active="counts.active"
      :pending="counts.pending"
      :rejected="counts.rejected"
    />

    <ApprovalPasswordCard />

    <div class="space-y-3 pt-4">
      <div class="flex items-baseline justify-between">
        <h2 class="text-lg font-semibold">
          {{ currentSectionLabel }}
        </h2>
        <span class="text-sm text-muted-foreground">{{ currentTotal }}</span>
      </div>

      <div class="relative">
        <Search
          class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
        />
        <Input
          v-model="searchInput"
          type="search"
          :placeholder="t('admin.users.searchPlaceholder')"
          class="pl-9 pr-9"
          data-testid="users-search"
        />
        <button
          v-if="searchInput"
          type="button"
          class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          :aria-label="t('common.actions.reset')"
          @click="clearSearch"
        >
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="flex flex-wrap gap-2">
        <Button
          v-for="option in statusOptions"
          :key="option.value"
          :variant="statusFilter === option.value ? 'default' : 'outline'"
          size="sm"
          @click="setStatus(option.value)"
        >
          {{ option.label }}
          <span class="ml-1.5 text-xs opacity-70">{{ option.count }}</span>
        </Button>
      </div>
    </div>

    <div v-if="loading && users.length === 0" class="py-12 text-center text-muted-foreground">
      {{ t('common.states.loading') }}
    </div>

    <template v-else>
      <UsersTable
        v-if="isDesktop"
        :users="users"
        :updating-id="updatingId"
        @toggle-active="toggleActive"
        @reject="openRejectDialog"
        @toggle-admin="toggleAdmin"
        @toggle-event-manager="toggleEventManager"
        @delete="openDeleteDialog"
      />
      <UsersGroupedList
        v-else
        :users="users"
        :updating-id="updatingId"
        @toggle-active="toggleActive"
        @reject="openRejectDialog"
        @toggle-admin="toggleAdmin"
        @toggle-event-manager="toggleEventManager"
        @delete="openDeleteDialog"
      />
    </template>

    <div v-if="totalPages > 1" class="flex justify-center">
      <Pagination
        v-model:page="currentPage"
        :total="currentTotal"
        :items-per-page="PAGE_SIZE"
        :sibling-count="1"
      >
        <PaginationContent>
          <PaginationFirst />
          <PaginationPrevious />
          <template v-for="(item, index) in totalPages" :key="index">
            <PaginationItem
              v-if="Math.abs(item - currentPage) <= 1 || item === 1 || item === totalPages"
              :value="item"
              :is-active="currentPage === item"
              as-child
            >
              <Button
                variant="outline"
                size="icon"
                class="h-9 w-9"
                :class="
                  currentPage === item
                    ? '!bg-primary !text-primary-foreground !border-primary'
                    : ''
                "
              >
                {{ item }}
              </Button>
            </PaginationItem>
            <PaginationEllipsis v-else-if="Math.abs(item - currentPage) === 2" />
          </template>
          <PaginationNext />
          <PaginationLast />
        </PaginationContent>
      </Pagination>
    </div>

    <RejectUserDialog
      v-model:open="showRejectDialog"
      :user="rejectingUser"
      :loading="isRejecting"
      @confirm="submitRejection"
    />

    <DeleteUserDialog
      v-model:open="showDeleteDialog"
      :user="deletingUser"
      :loading="isDeleting"
      @confirm="submitDelete"
    />
  </div>
</template>
