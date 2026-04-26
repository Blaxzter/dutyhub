<template>
  <div class="flex items-start gap-4">
    <Avatar class="h-20 w-20">
      <AvatarImage v-if="avatarUrl" :src="avatarUrl" :alt="altText" />
      <AvatarFallback class="text-lg">{{ initials }}</AvatarFallback>
    </Avatar>
    <div class="flex flex-1 flex-col gap-2">
      <Label>{{ $t('user.settings.profile.edit.fields.picture.label') }}</Label>
      <p class="text-sm text-muted-foreground">
        {{ $t('user.settings.profile.edit.fields.picture.description') }}
      </p>
      <div class="flex flex-wrap gap-2">
        <input
          ref="fileInput"
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          class="hidden"
          @change="onFileSelected"
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="isUploading"
          @click="fileInput?.click()"
        >
          <UploadIcon v-if="!isUploading" class="mr-2 h-4 w-4" />
          <LoaderIcon v-else class="mr-2 h-4 w-4 animate-spin" />
          {{
            isUploading
              ? $t('user.settings.profile.edit.fields.picture.uploading')
              : $t('user.settings.profile.edit.fields.picture.upload')
          }}
        </Button>
        <Button
          v-if="hasAvatar"
          type="button"
          variant="ghost"
          size="sm"
          :disabled="isUploading || isRemoving"
          @click="removeAvatar"
        >
          <Trash2Icon v-if="!isRemoving" class="mr-2 h-4 w-4" />
          <LoaderIcon v-else class="mr-2 h-4 w-4 animate-spin" />
          {{ $t('user.settings.profile.edit.fields.picture.remove') }}
        </Button>
      </div>
    </div>
  </div>

  <AvatarCropperDialog
    :open="cropperOpen"
    :file="cropperFile"
    @confirm="onCropConfirm"
    @cancel="closeCropper"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import { LoaderIcon, Trash2Icon, UploadIcon } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'
import { useAvatarUrl } from '@/composables/useAvatarUrl'

import { useAuthStore } from '@/stores/auth'

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'

import AvatarCropperDialog from './AvatarCropperDialog.vue'

import { toastApiError } from '@/lib/api-errors'

const { t } = useI18n()
const { getAuthToken } = useAuthenticatedClient()
const authStore = useAuthStore()

const isUploading = ref(false)
const isRemoving = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const cropperOpen = ref(false)
const cropperFile = ref<File | null>(null)

const avatarUrl = useAvatarUrl(() => authStore.profile)
const hasAvatar = computed(() => !!authStore.profile?.avatar_etag)

const altText = computed(
  () => authStore.profile?.name || authStore.profile?.email || '',
)

const initials = computed(() => {
  const name = authStore.profile?.name
  const email = authStore.profile?.email
  if (name) {
    return name
      .split(' ')
      .map((n: string) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }
  if (email) return email[0].toUpperCase()
  return 'U'
})

// For animated formats (GIF), extract the first frame so the cropper sees a
// static image instead of whichever frame is rendered when the user confirms.
// createImageBitmap is spec'd to return only the first frame.
const flattenAnimated = async (file: File): Promise<File> => {
  if (file.type !== 'image/gif') return file
  const bitmap = await createImageBitmap(file)
  try {
    const canvas = document.createElement('canvas')
    canvas.width = bitmap.width
    canvas.height = bitmap.height
    const ctx = canvas.getContext('2d')
    if (!ctx) return file
    ctx.drawImage(bitmap, 0, 0)
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/png'),
    )
    if (!blob) return file
    return new File([blob], file.name.replace(/\.gif$/i, '.png'), {
      type: 'image/png',
    })
  } finally {
    bitmap.close()
  }
}

const onFileSelected = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  try {
    cropperFile.value = await flattenAnimated(file)
  } catch {
    cropperFile.value = file
  }
  cropperOpen.value = true
}

const closeCropper = () => {
  cropperOpen.value = false
  cropperFile.value = null
  if (fileInput.value) fileInput.value.value = ''
}

const onCropConfirm = async (blob: Blob) => {
  cropperOpen.value = false
  isUploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', blob, 'avatar.png')
    const token = await getAuthToken()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/users/me/avatar`, {
      method: 'PUT',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new Error(detail?.detail || `Upload failed: ${response.status}`)
    }
    await authStore.loadProfile()
    toast.success(t('user.settings.profile.edit.fields.picture.uploadSuccess'))
  } catch (error) {
    console.error('Avatar upload failed:', error)
    toastApiError(error)
  } finally {
    isUploading.value = false
    cropperFile.value = null
    if (fileInput.value) fileInput.value.value = ''
  }
}

const removeAvatar = async () => {
  isRemoving.value = true
  try {
    const token = await getAuthToken()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/users/me/avatar`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok && response.status !== 204) {
      throw new Error(`Delete failed: ${response.status}`)
    }
    await authStore.loadProfile()
    toast.success(t('user.settings.profile.edit.fields.picture.removeSuccess'))
  } catch (error) {
    console.error('Avatar delete failed:', error)
    toastApiError(error)
  } finally {
    isRemoving.value = false
  }
}
</script>
