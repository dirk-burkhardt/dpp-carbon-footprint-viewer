<template>
  <div class="mt-4 text-center" v-if="error">
    <FaceFrownIcon class="w-24 mx-auto" />
    <div class="mx-auto inline-block">
      <div class="alert alert-error">
        {{ error }}
      </div>
      <button class="btn btn-secondary btn-outline mt-2" @click="$router.back(); error = undefined; backButton = undefined;"><ChevronLeftIcon class="h-6 -m-1" />{{ backButton || "Go back" }}</button>
    </div>
  </div>
</template>
<script lang="ts" setup>
import { ref, watch } from 'vue'
import { BackOnErrorHandler } from '@/lib/BackOnErrorHandler'
import { FaceFrownIcon, ChevronLeftIcon } from '@heroicons/vue/24/outline';
import router from '@/router'

const error = ref<string>();
const backButton = ref<string>();


watch(() => router.currentRoute.value.fullPath, () => {
  error.value = undefined;
  backButton.value = undefined;
})

BackOnErrorHandler.errorFunction = (e: string, b?: string) => {
  error.value = e;
  backButton.value = b;
}
</script>
