#!/bin/sh
# Erzeugt beim Start des Containers die Laufzeitkonfiguration der Oberfläche (/config.json) und die
# nginx-Konfiguration mit passender Content-Security-Policy. Wird vom Entrypoint des nginx-Images ausgeführt.
set -eu

DEFAULT_TILE_URL="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
DEFAULT_GEOCODING_URL="https://nominatim.openstreetmap.org"

mkdir -p /tmp/runtime /tmp/nginx/conf.d

json_escape() {
    printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

# Ursprung (Schema, Host, Port) einer URL; der Leaflet-Platzhalter {s} wird zu einem CSP-Platzhalter
origin() {
    printf '%s' "$1" | sed -E -e 's#^(https?://[^/?#]+).*#\1#' -e 's#\{s\}#*#g'
}

tile_url=${MAP_TILE_URL:-$DEFAULT_TILE_URL}
geocoding_url=${GEOCODING_URL:-$DEFAULT_GEOCODING_URL}

# config.json: nur gesetzte Werte, sonst gelten die Standardwerte aus dem Build
{
    printf '{\n'
    printf '  "assetAdministrationShellRegistryUrl": "%s",\n' "$(json_escape "${ASSET_ADMINISTRATION_SHELL_REGISTRY_URL:-}")"
    printf '  "assetAdministrationShellRepositoryUrl": "%s",\n' "$(json_escape "${ASSET_ADMINISTRATION_SHELL_REPOSITORY_URL:-}")"
    printf '  "assetAdministrationShellSubmodelRepositoryUrl": "%s",\n' "$(json_escape "${ASSET_ADMINISTRATION_SHELL_SUBMODEL_REPOSITORY_URL:-}")"
    printf '  "assetAdministrationShellAdditionalsUrl": "%s",\n' "$(json_escape "${ASSET_ADMINISTRATION_SHELL_ADDITIONALS_URL:-}")"
    printf '  "preferSubmodelRepository": "%s",\n' "$(json_escape "${PREFER_SUBMODELS_REPOSITORY:-}")"
    printf '  "mapTileUrl": "%s",\n' "$(json_escape "${MAP_TILE_URL:-}")"
    printf '  "mapAttribution": "%s",\n' "$(json_escape "${MAP_ATTRIBUTION:-}")"
    printf '  "geocodingUrl": "%s"\n' "$(json_escape "${GEOCODING_URL:-}")"
    printf '}\n'
} > /tmp/runtime/config.json

# Content-Security-Policy: nur eigene Skripte; Bilder auch vom Kachelserver, Verbindungen auch zum Geocoding
img_src="'self' data: blob: $(origin "$tile_url")"
connect_src="'self'"
if [ "$geocoding_url" != "off" ]; then
    connect_src="$connect_src $(origin "$geocoding_url")"
fi
csp="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src $img_src; connect-src $connect_src; font-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'"

sed_escape() {
    printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'
}

# Grenze für Uploads: UPLOAD_MAX_MB (Standard 25) aufgerundet plus 1 MB für den Rahmen der Anfrage
upload_max_mb=${UPLOAD_MAX_MB:-25}
case "$upload_max_mb" in
    ''|*[!0-9.]*) echo "dppviewer: UPLOAD_MAX_MB=$upload_max_mb ist keine Zahl" >&2; exit 1 ;;
esac
upload_body_limit="$(awk -v mb="$upload_max_mb" 'BEGIN { n = int(mb); if (n < mb) n++; print n + 1 }')m"

sed -e "s|@CSP@|$(sed_escape "$csp")|" \
    -e "s|@UPLOAD_BODY_LIMIT@|$upload_body_limit|" \
    -e "s|@API_UPSTREAM@|$(sed_escape "${API_UPSTREAM:-api:8080}")|" \
    -e "s|@DNS_RESOLVER@|$(sed_escape "${DNS_RESOLVER:-127.0.0.11}")|" \
    /etc/nginx/dppviewer/default.conf.template > /tmp/nginx/conf.d/default.conf

echo "dppviewer: Konfiguration erzeugt (API: ${API_UPSTREAM:-api:8080}, Karten: $(origin "$tile_url"), Uploads bis $upload_body_limit)"
