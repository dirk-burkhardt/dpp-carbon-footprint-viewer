<script setup lang="ts">
import { RouterView, useRouter } from 'vue-router'
import ErrorLog from '@/components/ErrorLog.vue'
import LogoSVG from '@/assets/CLiCE-DiPP.svg'
import { storageRef } from '@/lib/storage'
import { type Component, computed, provide, ref, watch } from 'vue'
import { allDescriptionsFromApi } from '@/lib/api/registry'
import { ErrorClient } from '@/lib/ErrorDataHandler'
import { darkModeKey, shellDescriptionsKey, assetIdMapKey, externalShellsKey, helpBarKey } from '@/lib/injectionKeys'
import BackOnError from '@/components/BackOnError.vue'
import { computedAsync } from '@vueuse/core'
import { AssetIdMap } from '@/lib/AssetIdMap'
import shellRepo from '@/lib/api/shells'
import type { components } from '@/lib/api/AssetAdministrationShellRepository'
import { ArrowLeftIcon } from '@heroicons/vue/24/outline'
import GlobalContextMenuComponent from '@/components/GlobalContextMenuComponent.vue'
import HelpBar from '@/components/HelpBar.vue'
import { decodeBase64 } from '@/lib/encoding'


const router = useRouter();

// Theming
const lightThemeName = "corporate";
const darkThemeName = "business";
const useDarkTheme = storageRef<boolean>("darkTheme", window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)").matches : false);
provide(darkModeKey, useDarkTheme);
watch(useDarkTheme, () => {
  document.documentElement.dataset.theme = useDarkTheme.value ? darkThemeName : lightThemeName;
}, { immediate: true });

// Shell information
const shellDescriptions = computedAsync(
  async () => allDescriptionsFromApi(),
  [],
  { onError(e: any) { ErrorClient.add(e.toString()) } })
provide(shellDescriptionsKey, shellDescriptions);

// AAS information
const assetIdMap = ref(new AssetIdMap());
watch(shellDescriptions, (descriptions) => {
  for (const description of descriptions) {
    assetIdMap.value.add({
      id: description.id,
      idShort: description.idShort,
      globalAssetId: description.globalAssetId,
    })
  }
})
provide(assetIdMapKey, assetIdMap);

const externalShells = ref<{ [url: string]: null | string | components["schemas"]["AssetAdministrationShell"][] }>({});  // null = loading, string = error message, otherwise the shell
provide(externalShellsKey, externalShells);

// Load one or more external shells if a preload-query is present
watch(() => router.currentRoute.value.query.preload, (encodedUrls) => {
  encodedUrls = encodedUrls || [];
  const urls = ((Array.isArray(encodedUrls) ? encodedUrls : [encodedUrls]) as string[]).map(decodeBase64);
  const removeUrls = new Set(Object.keys(externalShells.value));
  for (const url of urls) {
    if (url in externalShells.value) {
      removeUrls.delete(url);
       
      continue;
    }
    externalShells.value[url] = null;
    shellRepo.externalShell(url).then((assets) => {
      if (assets && Array.isArray(assets)) {
        for (const asset of assets) {
          assetIdMap?.value.add({
            id: asset.id,
            idShort: asset.idShort,
            globalAssetId: asset.assetInformation.globalAssetId,
            specificAssetIds: asset.assetInformation.specificAssetIds?.map((i) => i.value)
          })
        }
        externalShells.value[url] = assets;
      }
    }).catch((e) => {
      if (e.status === 422) {
        externalShells.value[url] = "The link does not point to a valid Asset Administration Shell";
      } else if (e.status === 404) {
        externalShells.value[url] = "The link does not points to a page which could not be found (404)";
      } else {
        console.error(e);
        externalShells.value[url] = "The asset could not be loaded"
      }
    })
  }
  for (const removeUrl of removeUrls) {
    delete externalShells.value[removeUrl];
  }
}, {
  immediate: true
})

// Route of the top left back arrow
const backRoute = computed(() => {
  let { back } = router.currentRoute.value.meta;
  if (typeof back !== "string" && typeof back !== "function" && typeof back !== "object" || back === null) {
    return undefined;
  }
  if (typeof back === "function") {
    back = back(router.currentRoute.value);
  }
  if (typeof back === "string") {
    return { name: back };
  }
  return back;
})

// Right hand help bar content
const helpBarContent = ref<Component>();
provide(helpBarKey, helpBarContent);
// $router.currentRoute.value.matched[0].props.default.test
</script>

<template>
  <div class="my-2 mx-4 fixed z-50" :class="backRoute ? 'w-10 h-10' : 'w-16'">
      <router-link
        v-if="backRoute"
        type="button"
        class="block w-10 h-10 p-2 bg-base-100 box-border rounded-sm border border-1 drop-shadow-sm active:drop-shadow-none"
        :to="backRoute"
      >
        <ArrowLeftIcon />
      </router-link>
      <router-link v-else to="/" title="CLiCE-DiPP" class="block my-2">
        <img
          :src="LogoSVG"
          alt="CLiCE-DiPP logo"
          class="w-full"
          :class="{ 'bg-white/90 rounded-sm p-0.5': useDarkTheme }"
        />
      </router-link>
  </div>
  <div class="fixed bottom-0 py-2 px-4 z-50">
    <input type="checkbox" class="toggle" v-model="useDarkTheme" />
  </div>

  <HelpBar />
  <GlobalContextMenuComponent />
  <BackOnError />
  <div class="grow">
    <RouterView :key="JSON.stringify([$route.name, $route.params])" />
  </div>
  <ErrorLog />
</template>
