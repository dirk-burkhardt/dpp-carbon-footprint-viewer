<script setup lang="ts" generic="PromiseValue">
import { ref } from 'vue'
import { ErrorClient } from '@/lib/ErrorDataHandler'

const props = withDefaults(
  defineProps<{
    promise: Promise<PromiseValue>,
    onfulfilled?: (data: PromiseValue) => any,
    onrejected?: (reason: any) => any,
    finally?: () => any,
  }>(),
  {
    onfulfilled: () => {},
    onrejected: (reason: any) => { ErrorClient.add(reason); },
    finally: () => {},
  }
)
const loading = ref(true);
const data = ref<PromiseValue | undefined>(undefined);
const error = ref<any>(undefined);

props.promise
  .then((d) => { data.value = d; })
  .catch((e) => { error.value = e; })
  .finally(() => { loading.value = false; })
</script>

<template>
  <slot name="loading" v-if="loading"></slot>
  <slot v-else-if="data" name="resolved" :data="data"></slot>
  <slot v-else name="rejected" :error="error"></slot>
</template>
