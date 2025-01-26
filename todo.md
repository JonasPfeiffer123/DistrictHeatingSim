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




Traceback (most recent call last):
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\timeseries\run_time_series.py", line 129, in run_time_step
    run_control_fct(net, ctrl_variables=ts_variables, **kwargs)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\control\run_control.py", line 303, in run_control
    control_implementation(net, controller_order, ctrl_variables, max_iter, **kwargs)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\control\run_control.py", line 219, in control_implementation
    ctrl_variables = evaluate_net_fct(net, levelorder, ctrl_variables, **kwargs)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\control\run_control.py", line 196, in _evaluate_net
    raise err
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\control\run_control.py", line 180, in _evaluate_net
    run_funct(net, **kwargs)  # run can be runpp, runopf or whatever
    ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\pipeflow.py", line 91, in pipeflow
    bidirectional(net)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\pipeflow.py", line 165, in bidirectional
    raise PipeflowNotConverged("The bidrectional calculation did not converge to a solution.")
pandapipes.pf.pipeflow_setup.PipeflowNotConverged: The bidrectional calculation did not converge to a solution.

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\jonas\DistrictHeatSim\src\districtheatingsim\gui\CalculationTab\net_calculation_threads.py", line 149, in run
    self.time_steps, self.net, self.net_results = thermohydraulic_time_series_net(self.net, self.yearly_time_steps, self.waerme_hast_ges_W, self.calc1, \
                                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\jonas\DistrictHeatSim\src\districtheatingsim\net_simulation_pandapipes\pp_net_time_series_simulation.py", line 233, in thermohydraulic_time_series_net
    run_time_series.run_timeseries(net, time_steps, mode="bidirectional", iter=100, alpha=0.2)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\timeseries\run_time_series.py", line 125, in run_timeseries
    run_loop(net, ts_variables, **kwargs)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\timeseries\run_time_series.py", line 329, in run_loop
    run_time_step(net, time_step, ts_variables, run_control_fct, output_writer_fct, **kwargs)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\timeseries\run_time_series.py", line 137, in run_time_step
    pf_not_converged(time_step, ts_variables)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\timeseries\run_time_series.py", line 80, in pf_not_converged
    raise ts_variables['errors'][0]
pandapipes.pf.pipeflow_setup.PipeflowNotConverged


Traceback (most recent call last):
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\timeseries\run_time_series.py", line 129, in run_time_step
    run_control_fct(net, ctrl_variables=ts_variables, **kwargs)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\control\run_control.py", line 303, in run_control
    control_implementation(net, controller_order, ctrl_variables, max_iter, **kwargs)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\control\run_control.py", line 219, in control_implementation
    ctrl_variables = evaluate_net_fct(net, levelorder, ctrl_variables, **kwargs)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\control\run_control.py", line 196, in _evaluate_net
    raise err
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\control\run_control.py", line 180, in _evaluate_net
    run_funct(net, **kwargs)  # run can be runpp, runopf or whatever
    ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\pipeflow.py", line 91, in pipeflow
    bidirectional(net)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\pipeflow.py", line 165, in bidirectional
    raise PipeflowNotConverged("The bidrectional calculation did not converge to a solution.")
pandapipes.pf.pipeflow_setup.PipeflowNotConverged: The bidrectional calculation did not converge to a solution.

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\jonas\DistrictHeatSim\src\districtheatingsim\gui\CalculationTab\net_calculation_threads.py", line 149, in run
    self.time_steps, self.net, self.net_results = thermohydraulic_time_series_net(self.net, self.yearly_time_steps, self.waerme_hast_ges_W, self.calc1, \
                                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\jonas\DistrictHeatSim\src\districtheatingsim\net_simulation_pandapipes\pp_net_time_series_simulation.py", line 233, in thermohydraulic_time_series_net
    run_time_series.run_timeseries(net, time_steps, mode="bidirectional", iter=100)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\timeseries\run_time_series.py", line 125, in run_timeseries
    run_loop(net, ts_variables, **kwargs)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\timeseries\run_time_series.py", line 329, in run_loop
    run_time_step(net, time_step, ts_variables, run_control_fct, output_writer_fct, **kwargs)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\timeseries\run_time_series.py", line 137, in run_time_step
    pf_not_converged(time_step, ts_variables)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\timeseries\run_time_series.py", line 80, in pf_not_converged
    raise ts_variables['errors'][0]
pandapipes.pf.pipeflow_setup.PipeflowNotConverged

NaN values in branch_pit or node_pit
Traceback (most recent call last):
  File "C:\Users\jonas\DistrictHeatSim\src\districtheatingsim\gui\CalculationTab\net_calculation_threads.py", line 149, in run
    self.time_steps, self.net, self.net_results = thermohydraulic_time_series_net(self.net, self.yearly_time_steps, self.waerme_hast_ges_W, self.calc1, \
                                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\jonas\DistrictHeatSim\src\districtheatingsim\net_simulation_pandapipes\pp_net_time_series_simulation.py", line 246, in thermohydraulic_time_series_net
    run_time_series.run_timeseries(net, time_steps, mode="bidirectional", iter=100, continue_on_divergence=False, verbose=True)
  File "c:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\timeseries\run_time_series.py", line 125, in run_timeseries
    run_loop(net, ts_variables, **kwargs)
  File "c:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\timeseries\run_time_series.py", line 396, in run_loop
    run_time_step(net, time_step, ts_variables, run_control_fct, output_writer_fct, **kwargs)
  File "c:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\timeseries\run_time_series.py", line 177, in run_time_step
    run_control_fct(net, ctrl_variables=ts_variables, **kwargs)
  File "c:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\control\run_control.py", line 303, in run_control
    control_implementation(net, controller_order, ctrl_variables, max_iter, **kwargs)
  File "c:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\control\run_control.py", line 219, in control_implementation
    ctrl_variables = evaluate_net_fct(net, levelorder, ctrl_variables, **kwargs)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "c:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\control\run_control.py", line 180, in _evaluate_net
    run_funct(net, **kwargs)  # run can be runpp, runopf or whatever
    ^^^^^^^^^^^^^^^^^^^^^^^^
  File "c:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\pipeflow.py", line 91, in pipeflow
    bidirectional(net)
  File "c:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\pipeflow.py", line 156, in bidirectional
    newton_raphson(
  File "c:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\pipeflow.py", line 127, in newton_raphson
    results, residual = funct(net)
                        ^^^^^^^^^^
  File "c:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\pipeflow.py", line 211, in solve_bidirectional
    res_hyd, residual_hyd = solve_hydraulics(net)
                            ^^^^^^^^^^^^^^^^^^^^^
  File "c:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\pipeflow.py", line 263, in solve_hydraulics
    raise ValueError("NaN values in branch_pit or node_pit")
ValueError: NaN values in branch_pit or node_pit


Traceback (most recent call last):
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\timeseries\run_time_series.py", line 177, in run_time_step
    run_control_fct(net, ctrl_variables=ts_variables, **kwargs)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\control\run_control.py", line 303, in run_control
    control_implementation(net, controller_order, ctrl_variables, max_iter, **kwargs)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\control\run_control.py", line 219, in control_implementation
    ctrl_variables = evaluate_net_fct(net, levelorder, ctrl_variables, **kwargs)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\control\run_control.py", line 196, in _evaluate_net
    raise err
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\control\run_control.py", line 180, in _evaluate_net
    run_funct(net, **kwargs)  # run can be runpp, runopf or whatever
    ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\pipeflow.py", line 94, in pipeflow
    bidirectional(net)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\pipeflow.py", line 159, in bidirectional
    newton_raphson(
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\pipeflow.py", line 130, in newton_raphson
    results, residual = funct(net)
                        ^^^^^^^^^^
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\pipeflow.py", line 218, in solve_bidirectional
    res_heat, residual_heat = solve_temperature(net)
                              ^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\pipeflow.py", line 328, in solve_temperature
    check_infeed_number(node_pit)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\pf\pipeflow_setup.py", line 782, in check_infeed_number
    raise PipeflowNotConverged(r'The number of infeeding nodes and slacks do not match')
pandapipes.pf.pipeflow_setup.PipeflowNotConverged: The number of infeeding nodes and slacks do not match

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\jonas\DistrictHeatSim\src\districtheatingsim\gui\CalculationTab\net_calculation_threads.py", line 149, in run
    self.time_steps, self.net, self.net_results = thermohydraulic_time_series_net(self.net, self.yearly_time_steps, self.waerme_hast_ges_W, self.calc1, \
                                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\jonas\DistrictHeatSim\src\districtheatingsim\net_simulation_pandapipes\pp_net_time_series_simulation.py", line 246, in thermohydraulic_time_series_net
    run_time_series.run_timeseries(net, time_steps, mode="bidirectional", iter=100, alpha=0.1)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapipes\timeseries\run_time_series.py", line 125, in run_timeseries
    run_loop(net, ts_variables, **kwargs)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\timeseries\run_time_series.py", line 396, in run_loop
    run_time_step(net, time_step, ts_variables, run_control_fct, output_writer_fct, **kwargs)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\timeseries\run_time_series.py", line 204, in run_time_step
    pf_not_converged(time_step, ts_variables)
  File "C:\Users\jonas\AppData\Local\Programs\Python\Python311\Lib\site-packages\pandapower\timeseries\run_time_series.py", line 129, in pf_not_converged
    raise ts_variables['errors'][0]
pandapipes.pf.pipeflow_setup.PipeflowNotConverged
