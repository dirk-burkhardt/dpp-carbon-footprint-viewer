<script setup lang="ts">
/**
 * Components ordered by the emissions they cause themselves (all units together). The components that together
 * cause the first 80 % are the hotspots where optimizing pays off most.
 */
import { computed } from 'vue'
import { grams, percent } from '@/lib/util'
import { analyzeStructure, HOTSPOT_SHARE } from '@/lib/keyFigures'
import type CarbonTree from '@/lib/model/CarbonTree'

const props = defineProps<{ carbonTree: CarbonTree }>()

const analysis = computed(() => analyzeStructure(props.carbonTree))
const hotspotCount = computed(() => analysis.value.hotspots.filter((h) => h.isHotspot).length)
</script>

<template>
  <div>
    <p class="text-sm mb-3">
      <template v-if="analysis.hotspots.length">
        {{ hotspotCount }} of {{ analysis.hotspots.length }} sources cause {{ percent(HOTSPOT_SHARE) }} of the
        declared emissions. Each row shows what a component causes itself, without its own components, for all its
        units in the product.
      </template>
      <template v-else>No component provides emissions.</template>
    </p>
    <table v-if="analysis.hotspots.length" class="table table-sm">
      <thead>
        <tr>
          <th>Component</th>
          <th class="text-right">Units</th>
          <th class="text-right">CO2eq</th>
          <th class="text-right">Share</th>
          <th class="w-1/3">Cumulative share</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(h, i) of analysis.hotspots" :key="i" :class="{ 'opacity-60': !h.isHotspot }">
          <td :class="{ 'font-semibold': h.isHotspot }">{{ h.name }}</td>
          <td class="text-right">{{ h.units }}</td>
          <td class="text-right whitespace-nowrap">{{ grams(h.co2eq, 'kg') }}</td>
          <td class="text-right">{{ percent(h.share) }}</td>
          <td>
            <div class="relative h-2 rounded-sm bg-base-300 overflow-hidden" :title="percent(h.cumulativeShare)">
              <div class="absolute inset-y-0 left-0 bg-primary/40" :style="{ width: `${(h.cumulativeShare - h.share) * 100}%` }"></div>
              <div
                class="absolute inset-y-0 bg-primary"
                :style="{ left: `${(h.cumulativeShare - h.share) * 100}%`, width: `${h.share * 100}%` }"
              ></div>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
