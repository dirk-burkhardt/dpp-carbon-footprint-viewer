<script setup lang="ts">
/**
 * Repository Overview and Asset Selection
 */
import { computed, inject, onMounted, type Ref, ref, watch } from 'vue'
import { externalShellsKey, shellDescriptionsKey } from '@/lib/injectionKeys'
import type { ShellDescriptionSmallInterface } from '@/lib/api/shellTypes'
import { GlobeEuropeAfricaIcon, CheckCircleIcon, ExclamationCircleIcon, ArrowUpTrayIcon } from '@heroicons/vue/24/outline'
import { createUpdateQuery } from '@/lib/util'
import { useRouter } from 'vue-router'
import clients from '@/lib/api/clients'
import type { components } from '@/lib/api/AssetAdministrationShellRepository'
import { toDescriptionsSmall } from '@/lib/api/registry'
import { encodeBase64 } from '@/lib/encoding'
import {
  deleteUpload,
  fetchUploadLimits,
  formatMegabytes,
  isUploadUrl,
  uploadFile,
  uploadIdFromUrl,
  uploadInfos,
  uploadUrl,
  type UploadLimits,
  UploadRequestError,
} from '@/lib/api/uploads'
import { addExternalSource, removeExternalSource } from '@/lib/externalSources'
import { lastAssetTab } from '@/lib/assetSelectionState'
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
// Links back to the asset selection (breadcrumbs) open the same tab again
watch(showExternal, (external) => { lastAssetTab.value = external ? 'external' : 'preloaded' }, { immediate: true });

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
/** Search results within the given shells (one tab), matches in name or ID first */
function searchIn(list: ShellDescriptionSmallInterface[]) {
  if (!searching.value) {
    return [];
  }
  const needle = searchText.value.trim().toLowerCase();
  const attrs = ["id", "name", "globalAssetId", "idShort", "description"] as const;
  return list
    .map((shell) => ({
      shell,
      nameMatch: attrs.some((a) => shell[a]?.toLowerCase().includes(needle)),
      deepHit: deepHits.value?.get(shell.globalAssetId) ?? deepHits.value?.get(shell.id),
    }))
    .filter((r) => r.nameMatch || r.deepHit)
    // Treffer in Name oder ID zuerst
    .sort((a, b) => Number(b.nameMatch) - Number(a.nameMatch));
}
const preloadedResults = computed(() => searchIn(descriptions?.value ?? []));
const externalResults = computed(() => searchIn(Object.values(externalAssets.value)));
// The tabs stay while searching: their counts show the matches, the open tab lists its own matches only
const searchResult = computed(() => (showExternal.value ? externalResults.value : preloadedResults.value));
const otherTabResults = computed(() => (showExternal.value ? preloadedResults.value : externalResults.value).length);
const tabCount = (external: boolean) => searching.value
  ? (external ? externalResults.value : preloadedResults.value).length
  : (external ? Object.keys(externalAssets.value).length : descriptions?.value?.length ?? 0);

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

// Uploads: limits come from the API, null = the API offers no uploads
const uploadLimits = ref<UploadLimits | null>(null);
const uploadInput = ref<HTMLInputElement>();
const uploading = ref(false);
const uploadError = ref<string | null>(null);
onMounted(async () => {
  if (clients.hasAssetAdditionals) {
    uploadLimits.value = await fetchUploadLimits();
  }
});

const retentionText = computed(() => {
  const hours = (uploadLimits.value?.ttlSeconds ?? 0) / 3600;
  return hours >= 1 ? `${Number.isInteger(hours) ? hours : hours.toFixed(1)} h` : `${Math.round(hours * 60)} min`;
});

async function onFileSelected() {
  const file = uploadInput.value?.files?.[0];
  if (!file || !uploadLimits.value) {
    return;
  }
  uploadError.value = null;
  if (file.size > uploadLimits.value.maxBytes) {
    uploadError.value = `${file.name} is larger than ${formatMegabytes(uploadLimits.value.maxBytes)}`;
    uploadInput.value!.value = '';
    return;
  }
  uploading.value = true;
  try {
    const upload = await uploadFile(file);
    const url = uploadUrl(upload.id);
    // Already loaded, App.vue does not need to request the shells again
    if (externalShells) {
      externalShells.value[url] = upload.shells;
    }
    addExternalSource(url, Date.parse(upload.expiresAt));
    await router.push(updateQuery('preload', [...preload.value, encodeBase64(url)]));
  } catch (e) {
    if (e instanceof UploadRequestError && e.status === 413) {
      uploadError.value = `${file.name} is too large`;
    } else if (e instanceof UploadRequestError && e.status === 422) {
      uploadError.value = `${file.name} is not a valid Asset Administration Shell file`;
    } else if (e instanceof UploadRequestError && e.status === 429) {
      uploadError.value = 'Too many uploads, please wait a minute';
    } else {
      console.error(e);
      uploadError.value = `${file.name} could not be uploaded`;
    }
  } finally {
    uploading.value = false;
    uploadInput.value!.value = '';
  }
}

// A link stays listed in this browser until it expires
function onAddLink() {
  if (externalUrl.value.trim()) {
    addExternalSource(externalUrl.value);
  }
  externalUrl.value = '';
}

// Removing a source forgets it in this browser; an uploaded file is also deleted on the server
function onRemoveExternal(url: string) {
  removeExternalSource(url);
  if (isUploadUrl(url)) {
    deleteUpload(uploadIdFromUrl(url)).catch((e) => console.error(e));
  }
}

function externalLabel(url: string) {
  if (!isUploadUrl(url)) {
    return url;
  }
  const info = uploadInfos[uploadIdFromUrl(url)];
  if (!info) {
    return 'Uploaded file';
  }
  const expires = new Date(info.expiresAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  return `${info.filename} (uploaded, deleted on the server at ${expires})`;
}

const shells = computed(() => (showExternal.value ? Object.values(externalAssets.value) : descriptions?.value ?? []));
</script>

<template>
  <div class="flex">
    <div class="grow min-w-0 px-3 md:px-6 py-4" v-if="descriptions">
      <div v-if="searching" class="flex flex-wrap items-center gap-4 mb-3">
        <h2 class="text-lg">
          {{ searchResult.length }} {{ searchResult.length === 1 ? 'shell matches' : 'shells match' }}
          <span class="opacity-70">&bdquo;{{ searchText.trim() }}&ldquo;</span>
          <span v-if="clients.hasAssetAdditionals" class="text-sm opacity-70">in {{ showExternal ? 'external' : 'pre-loaded' }} assets</span>
        </h2>
        <span v-if="deepSearch && deepSearchLoading" class="loading loading-spinner loading-sm"></span>
        <span v-else-if="!deepSearch" class="text-sm opacity-70">Only names and IDs were searched. Turn on &bdquo;Search inside shells&ldquo; to search their contents.</span>
        <span class="grow"></span>
        <button class="btn btn-sm" @click="searchText = ''">Clear search</button>
      </div>
      <template v-if="descriptions">
        <div role="tablist" class="asset-tabs" v-if="clients.hasAssetAdditionals">
          <router-link
            role="tab"
            class="asset-tab"
            :class="{ 'asset-tab-active': !showExternal }"
            :aria-selected="!showExternal"
            :to="updateQuery('assets', null)"
          >
            Pre-loaded assets
            <span class="asset-tab-count">{{ tabCount(false) }}</span>
          </router-link>
          <router-link
            role="tab"
            class="asset-tab"
            :class="{ 'asset-tab-active': showExternal }"
            :aria-selected="showExternal"
            :to="updateQuery('assets', 'external')"
          >
            External assets
            <span class="asset-tab-count">{{ tabCount(true) }}</span>
          </router-link>
        </div>
        <div class="asset-tab-panel flex flex-col px-4 pb-2 border border-t-0 border-base-300" v-if="showExternal">
          <div class="alert alert-warning mt-2">
            <strong>This is a proof-of-concept!</strong> Do not load shells with classified information that may not become public. This demo was not developed with information security as a priority.
          </div>
          <div class="label py-2">
            <span class="text-sm">
              Add a link to any <code>.aasx</code>, <code>.aas.json</code>, or <code>.aas.xml</code><template v-if="uploadLimits">
              or upload such a file (up to {{ formatMegabytes(uploadLimits.maxBytes) }}, kept on the server for
              {{ retentionText }})</template> and select its assets afterwards
            </span>
          </div>
          <div class="flex flex-wrap items-center gap-3">
            <label class="input flex items-center gap-2 grow w-full md:w-auto md:min-w-80">
              <GlobeEuropeAfricaIcon class="w-6 h-6 opacity-70" />
              <input type="url" class="grow peer" placeholder="https://..." v-model="externalUrl">
              <router-link
                class="btn btn-sm btn-primary p-2"
                :disabled="externalUrl.length ? undefined : 'disabled'"
                :to="updateQuery('preload', [...preload, encodeBase64(externalUrl)])"
                @click="onAddLink"
              >
                Load external assets
              </router-link>
            </label>
            <template v-if="uploadLimits">
              <span class="text-sm opacity-70">or</span>
              <input
                ref="uploadInput"
                type="file"
                class="hidden"
                accept=".aasx,.json,.xml"
                @change="onFileSelected"
              >
              <button type="button" class="btn btn-primary btn-outline" :disabled="uploading" @click="uploadInput?.click()">
                <span v-if="uploading" class="loading loading-spinner loading-sm"></span>
                <ArrowUpTrayIcon v-else class="w-5 h-5" />
                Upload file
              </button>
            </template>
          </div>
          <p v-if="uploadError" class="text-error text-sm mt-2">{{ uploadError }}</p>
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
                {{ externalLabel(url as string) }}: <strong>{{ asset === null ? 'Loading...' : typeof asset === 'string' ? asset : 'Loaded. Select assets below' }}</strong>
              </span>
              <router-link class="btn btn-outline btn-sm" :to="removeExternalUrlRoute(url as string)" @click="onRemoveExternal(url as string)">
                {{ asset && typeof asset === 'object' ? 'Remove' : 'Hide' }}
              </router-link>
            </li>
          </ul>
        </div>
        <div
          class="grid grid-cols-[repeat(auto-fill,minmax(15rem,1fr))] gap-4 p-4 border border-base-300"
          :class="clients.hasAssetAdditionals ? 'asset-tab-panel border-t-0' : 'bg-base-200/30'"
          v-if="searching ? searchResult.length : shells.length"
        >
          <template v-if="searching">
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
          </template>
          <template v-else>
            <AssetGridCard v-for="shell in shells" :key="shell.globalAssetId" :shell="shell" />
          </template>
        </div>
        <p
          v-else-if="searching && !(deepSearch && deepSearchLoading)"
          class="text-center italic py-8 border border-base-300"
          :class="clients.hasAssetAdditionals ? 'asset-tab-panel border-t-0' : ''"
        >
          No shells in this tab match the search<template v-if="otherTabResults">, but {{ otherTabResults }} in the other tab</template>.
        </p>
      </template>
    </div>
    <!-- Favourites, Compare and Datasheet need a large screen; on small screens only the asset list is shown -->
    <aside class="hidden md:flex w-80 2xl:w-96 shrink-0 sticky top-14 h-[calc(100vh-3.5rem)] flex-col">
      <FavoritesBox class="grow min-h-0" :shells-by-id="shellsById" />
      <div class="shrink-0 flex items-center justify-end px-4 py-3 border-l border-t border-base-300 bg-base-200/60">
        <StatusIndicator small />
      </div>
    </aside>
  </div>
</template>

<style scoped>
@reference "@/assets/main.css";

/*
 * Tabs: the active tab has the colour of the panel below it and merges with it, inactive tabs stay in the page
 * colour with muted text. The colour mix works for the light and the dark theme alike.
 */
.asset-tab-panel {
  background-color: color-mix(in oklab, var(--color-base-200) 55%, var(--color-base-100));
}

.asset-tabs {
  @apply flex items-end gap-1 border-b border-base-300;
}

.asset-tab {
  @apply relative -mb-px flex items-center gap-2 px-3 md:px-5 py-2.5 rounded-t-sm border border-b-0 border-base-300
    bg-base-100 text-base-content/60 transition-colors;

  &:hover {
    @apply text-base-content bg-base-200/60;
  }
}

.asset-tab-active {
  @apply text-base-content font-semibold;
  background-color: color-mix(in oklab, var(--color-base-200) 55%, var(--color-base-100));
  /* Coloured top edge; the bottom edge in panel colour covers the border of the tab list */
  box-shadow:
    inset 0 3px 0 var(--color-primary),
    0 1px 0 color-mix(in oklab, var(--color-base-200) 55%, var(--color-base-100));

  &:hover {
    background-color: color-mix(in oklab, var(--color-base-200) 55%, var(--color-base-100));
  }
}

.asset-tab-count {
  @apply text-xs font-normal opacity-70;
}
</style>
