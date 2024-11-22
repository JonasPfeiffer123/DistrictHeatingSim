# To dos Stand 21.11.2024

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

### LOD2-Datenverarbeitung:
- LOD2 Verarbeitung eindeutiger Gestalten, klarer im UI dokumentieren / Erklären was berechnet / verarbeitet wird.
- Versionierung überdenken
- LOD2-Daten laden --> Exception-Handling bei timeout Nominatim geocoding

### Wärmenetzgenerierung:
- Kartenanwendung überarbeiten, Bearbeitungsfunktionen ausweiten / Export von bearbeiteten Layern, Dateistrukturüberdenken

### Einzelversorgungslösungen
- UI-Integration

### Ergebnispräsentation:
- Feedback welche Daten geladen sind und ausgegeben werden.
- PDF-Ausgabe noch weiter ausarbeiten und visuell verbessern.

## Funktionalitäten:
### LOD2-Datenverarbeitung:
- Berechnungsvorgehen überprüfen, Vereinfachungen Herausheben, Detaillierungen vorschlagen

### Wärmenetzgenerierung:
- GeoJSON für Netzbestandteile
    - Festlegen, ob eine geoJSON-Datei für die Speicherung aller Netzbestandteile genutzt werden soll.
    - Implementierung der Datenhaltung in geoJSON-Format, falls entschieden.
- bestehende Netze Laden?
    - Ausbauszenarien? 

### Wärmenetzberechnung:
- **Prio 1:** Pandapipes 0.11 integrieren --> vorraussichtlich verschiedenste Optimierungen in der Berechnungslogik
- Sekundäre Erzeuger hinzufügen
- Bei sehr viel langeweile könnte man auch das manuelle Erstellen von Netzen anfangen. 

### Wirtschaftlichkeitsberechnung:
- Kostendefinitionen weiter recherchieren und einarbeiten

### Erzeugerauslegung:
- Ausbau Erzeuger / Speicher
    - Großwärmespeicher, Wasserstoff (Brennstoffzelle / Elektrolyseur --> Abwärme)

### Einzelversorgungslösung:
- weitere Ergebnisse?
- was braucht man eigentlich?

## Neue Features
### Betrachtung Stromsektor:
- Stromprofile zur Sektorkopplung
    - Implementierung von Stromprofilen sowohl auf Verbraucher- als auch auf Erzeugerseite zur Unterstützung der Sektorkopplung.
- PV-Klasse für Stromerzeugung
    - Stromprofile PV-Anlagen

### MILP based energy system calculation and optimization
- include flixOpt or similar approaches for system optimization

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



