<script setup lang="ts">
/**
 * Create an account.
 *
 * Registration signs you straight in — the response carries an access token, so
 * there is no "now go and confirm your address" wall in the way. The
 * verification mail is a nudge, announced as a toast on the way out rather than
 * as a gate; an unverified account can already do everything, it just cannot be
 * reached by email yet.
 */
import { computed, ref } from 'vue'

import { EyeIcon, EyeOffIcon, LoaderIcon, UserPlusIcon } from '@lucide/vue'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { useI18n } from 'vue-i18n'
import type { RouteLocationRaw } from 'vue-router'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { z } from 'zod'

import { useAuth } from '@/composables/useAuth'

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

import { zRegisterRequest } from '@/client/zod.gen'
import { toastApiError } from '@/lib/api-errors'

/**
 * Mirrors `settings.PASSWORD_MIN_LENGTH` on the server.
 *
 * The generated schema cannot carry it — the backend enforces the length in a
 * field validator, which never reaches the OpenAPI document. Duplicating the
 * number here buys an answer before the round trip; the server still has the
 * last word and answers `auth.weak_password` if the two ever drift apart.
 */
const PASSWORD_MIN_LENGTH = 8

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const { register } = useAuth()

const busy = ref(false)
const showPassword = ref(false)

/** Same-origin paths only — see the note in `LoginView.vue`. */
const redirectTarget = computed<RouteLocationRaw>(() => {
  const target = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  const isSameOrigin =
    target.startsWith('/') && !target.startsWith('//') && !target.startsWith('/\\')
  return isSameOrigin ? target : { name: 'home' }
})

/**
 * The generated schema, minus the field this form does not ask for and plus the
 * length rule the generated one cannot carry.
 *
 * `preferred_language` is dropped rather than hidden, for a mundane reason:
 * `@vee-validate/zod` reads Zod 3's `_def.defaultValue()` when it collects a
 * schema's defaults, and in Zod 4 that is a plain value — so a single
 * `.default()` anywhere in the shape throws `_def.defaultValue is not a
 * function` inside `useForm`, before the form ever renders. The value is set
 * from the live locale at submit time instead, which is what we want anyway.
 */
const registerSchema = computed(() =>
  toTypedSchema(
    zRegisterRequest.omit({ preferred_language: true }).extend({
      password: z
        .string()
        .min(PASSWORD_MIN_LENGTH, t('auth.password.minLength', { min: PASSWORD_MIN_LENGTH })),
    }),
  ),
)

const form = useForm({
  validationSchema: registerSchema,
  initialValues: { email: '', password: '', name: '' },
})

const onSubmit = form.handleSubmit(async (values) => {
  busy.value = true
  try {
    await register({
      email: values.email,
      password: values.password,
      name: values.name,
      // The language the form was filled in, not the browser's: it decides which
      // of the two verification mails is sent, and it seeds the account's
      // notification language for everything afterwards.
      preferred_language: locale.value,
    })
    toast.success(t('auth.register.success'))
    toast.info(t('auth.register.verificationSent', { email: values.email }))
    await router.replace(redirectTarget.value)
  } catch (error) {
    toastApiError(error)
  } finally {
    busy.value = false
  }
})
</script>

<template>
  <div class="flex min-h-screen items-center justify-center p-4">
    <Card class="w-full max-w-md" data-testid="register-card">
      <CardHeader class="space-y-3 text-center">
        <UserPlusIcon class="mx-auto h-10 w-10 text-primary" />
        <h1 class="text-xl leading-none font-semibold" data-testid="page-heading">
          {{ t('auth.register.title') }}
        </h1>
        <CardDescription>{{ t('auth.register.description') }}</CardDescription>
      </CardHeader>

      <CardContent class="space-y-4">
        <form class="space-y-4" data-testid="register-form" @submit="onSubmit">
          <FormField v-slot="{ componentField }" name="name">
            <FormItem>
              <FormLabel>{{ t('auth.register.fields.name.label') }}</FormLabel>
              <FormControl>
                <Input
                  type="text"
                  autocomplete="name"
                  data-testid="input-name"
                  :placeholder="t('auth.register.fields.name.placeholder')"
                  v-bind="componentField"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>

          <FormField v-slot="{ componentField }" name="email">
            <FormItem>
              <FormLabel>{{ t('auth.register.fields.email.label') }}</FormLabel>
              <FormControl>
                <Input
                  type="email"
                  autocomplete="email"
                  data-testid="input-email"
                  :placeholder="t('auth.register.fields.email.placeholder')"
                  v-bind="componentField"
                />
              </FormControl>
              <FormDescription>
                {{ t('auth.register.fields.email.description') }}
              </FormDescription>
              <FormMessage />
            </FormItem>
          </FormField>

          <FormField v-slot="{ componentField }" name="password">
            <FormItem>
              <FormLabel>{{ t('auth.register.fields.password.label') }}</FormLabel>
              <div class="relative">
                <FormControl>
                  <Input
                    :type="showPassword ? 'text' : 'password'"
                    autocomplete="new-password"
                    class="pr-10"
                    data-testid="input-password"
                    :placeholder="t('auth.register.fields.password.placeholder')"
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

          <Button class="w-full" type="submit" :disabled="busy" data-testid="btn-register">
            <LoaderIcon v-if="busy" class="h-4 w-4 animate-spin" />
            {{ busy ? t('auth.register.actions.submitting') : t('auth.register.actions.submit') }}
          </Button>
        </form>

        <p class="text-center text-sm text-muted-foreground">
          {{ t('auth.register.loginPrompt.text') }}
          <RouterLink
            class="font-medium text-primary underline-offset-4 hover:underline"
            data-testid="link-login"
            :to="{ name: 'login' }"
          >
            {{ t('auth.register.loginPrompt.action') }}
          </RouterLink>
        </p>
      </CardContent>
    </Card>
  </div>
</template>
