"""
Leaflet Tab Module
==================

Leaflet map integration for district heating network visualization.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-01-26
"""

import os
import sys
import json
import geopandas as gpd
import pandas as pd
import traceback
import os
import tempfile

from PyQt6.QtWidgets import QVBoxLayout, QWidget, QFileDialog, QMenuBar, QProgressBar, QMessageBox, QMainWindow, QDialog
from PyQt6.QtGui import QAction
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtCore import QUrl, QObject, pyqtSlot, pyqtSignal
from PyQt6.QtWebChannel import QWebChannel

from districtheatingsim.gui.LeafletTab.leaflet_dialogs import LayerGenerationDialog, DownloadOSMDataDialog, OSMBuildingQueryDialog
from districtheatingsim.gui.LeafletTab.net_generation_threads import NetGenerationThread, FileImportThread, GeocodingThread

from shapely.geometry import Point

class GeoJsonReceiver(QObject):
    """
    Bridge for receiving GeoJSON data from JavaScript.
    """
    
    @pyqtSlot(str)
    def sendGeoJSONToPython(self, geojson_str):
        """
        Receive GeoJSON from JavaScript and save to file.

        Parameters
        ----------
        geojson_str : str
            GeoJSON data as string.
        """
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
        output_file = 'exported_data.geojson' ### Replace with path dialog
        gdf.to_file(output_file, driver="GeoJSON")
        print(f"GeoJSON gespeichert in {output_file}")

    @pyqtSlot(str)
    def exportGeoJSON(self, geojsonString):
        """
        Export GeoJSON with file dialog.

        Parameters
        ----------
        geojsonString : str
            GeoJSON data as string.
        """
        fileName, _ = QFileDialog.getSaveFileName(None, "Save GeoJSON File", "", "GeoJSON Files (*.geojson);;All Files (*)")
        if fileName:
            geojson_data = json.loads(geojsonString)

            # Robust: FeatureCollection oder einzelnes Feature akzeptieren
            if geojson_data.get("type") == "FeatureCollection":
                features = geojson_data["features"]
            elif geojson_data.get("type") == "Feature":
                features = [geojson_data]
            else:
                print("Unbekannter GeoJSON-Typ:", geojson_data.get("type"))
                return

            # Debug: Zeige die Geometrie-Typen und Koordinaten
            for i, feature in enumerate(features):
                print(f"Feature {i}: type={feature['geometry']['type']}, coords={feature['geometry']['coordinates']}")

            # Optional: Korrigiere fehlerhafte Geometrien
            for feature in features:
                geom_type = feature["geometry"]["type"]
                coords = feature["geometry"]["coordinates"]
                # Beispiel: LineString mit verschachtelten Koordinaten (sollte flach sein)
                if geom_type == "LineString" and any(isinstance(c, list) and isinstance(c[0], list) for c in coords):
                    # Flache Liste erzeugen
                    feature["geometry"]["coordinates"] = [pt for sub in coords for pt in sub]
                if geom_type == "LineString":
                    feature["geometry"]["coordinates"] = [c[:2] if len(c) > 2 else c for c in feature["geometry"]["coordinates"]]
                elif geom_type == "Point":
                    feature["geometry"]["coordinates"] = feature["geometry"]["coordinates"][:2]
                elif geom_type == "Polygon":
                    feature["geometry"]["coordinates"] = [
                        [c[:2] if len(c) > 2 else c for c in ring]
                        for ring in feature["geometry"]["coordinates"]
                    ]
            try:
                gdf = gpd.GeoDataFrame.from_features(features)
                gdf.set_crs(epsg=4326, inplace=True)
                target_crs = 'EPSG:25833'
                gdf.to_crs(target_crs, inplace=True)
                gdf.to_file(fileName, driver="GeoJSON")
                print(f"GeoJSON-Datei gespeichert: {fileName}")
            except Exception as e:
                print("Fehler beim Erstellen des GeoDataFrame:", e)
                import traceback
                traceback.print_exc()
        else:
            print("Speichern abgebrochen.")

class VisualizationModel:
    """
    Data model for map visualization operations.
    """

    def __init__(self):
        """Initialize model with empty layers and base path."""
        self.layers = {}
        self.base_path = ""

    def set_base_path(self, base_path):
        """
        Set base path for file operations.

        Parameters
        ----------
        base_path : str
            Base path to set.
        """
        self.base_path = base_path

    def get_base_path(self):
        """
        Get current base path.

        Returns
        -------
        str
            Current base path.
        """
        return self.base_path

    def load_geojson(self, file_path):
        """
        Load GeoJSON file as GeoDataFrame.

        Parameters
        ----------
        file_path : str
            Path to GeoJSON file.

        Returns
        -------
        GeoDataFrame
            Loaded GeoJSON data.
        """
        return gpd.read_file(file_path)

    def create_geojson_from_csv(self, csv_file_path, geojson_file_path):
        """
        Create GeoJSON from CSV with coordinates.

        Parameters
        ----------
        csv_file_path : str
            Path to CSV file.
        geojson_file_path : str
            Output GeoJSON path.
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
        Get absolute path to resource.

        Parameters
        ----------
        relative_path : str
            Relative path to resource.

        Returns
        -------
        str
            Absolute path to resource.
        """
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_path, relative_path)

class VisualizationPresenter(QObject):
    """
    Presenter mediating between model and view for map visualization.
    """

    layers_imported = pyqtSignal(dict)

    def __init__(self, model, view, folder_manager, data_manager, config_manager):
        """
        Initialize presenter with model, view, and managers.

        Parameters
        ----------
        model : VisualizationModel
            Model instance.
        view : VisualizationTabView
            View instance.
        folder_manager : FolderManager
            Folder manager instance.
        data_manager : DataManager
            Data manager instance.
        config_manager : ConfigManager
            Configuration manager instance.
        """
        super().__init__()
        self.model = model
        self.view = view
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

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
        if self.folder_manager.variant_folder:
            self.on_project_folder_changed(self.folder_manager.variant_folder)

        # HTML-Karte wird geladen (Annahme: HTML-Datei ist vorbereitet)
        self.map_file_path = self.model.get_resource_path("leaflet\\map.html")
        self.view.web_view.setUrl(QUrl.fromLocalFile(self.map_file_path))

    def on_project_folder_changed(self, new_base_path):
        """
        Update base path when project folder changes.

        Parameters
        ----------
        new_base_path : str
            New base path.
        """
        if new_base_path:
            self.model.set_base_path(new_base_path)

    def open_geocode_addresses_dialog(self):
        """Open dialog to select CSV file for geocoding addresses."""
        fname, _ = QFileDialog.getOpenFileName(self.view, 'CSV-Koordinaten laden', self.model.get_base_path(), 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.geocode_addresses(fname)

    def geocode_addresses(self, inputfilename):
        """
        Start geocoding process for CSV file.

        Parameters
        ----------
        inputfilename : str
            Path to CSV file.
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
        Handle successful geocoding completion.

        Parameters
        ----------
        fname : str
            Path to generated CSV file.
        """
        self.view.progressBar.setRange(0, 1)
        self.load_csv_coordinates(fname)

    def on_geocode_error(self, error_message):
        """
        Handle geocoding errors.

        Parameters
        ----------
        error_message : str
            Error message.
        """
        self.view.show_error_message("Fehler beim Geocoding", error_message)
        self.view.progressBar.setRange(0, 1)

    def load_csv_coordinates(self, fname=None):
        """
        Load coordinates from CSV and add to map.

        Parameters
        ----------
        fname : str, optional
            CSV file path.
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
        """Import GeoJSON files and add to map."""
        try:
            fnames, _ = QFileDialog.getOpenFileNames(self.view, 'Netzdaten importieren', self.model.get_base_path(), 'GeoJSON Files (*.geojson);;All Files (*)')
            if fnames:
                self.add_geojson_layer(fnames)
        except Exception as e:
            error_message = f"{str(e)}\n\n{traceback.format_exc()}"
            self.view.show_error_message("Fehler beim Importieren von GeoJSON", error_message)

    def add_geojson_layer(self, filenames):
        """
        Add GeoJSON layers to map.

        Parameters
        ----------
        filenames : list
            List of GeoJSON file paths.
        """
        try:
            for filename in filenames:
                # Add the layer to the model
                layer_name = os.path.splitext(os.path.basename(filename))[0]

                # Read as UTF-8 to avoid encoding issues
                with open(filename, 'r', encoding='utf-8') as f:
                    geojson_data = json.load(f)

                # Pass the layers data to JavaScript via the WebChannel
                layer_json = json.dumps(geojson_data)
                self.view.web_view.page().runJavaScript(f"window.importGeoJSON({layer_json}, '{layer_name}');")

        except Exception as e:
            error_message = f"{str(e)}\n\n{traceback.format_exc()}"
            self.view.show_error_message("Fehler beim Hinzufügen einer GeoJSON-Schicht", error_message)

    def open_layer_generation_dialog(self):
        """Open dialog for generating layers from data."""
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
        Start layer generation process.

        Parameters
        ----------
        inputs : dict
            Generation inputs.
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
        Handle successful layer generation.

        Parameters
        ----------
        results : dict
            Generation results.
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
        Handle layer generation errors.

        Parameters
        ----------
        error_message : str
            Error message.
        """
        self.view.show_error_message("Berechnungsfehler", error_message)
        self.view.progressBar.setRange(0, 1)

    def open_osm_data_dialog(self):
        """Open dialog for downloading OSM data."""
        dialog = DownloadOSMDataDialog(self.model.get_base_path(), self.config_manager, self.view, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            pass  # Handle accepted case if necessary

    def open_osm_building_query_dialog(self):
        """Open dialog for querying OSM building data."""
        dialog = OSMBuildingQueryDialog(self.model.get_base_path(), self.config_manager, self.view, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            pass  # Handle accepted case if necessary

class VisualizationTabView(QWidget):
    """
    View component for map visualization interface.
    """

    def __init__(self, parent=None):
        """
        Initialize view with UI components.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        """Initialize user interface components."""
        self.main_layout = QVBoxLayout()

        self.initMenuBar()
        self.initMapView()

        self.progressBar = QProgressBar(self)
        self.main_layout.addWidget(self.progressBar)

        self.setLayout(self.main_layout)

    def initMenuBar(self):
        """Initialize menu bar with actions."""
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
        """Initialize map view with WebEngine and WebChannel."""
        self.web_view = QWebEngineView()
        
        # Configure WebEngine settings to allow mixed content and local requests
        settings = self.web_view.page().settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript, True)
        
        # Erstelle den WebChannel und registriere das Python-Objekt
        self.channel = QWebChannel()
        self.geoJsonReceiver = GeoJsonReceiver()
        self.channel.registerObject("geoJsonReceiver", self.geoJsonReceiver)
        self.web_view.page().setWebChannel(self.channel)

        # Füge das WebView in das Layout ein
        self.main_layout.addWidget(self.web_view)

    def update_map_view(self, map_obj):
        """
        Update map view with new data.

        Parameters
        ----------
        map_obj : object
            Map object to display.
        """
        # Verwende eine temporäre Datei für die HTML-Karte, falls es notwendig ist
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as temp_file:
            temp_file_path = temp_file.name
            map_obj.save(temp_file_path)

        self.web_view.load(QUrl.fromLocalFile(temp_file_path))

    def show_error_message(self, title, message):
        """
        Show error message dialog.

        Parameters
        ----------
        title : str
            Dialog title.
        message : str
            Error message.
        """
        QMessageBox.critical(self, title, message)

class VisualizationTabLeaflet(QMainWindow):
    """
    Main window integrating model, view, and presenter for map visualization.
    """

    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        """
        Initialize visualization tab with managers.

        Parameters
        ----------
        folder_manager : FolderManager
            Folder manager instance.
        data_manager : DataManager
            Data manager instance.
        config_manager : ConfigManager
            Configuration manager instance.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)

        # Initialize Model, View, and Presenter
        self.model = VisualizationModel()
        self.view = VisualizationTabView()
        self.presenter = VisualizationPresenter(self.model, self.view, folder_manager, data_manager, config_manager)

        # Set the central widget to the view
        self.setCentralWidget(self.view)