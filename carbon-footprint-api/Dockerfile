# syntax=docker/dockerfile:1
# Carbon-Footprint-API als Container. Gebaut und gestartet über ../docker-compose.yml.

# --- Build: Wheels für das Paket und alle Abhängigkeiten -------------------------------------------------------------
FROM python:3.13-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip wheel --wheel-dir /wheels .

# --- Laufzeit -------------------------------------------------------------------------------------------------------
FROM python:3.13-slim
ARG VERSION=dev
LABEL org.opencontainers.image.title="DPPviewer Carbon-Footprint-API" \
      org.opencontainers.image.description="REST-API für AAS-/AASX-Dateien (Carbon Footprints)" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CFA_HOST=0.0.0.0 \
    CFA_PORT=8080 \
    CFA_AASX=/opt/repo/*.aasx

RUN --mount=type=bind,from=build,source=/wheels,target=/wheels \
    pip install --no-index --find-links=/wheels carbon-footprint-api \
    && useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /opt/repo

# Die AASX-Dateien werden als Volume nach /opt/repo eingebunden (schreibgeschützt)
VOLUME ["/opt/repo"]
USER 10001
EXPOSE 8080

# Laden aller Dateien beim Start kann einige Sekunden dauern
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=4).status != 200)"]

CMD ["python", "-m", "carbon_footprint_api"]
