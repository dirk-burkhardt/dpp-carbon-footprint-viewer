<script setup lang="ts">
/**
 * Multi-Asset Data Sheet: exakte Werte mehrerer Assets nebeneinander, mit Stückzahl je Asset und einer
 * Spalte mit der Summe (Combined). Numerische Zellen sind je Zeile farblich normalisiert.
 * Die Assets kommen aus den Favoriten (Startseite).
 */
import { useRoute } from 'vue-router'
import { computed, inject, onUnmounted, type Ref, ref, watch } from 'vue'
import { computedAsync } from '@vueuse/core'
import { sum } from 'lodash'
import { ArrowTopRightOnSquareIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { BackOnErrorHandler, currentLoadError } from '@/lib/BackOnErrorHandler'
import { convertGrams, grams, loadFullAssetInfo, or, simulationFromRoute } from '@/lib/util'
import { AssetIdMap } from '@/lib/AssetIdMap'
import { assetIdMapKey } from '@/lib/injectionKeys'
import CarbonTree from '@/lib/model/CarbonTree'
import BreadcrumbsBar from '@/components/BreadcrumbsBar.vue'
import LoadFailed from '@/components/layout/LoadFailed.vue'
import { LifeCyclePhases } from '@/lib/lifeCycleUtil'
import { storageRef } from '@/lib/storage'
import { decodeBase64, encodeBase64 } from '@/lib/encoding'
import { ErrorClient } from '@/lib/ErrorDataHandler'
import { co2eqByLifeCyclePhases, sortPhases, type Carbon } from '@/lib/carbonValues'

const route = useRoute();
const routeAssets = computed(() => ([] as string[]).concat(route.params.assets ?? []));

// General shell information
const idMap = inject<Ref<AssetIdMap>>(assetIdMapKey);
type Info = Awaited<ReturnType<typeof loadFullAssetInfo>>
// Alle Assets anzeigen, auch ohne CO2-Daten. Kann ein einzelnes nicht geladen werden, erscheint es in der
// Fehlerliste; nur wenn keines geladen werden kann, ersetzt ein Hinweis die Tabelle.
const infos = computedAsync<Info[] | undefined>(async () => {
  // Route already changed while leaving the view
  if (!idMap?.value || route.name !== 'datasheet') {
    return undefined;
  }
  const results = await Promise.allSettled(routeAssets.value.map((a) =>
    loadFullAssetInfo(a, idMap.value, "url-", (title, details, source) => ErrorClient.warn(title, details, source ? { source } : undefined), simulationFromRoute(route))
  ));
  results.forEach((r, i) => {
    if (r.status === 'rejected') {
      ErrorClient.add({
        message: r.reason?.status === 404 ? "An asset of the data sheet could not be found" : "An asset of the data sheet could not be loaded",
        details: decodeBase64(routeAssets.value[i]),
        status: typeof r.reason?.status === 'number' ? r.reason.status : undefined,
      });
    }
  });
  const loaded = results.filter((r): r is PromiseFulfilledResult<Info> => r.status === 'fulfilled').map((r) => r.value);
  if (routeAssets.value.length && !loaded.length) {
    await BackOnErrorHandler.bind(Promise.reject(new Error("No asset could be loaded")), "The assets of the data sheet could not be loaded");
  }
  return loaded;
}, undefined)

const descriptions = computed(() => (infos.value || []).map(i => i.description));
const addresses = computed(() => (infos.value || []).map(i => i.address));
const carbon = computed<(Carbon | undefined)[]>(() => (infos.value || []).map(i => i.carbonTree ?? i.carbonFootprint));

const carbonMultipliers = ref<number[]>([]);
watch(() => carbon.value, (newValue) => {
  carbonMultipliers.value = Array(newValue.length).fill(1);
})
const multiplier = (i: number) => Math.max(0, Number(carbonMultipliers.value[i]) || 0);

const carbonRows = [['Total CO2eq', 'totalCo2eq'], ['Product CO2eq', 'productCo2eq'], ['Transport CO2eq', 'transportCo2eq']] as const;
const carbonValues = computed(() => (
  carbon.value.map((c, i) => ({
    'totalCo2eq': (c?.totalCo2eq || 0) * multiplier(i),
    'productCo2eq': (c?.productCo2eq || 0) * multiplier(i),
    'transportCo2eq': (c?.transportCo2eq || 0) * multiplier(i)
  }))
));
const carbonSums = computed(() => ({
  'totalCo2eq': sum(carbonValues.value.map(c => c.totalCo2eq)),
  'productCo2eq': sum(carbonValues.value.map(c => c.productCo2eq)),
  'transportCo2eq': sum(carbonValues.value.map(c => c.transportCo2eq)),
}))
const carbonMax = computed(() => ({
  'totalCo2eq': Math.max(...carbonValues.value.map(c => c.totalCo2eq)),
  'productCo2eq': Math.max(...carbonValues.value.map(c => c.productCo2eq)),
  'transportCo2eq': Math.max(...carbonValues.value.map(c => c.transportCo2eq)),
}))

const co2eqByPhases = computed(() => carbon.value.map((c, i) => (c ? co2eqByLifeCyclePhases(c, multiplier(i)) : {} as Record<string, number>)));
const availableCo2eqPhases = computed(() => sortPhases([...new Set(co2eqByPhases.value.map(Object.keys).flat())]));
const co2eqPhaseSums = computed(() => Object.fromEntries(availableCo2eqPhases.value.map((p) => [p, sum(co2eqByPhases.value.map((c) => c[p] || 0))])))
const co2eqPhaseMax = computed(() => Object.fromEntries(availableCo2eqPhases.value.map((p) => [p, Math.max(...co2eqByPhases.value.map((c) => c[p] || 0))])))

/** Anteil am Zeilenmaximum für die Farbe der Zelle */
function alpha(value: number | undefined, max: number) {
  return max > 0 && value ? (value / max) * 0.25 : 0;
}

const metaRows = [
  ['Description', 'description'],
  ['ID', 'id'],
  ['Global Asset ID', 'globalAssetId'],
  ['ID Short', 'idShort'],
  ['Asset Kind', 'assetKind'],
] as const;

function removeRoute(index: number) {
  return { name: 'datasheet', params: { assets: routeAssets.value.filter((_, i) => i !== index) } };
}

// Kopieren eines Zellwerts per Klick
const table = ref<HTMLTableElement>();
const copyToastVisible = ref(false);
let hideTimeout: number | undefined;
const copyValue = ref("");
const copyExplanation = ref("");
function copyContent(event: MouseEvent) {
  const cell = (event.target as HTMLElement).closest('td');
  if (!cell || cell.classList.contains('no-copy')) {
    return;
  }
  copyValue.value = cell.dataset.copy || cell.textContent?.trim() || "";
  copyExplanation.value = cell.dataset.copyExplanation || "";
  navigator.clipboard?.writeText(copyValue.value);
  clearTimeout(hideTimeout);
  copyToastVisible.value = true;
  hideTimeout = window.setTimeout(() => { copyToastVisible.value = false; }, 1200);
}
onUnmounted(() => clearTimeout(hideTimeout));

const pinCombined = storageRef("pinCombinedColumn", false);
</script>

<template>
  <div class="px-4 py-1">
    <BreadcrumbsBar />
  </div>
  <LoadFailed v-if="currentLoadError" :message="currentLoadError" />
  <div v-else class="px-4 pb-16">
    <div v-if="infos === undefined" class="skeleton h-96 w-full"></div>
    <p v-else-if="infos.length === 0" class="py-8 text-center">No assets selected.</p>
    <div v-else class="overflow-auto overscroll-x-contain max-h-[calc(100vh-7rem)] border border-base-300 rounded-sm">
      <table class="table table-sm table-pin-rows table-pin-cols table-data" ref="table" @click="copyContent">
        <thead>
          <tr class="bg-base-200">
            <th class="bg-base-200 align-bottom">
              <label class="flex items-center gap-2 font-normal text-xs cursor-pointer">
                <input type="checkbox" class="checkbox checkbox-xs" v-model="pinCombined" />
                Show combined first
              </label>
            </th>
            <td v-if="pinCombined && descriptions.length > 1" class="bg-base-200 align-top font-semibold">Combined</td>
            <td v-for="(d, i) of descriptions" :key="d!.id" class="bg-base-200 align-top no-copy">
              <div class="flex items-start gap-1">
                <router-link
                  :to="{ name: 'visualization.single', params: { asset: encodeBase64(d!.globalAssetId) } }"
                  class="font-semibold grow min-w-0 flex items-center gap-1 hover:underline"
                  :title="`${d!.name} (open asset)`"
                ><span class="truncate">{{ d!.name }}</span><ArrowTopRightOnSquareIcon class="shrink-0 h-3 opacity-60" /></router-link>
                <router-link
                  v-if="descriptions.length > 1"
                  :to="removeRoute(i)"
                  class="shrink-0 opacity-50 hover:opacity-100"
                  title="Remove from this data sheet"
                ><XMarkIcon class="h-4" /></router-link>
              </div>
              <label class="flex items-center gap-1 mt-1 font-normal text-xs" title="Number of units the values are multiplied with">
                Units
                <input class="input input-xs w-16 text-center" type="number" min="0" v-model.number="carbonMultipliers[i]" />
              </label>
            </td>
            <td v-if="!pinCombined && descriptions.length > 1" class="bg-base-200 align-top font-semibold">Combined</td>
          </tr>
        </thead>
        <tbody>
          <tr v-for="[name, key] of metaRows" :key="key">
            <th>{{ name }}</th>
            <td v-if="pinCombined && descriptions.length > 1" class="no-copy"></td>
            <td v-for="d of descriptions" :key="d.id">{{ d[key] }}</td>
            <td v-if="!pinCombined && descriptions.length > 1" class="no-copy"></td>
          </tr>
          <tr>
            <th>Address</th>
            <td v-if="pinCombined && descriptions.length > 1" class="no-copy"></td>
            <td v-for="(a, i) of addresses" :key="i">{{ a && String(a) !== 'undefined' ? a : '' }}</td>
            <td v-if="!pinCombined && descriptions.length > 1" class="no-copy"></td>
          </tr>
          <tr class="hover-with-before" v-for="[name, key] of carbonRows" :key="key">
            <th>{{ name }}</th>
            <td
              v-if="pinCombined && descriptions.length > 1"
              class="font-semibold"
              :data-copy="convertGrams(carbonSums[key], 'kg', 'g')"
              data-copy-explanation="CO2eq in g"
            >{{ grams(carbonSums[key], "kg") }}</td>
            <td
              v-for="(c, i) of carbon"
              :key="i"
              :data-copy="convertGrams(carbonValues[i][key], 'kg', 'g')"
              data-copy-explanation="CO2eq in g"
              :class="{ 'no-copy opacity-50 italic': !c }"
              :style="`--bg-alpha: ${alpha(carbonValues[i][key], carbonMax[key])};`"
            >
              {{ c ? grams(carbonValues[i][key], "kg") : 'no data' }}
            </td>
            <td
              v-if="!pinCombined && descriptions.length > 1"
              class="font-semibold"
              :data-copy="convertGrams(carbonSums[key], 'kg', 'g')"
              data-copy-explanation="CO2eq in g"
            >{{ grams(carbonSums[key], "kg") }}</td>
          </tr>
          <tr>
            <th>Covered Life Cycle Phases</th>
            <td v-if="pinCombined && descriptions.length > 1">{{ LifeCyclePhases.merged(...carbon.map(c => c?.coveredLifeCyclePhases).filter(x => x !== undefined) as LifeCyclePhases[]) }}</td>
            <td v-for="(c, i) of carbon" :key="i" :class="{ 'no-copy opacity-50 italic': !c }">{{ c ? or(c.coveredLifeCyclePhases, () => (c instanceof CarbonTree ? `${c.byChildrenCoveredLifeCyclePhases} (from its components)` : undefined)) : 'no carbon footprint data' }}</td>
            <td v-if="!pinCombined && descriptions.length > 1">{{ LifeCyclePhases.merged(...carbon.map(c => c?.coveredLifeCyclePhases).filter(x => x !== undefined) as LifeCyclePhases[]) }}</td>
          </tr>
          <tr v-for="phase of availableCo2eqPhases" :key="phase" class="hover-with-before">
            <th>{{ phase }}</th>
            <td
              v-if="pinCombined && descriptions.length > 1"
              class="font-semibold"
              :data-copy="convertGrams(co2eqPhaseSums[phase], 'kg', 'g')"
              data-copy-explanation="CO2eq in g"
            >{{ grams(co2eqPhaseSums[phase], "kg") }}</td>
            <td
              v-for="(c, i) of co2eqByPhases"
              :key="i"
              :data-copy="c[phase] ? convertGrams(c[phase], 'kg', 'g') : ''"
              data-copy-explanation="CO2eq in g"
              :style="`--bg-alpha: ${alpha(c[phase], co2eqPhaseMax[phase])};`"
            >
              {{ c[phase] ? grams(c[phase], "kg") : '' }}
            </td>
            <td
              v-if="!pinCombined && descriptions.length > 1"
              class="font-semibold"
              :data-copy="convertGrams(co2eqPhaseSums[phase], 'kg', 'g')"
              data-copy-explanation="CO2eq in g"
            >{{ grams(co2eqPhaseSums[phase], "kg") }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="infos && infos.length" class="text-xs opacity-60 mt-2">
      Click a cell to copy its value. Values are multiplied with the units of each asset.
    </p>
  </div>
  <div class="toast toast-start z-50" v-show="copyToastVisible">
    <div class="alert alert-info py-2">
      <span>Copied <code>{{ copyValue }}</code><span v-if="copyExplanation"> ({{ copyExplanation }})</span></span>
    </div>
  </div>
</template>
