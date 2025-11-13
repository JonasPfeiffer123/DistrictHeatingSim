.. _thermal_storage_architecture:

===============================================
Thermal Storage System Architecture
===============================================

Überblick
=========

Das DistrictHeatingSim-Tool implementiert eine hierarchische Speicherklassenarchitektur mit drei aufeinander aufbauenden Komplexitätsstufen für die Modellierung von thermischen Energiespeichern in Fernwärmesystemen. Diese Architektur ermöglicht die Auswahl des geeigneten Modellierungsansatzes abhängig von der Anwendung, den verfügbaren Daten und der gewünschten Genauigkeit.

.. image:: ../../images/thermal_storage_hierarchy.png
   :width: 100%
   :alt: Hierarchie der Speicherklassen
   :align: center

Klassenarchitektur
==================

Die Speicherklassen bauen hierarchisch aufeinander auf:

.. code-block:: text

    BaseHeatGenerator
            │
            ├─── ThermalStorage (Basisklasse)
                    │
                    ├─── SimpleThermalStorage (Komplexität 1)
                    │
                    ├─── StratifiedThermalStorage (Komplexität 2)
                    │           │
                    │           └─── STES (Komplexität 3)
                    │
                    └─── STES_Animation (Visualisierung)


Jede Klasse erweitert die Funktionalität der vorhergehenden und führt zusätzliche physikalische Effekte ein.

==============================================
Komplexitätsstufe 1: SimpleThermalStorage
==============================================

**Modul:** :py:mod:`districtheatingsim.heat_generators.simple_thermal_storage`

Beschreibung
------------

Die SimpleThermalStorage-Klasse implementiert ein vereinfachtes thermisches Speichermodell basierend auf der Lumped-Capacitance-Methode. Dieses Modell eignet sich für Vorstudien, grundlegende Auslegungsberechnungen und Fälle, in denen Schichtung vernachlässigbar ist.

Hauptmerkmale
-------------

- Einheitliche Temperaturverteilung (uniform temperature)
- Keine thermische Schichtung
- Zeitschrittbasierte Energiebilanzrechnung
- Unterstützte Geometrien: cylindrical (overground/underground), truncated cone/trapezoid (PTES)

Anwendungsbereich
-----------------

**Geeignet für:**
   - Vorläufige Machbarkeitsstudien
   - Kurzzeitpufferspeicher (Stunden bis Tage)
   - Kleine Speichervolumen (<100 m³)
   - Schnelle Sensitivitätsanalysen

**Detaillierte wissenschaftliche Dokumentation:**

Für eine umfassende Darstellung der Berechnungslogik, physikalischen Modelle, numerischen Methoden und Validierung siehe:

.. toctree::
   :maxdepth: 2

   SimpleThermalStorage_Calculation_Logic

==============================================
Komplexitätsstufe 2: StratifiedThermalStorage
==============================================

**Modul:** :py:mod:`districtheatingsim.heat_generators.stratified_thermal_storage`

Beschreibung
------------

Die StratifiedThermalStorage-Klasse erweitert die SimpleThermalStorage um eine mehrschichtige Temperaturverteilung. Dies ermöglicht die Abbildung thermischer Schichtungseffekte, die besonders bei großen saisonalen Wärmespeichern eine entscheidende Rolle spielen.

Hauptmerkmale
-------------

- Multi-Layer-Temperaturmodellierung
- Schichtspezifische Wärmeverluste
- Thermische Leitung zwischen Schichten
- Geschichtete Lade-/Entladestrategien

Anwendungsbereich
-----------------

**Geeignet für:**
   - Große saisonale Wärmespeicher (>1000 m³)
   - Erdbeckenspeicher (PTES) mit ausgeprägter Schichtung
   - Detaillierte Temperaturprofilanalysen
   - Optimierung von Lade-/Entladestrategien

**Detaillierte wissenschaftliche Dokumentation:**

Für eine umfassende Darstellung der Schichtungsphysik, Layer-Berechnungen, Inter-Layer Conduction und dem 6-Schritte-Simulationsalgorithmus siehe:

.. toctree::
   :maxdepth: 2

   StratifiedThermalStorage_Calculation_Logic

==============================================
Komplexitätsstufe 3: STES (Seasonal Thermal Energy Storage)
==============================================

**Modul:** :py:mod:`districtheatingsim.heat_generators.STES`

Beschreibung
------------

Die STES-Klasse stellt die höchste Komplexitätsstufe dar und erweitert die StratifiedThermalStorage um detaillierte Massenstrommodellierung, hydraulische Randbedingungen und realistische Systemintegration.

Hauptmerkmale
-------------

- Massenstrommodellierung mit temperaturabhängiger Regelung
- Hydraulische Randbedingungen (Vor- und Rücklauftemperaturen)
- Stagnationsschutz und Überhitzungserkennung
- Unterdeckungsanalyse (unmet demand tracking)
- Realistische Systemintegration mit Erzeugern und Verbrauchern

Anwendungsbereich
-----------------

**Geeignet für:**
   - Detaillierte saisonale Wärmespeicherplanung
   - Systemintegrationsstudien mit realen Erzeugern und Verbrauchern
   - Optimierung von Betriebsstrategien
   - Wirtschaftlichkeitsanalysen
   - Vor- und Rücklauftemperaturanalysen

**Detaillierte wissenschaftliche Dokumentation:**

Für eine umfassende Darstellung der Massenstrom-basierten Energieübertragung, operationalen Randbedingungen und des 7-Schritte-Simulationsalgorithmus siehe:

.. toctree::
   :maxdepth: 2

   STES_Calculation_Logic

==============================================
Vergleich der Modellkomplexitäten
==============================================

.. list-table:: Modellvergleich
   :widths: 25 25 25 25
   :header-rows: 1

   * - **Eigenschaft**
     - **SimpleThermalStorage**
     - **StratifiedThermalStorage**
     - **STES**
   * - **Temperaturverteilung**
     - Uniform (1 Knoten)
     - Geschichtet (5-20 Schichten)
     - Geschichtet (5-20 Schichten)
   * - **Thermische Schichtung**
     - ❌ Nicht vorhanden
     - ✅ Modelliert
     - ✅ Modelliert + Erhalt
   * - **Massenströme**
     - ❌ Nicht berücksichtigt
     - ❌ Nicht berücksichtigt
     - ✅ Vollständig modelliert
   * - **Vor-/Rücklauftemperaturen**
     - ❌ Nicht vorhanden
     - ❌ Nicht vorhanden
     - ✅ Erzeuger- und Verbraucherseite
   * - **Betriebsgrenzen**
     - Nur T_min / T_max
     - Nur T_min / T_max
     - ✅ Rücklauf-/Vorlaufgrenzen
   * - **Stagnationsanalyse**
     - ❌ Nicht vorhanden
     - ❌ Nicht vorhanden
     - ✅ Überschusswärme getrackt
   * - **Unterdeckungsanalyse**
     - ❌ Nicht vorhanden
     - ❌ Nicht vorhanden
     - ✅ Unmet demand getrackt
   * - **Wärmeverluste**
     - Pauschal
     - Schichtspezifisch
     - Schichtspezifisch
   * - **Inter-Layer Conduction**
     - ❌ Nicht vorhanden
     - ✅ Modelliert
     - ✅ Modelliert
   * - **Anwendung**
     - Vorstudien, kleine Speicher
     - Große PTES, Stratifikation
     - Detailplanung, Systemintegration
   * - **Genauigkeit**
     - Niedrig-Mittel
     - Mittel-Hoch
     - Hoch

Auswahlkriterien
----------------

**Wählen Sie SimpleThermalStorage wenn:**
   - Schnelle Überschlagsrechnungen erforderlich sind
   - Speichervolumen < 100 m³
   - Speicherdauer < 1 Woche
   - Schichtung vernachlässigbar ist
   - Sensitivitätsstudien mit vielen Varianten

**Wählen Sie StratifiedThermalStorage wenn:**
   - Große saisonale Speicher (> 1000 m³) modelliert werden
   - Schichtungseffekte relevant sind
   - Detaillierte Temperaturprofile benötigt werden
   - Optimierung von Lade-/Entladestrategien
   - Keine detaillierte Systemintegration erforderlich

**Wählen Sie STES wenn:**
   - Realistische Systemintegration erforderlich ist
   - Massenströme und Temperaturen genau abgebildet werden müssen
   - Erzeugerschutz (Rücklauftemperatur) kritisch ist
   - Stagnations- und Unterdeckungsanalysen notwendig sind
   - Wirtschaftlichkeitsanalysen auf Basis realer Betriebsdaten
   - Dimensionierung und Detailplanung

==============================================
Gemeinsame Grundlagen
==============================================

Geometrieberechnungen
---------------------

Alle Speicherklassen unterstützen folgende Geometrien:

1. **Zylindrischer Speicher**

   .. math::
   
      V = \pi R^2 H
   
   .. math::
   
      A_{\text{top}} = A_{\text{bottom}} = \pi R^2
   
   .. math::
   
      A_{\text{side}} = 2\pi R H

2. **Kegelstumpf (Truncated Cone)**

   .. math::
   
      V = \frac{\pi H}{3} \left( R_{\text{top}}^2 + R_{\text{bottom}}^2 + R_{\text{top}} \cdot R_{\text{bottom}} \right)
   
   .. math::
   
      A_{\text{top}} = \pi R_{\text{top}}^2, \quad A_{\text{bottom}} = \pi R_{\text{bottom}}^2
   
   .. math::
   
      A_{\text{side}} = \pi (R_{\text{top}} + R_{\text{bottom}}) \cdot s
   
   Mit Mantellinie:
   
   .. math::
   
      s = \sqrt{(R_{\text{bottom}} - R_{\text{top}})^2 + H^2}

3. **Trapezförmiger Speicher (Truncated Trapezoid)**

   .. math::
   
      V = \frac{H}{3} \left( A_{\text{top}} + A_{\text{bottom}} + \sqrt{A_{\text{top}} \cdot A_{\text{bottom}}} \right)
   
   Mit:
   
   .. math::
   
      A_{\text{top}} = L_{\text{top}} \cdot W_{\text{top}}, \quad A_{\text{bottom}} = L_{\text{bottom}} \cdot W_{\text{bottom}}

Materialparameter
-----------------

.. list-table:: Typische Materialparameter
   :widths: 30 20 50
   :header-rows: 1

   * - **Material/Parameter**
     - **Wert**
     - **Anmerkung**
   * - **Speichermedium: Wasser**
     - 
     - 
   * - Dichte ρ
     - 1000 kg/m³
     - Bei 20-90°C annähernd konstant
   * - Spez. Wärmekapazität cp
     - 4186 J/(kg·K)
     - Temperaturabhängigkeit <5% im Bereich 20-90°C
   * - Wärmeleitfähigkeit λ
     - 0.6 W/(m·K)
     - Für Inter-Layer Conduction
   * - **Isolierungsmaterialien**
     - 
     - 
   * - Mineralwolle
     - 0.035-0.045 W/(m·K)
     - Standard für oberirdische Speicher
   * - XPS/EPS
     - 0.030-0.040 W/(m·K)
     - Druckfest für erdverlegte Speicher
   * - Vakuumisolation
     - 0.005-0.010 W/(m·K)
     - Hochleistungsisolierung (teuer)
   * - **Erdreich**
     - 
     - 
   * - Trockener Sand
     - 0.3-0.6 W/(m·K)
     - Ungünstig für PTES
   * - Feuchter Lehm
     - 1.5-2.5 W/(m·K)
     - Typisch für PTES
   * - Gesättigter Ton
     - 2.0-3.0 W/(m·K)
     - Hohe Wärmeverluste

Effizienzberechnung
-------------------

Die Speichereffizienz wird für alle Modelle einheitlich berechnet:

.. math::

   \eta_{\text{storage}} = 1 - \frac{\sum_{t=1}^{T} \dot{Q}_{\text{loss},t} \cdot \Delta t}{\sum_{t=1}^{T} \dot{Q}_{\text{in},t} \cdot \Delta t}

Typische Wirkungsgrade:
   - Kurzzeitspeicher (Tage): 85-95%
   - Mittelzeitspeicher (Wochen): 70-85%
   - Saisonalspeicher (Monate): 50-70%

==============================================
Literatur und Referenzen
==============================================

Grundlegende Literatur
----------------------

1. **Narula, K., de Oliveira Filho, F., Villasmil, W., & Patel, M. K. (2020)**
   
   "Simulation method for assessing hourly energy flows in district heating system with seasonal thermal energy storage"
   
   *Renewable Energy*, 151, 1250-1268.
   
   DOI: https://doi.org/10.1016/j.renene.2019.11.121
   
   → **Hauptreferenz für STES-Modellierung**

VDI-Richtlinien
---------------

- **VDI 2067**: Wirtschaftlichkeit gebäudetechnischer Anlagen

==============================================
Module-Referenzen
==============================================

Für detaillierte API-Dokumentation siehe:

- :py:mod:`districtheatingsim.heat_generators.simple_thermal_storage`
- :py:mod:`districtheatingsim.heat_generators.stratified_thermal_storage`
- :py:mod:`districtheatingsim.heat_generators.STES`
- :py:mod:`districtheatingsim.heat_generators.STES_animation`

==============================================
Kontakt und Support
==============================================

Bei Fragen zur Speichermodellierung:

**Autor:** Dipl.-Ing. (FH) Jonas Pfeiffer

**Projekt:** DistrictHeatingSim

**Letzte Aktualisierung:** Oktober 2025
