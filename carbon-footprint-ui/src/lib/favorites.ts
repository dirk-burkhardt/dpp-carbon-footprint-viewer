/**
 * Favoriten als geordnete Liste von globalAssetIds.
 *
 * Die Reihenfolge ist wichtig: Compare vergleicht die ersten beiden Favoriten. Ältere Versionen speicherten
 * die Favoriten als Objekt {globalAssetId: boolean} unter "selectedShellsById"; diese werden einmalig übernommen.
 */
import { getLocalStorage, setLocalStorage, storageRef } from '@/lib/storage'

const LEGACY_KEY = 'selectedShellsById'
const KEY = 'favoriteShells'

function initial(): string[] {
  const current = getLocalStorage<string[] | null>(KEY, null)
  if (Array.isArray(current)) {
    return current.filter((id) => typeof id === 'string')
  }
  const legacy = getLocalStorage<Record<string, boolean>>(LEGACY_KEY, {})
  const migrated = Object.entries(legacy ?? {})
    .filter(([, selected]) => selected)
    .map(([id]) => id)
  setLocalStorage(KEY, migrated)
  return migrated
}

export const favoriteIds = storageRef<string[]>(KEY, initial())

export function isFavorite(globalAssetId: string) {
  return favoriteIds.value.includes(globalAssetId)
}

export function toggleFavorite(globalAssetId: string) {
  const i = favoriteIds.value.indexOf(globalAssetId)
  if (i >= 0) {
    favoriteIds.value.splice(i, 1)
  } else {
    favoriteIds.value.push(globalAssetId)
  }
}

/** Verschiebt den Favoriten von Position from an Position to */
export function moveFavorite(from: number, to: number) {
  const list = favoriteIds.value
  if (from < 0 || from >= list.length || to < 0 || to >= list.length || from === to) {
    return
  }
  const [item] = list.splice(from, 1)
  list.splice(to, 0, item)
}
