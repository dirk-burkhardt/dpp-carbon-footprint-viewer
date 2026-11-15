<script setup lang="ts">
import InfoBox from '@/components/InfoBox.vue'
import { type RouteLocationRaw, useRouter } from 'vue-router'
import { ChartBarSquareIcon } from '@heroicons/vue/24/outline'
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    explanation?: string,
    direction?: "left" | "right" | "top" | "bottom",
    to: RouteLocationRaw,
    fallbackTo?: RouteLocationRaw,
  }>(),
  {
    explanation: undefined,
    direction: "right",
    fallbackTo: undefined,
  }
);

const router = useRouter();

const isOtherRoute = computed(() => router.resolve(props.to).path === router.currentRoute.value.path);
const adjustedTo = computed(() => {
  if (isOtherRoute.value) {
    if (props.fallbackTo) {
      return props.fallbackTo;
    }
    return { name: 'visualization.single', params: router.currentRoute.value.params };
  }
  return props.to;
});
</script>

<template>
  <router-link class="col-span-2 text-center border-2 rounded-lg p-4" :to="adjustedTo">
    <InfoBox>
      <div class="text-center">
        <template v-if="!isOtherRoute">
          <slot />
        </template>
        <template v-else>
          <slot name="fallback">
            <ChartBarSquareIcon class="h-10 mx-auto mb-2" />
            <div class="text-base-content">
              <strong>Overview</strong><br />
              Not familiar with the asset and its components? Get an overview.
            </div>
          </slot>
        </template>
      </div>
    </InfoBox>
  </router-link>
</template>
