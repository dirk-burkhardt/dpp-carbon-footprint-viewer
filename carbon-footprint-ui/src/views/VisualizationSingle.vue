<script setup lang="ts">
/**
 * Single Asset Analysis
 */
import { useRoute } from 'vue-router'
import { computed, inject, type Ref } from 'vue'
import { diffToString, generateColor, loadFullAssetInfo, simulationFromRoute } from '@/lib/util'
import { computedAsync } from '@vueuse/core'
import { BackOnErrorHandler, currentLoadError } from '@/lib/BackOnErrorHandler'
import LoadFailed from '@/components/layout/LoadFailed.vue'
import { assetIdMapKey } from '@/lib/injectionKeys'
import { AssetIdMap } from '@/lib/AssetIdMap'
import BreadcrumbsBar from '@/components/BreadcrumbsBar.vue'
import {
  ChartBarSquareIcon,
  ChevronDoubleRightIcon,
  ChevronDoubleLeftIcon,
  CloudIcon,
  CubeIcon,
  CubeTransparentIcon,
  PuzzlePieceIcon,
  ArrowPathIcon
} from '@heroicons/vue/24/outline'
import InfoBox from '@/components/InfoBox.vue'
import { storageRef } from '@/lib/storage'
// PresentationChartBarIcon CircleStackIcon CogIcon
const route = useRoute();
const idMap = inject<Ref<AssetIdMap>>(assetIdMapKey);

// All information regarding an asset, incl. footprint infromation
const info = computedAsync<Awaited<ReturnType<typeof loadFullAssetInfo> | undefined>>(async () => {
  if (!idMap?.value) {
    return undefined;
  }
  return BackOnErrorHandler.bind(loadFullAssetInfo(route.params.asset as string, idMap.value, "url-", () => {}, simulationFromRoute(route)), (e) => {
    if (e.status === 422) {
      return "The URL to the asset is invalid or does not point to a valid asset";
    }
    if (e.status === 404) {
      return "The asset could not be found";
    }
    return "An error occurred while loading the asset";
  });
}, undefined)

// Whether to show the large version of the left-hand tabs
const expandTabs = storageRef('expandPageTabs', true);

// Whether this asset currently includes simulated values
const showSimulation = computed(() => info.value?.carbonTree?.hasChanges && route.name !== "visualization.single.simulation")
</script>

<template>
  <div class="px-4 py-1 bg-base-100 border-b border-base-300 relative z-30">
    <BreadcrumbsBar />
  </div>
  <LoadFailed v-if="currentLoadError" :message="currentLoadError" />
  <div class="flex w-full" v-else>
    <!-- Left hand tabs -->
    <div class="page-tabs pt-10 pb-4" :class="{'min-w-72': expandTabs }">
      <button class="absolute right-2 top-3" :title="expandTabs ? 'Collapse' : 'Expand'" @click="expandTabs = !expandTabs"><ChevronDoubleRightIcon class="w-4" v-if="!expandTabs" /><ChevronDoubleLeftIcon class="w-4" v-else /></button>
      <div class="page-tabs-container" v-if="info">
        <router-link
          class="page-tab h-1/4"
          :class="{'active': route.name === 'visualization.single'}"
          :to="{ name: 'visualization.single', params: { asset: route.params.asset } }"
        >
          <div class="page-tab-container">
            <ChartBarSquareIcon class="h-10 mx-auto mb-2 min-h-6 text-base-content" />
            <div class="text-base-content">
              <strong>Overview</strong>
              <div :class="{'hidden': !expandTabs}">
                Not familiar with the asset and its components? Get an overview.
              </div>
            </div>
          </div>
        </router-link>
        <router-link
          :to="{ name: 'visualization.single.components', params: { asset: route.params.asset } }"
          class="page-tab h-1/4"
          :class="{'active': route.name === 'visualization.single.components'}"
        >
          <div class="page-tab-container">
            <PuzzlePieceIcon class="h-10 mx-auto mb-2 min-h-6 text-base-content" />
            <div class="text-base-content">
              <strong>Components</strong>
              <div :class="{'hidden': !expandTabs}">
                Is one responsible for most of the products footprint?
              </div>
            </div>
          </div>
        </router-link>
        <router-link
          :to="{ name: 'visualization.single.lifecycle', params: { asset: route.params.asset } }"
          class="page-tab h-1/4"
          :class="{'active': route.name === 'visualization.single.lifecycle'}"
        >
          <div class="page-tab-container">
            <CloudIcon class="h-10 mx-auto mb-2 min-h-6 text-base-content" />
            <div class="text-base-content">
              <strong>Life Cycles</strong>
              <div :class="{'hidden': !expandTabs}">
                Which phases add how much to the carbon footprint? How much is emitted during transport?
              </div>
            </div>
          </div>
        </router-link>
        <router-link
          :to="{ name: 'visualization.single.simulation', params: { asset: route.params.asset } }"
          class="page-tab h-1/4"
          :class="{'active': route.name === 'visualization.single.simulation'}"
        >
          <div class="page-tab-container">
            <ArrowPathIcon class="h-10 mx-auto mb-2 min-h-6 text-base-content" />
            <div class="text-base-content">
              <strong>Simulation</strong>
              <div :class="{'hidden': !expandTabs}">
                Simulate the swap of one or multiple sub-components.
              </div>
            </div>
          </div>
        </router-link>
      </div>
    </div>

    <!-- Content -->
    <div class="grow min-w-0">
      <!-- General information present on all sites -->
      <Transition>
        <div class="m-4 gap-4 grid grid-cols-6 duration-200 absolute" v-if="!info">
          <div class="col-span-6 gap-2 flex">
            <div class="skeleton size-8 rounded-sm inline-block p-1"></div>
            <div>
              <div class="skeleton col col-span-2 h-6 w-52 mt-1"></div>
              <div class="skeleton col-span-2 h-5 mt-2 w-44"></div>
              <div class="mt-3 skeleton h-5 w-72"></div>
              <div class="mt-1 skeleton h-5 w-64"></div>
              <div class="mt-1 skeleton h-5 w-72"></div>
            </div>
          </div>
          <div class="skeleton col-span-6 bg-gray-100 h-96"></div>
        </div>
      </Transition>
      <Transition>
        <div class="m-4 gap-4 grid grid-cols-6 duration-200" v-if="info">
          <div class="col-span-4 gap-2 flex">
            <CubeTransparentIcon v-if="info.description?.assetKind === 'Type'" class="size-8 rounded-sm inline-block p-1 text-gray-800" :style="`background: ${generateColor(info.asset.id)}`" />
            <CubeIcon v-else class="size-8 rounded-sm inline-block p-1 text-gray-800" :style="`background: ${generateColor(info.asset.id)}`" />
            <div>
              <h1 class="col col-span-2 text-2xl">
                {{ info.description?.name }}
                <span v-if="info.carbonFootprint" class="badge badge-success text-success-content">carbon footprint provided</span>
                <span v-else-if="info.carbonTree" class="badge badge-warning text-warning-content">carbon footprint calculated from sub-components</span>
                <span v-else class="badge badge-error text-error-content">no carbon footprint data</span>
              </h1>
              <h2 v-if="info.description?.idShort" class="col-span-2 font-mono text-sm">{{ info.description.idShort }}</h2>
              <p class="pt-3 ital" v-if="info.description?.description">{{ info.description.description }}</p>
            </div>
          </div>
          <template v-if="info.carbonTree">
            <InfoBox
              class="col-span-1 text-center bg-base-200 rounded-lg p-4"
              explanation="Only components directly attached to this asset"
              direction="left"
            >
              <span class="text-3xl leading-4">
                {{ info.carbonTree.directComponentsCount }}
                <span class="text-xs" v-if="info.carbonTree.directComponentsCountDiff !== 0">
                  {{ diffToString(info.carbonTree.directComponentsCountDiff) }}
                </span>
              </span><br />
              direct sub-components
            </InfoBox>
            <InfoBox
              class="col-span-1 text-center bg-base-200 rounded-lg p-4"
              explanation="All components this asset and all its components are made of"
              direction="left"
            >
              <span class="text-3xl leading-4">{{ info.carbonTree.allComponentsCount }}
                <span class="text-xs" v-if="info.carbonTree.allComponentsCountDiff !== 0">
                  {{ diffToString(info.carbonTree.allComponentsCountDiff) }}
                </span>
              </span><br />
              overall sub-components
            </InfoBox>
          </template>
          <InfoBox
            class="col-span-2 text-center bg-base-200 rounded-lg flex align-middle"
            explanation="There are no components attached to this component"
            direction="left"
            v-else
          >
            <div>
              <span class="text-3xl">standalone</span><br />
              without sub-components
            </div>
          </InfoBox>
        </div>
      </Transition>

      <!-- Bar indicating that this is a simulation -->
      <Transition>
        <div class="sticky top-16 duration-200 px-4 z-30" v-if="showSimulation">
          <div class="alert alert-warning shadow-sm">
            <strong>Simulation</strong>
            <span>
              The values of this asset are being simulated. To view which changes were made, click
              <router-link class="btn btn-outline btn-sm" :to="{ name: 'visualization.single.simulation', params: { asset: route.params.asset } }">here</router-link>.
            </span>
          </div>
        </div>
      </Transition>

      <!-- CONTENT -->
      <router-view v-slot="{ Component }" v-if="info">
        <component :is="Component" :info="info" />
      </router-view>

      <!-- Debug information -->
      <div class="grid grid-cols-6 gap-4 m-4" v-if="info">
        <div class="collapse col-span-6 bg-base-200/30">
          <input type="checkbox" />
          <div class="collapse-title">Debug Info</div>
          <div class="collapse-content grid grid-cols-2 gap-2">
            <div class="col-span-1 overflow-x-scroll">
              <h2 class="text-2xl">Asset JSON</h2>
              <pre>{{ info.asset }}</pre>
            </div>
            <div class="col-span-1 overflow-x-scroll">
              <h2 class="text-2xl">Submodel JSON</h2>
              <pre>{{ info.submodels?.json() }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
