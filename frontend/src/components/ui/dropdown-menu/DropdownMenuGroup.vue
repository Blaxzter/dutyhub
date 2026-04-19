<script setup lang="ts">
import { DropdownMenuGroup, type DropdownMenuGroupProps } from 'reka-ui'

const props = defineProps<DropdownMenuGroupProps>()
</script>

<template>
  <DropdownMenuGroup data-slot="dropdown-menu-event" v-bind="props">
    <slot />
  </DropdownMenuGroup>
</template>
