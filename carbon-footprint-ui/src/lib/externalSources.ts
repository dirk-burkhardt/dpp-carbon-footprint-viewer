/**
 * External sources (links and uploads) the user added in this browser.
 *
 * They are kept in the browser storage, so they stay listed under "External assets" when navigating or reloading,
 * until the time to live of the server (CFA_UPLOAD_TTL_HOURS) has passed or the user removes them. They are only
 * visible in the browser in which they were added; shared links still work through the route parameter "preload".
 */
import { storageRef } from '@/lib/storage'

export type ExternalSource = {
  /** URL of the file, or "upload:<id>" for an uploaded file */
  url: string
  /** Expiry in milliseconds since 1970 */
  expiresAt: number
}

const DEFAULT_TTL_MS = 3 * 3600 * 1000
let ttlMs = DEFAULT_TTL_MS

export const externalSources = storageRef<ExternalSource[]>('externalSources', [])

// Expired in this session: not added again from an old link that still carries them
const expiredUrls = new Set<string>()

/** Time to live for new sources as configured on the server */
export function setSourceTtl(seconds: number) {
  if (seconds > 0) {
    ttlMs = seconds * 1000
  }
}

export function hasExternalSource(url: string): boolean {
  return externalSources.value.some((s) => s.url === url)
}

export function wasExpired(url: string): boolean {
  return expiredUrls.has(url)
}

/** Adds a source or, if known, updates its expiry */
export function addExternalSource(url: string, expiresAt?: number) {
  expiredUrls.delete(url)
  const expiry = expiresAt ?? Date.now() + ttlMs
  const existing = externalSources.value.find((s) => s.url === url)
  if (existing) {
    existing.expiresAt = expiresAt ?? existing.expiresAt
  } else {
    externalSources.value.push({ url, expiresAt: expiry })
  }
}

export function removeExternalSource(url: string) {
  externalSources.value = externalSources.value.filter((s) => s.url !== url)
}

/** Removes expired sources and returns their URLs */
export function pruneExpiredSources(): string[] {
  const now = Date.now()
  const expired = externalSources.value.filter((s) => s.expiresAt <= now).map((s) => s.url)
  if (expired.length) {
    expired.forEach((url) => expiredUrls.add(url))
    externalSources.value = externalSources.value.filter((s) => s.expiresAt > now)
  }
  return expired
}
