<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { ClipboardListIcon, HandHeartIcon, Loader2 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'
import { type SandboxRole, useSandboxStore } from '@/stores/sandbox'

import { Button } from '@/components/ui/button'
import {
  ResponsiveDialog,
  ResponsiveDialogBody,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from '@/components/ui/responsive-dialog'

/**
 * The one decision a visitor makes before the demo opens: which side of the
 * app they want to see.
 *
 * It is a decision worth asking about rather than guessing at, because the two
 * answers show almost disjoint screens — a helper never opens the shift
 * planner, an organiser rarely books themselves in. Guessing wrong means the
 * demo opens on a page that does not answer the question the visitor came with.
 */

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [value: boolean] }>()

const { t } = useI18n()
const authStore = useAuthStore()
const sandboxStore = useSandboxStore()

const ROLES = [
  { value: 'helper', icon: HandHeartIcon, testid: 'btn-sandbox-role-helper' },
  { value: 'manager', icon: ClipboardListIcon, testid: 'btn-sandbox-role-manager' },
] as const

const selected = ref<SandboxRole>('helper')

/**
 * Starting a demo replaces whatever session is open, so somebody who is
 * already signed in has to be told before they press the button — not after
 * they find themselves looking at an account that is not theirs.
 */
const warnsAboutSignOut = computed(() => authStore.isAuthenticated)

// Reopening should not resume the last visit's half-made choice.
watch(
  () => props.open,
  (open) => {
    if (open) selected.value = 'helper'
  },
)

async function start() {
  const entered = await sandboxStore.start(selected.value)
  // Only on success: a refusal (demo switched off, all slots taken) has already
  // put a toast on screen, and closing the dialog under it would leave the
  // visitor on the landing page with no way back to the button they just used.
  if (entered) emit('update:open', false)
}
</script>

<template>
  <ResponsiveDialog :open="props.open" @update:open="emit('update:open', $event)">
    <ResponsiveDialogContent data-testid="dialog-sandbox-start" dialog-class="sm:max-w-lg">
      <ResponsiveDialogHeader>
        <ResponsiveDialogTitle>{{ t('sandbox.startDialog.title') }}</ResponsiveDialogTitle>
        <ResponsiveDialogDescription class="text-left">
          {{ t('sandbox.startDialog.intro') }}
        </ResponsiveDialogDescription>
      </ResponsiveDialogHeader>

      <ResponsiveDialogBody class="pb-2">
        <fieldset class="space-y-3">
          <legend class="pb-2 text-sm font-medium">{{ t('sandbox.startDialog.question') }}</legend>

          <button
            v-for="role in ROLES"
            :key="role.value"
            type="button"
            :data-testid="role.testid"
            :aria-pressed="selected === role.value"
            class="flex w-full items-start gap-3 rounded-lg border p-4 text-left transition-colors hover:bg-muted/50"
            :class="selected === role.value ? 'border-primary bg-primary/5' : ''"
            @click="selected = role.value"
          >
            <component :is="role.icon" class="mt-0.5 size-5 shrink-0 text-primary" />
            <span class="min-w-0">
              <span class="block text-sm font-medium">
                {{ t(`sandbox.startDialog.${role.value}.title`) }}
              </span>
              <span class="mt-1 block text-sm text-muted-foreground">
                {{ t(`sandbox.startDialog.${role.value}.description`) }}
              </span>
            </span>
          </button>
        </fieldset>

        <p
          v-if="warnsAboutSignOut"
          data-testid="sandbox-signout-warning"
          class="mt-3 rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-sm"
        >
          {{ t('sandbox.startDialog.signedInWarning') }}
        </p>
      </ResponsiveDialogBody>

      <ResponsiveDialogFooter>
        <Button
          variant="outline"
          :disabled="sandboxStore.starting"
          @click="emit('update:open', false)"
        >
          {{ t('sandbox.startDialog.cancel') }}
        </Button>
        <Button data-testid="btn-sandbox-start" :disabled="sandboxStore.starting" @click="start">
          <Loader2 v-if="sandboxStore.starting" class="size-4 animate-spin" />
          {{
            sandboxStore.starting
              ? t('sandbox.startDialog.starting')
              : t('sandbox.startDialog.start')
          }}
        </Button>
      </ResponsiveDialogFooter>
    </ResponsiveDialogContent>
  </ResponsiveDialog>
</template>
