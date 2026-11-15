<script setup lang="ts">
import { computed } from 'vue'
import { grams, percent } from '../lib/util'

const props = defineProps<{ value: number, other: number }>();
const diff = computed(() => props.value - props.other);
</script>
<template>
  <strong v-if="diff > 0">
    {{ grams(props.value, "kg") }} (+{{ percent(diff/props.value) }})
  </strong>
  <template v-else-if="diff < 0">
    {{ grams(props.value, "kg") }} ({{ percent(diff/props.value) }})
  </template>
  <template v-else>
    {{ grams(props.value, "kg") }}
  </template>
</template>
