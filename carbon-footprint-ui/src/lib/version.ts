import apiConfig from '@/lib/apiConfig'

/** Version der Oberfläche (aus package.json) */
export const uiVersion: string = __APP_VERSION__

/** Hauptversion der API, mit der diese Oberfläche arbeitet (Präfix /api/v4) */
export const requiredApiMajor = 4

export type ApiStatus = { version: string; shells: number }

/**
 * Status der API von /api/health. Die Adresse wird aus der Repository-URL abgeleitet
 * (z. B. /api/v4 → /api/health).
 */
export async function fetchApiStatus(): Promise<ApiStatus | undefined> {
  try {
    const base = new URL(apiConfig.assetAdministrationShellRepositoryUrl.replace(/\/*$/, '/'), window.location.href)
    const response = await fetch(new URL('../health', base), { cache: 'no-cache' })
    if (!response.ok) {
      return undefined
    }
    const data: unknown = await response.json()
    if (data && typeof data === 'object' && 'version' in data && typeof data.version === 'string') {
      return { version: data.version, shells: Number((data as { shells?: unknown }).shells) || 0 }
    }
  } catch (error) {
    console.warn('API-Status nicht abrufbar', error)
  }
  return undefined
}

/** Ob die Hauptversion der API zur Oberfläche passt */
export function isCompatibleApi(version: string): boolean {
  return Number.parseInt(version.split('.')[0] ?? '', 10) === requiredApiMajor
}
