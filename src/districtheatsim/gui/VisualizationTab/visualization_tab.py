"""
Filename: visualization_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-01
Description: Contains the VisualizationTab.
"""

import os
import random
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from PyQt5.QtCore import pyqtSignal, QUrl
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMenuBar, QAction, QFileDialog, \
    QHBoxLayout, QListWidget, QDialog, QProgressBar, QColorDialog, QListWidgetItem, QMessageBox
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWebEngineWidgets import QWebEngineView

import folium

from gui.VisualizationTab.visualization_dialogs import LayerGenerationDialog, DownloadOSMDataDialog, OSMBuildingQueryDialog, SpatialAnalysisDialog, GeocodeAddressesDialog
from gui.threads import NetGenerationThread, FileImportThread, GeocodingThread

class VisualizationTab(QWidget):
    """
    The VisualizationTab class provides a GUI tab for visualizing geographical data using Folium.
    It allows importing and displaying layers from GeoJSON files, generating layers, and performing
    various spatial operations such as geocoding addresses and querying OSM data.
    """
    layers_imported = pyqtSignal(dict)

    def __init__(self, data_manager, parent=None):
        """
        Initialize the VisualizationTab.

        Args:
            data_manager: An object managing data-related operations.
            parent: The parent widget.
        """
        super().__init__(parent)
        self.data_manager = data_manager
        self.layers = {}

        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.project_folder)

        self.initUI()

    def initUI(self):
        """
        Initialize the user interface for the VisualizationTab.
        """
        layout = QVBoxLayout()

        self.m = folium.Map(location=[51.1657, 10.4515], zoom_start=6)
        self.mapView = QWebEngineView()

        self.menuBar = QMenuBar(self)
        self.menuBar.setFixedHeight(30)
        fileMenu = self.menuBar.addMenu('Datei')

        downloadAction = QAction('Adressdaten geocodieren', self)
        downloadAction.triggered.connect(self.openGeocodeAdressesDialog)
        fileMenu.addAction(downloadAction)

        loadCsvAction = QAction('CSV-Koordinaten laden', self)
        loadCsvAction.triggered.connect(self.loadCsvCoordinates)
        fileMenu.addAction(loadCsvAction)

        downloadAction = QAction('OSM Straßenabfrage', self)
        downloadAction.triggered.connect(self.openDownloadOSMDataDialog)
        fileMenu.addAction(downloadAction)

        osmBuildingAction = QAction('OSM Gebäudeabfrage', self)
        osmBuildingAction.triggered.connect(self.openOSMBuildingQueryDialog)
        fileMenu.addAction(osmBuildingAction)

        spatialAnalysisAction = QAction('Clustering Quartiere', self)
        spatialAnalysisAction.triggered.connect(self.openspatialAnalysisDialog)
        fileMenu.addAction(spatialAnalysisAction)

        importAction = QAction('Import geojson-Datei', self)
        importAction.triggered.connect(self.importNetData)
        fileMenu.addAction(importAction)

        downloadAction = QAction('Wärmenetz aus Daten generieren', self)
        downloadAction.triggered.connect(self.openLayerGenerationDialog)
        fileMenu.addAction(downloadAction)

        layout.addWidget(self.menuBar)

        self.updateMapView()
        layout.addWidget(self.mapView)

        self.layerList = QListWidget(self)
        self.layerList.setMaximumHeight(100)

        self.removeLayerButton = QPushButton("Layer entfernen", self)
        self.removeLayerButton.clicked.connect(self.removeSelectedLayer)

        self.changeColorButton = QPushButton("Farbe ändern", self)
        self.changeColorButton.clicked.connect(self.changeLayerColor)

        layerManagementLayout = QHBoxLayout()
        layerManagementLayout.addWidget(self.layerList)
        layerManagementLayout.addWidget(self.removeLayerButton)
        layerManagementLayout.addWidget(self.changeColorButton)
        layout.addLayout(layerManagementLayout)

        self.progressBar = QProgressBar(self)
        layout.addWidget(self.progressBar)

        self.setLayout(layout)

    def updateDefaultPath(self, new_base_path):
        """
        Update the default path for file operations.

        Args:
            new_base_path: The new base path.
        """
        self.base_path = new_base_path

    def connect_signals(self, calculation_tab):
        """
        Connect signals from the calculation tab.

        Args:
            calculation_tab: The calculation tab object.
        """
        calculation_tab.data_added.connect(self.loadNetData)
    
    def openGeocodeAdressesDialog(self):
        """
        Open the dialog for geocoding addresses from a CSV file.
        """
        fname, _ = QFileDialog.getOpenFileName(self, 'CSV-Koordinaten laden', self.base_path, 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.geocodeAdresses(fname)

    def geocodeAdresses(self, inputfilename):
        """
        Start the geocoding process for the provided CSV file.

        Args:
            inputfilename: The path to the CSV file.
        """
        if hasattr(self, 'geocodingThread') and self.geocodingThread.isRunning():
            self.geocodingThread.terminate()
            self.geocodingThread.wait()
        self.geocodingThread = GeocodingThread(inputfilename)
        self.geocodingThread.calculation_done.connect(self.on_generation_done_geocode_Adress)
        self.geocodingThread.calculation_error.connect(self.on_generation_error_geocode_Adress)
        self.geocodingThread.start()
        self.progressBar.setRange(0, 0)

    def on_generation_done_geocode_Adress(self, fname):
        """
        Handle successful geocoding completion.

        Args:
            fname: The path to the generated CSV file.
        """
        self.progressBar.setRange(0, 1)
        self.loadCsvCoordinates(fname)

    def on_generation_error_geocode_Adress(self, error_message):
        """
        Handle errors during the geocoding process.

        Args:
            error_message: The error message.
        """
        QMessageBox.critical(self, "Fehler beim Geocoding", str(error_message))
        self.progressBar.setRange(0, 1)

    def openDownloadOSMDataDialog(self):
        """
        Open the dialog for downloading OSM data.
        """
        dialog = DownloadOSMDataDialog(self.base_path, self)
        if dialog.exec_() == QDialog.Accepted:
            pass

    def openOSMBuildingQueryDialog(self):
        """
        Open the dialog for querying OSM building data.
        """
        dialog = OSMBuildingQueryDialog(self.base_path, self)
        if dialog.exec_() == QDialog.Accepted:
            pass

    def openspatialAnalysisDialog(self):
        """
        Open the dialog for performing spatial analysis.
        """
        dialog = SpatialAnalysisDialog(self.base_path, self)
        if dialog.exec_() == QDialog.Accepted:
            pass

    def openLayerGenerationDialog(self):
        """
        Open the dialog for generating layers from data.
        """
        dialog = LayerGenerationDialog(self.base_path, self)
        dialog.setVisualizationTab(self)
        dialog.accepted_inputs.connect(self.generateAndImportLayers)
        self.currentLayerDialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self.raise_()
        self.activateWindow()

    def generateAndImportLayers(self, inputs):
        """
        Start the process of generating and importing layers based on user inputs.

        Args:
            inputs: The inputs for generating layers.
        """
        if hasattr(self, 'netgenerationThread') and self.netgenerationThread.isRunning():
            self.netgenerationThread.terminate()
            self.netgenerationThread.wait()
        self.netgenerationThread = NetGenerationThread(inputs, self.base_path)
        self.netgenerationThread.calculation_done.connect(self.on_generation_done)
        self.netgenerationThread.calculation_error.connect(self.on_generation_error)
        self.netgenerationThread.start()
        self.progressBar.setRange(0, 0)

    def on_generation_done(self, results):
        """
        Handle successful layer generation.

        Args:
            results: The results of the layer generation.
        """
        self.progressBar.setRange(0, 1)
        filenames = [f"{self.base_path}\Wärmenetz\HAST.geojson", f"{self.base_path}\Wärmenetz\Rücklauf.geojson",
                     f"{self.base_path}\Wärmenetz\Vorlauf.geojson", f"{self.base_path}\Wärmenetz\Erzeugeranlagen.geojson"]
        self.loadNetData(filenames)
        
        generatedLayers = {
            'HAST': f"{self.base_path}\Wärmenetz\HAST.geojson",
            'Rücklauf': f"{self.base_path}\Wärmenetz\Rücklauf.geojson",
            'Vorlauf': f"{self.base_path}\Wärmenetz\Vorlauf.geojson",
            'Erzeugeranlagen': f"{self.base_path}\Wärmenetz\Erzeugeranlagen.geojson"
        }

        self.layers_imported.emit(generatedLayers)

    def on_generation_error(self, error_message):
        """
        Handle errors during the layer generation process.

        Args:
            error_message: The error message.
        """
        QMessageBox.critical(self, "Berechnungsfehler", error_message)
        self.progressBar.setRange(0, 1)

    def importNetData(self):
        """
        Import network data from selected GeoJSON files.
        """
        fnames, _ = QFileDialog.getOpenFileNames(self, 'Netzdaten importieren', self.base_path, 'GeoJSON Files (*.geojson);;All Files (*)')
        if fnames:
            self.loadNetData(fnames)
    
    def calculate_map_center_and_zoom(self):
        """
        Calculate the center and zoom level for the map based on the loaded layers.

        Returns:
            list: Center coordinates [latitude, longitude].
            int: Zoom level.
        """
        if not self.layers:
            return [51.1657, 10.4515], 6

        minx, miny, maxx, maxy = None, None, None, None
        for layer in self.layers.values():
            bounds = layer.get_bounds()
            if minx is None or bounds[0][0] < minx:
                minx = bounds[0][0]
            if miny is None or bounds[0][1] < miny:
                miny = bounds[0][1]
            if maxx is None or bounds[1][0] > maxx:
                maxx = bounds[1][0]
            if maxy is None or bounds[1][1] > maxy:
                maxy = bounds[1][1]

        center_x = (minx + maxx) / 2
        center_y = (miny + maxy) / 2
        zoom = 17

        return [center_x, center_y], zoom
    
    def updateMapView(self):
        """
        Update the map view with the current layers and settings.
        """
        try:
            center, zoom = self.calculate_map_center_and_zoom()
            if center is None or zoom is None:
                raise ValueError("Keine gültigen Daten zum Berechnen des Kartenmittelpunkts und Zooms gefunden.")

            self.m = folium.Map(location=center, zoom_start=zoom)
            for layer in self.layers.values():
                self.m.add_child(layer)
            self.update_map_view(self.mapView, self.m)
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Laden der Daten", f"Es gab ein Problem beim Laden der Daten: {str(e)}\nBitte überprüfen Sie, ob die Datei leer ist oder ungültige Daten enthält.")

    def update_map_view(self, mapView, map_obj):
        """
        Update the web view to display the current map object.

        Args:
            mapView: The QWebEngineView widget displaying the map.
            map_obj: The Folium map object.
        """
        map_file = os.path.join(self.base_path, 'results', 'map.html')

        click_marker = folium.ClickForMarker()
        map_obj.add_child(click_marker)

        map_obj.save(map_file)

        mapView.load(QUrl.fromLocalFile(map_file))

    def loadNetData(self, filenames, color="#{:06x}".format(random.randint(0, 0xFFFFFF))):
        """
        Load network data from GeoJSON files and add them as layers.

        Args:
            filenames: List of GeoJSON file paths.
            color: The color to use for the layers.
        """
        if not isinstance(filenames, list):
            filenames = [filenames]

        self.addGeoJsonLayer(self.m, filenames, color)

    def addGeoJsonLayer(self, m, filenames, color):
        """
        Add a GeoJSON layer to the map.

        Args:
            m: The Folium map object.
            filenames: List of GeoJSON file paths.
            color: The color to use for the layers.
        """
        if hasattr(self, 'netgenerationThread') and self.netgenerationThread.isRunning():
            self.netgenerationThread.terminate()
            self.netgenerationThread.wait()

        self.netgenerationThread = FileImportThread(m, filenames, color)
        self.netgenerationThread.calculation_done.connect(self.on_import_done)
        self.netgenerationThread.calculation_error.connect(self.on_import_error)
        self.netgenerationThread.start()
        self.progressBar.setRange(0, 0)

    def on_import_done(self, results):
        """
        Handle successful import of GeoJSON data.

        Args:
            results: The imported GeoJSON data.
        """
        self.progressBar.setRange(0, 1)
        for filename, geojson_data in results.items():
            def create_style_function(color, weight, fillOpacity):
                return lambda feature: {
                    'fillColor': color,
                    'color': color,
                    'weight': 1.5,
                    'fillOpacity': 0.5,
                }

            geojson_layer = folium.GeoJson(
                geojson_data['gdf'],
                name=geojson_data['name'],
                style_function=create_style_function(geojson_data['style']['color'], geojson_data['style']['weight'], geojson_data['style']['fillOpacity'])
            )
            geojson_layer.add_to(self.m)

            self.layers[geojson_data['name']] = geojson_layer

            if geojson_data['name'] not in [self.layerList.item(i).text() for i in range(self.layerList.count())]:
                listItem = QListWidgetItem(geojson_data['name'])
                listItem.setBackground(QColor(geojson_data['style']['color']))
                listItem.setForeground(QBrush(QColor('#FFFFFF')))
                self.layerList.addItem(listItem)

        self.updateMapView()

    def on_import_error(self, error_message):
        """
        Handle errors during the import process.

        Args:
            error_message: The error message.
        """
        self.progressBar.setRange(0, 1)
        print("Fehler beim Importieren der GeoJSON-Daten:", error_message)

    def removeSelectedLayer(self):
        """
        Remove the selected layer from the map.
        """
        selectedItems = self.layerList.selectedItems()
        if selectedItems:
            selectedItem = selectedItems[0]
            layerName = selectedItem.text()
            self.layerList.takeItem(self.layerList.row(selectedItem))
            del self.layers[layerName]
            self.updateMapView()

    def changeLayerColor(self):
        """
        Open a color dialog to change the color of the selected layer.
        """
        selectedItems = self.layerList.selectedItems()
        if selectedItems:
            selectedItem = selectedItems[0]
            layerName = selectedItem.text()
            
            color = QColorDialog.getColor()
            if color.isValid():
                self.updateLayerColor(layerName, color.name())

    def updateLayerColor(self, layerName, new_color):
        """
        Update the color of the specified layer.

        Args:
            layerName: The name of the layer.
            new_color: The new color for the layer.
        """
        if layerName in self.layers:
            del self.layers[layerName]
            self.loadNetData(layerName, new_color)
            self.updateListItemColor(layerName, new_color)

    def updateListItemColor(self, layerName, new_color):
        """
        Update the color of the specified layer item in the list.

        Args:
            layerName: The name of the layer.
            new_color: The new color for the layer item.
        """
        for index in range(self.layerList.count()):
            listItem = self.layerList.item(index)
            if listItem.text() == layerName:
                listItem.setBackground(QColor(new_color))
                listItem.setForeground(QBrush(QColor('#FFFFFF')))
                break

    def createGeoJsonFromCsv(self, csv_file_path, geojson_file_path):
        """
        Create a GeoJSON file from a CSV file containing coordinates.

        Args:
            csv_file_path: The path to the CSV file.
            geojson_file_path: The path to save the GeoJSON file.
        """
        df = pd.read_csv(csv_file_path, delimiter=';')

        gdf = gpd.GeoDataFrame(
            df, 
            geometry=[Point(xy) for xy in zip(df.UTM_X, df.UTM_Y)],
            crs="EPSG:25833"
        )

        gdf.to_file(geojson_file_path, driver='GeoJSON')

    def loadCsvCoordinates(self, fname=None):
        """
        Load coordinates from a CSV file and display them on the map.

        Args:
            fname: The path to the CSV file.
        """
        if not fname:
            fname, _ = QFileDialog.getOpenFileName(self, 'CSV-Koordinaten laden', self.base_path, 'CSV Files (*.csv);;All Files (*)')
        if fname:
            base_name = os.path.splitext(os.path.basename(fname))[0]
            geojson_path = os.path.join(self.base_path, 'Gebäudedaten', f"{base_name}.geojson")
            
            self.createGeoJsonFromCsv(fname, geojson_path)
            self.addGeoJsonLayer(self.m, [geojson_path], color=None)
