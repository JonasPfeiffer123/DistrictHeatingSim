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

**Modellierungsansatz:**
   - Einheitliche Temperaturverteilung im gesamten Speichervolumen
   - Keine thermische Schichtung (Stratifikation)
   - Ein einzelner Temperaturknoten repräsentiert den gesamten Speicher
   - Zeitschrittbasierte Energiebilanzrechnung

**Unterstützte Geometrien:**
   - ``cylindrical_overground``: Oberirdische zylindrische Speicher
   - ``cylindrical_underground``: Erdverlegte zylindrische Speicher  
   - ``truncated_cone``: Kegelstumpf-Erdbeckenspeicher (PTES)
   - ``truncated_trapezoid``: Trapezförmige Erdbeckenspeicher (PTES)

**Wärmeübertragungsmechanismen:**
   - Konduktive Wärmeverluste durch Isolierungsschichten
   - Wärmeübertragung an Erdreich für erdverlegte Speicher
   - Temperaturabhängige thermische Widerstandsberechnungen
   - Stationäre Wärmeübertragungsanalyse pro Zeitschritt

Physikalische Annahmen
----------------------

1. **Uniform Temperature Distribution**
   
   .. math::
   
      T_{\text{storage}}(t) = \text{const.} \quad \forall \, (x,y,z) \in V_{\text{storage}}

   Die Speichertemperatur ist zu jedem Zeitpunkt im gesamten Volumen konstant.

2. **Energiebilanzgleichung**
   
   .. math::
   
      \frac{dE}{dt} = \dot{Q}_{\text{in}} - \dot{Q}_{\text{out}} - \dot{Q}_{\text{loss}}

   Wobei:
      - :math:`\dot{Q}_{\text{in}}`: Wärmeleistung Eingang [kW]
      - :math:`\dot{Q}_{\text{out}}`: Wärmeleistung Ausgang [kW]
      - :math:`\dot{Q}_{\text{loss}}`: Wärmeverluste [kW]

3. **Temperaturberechnung**
   
   .. math::
   
      T_{\text{storage}} = \frac{E_{\text{stored}}}{m \cdot c_p} + T_{\text{ref}}

   Mit:
      - :math:`E_{\text{stored}}`: Gespeicherte thermische Energie [J]
      - :math:`m`: Speichermasse [kg] = :math:`\rho \cdot V`
      - :math:`c_p`: Spezifische Wärmekapazität [J/(kg·K)]
      - :math:`T_{\text{ref}}`: Referenztemperatur [°C]

4. **Wärmeverlustberechnung**

   Für **oberirdische zylindrische Speicher**:
   
   .. math::
   
      \dot{Q}_{\text{loss}} = \dot{Q}_{\text{top}} + \dot{Q}_{\text{side}} + \dot{Q}_{\text{bottom}}

   .. math::
   
      \dot{Q}_{\text{top}} = \frac{\lambda_{\text{top}}}{\delta_{\text{top}}} \cdot A_{\text{top}} \cdot (T_{\text{storage}} - T_{\text{amb}})

   .. math::
   
      \dot{Q}_{\text{side}} = \frac{\lambda_{\text{side}}}{\delta_{\text{side}}} \cdot A_{\text{side}} \cdot (T_{\text{storage}} - T_{\text{amb}})

   .. math::
   
      \dot{Q}_{\text{bottom}} = \frac{1}{R_{\text{total}}} \cdot A_{\text{bottom}} \cdot (T_{\text{storage}} - T_{\text{amb}})

   Mit thermischem Gesamtwiderstand:
   
   .. math::
   
      R_{\text{total}} = \frac{\delta_{\text{bottom}}}{\lambda_{\text{bottom}}} + \frac{4R}{3\pi\lambda_{\text{soil}}}

   Für **erdverlegte Speicher** (PTES):
   
   .. math::
   
      K_s = \frac{1}{bH} \ln\left(\frac{a + bH}{a}\right)

   .. math::
   
      a = \frac{\delta_s}{\lambda_s} + \frac{\pi H}{2\lambda_{\text{soil}}}, \quad b = \frac{\pi}{\lambda_{\text{soil}}}

   .. math::
   
      \dot{Q}_{\text{side}} = K_s \cdot A_{\text{side}} \cdot (T_{\text{storage}} - T_{\text{soil}})

Anwendungsbereich
-----------------

**Geeignet für:**
   - Vorläufige Machbarkeitsstudien
   - Kurzzeitpufferspeicher (Stunden bis Tage)
   - Kleine Speichervolumen (<100 m³)
   - Grobe Systemauslegung
   - Schnelle Sensitivitätsanalysen

**Nicht geeignet für:**
   - (Saisonale) Wärmespeicher mit ausgeprägter Schichtung
   - Detaillierte Temperaturprofilanalysen
   - Optimierung von Ein-/Ausströmstrategien
   - Große Erdbeckenspeicher (PTES) mit signifikanter Stratifikation

Beispielanwendung
-----------------

.. code-block:: python

   from districtheatingsim.heat_generators.simple_thermal_storage import SimpleThermalStorage
   import numpy as np
   
   # Initialisierung eines einfachen Pufferspeichers
   simple_storage = SimpleThermalStorage(
       name="Pufferspeicher_01",
       storage_type="cylindrical_overground",
       dimensions=(3.0, 6.0),      # Radius 3m, Höhe 6m
       rho=1000,                    # Wasserdichte [kg/m³]
       cp=4186,                     # Wärmekapazität Wasser [J/(kg·K)]
       T_ref=0,                     # Referenztemperatur [°C]
       lambda_top=0.03,             # Wärmeleitfähigkeit Isolierung [W/(m·K)]
       lambda_side=0.03,
       lambda_bottom=0.03,
       lambda_soil=1.5,             # Wärmeleitfähigkeit Erdreich [W/(m·K)]
       T_amb=10,                    # Umgebungstemperatur [°C]
       T_soil=8,                    # Erdreichtemperatur [°C]
       T_max=90,                    # Maximale Speichertemperatur [°C]
       T_min=10,                    # Minimale Speichertemperatur [°C]
       initial_temp=60,             # Anfangstemperatur [°C]
       dt_top=0.15,                 # Dämmstärke oben [m]
       ds_side=0.10,                # Dämmstärke seitlich [m]
       db_bottom=0.10,              # Dämmstärke unten [m]
       hours=8760
   )
   
   # Betriebsprofil definieren
   Q_in = np.zeros(8760)
   Q_out = np.zeros(8760)
   
   # Sommerbeladung (Mai-August)
   Q_in[3000:6000] = 500          # 500 kW Beladeleistung
   
   # Winterentladung (November-Februar)
   Q_out[7000:8760] = 200         # 200 kW Entladeleistung
   Q_out[0:1500] = 200
   
   # Simulation durchführen
   simple_storage.simulate(Q_in, Q_out)
   
   # Ergebnisse auswerten
   print(f"Speicherwirkungsgrad: {simple_storage.efficiency:.1%}")
   print(f"Maximale Temperatur: {np.max(simple_storage.T_sto):.1f}°C")
   print(f"Minimale Temperatur: {np.min(simple_storage.T_sto):.1f}°C")
   
   # Visualisierung
   simple_storage.plot_results()

Validierung
-----------

Eine Validierung steht aus.

==============================================
Komplexitätsstufe 2: StratifiedThermalStorage
==============================================

**Modul:** :py:mod:`districtheatingsim.heat_generators.stratified_thermal_storage`

Beschreibung
------------

Die StratifiedThermalStorage-Klasse erweitert die SimpleThermalStorage um eine mehrschichtige Temperaturverteilung. Dies ermöglicht die Abbildung thermischer Schichtungseffekte, die besonders bei großen saisonalen Wärmespeichern eine entscheidende Rolle spielen.

Hauptmerkmale
-------------

**Erweiterungen gegenüber SimpleThermalStorage:**
   - Multi-Layer-Temperaturmodellierung
   - Schichtspezifische Wärmeverluste
   - Thermische Leitung zwischen Schichten
   - Geschichtete Lade-/Entladestrategien

**Schichtungsphysik:**
   - Natürliche Temperaturgradienten durch Dichteunterschiede
   - Schichtspezifische Randbedingungen
   - Konduktiver Wärmetransfer zwischen benachbarten Schichten
   - Erhalt der Schichtung während Be- und Entladung

Physikalische Annahmen
----------------------

1. **Diskretisierte Temperaturverteilung**
   
   Der Speicher wird in :math:`N` horizontale Schichten gleicher Dicke unterteilt:
   
   .. math::
   
      \delta_{\text{layer}} = \frac{H}{N}

   Wobei :math:`H` die Gesamthöhe und :math:`N` die Anzahl der Schichten ist.

2. **Schichtvolumen**

   Für **zylindrische Geometrie**:
   
   .. math::
   
      V_{\text{layer}} = \frac{V_{\text{total}}}{N} = \frac{\pi R^2 H}{N}

   Für **Kegelstumpf** (variable Volumina):
   
   .. math::
   
      V_{\text{layer},i} = \frac{\pi \delta_{\text{layer}}}{3} \left( r_{\text{top},i}^2 + r_{\text{bottom},i}^2 + r_{\text{top},i} \cdot r_{\text{bottom},i} \right)

   Mit linearer Radiusinterpolation:
   
   .. math::
   
      r_i = r_1 + (r_2 - r_1) \cdot \frac{i}{N}

3. **Schichtspezifische Energiebilanz**

   Für jede Schicht :math:`i` gilt:
   
   .. math::
   
      \frac{dE_i}{dt} = \dot{Q}_{\text{in},i} - \dot{Q}_{\text{out},i} - \dot{Q}_{\text{loss},i} + \dot{Q}_{\text{cond},i-1 \to i} - \dot{Q}_{\text{cond},i \to i+1}

   Wobei:
      - :math:`\dot{Q}_{\text{loss},i}`: Schichtspezifische Wärmeverluste
      - :math:`\dot{Q}_{\text{cond},i \to i+1}`: Wärmeleitung zur nächsten Schicht

4. **Thermische Leitung zwischen Schichten**
   
   .. math::
   
      \dot{Q}_{\text{cond},i \to i+1} = \lambda_{\text{medium}} \cdot A_{\text{interface}} \cdot \frac{T_i - T_{i+1}}{\delta_{\text{layer}}}

   Mit:
      - :math:`\lambda_{\text{medium}}`: Wärmeleitfähigkeit des Speichermediums (Wasser: 0.6 W/(m·K))
      - :math:`A_{\text{interface}}`: Querschnittsfläche zwischen den Schichten

5. **Lade-/Entladestrategie**

   **Beladung (von oben nach unten):**
      - Wärmezufuhr erfolgt bevorzugt in die oberen Schichten
      - Erhalt der natürlichen Schichtung (heißes Wasser oben)
      - Kaskadierung zur nächsten Schicht bei Temperaturgrenzen
   
   **Entladung (von oben nach unten):**
      - Wärmeentnahme erfolgt aus den oberen Schichten
      - Kaltwasserreserve in unteren Schichten bleibt erhalten
      - Erhalt der Temperaturdifferenz für optimale Exergie

6. **Schichtspezifische Wärmeverluste**

   **Oberste Schicht** (atmosphärischer Kontakt):
   
   .. math::
   
      \dot{Q}_{\text{loss},1} = \frac{\lambda_{\text{top}}}{\delta_{\text{top}}} \cdot A_{\text{top}} \cdot (T_1 - T_{\text{amb}})

   **Mittlere Schichten** (seitliche Verluste):
   
   .. math::
   
      \dot{Q}_{\text{loss},i} = \frac{\lambda_{\text{side}}}{\delta_{\text{side}}} \cdot \frac{A_{\text{side}}}{N} \cdot (T_i - T_{\text{soil}})

   **Unterste Schicht** (erhöhter Bodenwiderstand):
   
   .. math::
   
      \dot{Q}_{\text{loss},N} = K_b \cdot A_{\text{bottom}} \cdot (T_N - T_{\text{soil}})

Anwendungsbereich
-----------------

**Geeignet für:**
   - Große saisonale Wärmespeicher (>1000 m³)
   - Erdbeckenspeicher (PTES) mit ausgeprägter Schichtung
   - Detailliertere Temperaturprofilanalysen
   - Optimierung von Lade-/Entladestrategien
   - Mittel- bis langfristige Speicherzyklen (Wochen bis Monate)

**Nicht geeignet für:**
   - Hochdynamische Massenströme mit komplexer Durchmischung
   - CFD-Genauigkeit bei Strömungsanalysen
   - Speicher mit aktiver Konvektion oder Rührwerken

Beispielanwendung
-----------------

.. code-block:: python

   from districtheatingsim.heat_generators.stratified_thermal_storage import StratifiedThermalStorage
   import numpy as np
   
   # Initialisierung eines geschichteten PTES
   stratified_ptes = StratifiedThermalStorage(
       name="PTES_Geschichtet",
       storage_type="truncated_cone",
       dimensions=(20.0, 30.0, 12.0),  # Radius oben, Radius unten, Höhe [m]
       rho=1000,
       cp=4186,
       T_ref=0,
       lambda_top=0.025,
       lambda_side=0.035,
       lambda_bottom=0.04,
       lambda_soil=2.0,
       T_amb=8,
       T_soil=10,
       T_max=85,
       T_min=15,
       initial_temp=40,
       dt_top=0.3,
       ds_side=0.5,
       db_bottom=0.3,
       hours=8760,
       num_layers=10,                   # 10 Schichten für detaillierte Stratifikation
       thermal_conductivity=0.6
   )
   
   # Saisonales Lade-/Entladeprofil
   time = np.arange(8760)
   
   # Sommerbeladung (solare Wärme)
   Q_in = 500 * np.maximum(0, np.sin(2 * np.pi * (time - 2000) / 8760)) ** 2
   
   # Winterwärmebedarf
   Q_out = 200 + 300 * np.maximum(0, np.cos(2 * np.pi * time / 8760))
   
   # Geschichtete Simulation
   stratified_ptes.simulate_stratified(Q_in, Q_out)
   
   # Stratifikationsanalyse
   final_temps = stratified_ptes.T_sto_layers[-1, :]
   temp_gradient = final_temps.max() - final_temps.min()
   
   print(f"Finale Temperaturschichtung: {temp_gradient:.1f} K")
   print(f"Oberste Schicht: {final_temps[0]:.1f}°C")
   print(f"Unterste Schicht: {final_temps[-1]:.1f}°C")
   print(f"Speicherwirkungsgrad: {stratified_ptes.efficiency:.1%}")
   
   # Visualisierung inkl. 3D-Temperaturverteilung
   stratified_ptes.plot_results()

Validierung
-----------

Die Validierung steht aus.

==============================================
Komplexitätsstufe 3: STES (Seasonal Thermal Energy Storage)
==============================================

**Modul:** :py:mod:`districtheatingsim.heat_generators.STES`

Beschreibung
------------

Die STES-Klasse stellt die höchste Komplexitätsstufe dar und erweitert die StratifiedThermalStorage um detaillierte Massenstrommodellierung, hydraulische Randbedingungen und realistische Systemintegration. Diese Klasse ermöglicht die genaue Simulation von saisonalen Wärmespeichern unter Berücksichtigung aller relevanten physikalischen und betrieblichen Randbedingungen.

Hauptmerkmale
-------------

**Erweiterungen gegenüber StratifiedThermalStorage:**
   - Massenstrommodellierung mit temperaturabhängiger Regelung
   - Hydraulische Randbedingungen (Vor- und Rücklauftemperaturen)
   - Stagnationsschutz und Überhitzungserkennung
   - Unterdeckungsanalyse (unmet demand tracking)
   - Realistische Systemintegration mit Erzeugern und Verbrauchern
   - Detaillierte Betriebszustandsanalyse

**Systemintegration:**
   - Vor- und Rücklauftemperaturen für Erzeuger- und Verbraucherseite
   - Massenstrombasierter Energietransfer
   - Temperaturabhängige Betriebsgrenzen
   - Schutz vor Rücklauftemperaturüberschreitung (Erzeuger)
   - Mindestvorlauftemperatur (Verbraucher)

Physikalische Annahmen
----------------------

1. **Massenstrombasierte Energieübertragung**

   **Beladung:**
   
   .. math::
   
      \dot{m}_{\text{in}} = \frac{\dot{Q}_{\text{in}} \cdot 1000}{c_p \cdot (T_{\text{supply}} - T_{\text{bottom}})}

   Wobei:
      - :math:`\dot{m}_{\text{in}}`: Massenstrom Eingang [kg/s]
      - :math:`\dot{Q}_{\text{in}}`: Wärmeleistung Eingang [kW]
      - :math:`T_{\text{supply}}`: Vorlauftemperatur Erzeuger [°C]
      - :math:`T_{\text{bottom}}`: Temperatur unterste Speicherschicht [°C]

   **Entladung:**
   
   .. math::
   
      \dot{m}_{\text{out}} = \frac{\dot{Q}_{\text{out}} \cdot 1000}{c_p \cdot (T_{\text{top}} - T_{\text{return}})}

   Wobei:
      - :math:`\dot{m}_{\text{out}}`: Massenstrom Ausgang [kg/s]
      - :math:`\dot{Q}_{\text{out}}`: Wärmeleistung Ausgang [kW]
      - :math:`T_{\text{top}}`: Temperatur oberste Speicherschicht [°C]
      - :math:`T_{\text{return}}`: Rücklauftemperatur Verbraucher [°C]

2. **Mischungstemperatur bei Beladung**

   Bei Einspeisung in Schicht :math:`i`:
   
   .. math::
   
      T_{\text{mix},i} = \frac{\dot{m}_{\text{in}} \cdot c_p \cdot T_{\text{flow}} + m_{\text{layer},i} \cdot c_p \cdot T_i}{\dot{m}_{\text{in}} \cdot c_p + m_{\text{layer},i} \cdot c_p} - 273.15

   Mit Umrechnung von Kelvin zu Celsius, wobei:
      - :math:`T_{\text{flow}}`: Aktuelle Einspeisetemperatur [°C]
      - :math:`m_{\text{layer},i} = V_i \cdot \rho`: Masse der Schicht [kg]

3. **Betriebsgrenzen**

   **Beladegrenze (Schutz der Wärmeerzeuger):**
   
   .. math::
   
      T_{\text{bottom}} < T_{\text{max,Rücklauf}}

   Typisch: :math:`T_{\text{max,Rücklauf}} = 70°C` (Schutz von Solarkollektoren, BHKW, etc.)

   **Entladegrenze (Versorgungssicherheit):**
   
   .. math::
   
      T_{\text{top}} > T_{\text{supply}} - \Delta T_{\text{VLT}}

   Typisch: :math:`\Delta T_{\text{VLT}} = 15 K` (Toleranz für Vorlauftemperatur)

4. **Stagnationsmodellierung**

   Bei Überschreitung der Beladegrenze:
   
   .. math::
   
      \dot{m}_{\text{in}} = 0, \quad Q_{\text{excess}} = Q_{\text{excess}} + \dot{Q}_{\text{available}} \cdot \Delta t

   Stagnationszeit wird gezählt:
   
   .. math::
   
      t_{\text{stagnation}} = t_{\text{stagnation}} + 1 \, \text{[h]}

5. **Unterdeckungsmodellierung**

   Bei Unterschreitung der Entladegrenze:
   
   .. math::
   
      \dot{m}_{\text{out}} = 0, \quad Q_{\text{unmet}} = Q_{\text{unmet}} + \dot{Q}_{\text{demand}} \cdot \Delta t

6. **Speicherzustandsberechnung**

   Der Speicherladezustand wird relativ zur maximal möglichen Energie berechnet:
   
   .. math::
   
      SOC(t) = \frac{E_{\text{available}}(t)}{E_{\text{max}}}

   .. math::
   
      E_{\text{available}}(t) = \sum_{i=1}^{N} \max\left(0, (T_i(t) - T_{\text{return}}) \cdot V_i \cdot \rho \cdot c_p\right) / 3.6 \times 10^6

   .. math::
   
      E_{\text{max}} = \sum_{i=1}^{N} \max\left(0, (T_{\text{supply}} - T_{\text{return}}) \cdot V_i \cdot \rho \cdot c_p\right) / 3.6 \times 10^6

Anwendungsbereich
-----------------

**Geeignet für:**
   - Detaillierte saisonale Wärmespeicherplanung
   - Systemintegrationsstudien mit realen Erzeugern und Verbrauchern
   - Optimierung von Betriebsstrategien
   - Wirtschaftlichkeitsanalysen
   - Dimensionierungsstudien für PTES-Systeme
   - Vor- und Rücklauftemperaturanalysen
   - Stagnations- und Unterdeckungsanalysen

**Essenziell wenn:**
   - Realistische Massenströme berücksichtigt werden müssen
   - Erzeugerschutz (Rücklauftemperaturbegrenzung) relevant ist
   - Verbraucherseitige Mindesttemperaturen eingehalten werden müssen
   - Detaillierte Betriebskosten- und Effizienzanalysen erforderlich sind

Betriebsparameter
-----------------

.. list-table:: Wichtige Betriebsparameter
   :widths: 30 20 50
   :header-rows: 1

   * - Parameter
     - Typischer Wert
     - Beschreibung
   * - T_max_rücklauf
     - 70°C
     - Maximale Rücklauftemperatur zu Erzeugern (Schutz)
   * - dT_VLT
     - 15 K
     - Toleranz Vorlauftemperatur (Mindestversorgung)
   * - T_supply
     - 70-90°C
     - Vorlauftemperatur Erzeuger (z.B. Solarthermie)
   * - T_return
     - 40-60°C
     - Rücklauftemperatur Verbraucher (Gebäude)
   * - Massenstrom
     - variabel
     - Automatisch aus Wärmeleistung und ΔT berechnet

Beispielanwendung
-----------------

.. code-block:: python

   from districtheatingsim.heat_generators.STES import STES
   import numpy as np
   import pandas as pd
   
   # Initialisierung eines STES-Systems mit vollständiger Systemintegration
   stes_params = {
       "storage_type": "truncated_cone",
       "dimensions": (25.0, 35.0, 15.0),
       "rho": 1000,
       "cp": 4186,
       "T_ref": 10,
       "lambda_top": 0.025,
       "lambda_side": 0.035,
       "lambda_bottom": 0.04,
       "lambda_soil": 2.0,
       "dt_top": 0.3,
       "ds_side": 0.5,
       "db_bottom": 0.3,
       "T_amb": 8,
       "T_soil": 10,
       "T_max": 90,
       "T_min": 20,
       "initial_temp": 45,
       "hours": 8760,
       "num_layers": 10,
       "thermal_conductivity": 0.6
   }
   
   stes = STES(name="Saisonalspeicher_Fernwärme", **stes_params)
   
   # Lastprofil laden (reale Verbrauchsdaten)
   df = pd.read_csv('Lastgang.csv', delimiter=';')
   Q_out_profile = df['Wärmebedarf_kW'].values
   
   # Erzeuger- und Verbrauchertemperaturen definieren
   T_supply = np.full(8760, 85.0)      # Solarthermie Vorlauf
   T_return = np.full(8760, 45.0)      # Gebäude Rücklauf
   
   # Solare Wärmeerzeugung (stark saisonal)
   time = np.arange(8760)
   Q_in = 500 * np.maximum(0, np.sin(2 * np.pi * (time - 2000) / 8760))
   
   # Simulation mit Massenströmen und Temperaturen
   for t in range(8760):
       stes.simulate_stratified_temperature_mass_flows(
           t, Q_in[t], Q_out_profile[t], T_supply[t], T_return[t]
       )
   
   # Umfassende Auswertung
   stes.calculate_efficiency(Q_in)
   
   print("=== STES Betriebsanalyse ===")
   print(f"Speicherwirkungsgrad: {stes.efficiency:.1%}")
   print(f"Überschüssige Wärme (Stagnation): {stes.excess_heat:.0f} kWh")
   print(f"Nicht gedeckter Bedarf: {stes.unmet_demand:.0f} kWh")
   print(f"Stagnationsdauer: {stes.stagnation_time} Stunden")
   print(f"Durchschn. Massenstrom Beladung: {stes.mass_flow_in[stes.mass_flow_in>0].mean():.2f} kg/s")
   print(f"Durchschn. Massenstrom Entladung: {stes.mass_flow_out[stes.mass_flow_out>0].mean():.2f} kg/s")
   
   # Detaillierte Visualisierung
   stes.plot_results(Q_in, Q_out_profile, T_supply, T_return)

Validierung
-----------

Die Validierung steht aus.

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
