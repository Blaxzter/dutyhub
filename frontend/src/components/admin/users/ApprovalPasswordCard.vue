<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { Check, Eye, EyeOff, KeyRound, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import Button from '@/components/ui/button/Button.vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import Input from '@/components/ui/input/Input.vue'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

import { toastApiError } from '@/lib/api-errors'

const { t } = useI18n()
const { get, patch } = useAuthenticatedClient()

const hasApprovalPassword = ref(false)
const approvalPasswordInput = ref('')
const approvalPasswordLoading = ref(false)
const showClearPasswordDialog = ref(false)
const showPassword = ref(false)

const approvalPasswordDirty = computed(() => approvalPasswordInput.value.trim().length > 0)

const loadApprovalPassword = async () => {
  try {
    const response = await get<{ data: { has_approval_password: boolean } }>({
      url: '/settings/',
    })
    hasApprovalPassword.value = response.data.has_approval_password
  } catch (error) {
    toastApiError(error)
  }
}

const saveApprovalPassword = async () => {
  approvalPasswordLoading.value = true
  try {
    const password = approvalPasswordInput.value.trim() || null
    const response = await patch<{ data: { has_approval_password: boolean } }>({
      url: '/settings/',
      body: { approval_password: password },
    })
    hasApprovalPassword.value = response.data.has_approval_password
    if (password) {
      await navigator.clipboard.writeText(password)
    }
    approvalPasswordInput.value = ''
    showPassword.value = false
    toast.success(
      password
        ? t('admin.users.approvalPassword.savedAndCopied')
        : t('admin.users.approvalPassword.cleared'),
    )
  } catch (error) {
    toastApiError(error)
  } finally {
    approvalPasswordLoading.value = false
  }
}

const clearApprovalPassword = async () => {
  approvalPasswordInput.value = ''
  approvalPasswordLoading.value = true
  try {
    const response = await patch<{ data: { has_approval_password: boolean } }>({
      url: '/settings/',
      body: { approval_password: null },
    })
    hasApprovalPassword.value = response.data.has_approval_password
    showClearPasswordDialog.value = false
    toast.success(t('admin.users.approvalPassword.cleared'))
  } catch (error) {
    toastApiError(error)
  } finally {
    approvalPasswordLoading.value = false
  }
}

onMounted(loadApprovalPassword)
</script>

<template>
  <Card data-testid="section-approval-password">
    <CardHeader>
      <div class="flex flex-col items-center gap-2 sm:flex-row sm:items-center">
        <KeyRound class="h-5 w-5 shrink-0 text-muted-foreground" />
        <div class="w-full sm:w-auto">
          <CardTitle class="text-base">{{ t('admin.users.approvalPassword.title') }}</CardTitle>
          <CardDescription>{{ t('admin.users.approvalPassword.description') }}</CardDescription>
        </div>
      </div>
    </CardHeader>
    <CardContent>
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
        <Input
          v-model="approvalPasswordInput"
          :type="showPassword ? 'text' : 'password'"
          name="wirksam-approval-password"
          autocomplete="new-password"
          data-1p-ignore
          data-lpignore="true"
          data-bwignore
          :placeholder="
            hasApprovalPassword
              ? t('admin.users.approvalPassword.changePlaceholder')
              : t('admin.users.approvalPassword.placeholder')
          "
          class="w-full min-w-0 flex-1 sm:max-w-sm"
        />
        <div class="flex justify-end gap-2">
          <Button
            size="icon"
            variant="outline"
            :aria-label="showPassword ? t('common.actions.hide') : t('common.actions.show')"
            @click="showPassword = !showPassword"
          >
            <EyeOff v-if="showPassword" class="h-4 w-4" />
            <Eye v-else class="h-4 w-4" />
          </Button>
          <Button
            size="icon"
            variant="outline"
            :disabled="approvalPasswordLoading || !approvalPasswordDirty"
            @click="saveApprovalPassword"
          >
            <Check class="h-4 w-4" />
          </Button>
          <TooltipProvider v-if="hasApprovalPassword">
            <Tooltip>
              <TooltipTrigger as-child>
                <Button
                  size="icon"
                  variant="outline"
                  :disabled="approvalPasswordLoading"
                  @click="showClearPasswordDialog = true"
                >
                  <Trash2 class="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {{ t('admin.users.approvalPassword.clear') }}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>
    </CardContent>
  </Card>

  <Dialog v-model:open="showClearPasswordDialog">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{{ t('admin.users.approvalPassword.clearDialogTitle') }}</DialogTitle>
        <DialogDescription>
          {{ t('admin.users.approvalPassword.clearDialogDescription') }}
        </DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button variant="outline" @click="showClearPasswordDialog = false">
          {{ t('common.actions.cancel') }}
        </Button>
        <Button
          variant="destructive"
          :disabled="approvalPasswordLoading"
          @click="clearApprovalPassword"
        >
          {{ t('admin.users.approvalPassword.clear') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
