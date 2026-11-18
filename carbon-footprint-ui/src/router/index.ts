import _ from "lodash"
import { createRouter, createWebHistory, type RouteLocation, type RouteLocationNormalizedLoaded, type RouteLocationRaw } from "vue-router"
import HomeView from "../views/HomeView.vue"

declare module 'vue-router' {
  interface RouteMeta {
    /** Ziel des Zurück-Links in der Brotkrümelleiste */
    back?: null | string | RouteLocationRaw | ((route: RouteLocationNormalizedLoaded | RouteLocation) => RouteLocationRaw)
    breadcrumb?: string
  }
}

// Bis auf die Startseite werden Ansichten erst bei Bedarf geladen (kleineres Startpaket)
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
      meta: {
        back: null,
        breadcrumb: "Asset Selection"
      }
    },
    {
      path: "/shells/:asset",
      component: () => import("../views/VisualizationSingle.vue"),
      children: [
        {
          path: "/shells/:asset",
          name: "visualization.single",
          component: () => import("@/views/single/SingleOverview.vue"),
          meta: {
            back: "home",
            breadcrumb: "Overview"
          },
        },
        {
          path: "/shells/:asset/lifecycle",
          name: "visualization.single.lifecycle",
          component: () => import("@/views/single/SingleLifeCycle.vue"),
          meta: {
            back: "visualization.single",
            breadcrumb: "Life Cycle Analysis"
          },
        },
        {
          path: "/shells/:asset/components",
          name: "visualization.single.components",
          component: () => import("@/views/single/SingleComponents.vue"),
          meta: {
            back: "visualization.single",
            breadcrumb: "Component Analysis"
          },
        },
        {
          path: "/shells/:asset/estimates",
          name: "visualization.single.estimates",
          component: () => import("@/views/single/SingleEstimates.vue"),
          meta: {
            back: "visualization.single",
            breadcrumb: "Estimates"
          },
        },
        {
          path: "/shells/:asset/simulation",
          name: "visualization.single.simulation",
          component: () => import("@/views/single/SingleSimulation.vue"),
          meta: {
            back: "visualization.single",
            breadcrumb: "Simulation"
          },
        }
      ]
    },
    {
      path: "/about",
      name: "about",
      component: () => import("@/views/AboutView.vue"),
      meta: {
        back: "home",
        breadcrumb: "About"
      }
    },
    {
      path: "/dual/:first/:second",
      name: "visualization.dual",
      component: () => import("../views/VisualizationDual.vue"),
      meta: {
        back: "home",
        breadcrumb: "Compare"
      }
    },
    {
      path: "/shells/:assets+",
      name: "visualization.multi",
      component: () => import("../views/VisualizationMulti.vue"),
      meta: {
        back: "home",
        breadcrumb: "Overview of Multiple Assets"
      },
      beforeEnter: (to, from, next) => {
        if (to.params.assets.length < 3) {
          console.error(`Parameter "assets" is required at least three times for route visualization.multi.`);
          next(false);
        } else {
          next();
        }
      }
    },
    {
      path: "/datasheet/:assets+",
      name: "datasheet",
      component: () => import("@/views/DatasheetComparison.vue"),
      meta: {
        back: "home",
        breadcrumb: "Data Sheet"
      }
      /*
      meta: {
        back: (r) => ({ name: "visualization.single", params: { asset: r.params.assets[0] }}),
        breadcrumb: "Datasheet"
      },
       */
    },
  ],
})

const guardHashIfEmpty = true;
const guardParameters = ["preload", "simulationChanges"];
router.beforeEach(async (to, from) => {
  let hashChanged = false;
  if (guardHashIfEmpty && from.hash && to.hash.length === 0) {
    if (to.fullPath.split("#")[0] !== from.fullPath.split("#")[0]) {
      to.hash = from.hash;
      hashChanged = true;
    }
  }
  // Only allow to remove values from param preload if that's the only param being edited
  // because we might need all preloaded assets to build references between assets.
  for (const param of guardParameters) {
    const fromParam = typeof from.query[param] === "string" ? [from.query[param]] : from.query[param] || [];
    const toParam = typeof to.query[param] === "string" ? [to.query[param]] : to.query[param] || [];
    if (
      (to.hash !== from.hash ||
        to.name !== from.name ||
        !_.isEqual(to.params, from.params) ||
        // Check all query params except preload if they changed
        Object.entries(from.query)
          .filter(([k]) => k !== param)
          .every(([k, v]) => !_.isEqual(to.query[k], v)
          ))
      && _.difference(fromParam, toParam).length > 0
    ) {
      to.query[param] = _.compact(_.uniq([toParam, fromParam].flat()));
      return to;
    }
  }
  if (hashChanged) {
    return to;
  }
})

export default router
