<script setup lang="ts">
import { ref, watch } from 'vue'

import { useI18n } from 'vue-i18n'

import Button from '@/components/ui/button/Button.vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import Textarea from '@/components/ui/textarea/Textarea.vue'

import type { UserRead } from '@/client/types.gen'

const props = defineProps<{
  open: boolean
  user: UserRead | null
  loading: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  confirm: [reason: string]
}>()

const { t } = useI18n()
const reason = ref('')

watch(
  () => props.open,
  (open) => {
    if (open) reason.value = ''
  },
)
</script>

<template>
  <Dialog :open="props.open" @update:open="emit('update:open', $event)">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{{ t('admin.users.rejectDialogTitle') }}</DialogTitle>
        <DialogDescription>
          {{
            t('admin.users.rejectDialogDescription', {
              name: props.user?.name ?? props.user?.email,
            })
          }}
        </DialogDescription>
      </DialogHeader>
      <Textarea v-model="reason" :placeholder="t('admin.users.rejectReasonPlaceholder')" rows="3" />
      <DialogFooter>
        <Button variant="outline" @click="emit('update:open', false)">
          {{ t('common.actions.cancel') }}
        </Button>
        <Button variant="destructive" :disabled="props.loading" @click="emit('confirm', reason)">
          {{ t('admin.users.reject') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
