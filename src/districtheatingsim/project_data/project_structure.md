# Projektstruktur

## Einleitung
In diesem Dokument wird die Verzeichnisstruktur der Projektordner visualisiert. Diese wird beim erstellen eines Projektes automatisch generiert. Die enthaltenen Dateien werden Standardmäßig dort erzeugt.

## Projektverzeichnis

Dies ist die Struktur der Projektordner:

- Projekt
    - Definition Quartier IST
        - Gebäude_IST.csv (Initiale Beschreibung des Quartiers anhand von Daten im IST-Zustand)
    - Eingangsdaten allgemein
        - Straßen.geojson (standortspezifisch --> Stadt, Stadtteil)
        - LOD2_data.geojson (standortspezifisch --> Stadt, Stadtteil)
        - zusätzliche Daten wie Wassertemepraturen, andere TRY-, COP-Daten (standortspezifisch --> Region, Stadt)
    - Variante 1 ... n
        - Gebäudedaten
            - Quartier.geojson (Räumliche Abgrenzung Quartier)
            - OSM_Gebäude.geojson
            - filtered_LOD2.geojson (Varianten an Gebäudestrukturen)
            - LOD2.csv (Varianten an Gebäudedaten)
        - Wärmenetz
            - Erzeugerstandorte (Eingangsdaten)
            - Vorlauf.geojson (generiertes Netz)
            - Rücklauf.geojson (generiertes Netz)
            - HAST.geojson (generiertes Netz)
            - Erzeugeranlagen.geojson (generiertes Netz)
            - Konfiguration Netzinitialisierung.json (thermohydraulische Berechnung)
            - Ergebnisse Netzinitialisierung.csv (thermohydraulische Berechnung)
            - Ergebnisse Netzinitialisierung.p (thermohydraulische Berechnung)
            - dimensioniertes Wärmenetz.geojson (thermohydraulische Berechnung)
        - Lastgang
            - Gebäudelastgang.csv (Gebäude)
            - Lastgang.csv (Netz)
            - calculated_heat_generation.csv (mit Erzeugern)
        - Ergebnisse
            - results.json (Berechnungsergebnisse Wirtschaftlichkeit)
            - results.pdf (Ergebnis-PDF)
            - pv_results.csv
            - Wirtschaftlichkeit_Sanierung.json (noch nicht implementiert)

## Erläuterung der Verzeichnisse und Dateien