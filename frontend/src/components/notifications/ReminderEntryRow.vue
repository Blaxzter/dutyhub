<script setup lang="ts">
import { ref, watch } from 'vue'

import { Check, EllipsisVertical, Lock, MessageCircle, Trash2, X } from '@respeak/lucide-motion-vue'
import { Loader2, Mail, Smartphone } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import Switch from '@/components/ui/switch/Switch.vue'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

defineProps<{
  offsetLabel: string
  channels: string[]
  availableChannels: string[]
  readonly?: boolean
  statusLabel?: string
  loading?: boolean
}>()

const emit = defineEmits<{
  'toggle-channel': [channel: string]
  remove: []
}>()

const { t } = useI18n()

const menuOpen = ref(false)
const confirmingDelete = ref(false)

watch(menuOpen, (open) => {
  if (!open) confirmingDelete.value = false
})

function onConfirmRemove() {
  menuOpen.value = false
  emit('remove')
}
</script>

<template>
  <div
    class="flex items-center gap-3 rounded-lg border p-3"
    :class="{ 'border-dashed opacity-50': readonly }"
  >
    <div class="flex-1 text-sm" :class="readonly ? '' : 'font-medium'">
      {{ offsetLabel }}
    </div>

    <!-- Channel toggle buttons (interactive) -->
    <div
      v-if="!readonly"
      class="flex items-center gap-1.5"
      :class="{ 'pointer-tasks-none opacity-50': loading }"
    >
      <template v-for="ch in availableChannels" :key="ch">
        <!-- Last remaining channel: looks active, tooltip describes effect, toast on click -->
        <TooltipProvider v-if="channels.includes(ch) && channels.length === 1">
          <Tooltip>
            <TooltipTrigger as-child>
              <button
                class="flex items-center gap-1 rounded-md bg-primary px-2 py-1 text-xs font-medium text-primary-foreground"
                @click="toast.info(t('notifications.reminders.lastChannelHint'))"
              >
                <Mail v-if="ch === 'email'" :size="14" />
                <Smartphone v-else-if="ch === 'push'" :size="14" />
                <MessageCircle v-else :size="14" animateOnHover triggerTarget="parent" />
                <span class="hidden md:inline">{{ t(`notifications.channels.${ch}`) }}</span>
              </button>
            </TooltipTrigger>
            <TooltipContent>
              {{
                t('notifications.reminders.channelActiveHint', {
                  channel: t(`notifications.channels.${ch}`),
                  offset: offsetLabel,
                })
              }}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <!-- Normal toggle button -->
        <button
          v-else
          :disabled="loading"
          :class="[
            'flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors',
            channels.includes(ch)
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-muted-foreground hover:bg-muted/80',
          ]"
          :title="
            channels.includes(ch)
              ? t('notifications.reminders.channelActiveHint', {
                  channel: t(`notifications.channels.${ch}`),
                  offset: offsetLabel,
                })
              : t(`notifications.channels.${ch}`)
          "
          @click="$emit('toggle-channel', ch)"
        >
          <Mail v-if="ch === 'email'" :size="14" />
          <Smartphone v-else-if="ch === 'push'" :size="14" />
          <MessageCircle v-else :size="14" animateOnHover triggerTarget="parent" />
          <span class="hidden md:inline">{{ t(`notifications.channels.${ch}`) }}</span>
        </button>
      </template>
    </div>

    <!-- Channel badges (readonly) -->
    <div v-else class="flex items-center gap-1.5">
      <span
        v-for="ch in channels"
        :key="ch"
        class="flex items-center gap-1 rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground"
      >
        <Mail v-if="ch === 'email'" :size="14" />
        <Smartphone v-else-if="ch === 'push'" :size="14" />
        <MessageCircle v-else :size="14" animateOnHover triggerTarget="parent" />
        <span class="hidden md:inline">{{ t(`notifications.channels.${ch}`) }}</span>
      </span>
    </div>

    <!-- Status badge for past reminders -->
    <span v-if="readonly && statusLabel" class="rounded-full border px-2 py-0.5 text-xs">
      {{ statusLabel }}
    </span>

    <!-- More menu (interactive only) -->
    <DropdownMenu v-if="!readonly" v-model:open="menuOpen">
      <DropdownMenuTrigger as-child :disabled="loading">
        <button
          :disabled="loading"
          class="rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:pointer-tasks-none"
        >
          <Loader2 v-if="loading" :size="16" class="animate-spin" />
          <EllipsisVertical v-else :size="16" animateOnHover triggerTarget="parent" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" class="w-48">
        <DropdownMenuLabel>{{ t('notifications.channels.sectionTitle') }}</DropdownMenuLabel>
        <div
          v-for="ch in availableChannels"
          :key="ch"
          class="flex items-center gap-2 rounded-sm px-2 py-1.5"
          @pointerdown.stop
          @click.stop
        >
          <Mail v-if="ch === 'email'" :size="14" class="shrink-0 text-muted-foreground" />
          <Smartphone v-else-if="ch === 'push'" :size="14" class="shrink-0 text-muted-foreground" />
          <MessageCircle
            v-else
            :size="14"
            class="shrink-0 text-muted-foreground"
            animateOnHover
            triggerTarget="parent"
          />
          <span class="flex-1 text-sm">{{ t(`notifications.channels.${ch}`) }}</span>
          <TooltipProvider v-if="channels.includes(ch) && channels.length === 1">
            <Tooltip>
              <TooltipTrigger as-child>
                <span
                  class="inline-flex items-center gap-1.5"
                  @click.stop="toast.info(t('notifications.reminders.lastChannelHint'))"
                >
                  <Lock
                    :size="12"
                    class="text-muted-foreground"
                    animateOnHover
                    triggerTarget="parent"
                  />
                  <Switch :model-value="true" class="pointer-tasks-none" />
                </span>
              </TooltipTrigger>
              <TooltipContent>
                {{ t('notifications.reminders.lastChannelHint') }}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <Switch
            v-else
            :model-value="channels.includes(ch)"
            @update:model-value="$emit('toggle-channel', ch)"
          />
        </div>

        <DropdownMenuSeparator />

        <!-- Delete: normal state -->
        <DropdownMenuItem
          v-if="!confirmingDelete"
          variant="destructive"
          @select="
            (e: Event) => {
              e.preventDefault()
              confirmingDelete = true
            }
          "
        >
          <Trash2 :size="14" animateOnHover triggerTarget="parent" />
          {{ t('notifications.reminders.remove') }}
        </DropdownMenuItem>

        <!-- Delete: confirm state -->
        <template v-else>
          <DropdownMenuItem variant="destructive" @select="onConfirmRemove">
            <Check :size="14" animateOnHover triggerTarget="parent" />
            {{ t('notifications.reminders.removeConfirm') }}
          </DropdownMenuItem>
          <DropdownMenuItem
            @select="
              (e: Event) => {
                e.preventDefault()
                confirmingDelete = false
              }
            "
          >
            <X :size="14" animateOnHover triggerTarget="parent" />
            {{ t('common.actions.cancel') }}
          </DropdownMenuItem>
        </template>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
</template>
