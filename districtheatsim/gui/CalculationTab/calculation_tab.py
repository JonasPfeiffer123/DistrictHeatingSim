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
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QMessageBox, QProgressBar, QMenuBar, QAction, QActionGroup, QPlainTextEdit

from net_simulation_pandapipes.pp_net_time_series_simulation import calculate_results, save_results_csv, import_results_csv

from gui.CalculationTab.calculation_dialogs import HeatDemandEditDialog, NetGenerationDialog, ZeitreihenrechnungDialog
from gui.threads import NetInitializationThread, NetCalculationThread
from net_simulation_pandapipes.config_plot import config_plot
from gui.checkable_combobox import CheckableComboBox

from net_simulation_pandapipes.utilities import export_net_geojson

class CalculationTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent
        self.calc_method = "Datensatz"
        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        # Update the base path immediately with the current project folder
        self.updateDefaultPath(self.data_manager.project_folder)
        self.show_map = False
        self.map_type = None
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
        self.main_layout = QHBoxLayout(self)
        self.main_layout.addWidget(scroll_area)

        # Vertikales Layout für Berechnungsergebnisse
        self.results_layout = QVBoxLayout()
        self.results_display = QPlainTextEdit()
        self.results_display.setReadOnly(True)
        self.results_display.setFixedWidth(400)  # Setze eine feste Breite für das Ergebnisfeld
        self.results_layout.addWidget(self.results_display)


        # Füge das vertikale Layout zum Hauptlayout hinzu
        self.main_layout.addLayout(self.results_layout)

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
        mapMenu = self.menubar.addMenu('Hintergrundkarte laden')

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

        # Kartenaktionen erstellen
        OSMAction = QAction('OpenStreetMap laden', self)
        SatelliteMapAction = QAction('Satellitenbild Laden', self)
        TopologyMapAction = QAction('Topologiekarte laden', self)

        # Aktionen auf checkable setzen
        OSMAction.setCheckable(True)
        SatelliteMapAction.setCheckable(True)
        TopologyMapAction.setCheckable(True)

        # QActionGroup für exklusive Auswahl erstellen
        mapActionGroup = QActionGroup(self)
        mapActionGroup.setExclusive(True)
        mapActionGroup.addAction(OSMAction)
        mapActionGroup.addAction(SatelliteMapAction)
        mapActionGroup.addAction(TopologyMapAction)

        # Aktionen dem Menü hinzufügen
        mapMenu.addAction(OSMAction)
        mapMenu.addAction(SatelliteMapAction)
        mapMenu.addAction(TopologyMapAction)

        # Fügen Sie die Menüleiste dem Layout von tab1 hinzu
        self.container_layout.addWidget(self.menubar)

        # Verbindungen zu den Funktionen
        generateNetAction.triggered.connect(self.openNetGenerationDialog)
        saveppnetAction.triggered.connect(self.saveNet)
        loadppnetAction.triggered.connect(self.loadNet)
        loadresultsppAction.triggered.connect(self.load_net_results)
        exportppnetGeoJSONAction.triggered.connect(self.exportNetGeoJSON)
        calculateNetAction.triggered.connect(self.opencalculateNetDialog)
        OSMAction.triggered.connect(lambda: self.loadMap("OSM", OSMAction))
        SatelliteMapAction.triggered.connect(lambda: self.loadMap("Satellite", SatelliteMapAction))
        TopologyMapAction.triggered.connect(lambda: self.loadMap("Topology", TopologyMapAction))

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
      
    def create_and_initialize_net_geojson(self, vorlauf, ruecklauf, hast, erzeugeranlagen, calc_method, building_type, supply_temperature_heat_consumer, return_temperature_heat_consumer, supply_temperature, \
                                          flow_pressure_pump, lift_pressure_pump, netconfiguration, dT_RL, v_max_heat_consumer, building_temp_checked, \
                                          pipetype, v_max_pipe, material_filter, insulation_filter, DiameterOpt_ckecked):
        self.supply_temperature_heat_consumer = supply_temperature_heat_consumer
        self.return_temperature_heat_consumer = return_temperature_heat_consumer
        self.supply_temperature = supply_temperature
        self.netconfiguration = netconfiguration
        self.dT_RL = dT_RL
        self.v_max_heat_consumer = v_max_heat_consumer
        self.building_temp_checked = building_temp_checked
        self.DiameterOpt_ckecked = DiameterOpt_ckecked
        self.TRY_filename = self.parent.try_filename
        self.COP_filename = self.parent.cop_filename
        args = (vorlauf, ruecklauf, hast, erzeugeranlagen, self.TRY_filename, self.COP_filename, calc_method, building_type, return_temperature_heat_consumer, supply_temperature_heat_consumer, supply_temperature, flow_pressure_pump, lift_pressure_pump, \
                netconfiguration, pipetype, v_max_pipe, material_filter, insulation_filter, self.base_path, self.dT_RL, self.v_max_heat_consumer, self.DiameterOpt_ckecked)
        kwargs = {"import_type": "GeoJSON"}
        self.initializationThread = NetInitializationThread(*args, **kwargs)
        self.common_thread_initialization()

    def create_and_initialize_net_stanet(self, stanet_csv, return_temp, supply_temperature, flow_pressure_pump, lift_pressure_pump):
        self.return_temperature_heat_consumer = return_temp
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
        self.net, self.yearly_time_steps, self.waerme_ges_W, self.supply_temperature_heat_consumer, self.return_temperature_heat_consumer, self.supply_temperature_buildings, self.return_temperature_buildings, \
            self.supply_temperature_buildings_curve, self.return_temperature_buildings_curve, self.strombedarf_hast_ges_W, self.max_el_leistung_hast_ges_W = results
        
        self.net_data = self.net, self.yearly_time_steps, self.waerme_ges_W, self.supply_temperature_heat_consumer, self.supply_temperature, self.return_temperature_heat_consumer, self.supply_temperature_buildings, self.return_temperature_buildings, \
            self.supply_temperature_buildings_curve, self.return_temperature_buildings_curve, self.netconfiguration, self.dT_RL, self.building_temp_checked, self.strombedarf_hast_ges_W, \
            self.max_el_leistung_hast_ges_W, self.TRY_filename, self.COP_filename

        self.waerme_ges_kW = np.where(self.waerme_ges_W == 0, 0, self.waerme_ges_W / 1000)
        self.strombedarf_hast_ges_kW = np.where(self.strombedarf_hast_ges_W == 0, 0, self.strombedarf_hast_ges_W / 1000)
        self.max_el_leistung_hast_ges_W = self.max_el_leistung_hast_ges_W

        self.waerme_ges_kW = np.sum(self.waerme_ges_kW, axis=0)
        self.strombedarf_hast_ges_kW = np.sum(self.strombedarf_hast_ges_kW, axis=0)

        self.plot(self.yearly_time_steps, self.waerme_ges_kW, self.strombedarf_hast_ges_kW)
        self.display_results()

    def display_results(self):
        Anzahl_Gebäude = len(self.net.heat_consumer)
        
        # Überprüfen, ob 'circ_pump_mass' im Netz vorhanden ist
        if hasattr(self.net, 'circ_pump_mass'):
            Anzahal_Heizzentralen = len(self.net.circ_pump_pressure) + len(self.net.circ_pump_mass)
        else:
            Anzahal_Heizzentralen = len(self.net.circ_pump_pressure)

        # Beispielberechnungen
        Gesamtwärmebedarf_Gebäude_MWh = np.sum(self.waerme_ges_kW) / 1000
        Gesamtheizlast_Gebäude_kW = np.max(self.waerme_ges_kW)
        
        # Berechnung der Trassenlänge aus dem pandapipes-Netz
        Trassenlänge_m = self.net.pipe.length_km.sum() * 1000 / 2 # Länge in Metern Trassenlänge ist nur halb so groß wie die von Vor- und Rücklauf zusammen
        
        Wärmebedarfsdichte_MWh_a_m = Gesamtwärmebedarf_Gebäude_MWh / Trassenlänge_m
        Anschlussdichte_kW_m = Gesamtheizlast_Gebäude_kW / Trassenlänge_m

        Jahreswärmeerzeugung_MWh = 0
        Pumpenstrombedarf_MWh = 0
        for pump_type, pumps in self.pump_results.items():
            for idx, pump_data in pumps.items():
                Jahreswärmeerzeugung_MWh += np.sum(pump_data['qext_kW']) / 1000
                Pumpenstrombedarf_MWh += np.sum((pump_data['mass_flow']/1000)*(pump_data['deltap']*100)) / 1000 # kg/s * bar-> m³/s * kPa = kW 
        Verteilverluste_kW = Jahreswärmeerzeugung_MWh - Gesamtwärmebedarf_Gebäude_MWh
        rel_Verteilverluste_percent = (Verteilverluste_kW / Jahreswärmeerzeugung_MWh) * 100

        #strombedarf_pumpen_kW = 

        # Formatierter Text
        self.result_text = (
            f"Anzahl angeschlossene Gebäude: {Anzahl_Gebäude}\n"
            f"Anzahl Heizzentralen: {Anzahal_Heizzentralen}\n\n"
            f"Jahresgesamtwärmebedarf Gebäude: {Gesamtwärmebedarf_Gebäude_MWh:.2f} MWh/a\n"
            f"max. Heizlast Gebäude: {Gesamtheizlast_Gebäude_kW:.2f} kW\n"
            f"Trassenlänge Wärmenetz: {Trassenlänge_m:.2f} m\n\n"
            f"Wärmebedarfsdichte: {Wärmebedarfsdichte_MWh_a_m:.2f} MWh/(a*m)\n"
            f"Anschlussdichte: {Anschlussdichte_kW_m:.2f} kW/m\n\n"
            f"Jahreswärmeerzeugung: {Jahreswärmeerzeugung_MWh:.2f} MWh\n"
            f"Verteilverluste: {Verteilverluste_kW:.2f} MWh\n"
            f"rel. Verteilverluste: {rel_Verteilverluste_percent:.2f} %\n\n"
            f"Pumpenstrom: {Pumpenstrombedarf_MWh:.2f} MWh\n"
        )
        
        self.results_display.setPlainText(self.result_text)  # Setze den Text in das Ergebnisfeld

    def plot(self, time_steps, qext_kW, strom_kW):
        # Clear previous figure
        self.figure4.clear()
        ax1 = self.figure4.add_subplot(111)

        if np.sum(strom_kW) == 0:
            ax1.plot(time_steps, qext_kW, 'b-', label=f"Gesamtheizlast Gebäude in kW")

        if np.sum(strom_kW) > 0:
            ax1.plot(time_steps, qext_kW+strom_kW, 'b-', label=f"Gesamtheizlast Gebäude in kW")
            ax1.plot(time_steps, strom_kW, 'g-', label=f"Gesamtstrombedarf Wärmepumpen Gebäude in kW")

        ax1.set_xlabel("Zeit")
        ax1.set_ylabel("Leistung in kW", color='b')
        ax1.tick_params('y', colors='b')
        ax1.legend(loc='upper left')
        ax1.plot
        ax1.grid()
        self.canvas4.draw()

        self.plotNet()

    def plotNet(self):
        self.figure5.clear()
        ax = self.figure5.add_subplot(111)
        config_plot(self.net, ax, show_junctions=True, show_pipes=True, show_heat_consumers=True, show_basemap=self.show_map, map_type=self.map_type)
        self.canvas5.draw()

    def loadMap(self, map_type, action):
        if action.isChecked():
            self.show_map = True
            self.map_type = map_type
            # Deaktivieren Sie die anderen Aktionen
            for act in action.parent().actions():
                if act != action:
                    act.setChecked(False)
        else:
            self.show_map = False
            self.map_type = None

        # Aktualisieren Sie den Plot hier
        #if self.net:
        #    self.plotNet()

    ### Zeitreihensimulation ###
    def simulate_net(self):
        if self.net_data is None:
            QMessageBox.warning(self, "Keine Netzdaten", "Bitte generieren Sie zuerst ein Netz.")
            return
        
        self.net, self.yearly_time_steps, self.waerme_ges_W, self.supply_temperature_heat_consumer, self.supply_temperature, self.return_temperature_heat_consumer, self.supply_temperature_buildings, \
            self.return_temperature_buildings, self.supply_temperature_buildings_curve, self.return_temperature_buildings_curve, self.netconfiguration, self.dT_RL, self.building_temp_checked, \
                self.strombedarf_hast_ges_W, self.max_el_leistung_hast_ges_W, self.TRY_filename, self.COP_filename = self.net_data

        try:
            self.calculationThread = NetCalculationThread(self.net, self.yearly_time_steps, self.waerme_ges_W, self.calc1, self.calc2, self.supply_temperature, self.supply_temperature_heat_consumer, \
                                                          self.return_temperature_heat_consumer, self.supply_temperature_buildings, self.return_temperature_buildings, self.supply_temperature_buildings_curve, \
                                                            self.return_temperature_buildings_curve, self.dT_RL, self.netconfiguration, self.building_temp_checked, self.TRY_filename, self.COP_filename)
            self.calculationThread.calculation_done.connect(self.on_simulation_done)
            self.calculationThread.calculation_error.connect(self.on_simulation_error)
            self.calculationThread.start()
            self.progressBar.setRange(0, 0)  # Aktiviert den indeterministischen Modus

        except ValueError as e:
            QMessageBox.warning("Ungültige Eingabe", str(e))

    def on_simulation_done(self, results):
        self.progressBar.setRange(0, 1)  # Deaktiviert den indeterministischen Modus
        self.time_steps, self.net, self.net_results, self.waerme_ges_W, self.strom_wp_W = results

        # Berechung Wärme und Strom
        self.waerme_ges_kW = (np.sum(self.waerme_ges_W, axis=0)/1000)[self.calc1:self.calc2]
        self.strom_wp_kW = (np.sum(self.strom_wp_W, axis=0)/1000)[self.calc1:self.calc2]

        # Verarbeitung der Zeitreihen-Ergebnisse
        self.pump_results = calculate_results(self.net, self.net_results)

        # Definition der plot-Daten
        self.plot_data =  self.time_steps, self.waerme_ges_kW, self.strom_wp_kW, self.pump_results
        self.plot_data_func(self.plot_data)
        self.plot2()
        self.display_results()
        save_results_csv(self.time_steps, self.waerme_ges_kW, self.strom_wp_kW, self.pump_results, self.output_filename)

    def plot_data_func(self, plot_data):
        self.time_steps, self.waerme_ges_kW, self.strom_wp_kW, pump_results = plot_data
        
        self.plot_data = {
            "Gesamtwärmebedarf Wärmeübertrager": {"data": self.waerme_ges_kW, "label": "Wärmebedarf Wärmeübertrager in kW", "axis": "left"}
        }
        if np.sum(self.strom_wp_kW) > 0:
            self.plot_data[f"Gesamtheizlast Gebäude"] = {"data": self.waerme_ges_kW+self.strom_wp_kW, "label": "Gesamtheizlast Gebäude in kW", "axis": "left"}
            self.plot_data[f"Gesamtstrombedarf Wärmepumpen Gebäude"] = {"data": self.strom_wp_kW, "label": "Gesamtstrombedarf Wärmepumpen Gebäude in kW", "axis": "left"}

         # Fügen Sie für jede Pumpe Einträge hinzu
        for pump_type, pumps in pump_results.items():
            for idx, pump_data in pumps.items():
                self.plot_data[f"Wärmeerzeugung {pump_type} {idx+1}"] = {"data": pump_data['qext_kW'], "label": "Wärmeerzeugung in kW", "axis": "left"}
                self.plot_data[f"Massenstrom {pump_type} {idx+1}"] = {"data": pump_data['mass_flow'], "label": "Massenstrom in kg/s", "axis": "right"}
                self.plot_data[f"Delta p {pump_type} {idx+1}"] = {"data": pump_data['deltap'], "label": "Druckdifferenz in bar", "axis": "right"}
                self.plot_data[f"Vorlauftemperatur {pump_type} {idx+1}"] = {"data": pump_data['flow_temp'], "label": "Temperatur in °C", "axis": "right"}
                self.plot_data[f"Rücklauftemperatur {pump_type} {idx+1}"] = {"data": pump_data['return_temp'], "label": "Temperatur in °C", "axis": "right"}
                self.plot_data[f"Vorlaufdruck {pump_type} {idx+1}"] = {"data": pump_data['flow_pressure'], "label": "Druck in bar", "axis": "right"}
                self.plot_data[f"Rücklaufdruck {pump_type} {idx+1}"] = {"data": pump_data['return_pressure'], "label": "Druck in bar", "axis": "right"}

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
                self.net, self.yearly_time_steps, self.waerme_ges_W, self.supply_temperature_heat_consumer, self.supply_temperature, self.return_temperature_heat_consumer, self.supply_temperature_buildings, self.return_temperature_buildings, \
                self.supply_temperature_buildings_curve, self.return_temperature_buildings_curve, self.netconfiguration, self.dT_RL, self.building_temp_checked, self.strombedarf_hast_ges_W, \
                    self.max_el_leistung_hast_ges_W, self.TRY_filename, self.COP_filename = self.net_data

                # Pandapipes-Netz als pickle speichern
                pp.to_pickle(self.net, pickle_file_path)
                
                # Umwandlung der Daten in ein DataFrame und Speichern als CSV
                # Umwandlung der Wärmedaten in ein DataFrame
                waerme_data = np.column_stack([self.waerme_ges_W[i] for i in range(self.waerme_ges_W.shape[0])])
                waerme_df = pd.DataFrame(waerme_data, index=self.yearly_time_steps, columns=[f'waerme_ges_W_{i+1}' for i in range(self.waerme_ges_W.shape[0])])

                # Umwandlung der Strombedarfsdaten in ein DataFrame
                strom_data = np.column_stack([self.strombedarf_hast_ges_W[i] for i in range(self.strombedarf_hast_ges_W.shape[0])])
                strom_df = pd.DataFrame(strom_data, index=self.yearly_time_steps, columns=[f'strombedarf_hast_ges_W_{i+1}' for i in range(self.strombedarf_hast_ges_W.shape[0])])

                # Zusammenführen der DataFrames
                combined_df = pd.concat([waerme_df, strom_df], axis=1)

                # Speichern des kombinierten DataFrames als CSV
                combined_df.to_csv(csv_file_path, sep=';', date_format='%Y-%m-%dT%H:%M:%S')

                # Vorbereiten der zusätzlichen Daten für JSON
                additional_data = {
                    'supply_temperature': self.supply_temperature.tolist(),
                    'supply_temperature_heat_consumers': self.supply_temperature_heat_consumer,
                    'return_temperature': self.return_temperature_heat_consumer.tolist(),
                    'supply_temperature_buildings': self.supply_temperature_buildings.tolist(),
                    'return_temperature_buildings': self.return_temperature_buildings.tolist(),
                    'supply_temperature_buildings_curve': self.supply_temperature_buildings_curve.tolist(),
                    'return_temperature_buildings_curve': self.return_temperature_buildings_curve.tolist(),
                    'netconfiguration': self.netconfiguration,
                    'dT_RL': self.dT_RL,
                    'building_temp_checked': self.building_temp_checked,
                    'max_el_leistung_hast_ges_W': self.max_el_leistung_hast_ges_W.tolist(),
                    'TRY_filename': self.TRY_filename, 
                    'COP_filename': self.COP_filename
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
            
            # Laden der Daten aus der CSV-Datei
            with open(csv_file_path, newline='') as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                headers = next(reader)  # Kopfzeile einlesen
                num_waerme_cols = len([h for h in headers if h.startswith('waerme_ges_W')])
                num_strom_cols = len([h for h in headers if h.startswith('strombedarf_hast_ges_W')])

                formatted_time_steps = []
                waerme_ges_W_data = []
                strombedarf_hast_ges_W_data = []
                
                for row in reader:
                    formatted_time_steps.append(np.datetime64(row[0]))
                    waerme_ges_W_data.append([float(value) for value in row[1:num_waerme_cols + 1]])
                    strombedarf_hast_ges_W_data.append([float(value) for value in row[num_waerme_cols + 1:num_waerme_cols + num_strom_cols + 1]])
                
                self.yearly_time_steps = np.array(formatted_time_steps)
                self.waerme_ges_W = np.array(waerme_ges_W_data).transpose()
                self.strombedarf_hast_ges_W = np.array(strombedarf_hast_ges_W_data).transpose()


                
            # Laden der zusätzlichen Daten aus der JSON-Datei
            with open(json_file_path, 'r') as json_file:
                additional_data = json.load(json_file)
                
            # Rekonstruktion der zusätzlichen Daten
            self.supply_temperature = np.array(additional_data['supply_temperature'])
            self.supply_temperature_heat_consumer = float(additional_data['supply_temperature_heat_consumers'])
            self.return_temperature_heat_consumer = np.array(additional_data['return_temperature'])
            self.supply_temperature_buildings = np.array(additional_data['supply_temperature_buildings'])
            self.return_temperature_buildings = np.array(additional_data['return_temperature_buildings'])
            self.supply_temperature_buildings_curve = np.array(additional_data['supply_temperature_buildings_curve'])
            self.return_temperature_buildings_curve = np.array(additional_data['return_temperature_buildings_curve'])
            self.netconfiguration = additional_data['netconfiguration']
            self.dT_RL = additional_data['dT_RL']
            self.building_temp_checked = additional_data['building_temp_checked']
            self.max_el_leistung_hast_ges_W = np.array(additional_data['max_el_leistung_hast_ges_W'])
            self.TRY_filename =  additional_data['TRY_filename']
            self.COP_filename =  additional_data['COP_filename']
            
            # Aktualisierung der net_data Eigenschaft mit den geladenen Daten
            self.net_data = self.net, self.yearly_time_steps, self.waerme_ges_W, self.supply_temperature_heat_consumer, self.supply_temperature, self.return_temperature_heat_consumer, self.supply_temperature_buildings, self.return_temperature_buildings, \
                            self.supply_temperature_buildings_curve, self.return_temperature_buildings_curve, self.netconfiguration, self.dT_RL, self.building_temp_checked, self.strombedarf_hast_ges_W, \
                            self.max_el_leistung_hast_ges_W, self.TRY_filename, self.COP_filename
            
            # Weiterverarbeitung oder Anzeigen der geladenen Daten
            self.waerme_ges_kW = np.where(self.waerme_ges_W == 0, 0, self.waerme_ges_W / 1000)
            self.strombedarf_hast_ges_kW = np.where(self.strombedarf_hast_ges_W == 0, 0, self.strombedarf_hast_ges_W / 1000)
            
            self.waerme_ges_kW = np.sum(self.waerme_ges_kW, axis=0)
            self.strombedarf_hast_ges_kW = np.sum(self.strombedarf_hast_ges_kW, axis=0)

            self.plot(self.yearly_time_steps, self.waerme_ges_kW, self.strombedarf_hast_ges_kW)
            self.display_results()

            QMessageBox.information(self, "Laden erfolgreich", "Daten erfolgreich geladen aus: {}, {} und {}.".format(csv_file_path, pickle_file_path, json_file_path))
        except Exception as e:
            QMessageBox.critical(self, "Laden fehlgeschlagen", "Fehler beim Laden der Daten: {}".format(e))

    def load_net_results(self):
        # das hier vielleicht noch variabel
        results_csv_filepath = f"{self.base_path}\Lastgang\Lastgang.csv"
        plot_data = import_results_csv(results_csv_filepath)
        self.time_steps, self.waerme_ges_kW, self.strom_wp_kW, self.pump_results = plot_data
        self.plot_data_func(plot_data)
        self.plot2()
        self.display_results()
    
    def exportNetGeoJSON(self):
        geoJSON_filepath = f"{self.base_path}\Wärmenetz\dimensioniertes Wärmenetz.geojson"
        if self.net_data:  # Überprüfe, ob das Netzwerk vorhanden ist
            net = self.net_data[0]
            
            try:
                export_net_geojson(net, geoJSON_filepath)
                
                QMessageBox.information(self, "Speichern erfolgreich", f"Pandapipes Wärmenetz erfolgreich als geoJSON gespeichert in: {geoJSON_filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Speichern fehlgeschlagen", f"Fehler beim Speichern der Daten: {e}")
