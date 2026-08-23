<script setup lang="ts">
/**
 * Redeem a reset link and choose a new password.
 *
 * The secret arrives as `?token=` and never leaves this component except in the
 * request body — it is not put in a route param, where it would end up in the
 * breadcrumb trail, nor kept after the flow finishes.
 *
 * A link that has expired, been used, or been mangled by a mail client is a
 * dead end, and it is treated as one: the form is replaced outright by a panel
 * that says so and offers the one thing that helps, a fresh link. Leaving the
 * form up would only collect a password that cannot be saved.
 */
import { computed, ref } from 'vue'

import { EyeIcon, EyeOffIcon, LoaderIcon, LockKeyholeIcon, TriangleAlertIcon } from '@lucide/vue'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader } from '@/components/ui/card'
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'

import { client } from '@/client/client.gen'
import { zResetPasswordRequest } from '@/client/zod.gen'
import { normalizeApiError, toastApiError } from '@/lib/api-errors'

/** Mirrors `settings.PASSWORD_MIN_LENGTH`; see the note in `RegisterView.vue`. */
const PASSWORD_MIN_LENGTH = 8

/** The two problem codes that mean "this link is over", whatever the reason. */
const DEAD_LINK_CODES = new Set(['auth.invalid_token', 'auth.token_expired'])

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const token = typeof route.query.token === 'string' ? route.query.token : ''

const busy = ref(false)
const showPassword = ref(false)
/** True once the link is known to be unusable — either on arrival or on submit. */
const linkIsDead = ref(token === '')

const resetSchema = computed(() =>
  toTypedSchema(
    zResetPasswordRequest
      .extend({
        password: z
          .string()
          .min(PASSWORD_MIN_LENGTH, t('auth.password.minLength', { min: PASSWORD_MIN_LENGTH })),
        confirm_password: z.string(),
      })
      .refine((values) => values.password === values.confirm_password, {
        message: t('auth.resetPassword.fields.confirmPassword.mismatch'),
        path: ['confirm_password'],
      }),
  ),
)

const form = useForm({
  validationSchema: resetSchema,
  // The token rides along as an ordinary form value so the generated schema
  // validates it with everything else, but it has no field of its own.
  initialValues: { token, password: '', confirm_password: '' },
})

const onSubmit = form.handleSubmit(async (values) => {
  busy.value = true
  try {
    // Public endpoint, and `confirm_password` is a UI-only field — send exactly
    // what the schema on the other side expects.
    await client.post<unknown, unknown, true>({
      url: '/auth/reset-password',
      body: { token: values.token, password: values.password },
      throwOnError: true,
    })
    toast.success(t('auth.resetPassword.success'))
    await router.replace({ name: 'login' })
  } catch (error) {
    const normalized = normalizeApiError(error)
    if (normalized.code && DEAD_LINK_CODES.has(normalized.code)) {
      linkIsDead.value = true
      return
    }
    toastApiError(error)
  } finally {
    busy.value = false
  }
})
</script>

<template>
  <div class="flex min-h-screen items-center justify-center p-4">
    <Card class="w-full max-w-md" data-testid="reset-password-card">
      <template v-if="linkIsDead">
        <CardHeader class="space-y-3 text-center">
          <TriangleAlertIcon class="mx-auto h-10 w-10 text-destructive" />
          <h1 class="text-xl leading-none font-semibold" data-testid="page-heading">
            {{ t('auth.resetPassword.invalid.title') }}
          </h1>
          <CardDescription data-testid="reset-password-invalid">
            {{ t('auth.resetPassword.invalid.description') }}
          </CardDescription>
        </CardHeader>

        <CardContent class="space-y-4">
          <Button class="w-full" as-child data-testid="link-request-new">
            <RouterLink :to="{ name: 'forgot-password' }">
              {{ t('auth.resetPassword.actions.requestNew') }}
            </RouterLink>
          </Button>
          <Button class="w-full" variant="ghost" as-child data-testid="link-back-to-login">
            <RouterLink :to="{ name: 'login' }">
              {{ t('auth.forgotPassword.actions.backToLogin') }}
            </RouterLink>
          </Button>
        </CardContent>
      </template>

      <template v-else>
        <CardHeader class="space-y-3 text-center">
          <LockKeyholeIcon class="mx-auto h-10 w-10 text-primary" />
          <h1 class="text-xl leading-none font-semibold" data-testid="page-heading">
            {{ t('auth.resetPassword.title') }}
          </h1>
          <CardDescription>{{ t('auth.resetPassword.description') }}</CardDescription>
        </CardHeader>

        <CardContent class="space-y-4">
          <form class="space-y-4" data-testid="reset-password-form" @submit="onSubmit">
            <FormField v-slot="{ componentField }" name="password">
              <FormItem>
                <FormLabel>{{ t('auth.resetPassword.fields.password.label') }}</FormLabel>
                <div class="relative">
                  <FormControl>
                    <Input
                      :type="showPassword ? 'text' : 'password'"
                      autocomplete="new-password"
                      class="pr-10"
                      data-testid="input-password"
                      :placeholder="t('auth.resetPassword.fields.password.placeholder')"
                      v-bind="componentField"
                    />
                  </FormControl>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    class="absolute top-0 right-0"
                    data-testid="btn-toggle-password"
                    :aria-label="
                      showPassword
                        ? t('common.actions.hidePassword')
                        : t('common.actions.showPassword')
                    "
                    @click="showPassword = !showPassword"
                  >
                    <EyeOffIcon v-if="showPassword" class="h-4 w-4" />
                    <EyeIcon v-else class="h-4 w-4" />
                  </Button>
                </div>
                <FormDescription>
                  {{ t('auth.password.minLength', { min: PASSWORD_MIN_LENGTH }) }}
                </FormDescription>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="confirm_password">
              <FormItem>
                <FormLabel>{{ t('auth.resetPassword.fields.confirmPassword.label') }}</FormLabel>
                <FormControl>
                  <Input
                    :type="showPassword ? 'text' : 'password'"
                    autocomplete="new-password"
                    data-testid="input-confirm-password"
                    :placeholder="t('auth.resetPassword.fields.confirmPassword.placeholder')"
                    v-bind="componentField"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <Button
              class="w-full"
              type="submit"
              :disabled="busy"
              data-testid="btn-reset-password-submit"
            >
              <LoaderIcon v-if="busy" class="h-4 w-4 animate-spin" />
              {{
                busy
                  ? t('auth.resetPassword.actions.submitting')
                  : t('auth.resetPassword.actions.submit')
              }}
            </Button>
          </form>

          <Button class="w-full" variant="ghost" as-child data-testid="link-back-to-login">
            <RouterLink :to="{ name: 'login' }">
              {{ t('auth.forgotPassword.actions.backToLogin') }}
            </RouterLink>
          </Button>
        </CardContent>
      </template>
    </Card>
  </div>
</template>
