/**
 * State of the asset selection (start page) that links back to it must restore, e.g. the breadcrumbs.
 */
import { ref } from 'vue'
import type { LocationQueryRaw } from 'vue-router'

/** Tab of the asset selection that was shown last */
export const lastAssetTab = ref<'preloaded' | 'external'>('preloaded')

/** Query for a link back to the asset selection, opening the tab shown last */
export function assetSelectionQuery(): LocationQueryRaw {
  return lastAssetTab.value === 'external' ? { assets: 'external' } : {}
}
