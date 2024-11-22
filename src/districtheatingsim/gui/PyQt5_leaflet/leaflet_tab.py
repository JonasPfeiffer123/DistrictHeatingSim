"""
Filename: leaflet_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-10-30
Description: Contains the LeafTab class for displaying a Leaflet map in a PyQt5 application.
"""

import os
import sys
import json
import geopandas as gpd
import pandas as pd
import traceback
import os
import tempfile

from PyQt5.QtWidgets import QVBoxLayout, QWidget, QFileDialog, QMenuBar, QAction, QProgressBar, QMessageBox, QMainWindow, QDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QObject, pyqtSlot, pyqtSignal
from PyQt5.QtWebChannel import QWebChannel

from districtheatingsim.gui.VisualizationTab.visualization_dialogs import LayerGenerationDialog, DownloadOSMDataDialog, OSMBuildingQueryDialog
from districtheatingsim.gui.VisualizationTab.net_generation_threads import NetGenerationThread, FileImportThread, GeocodingThread

from shapely.geometry import Point

class GeoJsonReceiver(QObject):
    @pyqtSlot(str)
    def sendGeoJSONToPython(self, geojson_str):
        print("Received GeoJSON from JavaScript")
        
        # Konvertiere den JSON-String in ein Python-Objekt
        geojson_data = json.loads(geojson_str)
        
        # Erstelle ein GeoDataFrame aus dem GeoJSON
        gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
        
        # Setze das ursprüngliche CRS (EPSG:4326)
        gdf.set_crs(epsg=4326, inplace=True)
        
        # Konvertiere das CRS in das gewünschte Ziel-CRS (z.B. EPSG:25833)
        target_crs = 'EPSG:25833'
        gdf.to_crs(target_crs, inplace=True)
        
        # Speichere die Daten als GeoJSON
        output_file = 'exported_data.geojson'
        gdf.to_file(output_file, driver="GeoJSON")
        print(f"GeoJSON gespeichert in {output_file}")

class VisualizationModel:
    """
    The VisualizationModel class is responsible for handling all data-related operations
    such as loading and saving GeoJSON files, generating GeoJSON from CSV files, 
    and calculating the center and zoom level of the map.
    """

    def __init__(self):
        """Initializes the VisualizationModel with empty layers and base path."""
        self.layers = {}
        self.base_path = ""

    def set_base_path(self, base_path):
        """
        Sets the base path for file operations.

        Args:
            base_path (str): The base path to be set.
        """
        self.base_path = base_path

    def get_base_path(self):
        """
        Returns the current base path.

        Returns:
            str: The current base path.
        """
        return self.base_path

    def load_geojson(self, file_path):
        """
        Loads a GeoJSON file and returns it as a GeoDataFrame.

        Args:
            file_path (str): The path to the GeoJSON file.

        Returns:
            GeoDataFrame: The loaded GeoJSON as a GeoDataFrame.
        """
        return gpd.read_file(file_path)

    def create_geojson_from_csv(self, csv_file_path, geojson_file_path):
        """
        Creates a GeoJSON file from a CSV file containing coordinates.

        Args:
            csv_file_path (str): The path to the CSV file.
            geojson_file_path (str): The path where the GeoJSON file will be saved.
        """
        df = pd.read_csv(csv_file_path, delimiter=';')
        gdf = gpd.GeoDataFrame(
            df,
            geometry=[Point(xy) for xy in zip(df.UTM_X, df.UTM_Y)],
            crs="EPSG:25833"
        )
        gdf.to_file(geojson_file_path, driver='GeoJSON')
        print(f"GeoJSON created at: {geojson_file_path}")

    def get_resource_path(self, relative_path):
        """
        Get the absolute path to the resource, works for development and for PyInstaller.

        Args:
            relative_path (str): The relative path to the resource.

        Returns:
            str: The absolute path to the resource.
        """
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_path, relative_path)

class VisualizationPresenter(QObject):
    """
    The VisualizationPresenter class acts as the mediator between the model and the view.
    It handles user input, updates the model, and refreshes the view accordingly.

    Attributes:
        layers_imported (pyqtSignal): Signal emitted when layers are imported.
        model (VisualizationModel): The model instance containing the data logic.
        view (VisualizationTabView): The view instance containing the UI logic.
        data_manager (DataManager): The data manager that handles project-related data.
    """

    layers_imported = pyqtSignal(dict)

    def __init__(self, model, view, folder_manager, data_manager, config_manager):
        """
        Initializes the VisualizationPresenter with the given model, view, and data manager.

        Args:
            model (VisualizationModel): The model instance.
            view (VisualizationTabView): The view instance.
            data_manager (DataManager): The data manager instance.
        """
        super().__init__()
        self.model = model
        self.view = view
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        self.view.map_file_path = self.model.get_resource_path("gui/PyQt5_leaflet/map.html")

        # Set up folder change handling
        self.folder_manager.project_folder_changed.connect(self.on_project_folder_changed)

        # Connect UI actions to methods
        self.view.downloadAction.triggered.connect(self.open_geocode_addresses_dialog)
        self.view.loadCsvAction.triggered.connect(self.load_csv_coordinates)
        self.view.importAction.triggered.connect(self.import_geojson)
        self.view.layerGenerationAction.triggered.connect(self.open_layer_generation_dialog)
        self.view.downloadActionOSM.triggered.connect(self.open_osm_data_dialog)
        self.view.osmBuildingAction.triggered.connect(self.open_osm_building_query_dialog)

        # Initialize map view
        self.on_project_folder_changed(self.folder_manager.variant_folder)

    def on_project_folder_changed(self, new_base_path):
        """
        Updates the base path in the model when the project folder changes.

        Args:
            new_base_path (str): The new base path.
        """
        self.model.set_base_path(new_base_path)

    def open_geocode_addresses_dialog(self):
        """
        Open a dialog to select a CSV file for geocoding addresses.
        """
        fname, _ = QFileDialog.getOpenFileName(self.view, 'CSV-Koordinaten laden', self.model.get_base_path(), 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.geocode_addresses(fname)

    def geocode_addresses(self, inputfilename):
        """
        Starts the geocoding process for the provided CSV file.

        Args:
            inputfilename (str): The path to the CSV file.
        """
        if hasattr(self, 'geocodingThread') and self.geocodingThread.isRunning():
            self.geocodingThread.terminate()
            self.geocodingThread.wait()
        self.geocodingThread = GeocodingThread(inputfilename)
        self.geocodingThread.calculation_done.connect(self.on_geocode_done)
        self.geocodingThread.calculation_error.connect(self.on_geocode_error)
        self.geocodingThread.start()
        self.view.progressBar.setRange(0, 0)

    def on_geocode_done(self, fname):
        """
        Handles successful completion of geocoding and loads the resulting CSV coordinates.

        Args:
            fname (str): The path to the generated CSV file.
        """
        self.view.progressBar.setRange(0, 1)
        self.load_csv_coordinates(fname)

    def on_geocode_error(self, error_message):
        """
        Handles errors that occur during the geocoding process.

        Args:
            error_message (str): The error message to display.
        """
        self.view.show_error_message("Fehler beim Geocoding", error_message)
        self.view.progressBar.setRange(0, 1)

    def load_csv_coordinates(self, fname=None):
        """
        Loads coordinates from a CSV file and adds them as a GeoJSON layer to the map.
        """
        try:
            if not fname:
                fname, _ = QFileDialog.getOpenFileName(self.view, 'CSV-Koordinaten laden', self.model.get_base_path(), 'CSV Files (*.csv);;All Files (*)')
            if fname:
                geojson_path = os.path.join(self.model.get_base_path(), 'Gebäudedaten', f"{os.path.splitext(os.path.basename(fname))[0]}.geojson")
                self.model.create_geojson_from_csv(fname, geojson_path)
                self.add_geojson_layer([geojson_path])
        except Exception as e:
            error_message = f"{str(e)}\n\n{traceback.format_exc()}"
            self.view.show_error_message("Fehler beim Importieren von GeoJSON", error_message)

    def import_geojson(self):
        """
        Imports GeoJSON files and adds them as layers to the map.
        """
        try:
            fnames, _ = QFileDialog.getOpenFileNames(self.view, 'Netzdaten importieren', self.model.get_base_path(), 'GeoJSON Files (*.geojson);;All Files (*)')
            if fnames:
                self.add_geojson_layer(fnames)
        except Exception as e:
            error_message = f"{str(e)}\n\n{traceback.format_exc()}"
            self.view.show_error_message("Fehler beim Importieren von GeoJSON", error_message)

    def add_geojson_layer(self, filenames):
        """
        Adds GeoJSON layers to the map.

        Args:
            filenames (list): A list of GeoJSON file paths.
            color (str, optional): The color to use for the layer.
        """
        try:
            for filename in filenames:
                # Add the layer to the model
                layer_name = os.path.splitext(os.path.basename(filename))[0]

                with open(filename, 'r') as f:
                    geojson_data = json.load(f)

                # Pass the layers data to JavaScript via the WebChannel
                layer_json = json.dumps(geojson_data)
                self.view.web_view.page().runJavaScript(f"window.importGeoJSON({layer_json}, '{layer_name}');")

        except Exception as e:
            error_message = f"{str(e)}\n\n{traceback.format_exc()}"
            self.view.show_error_message("Fehler beim Hinzufügen einer GeoJSON-Schicht", error_message)

    def open_layer_generation_dialog(self):
        """
        Opens the dialog for generating layers from data.
        """
        dialog = LayerGenerationDialog(self.model.get_base_path(), self.config_manager, self.view)
        dialog.setVisualizationTab(self)
        dialog.accepted_inputs.connect(self.generate_and_import_layers)
        self.currentLayerDialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self.view.raise_()
        self.view.activateWindow()

    def generate_and_import_layers(self, inputs):
        """
        Starts the process of generating and importing layers based on user inputs.

        Args:
            inputs (dict): The inputs for generating layers.
        """
        if hasattr(self, 'netgenerationThread') and self.netgenerationThread.isRunning():
            self.netgenerationThread.terminate()
            self.netgenerationThread.wait()
        self.netgenerationThread = NetGenerationThread(inputs, self.model.get_base_path())
        self.netgenerationThread.calculation_done.connect(self.on_generation_done)
        self.netgenerationThread.calculation_error.connect(self.on_generation_error)
        self.netgenerationThread.start()
        self.view.progressBar.setRange(0, 0)

    def on_generation_done(self, results):
        """
        Handles successful layer generation and updates the map view.

        Args:
            results (dict): The results of the layer generation.
        """
        self.view.progressBar.setRange(0, 1)
        filenames = [os.path.join(self.model.get_base_path(), self.config_manager.get_relative_path("net_building_transfer_station_path")), 
                     os.path.join(self.model.get_base_path(), self.config_manager.get_relative_path("net_return_pipes_path")),
                     os.path.join(self.model.get_base_path(), self.config_manager.get_relative_path("net_flow_pipes_path")), 
                     os.path.join(self.model.get_base_path(), self.config_manager.get_relative_path("net_heat_sources_path"))]
        
        self.add_geojson_layer(filenames)
        
        generatedLayers = {
            'HAST': os.path.join(self.model.get_base_path(), self.config_manager.get_relative_path("net_building_transfer_station_path")),
            'Rücklauf': os.path.join(self.model.get_base_path(), self.config_manager.get_relative_path("net_return_pipes_path")),
            'Vorlauf': os.path.join(self.model.get_base_path(), self.config_manager.get_relative_path("net_flow_pipes_path")),
            'Erzeugeranlagen': os.path.join(self.model.get_base_path(), self.config_manager.get_relative_path("net_heat_sources_path"))
            }
        
        self.layers_imported.emit(generatedLayers)

    def on_generation_error(self, error_message):
        """
        Handles errors that occur during the layer generation process.

        Args:
            error_message (str): The error message to display.
        """
        self.view.show_error_message("Berechnungsfehler", error_message)
        self.view.progressBar.setRange(0, 1)

    def open_osm_data_dialog(self):
        """
        Opens the dialog for downloading OSM data.
        """
        dialog = DownloadOSMDataDialog(self.model.get_base_path(), self.config_manager, self.view, self)
        if dialog.exec_() == QDialog.Accepted:
            pass  # Handle accepted case if necessary

    def open_osm_building_query_dialog(self):
        """
        Opens the dialog for querying OSM building data.
        """
        dialog = OSMBuildingQueryDialog(self.model.get_base_path(), self.config_manager, self.view, self)
        if dialog.exec_() == QDialog.Accepted:
            pass  # Handle accepted case if necessary

class VisualizationTabView(QWidget):
    """
    The VisualizationTabView class is responsible for managing the user interface components
    such as the map display, menus, buttons, and progress bar.

    Attributes:
        web_view (QWebEngineView): The web view used to render the map.
        menuBar (QMenuBar): The menu bar containing various actions.
        layerList (QListWidget): The list widget displaying the layers.
        removeLayerButton (QPushButton): The button to remove selected layers.
        changeColorButton (QPushButton): The button to change the color of a selected layer.
        progressBar (QProgressBar): The progress bar used to display the progress of operations.
    """

    def __init__(self, model, parent=None):
        """Initializes the VisualizationTabView with the necessary UI components."""
        super().__init__(parent)
        self.model = model
        self.initUI()

    def initUI(self):
        """Initializes the user interface components."""
        self.main_layout = QVBoxLayout()

        self.initMenuBar()
        self.initMapView()

        self.progressBar = QProgressBar(self)
        self.main_layout.addWidget(self.progressBar)

        self.setLayout(self.main_layout)

    def initMenuBar(self):
        self.menuBar = QMenuBar(self)
        self.menuBar.setFixedHeight(30)
        fileMenu = self.menuBar.addMenu('Datei')

        self.downloadAction = QAction('Adressdaten geocodieren', self)
        fileMenu.addAction(self.downloadAction)

        self.loadCsvAction = QAction('CSV-Koordinaten laden', self)
        fileMenu.addAction(self.loadCsvAction)

        self.downloadActionOSM = QAction('OSM Straßenabfrage', self)
        fileMenu.addAction(self.downloadActionOSM)

        self.osmBuildingAction = QAction('OSM Gebäudeabfrage', self)
        fileMenu.addAction(self.osmBuildingAction)
        
        self.importAction = QAction('Import geojson-Datei', self)
        fileMenu.addAction(self.importAction)

        self.layerGenerationAction = QAction('Wärmenetz aus Daten generieren', self)
        fileMenu.addAction(self.layerGenerationAction)

        self.main_layout.addWidget(self.menuBar)

    def initMapView(self):
        """
        Initializes the map view with the WebEngine and sets up the WebChannel.
        """
        self.web_view = QWebEngineView()
        
        # HTML-Karte wird geladen (Annahme: HTML-Datei ist vorbereitet)
        self.map_file_path = self.model.get_resource_path("gui/PyQt5_leaflet/map.html")
        print(self.map_file_path)
        #self.map_file_path = os.path.join(os.getcwd(), 'src\\districtheatingsim\\gui\\PyQt5_leaflet\\map.html')
        self.web_view.setUrl(QUrl.fromLocalFile(self.map_file_path))

        # Erstelle den WebChannel und registriere das Python-Objekt
        self.channel = QWebChannel()
        self.receiver = GeoJsonReceiver()
        self.channel.registerObject('pywebchannel', self.receiver)
        self.web_view.page().setWebChannel(self.channel)

        # Füge das WebView in das Layout ein
        self.main_layout.addWidget(self.web_view)

    def update_map_view(self, map_obj):
        """
        Updates the map view by reloading the WebEngine with new map data.
        """
        # Verwende eine temporäre Datei für die HTML-Karte, falls es notwendig ist
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as temp_file:
            temp_file_path = temp_file.name
            map_obj.save(temp_file_path)

        self.web_view.load(QUrl.fromLocalFile(temp_file_path))

    def show_error_message(self, title, message):
        """
        Displays an error message in a message box.

        Args:
            title (str): The title of the error message box.
            message (str): The error message to display.
        """
        QMessageBox.critical(self, title, message)

class VisualizationTabLeaflet(QMainWindow):
    """
    The VisualizationTab class integrates the model, view, and presenter
    into a single main window for the application.

    Attributes:
        model (VisualizationModel): The model instance containing the data logic.
        view (VisualizationTabView): The view instance containing the UI logic.
        presenter (VisualizationPresenter): The presenter instance handling the interaction between model and view.
    """

    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        """
        Initializes the VisualizationTab with the given data manager.

        Args:
            folder_manager (FolderManager): The folder manager instance handling project paths.
            data_manager (DataManager): The data manager instance handling project-related data.
            config_manager (ConfigManager): The config manager instance managing configuration settings.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        # Initialize Model, View, and Presenter
        self.model = VisualizationModel()
        self.view = VisualizationTabView(self.model)
        self.presenter = VisualizationPresenter(self.model, self.view, folder_manager, data_manager, config_manager)

        # Set the central widget to the view
        self.setCentralWidget(self.view)
