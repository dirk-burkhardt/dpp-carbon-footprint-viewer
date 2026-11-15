<script setup lang="ts">
/**
 * Repository Overview and Asset Selection
 */
import { computed, inject, type Ref, ref } from 'vue'
import { externalShellsKey, shellDescriptionsKey } from '@/lib/injectionKeys'
import type { ShellDescriptionSmallInterface } from '@/lib/api/shellTypes'
import { GlobeEuropeAfricaIcon, CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/vue/24/outline'
import { createUpdateQuery } from '@/lib/util'
import { useRouter } from 'vue-router'
import clients from '@/lib/api/clients'
import type { components } from '@/lib/api/AssetAdministrationShellRepository'
import { toDescriptionsSmall } from '@/lib/api/registry'
import { encodeBase64 } from '@/lib/encoding'
import AssetGridCard from '@/components/AssetGridCard.vue'
import FavoritesBox from '@/components/FavoritesBox.vue'
import StatusIndicator from '@/components/layout/StatusIndicator.vue'
import { deepHits, deepSearch, deepSearchLoading, searchText, type DeepSearchHit } from '@/lib/search'

const descriptions = inject<Ref<ShellDescriptionSmallInterface[]>>(shellDescriptionsKey)

const router = useRouter();
const updateQuery = createUpdateQuery(router);

// Whether to show the external window
const showExternal = computed(() => clients.hasAssetAdditionals && router.currentRoute.value.query.assets === "external");
const externalUrl = ref("");

const externalShells = inject<Ref<{ [url: string]: null | string | components["schemas"]["AssetAdministrationShell"][] }>>(externalShellsKey);
const externalAssets = computed<{[globalAssetId: string]: ShellDescriptionSmallInterface}>(() => {
  return Object.fromEntries(
    toDescriptionsSmall(
      Object.values(externalShells?.value || {})
      .filter(Array.isArray)
      .flat()
    ).map((s) => [s.globalAssetId, s])
  )
});

// Alle bekannten Shells (vorgeladene und externe) je globalAssetId
const allShells = computed(() => [...(descriptions?.value || []), ...Object.values(externalAssets.value)]);
const shellsById = computed(() => Object.fromEntries(allShells.value.map((s) => [s.globalAssetId, s])));

// Suche über den Header
const searching = computed(() => searchText.value.trim().length > 0);
const searchResult = computed(() => {
  if (!searching.value) {
    return [];
  }
  const needle = searchText.value.trim().toLowerCase();
  const attrs = ["id", "name", "globalAssetId", "idShort", "description"] as const;
  return allShells.value
    .map((shell) => ({
      shell,
      nameMatch: attrs.some((a) => shell[a]?.toLowerCase().includes(needle)),
      deepHit: deepHits.value?.get(shell.globalAssetId) ?? deepHits.value?.get(shell.id),
    }))
    .filter((r) => r.nameMatch || r.deepHit)
    // Treffer in Name oder ID zuerst
    .sort((a, b) => Number(b.nameMatch) - Number(a.nameMatch));
})

// Fundstellen innerhalb der Schale; passt schon der Name, sind Treffer in den Shell-Angaben selbst überflüssig
function matchLabel(hit: DeepSearchHit, nameMatch: boolean) {
  return hit.matches
    .filter((m) => !nameMatch || m.submodel !== null)
    .map((m) => ({
      where: [m.submodel ?? "Shell", m.path].filter(Boolean).join(" › "),
      text: m.text.length > 120 ? `${m.text.slice(0, 117)}...` : m.text,
    }));
}

// Shells to preload
const preload = computed(() => {
  let queryPreload = router.currentRoute.value.query.preload;
  if (!queryPreload) {
    queryPreload = [];
  }
  if (!Array.isArray(queryPreload)) {
    queryPreload = [queryPreload];
  }
  return queryPreload as string[];
})

function removeExternalUrlRoute(url: string) {
  url = encodeBase64(url);
  return updateQuery('preload', preload.value.filter(u => u !== url));
}

const shells = computed(() => (showExternal.value ? Object.values(externalAssets.value) : descriptions?.value ?? []));
</script>

<template>
  <div class="flex">
    <div class="grow min-w-0 px-6 py-4" v-if="descriptions">
      <template v-if="searching">
        <div class="flex items-center gap-4 mb-3">
          <h2 class="text-lg">
            {{ searchResult.length }} {{ searchResult.length === 1 ? 'shell matches' : 'shells match' }}
            <span class="opacity-70">&bdquo;{{ searchText.trim() }}&ldquo;</span>
          </h2>
          <span v-if="deepSearch && deepSearchLoading" class="loading loading-spinner loading-sm"></span>
          <span v-else-if="!deepSearch" class="text-sm opacity-70">Only names and IDs were searched. Turn on &bdquo;Search inside shells&ldquo; to search their contents.</span>
          <span class="grow"></span>
          <button class="btn btn-sm" @click="searchText = ''">Clear search</button>
        </div>
        <div class="grid grid-cols-[repeat(auto-fill,minmax(15rem,1fr))] gap-4 pb-4" v-if="searchResult.length > 0">
          <AssetGridCard v-for="r of searchResult" :key="r.shell.globalAssetId" :shell="r.shell">
            <div v-if="r.deepHit && matchLabel(r.deepHit, r.nameMatch).length" class="text-xs border-t border-base-300 pt-2 mt-1 space-y-1">
              <div v-for="(m, i) of matchLabel(r.deepHit, r.nameMatch)" :key="i" class="break-words">
                <span class="opacity-60">{{ m.where }}:</span> {{ m.text }}
              </div>
              <div v-if="r.deepHit.total > r.deepHit.matches.length" class="opacity-60">
                and {{ r.deepHit.total - r.deepHit.matches.length }} more
              </div>
            </div>
          </AssetGridCard>
        </div>
        <p v-else-if="!(deepSearch && deepSearchLoading)" class="text-center italic py-8">No shells match the search.</p>
      </template>
      <template v-else>
        <div role="tablist" class="tabs tabs-lift" v-if="clients.hasAssetAdditionals">
          <router-link role="tab" class="tab" :class="{'tab-active': !showExternal}" :to="updateQuery('assets', null)">Pre-loaded assets</router-link>
          <router-link role="tab" class="tab" :class="{'tab-active': showExternal}" :to="updateQuery('assets', 'external')">External assets</router-link>
        </div>
        <div class="flex flex-col bg-base-200/30 px-2 border border-t-0 border-base-300" v-if="showExternal">
          <div class="alert alert-warning mt-2">
            <strong>This is a proof-of-concept!</strong> Do not load shells with classified information that may not become public. This demo was not developed with information security as a priority.
          </div>
          <div class="label py-2">
            <span class="text-sm">Add a link to any <code>.aasx</code>, <code>.aas.json</code>, or <code>.aas.xml</code> and select its assets afterwards</span>
          </div>
          <label class="input flex items-center gap-2">
            <GlobeEuropeAfricaIcon class="w-6 h-6 opacity-70" />
            <input type="url" class="grow peer" placeholder="https://..." v-model="externalUrl">
            <router-link
              class="btn btn-sm btn-primary p-2"
              :disabled="externalUrl.length ? undefined : 'disabled'"
              :to="updateQuery('preload', [...preload, encodeBase64(externalUrl)])"
              @click="externalUrl = ''"
            >
              Load external assets
            </router-link>
          </label>
          <ul class="my-1">
            <li
              v-for="(asset, url) of externalShells"
              :key="url"
              class="flex gap-2 my-1 p-4 bg-base-200 transition-all duration-300"
              :class="{
                'text-error': typeof asset === 'string',
                'text-success': asset && typeof asset === 'object'
              }"
            >
              <div class="relative w-7 h-7">
                <span class="loading loading-spinner loading-md"></span>
                <ExclamationCircleIcon v-show="typeof asset === 'string'" class="w-full h-full -top-0.5 -left-0.5 absolute inset-0 z-10 bg-base-100 rounded-full animate-[ping-reverse_.3s_ease-in-out_forwards]" />
                <CheckCircleIcon v-show="asset !== null && typeof asset === 'object'" class="w-full h-full -top-0.5 -left-0.5 absolute inset-0 z-10 bg-base-100 rounded-full animate-[ping-reverse_.3s_ease-in-out_forwards]" />
              </div>
              <span class="grow">
                {{ url }}: <strong>{{ asset === null ? 'Loading...' : typeof asset === 'string' ? asset : 'Loaded. Select assets below' }}</strong>
              </span>
              <router-link class="btn btn-outline btn-sm" :to="removeExternalUrlRoute(url as string)">
                {{ asset && typeof asset === 'object' ? 'Remove' : 'Hide' }}
              </router-link>
            </li>
          </ul>
        </div>
        <div
          class="grid grid-cols-[repeat(auto-fill,minmax(15rem,1fr))] gap-4 p-4 bg-base-200/30 border border-base-300"
          :class="{ 'border-t-0': clients.hasAssetAdditionals }"
          v-if="shells.length"
        >
          <AssetGridCard v-for="shell in shells" :key="shell.globalAssetId" :shell="shell" />
        </div>
      </template>
    </div>
    <aside class="w-80 2xl:w-96 shrink-0 sticky top-14 h-[calc(100vh-3.5rem)] flex flex-col">
      <FavoritesBox class="grow min-h-0" :shells-by-id="shellsById" />
      <div class="shrink-0 flex items-center justify-end px-4 py-3 border-l border-t border-base-300 bg-base-200/60">
        <StatusIndicator small />
      </div>
    </aside>
  </div>
</template>
