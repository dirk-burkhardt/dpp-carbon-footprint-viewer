<script setup lang="ts">
/**
 * Favoriten: sortierbar per Drag-and-drop. Datasheet zeigt alle Favoriten, Compare vergleicht die ersten beiden.
 */
import { computed, ref } from 'vue'
import { ArrowsRightLeftIcon, ArrowsUpDownIcon, StarIcon, TableCellsIcon } from '@heroicons/vue/24/outline'
import { StarIcon as SolidStarIcon } from '@heroicons/vue/24/solid'
import type { ShellDescriptionSmallInterface } from '@/lib/api/shellTypes'
import ShellCard from '@/components/ShellCard.vue'
import { favoriteIds, moveFavorite, toggleFavorite } from '@/lib/favorites'
import { encodeBase64 } from '@/lib/encoding'

const props = defineProps<{
  /** Bekannte Shells (vorgeladene und externe) je globalAssetId */
  shellsById: Record<string, ShellDescriptionSmallInterface>
}>()

// Favoriten, deren Shell (noch) nicht geladen ist, werden nicht angezeigt, behalten aber ihre Position
const favorites = computed(() =>
  favoriteIds.value
    .map((id, index) => ({ index, shell: props.shellsById[id] }))
    .filter((f): f is { index: number, shell: ShellDescriptionSmallInterface } => f.shell !== undefined)
)

const compareRoute = computed(() => {
  const [first, second] = favorites.value
  if (!first || !second) {
    return undefined
  }
  return { name: 'visualization.dual', params: { first: encodeBase64(first.shell.globalAssetId), second: encodeBase64(second.shell.globalAssetId) } }
})
const datasheetRoute = computed(() => {
  if (!favorites.value.length) {
    return undefined
  }
  return { name: 'datasheet', params: { assets: favorites.value.map((f) => encodeBase64(f.shell.globalAssetId)) } }
})

// Drag-and-drop
const dragIndex = ref<number>()
const dropIndex = ref<number>()

function onDragStart(e: DragEvent, index: number) {
  dragIndex.value = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(index))
  }
}
function onDragOver(e: DragEvent, index: number) {
  if (dragIndex.value === undefined) {
    return
  }
  e.preventDefault()
  dropIndex.value = index
}
function onDrop(index: number) {
  if (dragIndex.value !== undefined) {
    moveFavorite(dragIndex.value, index)
  }
  onDragEnd()
}
function onDragEnd() {
  dragIndex.value = undefined
  dropIndex.value = undefined
}
</script>

<template>
  <div class="flex flex-col min-h-0 bg-base-200/60 border-l border-base-300">
    <div class="flex items-center gap-2 px-4 pt-3 pb-3">
      <StarIcon class="h-6 text-yellow-500" />
      <h2 class="text-lg">Favorites</h2>
      <span class="text-sm opacity-60">{{ favorites.length }}</span>
    </div>

    <!-- Analysen der Favoriten -->
    <div class="grid grid-cols-2 gap-2 px-4 py-3 border-y border-base-300">
      <router-link
        v-if="compareRoute"
        :to="compareRoute"
        class="btn btn-primary"
        :title="`Compare ${favorites[0].shell.name} with ${favorites[1].shell.name}`"
      ><ArrowsRightLeftIcon class="h-5" /> Compare</router-link>
      <button v-else type="button" class="btn btn-primary" disabled title="Compare needs at least two favorites">
        <ArrowsRightLeftIcon class="h-5" /> Compare
      </button>
      <router-link v-if="datasheetRoute" :to="datasheetRoute" class="btn btn-primary" title="Show all favorites in a data sheet">
        <TableCellsIcon class="h-5" /> Datasheet
      </router-link>
      <button v-else type="button" class="btn btn-primary" disabled title="Datasheet needs at least one favorite">
        <TableCellsIcon class="h-5" /> Datasheet
      </button>
    </div>

    <!-- Liste der Favoriten -->
    <div class="grow min-h-0 flex flex-col m-3 rounded-sm bg-base-100 border border-base-300 shadow-inner">
      <div v-if="favorites.length > 1" class="flex items-center gap-1 px-3 pt-2 text-xs opacity-60">
        <ArrowsUpDownIcon class="h-4" /> Drag to sort. Compare uses the first two.
      </div>
      <div class="grow min-h-0 overflow-y-auto p-3 flex flex-col gap-3">
        <p v-if="!favorites.length" class="text-sm text-center opacity-70 mt-2">
          Mark assets with the star to add them here.
        </p>
        <template v-for="(f, position) of favorites" :key="f.shell.globalAssetId">
          <div
            class="relative group rounded-sm shadow-md transition-opacity"
            :class="{
              'opacity-40': dragIndex === f.index,
              'outline-2 outline-primary': dropIndex === f.index && dragIndex !== f.index,
              'cursor-grab': favorites.length > 1,
            }"
            :draggable="favorites.length > 1"
            @dragstart="onDragStart($event, f.index)"
            @dragover="onDragOver($event, f.index)"
            @drop.prevent="onDrop(f.index)"
            @dragend="onDragEnd"
          >
            <button
              type="button"
              class="absolute top-0 left-0 z-10 w-7 h-7 p-1 bg-yellow-400 text-base-100 rounded-tl-sm rounded-br-lg"
              title="Remove from favorites"
              @click.stop="toggleFavorite(f.shell.globalAssetId)"
            >
              <SolidStarIcon />
            </button>
            <ShellCard
              :shell="f.shell"
              :to="{ name: 'visualization.single', params: { asset: encodeBase64(f.shell.globalAssetId) } }"
              compact
              draggable="false"
            />
          </div>
          <div v-if="position === 1 && favorites.length > 2" class="border-t-2 border-base-300"></div>
        </template>
      </div>
    </div>
  </div>
</template>
