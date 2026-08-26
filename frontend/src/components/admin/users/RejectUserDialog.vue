<script setup lang="ts">
import { ref, watch } from 'vue'

import { useI18n } from 'vue-i18n'

import Button from '@/components/ui/button/Button.vue'
import {
  ResponsiveDialog,
  ResponsiveDialogBody,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from '@/components/ui/responsive-dialog'
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
  <ResponsiveDialog :open="props.open" @update:open="emit('update:open', $event)">
    <ResponsiveDialogContent>
      <ResponsiveDialogHeader>
        <ResponsiveDialogTitle>{{ t('admin.users.rejectDialogTitle') }}</ResponsiveDialogTitle>
        <ResponsiveDialogDescription>
          {{
            t('admin.users.rejectDialogDescription', {
              name: props.user?.name ?? props.user?.email,
            })
          }}
        </ResponsiveDialogDescription>
      </ResponsiveDialogHeader>
      <ResponsiveDialogBody class="pb-2">
        <Textarea
          v-model="reason"
          :placeholder="t('admin.users.rejectReasonPlaceholder')"
          rows="3"
        />
      </ResponsiveDialogBody>
      <ResponsiveDialogFooter>
        <Button variant="outline" @click="emit('update:open', false)">
          {{ t('common.actions.cancel') }}
        </Button>
        <Button variant="destructive" :disabled="props.loading" @click="emit('confirm', reason)">
          {{ t('admin.users.reject') }}
        </Button>
      </ResponsiveDialogFooter>
    </ResponsiveDialogContent>
  </ResponsiveDialog>
</template>
