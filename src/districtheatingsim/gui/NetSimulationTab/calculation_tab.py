"""
Network Simulation Tab Module
=============================

District heating network simulation and calculation interface with pandapipes integration.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
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

from shapely.geometry import LineString

# Plotly imports for interactive network visualization
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False
    logging.warning("PyQt6.QtWebEngineWidgets not available. Interactive plot will use HTML export.")

from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QUrl
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QMessageBox, 
                            QProgressBar, QMenuBar, QPlainTextEdit, QLabel, QFrame, QGridLayout,
                            QApplication, QTableWidget, QTableWidgetItem, QAbstractItemView, QPushButton, QComboBox, QHeaderView)
from PyQt6.QtGui import QAction, QActionGroup, QFont

from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import save_results_csv, import_results_csv
from districtheatingsim.net_simulation_pandapipes.interactive_network_plot import InteractiveNetworkPlot
from districtheatingsim.net_simulation_pandapipes.utilities import export_net_geojson

from districtheatingsim.gui.NetSimulationTab.timeseries_dialog import TimeSeriesCalculationDialog
from districtheatingsim.gui.NetSimulationTab.net_generation_dialog import NetGenerationDialog
from districtheatingsim.gui.NetSimulationTab.net_calculation_threads import NetInitializationThread, NetCalculationThread
from districtheatingsim.net_simulation_pandapipes.NetworkDataClass import NetworkGenerationData

from districtheatingsim.gui.utilities import CheckableComboBox
from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema

import geopandas as gpd

class CalculationTab(QWidget):
    """
    Network simulation tab for district heating system calculations.

    .. note::
       Provides interface for network generation, time series simulation, and visualization of heating network data using pandapipes.
    """

    data_added = pyqtSignal(object)

    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        """
        Initialize calculation tab.

        :param folder_manager: Project folder manager.
        :type folder_manager: object
        :param data_manager: Application data manager.
        :type data_manager: object
        :param config_manager: Configuration manager.
        :type config_manager: object
        :param parent: Parent widget.
        :type parent: QWidget
        """
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.folder_manager.variant_folder)

        # Initialize cache for HTML plot
        self._plot_html_path = None
        
        # Timer for polling plot clicks
        self._plot_click_timer = QTimer()
        self._plot_click_timer.timeout.connect(self._check_plot_click)
        self._plot_click_timer.setInterval(200)  # Check every 200ms
        self._last_selected_pipe = None

        self.initUI()

        self.NetworkGenerationData = None

    def updateDefaultPath(self, new_base_path):
        """
        Update project base path.

        :param new_base_path: New base path.
        :type new_base_path: str
        """
        self.base_path = new_base_path

    def initUI(self):
        """
        Initialize user interface components.
        """
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
        """
        Initialize menu bar with file and calculation actions.
        """
        self.menubar = QMenuBar(self)
        self.menubar.setFixedHeight(30)

        fileMenu = self.menubar.addMenu('Datei')
        networkMenu = self.menubar.addMenu('Wärmenetz generieren')
        calcMenu = self.menubar.addMenu('Zeitreihenberechnung durchführen')

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

        self.container_layout.addWidget(self.menubar)

        generateNetAction.triggered.connect(self.openNetGenerationDialog)
        saveppnetAction.triggered.connect(self.saveNet)
        loadppnetAction.triggered.connect(self.loadNet)
        loadresultsppAction.triggered.connect(self.load_net_results)
        exportppnetGeoJSONAction.triggered.connect(self.exportNetGeoJSON)
        calculateNetAction.triggered.connect(self.opencalculateNetDialog)

    def setupPlotLayout(self):
        """
        Setup layout with network plot and info on top, time series full width below.
        """
        self.scrollArea = QScrollArea(self)
        self.scrollWidget = QWidget()
        
        # Main vertical layout for all content
        self.main_vertical_layout = QVBoxLayout(self.scrollWidget)
        
        # Top section: Network plot (left) + Network info (right)
        self.top_horizontal_layout = QHBoxLayout()
        
        # Left: Network plot container
        self.network_plot_container = QWidget()
        self.network_plot_layout = QVBoxLayout(self.network_plot_container)
        self.network_plot_layout.setSpacing(5)
        self.network_plot_layout.setContentsMargins(0, 0, 0, 0)
        
        # Parameter selection dropdown - native PyQt6 control
        from PyQt6.QtWidgets import QComboBox
        self.network_param_dropdown = QComboBox()
        self.network_param_dropdown.setFixedHeight(35)
        self.network_param_dropdown.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 2px solid #3498db;
                border-radius: 5px;
                background-color: white;
                font-size: 12px;
            }
            QComboBox:hover {
                border-color: #2980b9;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
        """)
        self.network_param_dropdown.addItem("Standard (ohne Parameter)", userData=None)
        self.network_param_dropdown.currentIndexChanged.connect(self._on_network_param_changed)
        self.network_plot_layout.addWidget(self.network_param_dropdown)
        
        # Network plot - Interactive Plotly visualization
        if WEBENGINE_AVAILABLE:
            self.pandapipes_net_canvas = QWebEngineView()
            self.pandapipes_net_canvas.setMinimumSize(500, 500)
            
            # Configure WebEngine settings to allow local resources
            from PyQt6.QtWebEngineCore import QWebEngineSettings
            settings = self.pandapipes_net_canvas.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        else:
            # Fallback to label with message
            self.pandapipes_net_canvas = QLabel("Interactive plot requires PyQt6-WebEngine")
            self.pandapipes_net_canvas.setMinimumSize(500, 500)
            self.pandapipes_net_canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.network_plot_layout.addWidget(self.pandapipes_net_canvas)
        
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
        
        # Middle section: Pipe configuration table (full width)
        self.pipe_table_container = QWidget()
        self.pipe_table_layout = QVBoxLayout(self.pipe_table_container)
        self.pipe_table_layout.setContentsMargins(5, 10, 5, 10)
        
        # Title for pipe table
        pipe_table_title = QLabel("🔧 Rohrleitungs-Konfiguration")
        pipe_table_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        pipe_table_title.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 6px;
                background-color: #ecf0f1;
                border-radius: 3px;
                border-left: 3px solid #e74c3c;
            }
        """)
        self.pipe_table_layout.addWidget(pipe_table_title)
        
        # Pipe table
        self.pipe_table = QTableWidget()
        self.pipe_table.setMinimumHeight(400)
        self.pipe_table.setMaximumHeight(600)
        self.pipe_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.pipe_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.pipe_table.setAlternatingRowColors(True)
        self.pipe_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                alternate-background-color: #f9f9f9;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 6px;
                font-weight: bold;
                border: 1px solid #2c3e50;
            }
        """)
        self.pipe_table.itemSelectionChanged.connect(self.on_pipe_selected_in_table)
        self.pipe_table.itemChanged.connect(self.on_table_item_changed)
        self.pipe_table_layout.addWidget(self.pipe_table)
        
        # Button row for pipe table
        pipe_button_layout = QHBoxLayout()
        
        self.restore_pipes_button = QPushButton("Standardwerte wiederherstellen")
        self.restore_pipes_button.clicked.connect(self.restore_pipe_defaults)
        pipe_button_layout.addWidget(self.restore_pipes_button)
        
        pipe_button_layout.addStretch()
        
        self.recalculate_button = QPushButton("Netz neu berechnen")
        self.recalculate_button.clicked.connect(self.recalculateNetwork)
        self.recalculate_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        pipe_button_layout.addWidget(self.recalculate_button)
        
        self.pipe_table_layout.addLayout(pipe_button_layout)
        
        # Hide pipe table initially (shown when network is loaded)
        self.pipe_table_container.hide()
        
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
        self.main_vertical_layout.addWidget(self.pipe_table_container)
        self.main_vertical_layout.addWidget(self.time_series_container)
        
        # Setup scroll area
        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.container_layout.addWidget(self.scrollArea)
    
    def createPlotControlDropdown(self):
        """
        Create dropdown for selecting plot data types.
        """
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
        """
        Open network generation dialog.
        """
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

        :param NetworkGenerationData: Network generation data.
        :type NetworkGenerationData: object
        """
        self.NetworkGenerationData = NetworkGenerationData

        if self.NetworkGenerationData.import_type == "GeoJSON":
            self.create_and_initialize_net_geojson()

    def opencalculateNetDialog(self):
        """
        Open time series calculation dialog.
        """
        dialog = TimeSeriesCalculationDialog(self.base_path, self)
        if dialog.exec():
            netCalcInputs = dialog.getValues()
            self.NetworkGenerationData.start_time_step = netCalcInputs["start"]
            self.NetworkGenerationData.end_time_step = netCalcInputs["end"]
            self.NetworkGenerationData.results_csv_filename = netCalcInputs["results_filename"]
            self.NetworkGenerationData.simplified_calculation = netCalcInputs["simplified"]
            self.time_series_simulation()
      
    def create_and_initialize_net_geojson(self):
        """
        Create and initialize network from GeoJSON files.
        """
        # uses the dataclass to get the values
        # add COP filename
        self.NetworkGenerationData.COP_filename = self.data_manager.get_cop_filename()
        self.NetworkGenerationData.TRY_filename = self.data_manager.get_try_filename()
        
        self.initializationThread = NetInitializationThread(self.NetworkGenerationData)
        self.common_thread_initialization()

    def common_thread_initialization(self):
        """
        Initialize common thread connections and progress.
        """
        self.initializationThread.calculation_done.connect(self.on_initialization_done)
        self.initializationThread.calculation_error.connect(self.on_time_series_simulation_error)
        self.initializationThread.start()
        self.progressBar.setRange(0, 0)

    def on_initialization_done(self, NetworkGenerationData):
        """
        Handle initialization completion.

        :param NetworkGenerationData: Network generation data.
        :type NetworkGenerationData: object
        """
        self.progressBar.setRange(0, 1)

        self.NetworkGenerationData = NetworkGenerationData
        
        # Store original pipe DataFrame for restore functionality
        if hasattr(self.NetworkGenerationData, 'net'):
            self._original_pipe_df = self.NetworkGenerationData.net.pipe.copy()
        
        # Invalidate plot cache to regenerate with new data
        self._invalidate_plot_cache()
        
        # Populate parameter dropdown with available parameters
        self._populate_network_param_dropdown()
        
        # Generate initial plot
        self.plot_pandapipes_net()
        
        # Populate pipe configuration table
        self.populate_pipe_table()
        
        self.NetworkGenerationData.prepare_plot_data()
        self.createPlotControlDropdown()
        self.update_time_series_plot()
        self.display_results()

    def create_info_card(self, title, value, unit="", description=""):
        """
        Create a compact info card for displaying network data.

        :param title: Card title.
        :type title: str
        :param value: Display value.
        :type value: float or str
        :param unit: Unit string.
        :type unit: str
        :param description: Description text.
        :type description: str
        :return: Info card widget.
        :rtype: QFrame
        """
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
        """
        Display network simulation results in compact card layout.
        """
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

    def _invalidate_plot_cache(self):
        """
        Invalidate and clean up old plot cache.
        """
        if self._plot_html_path and os.path.exists(self._plot_html_path):
            try:
                os.remove(self._plot_html_path)
            except Exception as e:
                logging.warning(f"Could not remove old plot file: {e}")
        self._plot_html_path = None
    
    def _populate_network_param_dropdown(self):
        """
        Populate dropdown with available network parameters.
        """
        if not hasattr(self.NetworkGenerationData, 'net'):
            logging.warning("Cannot populate dropdown: NetworkGenerationData.net not found")
            return
        
        logging.info("Populating network parameter dropdown...")
        
        # Clear existing items (keep first "Standard" item)
        self.network_param_dropdown.blockSignals(True)
        self.network_param_dropdown.clear()
        self.network_param_dropdown.addItem("Standard (ohne Parameter)", userData=None)
        
        try:
            # Get available parameters from network
            from districtheatingsim.net_simulation_pandapipes.interactive_network_plot import InteractiveNetworkPlot
            plotter = InteractiveNetworkPlot(self.NetworkGenerationData.net)
            available_params = plotter._get_available_parameters()
            
            logging.info(f"Available parameters: {available_params}")
            
            # Add junction parameters
            if 'junction' in available_params and available_params['junction']:
                for param in available_params['junction']:
                    label = f"Junction: {plotter._get_parameter_label(param)}"
                    self.network_param_dropdown.addItem(label, userData={'component': 'junction', 'parameter': param})
                    logging.debug(f"Added junction parameter: {label}")
            
            # Add pipe parameters
            if 'pipe' in available_params and available_params['pipe']:
                for param in available_params['pipe']:
                    label = f"Pipe: {plotter._get_parameter_label(param)}"
                    self.network_param_dropdown.addItem(label, userData={'component': 'pipe', 'parameter': param})
                    logging.debug(f"Added pipe parameter: {label}")
            
            # Add heat consumer parameters
            if 'heat_consumer' in available_params and available_params['heat_consumer']:
                for param in available_params['heat_consumer']:
                    label = f"Heat Consumer: {plotter._get_parameter_label(param)}"
                    self.network_param_dropdown.addItem(label, userData={'component': 'heat_consumer', 'parameter': param})
                    logging.debug(f"Added heat consumer parameter: {label}")
            
            # Add pump parameters
            if 'pump' in available_params and available_params['pump']:
                for param in available_params['pump']:
                    label = f"Pump: {plotter._get_parameter_label(param)}"
                    self.network_param_dropdown.addItem(label, userData={'component': 'pump', 'parameter': param})
                    logging.debug(f"Added pump parameter: {label}")
            
            # Add flow control parameters
            if 'flow_control' in available_params and available_params['flow_control']:
                for param in available_params['flow_control']:
                    label = f"Flow Control: {plotter._get_parameter_label(param)}"
                    self.network_param_dropdown.addItem(label, userData={'component': 'flow_control', 'parameter': param})
                    logging.debug(f"Added flow control parameter: {label}")
            
            logging.info(f"Dropdown populated with {self.network_param_dropdown.count()} options")
            
        except Exception as e:
            logging.error(f"Error populating dropdown: {e}")
            import traceback
            logging.error(traceback.format_exc())
        finally:
            self.network_param_dropdown.blockSignals(False)
    
    def _on_network_param_changed(self, index):
        """
        Handle network parameter selection change.

        :param index: Dropdown index.
        :type index: int
        """
        # Invalidate cache to force regeneration with new parameter
        self._invalidate_plot_cache()
        # Regenerate plot with selected parameter
        self.plot_pandapipes_net(force_refresh=True)

    def plot_pandapipes_net(self, force_refresh: bool = False):
        """
        Plot pandapipes network visualization using interactive Plotly.

        :param force_refresh: If True, regenerate the plot even if cached version exists.
        :type force_refresh: bool
        """
        if not hasattr(self.NetworkGenerationData, 'net'):
            return
        
        try:
            # Use cached HTML if available and not forcing refresh
            if not force_refresh and self._plot_html_path and os.path.exists(self._plot_html_path):
                if WEBENGINE_AVAILABLE:
                    self.pandapipes_net_canvas.setUrl(QUrl.fromLocalFile(self._plot_html_path))
                return
            
            # Get selected parameter from dropdown
            selected_data = self.network_param_dropdown.currentData()
            component_type = selected_data['component'] if selected_data else None
            parameter = selected_data['parameter'] if selected_data else None
            
            # Create interactive plot for selected parameter (FAST - only one view)
            plotter = InteractiveNetworkPlot(self.NetworkGenerationData.net)
            fig = plotter.create_plot(
                parameter=parameter,
                component_type=component_type,
                basemap_style='carto-positron',
                colorscale='RdYlBu_r'
            )
            
            if WEBENGINE_AVAILABLE:
                # Export to HTML with embedded Plotly.js (no CDN needed)
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    # Use 'inline' to embed full Plotly.js library (~3MB) directly in HTML
                    # This avoids CDN issues in QWebEngineView
                    fig.write_html(
                        f.name,
                        include_plotlyjs='inline',  # Embed Plotly.js directly - no external dependencies
                        config={'displayModeBar': True, 'displaylogo': False}
                    )
                    self._plot_html_path = f.name
                
                # Inject click event handler into HTML
                self._inject_click_handler(self._plot_html_path)
                
                # Load HTML in WebEngineView
                self.pandapipes_net_canvas.setUrl(QUrl.fromLocalFile(self._plot_html_path))
                
                # Start polling for clicks after plot is loaded
                if not self._plot_click_timer.isActive():
                    self._plot_click_timer.start()
            else:
                # Fallback message
                if isinstance(self.pandapipes_net_canvas, QLabel):
                    self.pandapipes_net_canvas.setText(
                        "Interactive visualization requires PyQt6-WebEngine.\n"
                        "Please install: pip install PyQt6-WebEngine"
                    )
        except Exception as e:
            logging.error(f"Error creating interactive plot: {e}")
            logging.error(traceback.format_exc())
            if WEBENGINE_AVAILABLE:
                self.pandapipes_net_canvas.setHtml(
                    f"<html><body><h3>Error creating plot:</h3><p>{str(e)}</p></body></html>"
                )

    def time_series_simulation(self):
        """
        Perform time series simulation.
        """
        if self.NetworkGenerationData is None:
            QMessageBox.warning(self, "Keine Netzdaten", "Bitte generieren Sie zuerst ein Netz.")
            return

        try:
            # Check if simplified calculation is requested
            simplified = getattr(self.NetworkGenerationData, 'simplified_calculation', False)
            self.calculationThread = NetCalculationThread(self.NetworkGenerationData, simplified=simplified)
            self.calculationThread.calculation_done.connect(self.on_time_series_simulation_done)
            self.calculationThread.calculation_error.connect(self.on_time_series_simulation_error)
            self.calculationThread.start()
            self.progressBar.setRange(0, 0)

        except ValueError as e:
            QMessageBox.warning("Ungültige Eingabe", str(e))

    def on_time_series_simulation_done(self, NetworkGenerationData):
        """
        Handle time series simulation completion.

        :param NetworkGenerationData: Network generation data with results.
        :type NetworkGenerationData: object
        """
        self.progressBar.setRange(0, 1)
        self.NetworkGenerationData = NetworkGenerationData

        # Invalidate plot cache to regenerate with simulation results
        self._invalidate_plot_cache()
        
        # Update parameter dropdown (in case new parameters available after simulation)
        self._populate_network_param_dropdown()

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

        :param error_message: Error message to display.
        :type error_message: str
        """
        QMessageBox.critical(self, "Berechnungsfehler", error_message)
        self.progressBar.setRange(0, 1)

    def update_time_series_plot(self):
        """
        Update time series plot based on selected data with modern styling.
        """
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

        :return: Data directory path.
        :rtype: str
        """
        # Gehe zwei Ebenen über base_path hinaus, um den Projektpfad zu erhalten
        project_base_path = os.path.dirname(os.path.dirname(self.base_path))

        # Kombiniere den Projektpfad mit dem festen Datenpfad
        return os.path.join(project_base_path, "src", "districtheatingsim", "data")

    def saveNet(self, show_dialog=True):
        """
        Save network data to pickle, CSV, and JSON files.

        :param show_dialog: Whether to show success/error dialogs.
        :type show_dialog: bool
        """
        print("Speichere Pandapipes-Netzwerk...")
        if not self.NetworkGenerationData:
            if show_dialog:
                QMessageBox.warning(self, "Keine Daten", "Kein Pandapipes-Netzwerk zum Speichern vorhanden.")
            return
            
        try:
            pickle_file_path = os.path.join(self.base_path, self.config_manager.get_relative_path('pp_pickle_file_path'))
            csv_file_path = os.path.join(self.base_path, self.config_manager.get_relative_path('csv_net_init_file_path'))
            json_file_path = os.path.join(self.base_path, self.config_manager.get_relative_path('json_net_init_file_path'))
            
            # Sichere die ursprünglichen absoluten Pfade für COP und TRY Dateien
            original_cop_filename = self.NetworkGenerationData.COP_filename
            original_try_filename = self.NetworkGenerationData.TRY_filename
            
            # Konvertiere zu relativen Pfaden für die Speicherung (relativ zu base_path)
            if self.NetworkGenerationData.COP_filename and os.path.isabs(self.NetworkGenerationData.COP_filename):
                self.NetworkGenerationData.COP_filename = os.path.relpath(self.NetworkGenerationData.COP_filename, self.base_path)
            if self.NetworkGenerationData.TRY_filename and os.path.isabs(self.NetworkGenerationData.TRY_filename):
                self.NetworkGenerationData.TRY_filename = os.path.relpath(self.NetworkGenerationData.TRY_filename, self.base_path)

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
            combined_df.to_csv(csv_file_path, sep=';', date_format='%Y-%m-%dT%H:%M:%S', encoding='utf-8-sig')

            # Metadaten/Parameter speichern
            meta_dict = self.NetworkGenerationData.to_dict()
            # Entferne große/unnötige Felder bzw. bereits gespeicherte Daten
            meta_dict.pop('net', None)
            meta_dict.pop('waerme_hast_ges_W', None)
            meta_dict.pop('strombedarf_hast_ges_W', None)
            meta_dict.pop('waerme_hast_ges_kW', None)
            meta_dict.pop('strombedarf_hast_ges_kW', None)
            meta_dict.pop('waerme_ges_kW', None)
            meta_dict.pop('strombedarf_ges_kW', None)
            meta_dict.pop('yearly_time_steps', None)
            meta_dict.pop('pump_results', None)
            meta_dict.pop('plot_data', None)

            # ggf. weitere Felder entfernen oder anpassen
            with open(json_file_path, 'w') as json_file:
                json.dump(meta_dict, json_file, indent=4, default=str)
            
            # Stelle die ursprünglichen absoluten Pfade wieder her
            self.NetworkGenerationData.COP_filename = original_cop_filename
            self.NetworkGenerationData.TRY_filename = original_try_filename
            
            if show_dialog:
                QMessageBox.information(
                    self, 
                    "Speichern erfolgreich", 
                    f"✓ Pandapipes Netz erfolgreich gespeichert!\n\n"
                    f"Dateien:\n"
                    f"  • {os.path.basename(pickle_file_path)}\n"
                    f"  • {os.path.basename(csv_file_path)}\n"
                    f"  • {os.path.basename(json_file_path)}\n\n"
                    f"Pfad: {os.path.dirname(pickle_file_path)}"
                )
        except Exception as e:
            if show_dialog:
                QMessageBox.critical(
                    self, 
                    "Speichern fehlgeschlagen", 
                    f"Fehler beim Speichern der Daten:\n\n{str(e)}"
                )

    def loadNet(self, show_dialog=True):
        """
        Load network data from saved files.

        :param show_dialog: Whether to show success/error dialogs.
        :type show_dialog: bool
        """
        print("Lade gespeichertes Pandapipes-Netzwerk...")
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
            self.NetworkGenerationData = NetworkGenerationData.from_dict(meta_dict)
            
            # Konvertiere relative Pfade zurück zu absoluten Pfaden (relativ zu base_path)
            if self.NetworkGenerationData.COP_filename and not os.path.isabs(self.NetworkGenerationData.COP_filename):
                self.NetworkGenerationData.COP_filename = os.path.normpath(os.path.join(self.base_path, self.NetworkGenerationData.COP_filename))
            if self.NetworkGenerationData.TRY_filename and not os.path.isabs(self.NetworkGenerationData.TRY_filename):
                self.NetworkGenerationData.TRY_filename = os.path.normpath(os.path.join(self.base_path, self.NetworkGenerationData.TRY_filename))
            
            self.NetworkGenerationData.net = net
            self.NetworkGenerationData.waerme_hast_ges_W = waerme_hast_ges_W
            self.NetworkGenerationData.strombedarf_hast_ges_W = strombedarf_hast_ges_W
            self.NetworkGenerationData.yearly_time_steps = yearly_time_steps

            self.NetworkGenerationData.waerme_hast_ges_kW = np.where(self.NetworkGenerationData.waerme_hast_ges_W == 0, 0, self.NetworkGenerationData.waerme_hast_ges_W / 1000)
            self.NetworkGenerationData.strombedarf_hast_ges_kW = np.where(self.NetworkGenerationData.strombedarf_hast_ges_W == 0, 0, self.NetworkGenerationData.strombedarf_hast_ges_W / 1000)
            
            self.NetworkGenerationData.waerme_ges_kW = np.sum(self.NetworkGenerationData.waerme_hast_ges_kW, axis=0)
            self.NetworkGenerationData.strombedarf_ges_kW = np.sum(self.NetworkGenerationData.strombedarf_hast_ges_kW, axis=0)
            
            # Store original pipe DataFrame for restore functionality
            if hasattr(self.NetworkGenerationData, 'net'):
                self._original_pipe_df = self.NetworkGenerationData.net.pipe.copy()
            
            # Populate parameter dropdown with loaded network
            self._populate_network_param_dropdown()
            
            self.plot_pandapipes_net()
            
            # Populate pipe configuration table
            self.populate_pipe_table()
            
            self.NetworkGenerationData.prepare_plot_data()
            self.createPlotControlDropdown()
            self.update_time_series_plot()
            self.display_results()

            if show_dialog:
                QMessageBox.information(
                    self, 
                    "Laden erfolgreich", 
                    f"✓ Netz erfolgreich geladen!\n\n"
                    f"Dateien:\n"
                    f"  • {os.path.basename(pickle_file_path)}\n"
                    f"  • {os.path.basename(csv_file_path)}\n"
                    f"  • {os.path.basename(json_file_path)}\n\n"
                    f"Pfad: {os.path.dirname(pickle_file_path)}"
                )
        except Exception as e:
            tb = traceback.format_exc()
            if show_dialog:
                QMessageBox.critical(
                    self, 
                    "Laden fehlgeschlagen", 
                    f"Fehler beim Laden der Daten:\n\n{str(e)}"
                )
            else:
                logging.error(f"Fehler beim Laden der Netzwerk-Daten: {e}\n{tb}")

    def load_net_results(self, show_dialog=True):
        """
        Load network simulation results from CSV file.

        :param show_dialog: Whether to show warning dialogs.
        :type show_dialog: bool
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
        """
        Export dimensioned network to unified GeoJSON format.

        :param show_dialog: Whether to show success/error dialogs.
        :type show_dialog: bool
        """
        print("Starte Export des Wärmenetzes im GeoJSON-Format...")
        if not self.NetworkGenerationData or not hasattr(self.NetworkGenerationData, 'net'):
            if show_dialog:
                QMessageBox.warning(
                    self,
                    "Kein Netz vorhanden",
                    "Es muss zuerst ein Netz generiert werden, bevor es exportiert werden kann."
                )
            return
        
        try:
            # Get unified GeoJSON path from config
            unified_path = os.path.join(
                self.base_path, 
                self.config_manager.get_relative_path('dimensioned_net_path')
            )
            
            print(f"Exportiere Wärmenetz zu: {unified_path}")
            # Export network using utility function
            feature_counts = export_net_geojson(self.NetworkGenerationData.net, unified_path)
            
            if show_dialog:
                total_features = sum(feature_counts.values())
                QMessageBox.information(
                    self,
                    "Export erfolgreich",
                    f"✓ Wärmenetz erfolgreich exportiert!\n\n"
                    f"Datei: {os.path.basename(unified_path)}\n"
                    f"Pfad: {os.path.dirname(unified_path)}\n\n"
                    f"Exportierte Features:\n"
                    f"  • Vorlauf: {feature_counts['flow']}\n"
                    f"  • Rücklauf: {feature_counts['return']}\n"
                    f"  • Gebäudeanschlüsse: {feature_counts['building']}\n"
                    f"  • Erzeuger: {feature_counts['generator']}\n"
                    f"  • Gesamt: {total_features} Features"
                )
                
        except Exception as e:
            if show_dialog:
                QMessageBox.critical(
                    self,
                    "Export fehlgeschlagen",
                    f"Fehler beim Exportieren des Wärmenetzes:\n\n{str(e)}"
                )
            else:
                logging.error(f"Fehler beim Exportieren des Wärmenetzes: {e}")
    
    def _inject_click_handler(self, html_path):
        """
        Inject JavaScript click handler into Plotly HTML for pipe selection.

        :param html_path: Path to the HTML file to modify.
        :type html_path: str
        """
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html = f.read()
            
            # JavaScript to handle pipe clicks and select table rows
            click_script = """
            <script>
            // Wait for Plotly to be ready
            document.addEventListener('DOMContentLoaded', function() {
                var plotDiv = document.getElementsByClassName('plotly-graph-div')[0];
                if (!plotDiv) return;
                
                
                // Store last highlighted trace
                window.lastHighlighted = -1;
                
                // Add click event listener
                plotDiv.on('plotly_click', function(data) {
                    console.log('Plotly click event:', data);
                    
                    try {
                        for (var i = 0; i < data.points.length; i++) {
                            var point = data.points[i];
                            
                            // Check if customdata exists (should contain pipe index)
                            if (point.customdata && point.customdata.length > 0) {
                                var pipeIdx = point.customdata[0];
                                var traceIdx = point.curveNumber;
                                console.log('Pipe clicked:', pipeIdx, 'trace:', traceIdx);
                                
                                // Highlight the clicked pipe
                                window.highlightPipe(pipeIdx, traceIdx);
                                
                                // Store for Python polling
                                window.selectedPipeIndex = pipeIdx;
                                console.log('Stored pipe index in window:', pipeIdx);
                            }
                        }
                    } catch (e) {
                        console.error('Error in click handler:', e);
                    }
                });
                
                // Function to highlight a specific pipe
                window.highlightPipe = function(pipeIdx, traceIdx) {
                    try {
                        var plotDiv = document.getElementsByClassName('plotly-graph-div')[0];
                        if (!plotDiv || !plotDiv.data) {
                            console.log('No plot div or data');
                            return;
                        }
                        
                        console.log('Highlighting pipe:', pipeIdx, 'trace:', traceIdx);
                        
                        // Reset previous highlight
                        if (window.lastHighlighted >= 0) {
                            Plotly.restyle(plotDiv, {
                                'line.width': 4,
                                'line.color': '#2c3e50'
                            }, [window.lastHighlighted]);
                        }
                        
                        // Find the trace to highlight
                        var targetTrace = -1;
                        if (traceIdx !== undefined && traceIdx >= 0) {
                            targetTrace = traceIdx;
                        } else {
                            // Search by pipe index
                            for (var i = 0; i < plotDiv.data.length; i++) {
                                var trace = plotDiv.data[i];
                                if (trace.customdata && trace.customdata[0] && trace.customdata[0][0] === pipeIdx) {
                                    targetTrace = i;
                                    break;
                                }
                            }
                        }
                        
                        // Apply highlight
                        if (targetTrace >= 0) {
                            console.log('Applying highlight to trace:', targetTrace);
                            Plotly.restyle(plotDiv, {
                                'line.width': 8,
                                'line.color': '#FF4500'
                            }, [targetTrace]);
                            window.lastHighlighted = targetTrace;
                        } else {
                            console.log('Target trace not found');
                        }
                    } catch (e) {
                        console.error('Error highlighting pipe:', e);
                    }
                };
                
                console.log('Plotly click handler registered');
            });
            </script>
            """
            
            # Inject before closing body tag
            html = html.replace('</body>', click_script + '</body>')
            
            # Write back
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
                
            logging.info("Click handler injected into plot HTML")
            
        except Exception as e:
            logging.error(f"Failed to inject click handler: {e}")
    
    def _check_plot_click(self):
        """
        Poll JavaScript for pipe clicks and update table selection.
        """
        if not WEBENGINE_AVAILABLE or not hasattr(self, 'pipe_table'):
            return
        
        try:
            # Query JavaScript for selected pipe index
            self.pandapipes_net_canvas.page().runJavaScript(
                "window.selectedPipeIndex",
                self._handle_plot_click_result
            )
        except Exception as e:
            logging.debug(f"Error checking plot click: {e}")
    
    def _handle_plot_click_result(self, pipe_idx):
        """
        Handle the result from JavaScript pipe click query.

        :param pipe_idx: Index of clicked pipe, or None if no click.
        :type pipe_idx: int or None
        """
        if pipe_idx is None or pipe_idx == self._last_selected_pipe:
            return
        
        try:
            # Find and select the table row for this pipe
            for row in range(self.pipe_table.rowCount()):
                item = self.pipe_table.item(row, 0)  # Index column
                if item and int(item.text()) == pipe_idx:
                    # Block signals to prevent recursion
                    self.pipe_table.blockSignals(True)
                    self.pipe_table.selectRow(row)
                    self.pipe_table.scrollToItem(item)
                    self.pipe_table.blockSignals(False)
                    
                    self._last_selected_pipe = pipe_idx
                    logging.info(f"Plot click: Selected pipe {pipe_idx} in table (row {row})")
                    
                    # Clear the JavaScript variable
                    self.pandapipes_net_canvas.page().runJavaScript(
                        "window.selectedPipeIndex = null;"
                    )
                    break
        except Exception as e:
            logging.error(f"Error handling plot click result: {e}")
    
    def apply_table_changes_to_net(self):
        """
        Apply all table changes to the network before calculation.
        """
        if not self.NetworkGenerationData or not hasattr(self.NetworkGenerationData, 'net'):
            return
        
        net = self.NetworkGenerationData.net
        
        try:
            # Get available pipe types
            pipe_std_types = pp.std_types.available_std_types(net, "pipe")
        except:
            pipe_std_types = None
        
        # Iterate through all rows and update net.pipe
        for row in range(self.pipe_table.rowCount()):
            pipe_idx = int(self.pipe_table.item(row, 0).text())
            
            # Update std_type from ComboBox
            combo = self.pipe_table.cellWidget(row, 5)
            if combo:
                std_type = combo.currentText()
                if std_type:
                    net.pipe.at[pipe_idx, 'std_type'] = std_type
                    
                    # Update properties from std_type
                    if pipe_std_types is not None and std_type in pipe_std_types.index:
                        properties = pipe_std_types.loc[std_type]
                        net.pipe.at[pipe_idx, 'u_w_per_m2k'] = properties['u_w_per_m2k']
            
            # Update diameter
            diameter_item = self.pipe_table.item(row, 6)
            if diameter_item:
                try:
                    diameter_mm = float(diameter_item.text())
                    net.pipe.at[pipe_idx, 'diameter_m'] = diameter_mm / 1000
                except ValueError:
                    pass
            
            # Update roughness k
            k_item = self.pipe_table.item(row, 7)
            if k_item:
                try:
                    k_mm = float(k_item.text())
                    net.pipe.at[pipe_idx, 'k_mm'] = k_mm
                except ValueError:
                    pass
        
        logging.info("Applied all table changes to network")
    
    def recalculateNetwork(self):
        """
        Recalculate network with current pipe parameters (pipeflow only, no optimization).
        """
        if not self.NetworkGenerationData or not hasattr(self.NetworkGenerationData, 'net'):
            QMessageBox.warning(
                self,
                "Kein Netz vorhanden",
                "Es muss zuerst ein Netz generiert werden, bevor neu berechnet werden kann."
            )
            return
        
        try:
            from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import run_control
            
            # Apply all table changes to network BEFORE calculation
            self.apply_table_changes_to_net()
            
            # Show progress with proper management
            self.progressBar.setVisible(True)
            self.progressBar.setValue(0)
            self.progressBar.setFormat("Führe thermohydraulische Berechnung durch...")
            QApplication.processEvents()
            
            # Run pipeflow calculation
            logging.info("Starting pipeflow recalculation...")
            self.progressBar.setValue(30)
            QApplication.processEvents()
            
            pp.pipeflow(self.NetworkGenerationData.net, mode="bidirectional", iter=100)
            
            # Run controller
            logging.info("Running controller...")
            self.progressBar.setValue(60)
            QApplication.processEvents()
            
            run_control(self.NetworkGenerationData.net, mode="bidirectional", iter=100)
            
            self.progressBar.setValue(90)
            QApplication.processEvents()
            
            # Invalidate cache and force plot refresh with new data
            self._invalidate_plot_cache()
            self.plot_pandapipes_net(force_refresh=True)
            
            # Update results display if available
            if hasattr(self, 'display_results'):
                self.display_results()
            
            self.progressBar.setValue(100)
            self.progressBar.setFormat("Berechnung abgeschlossen")
            QApplication.processEvents()
            
            logging.info("Network recalculation completed successfully")
            
            # Hide progress bar after short delay
            QTimer.singleShot(1000, lambda: self.progressBar.setVisible(False))
            
            QMessageBox.information(
                self,
                "Berechnung abgeschlossen",
                "Die thermohydraulische Berechnung wurde erfolgreich durchgeführt.\n\n"
                "Das Netzwerk wurde mit den aktuellen Rohrleitungsparametern neu berechnet."
            )
            
        except Exception as e:
            logging.error(f"Error recalculating network: {e}")
            import traceback
            traceback.print_exc()
            
            self.progressBar.setVisible(False)
            
            QMessageBox.critical(
                self,
                "Berechnungsfehler",
                f"Fehler bei der Netzberechnung:\n\n{str(e)}\n\n"
                f"Überprüfen Sie die Rohrleitungsparameter und Randbedingungen."
            )
    
    def populate_pipe_table(self):
        """
        Populate pipe configuration table with data from net.pipe DataFrame.
        """
        if not self.NetworkGenerationData or not hasattr(self.NetworkGenerationData, 'net'):
            return
        
        net = self.NetworkGenerationData.net
        
        # Block signals during population
        self.pipe_table.blockSignals(True)
        
        # Define columns
        columns = ['Index', 'Name', 'Von', 'Nach', 'Länge [m]', 'Std-Typ', 'DN [mm]', 'k [mm]']
        self.pipe_table.setColumnCount(len(columns))
        self.pipe_table.setHorizontalHeaderLabels(columns)
        
        # Set row count
        self.pipe_table.setRowCount(len(net.pipe))
        
        # Set row height for better ComboBox display
        self.pipe_table.verticalHeader().setDefaultSectionSize(50)
        
        # Load available pipe standard types
        try:
            pipe_std_types = pp.std_types.available_std_types(net, "pipe")
        except:
            pipe_std_types = None
        
        # Populate rows
        for row, (idx, pipe_data) in enumerate(net.pipe.iterrows()):
            # Column 0: Index (read-only)
            item = QTableWidgetItem(str(idx))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.pipe_table.setItem(row, 0, item)
            
            # Column 1: Name (read-only)
            name = pipe_data.get('name', f'Pipe {idx}')
            item = QTableWidgetItem(str(name))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.pipe_table.setItem(row, 1, item)
            
            # Column 2: From Junction (read-only)
            item = QTableWidgetItem(f"J{pipe_data['from_junction']}")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.pipe_table.setItem(row, 2, item)
            
            # Column 3: To Junction (read-only)
            item = QTableWidgetItem(f"J{pipe_data['to_junction']}")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.pipe_table.setItem(row, 3, item)
            
            # Column 4: Length (read-only)
            length_m = pipe_data['length_km'] * 1000
            item = QTableWidgetItem(f"{length_m:.1f}")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.pipe_table.setItem(row, 4, item)
            
            # Column 5: Std Type (ComboBox)
            combo = QComboBox()
            combo.setMinimumHeight(25)
            combo.setStyleSheet("""
                QComboBox {
                    padding: 4px 8px;
                    border: 1px solid #bdc3c7;
                    border-radius: 3px;
                    background-color: white;
                    color: black;
                    font-size: 11pt;
                }
                QComboBox:focus {
                    border: 2px solid #3498db;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox QAbstractItemView {
                    background-color: white;
                    color: black;
                    selection-background-color: #3498db;
                    selection-color: white;
                }
            """)
            if pipe_std_types is not None:
                combo.addItems(pipe_std_types.index.tolist())
                current_type = pipe_data.get('std_type', '')
                if current_type and current_type in pipe_std_types.index:
                    combo.setCurrentText(current_type)
                elif len(pipe_std_types.index) > 0:
                    # Fallback: set first item if no valid current type
                    combo.setCurrentIndex(0)
            combo.currentTextChanged.connect(lambda text, r=row: self.on_std_type_changed(r, text))
            self.pipe_table.setCellWidget(row, 5, combo)
            
            # Column 6: Diameter (editable)
            diameter_mm = pipe_data.get('diameter_m', 0) * 1000
            item = QTableWidgetItem(f"{diameter_mm:.1f}")
            self.pipe_table.setItem(row, 6, item)
            
            # Column 7: Roughness k (editable)
            k_mm = pipe_data.get('k_mm', 0.1)
            item = QTableWidgetItem(f"{k_mm:.2f}")
            self.pipe_table.setItem(row, 7, item)
        
        # Adjust column widths
        header = self.pipe_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setDefaultSectionSize(60)
        header.resizeSection(0, 60)  # Index
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 60)  # Von
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 60)  # Nach
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 90)  # Länge
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, 200)  # Std-Typ (breiter für bessere Sichtbarkeit)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(6, 80)  # DN
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(7, 80)  # k
        
        self.pipe_table.blockSignals(False)
        
        # Show pipe table container
        self.pipe_table_container.show()
    
    def on_pipe_selected_in_table(self):
        """
        Handle table row selection - highlight pipe in plot.
        """
        selected_rows = self.pipe_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        pipe_idx = int(self.pipe_table.item(row, 0).text())
        
        logging.info(f"Table selection: Pipe {pipe_idx}")
        
        # Highlight pipe in plot via JavaScript
        if WEBENGINE_AVAILABLE and hasattr(self, 'pandapipes_net_canvas'):
            js_code = f"if (window.highlightPipe) {{ window.highlightPipe({pipe_idx}); }}"
            self.pandapipes_net_canvas.page().runJavaScript(js_code)
    
    def on_std_type_changed(self, row, new_std_type):
        """
        Handle standard type change in ComboBox.

        :param row: Table row index.
        :type row: int
        :param new_std_type: New standard type name.
        :type new_std_type: str
        """
        if not new_std_type or not self.NetworkGenerationData:
            return
        
        net = self.NetworkGenerationData.net
        pipe_idx = int(self.pipe_table.item(row, 0).text())
        
        try:
            pipe_std_types = pp.std_types.available_std_types(net, "pipe")
            properties = pipe_std_types.loc[new_std_type]
            
            # Update net.pipe
            net.pipe.at[pipe_idx, 'std_type'] = new_std_type
            net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
            net.pipe.at[pipe_idx, 'u_w_per_m2k'] = properties['u_w_per_m2k']
            
            # Update table (diameter)
            self.pipe_table.blockSignals(True)
            diameter_item = self.pipe_table.item(row, 6)
            if diameter_item:
                diameter_item.setText(f"{properties['inner_diameter_mm']:.1f}")
            self.pipe_table.blockSignals(False)
            
            logging.info(f"Pipe {pipe_idx}: std_type changed to {new_std_type}")
            
        except Exception as e:
            logging.error(f"Failed to update pipe {pipe_idx} std_type: {e}")
    
    def on_table_item_changed(self, item):
        """
        Handle direct table cell edits (diameter, k).

        :param item: Changed table item.
        :type item: QTableWidgetItem
        """
        if not self.NetworkGenerationData:
            return
        
        row = item.row()
        col = item.column()
        
        pipe_idx = int(self.pipe_table.item(row, 0).text())
        net = self.NetworkGenerationData.net
        
        try:
            # Column 6: Diameter
            if col == 6:
                diameter_mm = float(item.text())
                net.pipe.at[pipe_idx, 'diameter_m'] = diameter_mm / 1000
                logging.info(f"Pipe {pipe_idx}: diameter changed to {diameter_mm} mm")
            
            # Column 7: Roughness k
            elif col == 7:
                k_mm = float(item.text())
                net.pipe.at[pipe_idx, 'k_mm'] = k_mm
                logging.info(f"Pipe {pipe_idx}: k changed to {k_mm} mm")
                
        except ValueError:
            logging.warning(f"Invalid value entered in row {row}, col {col}")
            # Revert to original value
            if col == 6:
                diameter_mm = net.pipe.at[pipe_idx, 'diameter_m'] * 1000
                item.setText(f"{diameter_mm:.1f}")
            elif col == 7:
                k_mm = net.pipe.at[pipe_idx, 'k_mm']
                item.setText(f"{k_mm:.2f}")
    
    def restore_pipe_defaults(self):
        """
        Restore pipe parameters to original values.
        """
        if not self.NetworkGenerationData or not hasattr(self, '_original_pipe_df'):
            QMessageBox.warning(
                self,
                "Keine Originaldaten",
                "Es sind keine Originaldaten zum Wiederherstellen vorhanden."
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Standardwerte wiederherstellen",
            "Möchten Sie alle Änderungen an den Rohrleitungsparametern verwerfen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.NetworkGenerationData.net.pipe = self._original_pipe_df.copy()
            self.populate_pipe_table()
            logging.info("Restored original pipe parameters")