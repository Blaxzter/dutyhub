<script lang="ts" setup>
defineProps({
  iconData: {
    type: Object,
    required: true,
  },
  className: {
    type: String,
    default: '',
  },
  color: {
    type: String,
    default: 'currentColor',
  },
})
</script>

<template>
  <!-- `role="img"` promises an accessible name, so it is only claimed when
       `iconData.title` actually has one. Some call sites render before the
       icon data resolves, which produced `<svg role="img"><title></title>` —
       a named image with no name (axe `svg-img-alt`, serious). Without a
       title the icon is decorative, so it is hidden from the a11y tree
       instead. -->
  <svg
    :class="className"
    :role="iconData?.title ? 'img' : undefined"
    :aria-hidden="iconData?.title ? undefined : 'true'"
    viewBox="0 0 24 24"
    xmlns="http://www.w3.org/2000/svg"
    :fill="color"
  >
    <title v-if="iconData?.title">{{ iconData.title }}</title>
    <path :d="iconData?.path" />
  </svg>
</template>
