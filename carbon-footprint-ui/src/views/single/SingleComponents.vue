<script setup lang="ts">
import type { loadFullAssetInfo } from '@/lib/util'
import ComponentFootprintPlot from '@/components/ComponentFootprintPlot.vue'
import CarbonSankeyDiagram from '@/components/CarbonSankeyDiagram.vue'
import AssetTree from '@/components/AssetTree.vue'
import ShellCard from '@/components/ShellCard.vue'

defineProps<{ info: Awaited<ReturnType<typeof loadFullAssetInfo>>}>()

</script>
<template>
  <div class="col-span-3" v-if="info.carbonTree">
    <div class="card bg-base-100">
      <div class="card-body pr-0 overflow-visible">
        <h2 class="card-title px-8">Asset Structure</h2>
        <ShellCard :shell="info.description" class="shadow-xl w-80 m-6 ml-8" compact show-co2 />
        <div>
          <AssetTree :asset="info.carbonTree" :hide-expand="true" :scroll-y="true" :allow-zoom="true" :show-to-asset="true" :show-diff="info.carbonTree.hasChanges" />
        </div>
      </div>
    </div>
  </div>
  <div class="col-span-3" v-if="info.carbonTree">
    <div class="card bg-base-100">
      <div class="card-body">
        <h2 class="card-title">Component Footprints</h2>
        <ComponentFootprintPlot :carbon-tree="info.carbonTree" />
      </div>
    </div>
  </div>
  <div class="col-span-6" v-if="info.carbonTree">
    <div class="card bg-base-100">
      <div class="card-body">
        <h2 class="card-title">Component Distribution of the Carbon Footprint</h2>
        <CarbonSankeyDiagram :carbon-tree="info.carbonTree" />
      </div>
    </div>
  </div>
</template>
