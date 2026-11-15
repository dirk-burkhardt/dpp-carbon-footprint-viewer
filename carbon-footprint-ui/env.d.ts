/// <reference types="vite/client" />

/** Version der Oberfläche aus package.json (wird beim Bauen eingesetzt) */
declare const __APP_VERSION__: string

interface ImportMetaEnv {
  readonly VITE_API_ASSET_ADMINISTRATION_SHELL_REGISTRY_URL?: string
  readonly VITE_API_ASSET_ADMINISTRATION_SHELL_REPOSITORY_URL?: string
  readonly VITE_API_SUBMODEL_REPOSITORY_URL?: string
  readonly VITE_API_ASSET_ADDITIONALS_URL?: string
  readonly VITE_API_PREFER_SUBMODELS_REPOSITORY?: string
  readonly VITE_MAP_TILE_URL?: string
  readonly VITE_MAP_ATTRIBUTION?: string
  readonly VITE_GEOCODING_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
