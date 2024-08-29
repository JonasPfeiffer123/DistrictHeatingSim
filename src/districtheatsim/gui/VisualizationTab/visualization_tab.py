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
from gui.VisualizationTab.net_generation_threads import NetGenerationThread, FileImportThread, GeocodingThread

class VisualizationModel:
    """
    The VisualizationModel class is responsible for handling all data-related operations
    such as loading and saving GeoJSON files, generating GeoJSON from CSV files, 
    and calculating the center and zoom level of the map.

    Attributes:
        layers (dict): A dictionary storing the layers added to the model.
        base_path (str): The base path used for file operations.
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

    def calculate_map_center_and_zoom(self):
        """
        Calculates the center coordinates and zoom level for the map based on the loaded layers.

        Returns:
            list: The center coordinates [latitude, longitude].
            int: The zoom level.
        """
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

    def __init__(self, model, view, data_manager):
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
        """
        Updates the base path in the model when the project folder changes.

        Args:
            new_base_path (str): The new base path.
        """
        self.model.set_base_path(new_base_path)

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
            self.view.show_error_message("Fehler beim Laden von CSV-Koordinaten", str(e))

    def import_geojson(self):
        """
        Imports GeoJSON files and adds them as layers to the map.
        """
        try:
            fnames, _ = QFileDialog.getOpenFileNames(self.view, 'Netzdaten importieren', self.model.get_base_path(), 'GeoJSON Files (*.geojson);;All Files (*)')
            if fnames:
                self.add_geojson_layer(fnames)
        except Exception as e:
            self.view.show_error_message("Fehler beim Importieren von GeoJSON", str(e))

    def terminate_thread(self, thread):
        """
        Terminates the specified thread if it is running.

        Args:
            thread (str): The name of the thread attribute to terminate.
        """
        if hasattr(self, thread) and getattr(self, thread).isRunning():
            getattr(self, thread).terminate()
            getattr(self, thread).wait()

    def add_geojson_layer(self, filenames, color=None):
        """
        Adds a GeoJSON layer to the map.

        Args:
            filenames (list): A list of GeoJSON file paths.
            color (str, optional): The color to use for the layer. Defaults to a random color.
        """
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
        """
        Handles the successful import of GeoJSON data and updates the map view.

        Args:
            results (dict): The imported GeoJSON data.
        """
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
        """
        Handles errors that occur during the import of GeoJSON data.

        Args:
            error_message (str): The error message to display.
        """
        self.view.progressBar.setRange(0, 1)
        self.view.show_error_message("Fehler beim Importieren der GeoJSON-Daten", error_message)

    def update_map_view(self):
        """
        Updates the map view with the current layers and settings.
        """
        try:
            center, zoom = self.model.calculate_map_center_and_zoom()
            if center is None or zoom is None:
                raise ValueError("Keine gültigen Daten zum Berechnen des Kartenmittelpunkts und Zooms gefunden.")

            m = folium.Map(location=center, zoom_start=zoom)
            for layer in self.model.layers.values():
                layer.add_to(m)
            self.view.update_map_view(m)
        except Exception as e:
            self.view.show_error_message("Fehler beim Laden der Daten", str(e))

    def remove_selected_layer(self):
        """
        Removes the selected layer from the map.
        """
        selectedItems = self.view.layerList.selectedItems()
        if selectedItems:
            selectedItem = selectedItems[0]
            layerName = selectedItem.text()
            self.view.layerList.takeItem(self.view.layerList.row(selectedItem))
            del self.model.layers[layerName]
            self.update_map_view()

    def change_layer_color(self):
        """
        Opens a color dialog to change the color of the selected layer.
        """
        selectedItems = self.view.layerList.selectedItems()
        if selectedItems:
            selectedItem = selectedItems[0]
            layerName = selectedItem.text()
            color = QColorDialog.getColor()
            if color.isValid():
                self.update_layer_color(layerName, color.name())

    def update_layer_color(self, layerName, new_color):
        """
        Updates the color of the specified layer.

        Args:
            layerName (str): The name of the layer.
            new_color (str): The new color for the layer.
        """
        if layerName in self.model.layers:
            del self.model.layers[layerName]
            self.add_geojson_layer([layerName], new_color)

    def open_geocode_addresses_dialog(self):
        """
        Opens the dialog for geocoding addresses from a CSV file.
        """
        dialog = GeocodeAddressesDialog(self.model.get_base_path(), self.view)
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
    """
    The VisualizationTabView class is responsible for managing the user interface components
    such as the map display, menus, buttons, and progress bar.

    Attributes:
        m (folium.Map): The folium map object used to display geographical data.
        mapView (QWebEngineView): The web view used to render the folium map.
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
        """
        Updates the web view to display the current map object.

        Args:
            map_obj (folium.Map): The folium map object to render.
        """
        map_html = map_obj._repr_html_()
        self.mapView.setHtml(map_html)

    def show_error_message(self, title, message):
        """
        Displays an error message in a message box.

        Args:
            title (str): The title of the error message box.
            message (str): The error message to display.
        """
        QMessageBox.critical(self, title, message)


class VisualizationTab(QMainWindow):
    """
    The VisualizationTab class integrates the model, view, and presenter
    into a single main window for the application.

    Attributes:
        model (VisualizationModel): The model instance containing the data logic.
        view (VisualizationTabView): The view instance containing the UI logic.
        presenter (VisualizationPresenter): The presenter instance handling the interaction between model and view.
    """

    def __init__(self, data_manager, parent=None):
        """
        Initializes the VisualizationTab with the given data manager.

        Args:
            data_manager (DataManager): The data manager instance handling project-related data.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__()
        self.setWindowTitle("Visualization Tab")
        self.setGeometry(100, 100, 800, 600)

        self.model = VisualizationModel()
        self.view = VisualizationTabView()
        self.presenter = VisualizationPresenter(self.model, self.view, data_manager)

        self.setCentralWidget(self.view)
