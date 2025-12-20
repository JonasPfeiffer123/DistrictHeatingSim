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
from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema

from shapely.geometry import Point

class GeoJsonReceiver(QObject):
    """
    Bridge for receiving GeoJSON data from JavaScript.
    """
    coordinate_picked = pyqtSignal(float, float)
    polygon_drawn = pyqtSignal(dict)
    polygon_ready = pyqtSignal()
    
    def __init__(self, base_path=""):
        """Initialize GeoJsonReceiver with base path.
        
        Parameters
        ----------
        base_path : str, optional
            Base path for file dialogs.
        """
        super().__init__()
        self.base_path = base_path
    
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
        fileName, _ = QFileDialog.getSaveFileName(None, "Save GeoJSON File", self.base_path, "GeoJSON Files (*.geojson);;All Files (*)")
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
                # Erstelle GeoDataFrame mit expliziter Geometrie
                from shapely.geometry import shape
                geometries = [shape(feature['geometry']) for feature in features]
                
                # Stelle sicher dass jedes Feature properties hat
                properties_list = []
                for feature in features:
                    props = feature.get('properties', {})
                    if props is None:
                        props = {}
                    properties_list.append(props)
                
                gdf = gpd.GeoDataFrame(properties_list, geometry=geometries, crs='EPSG:4326')
                
                # Transformiere zu Ziel-CRS
                target_crs = 'EPSG:25833'
                gdf.to_crs(target_crs, inplace=True)
                gdf.to_file(fileName, driver="GeoJSON")
                print(f"GeoJSON-Datei gespeichert: {fileName}")
            except Exception as e:
                print("Fehler beim Erstellen des GeoDataFrame:", e)
                import traceback
                traceback.print_exc()
    
    @pyqtSlot(str)
    def exportUnifiedNetworkGeoJSON(self, geojsonString):
        """
        Export edited network in unified format, preserving protected data.
        
        This merges edited geometries from the map with protected building
        data to create a complete unified network GeoJSON.

        Parameters
        ----------
        geojsonString : str
            GeoJSON data from map (edited geometries).
        """
        fileName, _ = QFileDialog.getSaveFileName(
            None, 
            "Export Unified Network GeoJSON", 
            self.base_path, 
            "GeoJSON Files (*.geojson);;All Files (*)"
        )
        
        if not fileName:
            return
        
        try:
            from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema
            
            geojson_data = json.loads(geojsonString)
            
            # Check if this is already unified format
            if geojson_data.get("metadata", {}).get("version") == NetworkGeoJSONSchema.VERSION:
                # Just save as-is
                with open(fileName, 'w', encoding='utf-8') as f:
                    json.dump(geojson_data, f, indent=2, ensure_ascii=False)
                print(f"✓ Exported unified network GeoJSON: {fileName}")
            else:
                # Convert to unified format (if needed, can implement merge logic here)
                print("Converting to unified format...")
                with open(fileName, 'w', encoding='utf-8') as f:
                    json.dump(geojson_data, f, indent=2, ensure_ascii=False)
                print(f"✓ Exported GeoJSON: {fileName}")
                
        except Exception as e:
            print(f"✗ Export failed: {e}")
            import traceback
            traceback.print_exc()
    
    @pyqtSlot(str, str)
    def saveEditedNetwork(self, geojsonString, filepath):
        """
        Save edited network back to unified GeoJSON file.
        
        Merges edited geometries from map with original protected data.
        This is called when user saves changes in the map.

        Parameters
        ----------
        geojsonString : str
            Edited GeoJSON data from map.
        filepath : str
            Path to save the network.
        """
        try:
            from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema
            
            edited_data = json.loads(geojsonString)
            
            # If already in unified format, just save
            if edited_data.get("metadata", {}).get("version") == NetworkGeoJSONSchema.VERSION:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(edited_data, f, indent=2, ensure_ascii=False)
                print(f"✓ Saved edited network: {filepath}")
            else:
                # Legacy format - just save as-is
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(edited_data, f, indent=2, ensure_ascii=False)
                print(f"✓ Saved GeoJSON: {filepath}")
                
        except Exception as e:
            print(f"✗ Save failed: {e}")
            import traceback
            traceback.print_exc()

    @pyqtSlot(float, float)
    def receiveCoordinateFromMap(self, lat, lon):
        """Receive coordinate from map click.
        
        Parameters
        ----------
        lat : float
            Latitude (WGS84).
        lon : float
            Longitude (WGS84).
        """
        print(f"Received coordinates from map: Lat={lat}, Lon={lon}")
        self.coordinate_picked.emit(lat, lon)

    @pyqtSlot()
    def polygonReadyForCapture(self):
        """Signal that polygon has been drawn and is ready for capture."""
        self.polygon_ready.emit()


    @pyqtSlot(str)
    def receivePolygonFromMap(self, geojson_str):
        """Receive polygon GeoJSON from map drawing.
        
        Parameters
        ----------
        geojson_str : str
            GeoJSON string of the drawn polygon.
        """
        print(f"Received polygon from map")
        try:
            geojson_data = json.loads(geojson_str)
            self.polygon_drawn.emit(geojson_data)
        except Exception as e:
            print(f"Error parsing polygon GeoJSON: {e}")

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
        self.view.saveNetworkAction.triggered.connect(self.save_network)
        
        # Track current unified network file
        self.current_unified_network = None

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
            self.view.set_base_path(new_base_path)

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
                
                # Check if this is a unified network GeoJSON
                if self._is_unified_network_geojson(geojson_data):
                    print(f"Loading unified network GeoJSON: {filename}")
                    self._load_unified_network_geojson(geojson_data, filepath=filename)
                else:
                    # Legacy format - add as single layer
                    layer_json = json.dumps(geojson_data)
                    self.view.web_view.page().runJavaScript(f"window.importGeoJSON({layer_json}, '{layer_name}');")

        except Exception as e:
            error_message = f"{str(e)}\n\n{traceback.format_exc()}"
            self.view.show_error_message("Fehler beim Hinzufügen einer GeoJSON-Schicht", error_message)
    
    def _is_unified_network_geojson(self, geojson_data):
        """
        Check if GeoJSON is unified network format.
        
        Parameters
        ----------
        geojson_data : dict
            GeoJSON data
            
        Returns
        -------
        bool
            True if unified format
        """
        if geojson_data.get("type") != "FeatureCollection":
            return False
        
        # Check for metadata marker
        metadata = geojson_data.get("metadata", {})
        if "version" in metadata and metadata["version"] == NetworkGeoJSONSchema.VERSION:
            return True
        
        # Check if features have feature_type property
        features = geojson_data.get("features", [])
        if features and "feature_type" in features[0].get("properties", {}):
            return True
        
        return False
    
    def _load_unified_network_geojson(self, geojson_data, filepath=None):
        """
        Load unified network GeoJSON and add layers to map.
        
        Parameters
        ----------
        geojson_data : dict
            Unified network GeoJSON
        filepath : str, optional
            Path to the loaded file (for saving later)
        """
        # Separate features by type
        flow_features = []
        return_features = []
        building_features = []
        generator_features = []
        
        for feature in geojson_data.get("features", []):
            ftype = feature["properties"].get("feature_type")
            
            if ftype == NetworkGeoJSONSchema.FEATURE_TYPE_FLOW:
                flow_features.append(feature)
            elif ftype == NetworkGeoJSONSchema.FEATURE_TYPE_RETURN:
                return_features.append(feature)
            elif ftype == NetworkGeoJSONSchema.FEATURE_TYPE_BUILDING:
                building_features.append(feature)
            elif ftype == NetworkGeoJSONSchema.FEATURE_TYPE_GENERATOR:
                generator_features.append(feature)
        
        # Create separate layers for each type with editable flags
        layers = [
            ("Vorlauf", flow_features, True),
            ("Rücklauf", return_features, True),
            ("HAST", building_features, False),
            ("Erzeugeranlagen", generator_features, False)
        ]
        
        # Get CRS from original GeoJSON
        crs = geojson_data.get("crs", {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:EPSG::25833"
            }
        })
        
        for layer_name, features, editable in layers:
            if features:
                layer_geojson = {
                    "type": "FeatureCollection",
                    "crs": crs,  # Include CRS in each layer
                    "features": features
                }
                layer_json = json.dumps(layer_geojson)
                
                # Pass editable flag to JavaScript
                self.view.web_view.page().runJavaScript(
                    f"window.importGeoJSON({layer_json}, '{layer_name}', {str(editable).lower()});"
                )
                print(f"✓ Loaded layer '{layer_name}': {len(features)} features (editable: {editable})")
        
        # Store filepath for saving
        if filepath:
            self.current_unified_network = filepath
            self.view.saveNetworkAction.setEnabled(True)

    def open_layer_generation_dialog(self):
        """Open dialog for generating layers from data."""
        dialog = LayerGenerationDialog(self.model.get_base_path(), self.config_manager, self.view)
        dialog.setVisualizationTab(self)
        dialog.accepted_inputs.connect(self.generate_and_import_layers)
        
        # Connect map picker signals
        dialog.request_map_coordinate.connect(self.activate_map_coordinate_picker)
        self.view.geoJsonReceiver.coordinate_picked.connect(dialog.receiveMapCoordinates)
        
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
        
        # Try to load unified network GeoJSON first
        unified_path = os.path.join(
            self.model.get_base_path(), 
            self.config_manager.get_relative_path('dimensioned_net_path')
        )
        
        print(f"Checking for unified GeoJSON at: {unified_path}")
        print(f"File exists: {os.path.exists(unified_path)}")
        
        if os.path.exists(unified_path):
            print(f"Loading unified network GeoJSON: {unified_path}")
            self.add_geojson_layer([unified_path])
            
            # Store reference to unified file
            self.current_unified_network = unified_path
            
            # Enable save action
            self.view.saveNetworkAction.setEnabled(True)
            
            generatedLayers = {
                'Wärmenetz': unified_path
            }
        else:
            # Unified file not found
            print(f"Unified network file not found: {unified_path}")
            self.view.show_error_message(
                "Netzwerk nicht gefunden", 
                f"Die Wärmenetz.geojson Datei wurde nicht gefunden:\n{unified_path}"
            )
            return
        
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
    
    def save_network(self):
        """
        Save edited network back to unified GeoJSON file.
        
        Requests current network data from JavaScript and saves to file.
        """
        if not self.current_unified_network:
            QMessageBox.warning(
                self.view,
                "Kein Netzwerk geladen",
                "Es ist kein unified Netzwerk geladen, das gespeichert werden kann."
            )
            return
        
        # Request network data from JavaScript
        # The JavaScript should call saveEditedNetwork with the current data
        self.view.web_view.page().runJavaScript(
            f"""
            if (typeof getAllLayersAsGeoJSON === 'function') {{
                var geojson = getAllLayersAsGeoJSON();
                if (window.qt && window.qt.webChannelTransport) {{
                    new QWebChannel(window.qt.webChannelTransport, function(channel) {{
                        channel.objects.geoJsonReceiver.saveEditedNetwork(
                            JSON.stringify(geojson),
                            '{self.current_unified_network.replace(chr(92), chr(92)+chr(92))}'
                        );
                    }});
                }}
            }} else {{
                console.error('getAllLayersAsGeoJSON function not found');
            }}
            """
        )
        print(f"Requested save of network to: {self.current_unified_network}")

    def activate_map_coordinate_picker(self):
        """Activate map coordinate picker mode by calling JavaScript."""
        self.view.web_view.page().runJavaScript("activateCoordinatePicker();")

    def open_osm_data_dialog(self):
        """Open dialog for downloading OSM data."""
        dialog = DownloadOSMDataDialog(self.model.get_base_path(), self.config_manager, self.view, self)
        dialog.setVisualizationTab(self)
        dialog.show()  # Non-modal dialog - allows map interaction
        dialog.raise_()
        dialog.activateWindow()

    def open_osm_building_query_dialog(self):
        """Open dialog for querying OSM building data."""
        dialog = OSMBuildingQueryDialog(
            self.model.get_base_path(), 
            self.config_manager, 
            self.view, 
            self, 
            visualization_tab=self
        )
        dialog.show()  # Non-modal dialog - allows map interaction
        dialog.raise_()
        dialog.activateWindow()

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
        
        fileMenu.addSeparator()
        
        self.saveNetworkAction = QAction('Netzwerk speichern', self)
        self.saveNetworkAction.setEnabled(False)  # Initially disabled
        fileMenu.addAction(self.saveNetworkAction)

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

    def set_base_path(self, base_path):
        """Set base path for GeoJsonReceiver.
        
        Parameters
        ----------
        base_path : str
            Base path for file dialogs.
        """
        if hasattr(self, 'geoJsonReceiver'):
            self.geoJsonReceiver.base_path = base_path
    
    def show_error_message(self, title, message):
        """
        Show error message dialog.

        Parameters
        ----------
        title : str
            Dialog title.
        message : str
            Error message text.
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
        
        # Set base path for GeoJsonReceiver after presenter is initialized
        self.view.set_base_path(self.model.get_base_path())

        # Set the central widget to the view
        self.setCentralWidget(self.view)
    
    def update_base_path(self, base_path):
        """Update base path in model and view.
        
        Parameters
        ----------
        base_path : str
            New base path for project.
        """
        self.model.set_base_path(base_path)
        self.view.set_base_path(base_path)