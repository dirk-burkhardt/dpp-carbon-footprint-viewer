/**
 * Suche im Header, gemeinsam für alle Ansichten.
 *
 * Ohne Tiefensuche werden Name, IDs, idShort und Beschreibung der bekannten Shells durchsucht. Mit Tiefensuche
 * fragt die Oberfläche zusätzlich die API (/search), die alle Submodell-Inhalte durchsucht.
 */
import { ref, watch } from 'vue'
import { debounce } from 'lodash'
import apiConfig from '@/lib/apiConfig'
import { storageRef } from '@/lib/storage'
import { ErrorClient } from '@/lib/ErrorDataHandler'

export type SearchMatch = { submodel: string | null, path: string, text: string }
export type DeepSearchHit = {
  id: string
  globalAssetId: string | null
  idShort: string | null
  total: number
  matches: SearchMatch[]
}

/** Suchtext */
export const searchText = ref('')

/** Ob auch innerhalb der Schalen (Submodell-Inhalte) gesucht wird */
export const deepSearch = storageRef<boolean>('deepSearch', false)

/** Treffer der Tiefensuche je globalAssetId (und id), undefined solange keine Tiefensuche aktiv ist */
export const deepHits = ref<Map<string, DeepSearchHit> | undefined>(undefined)
export const deepSearchLoading = ref(false)

/** IDs heruntergeladener (externer) Shells, die die API zusätzlich durchsuchen soll */
export const externalShellIds = ref<string[]>([])

let requestNumber = 0

async function runDeepSearch(text: string, include: string[]) {
  const current = ++requestNumber
  const params = new URLSearchParams({ q: text })
  include.forEach((id) => params.append('include', id))
  try {
    const response = await fetch(`${apiConfig.assetAdministrationShellRepositoryUrl}/search?${params}`)
    if (!response.ok) {
      throw new Error(`Search failed (HTTP ${response.status})`)
    }
    const data = (await response.json()) as { result: DeepSearchHit[] }
    if (current !== requestNumber) {
      return
    }
    const hits = new Map<string, DeepSearchHit>()
    for (const hit of data.result) {
      hits.set(hit.id, hit)
      if (hit.globalAssetId) {
        hits.set(hit.globalAssetId, hit)
      }
    }
    deepHits.value = hits
  } catch (e) {
    if (current === requestNumber) {
      deepHits.value = new Map()
      ErrorClient.warn('Search within the shells is not available', e instanceof Error ? e.message : undefined)
    }
  } finally {
    if (current === requestNumber) {
      deepSearchLoading.value = false
    }
  }
}

const debouncedDeepSearch = debounce(runDeepSearch, 300)

watch([searchText, deepSearch, externalShellIds], ([text, deep, include]) => {
  const trimmed = text.trim()
  if (!deep || trimmed.length === 0) {
    requestNumber++
    debouncedDeepSearch.cancel()
    deepHits.value = undefined
    deepSearchLoading.value = false
    return
  }
  deepSearchLoading.value = true
  debouncedDeepSearch(trimmed, include.slice(0, 100))
})
