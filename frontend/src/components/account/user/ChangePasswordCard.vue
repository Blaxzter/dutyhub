<script setup lang="ts">
/**
 * Change the password of the signed-in account.
 *
 * The current password is asked for even though the caller is already signed
 * in: it is the one thing standing between a borrowed, unlocked browser and a
 * permanent takeover, and the server insists on it regardless.
 *
 * Saving also signs every *other* device out. That is the server's doing, not
 * ours, but it is the part people need told — so the confirmation stays on
 * screen as a panel rather than passing by as a toast. Failures go the other
 * way and use the house `toastApiError`, which turns `auth.invalid_credentials`
 * and friends into translated sentences.
 */
import { computed, ref } from 'vue'

import { CircleCheckIcon, EyeIcon, EyeOffIcon, KeyRoundIcon, LoaderIcon } from '@lucide/vue'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { useI18n } from 'vue-i18n'
import { z } from 'zod'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import PasswordRequirement from '@/components/auth/PasswordRequirement.vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'

import { zChangePasswordRequest } from '@/client/zod.gen'
import { toastApiError } from '@/lib/api-errors'

/** Mirrors `settings.PASSWORD_MIN_LENGTH`; see the note in `RegisterView.vue`. */
const PASSWORD_MIN_LENGTH = 8

const { t } = useI18n()
const { post } = useAuthenticatedClient()

const busy = ref(false)
const showCurrent = ref(false)
const showNew = ref(false)
/** True from a successful save until the next attempt starts. */
const saved = ref(false)

// Rebuilt against `t` so the messages follow a language switch instead of
// freezing in whatever locale the settings page happened to open in.
const changePasswordSchema = computed(() =>
  toTypedSchema(
    zChangePasswordRequest
      .extend({
        current_password: z
          .string()
          .min(1, t('user.settings.password.fields.currentPassword.required')),
        // Message comes from the global map in `lib/zod-i18n.ts`. Supplying one
        // here is what used to make the error and the hint below the field the
        // very same sentence, printed twice.
        new_password: z.string().min(PASSWORD_MIN_LENGTH),
        // UI-only: the server has no use for it and never sees it.
        confirm_password: z.string(),
      })
      // Saving the password you already have signs your other devices out for
      // nothing, so it is caught here — the server is happy to allow it. Skipped
      // on an empty field so the length message gets to speak first.
      .refine((values) => !values.new_password || values.new_password !== values.current_password, {
        message: t('user.settings.password.fields.newPassword.unchanged'),
        path: ['new_password'],
      })
      .refine((values) => values.new_password === values.confirm_password, {
        message: t('user.settings.password.fields.confirmPassword.mismatch'),
        path: ['confirm_password'],
      }),
  ),
)

const form = useForm({
  validationSchema: changePasswordSchema,
  initialValues: { current_password: '', new_password: '', confirm_password: '' },
})

const passwordLongEnough = computed(
  () => String(form.values.new_password ?? '').length >= PASSWORD_MIN_LENGTH,
)

const onSubmit = form.handleSubmit(async (values) => {
  busy.value = true
  saved.value = false
  try {
    await post<void>({
      url: '/auth/change-password',
      body: { current_password: values.current_password, new_password: values.new_password },
    })
    saved.value = true
    // Nothing here is worth keeping in the fields, and a filled-in password form
    // left behind on a settings page is an invitation.
    form.resetForm()
  } catch (error) {
    toastApiError(error)
  } finally {
    busy.value = false
  }
})
</script>

<template>
  <Card data-testid="change-password-card">
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <KeyRoundIcon class="h-5 w-5" />
        {{ t('user.settings.password.title') }}
      </CardTitle>
      <CardDescription>{{ t('user.settings.password.subtitle') }}</CardDescription>
    </CardHeader>
    <CardContent class="space-y-4">
      <div
        v-if="saved"
        class="flex items-start gap-3 rounded-lg border bg-muted p-4"
        data-testid="change-password-success"
      >
        <CircleCheckIcon class="mt-0.5 h-5 w-5 shrink-0 text-primary" />
        <div class="space-y-1">
          <h4 class="text-sm font-medium">{{ t('user.settings.password.success.title') }}</h4>
          <p class="text-sm text-muted-foreground">
            {{ t('user.settings.password.success.description') }}
          </p>
        </div>
      </div>

      <form class="space-y-4" data-testid="change-password-form" @submit="onSubmit">
        <FormField v-slot="{ componentField }" name="current_password">
          <FormItem>
            <FormLabel>{{ t('user.settings.password.fields.currentPassword.label') }}</FormLabel>
            <div class="relative">
              <FormControl>
                <Input
                  :type="showCurrent ? 'text' : 'password'"
                  autocomplete="current-password"
                  class="pr-10"
                  data-testid="input-current-password"
                  :placeholder="t('user.settings.password.fields.currentPassword.placeholder')"
                  v-bind="componentField"
                />
              </FormControl>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                class="absolute top-0 right-0"
                data-testid="btn-toggle-current-password"
                :aria-label="
                  showCurrent ? t('common.actions.hidePassword') : t('common.actions.showPassword')
                "
                @click="showCurrent = !showCurrent"
              >
                <EyeOffIcon v-if="showCurrent" class="h-4 w-4" />
                <EyeIcon v-else class="h-4 w-4" />
              </Button>
            </div>
            <FormMessage />
          </FormItem>
        </FormField>

        <FormField v-slot="{ componentField, errorMessage }" name="new_password">
          <FormItem>
            <FormLabel>{{ t('user.settings.password.fields.newPassword.label') }}</FormLabel>
            <div class="relative">
              <FormControl>
                <Input
                  :type="showNew ? 'text' : 'password'"
                  autocomplete="new-password"
                  class="pr-10"
                  data-testid="input-new-password"
                  :placeholder="t('user.settings.password.fields.newPassword.placeholder')"
                  v-bind="componentField"
                />
              </FormControl>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                class="absolute top-0 right-0"
                data-testid="btn-toggle-new-password"
                :aria-label="
                  showNew ? t('common.actions.hidePassword') : t('common.actions.showPassword')
                "
                @click="showNew = !showNew"
              >
                <EyeOffIcon v-if="showNew" class="h-4 w-4" />
                <EyeIcon v-else class="h-4 w-4" />
              </Button>
            </div>
            <!-- The rule, the tick and the error in one row. See `RegisterView`. -->
            <FormDescription aria-live="polite">
              <PasswordRequirement
                :label="t('auth.password.requirement.unmet', { min: PASSWORD_MIN_LENGTH })"
                :met-label="t('auth.password.requirement.met')"
                :met="passwordLongEnough"
                :message="errorMessage"
              />
            </FormDescription>
          </FormItem>
        </FormField>

        <FormField v-slot="{ componentField }" name="confirm_password">
          <FormItem>
            <FormLabel>{{ t('user.settings.password.fields.confirmPassword.label') }}</FormLabel>
            <FormControl>
              <Input
                :type="showNew ? 'text' : 'password'"
                autocomplete="new-password"
                data-testid="input-confirm-password"
                :placeholder="t('user.settings.password.fields.confirmPassword.placeholder')"
                v-bind="componentField"
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        </FormField>

        <Button
          type="submit"
          :disabled="busy"
          class="w-full sm:w-auto"
          data-testid="btn-change-password-submit"
        >
          <LoaderIcon v-if="busy" class="h-4 w-4 animate-spin" />
          <KeyRoundIcon v-else class="h-4 w-4" />
          {{
            busy
              ? t('user.settings.password.actions.submitting')
              : t('user.settings.password.actions.submit')
          }}
        </Button>
      </form>
    </CardContent>
  </Card>
</template>
