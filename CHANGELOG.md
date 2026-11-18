# Changelog

Changelog des Gesamtprojekts. Einträge nach Datum, je Zeile der Teil mit seiner neuen Version. Die Einzelheiten stehen in den Changelogs von [API](carbon-footprint-api/CHANGELOG.md) und [Oberfläche](carbon-footprint-ui/CHANGELOG.md).

## 2026-11-18

- UI 1.4.0: Über Links geladene und hochgeladene Dateien bleiben im Browser unter External assets gelistet, auch nach dem Wechsel zur Übersicht oder einem Neuladen, bis sie nach der Zeit des Servers ablaufen oder entfernt werden
- API 4.6.0: Über Links geladene Dateien werden nach `CFA_UPLOAD_TTL_HOURS` verworfen und beim nächsten Abruf neu geladen
- API 4.6.0: Option `--uploadDir`
- UI 1.4.0: Carbon Footprints kommen aus dem normalisierten Endpunkt der API (`/products/{id}/carbon-footprint`) statt aus eigener Auswertung der Submodelle; damit werden alle Versionen des Templates angezeigt (bisher nur die Struktur von 0.9, Footprints nach 1.0 erschienen mit „carbon footprint provided“, aber ohne Werte). Ohne diesen Endpunkt (fremder AAS-Server) wird wie bisher selbst ausgewertet; Warnungen der API erscheinen mit Asset und Element in der Fehlertabelle
- Konzept `docs/strategie-technical-data-und-hierarchie.md`: Einbindung von Technical Data und Hierarchical Structures in die CO2-Darstellung
- `docker-compose.yml`: `repo/uploads` als einziger beschreibbarer Ordner des API-Containers
- API 4.6.0: Uploads werden mit CFA_UPLOAD_DIR in einem Ordner abgelegt (im Container repo/uploads, getrennt vom statischen Bestand), Anhänge werden aus der Datei gelesen; beim Start werden frühere Uploads dort gelöscht, andere Dateien bleiben unberührt; ist der Ordner nicht beschreibbar, bleiben Uploads im Arbeitsspeicher
- API 4.5.0: Temporäres Hochladen von AAS(X)-Dateien unter `/uploads` (`POST`, `GET`, `DELETE`): nur im Arbeitsspeicher, Größe über `CFA_UPLOAD_MAX_MB` (Standard 25 MB), gelöscht nach `CFA_UPLOAD_TTL_HOURS` (Standard 3 h), bei mehr als `CFA_UPLOAD_MAX_COUNT` Uploads (Standard 20) und bei jedem Neustart; zufällige Upload-IDs, hochgeladene Shells ersetzen nie vorhandene
- API 4.5.0: Heruntergeladene und hochgeladene Shells teilen sich eine Verwaltung, eine Shell wird erst entfernt, wenn keine Quelle sie mehr nutzt
- API 4.5.0: CORS erlaubt zusätzlich `POST` und `DELETE` (für Uploads)
- UI 1.3.0: AAS(X)-Dateien unter „External assets“ hochladen; Größe und Aufbewahrung kommen von der API, beim Entfernen wird der Upload auch auf dem Server gelöscht, Links funktionieren bis zum Ablauf
- UI 1.3.0: Tabs „Pre-loaded assets“ und „External assets“ deutlicher als Tabs gestaltet (aktiver Tab mit farbiger Oberkante, verbunden mit dem Inhalt, Anzahl der Assets), im hellen und dunklen Modus
- UI 1.3.0: Kopfzeile mit Suche bleibt nur auf der Assetauswahl stehen, in den Analysen scrollt sie mit weg; Navigation und Simulationshinweis haften dann am oberen Fensterrand
- UI 1.3.0: Brotkrümel: „Overview of One Asset“ heißt „Overview“, die Simulation heißt „Simulation“ statt „Component Analysis“
- UI 1.3.0: Fehlertabelle: Spalte „Asset“ mit den betroffenen Assets, aufgeklappt jede Fundstelle (Asset und Element); gleiche Warnungen werden je Asset und Element nur einmal gezählt, erneutes Laden erhöht den Zähler nicht mehr
- UI 1.3.0: Compare: Schalter „Opposed bars“ / „Bars side by side“, zeigt beide Balken je Zeile nebeneinander in einem Diagramm
- UI 1.3.0: Fehler „can't access property startsWith, t is undefined“ behoben, der beim Verlassen einer Analyse (z. B. über die Brotkrümel) auftrat
- UI 1.3.0: Nginx im Container: Uploads bis `UPLOAD_MAX_MB` (+1 MB) über `/api/v4/uploads`, höchstens 10 Uploads pro Minute und Client
- Changelogs aus den READMEs in eigene Dateien `CHANGELOG.md` (Projekt, API, Oberfläche) verschoben; `tools/bump_version.py`, API-Test und Versionsprüfung der Oberfläche lesen von dort
- README: Abschnitt „Schnellstart (Docker, lokal)“ mit Einstellungen und allen Adressen im Browser; README der Oberfläche: veralteten Docker-Abschnitt ersetzt
- `CLAUDE.md`: Vorgaben aus `AI_Coding` allgemein beachten und gelegentlich auf Änderungen prüfen

## 2026-11-15

- UI 1.2.5: Logo in der Kopfzeile mit dem Schriftzug „DPPviewer“ statt „CLiCE - DiPP“ (Datei src/assets/DPPviewer-logo.svg, Schrift Quicksand als Pfad)
- UI 1.2.4: Favicon und App-Symbole zeigen das CLiCE-DiPP-Logo (Lupe mit Blatt-Etikett)
- UI 1.2.4: Datasheet: lange Asset-Namen in der Kopfzeile werden gekürzt, der volle Name erscheint beim Überfahren
- UI 1.2.3: Datasheet scrollt bei vielen Assets waagerecht, die linke Spalte mit den Bezeichnungen bleibt dabei stehen
- UI 1.2.2: Datasheet zeigt alle Favoriten, auch ohne CO2-Daten (Zellen mit „no data“); ein nicht ladbares Asset blockiert nicht mehr das ganze Datasheet
- UI 1.2.2: Favoritenbox: Compare und Datasheet mit Symbolen, durch Linien vom Titel abgesetzt; Favoriten in einem eigenen, helleren Bereich
- UI 1.2.2: Statussymbol auf der Startseite rechts unten statt mittig unter den Favoriten
- UI 1.2.2: Fehlertabelle standardmäßig etwa ein Drittel der Fensterhöhe, kompaktere Zeilen, Scrollen ohne Mitscrollen der Seite
- UI 1.2.1: Karte der Übersicht schiebt sich beim Scrollen nicht mehr über die Kopfzeile
- UI 1.2.1: Doppelte Auswahl „More“ (Components, Life Cycles, Simulation) samt Symbol unter der Einzelansicht entfernt, die Navigation links genügt
- UI 1.2.1: Dunkelmodus: Beschriftungen und Linien der Diagramme in Overview, Components, Life Cycles und Simulation in der Schriftfarbe des Themas statt Schwarz; Adressfeld auf der Karte besser lesbar
- UI 1.2.1: Fehlertabelle höher (45 % der Fensterhöhe), am oberen Rand in der Höhe verstellbar, größere Schrift
- UI 1.2.1: Abweichende Berechnungen (CO2eq der Komponenten höher als das des Assets, fehlende Angabe Well-to-Tank/Tank-to-Wheel) erscheinen als Warnung statt als Fehler
- API 4.4.0: Parser für Technical Data (ZVEI 1.0 bis Generic Frame 2.0.4), Handover Documentation (VDI 2770 1.0, 1.2, 2.0 bis 2.0.4) und Maintenance Instructions (1.0 bis 1.0.2) mit Endpunkten unter /products; ConceptDescriptions der Dateien werden gelesen und unter /concept-descriptions bereitgestellt; AAS-Metamodell 3.2 (createdAt/updatedAt, DataSpecificationUom) und AASX-Fallback auf data.xml/data.json
- UI 1.2.0: Neue Gestaltung: Kopfzeile mit Logo, Suche (optional innerhalb der Schalen), Hell/Dunkel und Info; linke Spalte entfällt
- UI 1.2.0: Favoriten per Drag-and-drop sortierbar, in der Favoritenbox die Analysen Compare (die ersten beiden Favoriten) und Datasheet (alle Favoriten); bisherige Favoriten werden übernommen
- UI 1.2.0: Compare als grafischer Vergleich zweier Assets nach dem Konzept der Thesis (Balken in zwei Richtungen um eine Nulllinie, Absolutwerte oder Differenz, Transport und Produkt je Lebenszyklusphase)
- UI 1.2.0: Datasheet ohne eigenes Hinzufügen von Schalen, kompakteres Layout; Summe der Lebenszyklusphasen aus Komponenten korrigiert (Stückzahlen wurden teils doppelt bzw. gar nicht berücksichtigt)
- UI 1.2.0: Klick auf eine Schale öffnet die Einzelansicht, die Auswahlschaltflächen beim Überfahren entfallen; gelber Rahmen nur noch bei Favoriten
- UI 1.2.0: Statussymbol (OK, Warnungen, Fehler mit Anzahl) unter den Favoriten, auf anderen Seiten unten rechts; Klick öffnet eine kompakte Tabelle, gleiche Meldungen werden zusammengefasst
- UI 1.2.0: Globale Fehlermeldung oben entfernt: Ladefehler erscheinen nur noch in der betroffenen Ansicht, auch wenn die Anfrage erst nach einem Seitenwechsel scheitert
- API 4.3.0: Neuer Endpunkt /search: Volltextsuche in allen Shells und Submodels
- API 4.2.0: Versionsunabhängige Parser für IDTA-Submodels: Carbon Footprint 0.9, 1.0-Entwurf und 1.0 bis 1.0.3 (Metamodell 3.0/3.1) inkl. Battery-Passport-PCF, Digital Nameplate 1.0 bis 3.0.3, Contact Information, Hierarchical Structures 1.0/1.1; Erkennung von Handover Documentation und Technical Data
- Prüfskript `tools/check_idta_templates.py` für neue Versionen der IDTA-Submodel-Templates auf GitHub; Hinweis in `CLAUDE.md`, es zu Beginn jeder Arbeitssitzung auszuführen
- UI 1.1.0: Betrieb als Docker-Container mit nginx: Weiterleitung von /api an die API, Laufzeitkonfiguration und Content-Security-Policy aus Umgebungsvariablen, Sicherheits-Header, Caching, Begrenzung der Downloads über URLs; Adresssuche mit GEOCODING_URL=off abschaltbar
- API 4.1.0: Betrieb als Docker-Container (python:3.13-slim, ohne Root-Rechte, schreibgeschütztes Dateisystem, Healthcheck über /api/health) mit docker-compose.yml; AASX-Dateien aus repo werden nach /opt/repo eingebunden
- API 4.0.0: Neuimplementierung in Python (FastAPI) mit Präfix `/api/v4`, Konfiguration über Umgebungsvariablen,
  Sicherheitsüberarbeitung
- UI 1.0.0: umbenannt in `carbon-footprint-ui`, Leaflet/OpenStreetMap statt Mapbox, CLiCE-DiPP-Logo, aktuelle
  Bibliotheken, zahlreiche Fehlerbehebungen, Versionsanzeige
- Projekt aufgeräumt: Java-Umsetzung der API und alter Frontend-Ordner `carbon-trace-main` entfernt, Versionierung
  und Changelogs eingeführt
