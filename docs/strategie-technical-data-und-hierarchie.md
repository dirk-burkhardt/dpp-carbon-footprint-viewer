# Strategie: Technical Data und Hierarchical Structures für die CO2-Darstellung

Stand: 18.11.2026. Stufe 1 und 2 sind umgesetzt (API 4.7.0, Oberfläche 1.5.0), Stufe 3 und 4 warten auf die
Entscheidungen unter „Offene Fragen“.

## Ausgangslage

Der DPPviewer zeigt heute die **deklarierten** Emissionen: Product und Transport Carbon Footprints aus dem
Carbon-Footprint-Submodell, bei Assets mit Stückliste ergänzt um die Footprints der Komponenten. Technical Data
und Hierarchical Structures liest die API bereits (`/products/{id}/technical-data`, `/products/{id}/tree`), die
Oberfläche nutzt aber nur die Hierarchie, um den Komponentenbaum aufzubauen.

Beide Submodelle liefern **keine weiteren Emissionen**, sondern zwei andere Dinge:

1. **Bezugsgrößen** (Masse, Maße, Leistungsaufnahme, Lebensdauer, Material). Mit ihnen werden Footprints
   unterschiedlich großer Assets vergleichbar, und Lücken lassen sich abschätzen.
2. **Struktur** (Komponenten, Stückzahlen, Tiefe). Mit ihr lässt sich zeigen, woher die Emissionen kommen
   und wo Daten fehlen.

## Grundsatz: deklariert und geschätzt nie vermischen

Jeder Wert bekommt eine Herkunft:

| Herkunft | Bedeutung | Darstellung |
|---|---|---|
| deklariert | aus einem Carbon Footprint der Schale | wie heute, volle Farbe |
| aus Komponenten | Summe deklarierter Footprints der Komponenten | wie heute |
| geschätzt | aus Bezugsgrößen und Emissionsfaktoren berechnet | schraffiert oder heller, mit Hinweis auf die Annahmen |
| unbekannt | Komponente oder Phase ohne Daten und ohne Schätzung | als eigener Anteil sichtbar, nicht als null |

Regeln:

- Geschätzt wird nur für Lebenszyklusphasen, die **kein** deklarierter Footprint abdeckt. Die API kennt die
  abgedeckten Phasen bereits (`summary.coveredPhases`). So entsteht keine Doppelzählung.
- Die bestehende Summenregel gilt weiter: Summen je Berechnungsmethode über die Phasen, nie über Methoden.
  Schätzungen bilden eine eigene „Methode“ und werden nur zusammen mit dem deklarierten Wert angezeigt, wenn der
  Nutzer das ausdrücklich einschaltet.
- Die deklarierten Gesamtwerte in Overview, Compare und Datasheet bleiben unverändert. Ein Gesamtwert inklusive
  Schätzungen erscheint immer getrennt und ist als solcher bezeichnet.

## 1. Technical Data

### 1a. Kennzahlen je Bezugsgröße (geringes Risiko, hoher Nutzen)

Die API leitet aus Technical Data (und ersatzweise dem Typenschild) Bezugsgrößen mit Einheit ab und rechnet sie
über die ConceptDescriptions in SI-Einheiten um: Masse in kg, Leistung in W, Volumen in m³, Lebensdauer in
Jahren. Daraus entstehen Intensitäten:

- CO2eq je kg (Material- und Fertigungseffizienz)
- CO2eq je W Nennleistung (bei Antrieben, Netzteilen, Steuerungen)
- CO2eq je Funktionseinheit, wenn das Template sie hergibt (z. B. kWh bei Batterien, schon im Battery-Passport-PCF)

Darstellung: im Overview als zweite Kennzahl unter dem Gesamtwert, in Compare und Datasheet als umschaltbare
Ansicht „absolut / je kg / je W“. Fehlt die Bezugsgröße bei einem der Assets, wird die Ansicht für dieses Asset
mit „keine Angabe“ markiert statt geraten.

### 1b. Schätzung fehlender Phasen

Nur für Phasen, die der Footprint nicht abdeckt. Je Phase eine einfache, nachvollziehbare Formel:

| Phase | Schätzung | benötigte Angaben |
|---|---|---|
| A1 bis A3 (nur als Plausibilitätsprüfung) | Masse × materialspezifischer Faktor | Masse, Material |
| A4 Transport zum Kunden | Masse × Entfernung × Faktor je Verkehrsträger | Masse, Adressen (Typenschild, Footprint) |
| B6 Energie in der Nutzung | Leistung × Betriebsstunden pro Jahr × Lebensdauer × Strommix-Faktor | Leistung, Lebensdauer, Land |
| C1 bis C4 Entsorgung | Masse × Faktor je Material und Entsorgungsweg | Masse, Material |

Annahmen, die die Daten nicht hergeben (Betriebsstunden, Lebensdauer, Strommix, Verkehrsträger), sind
voreingestellt, sichtbar und vom Nutzer änderbar. Die Entfernung kann die Oberfläche schon heute berechnen
(Vincenty-Formel für die Karte).

Bei A1 bis A3 ersetzt die Schätzung nie einen deklarierten Wert. Sie dient als Plausibilitätsprüfung: liegt der
deklarierte Wert weit außerhalb der Schätzung, erscheint ein Hinweis in der Fehlertabelle.

## 2. Hierarchical Structures

Der Komponentenbaum ist vorhanden. Daraus lassen sich ohne neue Daten folgende Auswertungen gewinnen:

- **Eigenanteil und Zukaufanteil:** Footprint des Assets minus Summe der Komponenten-Footprints (mit Stückzahl)
  ergibt den Anteil der eigenen Fertigung. Darstellung als gestapelter Balken „eigene Fertigung / Zukaufteile /
  unbekannt“ im Overview. Die vorhandene Warnung bei negativem Eigenanteil bleibt.
- **Datenabdeckung:** Anteil der Komponenten mit eigenem Footprint, gewichtet nach Stückzahl und, wenn
  vorhanden, nach Masse. Als Kennzahl „Datenabdeckung 72 %“ im Overview und als Spalte in Components.
- **Hotspots:** Pareto-Darstellung der Komponenten, die zusammen 80 % der Emissionen verursachen. Das zeigt,
  wo sich Optimieren lohnt, und verbindet sich mit der vorhandenen Simulation (Komponente tauschen).
- **Lücken füllen:** Komponenten ohne Footprint können über 1b (Masse × Faktor) geschätzt werden und
  erscheinen dann schraffiert im Baum.

## 3. Einbindung in die Oberfläche

Empfehlung: **keine Vermischung in den bestehenden Ansichten, aber eine eigene Ansicht für Schätzungen.**

| Ansicht | Änderung |
|---|---|
| Overview | Intensitäten (je kg, je W), Datenabdeckung, Eigen- und Zukaufanteil. Gesamtwert bleibt deklariert |
| Components | Spalten Datenabdeckung und Anteil am Gesamtwert; Komponenten ohne Daten deutlich markiert; optional geschätzte Werte schraffiert |
| Life Cycle | Ja, hier gehört die Erweiterung hin: je Phase deklariert und geschätzt gestapelt, nicht abgedeckte Phasen sichtbar statt leer. Schalter „Schätzungen anzeigen“, standardmäßig aus |
| neu: Estimates (nach Components) | Alle Schätzungen mit Formel, Eingangswerten (mit Pfad in der Schale), Faktoren samt Quelle und änderbaren Annahmen. Ändert der Nutzer eine Annahme, aktualisieren sich Life Cycle und Overview |
| Compare, Datasheet | Umschalter absolut / je kg / je W; Schätzungen nur mit Schalter |

Die eigene Ansicht ist wichtig, weil Schätzungen ohne sichtbare Annahmen wie Fakten wirken würden. Life Cycle
zeigt das Ergebnis, Estimates erklärt es.

## 4. Architektur

Wie beim Parsen liegt die Berechnung auf dem Server, die Oberfläche stellt nur dar:

- `GET /products/{id}/indicators`: Bezugsgrößen in SI-Einheiten mit Quelle (Submodel, Pfad, Originaleinheit).
- `GET /products/{id}/estimates?lifetimeYears=…&hoursPerYear=…&gridCountry=…`: Schätzungen je Phase mit
  Formel, Eingangswerten, Faktoren und Unsicherheit. Annahmen kommen als Parameter, damit Links den Stand
  festhalten (wie heute die Simulation).
- `GET /products/{id}/tree` erweitert um Datenabdeckung und Anteile je Knoten.
- Emissionsfaktoren in einer versionierten Datei im API-Paket (`factors.json`) mit Quelle und Jahr je Faktor.
  Nur frei nutzbare Quellen, z. B. Strommix der EEA oder des Umweltbundesamts, Transportfaktoren nach GLEC
  Framework. Kommerzielle Datenbanken wie ecoinvent scheiden wegen der Lizenz aus.

## 5. Vorgehen in Stufen

1. **Bezugsgrößen und Intensitäten** (API `indicators`, Overview, Compare, Datasheet). Keine Annahmen nötig.
2. **Auswertungen der Hierarchie** (Eigen- und Zukaufanteil, Datenabdeckung, Hotspots). Keine Annahmen nötig.
3. **Schätzungen B6 und A4** mit Ansicht Estimates und Erweiterung von Life Cycle.
4. **Schätzungen C und Plausibilitätsprüfung A1 bis A3** (braucht Materialangaben, die in den Dateien seltener
   gepflegt sind).

Stufe 1 und 2 sind risikoarm, weil sie nur vorhandene Angaben neu bezieht. Ab Stufe 3 braucht es Entscheidungen.

## Offene Fragen

- Welche Emissionsfaktor-Quellen sind für das Projekt akzeptabel?
- Sollen Schätzungen standardmäßig aus- oder eingeschaltet sein?
- Welche Voreinstellungen für Lebensdauer und Betriebsstunden (je Produktklasse aus der Klassifikation in
  Technical Data, z. B. ECLASS, oder ein einheitlicher Wert)?
