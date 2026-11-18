"""Kommandozeilenoptionen."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any, Optional

from pydantic import ValidationError

from .config import Settings, SettingsError


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="carbon-footprint-api",
        description="Backend für die Generierung von Carbon Footprints aus AAS- und AASX-Dateien. "
        "Alle Optionen lassen sich auch als Umgebungsvariable CFA_<NAME> setzen.",
        argument_default=argparse.SUPPRESS,
    )
    p.add_argument("--port", type=int, help="Port to run the server on (default 8080)")
    p.add_argument("--host", help="Interface to bind to (default 127.0.0.1, in containers 0.0.0.0)")
    p.add_argument("--cors", dest="cors_origins", help="Allowed cors origins (comma separated)")
    p.add_argument(
        "--aas",
        action="append",
        help="Aas-files to add to the lookup repository, comma separated, can be used multiple times",
    )
    p.add_argument(
        "--aasx", action="append", help="Aasx-files to add to the lookup repository, can be used multiple times"
    )
    p.add_argument(
        "--checkReposNotEmpty",
        dest="check_repos_not_empty",
        action="store_true",
        help="When using --aas and --aasx, check whether it matches at least one file and otherwise exit",
    )
    p.add_argument("--static", dest="static_dir", help="Static resources to serve")
    p.add_argument(
        "--notFoundResource",
        dest="not_found_resource",
        help="Relative path of a file inside the static resources directory (specified with --static) "
        "to serve when a 404 error occurs, should start with a /. E.g. /index.html for SPAs.",
    )
    p.add_argument(
        "--suppress404",
        dest="suppress_404",
        action="store_true",
        help="Suppress a 404 return value if notFoundResource is being served (useful for SPAs)",
    )
    p.add_argument("--logLevel", dest="log_level", help="Log level (default INFO)")
    p.add_argument("--noDocs", dest="docs_enabled", action="store_false", help="Disable Swagger under /api/docs")
    p.add_argument(
        "--noExternalShells",
        dest="external_shells_enabled",
        action="store_false",
        help="Disable downloading shells from urls (/external-shells)",
    )
    p.add_argument(
        "--noUploads", dest="uploads_enabled", action="store_false", help="Disable temporary uploads (/uploads)"
    )
    p.add_argument("--uploadMaxMb", dest="upload_max_mb", type=float, help="Max. size of an uploaded file in MB")
    p.add_argument(
        "--uploadTtlHours", dest="upload_ttl_hours", type=float, help="Hours after which an upload is deleted"
    )
    return p


def parse_arguments(argv: Optional[Sequence[str]] = None) -> Settings:
    """Liest Kommandozeile und Umgebungsvariablen. Bei Fehlern wird mit Hilfetext beendet."""
    parser = _parser()
    overrides: dict[str, Any] = vars(parser.parse_args(argv))
    try:
        settings = Settings(**overrides)
        # Muster einmal auflösen, damit --checkReposNotEmpty sofort greift
        settings.aas_files()
        settings.aasx_files()
    except ValidationError as e:
        messages = (err["msg"].removeprefix("Value error, ") for err in e.errors())
        parser.error("Error parsing arguments: " + "; ".join(messages))
    except SettingsError as e:
        parser.error(f"Error parsing arguments: {e}")
    return settings
