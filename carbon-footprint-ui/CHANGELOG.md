# Changelog

Änderungen der DPPviewer-Oberfläche, neueste Version oben. Versionen nach [Semantic Versioning](https://semver.org/lang/de/), siehe [README](README.md#versionierung).

## 1.5.0 – 2026-11-18

- Kennzahlen im Overview: CO2eq je kg und je W (aus Technical Data), Anteil der eigenen Fertigung und Datenabdeckung der Komponenten
- Components: Tabelle „Hotspots“ mit den Komponenten, die zusammen 80 % der deklarierten Emissionen verursachen (je Komponente der eigene Anteil für alle Einheiten)
- Compare: Umschalter „Absolute / per kg / per W“, gesperrt, wenn einem Asset die Angabe fehlt
- Datasheet: Zeilen Masse, Leistung, CO2eq je kg und je W, eigene Fertigung und Datenabdeckung
- Brotkrümel „Asset Selection“ öffnet wieder den zuletzt gezeigten Reiter (z. B. External assets)

## 1.4.0 – 2026-11-18

- Über Links geladene und hochgeladene Dateien bleiben im Browser unter External assets gelistet, auch nach dem Wechsel zur Übersicht oder einem Neuladen, bis sie nach der Zeit des Servers ablaufen oder entfernt werden
- Carbon Footprints kommen aus dem normalisierten Endpunkt der API (`/products/{id}/carbon-footprint`) statt aus eigener Auswertung der Submodelle; damit werden alle Versionen des Templates angezeigt (bisher nur die Struktur von 0.9, Footprints nach 1.0 erschienen mit „carbon footprint provided“, aber ohne Werte). Ohne diesen Endpunkt (fremder AAS-Server) wird wie bisher selbst ausgewertet; Warnungen der API erscheinen mit Asset und Element in der Fehlertabelle

## 1.3.0 – 2026-11-18

- AAS(X)-Dateien unter „External assets“ hochladen; Größe und Aufbewahrung kommen von der API, beim Entfernen wird der Upload auch auf dem Server gelöscht, Links funktionieren bis zum Ablauf
- Tabs „Pre-loaded assets“ und „External assets“ deutlicher als Tabs gestaltet (aktiver Tab mit farbiger Oberkante, verbunden mit dem Inhalt, Anzahl der Assets), im hellen und dunklen Modus
- Kopfzeile mit Suche bleibt nur auf der Assetauswahl stehen, in den Analysen scrollt sie mit weg; Navigation und Simulationshinweis haften dann am oberen Fensterrand
- Brotkrümel: „Overview of One Asset“ heißt „Overview“, die Simulation heißt „Simulation“ statt „Component Analysis“
- Fehlertabelle: Spalte „Asset“ mit den betroffenen Assets, aufgeklappt jede Fundstelle (Asset und Element); gleiche Warnungen werden je Asset und Element nur einmal gezählt, erneutes Laden erhöht den Zähler nicht mehr
- Compare: Schalter „Opposed bars“ / „Bars side by side“, zeigt beide Balken je Zeile nebeneinander in einem Diagramm
- Fehler „can't access property startsWith, t is undefined“ behoben, der beim Verlassen einer Analyse (z. B. über die Brotkrümel) auftrat
- Nginx im Container: Uploads bis `UPLOAD_MAX_MB` (+1 MB) über `/api/v4/uploads`, höchstens 10 Uploads pro Minute und Client

## 1.2.5 – 2026-11-15

- Logo in der Kopfzeile mit dem Schriftzug „DPPviewer“ statt „CLiCE - DiPP“ (Datei src/assets/DPPviewer-logo.svg, Schrift Quicksand als Pfad)

## 1.2.4 – 2026-11-15

- Favicon und App-Symbole zeigen das CLiCE-DiPP-Logo (Lupe mit Blatt-Etikett)
- Datasheet: lange Asset-Namen in der Kopfzeile werden gekürzt, der volle Name erscheint beim Überfahren

## 1.2.3 – 2026-11-15

- Datasheet scrollt bei vielen Assets waagerecht, die linke Spalte mit den Bezeichnungen bleibt dabei stehen

## 1.2.2 – 2026-11-15

- Datasheet zeigt alle Favoriten, auch ohne CO2-Daten (Zellen mit „no data“); ein nicht ladbares Asset blockiert nicht mehr das ganze Datasheet
- Favoritenbox: Compare und Datasheet mit Symbolen, durch Linien vom Titel abgesetzt; Favoriten in einem eigenen, helleren Bereich
- Statussymbol auf der Startseite rechts unten statt mittig unter den Favoriten
- Fehlertabelle standardmäßig etwa ein Drittel der Fensterhöhe, kompaktere Zeilen, Scrollen ohne Mitscrollen der Seite

## 1.2.1 – 2026-11-15

- Karte der Übersicht schiebt sich beim Scrollen nicht mehr über die Kopfzeile
- Doppelte Auswahl „More“ (Components, Life Cycles, Simulation) samt Symbol unter der Einzelansicht entfernt, die Navigation links genügt
- Dunkelmodus: Beschriftungen und Linien der Diagramme in Overview, Components, Life Cycles und Simulation in der Schriftfarbe des Themas statt Schwarz; Adressfeld auf der Karte besser lesbar
- Fehlertabelle höher (45 % der Fensterhöhe), am oberen Rand in der Höhe verstellbar, größere Schrift
- Abweichende Berechnungen (CO2eq der Komponenten höher als das des Assets, fehlende Angabe Well-to-Tank/Tank-to-Wheel) erscheinen als Warnung statt als Fehler

## 1.2.0 – 2026-11-15

- Neue Gestaltung: Kopfzeile mit Logo, Suche (optional innerhalb der Schalen), Hell/Dunkel und Info; linke Spalte entfällt
- Favoriten per Drag-and-drop sortierbar, in der Favoritenbox die Analysen Compare (die ersten beiden Favoriten) und Datasheet (alle Favoriten); bisherige Favoriten werden übernommen
- Compare als grafischer Vergleich zweier Assets nach dem Konzept der Thesis (Balken in zwei Richtungen um eine Nulllinie, Absolutwerte oder Differenz, Transport und Produkt je Lebenszyklusphase)
- Datasheet ohne eigenes Hinzufügen von Schalen, kompakteres Layout; Summe der Lebenszyklusphasen aus Komponenten korrigiert (Stückzahlen wurden teils doppelt bzw. gar nicht berücksichtigt)
- Klick auf eine Schale öffnet die Einzelansicht, die Auswahlschaltflächen beim Überfahren entfallen; gelber Rahmen nur noch bei Favoriten
- Statussymbol (OK, Warnungen, Fehler mit Anzahl) unter den Favoriten, auf anderen Seiten unten rechts; Klick öffnet eine kompakte Tabelle, gleiche Meldungen werden zusammengefasst
- Globale Fehlermeldung oben entfernt: Ladefehler erscheinen nur noch in der betroffenen Ansicht, auch wenn die Anfrage erst nach einem Seitenwechsel scheitert

## 1.1.0 – 2026-11-15

- Betrieb als Docker-Container mit nginx: Weiterleitung von /api an die API, Laufzeitkonfiguration und Content-Security-Policy aus Umgebungsvariablen, Sicherheits-Header, Caching, Begrenzung der Downloads über URLs; Adresssuche mit GEOCODING_URL=off abschaltbar

## 1.0.0 – 2026-11-15

- Umbenannt von `carbon-trace` in `carbon-footprint-ui`, Logo oben links ist jetzt das CLiCE-DiPP-Logo
- Inkompatibel: nutzt die API 4.x unter `/api/v4`; im Entwicklungsbetrieb leitet Vite `/api` an die API weiter
- Karten mit Leaflet und OpenStreetMap, Adresssuche über Nominatim statt Mapbox (keine kommerzielle Lizenz und kein
  Zugangstoken mehr nötig)
- Versionsanzeige von Oberfläche und API auf der About-Seite
- Aktualisiert: Vue 3.5, vue-router 5, Vite 8, Tailwind CSS 4, daisyUI 5, TypeScript 6, ESLint 10; ungenutzte
  Pakete entfernt (ECharts, pako, htl)
- Korrigiert: Transport-Footprints wurden in der Simulation verworfen; falsche Tooltips im Änderungsdiagramm bei
  aktivem Filter; Brotkrümel der Zwei-Asset-Ansicht; IDs mit Umlauten und Sonderzeichen; fehlgeschlagene
  Anfragen blieben bis zum Neuladen gespeichert; Erkennung des Dunkelmodus; fett gesetzte Namen in Tooltips;
  Simulationslink
- Sicherheit: Attachment-Pfade werden codiert, externe Links mit `noopener`, keine Zugangsdaten im Code,
  `npm audit` ohne Befund
- Ansichten werden erst bei Bedarf geladen (Startpaket 378 statt 995 KB), Typcheck und Lint ohne Fehler

## 0.0.0

- Ursprüngliche Oberfläche `carbon-trace` (Vue 3, Vite 5, Tailwind CSS 3, Mapbox)
