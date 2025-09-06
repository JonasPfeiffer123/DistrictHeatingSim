"""
Network Simulation Tab Module
=============================

District heating network simulation and calculation interface with pandapipes integration.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-17
"""

import logging
import numpy as np
import pandapipes as pp
import csv
import pandas as pd
import itertools
import json
import os
import traceback

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QMessageBox, QProgressBar, QMenuBar, QPlainTextEdit
from PyQt6.QtGui import QAction, QActionGroup

from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import save_results_csv, import_results_csv
from districtheatingsim.net_simulation_pandapipes.config_plot import config_plot
from districtheatingsim.net_simulation_pandapipes.utilities import export_net_geojson

from districtheatingsim.gui.NetSimulationTab.timeseries_dialog import TimeSeriesCalculationDialog
from districtheatingsim.gui.NetSimulationTab.net_generation_dialog import NetGenerationDialog
from districtheatingsim.gui.NetSimulationTab.net_calculation_threads import NetInitializationThread, NetCalculationThread
from districtheatingsim.net_simulation_pandapipes.NetworkDataClass import NetworkGenerationData

from districtheatingsim.gui.utilities import CheckableComboBox

class CalculationTab(QWidget):
    """
    Network simulation tab for district heating system calculations.
    
    Provides interface for network generation, time series simulation,
    and visualization of heating network data using pandapipes.
    """

    data_added = pyqtSignal(object)

    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        """
        Initialize calculation tab.

        Parameters
        ----------
        folder_manager : object
            Project folder manager.
        data_manager : object
            Application data manager.
        config_manager : object
            Configuration manager.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.folder_manager.variant_folder)

        self.show_map = False
        self.map_type = None

        self.initUI()

        self.NetworkGenerationData = None

    def updateDefaultPath(self, new_base_path):
        """
        Update project base path.

        Parameters
        ----------
        new_base_path : str
            New base path.
        """
        self.base_path = new_base_path

    def initUI(self):
        """Initialize user interface components."""
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        container_widget = QWidget()
        scroll_area.setWidget(container_widget)

        self.container_layout = QVBoxLayout(container_widget)

        self.initMenuBar()
        self.setupPlotLayout()

        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(scroll_area)

        self.results_layout = QVBoxLayout()
        self.results_display = QPlainTextEdit()
        self.results_display.setReadOnly(True)
        self.results_display.setFixedHeight(250)
        self.results_layout.addWidget(self.results_display)

        self.main_layout.addLayout(self.results_layout)
        self.setLayout(self.main_layout)

        self.progressBar = QProgressBar(self)
        self.container_layout.addWidget(self.progressBar)

    def initMenuBar(self):
        """Initialize menu bar with file and calculation actions."""
        self.menubar = QMenuBar(self)
        self.menubar.setFixedHeight(30)

        fileMenu = self.menubar.addMenu('Datei')
        networkMenu = self.menubar.addMenu('Wärmenetz generieren')
        calcMenu = self.menubar.addMenu('Zeitreihenberechnung durchführen')
        mapMenu = self.menubar.addMenu('Hintergrundkarte laden')

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

        OSMAction = QAction('OpenStreetMap laden', self)
        SatelliteMapAction = QAction('Satellitenbild Laden', self)
        TopologyMapAction = QAction('Topologiekarte laden', self)

        OSMAction.setCheckable(True)
        SatelliteMapAction.setCheckable(True)
        TopologyMapAction.setCheckable(True)

        mapActionGroup = QActionGroup(self)
        mapActionGroup.setExclusive(True)
        mapActionGroup.addAction(OSMAction)
        mapActionGroup.addAction(SatelliteMapAction)
        mapActionGroup.addAction(TopologyMapAction)

        mapMenu.addAction(OSMAction)
        mapMenu.addAction(SatelliteMapAction)
        mapMenu.addAction(TopologyMapAction)

        self.container_layout.addWidget(self.menubar)

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
        """Setup horizontal layout for network and time series plots."""
        self.scrollArea = QScrollArea(self)
        self.scrollWidget = QWidget()
        self.scrollLayout = QHBoxLayout(self.scrollWidget)

        # Left: Pandapipes net plot
        self.pandapipes_net_figure = Figure()
        self.pandapipes_net_canvas = FigureCanvas(self.pandapipes_net_figure)
        self.pandapipes_net_canvas.setMinimumSize(250, 250)
        self.pandapipes_net_figure_toolbar = NavigationToolbar(self.pandapipes_net_canvas, self)

        # Right: Time series plot
        self.time_series_figure = Figure()
        self.time_series_canvas = FigureCanvas(self.time_series_figure)
        self.time_series_canvas.setMinimumSize(250, 250)
        self.time_series_toolbar = NavigationToolbar(self.time_series_canvas, self)

        # Layout for left plot and toolbar
        self.left_plot_layout = QVBoxLayout()
        self.left_plot_layout.addWidget(self.pandapipes_net_canvas)
        self.left_plot_layout.addWidget(self.pandapipes_net_figure_toolbar)

        # Layout for right plot and toolbar
        self.right_plot_layout = QVBoxLayout()
        self.dropdownLayout = QHBoxLayout()
        self.right_plot_layout.addLayout(self.dropdownLayout)
        self.right_plot_layout.addWidget(self.time_series_canvas)
        self.right_plot_layout.addWidget(self.time_series_toolbar)

        # Add both layouts horizontally
        self.scrollLayout.addLayout(self.left_plot_layout)
        self.scrollLayout.addLayout(self.right_plot_layout)

        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setWidgetResizable(True)

        self.container_layout.addWidget(self.scrollArea)
    
    def createPlotControlDropdown(self):
        """Create dropdown for selecting plot data types."""
        # Remove existing dropdown if present
        if hasattr(self, 'dropdownLayout'):
            # Remove widgets from layout
            while self.dropdownLayout.count():
                item = self.dropdownLayout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)

        self.dataSelectionDropdown = CheckableComboBox(self)

        initial_checked = True

        for label in self.NetworkGenerationData.plot_data.keys():
            self.dataSelectionDropdown.addItem(label)
            item = self.dataSelectionDropdown.model().item(self.dataSelectionDropdown.count() - 1, 0)
            item.setCheckState(Qt.CheckState.Checked if initial_checked else Qt.CheckState.Unchecked)
            initial_checked = False

        self.dropdownLayout.addWidget(self.dataSelectionDropdown)
        self.dataSelectionDropdown.checkedStateChanged.connect(self.update_time_series_plot)
    
    def openNetGenerationDialog(self):
        """Open network generation dialog."""
        try:
            dialog = NetGenerationDialog(
                self.generateNetworkCallback,
                self.base_path,
                self
            )
            dialog.exec()
        except Exception as e:
            logging.error(f"Fehler beim öffnen des Dialogs aufgetreten: {e}")
            QMessageBox.critical(self, "Fehler", f"Fehler beim öffnen des Dialogs aufgetreten: {e}")

    def generateNetworkCallback(self, NetworkGenerationData):
        """
        Handle network generation callback.

        Parameters
        ----------
        NetworkGenerationData : object
            Network generation data.
        """
        self.NetworkGenerationData = NetworkGenerationData

        if self.NetworkGenerationData.import_type == "GeoJSON":
            self.create_and_initialize_net_geojson()

    def opencalculateNetDialog(self):
        """Open time series calculation dialog."""
        dialog = TimeSeriesCalculationDialog(self.base_path, self)
        if dialog.exec():
            netCalcInputs = dialog.getValues()
            self.NetworkGenerationData.start_time_step = netCalcInputs["start"]
            self.NetworkGenerationData.end_time_step = netCalcInputs["end"]
            self.NetworkGenerationData.results_csv_filename = netCalcInputs["results_filename"]
            self.time_series_simulation()
      
    def create_and_initialize_net_geojson(self):
        """Create and initialize network from GeoJSON files."""
        # uses the dataclass to get the values
        # add COP filename
        self.NetworkGenerationData.COP_filename = self.data_manager.get_cop_filename()
        self.NetworkGenerationData.TRY_filename = self.data_manager.get_try_filename()
        
        self.initializationThread = NetInitializationThread(self.NetworkGenerationData)
        self.common_thread_initialization()

    def common_thread_initialization(self):
        """Initialize common thread connections and progress."""
        self.initializationThread.calculation_done.connect(self.on_initialization_done)
        self.initializationThread.calculation_error.connect(self.on_time_series_simulation_error)
        self.initializationThread.start()
        self.progressBar.setRange(0, 0)

    def on_initialization_done(self, NetworkGenerationData):
        """
        Handle initialization completion.

        Parameters
        ----------
        NetworkGenerationData : object
            Network generation data.
        """
        self.progressBar.setRange(0, 1)

        self.NetworkGenerationData = NetworkGenerationData        
        
        self.plot_pandapipes_net()
        self.NetworkGenerationData.prepare_plot_data()
        self.createPlotControlDropdown()
        self.update_time_series_plot()
        self.display_results()

    def display_results(self):
        """Display network simulation results in text area."""
        if not hasattr(self.NetworkGenerationData, 'net'):
            self.result_text = "Netzdaten nicht verfügbar."
            self.results_display.setPlainText(self.result_text)
            return

        results = self.NetworkGenerationData.calculate_results()
        result_text_parts = []
        for key, value in results.items():
            if value is None:
                result_text_parts.append(f"{key}: N/A\n")
            elif isinstance(value, float):
                # Formatierung je nach Einheit
                if "%" in key:
                    result_text_parts.append(f"{key}: {value:.2f} %\n")
                elif "kW" in key or "MWh" in key or "m" in key:
                    result_text_parts.append(f"{key}: {value:.2f}\n")
                else:
                    result_text_parts.append(f"{key}: {value}\n")
            else:
                result_text_parts.append(f"{key}: {value}\n")

        self.result_text = ''.join(result_text_parts)
        self.results_display.setPlainText(self.result_text)

    def plot_pandapipes_net(self):
        """Plot pandapipes network visualization."""
        self.pandapipes_net_figure.clear()
        ax = self.pandapipes_net_figure.add_subplot(111)
        config_plot(self.NetworkGenerationData.net, ax, show_junctions=True, show_pipes=True, show_heat_consumers=True, show_basemap=self.show_map, map_type=self.map_type)
        self.pandapipes_net_canvas.draw()

    def loadMap(self, map_type, action):
        """
        Load background map for network visualization.

        Parameters
        ----------
        map_type : str
            Type of map to load.
        action : QAction
            Action triggering map load.
        """
        if action.isChecked():
            self.show_map = True
            self.map_type = map_type
            for act in action.parent().actions():
                if act != action:
                    act.setChecked(False)
        else:
            self.show_map = False
            self.map_type = None

    def time_series_simulation(self):
        """Perform time series simulation."""
        if self.NetworkGenerationData is None:
            QMessageBox.warning(self, "Keine Netzdaten", "Bitte generieren Sie zuerst ein Netz.")
            return

        try:
            self.calculationThread = NetCalculationThread(self.NetworkGenerationData)
            self.calculationThread.calculation_done.connect(self.on_time_series_simulation_done)
            self.calculationThread.calculation_error.connect(self.on_time_series_simulation_error)
            self.calculationThread.start()
            self.progressBar.setRange(0, 0)

        except ValueError as e:
            QMessageBox.warning("Ungültige Eingabe", str(e))

    def on_time_series_simulation_done(self, NetworkGenerationData):
        """
        Handle time series simulation completion.

        Parameters
        ----------
        NetworkGenerationData : object
            Network generation data with results.
        """
        self.progressBar.setRange(0, 1)
        self.NetworkGenerationData = NetworkGenerationData

        self.NetworkGenerationData.prepare_plot_data()
        self.createPlotControlDropdown()
        self.update_time_series_plot()
        self.display_results()

        save_results_csv(self.NetworkGenerationData.yearly_time_steps[self.NetworkGenerationData.start_time_step:self.NetworkGenerationData.end_time_step], 
                         self.NetworkGenerationData.waerme_ges_kW[self.NetworkGenerationData.start_time_step:self.NetworkGenerationData.end_time_step], 
                         self.NetworkGenerationData.strombedarf_ges_kW[self.NetworkGenerationData.start_time_step:self.NetworkGenerationData.end_time_step], 
                         self.NetworkGenerationData.pump_results, 
                         self.NetworkGenerationData.results_csv_filename)

        print("Simulation erfolgreich abgeschlossen.")

    def on_time_series_simulation_error(self, error_message):
        """
        Handle simulation errors.

        Parameters
        ----------
        error_message : str
            Error message to display.
        """
        QMessageBox.critical(self, "Berechnungsfehler", error_message)
        self.progressBar.setRange(0, 1)

    def update_time_series_plot(self):
        """Update time series plot based on selected data."""
        if not hasattr(self, 'dataSelectionDropdown'):
            self.createPlotControlDropdown()

        self.time_series_figure.clear()
        ax_left = self.time_series_figure.add_subplot(111)
        ax_right = ax_left.twinx()

        left_labels = set()
        right_labels = set()
        color_cycle = itertools.cycle(['b', 'g', 'r', 'c', 'm', 'y', 'k'])

        min_time, max_time = None, None

        for i in range(self.dataSelectionDropdown.model().rowCount()):
            if self.dataSelectionDropdown.itemChecked(i):
                key = self.dataSelectionDropdown.itemText(i)
                data_info = self.NetworkGenerationData.plot_data[key]
                color = next(color_cycle)
                time_steps = data_info.get("time", None)
                if time_steps is None or len(time_steps) != len(data_info["data"]):
                    print(f"Warnung: Zeitachse und Datenlänge passen nicht für {key}")
                    continue
                if data_info["axis"] == "left":
                    ax_left.plot(time_steps, data_info["data"], label=key, color=color)
                    left_labels.add(data_info["label"])
                elif data_info["axis"] == "right":
                    ax_right.plot(time_steps, data_info["data"], label=key, color=color)
                    right_labels.add(data_info["label"])

                tmin, tmax = time_steps[0], time_steps[-1]
                min_time = tmin if min_time is None else max(min_time, tmin)
                max_time = tmax if max_time is None else min(max_time, tmax)

        label_fontsize = 14
        legend_fontsize = 12

        ax_left.set_xlabel("Time", fontsize=label_fontsize)
        ax_left.set_ylabel(", ".join(left_labels), fontsize=label_fontsize)
        ax_right.set_ylabel(", ".join(right_labels), fontsize=label_fontsize)

        ax_left.tick_params(axis='both', labelsize=label_fontsize)
        ax_right.tick_params(axis='both', labelsize=label_fontsize)

        # X-Achse ggf. zoomen
        if min_time is not None and max_time is not None:
            ax_left.set_xlim(min_time, max_time)
            ax_right.set_xlim(min_time, max_time)
        else:
            ax_left.set_xlim(auto=True)
            ax_right.set_xlim(auto=True)

        lines_left, labels_left = ax_left.get_legend_handles_labels()
        lines_right, labels_right = ax_right.get_legend_handles_labels()
        by_label = dict(zip(labels_left + labels_right, lines_left + lines_right))
        ax_left.legend(by_label.values(), by_label.keys(), loc='upper center', fontsize=legend_fontsize)

        ax_left.grid()

        # Prevent x-axis label overlap
        self.time_series_figure.autofmt_xdate(rotation=30)
        self.time_series_figure.tight_layout()
        
        self.time_series_canvas.draw()

    def get_data_path(self):
        """
        Get absolute path to data directory.

        Returns
        -------
        str
            Data directory path.
        """
        # Gehe zwei Ebenen über base_path hinaus, um den Projektpfad zu erhalten
        project_base_path = os.path.dirname(os.path.dirname(self.base_path))

        # Kombiniere den Projektpfad mit dem festen Datenpfad
        return os.path.join(project_base_path, "src", "districtheatingsim", "data")

    def saveNet(self):
        """Save network data to pickle, CSV, and JSON files."""
        if self.NetworkGenerationData:
            try:
                pickle_file_path = os.path.join(self.base_path, self.config_manager.get_relative_path('pp_pickle_file_path'))
                csv_file_path = os.path.join(self.base_path, self.config_manager.get_relative_path('csv_net_init_file_path'))
                json_file_path = os.path.join(self.base_path, self.config_manager.get_relative_path('json_net_init_file_path'))
                
                # Speichere den relativen Pfad für die COP-Datei relativ zum Datenpfad
                data_path = self.get_data_path()  # Hole den Datenpfad
                self.NetworkGenerationData.COP_filename = os.path.relpath(self.NetworkGenerationData.COP_filename, data_path)

                # Speichere die Pandapipes-Netzwerkdaten mit der pandapipes-Funktion, das Netzwerk wird in pickle_file_path gespeichert
                # Das Format kann auch allein mit pandapipes wieder geladen werden
                pp.to_pickle(self.NetworkGenerationData.net, pickle_file_path)
                
                # Hier müsste man nochmal die Formate überarbeiten
                # Die mehrschichtigen Daten für Wärme und Strom werden in einer CSV-Datei gespeichert
                waerme_data = np.column_stack([self.NetworkGenerationData.waerme_hast_ges_W[i] for i in range(self.NetworkGenerationData.waerme_hast_ges_W.shape[0])])
                waerme_df = pd.DataFrame(waerme_data, index=self.NetworkGenerationData.yearly_time_steps, columns=[f'waerme_hast_ges_W_{i+1}' for i in range(self.NetworkGenerationData.waerme_hast_ges_W.shape[0])])

                strom_data = np.column_stack([self.NetworkGenerationData.strombedarf_hast_ges_W[i] for i in range(self.NetworkGenerationData.strombedarf_hast_ges_W.shape[0])])
                strom_df = pd.DataFrame(strom_data, index=self.NetworkGenerationData.yearly_time_steps, columns=[f'strombedarf_hast_ges_W_{i+1}' for i in range(self.NetworkGenerationData.strombedarf_hast_ges_W.shape[0])])

                combined_df = pd.concat([waerme_df, strom_df], axis=1)
                combined_df.to_csv(csv_file_path, sep=';', date_format='%Y-%m-%dT%H:%M:%S')

                # Metadaten/Parameter speichern
                meta_dict = self.NetworkGenerationData.__dict__.copy()
                # Entferne große/unnötige Felder bzw. bereits gespeicherte Daten
                meta_dict.pop('net', None)
                meta_dict.pop('waerme_hast_ges_W', None)
                meta_dict.pop('strombedarf_hast_ges_W', None)
                meta_dict.pop('waerme_hast_ges_kW', None)
                meta_dict.pop('strombedarf_hast_ges_kW', None)
                meta_dict.pop('waerme_ges_kW', None)
                meta_dict.pop('strombedarf_ges_kW', None)
                meta_dict.pop('yearly_time_steps', None)#
                meta_dict.pop('pump_results', None)
                meta_dict.pop('plot_data', None)

                # ggf. weitere Felder entfernen oder anpassen
                with open(json_file_path, 'w') as json_file:
                    json.dump(meta_dict, json_file, indent=4, default=str)
                
                QMessageBox.information(self, "Speichern erfolgreich", f"Pandapipes Netz erfolgreich gespeichert in: {pickle_file_path}, Daten erfolgreich gespeichert in: {csv_file_path} und {json_file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Speichern fehlgeschlagen", f"Fehler beim Speichern der Daten: {e}")
        else:
            QMessageBox.warning(self, "Keine Daten", "Kein Pandapipes-Netzwerk zum Speichern vorhanden.")

    def loadNet(self):
        """Load network data from saved files."""
        try:
            data_path = self.get_data_path()
            pickle_file_path = os.path.join(self.base_path, self.config_manager.get_relative_path('pp_pickle_file_path'))
            csv_file_path = os.path.join(self.base_path, self.config_manager.get_relative_path('csv_net_init_file_path'))
            json_file_path = os.path.join(self.base_path, self.config_manager.get_relative_path('json_net_init_file_path'))

            # Lade die Pandapipes-Netzwerkdaten
            net = pp.from_pickle(pickle_file_path)
            
            with open(csv_file_path, newline='') as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                headers = next(reader)
                num_waerme_cols = len([h for h in headers if h.startswith('waerme_hast_ges_W')])
                num_strom_cols = len([h for h in headers if h.startswith('strombedarf_hast_ges_W')])

                formatted_time_steps = []
                waerme_hast_ges_W_data = []
                strombedarf_hast_ges_W_data = []
                
                for row in reader:
                    formatted_time_steps.append(np.datetime64(row[0]))
                    waerme_hast_ges_W_data.append([float(value) for value in row[1:num_waerme_cols + 1]])
                    strombedarf_hast_ges_W_data.append([float(value) for value in row[num_waerme_cols + 1:num_waerme_cols + num_strom_cols + 1]])
                
                yearly_time_steps = np.array(formatted_time_steps)
                waerme_hast_ges_W = np.array(waerme_hast_ges_W_data).transpose()
                strombedarf_hast_ges_W = np.array(strombedarf_hast_ges_W_data).transpose()

            # Metadaten/Parameter laden
            with open(json_file_path, 'r') as json_file:
                meta_dict = json.load(json_file)

            # DataClass rekonstruieren
            self.NetworkGenerationData = NetworkGenerationData(**meta_dict)
            self.NetworkGenerationData.COP_filename = os.path.join(data_path, self.NetworkGenerationData.COP_filename)
            self.NetworkGenerationData.net = net
            self.NetworkGenerationData.waerme_hast_ges_W = waerme_hast_ges_W
            self.NetworkGenerationData.strombedarf_hast_ges_W = strombedarf_hast_ges_W
            self.NetworkGenerationData.yearly_time_steps = yearly_time_steps

            self.NetworkGenerationData.waerme_hast_ges_kW = np.where(self.NetworkGenerationData.waerme_hast_ges_W == 0, 0, self.NetworkGenerationData.waerme_hast_ges_W / 1000)
            self.NetworkGenerationData.strombedarf_hast_ges_kW = np.where(self.NetworkGenerationData.strombedarf_hast_ges_W == 0, 0, self.NetworkGenerationData.strombedarf_hast_ges_W / 1000)
            
            self.NetworkGenerationData.waerme_ges_kW = np.sum(self.NetworkGenerationData.waerme_hast_ges_kW, axis=0)
            self.NetworkGenerationData.strombedarf_ges_kW = np.sum(self.NetworkGenerationData.strombedarf_hast_ges_kW, axis=0)
            
            self.plot_pandapipes_net()
            self.NetworkGenerationData.prepare_plot_data()
            self.createPlotControlDropdown()
            self.update_time_series_plot()
            self.display_results()

            QMessageBox.information(self, "Laden erfolgreich", "Daten erfolgreich geladen aus: {}, {} und {}.".format(csv_file_path, pickle_file_path, json_file_path))
        except Exception as e:
            tb = traceback.format_exc()
            QMessageBox.critical(self, "Laden fehlgeschlagen", f"Fehler beim Laden der Daten: {e}\n\n{tb}")

    def load_net_results(self):
        """Load network simulation results from CSV file."""
        if self.NetworkGenerationData:
            results_csv_filepath = os.path.join(self.base_path, self.config_manager.get_relative_path('load_profile_path'))
            
            _, self.NetworkGenerationData.waerme_ges_kW, self.NetworkGenerationData.strombedarf_ges_kW, self.NetworkGenerationData.pump_results = import_results_csv(results_csv_filepath)
            
            self.NetworkGenerationData.prepare_plot_data()
            self.createPlotControlDropdown()
            self.update_time_series_plot()
            self.display_results()

        else:
            QMessageBox.warning(self, "Keine Daten", "Kein Pandapipes-Netzwerk zum Laden vorhanden.")
    
    def exportNetGeoJSON(self):
        """Export network to GeoJSON format."""
        geoJSON_filepath = os.path.join(self.base_path, self.config_manager.get_relative_path('dimensioned_net_path'))
        if self.NetworkGenerationData:   
            try:
                export_net_geojson(self.NetworkGenerationData.net, geoJSON_filepath)
                
                QMessageBox.information(self, "Speichern erfolgreich", f"Pandapipes Wärmenetz erfolgreich als geoJSON gespeichert in: {geoJSON_filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Speichern fehlgeschlagen", f"Fehler beim Speichern der Daten: {e}")