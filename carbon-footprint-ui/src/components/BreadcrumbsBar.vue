<script setup lang="ts">
import {
  type RouteLocation,
  type RouteLocationRaw,
  useRouter
} from 'vue-router'
import { computed } from 'vue'
import { ArrowLeftIcon } from '@heroicons/vue/24/outline'
import { assetSelectionQuery } from '@/lib/assetSelectionState'

const router = useRouter();
const routesByPath = Object.fromEntries(router.getRoutes().map((r) => [r.path, r]))
const routesByName = Object.fromEntries(router.getRoutes().map((r) => [r.name, r]))
const terminusRoute = routesByPath["/"];
if (!terminusRoute) {
  console.error("Breadcrumbs terminus not correctly set")
}
// Shared external sources stay part of the link back
function preloadQuery() {
  const { preload } = router.currentRoute.value.query;
  return preload ? { preload } : {};
}

const routePath = computed(() => {
  let c: RouteLocation = router.currentRoute.value;
  const p: [RouteLocationRaw, string][] = [
    [c, c.meta.breadcrumb as string]
  ];
  while (c.meta.back) {
    let { back } = c.meta;
    if (typeof back !== "string" && typeof back !== "function" && typeof back !== "object") {
      console.error("Could not build breadcrumb path, terminating early");
      break;
    }
    if (typeof back === "function") {
      back = back(router.resolve(p[0][0]));
    }
    if (typeof back === "string") {
      back = { name: back };
    }
    const routeLocation = back as RouteLocation;
    if (!routeLocation.name && !routeLocation.path) {
      console.error("Could not build breadcrumb path, terminating early");
      break;
    }
    const backRoute: RouteLocation = routeLocation.path ? routesByPath[routeLocation.path] : routesByName[routeLocation.name!];
    p.unshift([routeLocation, backRoute.meta.breadcrumb as string]);
    c = backRoute;
  }
  if (c.path !== terminusRoute.path) {
    p.unshift([terminusRoute, terminusRoute.meta.breadcrumb as string]);
  }
  // The asset selection opens the tab it showed last (e.g. "External assets"), keeping loaded sources
  return p.map(([location, label], i): [RouteLocationRaw, string] => {
    const isSelection = i < p.length - 1 && router.resolve(location).name === 'home';
    return isSelection
      ? [{ name: 'home', query: { ...preloadQuery(), ...assetSelectionQuery() } }, label]
      : [location, label];
  });
})

// Ziel des Zurück-Pfeils: der vorletzte Eintrag der Brotkrümel
const backRoute = computed(() => (routePath.value.length > 1 ? routePath.value[routePath.value.length - 2][0] : undefined))
</script>
<template>
  <div class="flex items-center gap-2">
    <router-link v-if="backRoute" :to="backRoute" class="btn btn-ghost btn-sm btn-square" title="Back">
      <ArrowLeftIcon class="h-5" />
    </router-link>
    <div class="breadcrumbs">
      <ul>
        <li v-for="([route, breadcrumb], i) of routePath" :key="i"><router-link :to="route">{{ breadcrumb }}</router-link></li>
      </ul>
    </div>
  </div>
</template>
