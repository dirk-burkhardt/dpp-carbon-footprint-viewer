"""Prüft, ob es auf GitHub neue Versionen der beobachteten IDTA-Submodel-Templates oder AAS-Formate gibt.

Quellen: https://github.com/admin-shell-io/submodel-templates (Ordner published/ und deprecated/) sowie die
Releases von aas-specs-metamodel (Metamodell, XML-/JSON-Schema) und aas-specs-aasx (Paketformat).
Beobachtet wird, was in carbon-footprint-api/src/carbon_footprint_api/submodels/known_templates.json steht.

Aufruf (im Projektordner, nur Standardbibliothek):

    python tools/check_idta_templates.py              # Bericht; Exit-Code 1, wenn es neue Versionen gibt
    python tools/check_idta_templates.py --fixtures   # Templates und Formatbeispiele laden, Testdaten neu erzeugen
    python tools/check_idta_templates.py --accept     # neue Versionen/Releases in known_templates.json übernehmen

Für eine neue Version zeigt der Bericht, welche Elemente (idShort-Pfad, SemanticId) gegenüber der letzten
bekannten Version hinzugekommen oder weggefallen sind. Ist nichts strukturell neu, genügt meist --accept und
--fixtures; sonst wird der Parser in carbon_footprint_api/submodels angepasst.

Ein Token in der Umgebungsvariable GITHUB_TOKEN erhöht das Abruflimit der GitHub-API (optional).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import io
import json
import os
import re
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "carbon-footprint-api"
CATALOG = API / "src" / "carbon_footprint_api" / "submodels" / "known_templates.json"
VALUE_IDS = API / "src" / "carbon_footprint_api" / "submodels" / "value_ids.json"
FIXTURES = API / "tests" / "idta_templates.tar.gz"
FORMAT_FIXTURES = API / "tests" / "aas_format_examples.tar.gz"
_RELEASE_VERSION = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")
BRANCH = "main"
TIMEOUT = 60
_VERSION_SEGMENT = re.compile(r"^\d+$")
_IRDI_VERSION = re.compile(r"#\d{3}$")


def _request(url: str) -> bytes:
    headers = {"User-Agent": "DPPviewer-template-check", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)  # noqa: S310 - feste https-Adressen
    for attempt in range(3):  # Proxys und GitHub liefern gelegentlich kurzzeitig 502/503
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:  # noqa: S310
                data: bytes = response.read()
                return data
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 2:
                raise
        except urllib.error.URLError:
            if attempt == 2:
                raise
        time.sleep(2 * (attempt + 1))
    raise OSError(f"{url} nicht erreichbar")


def load_catalog() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(CATALOG.read_text(encoding="utf-8"))
    return data


def github_tree(repository: str) -> list[dict[str, Any]]:
    url = f"https://api.github.com/repos/{repository}/git/trees/{BRANCH}?recursive=1"
    data = json.loads(_request(url))
    if data.get("truncated"):
        print("Warnung: GitHub hat den Dateibaum gekürzt, der Bericht kann unvollständig sein.", file=sys.stderr)
    tree: list[dict[str, Any]] = data["tree"]
    return tree


def raw_url(repository: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{repository}/{BRANCH}/{urllib.parse.quote(path)}"


def versions(tree: list[dict[str, Any]], folder: str) -> dict[str, list[str]]:
    """Versionsordner einer Familie (z. B. ``1/0/3``) mit ihren Dateien, aus published/ und deprecated/."""
    result: dict[str, list[str]] = {}
    for entry in tree:
        if entry["type"] != "blob":
            continue
        path = entry["path"]
        for area in ("published", "deprecated"):
            prefix = f"{area}/{folder}/"
            if not path.startswith(prefix):
                continue
            parts = path[len(prefix) :].split("/")
            segments = []
            for part in parts[:-1]:
                if not _VERSION_SEGMENT.match(part):
                    break
                segments.append(part)
            if segments and len(segments) == len(parts) - 1:
                result.setdefault("/".join(segments), []).append(path)
    return result


def template_json(files: list[str]) -> str | None:
    """Bevorzugte JSON-Datei einer Version: Template für Metamodell 3.0, ohne reine Beispieldaten."""
    candidates = [f for f in files if f.lower().endswith(".json") and "without_examplevalues" not in f]
    candidates.sort(key=lambda f: ("V3.1" in f, "Template" not in f, "Sample" in f or "Example" in f, f))
    return candidates[0] if candidates else None


def _sid(element: dict[str, Any]) -> str:
    keys = (element.get("semanticId") or {}).get("keys") or [{}]
    value = str(keys[0].get("value") or "")
    return _IRDI_VERSION.sub("", value) if "#" in value and not value.startswith("http") else value


def structure(data: dict[str, Any]) -> set[str]:
    """Elemente aller Submodels als ``Pfad [Typ] SemanticId``."""
    result: set[str] = set()

    def walk(element: dict[str, Any], path: str) -> None:
        here = f"{path}/{element.get('idShort') or '*'}"
        result.add(f"{here} [{element.get('modelType')}] {_sid(element)}")
        value = element.get("value")
        for child in [*(value if isinstance(value, list) else []), *element.get("statements", [])]:
            if isinstance(child, dict) and "modelType" in child:
                walk(child, here)

    for sm in data.get("submodels", []):
        result.add(f"Submodel {_sid(sm)}")
        for element in sm.get("submodelElements", []):
            walk(element, "")
    return result


def _fetch_all(urls: list[str]) -> list[bytes]:
    """Lädt mehrere Dateien parallel (Reihenfolge wie ``urls``)."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(_request, urls))


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(p) for p in version.split("/"))


def report(catalog: dict[str, Any], tree: list[dict[str, Any]]) -> dict[str, list[str]]:
    repository = catalog["repository"]
    new: dict[str, list[str]] = {}
    for fam in catalog["families"]:
        found: dict[str, list[str]] = {}
        for folder in fam["folders"]:
            found.update(versions(tree, folder))
        known = set(fam["knownVersions"])
        added = sorted(set(found) - known, key=_version_key)
        missing = sorted(known - set(found), key=_version_key)
        status = "neu: " + ", ".join(added) if added else "aktuell"
        print(f"{fam['idta']:13} {fam['name']}: {len(found)} Versionen, {status}")
        for version in missing:
            print(f"    nicht mehr auf GitHub: {version}")
        if not added:
            continue
        new[fam["key"]] = added
        previous = max(known & set(found), key=_version_key, default=None)
        base = template_json(found[previous]) if previous else None
        base_structure = structure(json.loads(_request(raw_url(repository, base)))) if base else set()
        for version in added:
            print(f"  Version {version}:")
            for path in found[version]:
                print(f"    {path}")
            target = template_json(found[version])
            if target is None:
                print("    (keine JSON-Datei, Struktur nicht verglichen)")
                continue
            current = structure(json.loads(_request(raw_url(repository, target))))
            sids = {s.split(" ", 1)[1] for s in current if s.startswith("Submodel ")}
            unknown = {
                s for s in sids if s not in fam["semanticIds"] and _IRDI_VERSION.sub("", s) not in fam["semanticIds"]
            }
            if unknown:
                print(f"    NEUE SemanticId des Submodels: {', '.join(sorted(unknown))} → Parser erweitern")
            if base_structure:
                plus, minus = sorted(current - base_structure), sorted(base_structure - current)
                print(f"    gegenüber {previous}: {len(plus)} Elemente neu, {len(minus)} entfallen")
                for line in plus[:40]:
                    print(f"      + {line}")
                for line in minus[:40]:
                    print(f"      - {line}")
                if not plus and not minus:
                    print("    Struktur unverändert → --accept und --fixtures genügen")
    return new


def releases(repository: str) -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = json.loads(
        _request(f"https://api.github.com/repos/{repository}/releases?per_page=100")
    )
    return [r for r in data if not r.get("draft")]


def release_version(tag: str) -> tuple[int, ...]:
    """``v3.1.2`` -> (3, 1, 2); ``IDTA-01001-3-0-1_schemasV3.0.9`` -> (3, 0, 9)."""
    matches = _RELEASE_VERSION.findall(tag)
    if not matches:
        return (0,)
    return tuple(int(p) for p in matches[-1] if p)


def format_report(catalog: dict[str, Any]) -> dict[str, list[str]]:
    """Neue Releases der Formatspezifikationen (Metamodell, AASX)."""
    new: dict[str, list[str]] = {}
    for fmt in catalog.get("formats", []):
        found = releases(fmt["repository"])
        known = set(fmt["knownReleases"])
        added = [r for r in found if r["tag_name"] not in known]
        status = "neu: " + ", ".join(r["tag_name"] for r in added) if added else "aktuell"
        print(f"{fmt['idta']:13} {fmt['name']}: {len(found)} Releases, {status}")
        for r in added:
            print(f"    {r['tag_name']} vom {str(r.get('published_at'))[:10]}: {r.get('html_url')}")
            print("    Changelog prüfen (documentation/…/changelog.adoc), Leser in aas/model.py bzw. aas/package.py")
            print("    anpassen; --fixtures lädt die Beispieldateien des Releases als Testfälle")
        if added:
            new[fmt["key"]] = [r["tag_name"] for r in added]
    return new


def accept(catalog: dict[str, Any], new: dict[str, list[str]], new_formats: dict[str, list[str]]) -> None:
    for fam in catalog["families"]:
        if fam["key"] in new:
            fam["knownVersions"] = sorted({*fam["knownVersions"], *new[fam["key"]]}, key=_version_key)
    for fmt in catalog.get("formats", []):
        if fmt["key"] in new_formats:
            fmt["knownReleases"] = sorted({*fmt["knownReleases"], *new_formats[fmt["key"]]}, key=release_version)
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{CATALOG.relative_to(ROOT)} aktualisiert.")


def build_fixtures(catalog: dict[str, Any], tree: list[dict[str, Any]]) -> None:
    """Alle JSON-Dateien der bekannten Versionen als Testdaten der API (tests/idta_templates.tar.gz)."""
    repository = catalog["repository"]
    buffer = io.BytesIO()
    value_ids: dict[str, str] = {}
    count = 0
    wanted: list[tuple[str, str]] = []
    for fam in catalog["families"]:
        found: dict[str, list[str]] = {}
        for folder in fam["folders"]:
            found.update(versions(tree, folder))
        for version in fam["knownVersions"]:
            for path in found.get(version, []):
                if path.lower().endswith(".json") and "without_examplevalues" not in path:
                    wanted.append((f"idta_templates/{fam['key']}/{version}/{Path(path).name}", path))
    contents = _fetch_all([raw_url(repository, path) for _, path in wanted])
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for (name, _), data in zip(wanted, contents, strict=True):
            _collect_value_ids(json.loads(data), value_ids)
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
            count += 1
    FIXTURES.write_bytes(buffer.getvalue())
    print(f"{count} Templates nach {FIXTURES.relative_to(ROOT)} geschrieben.")
    _write_value_ids(value_ids)


def _latest_per_minor(tags: list[str]) -> list[str]:
    best: dict[tuple[int, ...], str] = {}
    for tag in tags:
        minor = release_version(tag)[:2]
        if minor not in best or release_version(tag) > release_version(best[minor]):
            best[minor] = tag
    return [best[k] for k in sorted(best)]


def build_format_fixtures(catalog: dict[str, Any]) -> None:
    """Beispieldateien der Formatspezifikationen als Testdaten (tests/aas_format_examples.tar.gz).

    Metamodell: je Minor-Version das neueste Release, daraus die gültigen Beispiele ``maximal`` und ``minimal``
    jeder Klasse in JSON und XML. AASX: das Beispielpaket jedes bekannten Releases.
    """
    buffer = io.BytesIO()
    wanted: list[tuple[str, str]] = []
    for fmt in catalog.get("formats", []):
        repository = fmt["repository"]
        for tag in _latest_per_minor(fmt["knownReleases"]):
            ref = urllib.parse.quote(tag)
            tree = json.loads(_request(f"https://api.github.com/repos/{repository}/git/trees/{ref}?recursive=1"))
            version = ".".join(str(p) for p in release_version(tag))
            for entry in tree["tree"]:
                path = entry["path"]
                if entry["type"] != "blob":
                    continue
                url = f"https://raw.githubusercontent.com/{repository}/{ref}/{urllib.parse.quote(path)}"
                if fmt["key"] == "metamodel" and "/examples/generated/" in path:
                    schema, rest = path.split("/examples/generated/", 1)
                    if rest.rsplit("/", 1)[-1] in ("maximal.json", "minimal.json", "maximal.xml", "minimal.xml"):
                        wanted.append((f"metamodel/{version}/{schema.rsplit('/', 1)[-1]}/{rest}", url))
                elif fmt["key"] == "aasx" and path.startswith("examples/") and path.lower().endswith(".aasx"):
                    wanted.append((f"aasx/{version}/{Path(path).name}", url))
    contents = _fetch_all([url for _, url in wanted])
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for (name, _), data in zip(wanted, contents, strict=True):
            info = tarfile.TarInfo(f"aas_format_examples/{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    count = len(wanted)
    FORMAT_FIXTURES.write_bytes(buffer.getvalue())
    print(f"{count} Formatbeispiele nach {FORMAT_FIXTURES.relative_to(ROOT)} geschrieben.")


def _collect_value_ids(data: dict[str, Any], target: dict[str, str]) -> None:
    for cd in data.get("conceptDescriptions", []):
        for eds in cd.get("embeddedDataSpecifications", []):
            value_list = (eds.get("dataSpecificationContent") or {}).get("valueList") or {}
            for pair in value_list.get("valueReferencePairs", []):
                keys = (pair.get("valueId") or {}).get("keys") or [{}]
                value_id = str(keys[0].get("value") or "").strip()
                if "#07-" in value_id and pair.get("value"):
                    target.setdefault(_IRDI_VERSION.sub("", value_id), str(pair["value"]).strip())


def _write_value_ids(value_ids: dict[str, str]) -> None:
    old = json.loads(VALUE_IDS.read_text(encoding="utf-8")) if VALUE_IDS.exists() else {"values": {}}
    merged = {**value_ids, **old.get("values", {})}  # vorhandene Texte bleiben stabil
    content = {
        "_comment": "ECLASS-Wert-IRDIs (0173-1#07-…) und ihre Texte aus den ConceptDescriptions der IDTA-Templates. "
        "Erzeugt mit tools/check_idta_templates.py --fixtures.",
        "values": dict(sorted(merged.items())),
    }
    VALUE_IDS.write_text(json.dumps(content, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(merged)} Wert-IRDIs in {VALUE_IDS.relative_to(ROOT)}.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--accept", action="store_true", help="neue Versionen in known_templates.json übernehmen")
    parser.add_argument("--skip-formats", action="store_true", help="Releases der Formatspezifikationen nicht prüfen")
    parser.add_argument("--fixtures", action="store_true", help="Testdaten der API aus GitHub neu erzeugen")
    args = parser.parse_args(argv)
    catalog = load_catalog()
    try:
        tree = github_tree(catalog["repository"])
        new = report(catalog, tree)
        new_formats = {} if args.skip_formats else format_report(catalog)
        if args.accept and (new or new_formats):
            accept(catalog, new, new_formats)
            new, new_formats = {}, {}
        if args.fixtures:
            build_fixtures(load_catalog(), tree)
            if not args.skip_formats:
                build_format_fixtures(load_catalog())
    except OSError as e:
        sys.stdout.flush()
        print(f"GitHub nicht erreichbar: {e}", file=sys.stderr)
        return 2
    if new or new_formats:
        print("\nEs gibt neue Template-Versionen oder Format-Releases (siehe oben).")
        return 1
    print("\nAlle beobachteten Templates und Formate sind auf dem bekannten Stand.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
