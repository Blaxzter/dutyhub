<script setup lang="ts">
import { UserIcon } from '@lucide/vue'

import { useAuthStore } from '@/stores/auth'

import { useAvatarUrl } from '@/composables/useAvatarUrl'

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'

defineEmits<{
  navigate: []
}>()

const authStore = useAuthStore()
const avatarUrl = useAvatarUrl(() => authStore.profile)
</script>

<template>
  <button
    type="button"
    class="flex cursor-pointer items-center gap-3 rounded p-1 hover:bg-muted"
    @click="$emit('navigate')"
  >
    <Avatar class="size-8">
      <AvatarImage
        v-if="avatarUrl"
        :src="avatarUrl"
        :alt="authStore.user?.name || authStore.user?.email || 'User'"
      />
      <AvatarFallback>
        <UserIcon class="size-4" />
      </AvatarFallback>
    </Avatar>

    <!-- Avatar-only on small screens: the pre-auth header now carries the
         language, theme and sign-in controls inline at every width, and the
         name plus caption is more than the remaining room allows. -->
    <span class="hidden flex-col text-left sm:flex">
      <span class="text-sm font-medium">{{ authStore.user?.name || authStore.user?.email }}</span>
      <span class="text-xs text-muted-foreground">
        {{ $t('preauth.layout.navigation.goToDashboard') }}
      </span>
    </span>
  </button>
</template>
