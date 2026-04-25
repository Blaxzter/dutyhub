<template>
  <Card>
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <EditIcon class="h-5 w-5" />
        {{ $t('user.settings.profile.edit.title') }}
      </CardTitle>
      <CardDescription>
        {{ $t('user.settings.profile.edit.subtitle') }}
      </CardDescription>
    </CardHeader>
    <CardContent>
      <form @submit="onSubmit" class="space-y-6">
        <!-- Name Field -->
        <FormField v-slot="{ componentField }" name="name">
          <FormItem>
            <FormLabel>{{ $t('user.settings.profile.edit.fields.displayName.label') }}</FormLabel>
            <FormControl>
              <Input
                type="text"
                :placeholder="$t('user.settings.profile.edit.fields.displayName.placeholder')"
                v-bind="componentField"
              />
            </FormControl>
            <FormDescription>{{
              $t('user.settings.profile.edit.fields.displayName.description')
            }}</FormDescription>
            <FormMessage />
          </FormItem>
        </FormField>

        <!-- Nickname Field -->
        <FormField v-slot="{ componentField }" name="nickname">
          <FormItem>
            <FormLabel>{{ $t('user.settings.profile.edit.fields.nickname.label') }}</FormLabel>
            <FormControl>
              <Input
                type="text"
                :placeholder="$t('user.settings.profile.edit.fields.nickname.placeholder')"
                v-bind="componentField"
              />
            </FormControl>
            <FormDescription>{{
              $t('user.settings.profile.edit.fields.nickname.description')
            }}</FormDescription>
            <FormMessage />
          </FormItem>
        </FormField>

        <!-- Picture URL Field -->
        <FormField v-if="canEditProfilePicture" v-slot="{ componentField }" name="picture">
          <FormItem>
            <FormLabel>{{ $t('user.settings.profile.edit.fields.picture.label') }}</FormLabel>
            <FormControl>
              <Input
                type="url"
                :placeholder="$t('user.settings.profile.edit.fields.picture.placeholder')"
                v-bind="componentField"
              />
            </FormControl>
            <FormDescription>
              {{ $t('user.settings.profile.edit.fields.picture.description') }}
            </FormDescription>
            <FormMessage />
          </FormItem>
        </FormField>

        <!-- Phone Number Field -->
        <FormField v-slot="{ componentField }" name="phone_number">
          <FormItem>
            <FormLabel>{{ $t('user.settings.profile.edit.fields.phoneNumber.label') }}</FormLabel>
            <FormControl>
              <Input
                type="tel"
                :placeholder="$t('user.settings.profile.edit.fields.phoneNumber.placeholder')"
                v-bind="componentField"
              />
            </FormControl>
            <FormDescription>{{
              $t('user.settings.profile.edit.fields.phoneNumber.description')
            }}</FormDescription>
            <FormMessage />
          </FormItem>
        </FormField>

        <!-- Bio/Description Field -->
        <FormField v-slot="{ componentField }" name="bio">
          <FormItem>
            <FormLabel>{{ $t('user.settings.profile.edit.fields.bio.label') }}</FormLabel>
            <FormControl>
              <Textarea
                :placeholder="$t('user.settings.profile.edit.fields.bio.placeholder')"
                class="min-h-[100px]"
                v-bind="componentField"
              />
            </FormControl>
            <FormDescription>
              {{ $t('user.settings.profile.edit.fields.bio.description') }}
            </FormDescription>
            <FormMessage />
          </FormItem>
        </FormField>

        <!-- Provider Limitation Notice -->
        <div v-if="!canEditProfilePicture" class="p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p class="text-sm text-blue-700">
            <InfoIcon class="h-4 w-4 inline mr-1" />
            {{
              $t('user.settings.profile.edit.providerLimitation', { provider: authProviderName })
            }}
          </p>
        </div>

        <!-- Form Actions -->
        <div class="flex items-center gap-4 pt-4">
          <Button type="submit" :disabled="isSubmitting" class="flex items-center gap-2">
            <LoaderIcon v-if="isSubmitting" class="h-4 w-4 animate-spin" />
            <SaveIcon v-else class="h-4 w-4" />
            {{
              isSubmitting
                ? $t('user.settings.profile.edit.actions.updating')
                : $t('user.settings.profile.edit.actions.update')
            }}
          </Button>
          <Button type="button" variant="outline" @click="resetForm" :disabled="isSubmitting">
            {{ $t('user.settings.profile.edit.actions.reset') }}
          </Button>
        </div>
      </form>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import type { User } from '@auth0/auth0-vue'
import { Loader as LoaderIcon } from '@respeak/lucide-motion-vue'
import { toTypedSchema } from '@vee-validate/zod'
import { EditIcon, InfoIcon, SaveIcon } from 'lucide-vue-next'
import { useForm } from 'vee-validate'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

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
import { Textarea } from '@/components/ui/textarea'

import type { UserProfileUpdate } from '@/client/types.gen'
import { zUserProfileUpdate } from '@/client/zod.gen'

interface Props {
  user: User | undefined
  canEditProfilePicture: boolean
  authProviderName: string
}

interface Emits {
  (e: 'profile-updated', values: UserProfileUpdate): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()
const { t } = useI18n()

// Validation schema
const profileSchema = toTypedSchema(zUserProfileUpdate)

// Composables
const { patch } = useAuthenticatedClient()

// Reactive data
const isSubmitting = ref(false)

// Form setup
const form = useForm({
  validationSchema: profileSchema,
  initialValues: {
    name: '',
    nickname: '',
    picture: '',
    bio: '',
    phone_number: '',
  },
})

// Initialize form with current user data
onMounted(() => {
  if (props.user) {
    const userRecord = props.user as Record<string, string>
    const formValues: Record<string, string> = {
      name: props.user.name || '',
      nickname: props.user.nickname || '',
      bio: userRecord.bio || '',
      phone_number: userRecord.phone_number || '',
    }

    // Only include picture if it can be edited
    if (props.canEditProfilePicture) {
      formValues.picture = props.user.picture || ''
    }

    form.setValues(formValues)
  }
})

// Form submission
const onSubmit = form.handleSubmit(async (values) => {
  if (!props.user) {
    showError(t('user.settings.profile.edit.authError'))
    return
  }

  isSubmitting.value = true
  try {
    await updateUserProfile(values)
    showSuccess()
    emit('profile-updated', values)
  } catch (error) {
    console.error('Error updating profile:', error)
    showError(t('user.settings.profile.edit.error'))
  } finally {
    isSubmitting.value = false
  }
})

// Update user profile via API
const updateUserProfile = async (values: UserProfileUpdate) => {
  try {
    const updateData: UserProfileUpdate = {
      name: values.name,
      nickname: values.nickname,
      bio: values.bio,
      phone_number: values.phone_number || undefined,
    }

    // Only include picture if it can be edited
    if (props.canEditProfilePicture && values.picture !== undefined) {
      updateData.picture = values.picture || undefined
    }

    await patch({
      url: '/users/me',
      body: updateData,
    })
  } catch (error) {
    console.error('API Error:', error)
    throw error
  }
}

// Reset form to current user values
const resetForm = () => {
  if (props.user) {
    const userRecord = props.user as Record<string, string>
    const formValues: Record<string, string> = {
      name: props.user.name || '',
      nickname: props.user.nickname || '',
      bio: userRecord.bio || '',
      phone_number: userRecord.phone_number || '',
    }

    // Only include picture if it can be edited
    if (props.canEditProfilePicture) {
      formValues.picture = props.user.picture || ''
    }

    form.setValues(formValues)
  }
}

// Toast functions
const showSuccess = () => {
  toast.success(t('user.settings.profile.edit.success'))
}

const showError = (message: string) => {
  toast.error(message)
}
</script>
