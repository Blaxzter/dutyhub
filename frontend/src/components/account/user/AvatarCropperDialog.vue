<template>
  <Dialog :open="open" @update:open="handleOpenChange">
    <DialogContent class="sm:max-w-xl" @open-auto-focus="(e) => e.preventDefault()">
      <DialogHeader>
        <DialogTitle>{{ $t('user.settings.profile.edit.fields.picture.cropper.title') }}</DialogTitle>
        <DialogDescription>
          {{ $t('user.settings.profile.edit.fields.picture.cropper.description') }}
        </DialogDescription>
      </DialogHeader>

      <div class="min-w-0 space-y-3">
        <div
          ref="containerRef"
          class="relative overflow-hidden rounded-md border bg-muted/40"
          style="height: 360px"
        >
          <Cropper
            v-if="imageSrc"
            :key="imageSrc"
            ref="cropperRef"
            class="h-full w-full"
            :src="imageSrc"
            :stencil-component="RectangleStencil"
            :stencil-props="{ aspectRatio: 1, movable: true, resizable: true }"
            :default-size="defaultSize"
            default-boundaries="fit"
            image-restriction="fit-area"
            :background="true"
            @ready="onReady"
          />
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="!ready"
            @click="rotate(-90)"
          >
            <RotateCcwIcon class="mr-1.5 h-4 w-4" />
            {{ $t('user.settings.profile.edit.fields.picture.cropper.rotateLeft') }}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="!ready"
            @click="rotate(90)"
          >
            <RotateCwIcon class="mr-1.5 h-4 w-4" />
            {{ $t('user.settings.profile.edit.fields.picture.cropper.rotateRight') }}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            :disabled="!ready"
            @click="reset"
          >
            {{ $t('user.settings.profile.edit.fields.picture.cropper.reset') }}
          </Button>
        </div>
      </div>

      <DialogFooter>
        <Button type="button" variant="outline" :disabled="confirming" @click="cancel">
          {{ $t('common.actions.cancel') }}
        </Button>
        <Button type="button" :disabled="!ready || confirming" @click="confirm">
          <LoaderIcon v-if="confirming" class="mr-2 h-4 w-4 animate-spin" />
          {{ $t('user.settings.profile.edit.fields.picture.cropper.confirm') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

import { useResizeObserver } from '@vueuse/core'
import { LoaderIcon, RotateCcwIcon, RotateCwIcon } from 'lucide-vue-next'
import { Cropper, RectangleStencil } from 'vue-advanced-cropper'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

import 'vue-advanced-cropper/dist/style.css'

interface Props {
  open: boolean
  file: File | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  confirm: [blob: Blob]
  cancel: []
}>()

// `Cropper` doesn't ship strict types for its instance methods we use here.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const cropperRef = ref<any>(null)
const containerRef = ref<HTMLElement | null>(null)
const imageSrc = ref<string | null>(null)
const ready = ref(false)
const confirming = ref(false)

// Re-measure on container resize as a cheap safety net (window resize, devtools
// toggle, etc.). Not load-bearing — `min-w-0` on the grid item is what keeps
// the cropper at the correct width even when mounted during the dialog's
// scale-only open animation.
useResizeObserver(containerRef, () => {
  cropperRef.value?.refresh()
})

watch(
  () => props.file,
  (file) => {
    if (imageSrc.value) {
      URL.revokeObjectURL(imageSrc.value)
      imageSrc.value = null
    }
    ready.value = false
    if (file) {
      imageSrc.value = URL.createObjectURL(file)
    }
  },
  { immediate: true },
)

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) ready.value = false
  },
)

const onReady = () => {
  ready.value = true
  // Backstop: if the cropper measured a stale container size, this re-runs
  // its layout against the current DOM. Cheap and idempotent.
  requestAnimationFrame(() => {
    cropperRef.value?.refresh()
  })
}

// Start the stencil as the largest square that fits inside the image — the
// library's default of ~80% of the visible area is needlessly conservative for
// avatars where users typically want the whole picture cropped square.
const defaultSize = ({ imageSize }: { imageSize: { width: number; height: number } }) => {
  const side = Math.min(imageSize.width, imageSize.height)
  return { width: side, height: side }
}

const rotate = (degrees: number) => {
  cropperRef.value?.rotate(degrees)
}

const reset = () => {
  cropperRef.value?.reset()
}

const cancel = () => {
  emit('cancel')
}

const handleOpenChange = (next: boolean) => {
  if (!next && !confirming.value) emit('cancel')
}

const confirm = async () => {
  if (!cropperRef.value) return
  const result = cropperRef.value.getResult()
  const canvas: HTMLCanvasElement | undefined = result?.canvas
  if (!canvas) return
  confirming.value = true
  try {
    const blob: Blob | null = await new Promise((resolve) =>
      canvas.toBlob((b) => resolve(b), 'image/png'),
    )
    if (!blob) {
      emit('cancel')
      return
    }
    emit('confirm', blob)
  } finally {
    confirming.value = false
  }
}
</script>
