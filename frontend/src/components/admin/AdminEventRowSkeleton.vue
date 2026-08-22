<script setup lang="ts">
import Skeleton from '@/components/ui/skeleton/Skeleton.vue'
</script>

<template>
  <tr aria-hidden="true">
    <td class="px-4 py-3">
      <Skeleton class="h-4 w-40" />
      <Skeleton class="mt-1.5 h-3 w-56" />
    </td>
    <td class="px-4 py-3"><Skeleton class="h-4 w-20" /></td>
    <td class="px-4 py-3"><Skeleton class="h-4 w-20" /></td>
    <td class="px-4 py-3"><Skeleton class="h-5 w-16 rounded-full" /></td>
    <td class="px-4 py-3"><Skeleton class="h-4 w-8" /></td>
    <td class="px-4 py-3 text-right">
      <div class="flex justify-end gap-1">
        <Skeleton class="h-8 w-8 rounded-md" />
        <Skeleton class="h-8 w-8 rounded-md" />
      </div>
    </td>
  </tr>
</template>
