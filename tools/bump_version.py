"""Erhöht die Version von API oder UI und trägt die Änderung in die Changelogs ein.

Aufruf (im Projektordner):

    python tools/bump_version.py api patch "Fehler beim Laden leerer AASX-Dateien behoben"
    python tools/bump_version.py ui minor "Neue Vergleichsansicht"

Teil:   api | ui
Stufe:  major (inkompatible Änderung) | minor (neue Funktion) | patch (Fehlerbehebung)

Geändert werden:
- api: carbon-footprint-api/src/carbon_footprint_api/__init__.py (__version__) und carbon-footprint-api/README.md
- ui:  carbon-footprint-ui/package.json, package-lock.json und carbon-footprint-ui/README.md
- immer: README.md im Projektordner (Changelog des Gesamtprojekts) und die Image-Versionen in docker-compose.yml
"""

from __future__ import annotations

import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_INIT = ROOT / "carbon-footprint-api" / "src" / "carbon_footprint_api" / "__init__.py"
API_README = ROOT / "carbon-footprint-api" / "README.md"
UI_PACKAGE = ROOT / "carbon-footprint-ui" / "package.json"
UI_LOCK = ROOT / "carbon-footprint-ui" / "package-lock.json"
UI_README = ROOT / "carbon-footprint-ui" / "README.md"
ROOT_README = ROOT / "README.md"
COMPOSE = ROOT / "docker-compose.yml"
CHANGELOG_HEADING = "## Changelog"
VERSION_RE = re.compile(r'__version__ = "(\d+)\.(\d+)\.(\d+)"')


def bump(version: str, level: str) -> str:
    major, minor, patch = (int(p) for p in version.split("."))
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    if level == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise SystemExit(f"Unbekannte Stufe {level!r}, erlaubt: major, minor, patch")


def add_changelog_entry(readme: Path, heading: str, line: str) -> None:
    """Fügt unter "## Changelog" einen Eintrag ein (bzw. ergänzt einen vorhandenen gleichen Abschnitt)."""
    text = readme.read_text(encoding="utf-8")
    if CHANGELOG_HEADING not in text:
        raise SystemExit(f"{readme} enthält keinen Abschnitt '{CHANGELOG_HEADING}'")
    head, tail = text.split(CHANGELOG_HEADING, 1)
    tail = tail.lstrip("\n")
    if tail.startswith(heading + "\n"):
        first, rest = tail.split("\n", 1)
        tail = f"{first}\n\n{line}\n" + rest.lstrip("\n")
    else:
        tail = f"{heading}\n\n{line}\n\n" + tail
    readme.write_text(f"{head}{CHANGELOG_HEADING}\n\n{tail}", encoding="utf-8")


def update_compose(service: str, version: str) -> None:
    """Setzt Image-Tag und Build-Argument VERSION des Dienstes in docker-compose.yml."""
    if not COMPOSE.exists():
        return
    text = COMPOSE.read_text(encoding="utf-8")
    text = re.sub(rf"(image: dppviewer-{service}:)\d+\.\d+\.\d+", rf"\g<1>{version}", text)
    block = re.search(rf"\n  {service}:\n(?:    .*\n|\n)*", text)
    if block:
        updated = re.sub(r'(VERSION: ")\d+\.\d+\.\d+(")', rf"\g<1>{version}\g<2>", block.group(0))
        text = text[: block.start()] + updated + text[block.end() :]
    COMPOSE.write_text(text, encoding="utf-8")


def main(part: str, level: str, description: str) -> None:
    today = datetime.date.today().isoformat()
    if part == "api":
        text = API_INIT.read_text(encoding="utf-8")
        match = VERSION_RE.search(text)
        if not match:
            raise SystemExit(f"__version__ nicht gefunden in {API_INIT}")
        old = ".".join(match.groups())
        new = bump(old, level)
        API_INIT.write_text(VERSION_RE.sub(f'__version__ = "{new}"', text, count=1), encoding="utf-8")
        add_changelog_entry(API_README, f"### {new} – {today}", f"- {description}")
        update_compose("api", new)
        label = "API"
    elif part == "ui":
        package = json.loads(UI_PACKAGE.read_text(encoding="utf-8"))
        old = package["version"]
        new = bump(old, level)
        package["version"] = new
        UI_PACKAGE.write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if UI_LOCK.exists():
            lock = json.loads(UI_LOCK.read_text(encoding="utf-8"))
            lock["version"] = new
            lock.get("packages", {}).get("", {})["version"] = new
            UI_LOCK.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        add_changelog_entry(UI_README, f"### {new} – {today}", f"- {description}")
        update_compose("ui", new)
        label = "UI"
    else:
        raise SystemExit(f"Unbekannter Teil {part!r}, erlaubt: api, ui")
    add_changelog_entry(ROOT_README, f"### {today}", f"- {label} {new}: {description}")
    print(f"{label}: {old} -> {new}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        raise SystemExit(2)
    main(*sys.argv[1:4])
