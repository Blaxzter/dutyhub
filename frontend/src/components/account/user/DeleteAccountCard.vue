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

        <Dialog v-model:open="showConfirmDialog">
          <DialogTrigger as-child>
            <Button variant="destructive" size="sm" class="w-full sm:w-auto">
              <Trash2Icon class="h-4 w-4 mr-2" />
              {{ $t('user.settings.deleteAccount.button') }}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{{ $t('user.settings.deleteAccount.confirmTitle') }}</DialogTitle>
              <DialogDescription>
                {{ $t('user.settings.deleteAccount.confirmDescription') }}
              </DialogDescription>
            </DialogHeader>

            <div class="space-y-4 py-4">
              <div>
                <label class="text-sm font-medium">
                  {{ $t('user.settings.deleteAccount.typeToConfirm', { confirmWord }) }}
                </label>
                <Input v-model="confirmText" :placeholder="confirmWord" class="mt-2" />
              </div>
            </div>

            <DialogFooter>
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
            </DialogFooter>
          </DialogContent>
        </Dialog>

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

import { Trash2Icon } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'

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
