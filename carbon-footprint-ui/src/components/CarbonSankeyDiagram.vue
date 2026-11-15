<template>
  <div ref="visualizationContainer"></div>
</template>
<script lang="ts" setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { toD3Color } from '@/lib/util'
import CarbonSankey from '@/lib/visualization/CarbonSankey'
import c from '@/lib/visualizationColors'
import Color from 'colorjs.io'
import { rgb } from 'd3';
import type CarbonTree from '@/lib/model/CarbonTree'

const props = defineProps<{ carbonTree: CarbonTree }>()

const visualizationContainer = ref<HTMLDivElement>();
const carbonSankey = ref<CarbonSankey>();

function getColor(cssVariable: string) {
  return new Color(`oklch(${window.getComputedStyle(visualizationContainer.value!).getPropertyValue(cssVariable)})`);
}

/**
 * Load the visualization
 */
watch(() => visualizationContainer.value, () => {
  if (visualizationContainer.value && props.carbonTree) {
    carbonSankey.value = new CarbonSankey(visualizationContainer.value!, props.carbonTree, {
      nodeLabelPrimary: toD3Color(getColor("--p")),
      nodeLabelSecondary: toD3Color(getColor("--s")),
      defaultNode: toD3Color(getColor("--b3").set({ l: l => l * .6 })),
      transportLink: rgb(...c("tcf")),
      productLink: rgb(...c("pcf"))
    })
    carbonSankey.value.visualize(visualizationContainer.value!.clientWidth, 450, 10);

    // Update filters when a visualization was (re-)calculated
    // d.onVisualizeDone = () => {
    //   forcePathsUpdate.value += 1
    // }
    // Set the actual button methods
    // downloadPNG.value = () => d.downloadAsPNG(description.value)
    // downloadSVG.value = () => d.downloadAsSVG(description.value)
    // Bind filter methods (show/hide paths, show/hide pcf/tcf, show/hide lifecycles)
    // onMustInclude.value = (pathItem: string) => {
    //   d.pathMustInclude = pathItem
    // }
    // hidePaths.value = d.hiddenPaths
    // showLifeCycle.value = d.visibleLifeCyclePhases
    // watch(showUndefinedLifeCycle, (v) => { d.showUndefinedLifeCyclePhase = v })
    // watch(showPCF, (v) => { d.hidePCF = !v })
    // watch(showTCF, (v) => { d.hideTCF = !v })
  }
}, { immediate: true });

onBeforeUnmount(() => {
  carbonSankey.value?.destroy();
})

</script>
