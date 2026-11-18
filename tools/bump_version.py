"""Erhöht die Version von API oder UI und trägt die Änderung in die Changelogs ein.

Aufruf (im Projektordner):

    python tools/bump_version.py api patch "Fehler beim Laden leerer AASX-Dateien behoben"
    python tools/bump_version.py ui minor "Neue Vergleichsansicht"

Teil:   api | ui
Stufe:  major (inkompatible Änderung) | minor (neue Funktion) | patch (Fehlerbehebung)

Geändert werden:
- api: carbon-footprint-api/src/carbon_footprint_api/__init__.py (__version__) und carbon-footprint-api/CHANGELOG.md
- ui:  carbon-footprint-ui/package.json, package-lock.json und carbon-footprint-ui/CHANGELOG.md
- immer: CHANGELOG.md im Projektordner (Changelog des Gesamtprojekts) und die Image-Versionen in docker-compose.yml
"""

from __future__ import annotations

import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_INIT = ROOT / "carbon-footprint-api" / "src" / "carbon_footprint_api" / "__init__.py"
API_CHANGELOG = ROOT / "carbon-footprint-api" / "CHANGELOG.md"
UI_PACKAGE = ROOT / "carbon-footprint-ui" / "package.json"
UI_LOCK = ROOT / "carbon-footprint-ui" / "package-lock.json"
UI_CHANGELOG = ROOT / "carbon-footprint-ui" / "CHANGELOG.md"
ROOT_CHANGELOG = ROOT / "CHANGELOG.md"
COMPOSE = ROOT / "docker-compose.yml"
ENTRY_PREFIX = "## "
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


def add_changelog_entry(changelog: Path, heading: str, line: str) -> None:
    """Insert a changelog entry above the newest one.

    Entries are second-level headings ("## 1.2.3 – 2026-01-01" or "## 2026-01-01"). If the newest entry already
    has the given heading, the line is appended to it instead of creating a new entry.
    """
    text = changelog.read_text(encoding="utf-8")
    lines = text.split("\n")
    first = next((i for i, current in enumerate(lines) if current.startswith(ENTRY_PREFIX)), None)
    if first is None:
        text = text.rstrip("\n") + f"\n\n{heading}\n\n{line}\n"
    elif lines[first] == heading:
        # Newest entry has the same heading: add the line at the top of its list
        position = first + 2 if first + 1 < len(lines) and lines[first + 1] == "" else first + 1
        lines.insert(position, line)
        text = "\n".join(lines)
    else:
        lines[first:first] = [heading, "", line, ""]
        text = "\n".join(lines)
    changelog.write_text(text, encoding="utf-8")


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
        add_changelog_entry(API_CHANGELOG, f"## {new} – {today}", f"- {description}")
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
        add_changelog_entry(UI_CHANGELOG, f"## {new} – {today}", f"- {description}")
        update_compose("ui", new)
        label = "UI"
    else:
        raise SystemExit(f"Unbekannter Teil {part!r}, erlaubt: api, ui")
    add_changelog_entry(ROOT_CHANGELOG, f"## {today}", f"- {label} {new}: {description}")
    print(f"{label}: {old} -> {new}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        raise SystemExit(2)
    main(*sys.argv[1:4])
