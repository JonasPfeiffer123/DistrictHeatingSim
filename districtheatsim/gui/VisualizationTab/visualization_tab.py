"""
Filename: visualiztion_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
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
from gui.threads import NetGenerationThread, FileImportThread

# Tab class
class VisualizationTab(QWidget):
    layers_imported = pyqtSignal(dict)

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.layers = {}

        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.project_folder)

        self.initUI()

    def initUI(self):
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
        self.base_path = new_base_path

    def connect_signals(self, calculation_tab):
        calculation_tab.data_added.connect(self.loadNetData)
    
    def openGeocodeAdressesDialog(self):
        dialog = GeocodeAddressesDialog(self.base_path, self)
        if dialog.exec_() == QDialog.Accepted:
            pass

    def openDownloadOSMDataDialog(self):
        dialog = DownloadOSMDataDialog(self.base_path, self)
        if dialog.exec_() == QDialog.Accepted:
            pass

    def openOSMBuildingQueryDialog(self):
        dialog = OSMBuildingQueryDialog(self.base_path, self)
        if dialog.exec_() == QDialog.Accepted:
            pass

    def openspatialAnalysisDialog(self):
        dialog = SpatialAnalysisDialog(self.base_path, self)
        if dialog.exec_() == QDialog.Accepted:
            pass

    def openLayerGenerationDialog(self):
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
        if hasattr(self, 'netgenerationThread') and self.netgenerationThread.isRunning():
            self.netgenerationThread.terminate()
            self.netgenerationThread.wait()
        self.netgenerationThread = NetGenerationThread(inputs, self.base_path)
        self.netgenerationThread.calculation_done.connect(self.on_generation_done)
        self.netgenerationThread.calculation_error.connect(self.on_generation_error)
        self.netgenerationThread.start()
        self.progressBar.setRange(0, 0)

    def on_generation_done(self, results):
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
        QMessageBox.critical(self, "Berechnungsfehler", error_message)
        self.progressBar.setRange(0, 1)

    def importNetData(self):
        fnames, _ = QFileDialog.getOpenFileNames(self, 'Netzdaten importieren', '', 'GeoJSON Files (*.geojson);;All Files (*)')
        if fnames:
            self.loadNetData(fnames)
    
    def calculate_map_center_and_zoom(self):
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
        map_file = os.path.join(self.base_path, 'results', 'map.html')

        # Marker setzen und ClickForMarker hinzufügen
        click_marker = folium.ClickForMarker()
        map_obj.add_child(click_marker)

        # Karte speichern
        map_obj.save(map_file)

        mapView.load(QUrl.fromLocalFile(map_file))

    def loadNetData(self, filenames, color="#{:06x}".format(random.randint(0, 0xFFFFFF))):
        if not isinstance(filenames, list):
            filenames = [filenames]

        self.addGeoJsonLayer(self.m, filenames, color)

    def addGeoJsonLayer(self, m, filenames, color):
        if hasattr(self, 'netgenerationThread') and self.netgenerationThread.isRunning():
            self.netgenerationThread.terminate()
            self.netgenerationThread.wait()

        self.netgenerationThread = FileImportThread(m, filenames, color)
        self.netgenerationThread.calculation_done.connect(self.on_import_done)
        self.netgenerationThread.calculation_error.connect(self.on_import_error)
        self.netgenerationThread.start()
        self.progressBar.setRange(0, 0)

    def on_import_done(self, results):
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
        self.progressBar.setRange(0, 1)
        print("Fehler beim Importieren der GeoJSON-Daten:", error_message)

    def removeSelectedLayer(self):
        selectedItems = self.layerList.selectedItems()
        if selectedItems:
            selectedItem = selectedItems[0]
            layerName = selectedItem.text()
            self.layerList.takeItem(self.layerList.row(selectedItem))
            del self.layers[layerName]
            self.updateMapView()

    def changeLayerColor(self):
        selectedItems = self.layerList.selectedItems()
        if selectedItems:
            selectedItem = selectedItems[0]
            layerName = selectedItem.text()
            
            color = QColorDialog.getColor()
            if color.isValid():
                self.updateLayerColor(layerName, color.name())

    def updateLayerColor(self, layerName, new_color):
        if layerName in self.layers:
            del self.layers[layerName]
            self.loadNetData(layerName, new_color)
            self.updateListItemColor(layerName, new_color)

    def updateListItemColor(self, layerName, new_color):
        for index in range(self.layerList.count()):
            listItem = self.layerList.item(index)
            if listItem.text() == layerName:
                listItem.setBackground(QColor(new_color))
                listItem.setForeground(QBrush(QColor('#FFFFFF')))
                break

    def createGeoJsonFromCsv(self, csv_file_path, geojson_file_path):
        df = pd.read_csv(csv_file_path, delimiter=';')

        gdf = gpd.GeoDataFrame(
            df, 
            geometry=[Point(xy) for xy in zip(df.UTM_X, df.UTM_Y)],
            crs="EPSG:25833"
        )

        gdf.to_file(geojson_file_path, driver='GeoJSON')
        print(f"GeoJSON-Datei erfolgreich erstellt: {geojson_file_path}")

    def loadCsvCoordinates(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'CSV-Koordinaten laden', '', 'CSV Files (*.csv);;All Files (*)')
        if fname:
            geojson_path = f"{self.base_path}\Gebäudedaten\Koordinaten.geojson"
            self.createGeoJsonFromCsv(fname, geojson_path)
            self.addGeoJsonLayer(self.m, [geojson_path], color=None)
