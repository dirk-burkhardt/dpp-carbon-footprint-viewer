<script setup lang="ts">
/**
 * Kopfzeile auf allen Seiten: Logo, Suche (optional innerhalb der Schalen), Hell/Dunkel, Info
 */
import { inject, ref, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import { InformationCircleIcon, MagnifyingGlassIcon, MoonIcon, SunIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import LogoSVG from '@/assets/DPPviewer-logo.svg'
import { darkModeKey } from '@/lib/injectionKeys'
import { deepSearch, deepSearchLoading, searchText } from '@/lib/search'
import AboutContent from '@/components/AboutContent.vue'
import { isMobile } from '@/lib/viewport'

const router = useRouter()
const useDarkTheme = inject<Ref<boolean>>(darkModeKey)
const infoDialog = ref<HTMLDialogElement>()

// Suchen ist nur auf der Assetauswahl möglich, daher dorthin wechseln
function onSearchInput() {
  if (router.currentRoute.value.name !== 'home' && searchText.value.trim().length > 0) {
    router.push({ name: 'home' })
  }
}
</script>

<template>
  <!-- Only the asset selection keeps the header (and its search) in view; analyses scroll it away -->
  <header
    class="top-0 z-[60] h-14 flex items-center gap-2 md:gap-4 px-2 md:px-4 bg-base-100 border-b border-base-300"
    :class="{ sticky: router.currentRoute.value.name === 'home' }"
  >
    <router-link to="/" title="Asset selection" class="shrink-0">
      <img
        :src="LogoSVG"
        alt="DPPviewer logo"
        class="h-8 md:h-10"
        :class="{ 'bg-white/90 rounded-sm p-0.5': useDarkTheme }"
      />
    </router-link>

    <div class="input grow min-w-0">
      <MagnifyingGlassIcon class="h-5 opacity-60 shrink-0" />
      <input
        v-model="searchText"
        type="search"
        class="grow min-w-0"
        :placeholder="isMobile ? 'Search' : deepSearch ? 'Search asset administration shells and their contents' : 'Search asset administration shells'"
        @input="onSearchInput"
      />
      <span v-if="deepSearch && deepSearchLoading" class="loading loading-spinner loading-xs opacity-60"></span>
      <button v-if="searchText" type="button" class="opacity-60 hover:opacity-100" title="Clear search" @click="searchText = ''">
        <XMarkIcon class="h-4" />
      </button>
      <span class="h-6 border-l border-base-300 mx-1 hidden sm:block"></span>
      <button
        type="button"
        role="switch"
        :aria-checked="deepSearch"
        class="flex items-center gap-2 whitespace-nowrap text-sm shrink-0"
        title="Also search the submodel contents of all shells (e.g. materials, manufacturers, components)"
        @click="deepSearch = !deepSearch; onSearchInput()"
      >
        <span
          class="relative inline-block w-8 h-4 rounded-full transition-colors"
          :class="deepSearch ? 'bg-primary' : 'bg-base-300'"
        >
          <span
            class="absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-base-100 shadow-sm transition-transform"
            :class="{ 'translate-x-4': deepSearch }"
          ></span>
        </span>
        <span class="hidden md:inline">Search inside shells</span>
      </button>
    </div>

    <label class="swap swap-rotate shrink-0" :title="useDarkTheme ? 'Switch to light mode' : 'Switch to dark mode'">
      <input v-if="useDarkTheme !== undefined" v-model="useDarkTheme" type="checkbox" />
      <SunIcon class="swap-off h-6" />
      <MoonIcon class="swap-on h-6" />
    </label>

    <button type="button" class="shrink-0" title="About this tool" @click="infoDialog?.showModal()">
      <InformationCircleIcon class="h-7" />
    </button>

    <dialog ref="infoDialog" class="modal">
      <div class="modal-box max-w-3xl">
        <form method="dialog">
          <button class="btn btn-sm btn-ghost absolute right-2 top-2" title="Close"><XMarkIcon class="h-5" /></button>
        </form>
        <AboutContent />
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>
  </header>
</template>
