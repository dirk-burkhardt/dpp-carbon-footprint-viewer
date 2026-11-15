<script setup lang="ts">
import { QuestionMarkCircleIcon } from '@heroicons/vue/24/outline'
import { inject, type Ref, type Slot, useSlots } from 'vue'
import { helpBarKey } from '@/lib/injectionKeys'

const slots = useSlots();
const content = inject<Ref<Slot>>(helpBarKey);

const show = () => {
  if (content && slots.default) {
    content.value = slots.default;
  }
}
</script>
<template>
  <div class="relative inline-block">
    <button class="inline-block" @click="show">
      <slot name="icon">
        <QuestionMarkCircleIcon class="w-6 h-6 opacity-70" />
      </slot>
    </button>
  </div>
</template>
