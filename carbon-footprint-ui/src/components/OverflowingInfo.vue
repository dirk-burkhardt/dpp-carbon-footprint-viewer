<template>
  <div class="alert bg-base-200/20 flex">
    <InformationCircleIcon class="w-8 h-8 py-1" />
    <div
      class="overflow-hidden text-ellipsis relative w-full z-0"
      :class="{'whitespace-nowrap h-6': !expanded}"
    >
      <button
        class="float-right link pl-1 cursor-pointer z-50"
        @click="expanded = !expanded"
        v-show="!expanded"
      >
        Show more
      </button>
      <div
        class="inline relative text-justify hyphens-auto"
        :class="{'-z-10': !expanded}"
      >
        <slot />
        <button
          class="link cursor-pointer"
          @click="expanded = !expanded"
          v-show="expanded"
        >
          Show less
        </button>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { InformationCircleIcon } from '@heroicons/vue/24/outline'

const expanded = defineModel();
</script>
