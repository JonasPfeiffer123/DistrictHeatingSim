"""
Filename: PyQt5_Leaflet.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-19
Description: Contains the LeafTab class for displaying a Leaflet map in a PyQt5 application.
"""

import sys
import os
import json
import geopandas as gpd
import pandas as pd
import random
import traceback
import os
import tempfile

from PyQt5.QtWidgets import QApplication, QVBoxLayout, QPushButton, QWidget, QFileDialog, QHBoxLayout, QMenuBar, QAction, QListWidget, QProgressBar, QMessageBox, QMainWindow, QDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QObject, pyqtSlot, pyqtSignal
from PyQt5.QtWebChannel import QWebChannel

from gui.VisualizationTab.visualization_dialogs import LayerGenerationDialog, DownloadOSMDataDialog, OSMBuildingQueryDialog, GeocodeAddressesDialog
from gui.VisualizationTab.net_generation_threads import NetGenerationThread, FileImportThread, GeocodingThread

from shapely.geometry import Point

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

    def calculate_map_center_and_zoom(self):
        """
        Calculate the center and zoom level for the map based on the loaded layers.

        Returns:
            list: Center coordinates [latitude, longitude].
            int: Zoom level.
        """
        if not self.layers:
            return [51.1657, 10.4515], 6  # Default center for Germany if no layers are loaded

        minx, miny, maxx, maxy = None, None, None, None
        for layer_name, layer_data in self.layers.items():
            geojson_file_path = layer_data['file_path']
            try:
                gdf = gpd.read_file(geojson_file_path)
                bounds = gdf.total_bounds  # Get [minx, miny, maxx, maxy] of all features in the GeoDataFrame

                # Update min and max bounds
                if minx is None or bounds[0] < minx:
                    minx = bounds[0]
                if miny is None or bounds[1] < miny:
                    miny = bounds[1]
                if maxx is None or bounds[2] > maxx:
                    maxx = bounds[2]
                if maxy is None or bounds[3] > maxy:
                    maxy = bounds[3]
            except Exception as e:
                print(f"Error loading GeoJSON file {geojson_file_path}: {e}")

        # Calculate center and set a default zoom level
        center_x = (minx + maxx) / 2
        center_y = (miny + maxy) / 2
        zoom = 17

        return [center_x, center_y], zoom

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

        # Set up folder change handling
        self.folder_manager.project_folder_changed.connect(self.on_project_folder_changed)

        # Connect UI actions to methods
        self.view.downloadAction.triggered.connect(self.open_geocode_addresses_dialog)
        self.view.loadCsvAction.triggered.connect(self.load_csv_coordinates)
        self.view.importAction.triggered.connect(self.import_geojson)
        self.view.removeLayerButton.clicked.connect(self.remove_selected_layer)
        self.view.layerGenerationAction.triggered.connect(self.open_layer_generation_dialog)
        self.view.downloadActionOSM.triggered.connect(self.open_osm_data_dialog)
        self.view.osmBuildingAction.triggered.connect(self.open_osm_building_query_dialog)

        # Initialize map view
        self.on_project_folder_changed(self.folder_manager.variant_folder)
        self.update_map_view()

    def update_map_view(self):
        """
        Updates the map view by sending layer data to JavaScript using WebChannel.
        """
        try:
            # Calculate center and zoom level
            center, zoom = self.model.calculate_map_center_and_zoom()

            # Prepare each layer to send to JavaScript
            layers_data = []
            geojson_filenames = []
            for layer_name, layer in self.model.layers.items():
                geojson_file_path = os.path.join(self.model.get_base_path(), 'Gebäudedaten', f"{layer_name}.geojson")
                with open(geojson_file_path, 'r') as f:
                    geojson_data = json.load(f)
                
                # Create a data structure to hold the layer data
                layers_data.append({
                    "name": layer_name,
                    "geojson": geojson_data,
                    "color": layer.get("style", {}).get("color", "#3388FF")
                })

                geojson_filenames.append(geojson_file_path.split('/')[-1])

            # Pass the layers data to JavaScript via the WebChannel
            layers_json = json.dumps(layers_data)
            self.view.web_view.page().runJavaScript(f"window.importGeoJSON({layers_json}, '{geojson_filenames}');")

        except Exception as e:
            error_message = f"{str(e)}\n\n{traceback.format_exc()}"
            self.view.show_error_message("Fehler beim Laden der Daten", error_message)

    def load_csv_coordinates(self):
        """
        Loads coordinates from a CSV file and adds them as a GeoJSON layer to the map.
        """
        try:
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

    def add_geojson_layer(self, filenames, color=None):
        """
        Adds GeoJSON layers to the map.

        Args:
            filenames (list): A list of GeoJSON file paths.
            color (str, optional): The color to use for the layer.
        """
        try:
            color = color or "#{:06x}".format(random.randint(0, 0xFFFFFF))
            for filename in filenames:
                # Add the layer to the model
                layer_name = os.path.splitext(os.path.basename(filename))[0]
                self.model.layers[layer_name] = {"file_path": filename, "color": color}

            # Update map view to reflect the added layers
            self.update_map_view()

        except Exception as e:
            error_message = f"{str(e)}\n\n{traceback.format_exc()}"
            self.view.show_error_message("Fehler beim Hinzufügen einer GeoJSON-Schicht", error_message)

    def on_project_folder_changed(self, new_base_path):
        """
        Updates the base path in the model when the project folder changes.

        Args:
            new_base_path (str): The new base path.
        """
        self.model.set_base_path(new_base_path)

    def remove_selected_layer(self):
        """
        Removes the selected layer from the map and updates the view.
        """
        selectedItems = self.view.layerList.selectedItems()
        if selectedItems:
            selectedItem = selectedItems[0]
            layer_name = selectedItem.text()

            # Entferne den Layer aus dem Modell
            if layer_name in self.model.layers:
                del self.model.layers[layer_name]

            # Entferne den Layer aus der Ansicht und sende das Entfernen an JavaScript
            self.view.layerList.takeItem(self.view.layerList.row(selectedItem))
            self.view.web_view.page().runJavaScript(f"window.removeLayer('{layer_name}');")

            # Aktualisiere die Karte
            self.update_map_view()

    def open_geocode_addresses_dialog(self):
        """
        Opens the dialog for geocoding addresses from a CSV file.
        """
        dialog = GeocodeAddressesDialog(self.model.get_base_path(), self.config_manager, self.view)
        if dialog.exec_() == QDialog.Accepted:
            fname = dialog.get_file_name()
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

    def __init__(self, parent=None):
        """Initializes the VisualizationTabView with the necessary UI components."""
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        """Initializes the user interface components."""
        self.main_layout = QVBoxLayout()

        self.initMenuBar()
        self.initMapView()
        self.initLayerManagement()

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
        map_file_path = os.path.join(os.getcwd(), 'src\\districtheatingsim\\gui\\PyQt5_leaflet\\map.html')
        self.web_view.setUrl(QUrl.fromLocalFile(map_file_path))

        # Erstelle den WebChannel und registriere das Python-Objekt
        self.channel = QWebChannel()
        self.receiver = GeoJsonReceiver()
        self.channel.registerObject('pywebchannel', self.receiver)
        self.web_view.page().setWebChannel(self.channel)

        # Füge das WebView in das Layout ein
        self.main_layout.addWidget(self.web_view)

    def initLayerManagement(self):
        """
        Initializes the layer management components.
        """
        self.layerList = QListWidget(self)
        self.layerList.setMaximumHeight(100)

        self.removeLayerButton = QPushButton("Layer entfernen", self)

        layerManagementLayout = QHBoxLayout()
        layerManagementLayout.addWidget(self.layerList)
        layerManagementLayout.addWidget(self.removeLayerButton)
        self.main_layout.addLayout(layerManagementLayout)

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
        self.setWindowTitle("Visualization Tab")
        self.setGeometry(100, 100, 800, 600)

        # Initialize Model, View, and Presenter
        self.model = VisualizationModel()
        self.view = VisualizationTabView()
        self.presenter = VisualizationPresenter(self.model, self.view, folder_manager, data_manager, config_manager)

        # Set the central widget to the view
        self.setCentralWidget(self.view)

        # Additional setup for the window if needed
        self.setup_ui()

    def setup_ui(self):
        """
        Sets up additional UI elements and layout properties for the tab if needed.
        """
        # For future customizations or added UI setup logic, if required
        pass

class LeafletTab(QWidget):
    def __init__(self, folder_manager, data_manager, config_manager):
        super().__init__()

        self.setWindowTitle('Leaflet.draw in PyQt5')
        self.showMaximized()

        # Erstelle eine QWebEngineView, um die HTML-Karte anzuzeigen
        self.web_view = QWebEngineView()

        # Lade die HTML-Datei
        map_file_path = os.path.join(os.getcwd(), 'src\\districtheatingsim\\gui\\PyQt5_leaflet\\map.html')
        print(map_file_path)
        self.web_view.setUrl(QUrl.fromLocalFile(map_file_path))

        # Erstelle den WebChannel und registriere das Python-Objekt
        self.channel = QWebChannel()
        self.receiver = GeoJsonReceiver()
        self.channel.registerObject('pywebchannel', self.receiver)
        self.web_view.page().setWebChannel(self.channel)

        # Set up layout
        layout = QVBoxLayout()
        layout.addWidget(self.web_view)
        self.setLayout(layout)

        # Add export button
        export_button = QPushButton('Export GeoJSON')
        export_button.clicked.connect(self.export_geojson)
        layout.addWidget(export_button)

        # Add import button
        import_button = QPushButton('Import GeoJSON')
        import_button.clicked.connect(self.import_geojson)
        layout.addWidget(import_button)

    def export_geojson(self):
        # Ruft die Funktion aus JavaScript auf
        self.web_view.page().runJavaScript("exportGeoJSON()")

    def import_geojson(self):
        # Öffne ein Dialogfeld, um eine GeoJSON-Datei auszuwählen
        options = QFileDialog.Options()
        geojson_file, _ = QFileDialog.getOpenFileName(self, 'Open GeoJSON File', '', 'GeoJSON Files (*.geojson)', options=options)

        # isolating the file name
        geojson_filename = geojson_file.split('/')[-1]

        if geojson_file:
            # Lese den Inhalt der GeoJSON-Datei
            with open(geojson_file, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)

            # Übergebe die GeoJSON-Daten an JavaScript
            geojson_str = json.dumps(geojson_data)
            # geojson_filename is passed to the JavaScript function, necessary for the function to work, transformed to a string
            self.web_view.page().runJavaScript(f"window.importGeoJSON({geojson_str}, '{geojson_filename}');")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LeafletTab()
    window.show()
    sys.exit(app.exec_())