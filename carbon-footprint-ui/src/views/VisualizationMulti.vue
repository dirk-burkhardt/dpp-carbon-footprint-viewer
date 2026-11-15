<script setup lang="ts">
/**
 * This file is currently not being used.
 * It contains the basic setup for loading and comparing multiple assets.
 * DatasheetComparison.vue encompasses a similar setup which is currently being used.
 */
import { useRoute, useRouter } from 'vue-router'
import shellRepo from '@/lib/api/shells'
import { ref, watch } from 'vue'
import { CubeIcon, CubeTransparentIcon } from '@heroicons/vue/24/outline'
import { generateColor, pretend } from '@/lib/util'
import AssetSelection from '@/components/AssetSelection.vue'
import type { components } from '@/lib/api/AssetAdministrationShellRepository'
import { BackOnErrorHandler, currentLoadError } from '@/lib/BackOnErrorHandler'
import LoadFailed from '@/components/layout/LoadFailed.vue'
import BreadcrumbsBar from '@/components/BreadcrumbsBar.vue'
import { encodeBase64 } from '@/lib/encoding'

const route = useRoute();
const router = useRouter();
type Asset = components["schemas"]["AssetAdministrationShell"]
const assets = ref<(Asset | Asset[])[]>([]);
watch(() => route.params.assets as string[], async (newAssets) => {
  assets.value = structuredClone(await BackOnErrorHandler.bind(shellRepo.multiSourceShells(newAssets, "url-"), (e) => {
    return e.status === 422 ? "The URL to at least one asset is invalid or does not point to a valid asset" : "An error occurred while loading the assets";
  }));
}, { immediate: true });

function changeUrl(asset: Asset, _: any, __: any, index: number) {
  const assets = [...route.params.assets as string[]];
  assets[index] = encodeBase64(asset.id);
  pretend(router, { params: { assets }});
}
</script>

<template>
  <BreadcrumbsBar class="mt-1.5 ml-4" />
  <LoadFailed v-if="currentLoadError" :message="currentLoadError" />
  <div class="grid gap-4 m-4 grid-cols-2" v-else>
    <AssetSelection v-model="assets" class="gap-4 grid grid-cols-1 p-4 border border-1 rounded-lg" @change="changeUrl">
      <template v-slot="{ asset, description }">
        <CubeTransparentIcon v-if="description.assetKind === 'Type'" class="size-8 rounded-sm inline-block p-1 text-gray-800" :style="`background: ${generateColor(asset.id)}`" />
        <CubeIcon v-else class="size-8 rounded-sm inline-block p-1 text-gray-800" :style="`background: ${generateColor(asset.id)}`" />
        <div>
          <h1 class="col col-span-2 text-2xl">
            {{ description.name }}
          </h1>
          <h2 v-if="description.idShort" class="col-span-2 font-mono text-sm">{{ description.idShort
            }}</h2>
          <p class="pt-3 ital" v-if="description.description">{{ description.description }}</p>
        </div>
      </template>
    </AssetSelection>
  </div>
</template>
