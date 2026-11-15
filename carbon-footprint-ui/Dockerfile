# syntax=docker/dockerfile:1
# Carbon-Footprint-UI als Container: Build mit Node, Auslieferung mit nginx (ohne Root-Rechte).
# Gebaut und gestartet über ../docker-compose.yml.

# --- Build ----------------------------------------------------------------------------------------------------------
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# Versionsprüfung, Typcheck und Produktions-Build
RUN npm run build

# --- Laufzeit -------------------------------------------------------------------------------------------------------
FROM nginxinc/nginx-unprivileged:1.29-alpine
ARG VERSION=dev
LABEL org.opencontainers.image.title="DPPviewer Carbon-Footprint-UI" \
      org.opencontainers.image.description="Oberfläche zur Analyse von Carbon Footprints aus AAS/AASX" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.licenses="Apache-2.0"

USER root
# Eigene Konfiguration statt der mitgelieferten; die Laufzeitdateien entstehen beim Start unter /tmp
RUN rm -f /etc/nginx/conf.d/default.conf
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/default.conf.template docker/security-headers.conf /etc/nginx/dppviewer/
COPY --chmod=755 docker/40-dppviewer-config.sh /docker-entrypoint.d/40-dppviewer-config.sh
COPY --from=build /app/dist /usr/share/nginx/html
USER 101

# Ziel für /api (Dienstname und Port im Compose-Netz) sowie Karten- und Geocoding-Dienste
ENV API_UPSTREAM=api:8080 \
    DNS_RESOLVER=127.0.0.11 \
    MAP_TILE_URL="" \
    MAP_ATTRIBUTION="" \
    GEOCODING_URL=""

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
