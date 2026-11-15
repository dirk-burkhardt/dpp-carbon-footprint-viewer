/**
 * Laufzeit-Konfiguration.
 *
 * Standardwerte kommen aus den Vite-Umgebungsvariablen (.env), können aber beim Start durch /config.json
 * überschrieben werden (z. B. im Container). Leere Werte in config.json überschreiben nichts.
 */
export type AppConfig = {
  // Pflicht: Endpunkte der AAS-API
  assetAdministrationShellRegistryUrl: string
  assetAdministrationShellRepositoryUrl: string
  assetAdministrationShellSubmodelRepositoryUrl: string
  // Optional: ohne diesen Endpunkt können keine Dateien über eine URL geladen werden
  assetAdministrationShellAdditionalsUrl: string
  // /submodels/{submodelIdentifier} statt /shells/{aasIdentifier}/submodels/{submodelIdentifier}
  preferSubmodelRepository: boolean
  // Karte (Leaflet) und Geocoding (Nominatim-kompatibel); leere geocodingUrl schaltet Geocoding ab
  mapTileUrl: string
  mapAttribution: string
  geocodingUrl: string
}

const env = import.meta.env

const apiConfig: AppConfig = {
  assetAdministrationShellRegistryUrl: env.VITE_API_ASSET_ADMINISTRATION_SHELL_REGISTRY_URL ?? '/api/v4',
  assetAdministrationShellRepositoryUrl: env.VITE_API_ASSET_ADMINISTRATION_SHELL_REPOSITORY_URL ?? '/api/v4',
  assetAdministrationShellSubmodelRepositoryUrl: env.VITE_API_SUBMODEL_REPOSITORY_URL ?? '/api/v4',
  assetAdministrationShellAdditionalsUrl: env.VITE_API_ASSET_ADDITIONALS_URL ?? '/api/v4',
  preferSubmodelRepository: env.VITE_API_PREFER_SUBMODELS_REPOSITORY === '1',
  mapTileUrl: env.VITE_MAP_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  mapAttribution:
    env.VITE_MAP_ATTRIBUTION ||
    '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>',
  geocodingUrl: env.VITE_GEOCODING_URL ?? 'https://nominatim.openstreetmap.org'
}

const booleanKeys: (keyof AppConfig)[] = ['preferSubmodelRepository']

export function update(newConfig: Record<string, unknown>) {
  for (const key of Object.keys(apiConfig) as (keyof AppConfig)[]) {
    const value = newConfig[key]
    if (value === undefined || value === null || value === '') {
      continue
    }
    if (booleanKeys.includes(key)) {
      ;(apiConfig as Record<string, unknown>)[key] = value === true || value === '1' || value === 'true'
    } else if (typeof value === 'string') {
      ;(apiConfig as Record<string, unknown>)[key] = value
    } else {
      console.warn(`config.json: ${key} muss ein Text sein und wird ignoriert`)
    }
  }
}

export default apiConfig
