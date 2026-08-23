<script setup lang="ts">
/**
 * Sign in with an email address and a password.
 *
 * The whole screen is one card under `NoLayout`: someone who is being asked for
 * a password should not also be offered a navigation bar full of places to go
 * instead. The only ways out are the two links below the form — one to recover
 * a forgotten password, one to create an account.
 */
import { computed, ref } from 'vue'

import { EyeIcon, EyeOffIcon, LoaderIcon, LogInIcon } from '@lucide/vue'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { useI18n } from 'vue-i18n'
import type { RouteLocationRaw } from 'vue-router'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { useAuth } from '@/composables/useAuth'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader } from '@/components/ui/card'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'

import { zLoginRequest } from '@/client/zod.gen'
import { toastApiError } from '@/lib/api-errors'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { login } = useAuth()

const busy = ref(false)
const showPassword = ref(false)

/**
 * Where to land once signed in.
 *
 * `?redirect=` is written by the route guard, but it arrives through the URL
 * bar like any other query — so only a same-origin path is honoured. An
 * absolute URL there would make this screen an open redirect for anybody who
 * can get a link clicked, and the phishing version of that link is a real
 * sign-in page that hands the visitor onwards to a fake one.
 */
const redirectTarget = computed<RouteLocationRaw>(() => {
  const target = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  const isSameOrigin =
    target.startsWith('/') && !target.startsWith('//') && !target.startsWith('/\\')
  return isSameOrigin ? target : { name: 'home' }
})

const form = useForm({
  validationSchema: toTypedSchema(zLoginRequest),
  initialValues: { email: '', password: '' },
})

const onSubmit = form.handleSubmit(async (values) => {
  busy.value = true
  try {
    await login(values)
    toast.success(t('auth.login.success'))
    // Replace rather than push: the back button should return to wherever the
    // visitor came from, not to a sign-in form they have already used.
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
    <Card class="w-full max-w-md" data-testid="login-card">
      <CardHeader class="space-y-3 text-center">
        <LogInIcon class="mx-auto h-10 w-10 text-primary" />
        <h1 class="text-xl leading-none font-semibold" data-testid="page-heading">
          {{ t('auth.login.title') }}
        </h1>
        <CardDescription>{{ t('auth.login.description') }}</CardDescription>
      </CardHeader>

      <CardContent class="space-y-4">
        <form class="space-y-4" data-testid="login-form" @submit="onSubmit">
          <FormField v-slot="{ componentField }" name="email">
            <FormItem>
              <FormLabel>{{ t('auth.login.fields.email.label') }}</FormLabel>
              <FormControl>
                <Input
                  type="email"
                  autocomplete="email"
                  data-testid="input-email"
                  :placeholder="t('auth.login.fields.email.placeholder')"
                  v-bind="componentField"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>

          <FormField v-slot="{ componentField }" name="password">
            <FormItem>
              <FormLabel>{{ t('auth.login.fields.password.label') }}</FormLabel>
              <div class="relative">
                <FormControl>
                  <Input
                    :type="showPassword ? 'text' : 'password'"
                    autocomplete="current-password"
                    class="pr-10"
                    data-testid="input-password"
                    :placeholder="t('auth.login.fields.password.placeholder')"
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
              <FormMessage />
            </FormItem>
          </FormField>

          <Button class="w-full" type="submit" :disabled="busy" data-testid="btn-login">
            <LoaderIcon v-if="busy" class="h-4 w-4 animate-spin" />
            {{ busy ? t('auth.login.actions.submitting') : t('auth.login.actions.submit') }}
          </Button>
        </form>

        <div class="text-center">
          <RouterLink
            class="text-sm text-muted-foreground underline-offset-4 hover:underline"
            data-testid="link-forgot-password"
            :to="{ name: 'forgot-password' }"
          >
            {{ t('auth.login.actions.forgotPassword') }}
          </RouterLink>
        </div>

        <p class="text-center text-sm text-muted-foreground">
          {{ t('auth.login.registerPrompt.text') }}
          <RouterLink
            class="font-medium text-primary underline-offset-4 hover:underline"
            data-testid="link-register"
            :to="{ name: 'register' }"
          >
            {{ t('auth.login.registerPrompt.action') }}
          </RouterLink>
        </p>
      </CardContent>
    </Card>
  </div>
</template>
