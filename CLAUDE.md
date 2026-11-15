# Hinweise für die Arbeit an diesem Projekt

## Versionierung (eigenständig durchführen)

Nach jeder Änderung an `carbon-footprint-api` oder `carbon-footprint-ui` die Version des betroffenen Teils selbst
erhöhen, ohne Rückfrage, nach den Kriterien in `README.md` (Abschnitt „Versionierung“):

    python tools/bump_version.py <api|ui> <major|minor|patch> "<Beschreibung>"

- Eine Erhöhung je Teil und Arbeitsschritt, Stufe nach der schwersten Änderung; weitere Punkte als zusätzliche
  Zeilen unter demselben Changelog-Eintrag ergänzen.
- Bei `major` der API zusätzlich `API_PREFIX` in `src/carbon_footprint_api/__init__.py`, die Standard-URLs der
  Oberfläche (`.env`, `src/lib/apiConfig.ts`) und `requiredApiMajor` in `src/lib/version.ts` anpassen; die
  Oberfläche erhält dann ebenfalls `major`.
- Reine Doku-Änderungen (README, Kommentare) erhöhen keine Version, gehören aber in den Projekt-Changelog.
- Dem Nutzer am Ende nennen, welche Versionen erhöht wurden und warum.

## Weitere Vorgaben

- UI-Gestaltung: Regeln in `AI_Coding/Coding-Rules/UI-Styles.txt` beachten (liegt außerhalb dieses Ordners).
- Keine Schlüssel oder Tokens im Code, nur in `.env`-Dateien. Keine Mailadressen.
- Nur Bibliotheken mit freien Lizenzen (MIT, BSD, Apache-2.0, ISC o. ä.), keine kommerziellen.
- Vor Abschluss: API `pytest`, `ruff check`, `mypy`; Oberfläche `npm run build` und `npm run lint`.
