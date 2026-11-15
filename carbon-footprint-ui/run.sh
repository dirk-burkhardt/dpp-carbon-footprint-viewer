#!/bin/sh
# Schreibt die Laufzeit-Konfiguration aus Umgebungsvariablen. Leere Werte werden im Frontend ignoriert,
# dann gelten die Standardwerte aus dem Build (.env).
json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
cat > /opt/static/config.json <<JSON
{
  "assetAdministrationShellRegistryUrl": "$(json_escape "$ASSET_ADMINISTRATION_SHELL_REGISTRY_URL")",
  "assetAdministrationShellRepositoryUrl": "$(json_escape "$ASSET_ADMINISTRATION_SHELL_REPOSITORY_URL")",
  "assetAdministrationShellSubmodelRepositoryUrl": "$(json_escape "$ASSET_ADMINISTRATION_SHELL_SUBMODEL_REPOSITORY_URL")",
  "assetAdministrationShellAdditionalsUrl": "$(json_escape "$ASSET_ADMINISTRATION_SHELL_ADDITIONALS_URL")",
  "preferSubmodelRepository": "$(json_escape "$PREFER_SUBMODELS_REPOSITORY")",
  "mapTileUrl": "$(json_escape "$MAP_TILE_URL")",
  "mapAttribution": "$(json_escape "$MAP_ATTRIBUTION")",
  "geocodingUrl": "$(json_escape "$GEOCODING_URL")"
}
JSON
exec "$@"
