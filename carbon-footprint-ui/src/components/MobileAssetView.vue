<script setup lang="ts">
/**
 * Compact single asset view for small screens: name, totals, key figures, emissions per life cycle phase
 * (declared and estimated) and the estimated phases. Components, simulation, maps and the detailed charts are
 * left to larger screens.
 */
import { computed } from 'vue'
import { ComputerDesktopIcon } from '@heroicons/vue/24/outline'
import type { loadFullAssetInfo } from '@/lib/util'
import { grams } from '@/lib/util'
import KeyFigures from '@/components/KeyFigures.vue'
import AssetThumbnail from '@/components/AssetThumbnail.vue'
import DeclaredAndEstimatedPhases from '@/components/DeclaredAndEstimatedPhases.vue'
import { showEstimates, useEstimates } from '@/lib/estimates'
import { showDesktopViewsAnyway } from '@/lib/viewport'

const props = defineProps<{ info: Awaited<ReturnType<typeof loadFullAssetInfo>> }>()

const carbon = computed(() => props.info.carbonTree ?? props.info.carbonFootprint)
const totals = computed(() => [
  { label: 'Total', value: carbon.value?.totalCo2eq },
  { label: 'Product', value: carbon.value?.productCo2eq },
  { label: 'Transport', value: carbon.value?.transportCo2eq },
])
const { estimates } = useEstimates(computed(() => props.info.asset.id))
const statusLabels = { estimated: 'estimated', declared: 'declared', missing: 'not possible' } as const
</script>

<template>
  <div class="px-4 py-3 space-y-5">
    <div class="flex gap-3 items-start">
      <AssetThumbnail :asset-id="info.asset.id" class="w-20 h-20 shrink-0 rounded-sm overflow-hidden" />
      <div class="min-w-0">
        <h1 class="text-xl break-words">{{ info.description?.name }}</h1>
        <div v-if="info.description?.idShort" class="font-mono text-xs break-all opacity-70">{{ info.description.idShort }}</div>
        <div class="text-sm mt-1">
          <template v-if="info.carbonFootprint">carbon footprint provided</template>
          <template v-else-if="info.carbonTree">carbon footprint calculated from sub-components</template>
          <template v-else>no carbon footprint data</template>
        </div>
      </div>
    </div>

    <div v-if="carbon" class="grid grid-cols-3 gap-2">
      <div v-for="t of totals" :key="t.label" class="rounded-lg border border-base-300 px-2 py-2 text-center">
        <div class="text-xs opacity-70">{{ t.label }}</div>
        <div class="text-base">{{ grams(t.value ?? 0, 'kg') }}</div>
      </div>
    </div>

    <KeyFigures :asset-id="info.asset.id" :total-co2eq="carbon?.totalCo2eq" :indicators="info.indicators" :carbon-tree="info.carbonTree" />

    <section>
      <div class="flex items-center gap-2 mb-2">
        <h2 class="text-lg grow">Emissions per phase</h2>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="showEstimates" type="checkbox" class="toggle toggle-sm" />
          Estimates
        </label>
      </div>
      <DeclaredAndEstimatedPhases :carbon="carbon" :estimates="estimates" :show-estimates="showEstimates" />
    </section>

    <section v-if="showEstimates && estimates">
      <h2 class="text-lg mb-2">Estimated phases</h2>
      <ul class="divide-y divide-base-300 text-sm">
        <li v-for="p of estimates.phases" :key="p.phase" class="py-2 flex gap-3">
          <span class="w-16 shrink-0 font-semibold">{{ p.phase }}</span>
          <span class="grow min-w-0">
            {{ p.label }}<br />
            <span class="opacity-70">{{ statusLabels[p.status] }}<template v-if="p.status !== 'estimated' && p.reason">: {{ p.reason }}</template></span>
          </span>
          <span v-if="p.co2eq != null" class="shrink-0 whitespace-nowrap">
            <span class="inline-block w-3 h-3 align-middle mr-1 estimate-fill"></span>{{ grams(p.co2eq, 'kg') }}
          </span>
        </li>
      </ul>
      <p class="text-xs opacity-70 mt-2">
        Assumptions and sources can be changed and viewed in the Estimates view on a larger screen.
      </p>
    </section>

    <div class="rounded-lg border border-base-300 p-3 text-sm flex gap-3 items-start">
      <ComputerDesktopIcon class="h-6 shrink-0 opacity-70" />
      <div>
        Components, simulation, map, transport routes and the detailed life cycle charts are made for larger screens.
        <button type="button" class="link block mt-1" @click="showDesktopViewsAnyway = true">Show the full view anyway</button>
      </div>
    </div>
  </div>
</template>
