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

import AuthShell from '@/components/auth/AuthShell.vue'
import PasswordRequirement from '@/components/auth/PasswordRequirement.vue'
import { Button } from '@/components/ui/button'
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

/**
 * Mirrors `BCRYPT_MAX_PASSWORD_BYTES` in `backend/app/schemas/auth.py`.
 *
 * Bytes, not characters: bcrypt hashes at most 72 of them and raises above
 * that, so the server answers 422. "ö" costs two, which is why a German
 * passphrase runs out a dozen characters before an English one — and why
 * counting `.length` here would let that 422 straight through.
 */
const PASSWORD_MAX_BYTES = 72

const byteLength = (value: string) => new TextEncoder().encode(value).length

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const { register } = useAuth()

const busy = ref(false)
const showPassword = ref(false)
const formRef = ref<HTMLFormElement | null>(null)

/** Same-origin paths only — see the note in `LoginView.vue`. */
const redirectTarget = computed<RouteLocationRaw>(() => {
  const target = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  const isSameOrigin =
    target.startsWith('/') && !target.startsWith('//') && !target.startsWith('/\\')
  return isSameOrigin ? target : { name: 'home' }
})

/**
 * The generated schema, minus the field this form does not ask for, plus the
 * two rules the generated one cannot carry and one field the endpoint never
 * sees.
 *
 * `preferred_language` is dropped rather than hidden, for a mundane reason:
 * `@vee-validate/zod` reads Zod 3's `_def.defaultValue()` when it collects a
 * schema's defaults, and in Zod 4 that is a plain value — so a single
 * `.default()` anywhere in the shape throws `_def.defaultValue is not a
 * function` inside `useForm`, before the form ever renders. The value is set
 * from the live locale at submit time instead, which is what we want anyway.
 *
 * The `.min()` message is deliberately *not* supplied here: it comes from the
 * global map in `lib/zod-i18n.ts`, which is what stops it from being the same
 * sentence as the requirement line under the field.
 */
const registerSchema = computed(() => {
  void locale.value
  return toTypedSchema(
    zRegisterRequest
      .omit({ preferred_language: true })
      .extend({
        password: z
          .string()
          .min(PASSWORD_MIN_LENGTH)
          .refine((value) => byteLength(value) <= PASSWORD_MAX_BYTES, {
            error: () => t('auth.password.maxBytes'),
          }),
        // UI only. `RegisterRequest` has no such field, and the submit handler
        // names the three it does send — an extra key would earn a 422.
        confirm_password: z.string(),
      })
      .refine((values) => values.password === values.confirm_password, {
        error: () => t('auth.password.mismatch'),
        path: ['confirm_password'],
      }),
  )
})

const { errors, values, handleSubmit } = useForm({
  validationSchema: registerSchema,
  initialValues: { email: '', password: '', name: '', confirm_password: '' },
})

const passwordLongEnough = computed(
  () => String(values.password ?? '').length >= PASSWORD_MIN_LENGTH,
)

/** See the note on the same helper in `LoginView.vue`. */
const liveValidate = (field: 'email' | 'password' | 'name' | 'confirm_password') =>
  Boolean(errors.value[field])

/**
 * Send the cursor to the first field that is actually wrong.
 *
 * Somebody submitting from the keyboard has to be told *where* the problem is,
 * not just that there is one. Walked in DOM order rather than over
 * `Object.keys(errors)`, whose order comes from the generated schema and does
 * not have to match the order the fields are laid out in — on the register form
 * it lists `email` before `name`, and the cursor would skip the first field on
 * the screen. Scoped to this form, so nothing else on the page can steal focus.
 */
function focusFirstInvalid(form: HTMLFormElement | null, invalid: Record<string, unknown>): void {
  if (!form) return
  const fields = Array.from(form.querySelectorAll<HTMLElement>('[name]'))
  const first = fields.find((field) => invalid[field.getAttribute('name') ?? ''])
  first?.focus()
}

const onSubmit = handleSubmit(
  async (formValues) => {
    busy.value = true
    try {
      await register({
        email: formValues.email,
        password: formValues.password,
        name: formValues.name,
        // The language the form was filled in, not the browser's: it decides
        // which of the two verification mails is sent, and it seeds the
        // account's notification language for everything afterwards.
        preferred_language: locale.value,
      })
      toast.success(t('auth.register.success'))
      toast.info(t('auth.register.verificationSent', { email: formValues.email }))
      await router.replace(redirectTarget.value)
    } catch (error) {
      toastApiError(error)
    } finally {
      busy.value = false
    }
  },
  ({ errors: invalid }) => {
    focusFirstInvalid(formRef.value, invalid)
  },
)
</script>

<template>
  <AuthShell
    hero="register"
    :icon="UserPlusIcon"
    :title="t('auth.register.title')"
    :description="t('auth.register.description')"
  >
    <form ref="formRef" class="space-y-4" data-testid="register-form" @submit="onSubmit">
      <FormField
        v-slot="{ componentField }"
        name="name"
        :validate-on-model-update="liveValidate('name')"
      >
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

      <FormField
        v-slot="{ componentField, errorMessage }"
        name="email"
        :validate-on-model-update="liveValidate('email')"
      >
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
          <!-- The hint steps aside for the error rather than stacking above it. -->
          <FormDescription v-if="!errorMessage">
            {{ t('auth.register.fields.email.description') }}
          </FormDescription>
          <FormMessage />
        </FormItem>
      </FormField>

      <FormField
        v-slot="{ componentField, errorMessage }"
        name="password"
        :validate-on-model-update="liveValidate('password')"
      >
        <FormItem>
          <FormLabel>{{ t('auth.register.fields.password.label') }}</FormLabel>
          <div class="relative">
            <FormControl>
              <Input
                :type="showPassword ? 'text' : 'password'"
                autocomplete="new-password"
                class="pr-11"
                data-testid="input-password"
                :placeholder="t('auth.register.fields.password.placeholder')"
                v-bind="componentField"
              />
            </FormControl>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              class="absolute top-1/2 right-1 size-7 -translate-y-1/2 rounded-sm text-muted-foreground hover:bg-transparent hover:text-foreground focus-visible:ring-2"
              data-testid="btn-toggle-password"
              :aria-label="
                showPassword ? t('common.actions.hidePassword') : t('common.actions.showPassword')
              "
              @click="showPassword = !showPassword"
            >
              <EyeOffIcon v-if="showPassword" class="size-4" />
              <EyeIcon v-else class="size-4" />
            </Button>
          </div>
          <!--
            The rule, the tick and the error in one row, and deliberately no
            <FormMessage /> beside it: the two used to render the same sentence
            twice, once as a hint and once as a complaint. It never leaves the
            DOM, so `aria-describedby` always resolves, and `aria-live`
            announces the swap for anyone who cannot see the colour change.
          -->
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

      <FormField
        v-slot="{ componentField }"
        name="confirm_password"
        :validate-on-model-update="liveValidate('confirm_password')"
      >
        <FormItem>
          <FormLabel>{{ t('auth.register.fields.confirmPassword.label') }}</FormLabel>
          <FormControl>
            <!-- `new-password` on both fields, not a `confirm-` token that does
                 not exist: it is what tells a password manager these two are a
                 set-a-password pair and to fill both with the same value. -->
            <Input
              :type="showPassword ? 'text' : 'password'"
              autocomplete="new-password"
              data-testid="input-confirm-password"
              :placeholder="t('auth.register.fields.confirmPassword.placeholder')"
              v-bind="componentField"
            />
          </FormControl>
          <FormMessage />
        </FormItem>
      </FormField>

      <Button class="w-full" type="submit" :disabled="busy" data-testid="btn-register">
        <LoaderIcon v-if="busy" class="size-4 animate-spin" />
        {{ busy ? t('auth.register.actions.submitting') : t('auth.register.actions.submit') }}
      </Button>
    </form>

    <template #footer>
      {{ t('auth.register.loginPrompt.text') }}
      <RouterLink
        class="font-medium text-primary underline-offset-4 hover:underline"
        data-testid="link-login"
        :to="{ name: 'login' }"
      >
        {{ t('auth.register.loginPrompt.action') }}
      </RouterLink>
    </template>
  </AuthShell>
</template>
