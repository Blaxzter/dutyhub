<script setup lang="ts">
import { computed } from 'vue'

import { ChevronDownIcon } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface Props {
  variant?: 'default' | 'ghost' | 'outline'
  size?: 'sm' | 'default' | 'lg'
  showText?: boolean
}

withDefaults(defineProps<Props>(), {
  variant: 'ghost',
  size: 'default',
  showText: true,
})

const { locale } = useI18n()
const authStore = useAuthStore()
const { patch } = useAuthenticatedClient()

const languages = [
  {
    code: 'en',
    name: 'English',
    flag: 'us',
    nativeName: 'English',
  },
  {
    code: 'de',
    name: 'German',
    flag: 'de',
    nativeName: 'Deutsch',
  },
]

const currentLanguage = computed(() => {
  return languages.find((lang) => lang.code === locale.value) || languages[0]
})

const changeLanguage = async (languageCode: string) => {
  locale.value = languageCode
  localStorage.setItem('locale', languageCode)

  // Sync to backend if logged in
  if (authStore.isAuthenticated && authStore.profile) {
    try {
      await patch({
        url: '/users/me',
        body: { preferred_language: languageCode },
      })
      if (authStore.profile) {
        authStore.profile.preferred_language = languageCode
      }
    } catch {
      // Non-critical: local preference is already set
    }
  }
}
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button :variant="variant" :size="size" class="gap-2">
        <span :class="`fi fi-${currentLanguage.flag}`" class="h-4 w-6 rounded-sm" />
        <span v-if="showText" class="hidden sm:inline">{{ currentLanguage.nativeName }}</span>
        <ChevronDownIcon class="h-3 w-3 opacity-50" />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" class="w-48">
      <DropdownMenuItem
        v-for="language in languages"
        :key="language.code"
        @click="changeLanguage(language.code)"
        :class="{ 'bg-accent': language.code === locale }"
        class="cursor-pointer gap-3"
      >
        <span :class="`fi fi-${language.flag}`" class="h-4 w-6 rounded-sm" />
        <div class="flex flex-col">
          <span class="font-medium">{{ language.nativeName }}</span>
          <span class="text-xs text-muted-foreground">{{ language.name }}</span>
        </div>
        <div v-if="language.code === locale" class="ml-auto">
          <div class="h-2 w-2 rounded-full bg-primary"></div>
        </div>
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
