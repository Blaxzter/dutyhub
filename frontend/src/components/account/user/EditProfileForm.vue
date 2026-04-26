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
      <div class="mb-6">
        <AvatarPicker />
      </div>

      <form @submit="onSubmit" class="space-y-6">
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
import { toTypedSchema } from '@vee-validate/zod'
import { EditIcon, LoaderIcon, SaveIcon } from 'lucide-vue-next'
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

import AvatarPicker from './AvatarPicker.vue'

import type { UserProfileUpdate } from '@/client/types.gen'
import { zUserProfileUpdate } from '@/client/zod.gen'

interface Props {
  user: User | undefined
}

interface Emits {
  (e: 'profile-updated', values: UserProfileUpdate): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()
const { t } = useI18n()

const { patch } = useAuthenticatedClient()

const isSubmitting = ref(false)

const profileSchema = toTypedSchema(zUserProfileUpdate)

const form = useForm({
  validationSchema: profileSchema,
  initialValues: {
    name: '',
    nickname: '',
    bio: '',
    phone_number: '',
  },
})

onMounted(() => {
  if (props.user) {
    const userRecord = props.user as Record<string, string>
    form.setValues({
      name: props.user.name || '',
      nickname: props.user.nickname || '',
      bio: userRecord.bio || '',
      phone_number: userRecord.phone_number || '',
    })
  }
})

const onSubmit = form.handleSubmit(async (values) => {
  if (!props.user) {
    toast.error(t('user.settings.profile.edit.authError'))
    return
  }

  isSubmitting.value = true
  try {
    const updateData: UserProfileUpdate = {
      name: values.name,
      nickname: values.nickname,
      bio: values.bio,
      phone_number: values.phone_number || undefined,
    }
    await patch({ url: '/users/me', body: updateData })
    toast.success(t('user.settings.profile.edit.success'))
    emit('profile-updated', values)
  } catch (error) {
    console.error('Error updating profile:', error)
    toast.error(t('user.settings.profile.edit.error'))
  } finally {
    isSubmitting.value = false
  }
})

const resetForm = () => {
  if (props.user) {
    const userRecord = props.user as Record<string, string>
    form.setValues({
      name: props.user.name || '',
      nickname: props.user.nickname || '',
      bio: userRecord.bio || '',
      phone_number: userRecord.phone_number || '',
    })
  }
}
</script>
