import sys
import os

import logging
import numpy as np
import geopandas as gpd
import pandapipes as pp
import csv
import pandas as pd
import itertools
import json

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QMessageBox, QProgressBar, QMenuBar, QAction

from tests.main import calculate_results, save_results_csv, import_results_csv
from gui.calculation_dialogs import HeatDemandEditDialog, NetGenerationDialog, ZeitreihenrechnungDialog
from gui.threads import NetInitializationThread, NetCalculationThread
from net_simulation_pandapipes.config_plot import config_plot
from gui.checkable_combobox import CheckableComboBox

from net_simulation_pandapipes.net_simulation_calculation import export_net_geojson

class CalculationTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.calc_method = "Datensatz"
        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        # Update the base path immediately with the current project folder
        self.updateDefaultPath(self.data_manager.project_folder)
        self.initUI()
        self.net_data = None  # Variable zum Speichern der Netzdaten
        self.supply_temperature = None # Variable Vorlauftemperatur

    def initUI(self):
        # Erstellen eines Scrollbereichs
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        # Erstellen eines Container-Widgets für den Scrollbereich
        container_widget = QWidget()
        scroll_area.setWidget(container_widget)

        # Erstellen eines Layouts für das Container-Widget
        self.container_layout = QVBoxLayout(container_widget)

        # Hier fügen Sie alle Ihre vorhandenen Setup-Funktionen hinzu
        self.initMenuBar()
        self.setupPlotLayout()

        # Hauptlayout für das Tab
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(scroll_area)
        self.setLayout(self.main_layout)

        self.progressBar = QProgressBar(self)
        self.container_layout.addWidget(self.progressBar)

    def initMenuBar(self):
        self.menubar = QMenuBar(self)
        self.menubar.setFixedHeight(30)

        # Wärmenetz-Generierungsmenü
        fileMenu = self.menubar.addMenu('Datei')
        networkMenu = self.menubar.addMenu('Wärmenetz generieren')
        calcMenu = self.menubar.addMenu('Zeitreihenberechnung durchführen')

        # Unterpunkte für geojson und Stanet
        saveppnetAction = QAction('Pandapipes Netz speichern', self)
        loadppnetAction = QAction('Pandapipes Netz laden', self)
        loadresultsppAction = QAction('Ergebnisse Zeitreihenrechnung Laden', self)
        exportppnetGeoJSONAction = QAction('Pandapipes Netz als geoJSON exportieren', self)
        fileMenu.addAction(saveppnetAction)
        fileMenu.addAction(loadppnetAction)
        fileMenu.addAction(loadresultsppAction)
        fileMenu.addAction(exportppnetGeoJSONAction)

        generateNetAction = QAction('Netz generieren', self)
        networkMenu.addAction(generateNetAction)

        calculateNetAction = QAction('Zeitreihenberechnung', self)
        calcMenu.addAction(calculateNetAction)

        # Fügen Sie die Menüleiste dem Layout von tab1 hinzu
        self.container_layout.addWidget(self.menubar)

        # Verbindungen zu den Funktionen
        generateNetAction.triggered.connect(self.openNetGenerationDialog)
        saveppnetAction.triggered.connect(self.saveNet)
        loadppnetAction.triggered.connect(self.loadNet)
        loadresultsppAction.triggered.connect(self.load_net_results)
        exportppnetGeoJSONAction.triggered.connect(self.exportNetGeoJSON)
        calculateNetAction.triggered.connect(self.opencalculateNetDialog)

    def setupPlotLayout(self):
        self.scrollArea = QScrollArea(self)  # Erstelle ein ScrollArea-Widget
        self.scrollWidget = QWidget()  # Erstelle ein Widget für den Inhalt der ScrollArea
        self.scrollLayout = QVBoxLayout(self.scrollWidget)  # Erstelle ein Layout für das Scroll-Widget

        self.figure3 = Figure()
        self.canvas3 = FigureCanvas(self.figure3)
        self.canvas3.setMinimumSize(700, 700)  # Setze eine Mindestgröße für die Canvas
        self.toolbar3 = NavigationToolbar(self.canvas3, self)

        self.figure4 = Figure()
        self.canvas4 = FigureCanvas(self.figure4)
        self.canvas4.setMinimumSize(700, 700)  # Setze eine Mindestgröße für die Canvas
        self.toolbar4 = NavigationToolbar(self.canvas4, self)

        self.figure5 = Figure()
        self.canvas5 = FigureCanvas(self.figure5)
        self.canvas5.setMinimumSize(700, 700)  # Setze eine Mindestgröße für die Canvas
        self.toolbar5 = NavigationToolbar(self.canvas5, self)

        # Fügen Sie die Diagramme und Toolbars zum Container-Layout hinzu
        self.scrollLayout.addWidget(self.canvas5)
        self.scrollLayout.addWidget(self.toolbar5)
        self.scrollLayout.addWidget(self.canvas4)
        self.scrollLayout.addWidget(self.toolbar4)
        self.scrollLayout.addWidget(self.canvas3)
        self.scrollLayout.addWidget(self.toolbar3)

        # Setze das Scroll-Widget als Inhalt der ScrollArea
        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setWidgetResizable(True)  # Erlaubt das Resize der Inhalte innerhalb der ScrollArea

        # Füge die ScrollArea zum Hauptlayout hinzu
        self.container_layout.addWidget(self.scrollArea)
    
    def createPlotControlDropdown(self):
        self.dropdownLayout = QHBoxLayout()
        self.dataSelectionDropdown = CheckableComboBox(self)

        # Hier wird angenommen, dass die erste Reihe von Daten standardmäßig geplottet wird.
        initial_checked = True

        # Füllen des Dropdown-Menüs mit Optionen und Setzen des Checkbox-Zustands
        for label in self.plot_data.keys():
            self.dataSelectionDropdown.addItem(label)
            item = self.dataSelectionDropdown.model().item(self.dataSelectionDropdown.count() - 1, 0)
            item.setCheckState(Qt.Checked if initial_checked else Qt.Unchecked)
            initial_checked = False  # Nur das erste Element wird standardmäßig ausgewählt

        self.dropdownLayout.addWidget(self.dataSelectionDropdown)
        self.scrollLayout.addLayout(self.dropdownLayout)

        # Verbindung des Dropdown-Menüs mit der Aktualisierungsfunktion
        self.dataSelectionDropdown.checkedStateChanged.connect(self.updatePlot)

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path
    
    def openNetGenerationDialog(self):
        try:
            dialog = NetGenerationDialog(
                self.generateNetworkCallback,
                self.editHeatDemandData,
                self.base_path,
                self
            )
            dialog.exec_()
        except Exception as e:
            logging.error(f"Fehler beim öffnen des Dialogs aufgetreten: {e}")
            QMessageBox.critical(self, "Fehler", f"Fehler beim öffnen des Dialogs aufgetreten: {e}")

    def generateNetworkCallback(self, *args):
        # Das letzte Element in args ist import_type
        import_type = args[-1]

        if import_type == "GeoJSON":
            print(*args)
            # Übergeben Sie alle Argumente außer dem letzten (import_type)
            self.create_and_initialize_net_geojson(*args[:-1])
        elif import_type == "Stanet":
            print(*args)
            # Übergeben Sie alle Argumente außer dem letzten (import_type)
            self.create_and_initialize_net_stanet(*args[:-1])
    
    def editHeatDemandData(self, hastInput):
        try:
            self.gdf_HAST = gpd.read_file(hastInput)
            if "Gebäudetyp" not in self.gdf_HAST.columns:
                self.gdf_HAST["Gebäudetyp"] = "HMF"

            self.dialog = HeatDemandEditDialog(self.gdf_HAST, hastInput, self)
            self.dialog.exec_()  # Öffnet den Dialog als Modal
        except Exception as e:
            logging.error(f"Fehler beim Laden der HAST-Daten: {e}")
            QMessageBox.critical(self, "Fehler", "Fehler beim Laden der HAST-Daten.")

    def opencalculateNetDialog(self):
        dialog = ZeitreihenrechnungDialog(self.base_path, self)
        if dialog.exec_():
            netCalcInputs = dialog.getValues()
            self.calc1 = netCalcInputs["start"]
            self.calc2 = netCalcInputs["end"]
            self.output_filename = netCalcInputs["results_filename"]
            self.simulate_net()
      
    def create_and_initialize_net_geojson(self, vorlauf, ruecklauf, hast, erzeugeranlagen, calc_method, building_type, return_temp, supply_temperature, \
                                          flow_pressure_pump, lift_pressure_pump, netconfiguration, dT_RL, building_temp_checked, pipetype, v_max_pipe, material_filter, insulation_filter):
        self.return_temperature = return_temp
        self.supply_temperature = supply_temperature
        supply_temperature = np.max(supply_temperature)
        self.netconfiguration = netconfiguration
        self.dT_RL = dT_RL
        self.building_temp_checked = building_temp_checked
        args = (vorlauf, ruecklauf, hast, erzeugeranlagen, calc_method, building_type, return_temp, supply_temperature, flow_pressure_pump, lift_pressure_pump, \
                netconfiguration, pipetype, v_max_pipe, material_filter, insulation_filter, self.base_path)
        kwargs = {"import_type": "GeoJSON"}
        self.initializationThread = NetInitializationThread(*args, **kwargs)
        self.common_thread_initialization()

    def create_and_initialize_net_stanet(self, stanet_csv, return_temp, supply_temperature, flow_pressure_pump, lift_pressure_pump):
        self.return_temperature = return_temp
        self.supply_temperature = supply_temperature
        supply_temperature = np.max(supply_temperature)
        args = (stanet_csv, return_temp, supply_temperature, flow_pressure_pump, lift_pressure_pump)
        kwargs = {"import_type": "Stanet"}
        self.initializationThread = NetInitializationThread(*args, **kwargs)
        self.common_thread_initialization()

    def common_thread_initialization(self):
        self.initializationThread.calculation_done.connect(self.on_initialization_done)
        self.initializationThread.calculation_error.connect(self.on_simulation_error)
        self.initializationThread.start()
        self.progressBar.setRange(0, 0)  # Aktiviert den indeterministischen Modus

    def on_initialization_done(self, results):
        self.progressBar.setRange(0, 1)  # Deaktiviert den indeterministischen Modus

        # Datenhaltung optimieren
        self.net, self.yearly_time_steps, self.waerme_ges_W, self.return_temperature, self.supply_temperature_buildings, self.return_temperature_buildings, \
            self.supply_temperature_buildings_curve, self.return_temperature_buildings_curve = results
        
        self.net_data = self.net, self.yearly_time_steps, self.waerme_ges_W, self.supply_temperature, self.return_temperature, self.supply_temperature_buildings, self.return_temperature_buildings, \
            self.supply_temperature_buildings_curve, self.return_temperature_buildings_curve, self.netconfiguration, self.dT_RL, self.building_temp_checked

        self.waerme_ges_kW = np.where(self.waerme_ges_W == 0, 0, self.waerme_ges_W / 1000)
        self.plot(self.net, self.yearly_time_steps, self.waerme_ges_kW)

    def plot(self, net, time_steps, qext_kW):
        # Clear previous figure
        self.figure4.clear()
        ax1 = self.figure4.add_subplot(111)

        # Plot für Wärmeleistung auf der ersten Y-Achse
        qext_gesamt_kW = np.sum(qext_kW, axis=0)
        ax1.plot(time_steps, qext_gesamt_kW, 'b-', label=f"Gesamtlast Gebäude")
        ax1.set_xlabel("Zeit")
        ax1.set_ylabel("Wärmebedarf in kW", color='b')
        ax1.tick_params('y', colors='b')
        ax1.legend(loc='upper left')
        ax1.plot
        ax1.grid()
        self.canvas4.draw()

        self.figure5.clear()
        ax = self.figure5.add_subplot(111)
        config_plot(net, ax, show_junctions=True, show_pipes=True, show_flow_controls=False, show_heat_exchangers=True)
        self.canvas5.draw()

    ### Zeitreihensimulation ###
    def simulate_net(self):
        if self.net_data is None:
            QMessageBox.warning(self, "Keine Netzdaten", "Bitte generieren Sie zuerst ein Netz.")
            return
        
        self.net, self.yearly_time_steps, self.waerme_ges_W, self.supply_temperature, self.return_temperature, self.supply_temperature_buildings, self.return_temperature_buildings, \
            self.supply_temperature_buildings_curve, self.return_temperature_buildings_curve, self.netconfiguration, self.dT_RL, self.building_temp_checked = self.net_data

        try:
            self.calculationThread = NetCalculationThread(self.net, self.yearly_time_steps, self.waerme_ges_W, self.calc1, self.calc2, self.supply_temperature, self.return_temperature, \
                                                          self.supply_temperature_buildings, self.return_temperature_buildings, self.supply_temperature_buildings_curve, \
                                                            self.return_temperature_buildings_curve, self.dT_RL, self.netconfiguration, self.building_temp_checked)
            self.calculationThread.calculation_done.connect(self.on_simulation_done)
            self.calculationThread.calculation_error.connect(self.on_simulation_error)
            self.calculationThread.start()
            self.progressBar.setRange(0, 0)  # Aktiviert den indeterministischen Modus

        except ValueError as e:
            QMessageBox.warning("Ungültige Eingabe", str(e))

    def on_simulation_done(self, results):
        self.progressBar.setRange(0, 1)  # Deaktiviert den indeterministischen Modus
        self.time_steps, self.net, self.net_results, self.waerme_ges_W, self.strom_wp_kW = results
        self.mass_flow_circ_pump, self.deltap_circ_pump, self.return_temp_circ_pump, self.flow_temp_circ_pump, \
            self.return_pressure_circ_pump, self.flow_pressure_circ_pump, self.qext_kW, self.pressure_junctions = calculate_results(self.net, self.net_results)

        self.waerme_ges_W = (np.sum(self.waerme_ges_W, axis=0)/1000)[self.calc1:self.calc2]
        
        if self.strom_wp_kW is not None:
            self.strom_wp_kW = (np.sum(self.strom_wp_kW, axis=0)/1000)[self.calc1:self.calc2]

        plot_data =  self.time_steps, self.qext_kW, self.waerme_ges_W, self.flow_temp_circ_pump, self.return_temp_circ_pump, self.mass_flow_circ_pump, self.deltap_circ_pump, \
            self.return_pressure_circ_pump, self.flow_pressure_circ_pump
        
        self.plot_data_func(plot_data)
        self.plot2()

        save_results_csv(self.time_steps, self.qext_kW, self.waerme_ges_W, self.flow_temp_circ_pump, self.return_temp_circ_pump, self.mass_flow_circ_pump, self.deltap_circ_pump, \
                         self.return_pressure_circ_pump, self.flow_pressure_circ_pump, self.output_filename)

    def plot_data_func(self, plot_data):
        self.time_steps, self.qext_kW, self.waerme_ges_W, self.flow_temp_circ_pump, self.return_temp_circ_pump, self.mass_flow_circ_pump, self.deltap_circ_pump, \
        self.return_pressure_circ_pump, self.flow_pressure_circ_pump = plot_data
        
        self.plot_data = {
            "Einspeiseleistung Heizzentrale": {"data": self.qext_kW, "label": "Leistung in kW", "axis": "left"},
            "Gesamtwärmebedarf Wärmeübertrager": {"data": self.waerme_ges_W, "label": "Wärmebedarf in kW", "axis": "left"},
            "Rücklauftemperatur Heizzentrale": {"data": self.return_temp_circ_pump, "label": "Temperatur in °C", "axis": "right"},
            "Vorlauftemperatur Heizzentrale": {"data": self.flow_temp_circ_pump, "label": "Temperatur in °C", "axis": "right"},
            "Massenstrom Heizzentrale": {"data": self.mass_flow_circ_pump, "label": "Massenstrom in kg/s", "axis": "right"},
            "Delta p Heizzentrale": {"data": self.deltap_circ_pump, "label": "Druck in bar", "axis": "right"},
            "Rücklaufdruck Heizzentrale": {"data": self.return_pressure_circ_pump, "label": "Druck in bar", "axis": "right"},
            "Vorlaufdruck Heizzentrale": {"data": self.flow_pressure_circ_pump, "label": "Druck in bar", "axis": "right"}
        }

    def on_simulation_error(self, error_message):
        QMessageBox.critical(self, "Berechnungsfehler", error_message)
        self.progressBar.setRange(0, 1)  # Deaktiviert den indeterministischen Modus

    def closeEvent(self, event):
        if hasattr(self, 'calculationThread') and self.calculationThread.isRunning():
            reply = QMessageBox.question(self, 'Thread läuft noch',
                                         "Eine Berechnung läuft noch. Wollen Sie wirklich beenden?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                self.calculationThread.stop()  # Stellen Sie sicher, dass der Thread beendet wird
                event.accept()  # Schließen Sie das Fenster
            else:
                event.ignore()  # Lassen Sie das Fenster offen
        else:
            event.accept()  # Schließen Sie das Fenster, wenn kein Thread läuft
    
    def plot2(self):
        if not hasattr(self, 'dataSelectionDropdown'):
            self.createPlotControlDropdown()
        
        self.updatePlot()  # Rufen Sie updatePlot auf, um den initialen Plot zu zeichnen

    def updatePlot(self):
        self.figure3.clear()
        ax_left = self.figure3.add_subplot(111)
        ax_right = ax_left.twinx()

        left_labels = set()
        right_labels = set()
        color_cycle = itertools.cycle(['b', 'g', 'r', 'c', 'm', 'y', 'k'])

        for i in range(self.dataSelectionDropdown.model().rowCount()):
            if self.dataSelectionDropdown.itemChecked(i):
                key = self.dataSelectionDropdown.itemText(i)
                data_info = self.plot_data[key]
                color = next(color_cycle)
                if data_info["axis"] == "left":
                    ax_left.plot(self.time_steps, data_info["data"], label=key, color=color)
                    left_labels.add(data_info["label"])
                elif data_info["axis"] == "right":
                    ax_right.plot(self.time_steps, data_info["data"], label=key, color=color)
                    right_labels.add(data_info["label"])

        ax_left.set_xlabel("Zeit")
        ax_left.set_ylabel(", ".join(left_labels))
        ax_right.set_ylabel(", ".join(right_labels))

        # Erstellen der Legenden und Zusammenführen
        lines_left, labels_left = ax_left.get_legend_handles_labels()
        lines_right, labels_right = ax_right.get_legend_handles_labels()
        by_label = dict(zip(labels_left + labels_right, lines_left + lines_right))
        ax_left.legend(by_label.values(), by_label.keys(), loc='upper left')

        ax_left.grid()
        self.canvas3.draw()

    def saveNet(self):
        pickle_file_path = f"{self.base_path}\Wärmenetz\Ergebnisse Netzinitialisierung.p"
        csv_file_path = f"{self.base_path}\Wärmenetz\Ergebnisse Netzinitialisierung.csv"
        json_file_path = f"{self.base_path}\Wärmenetz\Konfiguration Netzinitialisierung.json"
        
        if self.net_data:  # Überprüfe, ob das Netzwerk vorhanden ist
            try:
                self.net, self.yearly_time_steps, self.waerme_ges_W, self.supply_temperature, self.return_temperature, self.supply_temperature_buildings, self.return_temperature_buildings, \
                self.supply_temperature_buildings_curve, self.return_temperature_buildings_curve, self.netconfiguration, self.dT_RL, self.building_temp_checked = self.net_data

                # Pandapipes-Netz als pickle speichern
                pp.to_pickle(self.net, pickle_file_path)
                
                # Umwandlung der Daten in ein DataFrame und Speichern als CSV
                data = np.column_stack([self.waerme_ges_W[i] for i in range(self.waerme_ges_W.shape[0])])
                df = pd.DataFrame(data, index=self.yearly_time_steps, columns=[f'waerme_ges_W_{i+1}' for i in range(self.waerme_ges_W.shape[0])])
                df.to_csv(csv_file_path, sep=';', date_format='%Y-%m-%dT%H:%M:%S')

                # Vorbereiten der zusätzlichen Daten für JSON
                additional_data = {
                    'supply_temperature': self.supply_temperature.tolist(),
                    'return_temperature': self.return_temperature.tolist(),
                    'supply_temperature_buildings': self.supply_temperature_buildings.tolist(),
                    'return_temperature_buildings': self.return_temperature_buildings.tolist(),
                    'supply_temperature_buildings_curve': self.supply_temperature_buildings_curve.tolist(),
                    'return_temperature_buildings_curve': self.return_temperature_buildings_curve.tolist(),
                    'netconfiguration': self.netconfiguration,
                    'dT_RL': self.dT_RL,
                    'building_temp_checked': self.building_temp_checked
                }
                
                # Speichern der zusätzlichen Daten als JSON
                with open(json_file_path, 'w') as json_file:
                    json.dump(additional_data, json_file, indent=4)
                
                QMessageBox.information(self, "Speichern erfolgreich", f"Pandapipes Netz erfolgreich gespeichert in: {pickle_file_path}, Daten erfolgreich gespeichert in: {csv_file_path} und {json_file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Speichern fehlgeschlagen", f"Fehler beim Speichern der Daten: {e}")
        else:
            QMessageBox.warning(self, "Keine Daten", "Kein Pandapipes-Netzwerk zum Speichern vorhanden.")

    def loadNet(self):
        csv_file_path = f"{self.base_path}\Wärmenetz\Ergebnisse Netzinitialisierung.csv"
        pickle_file_path = f"{self.base_path}\Wärmenetz\Ergebnisse Netzinitialisierung.p"
        json_file_path = f"{self.base_path}\Wärmenetz\Konfiguration Netzinitialisierung.json"  # Pfad zur JSON-Datei
        
        try:
            # Laden des Pandapipes-Netzes aus der Pickle-Datei
            self.net = pp.from_pickle(pickle_file_path)
            
            # Laden der Wärmeleistungsdaten aus der CSV-Datei
            with open(csv_file_path, newline='') as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                next(reader)  # Überspringe die Kopfzeile
                
                formatted_time_steps = []
                waerme_ges_W_data = []
                
                for row in reader:
                    formatted_time_steps.append(np.datetime64(row[0]))
                    waerme_ges_W_data.append([float(value) for value in row[1:]])
                
                self.yearly_time_steps = np.array(formatted_time_steps)
                self.waerme_ges_W = np.array(waerme_ges_W_data).transpose()
                
            # Laden der zusätzlichen Daten aus der JSON-Datei
            with open(json_file_path, 'r') as json_file:
                additional_data = json.load(json_file)
                
            # Rekonstruktion der zusätzlichen Daten
            self.supply_temperature = np.array(additional_data['supply_temperature'])
            self.return_temperature = np.array(additional_data['return_temperature'])
            self.supply_temperature_buildings = np.array(additional_data['supply_temperature_buildings'])
            self.return_temperature_buildings = np.array(additional_data['return_temperature_buildings'])
            self.supply_temperature_buildings_curve = np.array(additional_data['supply_temperature_buildings_curve'])
            self.return_temperature_buildings_curve = np.array(additional_data['return_temperature_buildings_curve'])
            self.netconfiguration = additional_data['netconfiguration']
            self.dT_RL = additional_data['dT_RL']
            self.building_temp_checked = additional_data['building_temp_checked']
            
            # Aktualisierung der net_data Eigenschaft mit den geladenen Daten
            self.net_data = self.net, self.yearly_time_steps, self.waerme_ges_W, self.supply_temperature, self.return_temperature, self.supply_temperature_buildings, self.return_temperature_buildings, \
                            self.supply_temperature_buildings_curve, self.return_temperature_buildings_curve, self.netconfiguration, self.dT_RL, self.building_temp_checked
            
            # Weiterverarbeitung oder Anzeigen der geladenen Daten
            self.waerme_ges_kW = np.where(self.waerme_ges_W == 0, 0, self.waerme_ges_W / 1000)
            self.plot(self.net, self.yearly_time_steps, self.waerme_ges_kW)
            
            QMessageBox.information(self, "Laden erfolgreich", "Daten erfolgreich geladen aus: {}, {} und {}.".format(csv_file_path, pickle_file_path, json_file_path))
        except Exception as e:
            QMessageBox.critical(self, "Laden fehlgeschlagen", "Fehler beim Laden der Daten: {}".format(e))

    def load_net_results(self):
        results_csv_filepath = f"{self.base_path}\Lastgang\Lastgang.csv"
        plot_data = import_results_csv(results_csv_filepath)
        self.time_steps, self.qext_kW, self.waerme_ges_W, self.flow_temp_circ_pump, self.return_temp_circ_pump, self.mass_flow_circ_pump, self.deltap_circ_pump, self.return_pressure_circ_pump, self.flow_pressure_circ_pump = plot_data
        self.plot_data_func(plot_data)
        self.plot2()
    
    def exportNetGeoJSON(self):
        geoJSON_filepath = f"{self.base_path}\Wärmenetz\dimensioniertes Wärmenetz.geojson"
        if self.net_data:  # Überprüfe, ob das Netzwerk vorhanden ist
            net = self.net_data[0]
            
            try:
                export_net_geojson(net, geoJSON_filepath)
                
                QMessageBox.information(self, "Speichern erfolgreich", f"Pandapipes Wärmenetz erfolgreich als geoJSON gespeichert in: {geoJSON_filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Speichern fehlgeschlagen", f"Fehler beim Speichern der Daten: {e}")
