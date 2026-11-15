/**
 * Base64-Codierung von IDs und URLs.
 *
 * btoa/atob funktionieren nur mit Latin-1 und werfen bei anderen Zeichen. Diese Funktionen codieren UTF-8.
 * Für reine ASCII-Texte ist encodeBase64 bitgleich mit btoa, bestehende Links bleiben also gültig.
 */

function bytesToBinary(bytes: Uint8Array): string {
  let binary = ''
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000))
  }
  return binary
}

/** Standard-Base64 (mit + / =) eines UTF-8-Textes, z. B. für Routenparameter. */
export function encodeBase64(text: string): string {
  return btoa(bytesToBinary(new TextEncoder().encode(text)))
}

/** Dekodiert Standard- oder URL-sicheres Base64 (mit oder ohne Padding) zu einem UTF-8-Text. */
export function decodeBase64(encoded: string): string {
  let normalized = encoded.trim().replace(/-/g, '+').replace(/_/g, '/')
  normalized += '='.repeat((4 - (normalized.length % 4)) % 4)
  const binary = atob(normalized)
  const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0))
  return new TextDecoder().decode(bytes)
}

/**
 * URL-sicheres Base64 ohne Padding nach AAS-Spezifikation, für IDs in API-Pfaden.
 * Enthält weder "/" noch "+", ist also ohne weitere Codierung in Pfadsegmenten verwendbar.
 */
export function encodeId(id: string): string {
  return encodeBase64(id).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}
