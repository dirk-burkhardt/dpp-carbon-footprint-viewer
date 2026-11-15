<script setup lang="ts">
import type { components } from '@/lib/api/AssetAdministrationShellRepository'
import { toDescriptionSmall } from '@/lib/api/registry'
import ShellCard from '@/components/ShellCard.vue'
import { computed } from 'vue'

type Asset = components["schemas"]["AssetAdministrationShell"]
const assets = defineModel<(Asset | Asset[])[]>({ default: () => [] });
const emit = defineEmits<{
  change: [asset: Asset, index: number, assetArray: Asset[], assetArrayIndex: number]
}>();

type ClassType = string | { [className: string]: boolean } | string[];
const props = withDefaults(defineProps<{
  class?: ClassType,
  wrapperClass?: ClassType,
}>(), { class: "", wrapperClass: "" });

function choose(asset: Asset, index: number, assetArray: Asset[], assetArrayIndex: number) {
  assets.value[assetArrayIndex] = asset;
  emit("change", asset, index, assetArray, assetArrayIndex)
}

const allAssets = computed(() => assets.value.some(Array.isArray) ? null : assets.value as Asset[]);
</script>
<template>
  <div v-for="(a, i) of assets" :key="i" :class="wrapperClass">
    <div v-if="Array.isArray(a)" :class="props.class">
      <slot name="none" v-if="!a.length">
        <div class="alert alert-warning">
          It seems like there is no asset in the file. Please choose another file in the
          <button @click="$router.back()" class="btn btn-secondary">previous step</button>.
        </div>
      </slot>
      <slot name="multiple" :n="a.length" v-else-if="a.length > 1">
        <div class="alert alert-info">
          It seems like there were multiple assets in the same file, please select the one you want to display
        </div>
      </slot>
      <div v-for="(asset, index) of (a as Asset[])" :key="index" @click="choose(asset, index, a as Asset[], i)" class="cursor-pointer">
        <slot name="selection" :asset="asset" :index="index" @click="choose(asset, index, a as Asset[], i)">
          <ShellCard
            :key="asset.id"
            :shell="toDescriptionSmall(asset)"
            class="shadow-lg"
          />
        </slot>
      </div>
    </div>
    <slot :asset="a" :description="toDescriptionSmall(a as Asset)" v-else />
    <slot name="assets" v-if="allAssets" :assets="allAssets" />
  </div>
</template>
