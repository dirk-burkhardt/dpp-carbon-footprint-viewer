<script setup lang="ts">
import {
  type RouteLocation,
  type RouteLocationRaw,
  useRouter
} from 'vue-router'
import { computed } from 'vue'

const router = useRouter();
const routesByPath = Object.fromEntries(router.getRoutes().map((r) => [r.path, r]))
const routesByName = Object.fromEntries(router.getRoutes().map((r) => [r.name, r]))
const terminusRoute = routesByPath["/"];
if (!terminusRoute) {
  console.error("Breadcrumbs terminus not correctly set")
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
  return p;
})
</script>
<template>
  <div class="breadcrumbs">
    <ul>
      <li v-for="([route, breadcrumb], i) of routePath" :key="i"><router-link :to="route">{{ breadcrumb }}</router-link></li>
    </ul>
  </div>
</template>
