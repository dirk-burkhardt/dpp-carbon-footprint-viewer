<script setup lang="ts">
/**
 * Shown on small screens instead of an analysis that needs a large screen. The user can open it anyway.
 */
import { ComputerDesktopIcon } from '@heroicons/vue/24/outline'
import { showDesktopViewsAnyway } from '@/lib/viewport'
import { assetSelectionQuery } from '@/lib/assetSelectionState'
</script>

<template>
  <div class="px-6 py-12 text-center max-w-md mx-auto">
    <ComputerDesktopIcon class="h-12 mx-auto mb-4 opacity-70" />
    <h1 class="text-xl mb-2">Made for larger screens</h1>
    <p class="text-sm mb-6">
      This analysis shows many values side by side and needs a larger screen. Open it on a computer or tablet for
      the full view.
    </p>
    <div class="flex flex-col gap-3">
      <router-link class="btn btn-primary" :to="{ name: 'home', query: assetSelectionQuery() }">Back to the asset selection</router-link>
      <button type="button" class="btn btn-outline" @click="showDesktopViewsAnyway = true">Show anyway</button>
    </div>
  </div>
</template>
