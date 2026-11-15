<script setup lang="ts">
/**
 * Hinweis anstelle des Inhalts, wenn die Assets einer Ansicht nicht geladen werden konnten.
 */
import { problemPanelOpen } from '@/lib/problems'

defineProps<{ message: string }>()
</script>

<template>
  <div class="mx-6 my-10 text-center">
    <p class="text-lg">{{ message }}</p>
    <p class="mt-2 text-sm opacity-70">
      <router-link :to="{ name: 'home' }" class="link">Back to the asset selection</router-link>
      or <button type="button" class="link" @click="problemPanelOpen = true">show details</button>
    </p>
  </div>
</template>
