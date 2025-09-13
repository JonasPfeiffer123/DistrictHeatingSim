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
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QMessageBox, 
                            QProgressBar, QMenuBar, QPlainTextEdit, QLabel, QFrame, QGridLayout)
from PyQt6.QtGui import QAction, QActionGroup, QFont

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
        self.setLayout(self.main_layout)

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
        """Setup layout with network plot and info on top, time series full width below."""
        self.scrollArea = QScrollArea(self)
        self.scrollWidget = QWidget()
        
        # Main vertical layout for all content
        self.main_vertical_layout = QVBoxLayout(self.scrollWidget)
        
        # Top section: Network plot (left) + Network info (right)
        self.top_horizontal_layout = QHBoxLayout()
        
        # Left: Network plot container
        self.network_plot_container = QWidget()
        self.network_plot_layout = QVBoxLayout(self.network_plot_container)
        
        # Network plot
        self.pandapipes_net_figure = Figure()
        self.pandapipes_net_canvas = FigureCanvas(self.pandapipes_net_figure)
        self.pandapipes_net_canvas.setMinimumSize(500, 500)  # Erhöht von 350 auf 450
        self.pandapipes_net_figure_toolbar = NavigationToolbar(self.pandapipes_net_canvas, self)
        
        self.network_plot_layout.addWidget(self.pandapipes_net_canvas)
        self.network_plot_layout.addWidget(self.pandapipes_net_figure_toolbar)
        
        # Right: Network information panel with height matching network plot + toolbar
        self.info_container = QWidget()
        self.info_container.setMinimumHeight(540)  # Match network plot (500) + toolbar (~40)
        self.info_container.setMaximumHeight(540)  # Fixed height for alignment
        self.info_layout = QVBoxLayout(self.info_container)
        self.info_layout.setContentsMargins(5, 5, 5, 5)
        
        # Compact title for info section
        self.info_title = QLabel("📊 Netzwerk-Informationen")
        self.info_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.info_title.setFixedHeight(35)  # Fixed title height
        self.info_title.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 6px;
                background-color: #ecf0f1;
                border-radius: 3px;
                border-left: 3px solid #3498db;
            }
        """)
        self.info_layout.addWidget(self.info_title)
        
        # Scrollable area for info cards with fixed dimensions
        self.info_scroll = QScrollArea()
        self.info_scroll.setWidgetResizable(True)
        self.info_scroll.setMinimumHeight(475)  # Remaining height: 540 - 35 (title) - 25 (progress) - 5 (spacing)
        self.info_scroll.setMaximumHeight(475)  # Fixed scrollable area height
        self.info_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.info_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.info_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # Container for info cards - more compact
        self.info_cards_widget = QWidget()
        self.info_cards_layout = QVBoxLayout(self.info_cards_widget)
        self.info_cards_layout.setSpacing(2)  # Reduced spacing
        self.info_cards_layout.setContentsMargins(2, 2, 2, 2)  # Reduced margins
        
        self.info_scroll.setWidget(self.info_cards_widget)
        self.info_layout.addWidget(self.info_scroll)
        
        # Progress bar in info panel with modern styling and fixed height
        self.progressBar = QProgressBar(self)
        self.progressBar.setFixedHeight(25)  # Fixed progress bar height
        self.progressBar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
                background-color: #ecf0f1;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        self.info_layout.addWidget(self.progressBar)
        
        # No stretch needed since we have fixed heights
        
        # Add network plot and info to top horizontal layout
        self.top_horizontal_layout.addWidget(self.network_plot_container, 7)  # 70% width
        self.top_horizontal_layout.addWidget(self.info_container, 3)          # 30% width
        
        # Bottom section: Time series plot (full width)
        self.time_series_container = QWidget()
        self.time_series_layout = QVBoxLayout(self.time_series_container)
        
        # Dropdown for time series controls
        self.dropdownLayout = QHBoxLayout()
        self.time_series_layout.addLayout(self.dropdownLayout)
        
        # Time series plot
        self.time_series_figure = Figure()
        self.time_series_canvas = FigureCanvas(self.time_series_figure)
        self.time_series_canvas.setMinimumSize(800, 500)  # Erhöht von 400 auf 500
        self.time_series_toolbar = NavigationToolbar(self.time_series_canvas, self)
        
        self.time_series_layout.addWidget(self.time_series_canvas)
        self.time_series_layout.addWidget(self.time_series_toolbar)
        
        # Add both sections to main vertical layout
        self.main_vertical_layout.addLayout(self.top_horizontal_layout)
        self.main_vertical_layout.addWidget(self.time_series_container)
        
        # Setup scroll area
        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
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
        
        # Trigger initial plot update to ensure correct rendering
        QTimer.singleShot(100, self.update_time_series_plot)
    
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

    def create_info_card(self, title, value, unit="", description=""):
        """Create a compact info card for displaying network data."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin: 1px;
            }
            QFrame:hover {
                border-color: #3498db;
                background-color: #f8f9fa;
            }
        """)
        card.setFrameStyle(QFrame.Shape.Box)
        
        # Use horizontal layout for compact display
        layout = QHBoxLayout(card)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Title (left side)
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label, 2)  # 2/3 of space
        
        # Value (right side)
        if isinstance(value, float):
            if "%" in title:
                value_text = f"{value:.1f}%"
            elif any(x in title for x in ["kW", "MWh", "m"]):
                value_text = f"{value:.1f}"
            else:
                value_text = f"{value:.1f}"
        else:
            value_text = str(value)
            
        value_label = QLabel(value_text)
        value_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        value_label.setStyleSheet("color: #27ae60;")
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(value_label, 1)  # 1/3 of space
        
        return card

    def display_results(self):
        """Display network simulation results in compact card layout."""
        # Clear existing cards
        while self.info_cards_layout.count():
            child = self.info_cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not hasattr(self.NetworkGenerationData, 'net'):
            # Compact no data message
            no_data_label = QLabel("⚠️ Keine Netzdaten verfügbar")
            no_data_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            no_data_label.setStyleSheet("""
                QLabel {
                    color: #e74c3c;
                    background-color: #ffebee;
                    border: 1px solid #ef5350;
                    border-radius: 4px;
                    padding: 8px;
                }
            """)
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.info_cards_layout.addWidget(no_data_label)
            return

        results = self.NetworkGenerationData.calculate_results()
        
        # Compact display - show most important results first
        important_keys = [
            "Anzahl angeschlossene Gebäude",
            "Anzahl Heizzentralen", 
            "Jahresgesamtwärmebedarf Gebäude [MWh/a]",
            "max. Heizlast Gebäude [kW]",
            "Trassenlänge Wärmenetz [m]",
            "Wärmebedarfsdichte [MWh/(a*m)]",
            "Anschlussdichte [kW/m]",
            "Jahreswärmeerzeugung [MWh]",
            "Pumpenstrom [MWh]",
            "Verteilverluste [MWh]",
            "rel. Verteilverluste [%]"
        ]
        
        # Show important results first
        for key in important_keys:
            if key in results and results[key] is not None:
                card = self.create_info_card(key, results[key])
                self.info_cards_layout.addWidget(card)
        
        # Show remaining results
        for key, value in results.items():
            if key not in important_keys and value is not None:
                card = self.create_info_card(key, value)
                self.info_cards_layout.addWidget(card)
        
        # Compact stretch
        self.info_cards_layout.addStretch()

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
        """Update time series plot based on selected data with modern styling."""
        if not hasattr(self, 'dataSelectionDropdown'):
            self.createPlotControlDropdown()

        # Apply modern theme
        plt.style.use('seaborn-v0_8-darkgrid')

        self.time_series_figure.clear()
        
        # Create grid layout with more space for long variable names
        gs = gridspec.GridSpec(1, 3, width_ratios=[0.25, 0.50, 0.25], figure=self.time_series_figure)
        ax_legend_left = self.time_series_figure.add_subplot(gs[0, 0])
        ax_main = self.time_series_figure.add_subplot(gs[0, 1])
        ax_legend_right = self.time_series_figure.add_subplot(gs[0, 2])
        ax_right = ax_main.twinx()

        # Modern styling parameters
        label_fontsize = 16
        legend_fontsize = 12
        line_width = 2

        # Color palettes
        left_color_map = plt.get_cmap('tab10')
        right_color_map = plt.get_cmap('Set2')
        
        left_color_idx = 0
        right_color_idx = 0
        
        lines_left = []
        labels_left = []
        lines_right = []
        labels_right = []
        
        left_y_labels = set()
        right_y_labels = set()

        min_time, max_time = None, None

        # Plot selected data
        for i in range(self.dataSelectionDropdown.model().rowCount()):
            if self.dataSelectionDropdown.itemChecked(i):
                key = self.dataSelectionDropdown.itemText(i)
                data_info = self.NetworkGenerationData.plot_data[key]
                
                time_steps = data_info.get("time", None)
                if time_steps is None or len(time_steps) != len(data_info["data"]):
                    print(f"Warnung: Zeitachse und Datenlänge passen nicht für {key}")
                    continue
                
                # Convert datetime to hours of year (0-8760) if needed
                try:
                    if hasattr(time_steps, '__iter__') and len(time_steps) > 0:
                        # Check if first element is datetime-like
                        first_element = time_steps[0] if hasattr(time_steps, '__getitem__') else next(iter(time_steps))
                        if hasattr(first_element, 'timetuple') or str(type(first_element)).find('datetime') != -1:
                            # Convert datetime to hour of year
                            if hasattr(first_element, 'year'):
                                start_of_year = pd.Timestamp(first_element.year, 1, 1)
                                hours_of_year = [(pd.Timestamp(t) - start_of_year).total_seconds() / 3600 for t in time_steps]
                            else:
                                # Fallback: assume sequential hours
                                hours_of_year = list(range(len(time_steps)))
                        else:
                            # Already numeric, use as is
                            hours_of_year = list(time_steps)
                    else:
                        # Fallback for empty or problematic time_steps
                        hours_of_year = list(range(len(data_info["data"])))
                except Exception as e:
                    print(f"Fehler bei Zeitkonvertierung für {key}: {e}")
                    # Fallback: use index as hours
                    hours_of_year = list(range(len(data_info["data"])))
                
                if data_info["axis"] == "left":
                    color = left_color_map(left_color_idx % 10)
                    line, = ax_main.plot(hours_of_year, data_info["data"], label=key, 
                                       color=color, linewidth=line_width)
                    lines_left.append(line)
                    labels_left.append(key)
                    left_y_labels.add(data_info["label"])
                    left_color_idx += 1
                elif data_info["axis"] == "right":
                    color = right_color_map(right_color_idx % 8)
                    line, = ax_right.plot(hours_of_year, data_info["data"], label=key, 
                                        color=color, linewidth=line_width, linestyle='--')
                    lines_right.append(line)
                    labels_right.append(key)
                    right_y_labels.add(data_info["label"])
                    right_color_idx += 1

                # Update time range with safe numeric conversion
                try:
                    tmin, tmax = float(hours_of_year[0]), float(hours_of_year[-1])
                    min_time = tmin if min_time is None else min(min_time, tmin)
                    max_time = tmax if max_time is None else max(max_time, tmax)
                except (ValueError, TypeError):
                    print(f"Fehler bei Zeitbereichsberechnung für {key}")
                    continue

        # Axis styling with line breaks for long labels
        ax_main.set_xlabel("Jahresstunden [h]", fontsize=label_fontsize)
        
        # Format Y-axis labels with line breaks for long text
        left_ylabel = ", ".join(left_y_labels) if left_y_labels else ""
        right_ylabel = ", ".join(right_y_labels) if right_y_labels else ""
        
        # Add line breaks for long labels (every ~40 characters)
        if len(left_ylabel) > 40:
            words = left_ylabel.split(", ")
            lines = []
            current_line = ""
            for word in words:
                if len(current_line + ", " + word) > 40 and current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    if current_line:
                        current_line += ", " + word
                    else:
                        current_line = word
            if current_line:
                lines.append(current_line)
            left_ylabel = "\n".join(lines)
            
        if len(right_ylabel) > 40:
            words = right_ylabel.split(", ")
            lines = []
            current_line = ""
            for word in words:
                if len(current_line + ", " + word) > 40 and current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    if current_line:
                        current_line += ", " + word
                    else:
                        current_line = word
            if current_line:
                lines.append(current_line)
            right_ylabel = "\n".join(lines)
        
        ax_main.set_ylabel(left_ylabel, fontsize=label_fontsize-1)
        ax_right.set_ylabel(right_ylabel, fontsize=label_fontsize-1)

        ax_main.tick_params(axis='both', labelsize=14)
        ax_right.tick_params(axis='y', labelsize=14)

        # Set time range
        if min_time is not None and max_time is not None:
            ax_main.set_xlim(min_time, max_time)
            ax_right.set_xlim(min_time, max_time)

        # Add some common hour markers for better orientation with larger steps
        if max_time is not None and isinstance(max_time, (int, float)):
            try:
                max_time_int = int(max_time)
                if max_time_int > 8760:  # More than one year
                    ax_main.set_xticks(range(0, max_time_int, 2000))  # Every ~2000 hours
                elif max_time_int > 4000:  # More than half year
                    ax_main.set_xticks(range(0, max_time_int, 1000))  # Every 1000 hours
                elif max_time_int > 2000:  # More than ~3 months
                    ax_main.set_xticks(range(0, max_time_int, 500))   # Every 500 hours
                else:
                    ax_main.set_xticks(range(0, max_time_int, 500))   # Every 500 hours for smaller ranges
            except (ValueError, TypeError):
                # Fallback: let matplotlib handle ticks automatically
                pass

        # Setup legend areas
        ax_legend_left.axis('off')
        ax_legend_right.axis('off')

        # Helper function for legend columns with better spacing for long names
        def get_ncol(n):
            if n <= 10:  # Reduced from 15 for long variable names
                return 1
            else:
                return 2

        # Add legends to side panels with optimized settings for long names
        if lines_left:
            ncol_left = get_ncol(len(lines_left))
            legend_left = ax_legend_left.legend(lines_left, labels_left, loc='upper left', 
                                              fontsize=legend_fontsize-2, frameon=False, ncol=ncol_left,
                                              columnspacing=0.2, handletextpad=0.3, handlelength=1.0)
        if lines_right:
            ncol_right = get_ncol(len(lines_right))
            legend_right = ax_legend_right.legend(lines_right, labels_right, loc='upper right', 
                                                fontsize=legend_fontsize-2, frameon=False, ncol=ncol_right,
                                                columnspacing=0.2, handletextpad=0.3, handlelength=1.0)

        # Title and grid
        self.time_series_figure.suptitle('Zeitreihen-Simulation Wärmenetz', fontsize=18)
        ax_main.grid(True, alpha=0.3)

        # Remove the date formatting since we're now using hours
        # self.time_series_figure.autofmt_xdate(rotation=30)  # Removed
        
        # Use subplots_adjust instead of tight_layout to avoid warnings
        self.time_series_figure.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.1, wspace=0.1)
        
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

    def saveNet(self, show_dialog=True):
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
                
                if show_dialog:
                    QMessageBox.information(self, "Speichern erfolgreich", f"Pandapipes Netz erfolgreich gespeichert in: {pickle_file_path}, Daten erfolgreich gespeichert in: {csv_file_path} und {json_file_path}")
            except Exception as e:
                if show_dialog:
                    QMessageBox.critical(self, "Speichern fehlgeschlagen", f"Fehler beim Speichern der Daten: {e}")
        else:
            if show_dialog:
                QMessageBox.warning(self, "Keine Daten", "Kein Pandapipes-Netzwerk zum Speichern vorhanden.")

    def loadNet(self, show_dialog=True):
        """Load network data from saved files.
        
        Parameters
        ----------
        show_dialog : bool, optional
            Whether to show success/error dialogs. Default is True.
        """
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

            if show_dialog:
                QMessageBox.information(self, "Laden erfolgreich", "Daten erfolgreich geladen aus: {}, {} und {}.".format(csv_file_path, pickle_file_path, json_file_path))
        except Exception as e:
            tb = traceback.format_exc()
            if show_dialog:
                QMessageBox.critical(self, "Laden fehlgeschlagen", f"Fehler beim Laden der Daten: {e}\n\n{tb}")
            else:
                logging.error(f"Fehler beim Laden der Netzwerk-Daten: {e}\n{tb}")

    def load_net_results(self, show_dialog=True):
        """Load network simulation results from CSV file.
        
        Parameters
        ----------
        show_dialog : bool, optional
            Whether to show warning dialogs. Default is True.
        """
        if self.NetworkGenerationData:
            results_csv_filepath = os.path.join(self.base_path, self.config_manager.get_relative_path('load_profile_path'))
            
            _, self.NetworkGenerationData.waerme_ges_kW, self.NetworkGenerationData.strombedarf_ges_kW, self.NetworkGenerationData.pump_results = import_results_csv(results_csv_filepath)
            
            self.NetworkGenerationData.prepare_plot_data()
            self.createPlotControlDropdown()
            self.update_time_series_plot()
            self.display_results()

        elif show_dialog:
            QMessageBox.warning(self, "Keine Daten", "Kein Pandapipes-Netzwerk zum Laden vorhanden.")
    
    def exportNetGeoJSON(self, show_dialog=True):
        """Export network to GeoJSON format."""
        geoJSON_filepath = os.path.join(self.base_path, self.config_manager.get_relative_path('dimensioned_net_path'))
        if self.NetworkGenerationData:   
            try:
                export_net_geojson(self.NetworkGenerationData.net, geoJSON_filepath)
                
                if show_dialog:
                    QMessageBox.information(self, "Speichern erfolgreich", f"Pandapipes Wärmenetz erfolgreich als geoJSON gespeichert in: {geoJSON_filepath}")
            except Exception as e:
                if show_dialog:
                    QMessageBox.critical(self, "Speichern fehlgeschlagen", f"Fehler beim Speichern der Daten: {e}")