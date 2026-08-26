<template>
  <Card class="border-destructive/50">
    <CardHeader>
      <CardTitle class="flex items-center gap-2 text-destructive">
        <Trash2Icon class="h-5 w-5" />
        {{ $t('user.settings.deleteAccount.title') }}
      </CardTitle>
      <CardDescription>{{ $t('user.settings.deleteAccount.subtitle') }}</CardDescription>
    </CardHeader>
    <CardContent>
      <div class="space-y-4">
        <div class="p-4 bg-destructive/10 rounded-lg border border-destructive/20">
          <p class="text-sm text-destructive">
            {{ $t('user.settings.deleteAccount.warning') }}
          </p>
        </div>

        <ResponsiveDialog v-model:open="showConfirmDialog">
          <ResponsiveDialogTrigger as-child>
            <Button variant="destructive" size="sm" class="w-full sm:w-auto">
              <Trash2Icon class="h-4 w-4 mr-2" />
              {{ $t('user.settings.deleteAccount.button') }}
            </Button>
          </ResponsiveDialogTrigger>
          <ResponsiveDialogContent>
            <ResponsiveDialogHeader>
              <ResponsiveDialogTitle>{{
                $t('user.settings.deleteAccount.confirmTitle')
              }}</ResponsiveDialogTitle>
              <ResponsiveDialogDescription>
                {{ $t('user.settings.deleteAccount.confirmDescription') }}
              </ResponsiveDialogDescription>
            </ResponsiveDialogHeader>

            <ResponsiveDialogBody class="space-y-4 pb-2">
              <div>
                <label class="text-sm font-medium">
                  {{ $t('user.settings.deleteAccount.typeToConfirm', { confirmWord }) }}
                </label>
                <Input v-model="confirmText" :placeholder="confirmWord" class="mt-2" />
              </div>
            </ResponsiveDialogBody>

            <ResponsiveDialogFooter>
              <Button variant="outline" @click="showConfirmDialog = false">
                {{ $t('user.settings.deleteAccount.cancelButton') }}
              </Button>
              <Button
                variant="destructive"
                :disabled="confirmText !== confirmWord || isDeleting"
                @click="handleDeleteAccount"
              >
                {{
                  isDeleting
                    ? $t('user.settings.deleteAccount.deleting')
                    : $t('user.settings.deleteAccount.confirmButton')
                }}
              </Button>
            </ResponsiveDialogFooter>
          </ResponsiveDialogContent>
        </ResponsiveDialog>

        <!-- Error message -->
        <div
          v-if="errorMessage"
          class="p-4 rounded-lg bg-red-50 border border-red-200 text-red-800"
        >
          <p class="text-sm">{{ errorMessage }}</p>
        </div>
      </div>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import { Trash2Icon } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  ResponsiveDialog,
  ResponsiveDialogBody,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
  ResponsiveDialogTrigger,
} from '@/components/ui/responsive-dialog'

const authStore = useAuthStore()
const { t } = useI18n()
const { delete: del } = useAuthenticatedClient()

const confirmWord = computed(() => t('user.settings.deleteAccount.confirmWord'))
const showConfirmDialog = ref(false)
const confirmText = ref('')
const isDeleting = ref(false)
const errorMessage = ref<string | null>(null)

const handleDeleteAccount = async () => {
  if (confirmText.value !== confirmWord.value) return

  isDeleting.value = true
  errorMessage.value = null

  try {
    await del({ url: '/users/me' })

    // Account deleted — log out and redirect
    authStore.logout()
  } catch (error) {
    console.error('Account deletion error:', error)
    errorMessage.value = t('user.settings.deleteAccount.error')
    showConfirmDialog.value = false
  } finally {
    isDeleting.value = false
    confirmText.value = ''
  }
}
</script>
