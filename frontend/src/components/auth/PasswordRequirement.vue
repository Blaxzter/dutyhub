<script setup lang="ts">
/**
 * The one line under a "choose a password" field.
 *
 * The rule, the live tick and the error message share a single row, because
 * they were never three different things — "use at least 8 characters" answers
 * all three questions. Rendering it twice, once as a hint and once as an error,
 * is the stacked duplicate this component exists to remove.
 *
 * The row never leaves the DOM, so the `aria-describedby` that `FormControl`
 * wires up always resolves, and the field needs no `<FormMessage>` of its own.
 *
 * The root is a `<span>` on purpose: it is slotted into `<FormDescription>`,
 * which is a `<p>`, and a `<p>` inside a `<p>` is not markup a browser keeps.
 */
import { computed } from 'vue'

import { Check, Circle, CircleAlert } from '@lucide/vue'

const props = defineProps<{
  /** The rule in words, shown whenever there is no error to show instead. */
  label: string
  /** Copy for the satisfied state — shorter, since the tick has said "yes". */
  metLabel: string
  /** True once the value satisfies the rule. */
  met: boolean
  /** The field's validation error, if it currently has one. */
  message?: string
}>()

const state = computed(() => (props.message ? 'failed' : props.met ? 'met' : 'idle'))
</script>

<template>
  <span
    class="flex items-center gap-1.5 transition-colors"
    :class="{
      'text-destructive': state === 'failed',
      'text-primary': state === 'met',
      'text-muted-foreground': state === 'idle',
    }"
    :data-state="state"
    data-testid="password-requirement"
  >
    <CircleAlert v-if="state === 'failed'" class="size-3.5 shrink-0" aria-hidden="true" />
    <Check v-else-if="state === 'met'" class="size-3.5 shrink-0" aria-hidden="true" />
    <Circle v-else class="size-3.5 shrink-0 opacity-50" aria-hidden="true" />
    <span>{{ message || (met ? metLabel : label) }}</span>
  </span>
</template>
