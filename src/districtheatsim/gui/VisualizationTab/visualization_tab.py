"""
Filename: visualization_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-27
Description: Contains the VisualizationTab as MVP model.
"""

import logging
logging.basicConfig(level=logging.DEBUG)

import os
import random
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

import folium

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMenuBar, QAction, QFileDialog, \
    QHBoxLayout, QListWidget, QProgressBar, QColorDialog, QListWidgetItem, QMessageBox, QMainWindow, QDialog
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWebEngineWidgets import QWebEngineView

from gui.VisualizationTab.visualization_dialogs import LayerGenerationDialog, DownloadOSMDataDialog, OSMBuildingQueryDialog, SpatialAnalysisDialog, GeocodeAddressesDialog
from gui.threads import NetGenerationThread, FileImportThread, GeocodingThread

class VisualizationModel:
    def __init__(self):
        self.layers = {}
        self.base_path = ""

    def set_base_path(self, base_path):
        self.base_path = base_path

    def get_base_path(self):
        return self.base_path

    def load_geojson(self, file_path):
        return gpd.read_file(file_path)

    def create_geojson_from_csv(self, csv_file_path, geojson_file_path):
        df = pd.read_csv(csv_file_path, delimiter=';')
        gdf = gpd.GeoDataFrame(
            df,
            geometry=[Point(xy) for xy in zip(df.UTM_X, df.UTM_Y)],
            crs="EPSG:25833"
        )
        gdf.to_file(geojson_file_path, driver='GeoJSON')

    def calculate_map_center_and_zoom(self):
        if not self.layers:
            return [51.1657, 10.4515], 6

        minx, miny, maxx, maxy = None, None, None, None
        for layer in self.layers.values():
            bounds = layer.total_bounds
            if minx is None or bounds[0] < minx:
                minx = bounds[0]
            if miny is None or bounds[1] < miny:
                miny = bounds[1]
            if maxx is None or bounds[2] > maxx:
                maxx = bounds[2]
            if maxy is None or bounds[3] > maxy:
                maxy = bounds[3]

        center_x = (minx + maxx) / 2
        center_y = (miny + maxy) / 2
        zoom = 17
        return [center_x, center_y], zoom

class VisualizationPresenter(QObject):
    layers_imported = pyqtSignal(dict)

    def __init__(self, model, view, data_manager):
        super().__init__()
        self.model = model
        self.view = view
        self.data_manager = data_manager

        self.data_manager.project_folder_changed.connect(self.on_project_folder_changed)

        self.view.downloadAction.triggered.connect(self.open_geocode_addresses_dialog)
        self.view.loadCsvAction.triggered.connect(self.load_csv_coordinates)
        self.view.importAction.triggered.connect(self.import_geojson)
        self.view.removeLayerButton.clicked.connect(self.remove_selected_layer)
        self.view.changeColorButton.clicked.connect(self.change_layer_color)
        self.view.layerGenerationAction.triggered.connect(self.open_layer_generation_dialog)
        self.view.downloadActionOSM.triggered.connect(self.open_osm_data_dialog)
        self.view.osmBuildingAction.triggered.connect(self.open_osm_building_query_dialog)
        self.view.spatialAnalysisAction.triggered.connect(self.open_spatial_analysis_dialog)

        self.on_project_folder_changed(self.data_manager.project_folder)

        self.update_map_view()

    def on_project_folder_changed(self, new_base_path):
        self.model.set_base_path(new_base_path)

    def load_csv_coordinates(self):
        try:
            fname, _ = QFileDialog.getOpenFileName(self.view, 'CSV-Koordinaten laden', self.model.get_base_path(), 'CSV Files (*.csv);;All Files (*)')
            if fname:
                geojson_path = os.path.join(self.model.get_base_path(), 'Gebäudedaten', f"{os.path.splitext(os.path.basename(fname))[0]}.geojson")
                self.model.create_geojson_from_csv(fname, geojson_path)
                self.add_geojson_layer([geojson_path])
        except Exception as e:
            self.view.show_error_message("Fehler beim Laden von CSV-Koordinaten", str(e))

    def import_geojson(self):
        try:
            fnames, _ = QFileDialog.getOpenFileNames(self.view, 'Netzdaten importieren', self.model.get_base_path(), 'GeoJSON Files (*.geojson);;All Files (*)')
            if fnames:
                self.add_geojson_layer(fnames)
        except Exception as e:
            self.view.show_error_message("Fehler beim Importieren von GeoJSON", str(e))

    def terminate_thread(self, thread):
        if hasattr(self, thread) and getattr(self, thread).isRunning():
            getattr(self, thread).terminate()
            getattr(self, thread).wait()

    def add_geojson_layer(self, filenames, color=None):
        try:
            color = color or "#{:06x}".format(random.randint(0, 0xFFFFFF))
            self.terminate_thread('netgenerationThread')

            self.netgenerationThread = FileImportThread(self.view.mapView, filenames, color)
            self.netgenerationThread.calculation_done.connect(self.on_import_done)
            self.netgenerationThread.calculation_error.connect(self.on_import_error)
            self.netgenerationThread.start()
            self.view.progressBar.setRange(0, 0)
        except Exception as e:
            self.view.show_error_message("Fehler beim Hinzufügen einer GeoJSON-Schicht", str(e))    

    def on_import_done(self, results):
        try:
            self.view.progressBar.setRange(0, 1)
            for filename, geojson_data in results.items():
                geojson_layer = folium.GeoJson(
                    geojson_data['gdf'],
                    name=geojson_data['name'],
                    style_function=lambda feature: {
                        'fillColor': geojson_data['style']['color'],
                        'color': geojson_data['style']['color'],
                        'weight': 1.5,
                        'fillOpacity': 0.5,
                    }
                )
                self.model.layers[geojson_data['name']] = geojson_layer

                if geojson_data['name'] not in [self.view.layerList.item(i).text() for i in range(self.view.layerList.count())]:
                    listItem = QListWidgetItem(geojson_data['name'])
                    listItem.setBackground(QColor(geojson_data['style']['color']))
                    listItem.setForeground(QBrush(QColor('#FFFFFF')))
                    self.view.layerList.addItem(listItem)

            self.update_map_view()
        except Exception as e:
            self.view.show_error_message("Fehler beim Importieren und Hinzufügen der Schicht", str(e))

    def on_import_error(self, error_message):
        self.view.progressBar.setRange(0, 1)
        self.view.show_error_message("Fehler beim Importieren der GeoJSON-Daten", error_message)

    def update_map_view(self):
        try:
            center, zoom = self.model.calculate_map_center_and_zoom()
            if center is None or zoom is None:
                raise ValueError("Keine gültigen Daten zum Berechnen des Kartenmittelpunkts und Zooms gefunden.")

            # Initialisiere die Karte mit den berechneten Werten
            m = folium.Map(location=center, zoom_start=zoom)
            
            # Füge die Layer der Karte hinzu
            for layer in self.model.layers.values():
                layer.add_to(m)
            
            # Aktualisiere die Webansicht
            self.view.update_map_view(m)
        except Exception as e:
            self.view.show_error_message("Fehler beim Laden der Daten", str(e))

    def remove_selected_layer(self):
        selectedItems = self.view.layerList.selectedItems()
        if selectedItems:
            selectedItem = selectedItems[0]
            layerName = selectedItem.text()
            self.view.layerList.takeItem(self.view.layerList.row(selectedItem))
            del self.model.layers[layerName]
            self.update_map_view()

    def change_layer_color(self):
        selectedItems = self.view.layerList.selectedItems()
        if selectedItems:
            selectedItem = selectedItems[0]
            layerName = selectedItem.text()
            color = QColorDialog.getColor()
            if color.isValid():
                self.update_layer_color(layerName, color.name())

    def update_layer_color(self, layerName, new_color):
        if layerName in self.model.layers:
            del self.model.layers[layerName]
            self.add_geojson_layer([layerName], new_color)

    def open_geocode_addresses_dialog(self):
        dialog = GeocodeAddressesDialog(self.model.get_base_path(), self.view)
        if dialog.exec_() == QDialog.Accepted:
            fname = dialog.get_file_name()
            self.geocode_addresses(fname)

    def geocode_addresses(self, inputfilename):
        if hasattr(self, 'geocodingThread') and self.geocodingThread.isRunning():
            self.geocodingThread.terminate()
            self.geocodingThread.wait()
        self.geocodingThread = GeocodingThread(inputfilename)
        self.geocodingThread.calculation_done.connect(self.on_geocode_done)
        self.geocodingThread.calculation_error.connect(self.on_geocode_error)
        self.geocodingThread.start()
        self.view.progressBar.setRange(0, 0)

    def on_geocode_done(self, fname):
        self.view.progressBar.setRange(0, 1)
        self.load_csv_coordinates(fname)

    def on_geocode_error(self, error_message):
        self.view.show_error_message("Fehler beim Geocoding", error_message)
        self.view.progressBar.setRange(0, 1)

    def open_layer_generation_dialog(self):
        dialog = LayerGenerationDialog(self.model.get_base_path(), self.view)
        dialog.setVisualizationTab(self)
        dialog.accepted_inputs.connect(self.generate_and_import_layers)
        self.currentLayerDialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self.view.raise_()
        self.view.activateWindow()

    def generate_and_import_layers(self, inputs):
        if hasattr(self, 'netgenerationThread') and self.netgenerationThread.isRunning():
            self.netgenerationThread.terminate()
            self.netgenerationThread.wait()
        self.netgenerationThread = NetGenerationThread(inputs, self.model.get_base_path())
        self.netgenerationThread.calculation_done.connect(self.on_generation_done)
        self.netgenerationThread.calculation_error.connect(self.on_generation_error)
        self.netgenerationThread.start()
        self.view.progressBar.setRange(0, 0)

    def on_generation_done(self, results):
        self.view.progressBar.setRange(0, 1)
        filenames = [f"{self.model.get_base_path()}\Wärmenetz\HAST.geojson", f"{self.model.get_base_path()}\Wärmenetz\Rücklauf.geojson",
                     f"{self.model.get_base_path()}\Wärmenetz\Vorlauf.geojson", f"{self.model.get_base_path()}\Wärmenetz\Erzeugeranlagen.geojson"]
        self.add_geojson_layer(filenames)
        generatedLayers = {
            'HAST': f"{self.model.get_base_path()}\Wärmenetz\HAST.geojson",
            'Rücklauf': f"{self.model.get_base_path()}\Wärmenetz\Rücklauf.geojson",
            'Vorlauf': f"{self.model.get_base_path()}\Wärmenetz\Vorlauf.geojson",
            'Erzeugeranlagen': f"{self.model.get_base_path()}\Wärmenetz\Erzeugeranlagen.geojson"
        }
        self.layers_imported.emit(generatedLayers)

    def on_generation_error(self, error_message):
        self.view.show_error_message("Berechnungsfehler", error_message)
        self.view.progressBar.setRange(0, 1)

    def open_osm_data_dialog(self):
        """
        Opens the dialog for downloading OSM data.
        """
        dialog = DownloadOSMDataDialog(self.model.get_base_path(), self.view)
        if dialog.exec_() == QDialog.Accepted:
            pass  # Handle accepted case if necessary

    def open_spatial_analysis_dialog(self):
        """
        Opens the dialog for performing spatial analysis.
        """
        dialog = SpatialAnalysisDialog(self.model.get_base_path(), self.view)
        if dialog.exec_() == QDialog.Accepted:
            pass  # Handle accepted case if necessary

    def open_osm_building_query_dialog(self):
        """
        Opens the dialog for querying OSM building data.
        """
        dialog = OSMBuildingQueryDialog(self.model.get_base_path(), self.view)
        if dialog.exec_() == QDialog.Accepted:
            pass  # Handle accepted case if necessary

class VisualizationTabView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.m = folium.Map(location=[51.1657, 10.4515], zoom_start=6)
        self.mapView = QWebEngineView()
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

        self.spatialAnalysisAction = QAction('Clustering Quartiere', self)
        fileMenu.addAction(self.spatialAnalysisAction)

        self.importAction = QAction('Import geojson-Datei', self)
        fileMenu.addAction(self.importAction)

        self.layerGenerationAction = QAction('Wärmenetz aus Daten generieren', self)
        fileMenu.addAction(self.layerGenerationAction)

        layout.addWidget(self.menuBar)
        layout.addWidget(self.mapView)

        self.layerList = QListWidget(self)
        self.layerList.setMaximumHeight(100)

        self.removeLayerButton = QPushButton("Layer entfernen", self)
        self.changeColorButton = QPushButton("Farbe ändern", self)

        layerManagementLayout = QHBoxLayout()
        layerManagementLayout.addWidget(self.layerList)
        layerManagementLayout.addWidget(self.removeLayerButton)
        layerManagementLayout.addWidget(self.changeColorButton)
        layout.addLayout(layerManagementLayout)

        self.progressBar = QProgressBar(self)
        layout.addWidget(self.progressBar)

        self.setLayout(layout)

    def update_map_view(self, map_obj):
        map_html = map_obj._repr_html_()  # Konvertiere die Karte in HTML
        self.mapView.setHtml(map_html)  # Setze das HTML in die Webansicht

    def show_error_message(self, title, message):
        QMessageBox.critical(self, title, message)

class VisualizationTab(QMainWindow):
    def __init__(self, data_manager, parent=None):
        super().__init__()
        self.setWindowTitle("Visualization Tab")
        self.setGeometry(100, 100, 800, 600)

        self.model = VisualizationModel()
        self.view = VisualizationTabView()
        self.presenter = VisualizationPresenter(self.model, self.view, data_manager)

        self.setCentralWidget(self.view)