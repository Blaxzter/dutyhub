<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { useSandboxStore } from '@/stores/sandbox'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

import { SANDBOX_ENDED_KEY } from '@/lib/auth-session'

/**
 * The explanation owed to somebody whose demo was swept away under them.
 *
 * The demo dies server-side on a timer, so the first the browser hears of it is
 * a refresh that comes back 401 — mid-click, on whatever page they were on.
 * `lib/auth-session.ts` leaves a note in `sessionStorage` on the way past; this
 * reads it once, on the landing page they were dropped onto, and turns a
 * baffling sign-out into an offer.
 */

const emit = defineEmits<{ startAnother: [] }>()

const { t } = useI18n()
const router = useRouter()
const sandboxStore = useSandboxStore()

const open = ref(false)

onMounted(() => {
  try {
    if (sessionStorage.getItem(SANDBOX_ENDED_KEY) === null) return
    // Removed as soon as it is read, not when the dialog closes: this is a
    // one-time explanation, and a note left behind would reappear on the next
    // visit to the landing page in this tab as if the demo had ended twice.
    sessionStorage.removeItem(SANDBOX_ENDED_KEY)
    open.value = true
  } catch {
    // A browser that blocks site data throws here. No note, no dialog — the
    // landing page is still perfectly usable.
  }
})

function startAnother() {
  open.value = false
  emit('startAnother')
}

function createAccount() {
  open.value = false
  void router.push({ name: 'register' })
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent data-testid="dialog-sandbox-expired" class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ t('sandbox.expired.title') }}</DialogTitle>
        <DialogDescription class="text-left">
          {{ t('sandbox.expired.message') }}
        </DialogDescription>
      </DialogHeader>

      <DialogFooter>
        <Button
          v-if="sandboxStore.enabled"
          variant="outline"
          data-testid="btn-sandbox-restart"
          @click="startAnother"
        >
          {{ t('sandbox.expired.startAnother') }}
        </Button>
        <Button data-testid="btn-sandbox-register" @click="createAccount">
          {{ t('sandbox.expired.createAccount') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
