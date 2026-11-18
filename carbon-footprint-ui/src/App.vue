<script setup lang="ts">
import { RouterView, useRouter } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import StatusIndicator from '@/components/layout/StatusIndicator.vue'
import ProblemPanel from '@/components/layout/ProblemPanel.vue'
import '@/lib/problems'
import { externalShellIds } from '@/lib/search'
import { storageRef } from '@/lib/storage'
import { type Component, provide, ref, watch } from 'vue'
import { allDescriptionsFromApi } from '@/lib/api/registry'
import { ErrorClient } from '@/lib/ErrorDataHandler'
import { darkModeKey, shellDescriptionsKey, assetIdMapKey, externalShellsKey, helpBarKey } from '@/lib/injectionKeys'
import { computedAsync } from '@vueuse/core'
import { AssetIdMap } from '@/lib/AssetIdMap'
import shellRepo from '@/lib/api/shells'
import type { components } from '@/lib/api/AssetAdministrationShellRepository'
import GlobalContextMenuComponent from '@/components/GlobalContextMenuComponent.vue'
import HelpBar from '@/components/HelpBar.vue'
import { decodeBase64 } from '@/lib/encoding'
import { isUploadUrl } from '@/lib/api/uploads'


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
      if (isUploadUrl(url) && e.status === 404) {
        externalShells.value[url] = "The uploaded file is no longer available on the server (expired or server restarted). Please upload it again";
      } else if (e.status === 422) {
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

// IDs der heruntergeladenen Shells, damit die Suche innerhalb der Schalen auch sie durchsucht
watch(externalShells, (shells) => {
  externalShellIds.value = Object.values(shells)
    .filter(Array.isArray)
    .flat()
    .map((shell) => shell.id)
}, { deep: true })

// Right hand help bar content
const helpBarContent = ref<Component>();
provide(helpBarKey, helpBarContent);
// $router.currentRoute.value.matched[0].props.default.test
</script>

<template>
  <AppHeader />
  <HelpBar />
  <GlobalContextMenuComponent />
  <main class="grow">
    <RouterView :key="JSON.stringify([$route.name, $route.params])" />
  </main>
  <!-- Auf der Startseite sitzt die Statusanzeige unter den Favoriten -->
  <div v-if="$route.name !== 'home'" class="fixed bottom-3 right-3 z-40 bg-base-100 rounded-full shadow-md">
    <StatusIndicator small />
  </div>
  <ProblemPanel />
</template>
