<script setup lang="ts">
/**
 * Ask for a password-reset link.
 *
 * The endpoint answers 202 whether or not the address belongs to anybody, and
 * this screen has to keep that promise: there is exactly one confirmation, it
 * is worded so that it says nothing either way, and it is shown for every
 * address that was typed. A "no such account" message here would turn the form
 * into a membership oracle — type an address, learn whether that person uses
 * the service.
 */
import { ref } from 'vue'

import { KeyRoundIcon, LoaderIcon, MailCheckIcon } from '@lucide/vue'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { useI18n } from 'vue-i18n'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader } from '@/components/ui/card'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'

import { client } from '@/client/client.gen'
import { zForgotPasswordRequest } from '@/client/zod.gen'
import { toastApiError } from '@/lib/api-errors'

const { t } = useI18n()

const busy = ref(false)
/** The address the confirmation is about — never a claim that it was found. */
const submittedEmail = ref<string | null>(null)

const form = useForm({
  validationSchema: toTypedSchema(zForgotPasswordRequest),
  initialValues: { email: '' },
})

const onSubmit = form.handleSubmit(async (values) => {
  busy.value = true
  try {
    // A public endpoint: no bearer token to attach, so this goes straight to the
    // generated client rather than through `useAuthenticatedClient`, which would
    // throw for the anonymous visitor this page exists for.
    await client.post<unknown, unknown, true>({
      url: '/auth/forgot-password',
      body: values,
      throwOnError: true,
    })
    submittedEmail.value = values.email
  } catch (error) {
    // Reached by a rate limit or an outage — never by "no such address".
    toastApiError(error)
  } finally {
    busy.value = false
  }
})

function startOver() {
  submittedEmail.value = null
  form.resetForm()
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center p-4">
    <Card class="w-full max-w-md" data-testid="forgot-password-card">
      <template v-if="submittedEmail">
        <CardHeader class="space-y-3 text-center">
          <MailCheckIcon class="mx-auto h-10 w-10 text-primary" />
          <h1 class="text-xl leading-none font-semibold" data-testid="page-heading">
            {{ t('auth.forgotPassword.sent.title') }}
          </h1>
          <CardDescription data-testid="forgot-password-sent">
            {{ t('auth.forgotPassword.sent.description', { email: submittedEmail }) }}
          </CardDescription>
        </CardHeader>

        <CardContent class="space-y-4">
          <p class="text-center text-sm text-muted-foreground">
            {{ t('auth.forgotPassword.sent.hint') }}
          </p>
          <Button
            class="w-full"
            variant="outline"
            data-testid="btn-forgot-password-retry"
            @click="startOver"
          >
            {{ t('auth.forgotPassword.sent.retry') }}
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
          <KeyRoundIcon class="mx-auto h-10 w-10 text-primary" />
          <h1 class="text-xl leading-none font-semibold" data-testid="page-heading">
            {{ t('auth.forgotPassword.title') }}
          </h1>
          <CardDescription>{{ t('auth.forgotPassword.description') }}</CardDescription>
        </CardHeader>

        <CardContent class="space-y-4">
          <form class="space-y-4" data-testid="forgot-password-form" @submit="onSubmit">
            <FormField v-slot="{ componentField }" name="email">
              <FormItem>
                <FormLabel>{{ t('auth.forgotPassword.fields.email.label') }}</FormLabel>
                <FormControl>
                  <Input
                    type="email"
                    autocomplete="email"
                    data-testid="input-email"
                    :placeholder="t('auth.forgotPassword.fields.email.placeholder')"
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
              data-testid="btn-forgot-password-submit"
            >
              <LoaderIcon v-if="busy" class="h-4 w-4 animate-spin" />
              {{
                busy
                  ? t('auth.forgotPassword.actions.submitting')
                  : t('auth.forgotPassword.actions.submit')
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
