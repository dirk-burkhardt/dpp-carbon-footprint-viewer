# Changelog

Änderungen der Carbon-Footprint-API, neueste Version oben. Versionen nach [Semantic Versioning](https://semver.org/lang/de/), siehe [README](README.md#versionierung).

## 4.8.0 – 2026-11-18

- Neuer Endpunkt /products/{id}/estimates: Schätzungen für Lebenszyklusphasen ohne deklarierten Footprint (A1-A3 nur ohne Product Footprint, sonst Plausibilitätsprüfung; A4, B6, C1-C4) mit Formel, Eingangswerten und Quellen; Faktoren von DESNZ 2026 und EEA 2024, Nutzungsdauern aus der AfA-Tabelle AV, Voreinstellungen je ECLASS-Segment oder ESPR-Kategorie
- Werkzeug `tools/update_factors.py` übernimmt die Faktoren jährlich aus den amtlichen Dateien in `factor-sources/` (openpyxl als Entwicklungsabhängigkeit)
- Vergleichsdaten der Tests auf den jetzigen Inhalt von `repo` neu aufgenommen, Test zur entfernten Datei „Stahlkugel“ entfernt

## 4.7.0 – 2026-11-18

- Neuer Endpunkt /products/{id}/indicators: Bezugsgrößen aus Technical Data in SI-Einheiten (Masse, Leistung, Lebensdauer, Maße, Volumen) mit Fundstelle und Materialangaben

## 4.6.0 – 2026-11-18

- Uploads werden mit CFA_UPLOAD_DIR in einem Ordner abgelegt (im Container repo/uploads, getrennt vom statischen Bestand), Anhänge werden aus der Datei gelesen; beim Start werden frühere Uploads dort gelöscht, andere Dateien bleiben unberührt; ist der Ordner nicht beschreibbar, bleiben Uploads im Arbeitsspeicher
- Über Links geladene Dateien werden nach `CFA_UPLOAD_TTL_HOURS` verworfen und beim nächsten Abruf neu geladen
- Option `--uploadDir`

## 4.5.0 – 2026-11-18

- Temporäres Hochladen von AAS(X)-Dateien unter `/uploads` (`POST`, `GET`, `DELETE`): nur im Arbeitsspeicher, Größe über `CFA_UPLOAD_MAX_MB` (Standard 25 MB), gelöscht nach `CFA_UPLOAD_TTL_HOURS` (Standard 3 h), bei mehr als `CFA_UPLOAD_MAX_COUNT` Uploads (Standard 20) und bei jedem Neustart; zufällige Upload-IDs, hochgeladene Shells ersetzen nie vorhandene
- Heruntergeladene und hochgeladene Shells teilen sich eine Verwaltung, eine Shell wird erst entfernt, wenn keine Quelle sie mehr nutzt
- CORS erlaubt zusätzlich `POST` und `DELETE` (für Uploads)

## 4.4.0 – 2026-11-15

- Parser für Technical Data (ZVEI 1.0 bis Generic Frame 2.0.4), Handover Documentation (VDI 2770 1.0, 1.2, 2.0 bis 2.0.4) und Maintenance Instructions (1.0 bis 1.0.2) mit Endpunkten unter /products; ConceptDescriptions der Dateien werden gelesen und unter /concept-descriptions bereitgestellt; AAS-Metamodell 3.2 (createdAt/updatedAt, DataSpecificationUom) und AASX-Fallback auf data.xml/data.json
- Kompatibilitätstests mit allen gültigen Beispielen der Metamodell-Releases 3.0.9, 3.1.2 und 3.2.0 (XML und JSON)
  und den AASX-Beispielen 3.1/3.2
- Prüfskript meldet auch neue Releases von aas-specs-metamodel und aas-specs-aasx

## 4.3.0 – 2026-11-15

- Neuer Endpunkt /search: Volltextsuche in allen Shells und Submodels

## 4.2.0 – 2026-11-15

- Versionsunabhängige Parser für IDTA-Submodels: Carbon Footprint 0.9, 1.0-Entwurf und 1.0 bis 1.0.3 (Metamodell 3.0/3.1) inkl. Battery-Passport-PCF, Digital Nameplate 1.0 bis 3.0.3, Contact Information, Hierarchical Structures 1.0/1.1; Erkennung von Handover Documentation und Technical Data
- Neue Endpunkte unter `/api/v4/products`: erkannte Templates je Submodel, normalisierter Carbon Footprint mit
  Zusammenfassung je Berechnungsmethode, Typenschild und Produktbaum über alle Shells
- Wert-IRDIs aus ECLASS-Wertelisten werden in Text übersetzt; Submodels ohne SemanticId werden über den idShort
  erkannt, leere Template-Kopien ignoriert
- Tests gegen alle bekannten IDTA-Templates von GitHub (`tests/idta_templates.tar.gz`)

## 4.1.0 – 2026-11-15

- Betrieb als Docker-Container (python:3.13-slim, ohne Root-Rechte, schreibgeschütztes Dateisystem, Healthcheck über /api/health) mit docker-compose.yml; AASX-Dateien aus repo werden nach /opt/repo eingebunden

## 4.0.0 – 2026-11-15

- Neu implementiert in Python mit FastAPI als Ersatz der bisherigen Java-/Spring-Boot-Umsetzung; Antwortformat
  unverändert, damit die Oberfläche weiter funktioniert
- Inkompatibel: Präfix `/api/v4` statt `/api/v3.0`
- Neu: `/api/health`, Konfiguration über Umgebungsvariablen `CFA_*`, Optionen `--host`, `--logLevel`, `--noDocs`,
  `--noExternalShells`
- Neu: IDs werden auch im Standard-Base64 (wie `btoa` im Browser) angenommen, auch mit `/` im codierten Wert
- Sicherheit: SSRF-Schutz und Limits für `/external-shells`, keine Überschreibung vorhandener Shells durch Downloads,
  begrenzter Cache, Größenlimit für AASX-Einträge, sichere Auslieferung aktiver Attachments, Sicherheits-Header,
  CORS nur `GET` ohne Credentials, Standard-Bind auf `127.0.0.1`
- Korrigiert: Elemente ohne `idShort` führten zu HTTP 500; AASX mit fehlerhafter Relation wurde nicht geladen;
  unbekannte Shell bei Submodel- und Attachment-Abfragen liefert 404 statt 500; `--aas`-Dateien wurden doppelt
  geladen; idShorts mit `/` im Pfad
- Abhängigkeiten auf aktuellem Stand, ausschließlich freie Lizenzen (MIT, BSD, Apache-2.0, PSF)

## 0.0.1

- Ursprüngliche Umsetzung in Java (Spring Boot, Eclipse AAS4J) mit Präfix `/api/v3.0`
