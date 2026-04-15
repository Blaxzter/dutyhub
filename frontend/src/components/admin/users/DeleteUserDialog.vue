<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'
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

import type { UserRead } from '@/client/types.gen'

const props = defineProps<{
  open: boolean
  user: UserRead | null
  loading: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  confirm: []
}>()

const { t } = useI18n()
</script>

<template>
  <Dialog :open="props.open" @update:open="emit('update:open', $event)">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{{ t('admin.users.deleteDialogTitle') }}</DialogTitle>
        <DialogDescription>
          {{
            t('admin.users.deleteDialogDescription', {
              name: props.user?.name ?? props.user?.email,
            })
          }}
        </DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button variant="outline" @click="emit('update:open', false)">
          {{ t('common.actions.cancel') }}
        </Button>
        <Button variant="destructive" :disabled="props.loading" @click="emit('confirm')">
          <Loader2 v-if="props.loading" class="h-4 w-4 animate-spin" />
          {{ t('admin.users.delete') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
