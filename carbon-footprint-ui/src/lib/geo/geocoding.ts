/**
 * Geocoding über eine Nominatim-kompatible Schnittstelle (Standard: OpenStreetMap Nominatim).
 *
 * Die Nutzungsbedingungen von nominatim.openstreetmap.org verlangen höchstens eine Anfrage pro Sekunde und
 * das Zwischenspeichern von Ergebnissen. Beides ist hier umgesetzt: Anfragen laufen nacheinander mit
 * Mindestabstand, Ergebnisse (auch "nicht gefunden") werden im localStorage gespeichert.
 */
import apiConfig from '@/lib/apiConfig'
import { getLocalStorage, setLocalStorage } from '@/lib/storage'

export type LatLng = [latitude: number, longitude: number]

export type AddressQuery = {
  street?: string
  houseNumber?: string
  city?: string
  postalCode?: string
  state?: string
  country?: string
  countryCode?: string
}

const MIN_INTERVAL_MS = 1100
const CACHE_SPACE = 'geocoding'
const CACHE_DAYS = 30

type CacheEntry = { at: number; result: LatLng | null }

const pending = new Map<string, Promise<LatLng | undefined>>()
let queue: Promise<unknown> = Promise.resolve()
let lastRequest = 0

function clean(value?: string) {
  return value?.replace(/\s+/g, ' ').trim() || undefined
}

function cacheKey(query: AddressQuery) {
  return JSON.stringify([
    clean(query.street),
    clean(query.houseNumber),
    clean(query.city),
    clean(query.postalCode),
    clean(query.state),
    clean(query.country),
    clean(query.countryCode)?.toLowerCase()
  ])
}

function readCache(key: string): LatLng | null | undefined {
  const entry = getLocalStorage<CacheEntry | null>(key, null, CACHE_SPACE)
  if (!entry || Date.now() - entry.at > CACHE_DAYS * 86_400_000) {
    return undefined
  }
  return entry.result
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/** Führt fn nacheinander mit Mindestabstand aus (Rate-Limit des Dienstes). */
function throttled<T>(fn: () => Promise<T>): Promise<T> {
  const run = queue.then(async () => {
    const wait = lastRequest + MIN_INTERVAL_MS - Date.now()
    if (wait > 0) {
      await sleep(wait)
    }
    lastRequest = Date.now()
    return fn()
  })
  queue = run.catch(() => undefined)
  return run
}

async function search(params: Record<string, string>): Promise<LatLng | null> {
  const base = apiConfig.geocodingUrl.replace(/\/+$/, '')
  const url = new URL(`${base}/search`, window.location.href)
  url.search = new URLSearchParams({ format: 'jsonv2', limit: '1', ...params }).toString()
  const response = await throttled(() =>
    fetch(url, { headers: { Accept: 'application/json' }, referrerPolicy: 'strict-origin-when-cross-origin' })
  )
  if (!response.ok) {
    throw new Error(`Geocoding fehlgeschlagen: ${response.status}`)
  }
  const data: unknown = await response.json()
  if (!Array.isArray(data) || data.length === 0) {
    return null
  }
  const lat = Number.parseFloat(data[0]?.lat)
  const lon = Number.parseFloat(data[0]?.lon)
  return Number.isFinite(lat) && Number.isFinite(lon) ? [lat, lon] : null
}

async function lookup(query: AddressQuery): Promise<LatLng | null> {
  const street = clean([query.houseNumber, query.street].filter(Boolean).join(' '))
  const structured: Record<string, string> = {}
  if (street) structured.street = street
  if (clean(query.city)) structured.city = clean(query.city)!
  if (clean(query.postalCode)) structured.postalcode = clean(query.postalCode)!
  if (clean(query.state)) structured.state = clean(query.state)!
  if (clean(query.country)) structured.country = clean(query.country)!
  const countryCodes = clean(query.countryCode)?.toLowerCase()
  if (countryCodes && /^[a-z]{2}$/.test(countryCodes)) structured.countrycodes = countryCodes

  const result = await search(structured)
  if (result || !street) {
    return result
  }
  // Fallback: Freitextsuche ohne Hausnummer und Straße, damit zumindest der Ort gefunden wird
  const { street: _street, ...withoutStreet } = structured
  return search(withoutStreet)
}

/**
 * Koordinaten zu einer Adresse oder undefined, wenn sie nicht gefunden wurde oder Geocoding abgeschaltet ist.
 */
export function geocode(query: AddressQuery): Promise<LatLng | undefined> {
  if (!apiConfig.geocodingUrl) {
    return Promise.resolve(undefined)
  }
  const key = cacheKey(query)
  const cached = readCache(key)
  if (cached !== undefined) {
    return Promise.resolve(cached ?? undefined)
  }
  let request = pending.get(key)
  if (!request) {
    request = lookup(query)
      .then((result) => {
        setLocalStorage<CacheEntry>(key, { at: Date.now(), result }, CACHE_SPACE)
        return result ?? undefined
      })
      .catch((error) => {
        console.warn('Geocoding fehlgeschlagen', error)
        return undefined
      })
      .finally(() => pending.delete(key))
    pending.set(key, request)
  }
  return request
}
