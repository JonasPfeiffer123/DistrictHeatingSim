# To dos Stand 27.01.2025

## UI-Management:
### Allgemeines:
- Dialoge sollen bei Programmstart initialisiert werden --> Optimierung Datenhaltung
- Dafür soll auch eine Speicherdatei geschaffen werden, welche für jeden Dialog die Eingaben aus der letzte Verwendung speichert (auch nach Beenden des Programms).
- Wird ein Dialog mehrmals geöffnet, sollen die letzten Parameter wieder geladen werden.
- EXCEPTION-HANDLING
- Vereinfachte Berechnungsansätze identifizieren, Ungenauigkeiten beschreiben, Optimierungspotenzial ermitteln
- Aktuell erfolgen sehr viele Definitionen von Werten in einzelnen Dialogen und Eingaben. Das soll prinzipiell so bleiben.
    - Jedoch wäre auch eine zentrale Dateneingabemöglichkeit sinnvoll. Also Projektweite Vorgabe. Speicherung als projektabhhängige Konfigdatei.
- Softwarearchitektur strukturieren nach MVP
- Fehlende Versionierung nach Änderung von Klassenobjekten etc ist Problem

### Projektmanagement:
- Versionierung der Projektergebnisse --> wie erkenntlich machen, wenn Eingangsdaten verändert wurden? --> Auswirkungen auf Ergebnisse
- Datenhaltung allgemein überdenken

## Funktionalitäten:
### Wärmenetzgenerierung:
- Dateistruktur überdenken
- GeoJSON für Netzbestandteile
    - Festlegen, ob eine geoJSON-Datei für die Speicherung aller Netzbestandteile genutzt werden soll.
    - Implementierung der Datenhaltung in geoJSON-Format, falls entschieden.
- bestehende Netze Laden? --> STANET
    - Ausbauszenarien? 

### Wirtschaftlichkeitsberechnung:
- Kostendefinitionen weiter recherchieren und einarbeiten

### Erzeugerauslegung:
- Ausbau Erzeuger / Speicher
    - Großwärmespeicher, Wasserstoff (Brennstoffzelle / Elektrolyseur --> Abwärme)

### Betrachtung Stromsektor:
- Stromprofile zur Sektorkopplung / variable Strompreise
    - Implementierung von Stromprofilen sowohl auf Verbraucher- als auch auf Erzeugerseite zur Unterstützung der Sektorkopplung.

### Calculate button for all process steps
- define the project and then press one button to calculate everything

## Testing
Test Projekte durcharbeiten:
- Was funktioniert?
- Was funktioniert noch nicht?
    --> Welche Lösungsansätze gibt es dafür?
- Welche Schritte sind vorab nötig?
    --> Wie können diese noch weiter vereinfacht werden?
- Welche Betrachtungen können noch wünschenswert sein?
- Welche Ergebnisse werden benötigt?
    --> Wie müssen diese aufbereitet sein?
- Nacharbeitung bereits durchgeführter Projekte: Können Ergebnisse reproduziert werden?
    --> Ist eine vollständige Betrachtung möglich oder Fehlen dafür Funktionen?
        --> Sind diese sinnvoll implementierbar?


03.05.2025
Liste von EnergySystems einführen. Ergebnis-CSV nicht mehr automatisch speichern, Dateiname abfragen. Benennung EnergySytems beim Speichern. JSON-Speichern speichert alle EnergySystems. Löschen & öffnen von EnergySystems. Variantenvergleich von EnergySystems

SaisonalSpeicher in Optimierung mit einbeziehen, wirtschaftliche Faktoren definieren, in Wirtschaftlichkeitsrechnung mit einbeziehen. InfrastructureCost ggf. noch in EnergySystem integrieren.

Snakemake
https://snakemake.readthedocs.io/en/stable/

To dos pandapipes:
Was sollte jetzt kurzfristig noch geändert werden um eine "fertige" Version zu erhalten. --> sytematisch durchtesten in verschiedenen Varianten --> Beispiele zu systematischen Tests --> benchmarking --> verschieden große Netze?

Fix problem with solar thermal with calculation problem after loading

To dos before PyQt6 migration push:
Check Documentation for unneccacary details, gui documentation can be reduced

check if data needs to be in geojson of generated files

Check functionality from beginning to end for multiple variants
