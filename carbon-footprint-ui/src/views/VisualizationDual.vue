<script setup lang="ts">
/**
 * Asset Comparison Analysis (Konzept der Thesis, Abschnitt 4.2.4).
 *
 * Vergleicht zwei Assets in einem Balkendiagramm mit zwei Richtungen um eine Nulllinie: links das erste,
 * rechts das zweite Asset. Wahlweise Absolutwerte (je Kennzahl zwei Balken) oder nur die Differenz (ein Balken
 * auf der Seite des Assets mit dem höheren Wert). Kategorien: Gesamt, Transport und Produkt je
 * Lebenszyklusphase. Gefahrstoffe und kritische Materialien sind im Prototyp nicht enthalten.
 *
 * Alternatively both bars of a row are drawn side by side in one direction (grouped bar chart).
 */
import { useRoute } from 'vue-router'
import { computed, inject, type Ref } from 'vue'
import { computedAsync } from '@vueuse/core'
import { ArrowTopRightOnSquareIcon } from '@heroicons/vue/24/outline'
import { grams, loadFullAssetInfo, percent, simulationFromRoute } from '@/lib/util'
import { BackOnErrorHandler, currentLoadError } from '@/lib/BackOnErrorHandler'
import { AssetIdMap } from '@/lib/AssetIdMap'
import { assetIdMapKey } from '@/lib/injectionKeys'
import { storageRef } from '@/lib/storage'
import { encodeBase64 } from '@/lib/encoding'
import { ErrorClient } from '@/lib/ErrorDataHandler'
import { co2eqByLifeCyclePhases, sortPhases, type Carbon } from '@/lib/carbonValues'
import { LifeCyclePhases, lifeCyclePhaseDescription, type LifeCyclePhase } from '@/lib/lifeCycleUtil'
import BreadcrumbsBar from '@/components/BreadcrumbsBar.vue'
import LoadFailed from '@/components/layout/LoadFailed.vue'
import type { ApiIndicators } from '@/lib/api/products'
import { referenceLabels, referenceMeasure, type ReferenceQuantity } from '@/lib/keyFigures'

const route = useRoute();
const idMap = inject<Ref<AssetIdMap>>(assetIdMapKey);

const infos = computedAsync(async () => {
  if (!idMap?.value) {
    return undefined;
  }
  const { first, second } = route.params;
  // Route already changed while leaving the view
  if (typeof first !== 'string' || typeof second !== 'string') {
    return undefined;
  }
  const data = ([first as string, second as string] as const).map((a) => BackOnErrorHandler.bind(
    loadFullAssetInfo(a, idMap.value, "url-", (title, details, source) => ErrorClient.warn(title, details, source ? { source } : undefined), simulationFromRoute(route)),
    (e) => e.status === 422
      ? "The URL to an asset is invalid or does not point to a valid asset"
      : "The assets could not be loaded for the comparison"
  ));
  return Promise.all(data);
}, undefined)

type Side = { name: string, globalAssetId: string, carbon: Carbon | undefined, indicators: ApiIndicators | null }
const sides = computed<[Side, Side] | undefined>(() => {
  if (!infos.value) {
    return undefined;
  }
  const [a, b] = infos.value.map((i) => ({
    name: i.description?.name ?? i.asset.idShort ?? i.asset.id,
    globalAssetId: i.asset.assetInformation.globalAssetId ?? i.asset.id,
    carbon: i.carbonTree ?? i.carbonFootprint,
    indicators: i.indicators,
  }));
  return [a, b];
});
const missingData = computed(() => sides.value?.filter((s) => !s.carbon).map((s) => s.name) ?? []);

// Darstellung
const mode = storageRef<'absolute' | 'difference'>('compareMode', 'absolute');
const scalePerRow = storageRef<boolean>('compareScalePerRow', false);
// "opposed": bars grow in two directions around a zero line; "grouped": both bars side by side in one direction
const layout = storageRef<'opposed' | 'grouped'>('compareLayout', 'opposed');
// Absolute values or CO2eq per kg / per watt (reference quantities from Technical Data)
const reference = storageRef<'absolute' | ReferenceQuantity>('compareReference', 'absolute');
const referenceAvailable = (quantity: ReferenceQuantity) =>
  !!sides.value?.every((s) => (referenceMeasure(s.indicators, quantity)?.value ?? 0) > 0);
const activeReference = computed<'absolute' | ReferenceQuantity>(() =>
  reference.value !== 'absolute' && referenceAvailable(reference.value) ? reference.value : 'absolute');
const referenceNote = computed(() => {
  const q = activeReference.value;
  if (q === 'absolute' || !sides.value) {
    return undefined;
  }
  const { unit } = referenceLabels[q];
  const values = sides.value.map((s) => `${s.name} ${Math.round(referenceMeasure(s.indicators, q)!.value * 1000) / 1000} ${unit}`);
  return `Values per ${unit}, ${q} from Technical Data: ${values.join(', ')}.`;
});
/** Divisor of each side for the chosen reference */
const divisors = computed(() => sides.value?.map((s) =>
  activeReference.value === 'absolute' ? 1 : referenceMeasure(s.indicators, activeReference.value)!.value) ?? [1, 1]);

type Row = { key: string, label: string, title?: string, group: string, a: number, b: number, strong?: boolean }
const rows = computed<Row[]>(() => {
  if (!sides.value) {
    return [];
  }
  const [a, b] = sides.value.map((s) => s.carbon);
  const [da, db] = divisors.value;
  const result: Row[] = [
    { key: 'total', label: 'Total', group: 'Total', a: a?.totalCo2eq ?? 0, b: b?.totalCo2eq ?? 0, strong: true },
    { key: 'transport', label: 'Transport', group: 'Transport Carbon Footprint', a: a?.transportCo2eq ?? 0, b: b?.transportCo2eq ?? 0, strong: true },
    { key: 'product', label: 'Product (all phases)', group: 'Product Carbon Footprint', a: a?.productCo2eq ?? 0, b: b?.productCo2eq ?? 0, strong: true },
  ];
  const phasesA = a ? co2eqByLifeCyclePhases(a) : {};
  const phasesB = b ? co2eqByLifeCyclePhases(b) : {};
  for (const phase of sortPhases([...new Set([...Object.keys(phasesA), ...Object.keys(phasesB)])])) {
    result.push({
      key: `phase-${phase}`,
      label: phase,
      title: lifeCyclePhaseDescription[phase as LifeCyclePhase],
      group: 'Product Carbon Footprint',
      a: phasesA[phase] ?? 0,
      b: phasesB[phase] ?? 0,
    });
  }
  return result.map((r) => ({ ...r, a: r.a / da, b: r.b / db }));
});

const globalMax = computed(() => Math.max(
  0,
  ...rows.value.map((r) => (mode.value === 'absolute' ? Math.max(r.a, r.b) : Math.abs(r.a - r.b)))
));

/** Balkenbreiten in Prozent der halben Breite */
function widths(row: Row) {
  const rowMax = mode.value === 'absolute' ? Math.max(row.a, row.b) : Math.abs(row.a - row.b);
  const max = scalePerRow.value ? rowMax : globalMax.value;
  if (max <= 0) {
    return { a: 0, b: 0 };
  }
  if (mode.value === 'absolute') {
    return { a: (row.a / max) * 100, b: (row.b / max) * 100 };
  }
  const diff = row.a - row.b;
  return { a: diff > 0 ? (diff / max) * 100 : 0, b: diff < 0 ? (-diff / max) * 100 : 0 };
}

/** Bar width in the grouped layout; leaves room for the value label to the right of the longest bar */
function groupedWidth(percentOfMax: number) {
  return `calc(${percentOfMax}% - 9rem * ${percentOfMax / 100})`;
}

function format(value: number) {
  const text = grams(value, 'kg');
  return activeReference.value === 'absolute' ? text : `${text} ${referenceLabels[activeReference.value].per}`;
}

function relative(row: Row) {
  const higher = Math.max(row.a, row.b);
  return higher > 0 ? percent(Math.abs(row.a - row.b) / higher) : '';
}

const groups = computed(() => {
  const result: { name: string, rows: Row[] }[] = [];
  for (const row of rows.value) {
    const last = result[result.length - 1];
    if (last?.name === row.group) {
      last.rows.push(row);
    } else {
      result.push({ name: row.group, rows: [row] });
    }
  }
  return result;
});

// Zusammenfassung: welches Asset hat insgesamt weniger Emissionen
const summary = computed(() => {
  const total = rows.value[0];
  if (!sides.value || !total || (total.a === 0 && total.b === 0)) {
    return undefined;
  }
  if (total.a === total.b) {
    return 'Both assets have the same total carbon footprint.';
  }
  const [lower, higher] = total.a < total.b ? [sides.value[0], sides.value[1]] : [sides.value[1], sides.value[0]];
  const per = activeReference.value === 'absolute' ? '' : ` ${referenceLabels[activeReference.value].per}`;
  return `${lower.name} emits ${relative(total)} less CO2eq in total${per} than ${higher.name} (${format(Math.abs(total.a - total.b))} difference).`;
});

// Abgedeckte Lebenszyklusphasen: unterschiedliche Abdeckung verzerrt den Vergleich
const coveredPhases = computed(() => sides.value?.map((s) => s.carbon?.coveredLifeCyclePhases as LifeCyclePhases | undefined));
const coverageDiffers = computed(() => {
  const [a, b] = coveredPhases.value ?? [];
  return !!a && !!b && a.toString() !== b.toString();
});
</script>

<template>
  <div class="px-4 py-1">
    <BreadcrumbsBar />
  </div>
  <LoadFailed v-if="currentLoadError" :message="currentLoadError" />
  <div v-else-if="!sides" class="px-6 py-4">
    <div class="skeleton h-12 w-full mb-4"></div>
    <div class="skeleton h-96 w-full"></div>
  </div>
  <div v-else class="px-6 pb-16">
    <!-- Kopf: beide Assets -->
    <div class="grid grid-cols-[1fr_12rem_1fr] items-end gap-4 py-3">
      <router-link
        :to="{ name: 'visualization.single', params: { asset: encodeBase64(sides[0].globalAssetId) } }"
        class="text-right text-xl hover:underline"
        title="Open asset"
      >
        <span class="inline-block w-3 h-3 rounded-sm compare-a mr-2"></span>{{ sides[0].name }}
        <ArrowTopRightOnSquareIcon class="inline h-4 opacity-60" />
      </router-link>
      <div class="text-center text-sm opacity-70">CO2eq</div>
      <router-link
        :to="{ name: 'visualization.single', params: { asset: encodeBase64(sides[1].globalAssetId) } }"
        class="text-xl hover:underline"
        title="Open asset"
      >
        <span class="inline-block w-3 h-3 rounded-sm compare-b mr-2"></span>{{ sides[1].name }}
        <ArrowTopRightOnSquareIcon class="inline h-4 opacity-60" />
      </router-link>
    </div>

    <div class="flex flex-wrap items-center gap-6 py-2 border-y border-base-300">
      <div class="join">
        <button type="button" class="btn btn-sm join-item" :class="{ 'btn-primary': mode === 'absolute' }" @click="mode = 'absolute'">Absolute values</button>
        <button type="button" class="btn btn-sm join-item" :class="{ 'btn-primary': mode === 'difference' }" @click="mode = 'difference'">Difference</button>
      </div>
      <div class="join" title="Arrangement of the bars">
        <button type="button" class="btn btn-sm join-item" :class="{ 'btn-primary': layout === 'opposed' }" @click="layout = 'opposed'">Opposed bars</button>
        <button type="button" class="btn btn-sm join-item" :class="{ 'btn-primary': layout === 'grouped' }" @click="layout = 'grouped'">Bars side by side</button>
      </div>
      <div class="join" title="Absolute values or CO2eq per unit of a reference quantity from Technical Data, so assets of different size become comparable">
        <button type="button" class="btn btn-sm join-item" :class="{ 'btn-primary': activeReference === 'absolute' }" @click="reference = 'absolute'">Absolute</button>
        <button
          v-for="q of (['mass', 'power'] as const)"
          :key="q"
          type="button"
          class="btn btn-sm join-item"
          :class="{ 'btn-primary': activeReference === q }"
          :disabled="!referenceAvailable(q)"
          :title="referenceAvailable(q) ? undefined : `Technical Data of at least one asset contains no ${referenceLabels[q].name}`"
          @click="reference = q"
        >{{ referenceLabels[q].per }}</button>
      </div>
      <label class="flex items-center gap-2 text-sm cursor-pointer" title="Each row uses its own scale, so small values become visible">
        <input v-model="scalePerRow" type="checkbox" class="toggle toggle-sm" />
        Scale each row separately
      </label>
      <span class="grow"></span>
      <span v-if="summary" class="text-sm">{{ summary }}</span>
    </div>

    <p v-if="referenceNote" class="text-sm mt-3">{{ referenceNote }}</p>
    <p v-if="missingData.length" class="text-sm mt-3">
      No carbon footprint data for {{ missingData.join(' and ') }}. Its values are shown as zero.
    </p>
    <p v-if="coverageDiffers" class="text-sm mt-3">
      The assets cover different life cycle phases ({{ coveredPhases?.[0] }} and {{ coveredPhases?.[1] }}),
      so totals are only comparable to a limited extent.
    </p>

    <!-- Diagramm: Balken in zwei Richtungen -->
    <div class="mt-4" v-if="layout === 'opposed'">
      <template v-for="group of groups" :key="group.name">
        <h3 v-if="group.name !== 'Total'" class="text-center text-sm font-semibold mt-5 mb-1 opacity-80">{{ group.name }}</h3>
        <div
          v-for="row of group.rows"
          :key="row.key"
          class="grid grid-cols-[1fr_12rem_1fr] items-center gap-0 h-8 hover:bg-base-200/60"
          :title="mode === 'difference' && row.a !== row.b ? `Difference ${format(Math.abs(row.a - row.b))} (${relative(row)})` : undefined"
        >
          <!-- erstes Asset: Balken wächst nach links -->
          <div class="flex justify-end items-center h-full border-r border-base-content/40">
            <span v-if="mode === 'absolute' || row.a > row.b" class="text-xs mr-2 whitespace-nowrap">
              {{ mode === 'absolute' ? format(row.a) : `+${format(row.a - row.b)}` }}
            </span>
            <div class="h-5 compare-a rounded-l-sm transition-all duration-300" :style="{ width: `calc(${widths(row).a}% - 5rem * ${widths(row).a / 100})` }"></div>
          </div>
          <div class="text-center text-sm px-2 truncate" :class="{ 'font-semibold': row.strong }" :title="row.title">{{ row.label }}</div>
          <!-- zweites Asset: Balken wächst nach rechts -->
          <div class="flex items-center h-full border-l border-base-content/40">
            <div class="h-5 compare-b rounded-r-sm transition-all duration-300" :style="{ width: `calc(${widths(row).b}% - 5rem * ${widths(row).b / 100})` }"></div>
            <span v-if="mode === 'absolute' || row.b > row.a" class="text-xs ml-2 whitespace-nowrap">
              {{ mode === 'absolute' ? format(row.b) : `+${format(row.b - row.a)}` }}
            </span>
          </div>
        </div>
      </template>
    </div>
    <!-- Grouped bar chart: both assets per row next to each other, growing to the right -->
    <div class="mt-4" v-else>
      <template v-for="group of groups" :key="group.name">
        <h3 v-if="group.name !== 'Total'" class="text-sm font-semibold mt-5 mb-1 opacity-80 grouped-heading">{{ group.name }}</h3>
        <div
          v-for="row of group.rows"
          :key="row.key"
          class="grid grid-cols-[12rem_1fr] items-center hover:bg-base-200/60 py-1"
          :title="mode === 'difference' && row.a !== row.b ? `Difference ${format(Math.abs(row.a - row.b))} (${relative(row)})` : undefined"
        >
          <div class="text-right text-sm pr-3 truncate" :class="{ 'font-semibold': row.strong }" :title="row.title">{{ row.label }}</div>
          <div class="flex flex-col justify-center gap-0.5 min-h-8 border-l border-base-content/40">
            <template v-if="mode === 'absolute'">
              <div class="flex items-center h-3.5">
                <div class="h-full compare-a rounded-r-sm transition-all duration-300" :style="{ width: groupedWidth(widths(row).a) }"></div>
                <span class="text-xs ml-2 whitespace-nowrap">{{ format(row.a) }}</span>
              </div>
              <div class="flex items-center h-3.5">
                <div class="h-full compare-b rounded-r-sm transition-all duration-300" :style="{ width: groupedWidth(widths(row).b) }"></div>
                <span class="text-xs ml-2 whitespace-nowrap">{{ format(row.b) }}</span>
              </div>
            </template>
            <div v-else class="flex items-center h-5">
              <div
                class="h-full rounded-r-sm transition-all duration-300"
                :class="row.a > row.b ? 'compare-a' : 'compare-b'"
                :style="{ width: groupedWidth(Math.max(widths(row).a, widths(row).b)) }"
              ></div>
              <span v-if="row.a !== row.b" class="text-xs ml-2 whitespace-nowrap">
                +{{ format(Math.abs(row.a - row.b)) }} {{ row.a > row.b ? sides[0].name : sides[1].name }}
              </span>
            </div>
          </div>
        </div>
      </template>
    </div>
    <p class="text-xs opacity-60 mt-4">
      <template v-if="mode === 'absolute'">Bars show the CO2eq of each asset. </template>
      <template v-else-if="layout === 'opposed'">A bar points to the asset with the higher value and shows by how much it is higher. </template>
      <template v-else>A bar in the colour of the asset with the higher value shows by how much it is higher. </template>
      <template v-if="scalePerRow">Each row is scaled separately, bar lengths can only be compared within a row.</template>
      <template v-else>All rows use the same scale.</template>
    </p>
  </div>
</template>

<style scoped>
.compare-a {
  background-color: #4e79a7;
}
.compare-b {
  background-color: #f28e2b;
}
.grouped-heading {
  padding-left: 12.75rem;
}
</style>
