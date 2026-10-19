<script setup lang="ts">
const props = defineProps<{
  name: string
  alt: string
}>()

const colorMode = useColorMode()
const root = useRuntimeConfig().app.baseURL.replace(/\/$/, '')

const light = computed(() => `${root}${props.name}`)
const current = computed(() => (colorMode.value === 'dark' ? `${light.value}-dark` : light.value))
</script>

<template>
  <div class="my-6 overflow-hidden rounded-md border border-default">
    <ClientOnly>
      <video
        :key="current"
        class="block h-auto w-full"
        autoplay
        loop
        muted
        playsinline
        preload="metadata"
        :poster="`${current}.webp`"
        :aria-label="alt"
      >
        <source :src="`${current}.webm`" type="video/webm">
        <source :src="`${current}.mp4`" type="video/mp4">
      </video>
      <template #fallback>
        <img
          class="block h-auto w-full dark:hidden"
          :src="`${light}.webp`"
          :alt="alt"
        >
        <img
          class="hidden h-auto w-full dark:block"
          :src="`${light}-dark.webp`"
          :alt="alt"
        >
      </template>
    </ClientOnly>
  </div>
</template>
