<script setup lang="ts">
/**
 * Karte einer Schale in der Assetauswahl. Ein Klick öffnet die Einzelansicht, der Stern markiert als Favorit.
 */
import { StarIcon } from '@heroicons/vue/24/outline'
import { StarIcon as SolidStarIcon } from '@heroicons/vue/24/solid'
import type { ShellDescriptionSmallInterface } from '@/lib/api/shellTypes'
import ShellCard from '@/components/ShellCard.vue'
import { favoriteIds, toggleFavorite } from '@/lib/favorites'
import { encodeBase64 } from '@/lib/encoding'
import { computed } from 'vue'

const props = defineProps<{ shell: ShellDescriptionSmallInterface }>()
const favorite = computed(() => favoriteIds.value.includes(props.shell.globalAssetId))
</script>

<template>
  <div
    class="relative group rounded-sm shadow-md hover:shadow-xl transition-shadow bg-base-100"
    :class="{ 'outline-4 outline-yellow-400': favorite }"
  >
    <button
      type="button"
      class="absolute top-0 left-0 z-10 w-8 h-8 p-1 rounded-tl-sm rounded-br-lg text-base-100 bg-yellow-400 transition-opacity"
      :class="favorite ? 'opacity-100' : 'opacity-0 group-hover:opacity-80 focus:opacity-80'"
      :title="favorite ? 'Remove from favorites' : 'Add to favorites'"
      @click.stop="toggleFavorite(props.shell.globalAssetId)"
    >
      <SolidStarIcon v-if="favorite" />
      <StarIcon v-else />
    </button>
    <ShellCard :shell="props.shell" :to="{ name: 'visualization.single', params: { asset: encodeBase64(props.shell.globalAssetId) } }">
      <slot />
    </ShellCard>
  </div>
</template>
