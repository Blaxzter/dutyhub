<script setup lang="ts">
import { computed } from 'vue'

import { useColorMode } from '@vueuse/core'
import { LogOut, Moon, Sun } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import wirksamDarkLogo from '@/assets/logo/wirksam-dark.svg'
import wirksamLightLogo from '@/assets/logo/wirksam-light.svg'

import { useAuthStore } from '@/stores/auth'

import Button from '@/components/ui/button/Button.vue'

import LanguageSwitch from '@/components/utils/LanguageSwitch.vue'

const { t } = useI18n()
const authStore = useAuthStore()
const mode = useColorMode()

const topBarLogo = computed(() => (mode.value === 'light' ? wirksamDarkLogo : wirksamLightLogo))
</script>

<template>
  <header class="flex items-center justify-between gap-3 px-4 py-4 sm:px-8">
    <img :src="topBarLogo" alt="WirkSam" class="h-7 w-auto lg:invisible" />
    <div class="flex items-center gap-1">
      <Button
        variant="ghost"
        size="icon"
        :title="
          mode === 'dark'
            ? t('navigation.user.actions.switchToLight')
            : t('navigation.user.actions.switchToDark')
        "
        @click="mode = mode === 'dark' ? 'light' : 'dark'"
      >
        <Sun v-if="mode === 'dark'" class="h-4 w-4" />
        <Moon v-else class="h-4 w-4" />
      </Button>
      <LanguageSwitch variant="ghost" size="sm" :show-text="false" />
      <Button
        variant="ghost"
        size="sm"
        data-testid="btn-logout"
        :title="t('navigation.user.actions.logout')"
        @click="authStore.logout"
      >
        <LogOut class="h-4 w-4" />
      </Button>
    </div>
  </header>
</template>
