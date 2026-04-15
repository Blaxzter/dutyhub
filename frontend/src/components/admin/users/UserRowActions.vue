<script setup lang="ts">
import {
  Ban,
  EllipsisVertical,
  Shield,
  ShieldCheck,
  ShieldOff,
  Trash2,
  UserCheck,
  UserX,
} from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import Button from '@/components/ui/button/Button.vue'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

import type { UserRead } from '@/client/types.gen'

const props = defineProps<{
  user: UserRead
  disabled: boolean
}>()

const emit = defineEmits<{
  toggleActive: [user: UserRead]
  reject: [user: UserRead]
  toggleAdmin: [user: UserRead]
  toggleEventManager: [user: UserRead]
  delete: [user: UserRead]
}>()

const { t } = useI18n()
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button variant="ghost" size="icon" class="h-8 w-8" :disabled="disabled">
        <EllipsisVertical class="h-4 w-4" />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end">
      <DropdownMenuItem @click="emit('toggleActive', props.user)">
        <UserX v-if="props.user.is_active" class="mr-2 h-4 w-4 text-destructive" />
        <UserCheck v-else class="mr-2 h-4 w-4" />
        {{ props.user.is_active ? t('admin.users.deactivate') : t('admin.users.activate') }}
      </DropdownMenuItem>
      <DropdownMenuItem v-if="!props.user.is_active" @click="emit('reject', props.user)">
        <Ban class="mr-2 h-4 w-4 text-destructive" />
        {{ t('admin.users.reject') }}
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem @click="emit('toggleAdmin', props.user)">
        <ShieldOff
          v-if="props.user.roles.includes('admin')"
          class="mr-2 h-4 w-4 text-destructive"
        />
        <Shield v-else class="mr-2 h-4 w-4" />
        {{
          props.user.roles.includes('admin')
            ? t('admin.users.removeAdmin')
            : t('admin.users.makeAdmin')
        }}
      </DropdownMenuItem>
      <DropdownMenuItem @click="emit('toggleEventManager', props.user)">
        <ShieldOff
          v-if="props.user.roles.includes('event_manager')"
          class="mr-2 h-4 w-4 text-amber-500"
        />
        <ShieldCheck v-else class="mr-2 h-4 w-4 text-amber-500" />
        {{
          props.user.roles.includes('event_manager')
            ? t('admin.users.removeEventManager')
            : t('admin.users.makeEventManager')
        }}
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem
        class="text-destructive focus:bg-destructive/10 focus:text-destructive dark:focus:bg-destructive/30"
        @click="emit('delete', props.user)"
      >
        <Trash2 class="mr-2 h-4 w-4 text-destructive" />
        {{ t('admin.users.delete') }}
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
