<script setup lang="ts">
/**
 * Shown when an account is suspended.
 *
 * Signup is open, so nobody waits for approval any more — but `is_active`
 * survives as a moderation switch, and someone who has been suspended still
 * needs to be told rather than left staring at a home page where every request
 * comes back 403.
 */
import { computed, ref } from 'vue'

import { Ban, LogOut } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import Button from '@/components/ui/button/Button.vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'

import LanguageSwitch from '@/components/utils/LanguageSwitch.vue'

const { t } = useI18n()
const authStore = useAuthStore()
const { delete: del } = useAuthenticatedClient()

const reason = computed(() => authStore.profile?.rejection_reason)

const showDeleteDialog = ref(false)
const isDeleting = ref(false)
const errorMessage = ref<string | null>(null)

const handleDeleteAccount = async () => {
  isDeleting.value = true
  errorMessage.value = null
  try {
    await del({ url: '/users/me' })
    authStore.logout()
  } catch (error) {
    console.error('Account deletion error:', error)
    errorMessage.value = t('common.accountSuspended.deleteError')
    showDeleteDialog.value = false
  } finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <div class="flex items-center justify-center">
    <div class="mx-auto max-w-md text-center">
      <div class="mb-6 flex justify-center">
        <div class="rounded-full bg-destructive/10 p-4">
          <Ban class="h-12 w-12 text-destructive" />
        </div>
      </div>

      <h1 data-testid="page-heading" class="text-2xl font-bold sm:text-3xl">
        {{ t('common.accountSuspended.title') }}
      </h1>
      <p class="mt-3 text-muted-foreground">
        {{ t('common.accountSuspended.description') }}
      </p>

      <div
        v-if="reason"
        class="mt-4 rounded-lg border border-destructive bg-destructive/10 p-4 text-left"
        data-testid="suspension-reason"
      >
        <p class="mb-1 text-xs font-medium text-destructive-foreground">
          {{ t('common.accountSuspended.reasonLabel') }}
        </p>
        <p class="text-sm text-destructive-foreground">{{ reason }}</p>
      </div>

      <div class="mt-8 flex items-center justify-center gap-3">
        <Button data-testid="btn-logout" variant="outline" @click="authStore.logout()">
          {{ t('common.accountSuspended.logout') }}
          <LogOut class="ml-2 h-4 w-4" />
        </Button>

        <LanguageSwitch variant="outline" size="default" :show-text="false" />
      </div>

      <div
        v-if="errorMessage"
        class="mt-4 rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive-foreground"
      >
        {{ errorMessage }}
      </div>

      <Dialog v-model:open="showDeleteDialog">
        <DialogTrigger as-child>
          <button
            data-testid="btn-delete-account"
            class="mt-6 text-xs text-muted-foreground underline-offset-4 transition-colors hover:text-destructive hover:underline"
          >
            {{ t('common.accountSuspended.deleteAccount') }}
          </button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{{ t('common.accountSuspended.deleteConfirmTitle') }}</DialogTitle>
            <DialogDescription>
              {{ t('common.accountSuspended.deleteConfirmDescription') }}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" @click="showDeleteDialog = false">
              {{ t('common.accountSuspended.cancel') }}
            </Button>
            <Button variant="destructive" :disabled="isDeleting" @click="handleDeleteAccount">
              {{
                isDeleting
                  ? t('common.accountSuspended.deleting')
                  : t('common.accountSuspended.confirmDelete')
              }}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  </div>
</template>
