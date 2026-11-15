<script setup lang="ts">

import { type Slot, inject, type Ref } from 'vue'
import { helpBarKey } from '@/lib/injectionKeys'
import { XMarkIcon } from '@heroicons/vue/24/outline'

const content = inject<Ref<Slot | undefined>>(helpBarKey);
</script>
<template>
  <Transition>
    <div class="fixed inset-0 flex" style="z-index: 99999;" v-if="content">
      <div class="grow bg-black opacity-10" @click="content = undefined;"></div>
      <div class="bg-base-100 h-full shadow-xl p-4 overflow-y-auto">
        <button @click="content = undefined;" class="btn btn-secondary btn-sm btn-outline px-1"><XMarkIcon class="w-6 h-6" /></button>
        <Component :is="content" v-if="content" />
        <div>
          <button class="btn btn-secondary btn-outline btn-block btn-sm" @click="content = undefined;">Close</button>
        </div>
      </div>
    </div>
  </Transition>
</template>
