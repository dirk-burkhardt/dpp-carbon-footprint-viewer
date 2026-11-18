"""Konfiguration über Kommandozeile und Umgebungsvariablen.

Jede Einstellung lässt sich als Umgebungsvariable mit dem Präfix ``CFA_`` setzen, z. B.
``CFA_AASX=/opt/repo/*.aasx`` oder ``CFA_CORS_ORIGINS=http://localhost:5173``. Listen werden kommagetrennt
angegeben. Kommandozeilenoptionen haben Vorrang vor Umgebungsvariablen.
"""

from __future__ import annotations

import glob
import logging
from pathlib import Path
from typing import Annotated, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

logger = logging.getLogger(__name__)

MiB = 1024 * 1024
CommaList = Annotated[list[str], NoDecode]


class SettingsError(ValueError):
    """Ungültige Kombination von Einstellungen oder nicht lesbare Dateien."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CFA_", extra="ignore")

    # Dateien
    aas: CommaList = Field(default_factory=list, description="AAS-Dateien (XML/JSON), Glob-Muster")
    aasx: CommaList = Field(default_factory=list, description="AASX-Dateien, Glob-Muster")
    check_repos_not_empty: bool = Field(False, description="Abbruch, wenn ein Muster keine Datei findet")
    max_entry_bytes: int = Field(256 * MiB, gt=0, description="Max. entpackte Größe eines Eintrags im AASX")

    # Server
    host: str = Field("127.0.0.1", description="Netzwerkschnittstelle (im Container 0.0.0.0)")
    port: int = Field(8080, ge=1, le=65535)
    log_level: str = Field("INFO")
    forwarded_allow_ips: Optional[str] = Field(
        None, description="IPs von Reverse-Proxys, deren X-Forwarded-Header vertraut wird"
    )
    cors_origins: CommaList = Field(default_factory=list, description="Erlaubte Origins für /api/v4/**")
    docs_enabled: bool = Field(True, description="Swagger unter /api/docs bereitstellen")

    # Statische Dateien
    static_dir: Optional[Path] = None
    not_found_resource: Optional[str] = None
    suppress_404: bool = False

    # Herunterladen über /external-shells
    external_shells_enabled: bool = True
    external_allow_private_networks: bool = Field(
        False, description="Downloads aus privaten Netzen und von localhost erlauben (nur für Tests)"
    )
    external_max_bytes: int = Field(50 * MiB, gt=0)
    external_timeout_seconds: float = Field(30.0, gt=0)
    external_max_cached: int = Field(50, ge=1, description="Max. Anzahl gemerkter heruntergeladener Dateien")

    # Temporäres Hochladen über /uploads (nach Ablauf und bei jedem Neustart gelöscht)
    uploads_enabled: bool = True
    upload_max_mb: float = Field(25.0, gt=0, description="Max. Größe einer hochgeladenen Datei in MB")
    upload_ttl_hours: float = Field(3.0, gt=0, description="Stunden, nach denen ein Upload gelöscht wird")
    upload_max_count: int = Field(20, ge=1, description="Max. Anzahl gleichzeitig gespeicherter Uploads")
    upload_dir: Optional[Path] = Field(
        None, description="Ordner für hochgeladene Dateien (z. B. repo/uploads); leer = nur Arbeitsspeicher"
    )

    @property
    def upload_max_bytes(self) -> int:
        return int(self.upload_max_mb * MiB)

    @property
    def upload_ttl_seconds(self) -> float:
        return self.upload_ttl_hours * 3600

    @field_validator("aas", "aasx", "cors_origins", mode="before")
    @classmethod
    def _split_comma_list(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(value, (list, tuple)):
            return [p.strip() for item in value for p in str(item).split(",") if p.strip()]
        return value

    @field_validator("log_level")
    @classmethod
    def _check_log_level(cls, value: str) -> str:
        value = value.upper()
        if value not in ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"):
            raise ValueError(f"Unbekannter Log-Level {value}")
        return value

    @model_validator(mode="after")
    def _check_dependencies(self) -> Settings:
        if self.not_found_resource and self.static_dir is None:
            raise ValueError("--notFoundResource requires --static being set.")
        if self.suppress_404 and not self.not_found_resource:
            raise ValueError("--suppress404 requires --notFoundResource being set.")
        return self

    def aas_files(self) -> list[Path]:
        return resolve_files(self.aas, self.check_repos_not_empty)

    def aasx_files(self) -> list[Path]:
        return resolve_files(self.aasx, self.check_repos_not_empty)


def resolve_files(patterns: list[str], check_not_empty: bool) -> list[Path]:
    """Löst Glob-Muster (z. B. ``repo/*.aasx``) in Dateien auf."""
    files: list[Path] = []
    for pattern in patterns:
        if glob.has_magic(pattern):
            matches = [Path(m) for m in sorted(glob.glob(pattern)) if Path(m).is_file()]
        else:
            matches = [Path(pattern)] if Path(pattern).exists() else []
        if not matches:
            if check_not_empty:
                raise SettingsError(f"File {pattern} does not exist or match any files.")
            logger.warning("%s passt auf keine Datei", pattern)
            continue
        for path in matches:
            if not path.is_file():
                raise SettingsError(f"File {path.resolve()} is not a file or not readable.")
            files.append(path)
    return files
