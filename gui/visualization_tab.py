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

from gui.visualization_dialogs import CSVEditorDialog, LayerGenerationDialog, DownloadOSMDataDialog, OSMBuildingQueryDialog, SpatialAnalysisDialog, GeocodeAddressesDialog, ProcessLOD2DataDialog
from gui.threads import NetGenerationThread, FileImportThread

class VisualizationTab(QWidget):
    layers_imported = pyqtSignal(dict)

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.layers = {}
        self.initUI()
        self.base_path = "project_data/Bad Muskau"  # initializing base path
        self.updateDefaultPath(self.base_path)
    
    def initUI(self):
        layout = QVBoxLayout()

        # initializing map
        self.m = folium.Map(location=[51.1657, 10.4515], zoom_start=6)
        self.mapView = QWebEngineView()
        # creating menubar
        self.menuBar = QMenuBar(self)
        self.menuBar.setFixedHeight(30)  # set specific height
        fileMenu = self.menuBar.addMenu('Datei')

        csvEditAction = QAction('CSV erstellen/bearbeiten', self)
        csvEditAction.triggered.connect(self.openCsvEditorDialog)
        fileMenu.addAction(csvEditAction)

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

        spatialAnalysisAction = QAction('Raumanalyse', self)
        spatialAnalysisAction.triggered.connect(self.openspatialAnalysisDialog)
        fileMenu.addAction(spatialAnalysisAction)

        processLOD2Action = QAction('Process LOD2', self)
        processLOD2Action.triggered.connect(self.openprocessLOD2Dialog)
        fileMenu.addAction(processLOD2Action)

        downloadAction = QAction('Wärmenetz aus Daten generieren', self)
        downloadAction.triggered.connect(self.openLayerGenerationDialog)
        fileMenu.addAction(downloadAction)

        importAction = QAction('Import geojson-Datei', self)
        importAction.triggered.connect(self.importNetData)
        fileMenu.addAction(importAction)

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

    def openCsvEditorDialog(self):
        dialog = CSVEditorDialog(self.base_path, self)
        if dialog.exec_() == QDialog.Accepted:
            pass
    
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
        if dialog.exec_() == QDialog.Accepted:
            inputs = dialog.getInputs()
            self.generateAndImportLayers(inputs)

    def openprocessLOD2Dialog(self):
        dialog = ProcessLOD2DataDialog(self.base_path, self)
        if dialog.exec_() == QDialog.Accepted:
            pass

    def generateAndImportLayers(self, inputs):
        # Make sure the previous thread exits
        if hasattr(self, 'netgenerationThread') and self.netgenerationThread.isRunning():
            self.netgenerationThread.terminate()
            self.netgenerationThread.wait()
        self.netgenerationThread = NetGenerationThread(inputs, self.base_path)
        self.netgenerationThread.calculation_done.connect(self.on_generation_done)
        self.netgenerationThread.calculation_error.connect(self.on_generation_error)
        self.netgenerationThread.start()
        self.progressBar.setRange(0, 0)  # Enables indeterministic mode

    # Storage location must be variable
    def on_generation_done(self, results):
        self.progressBar.setRange(0, 1)
        filenames = [f"{self.base_path}/Wärmenetz/HAST.geojson", f"{self.base_path}/Wärmenetz/Rücklauf.geojson",
                     f"{self.base_path}/Wärmenetz/Vorlauf.geojson", f"{self.base_path}/Wärmenetz/Erzeugeranlagen.geojson"]
        self.loadNetData(filenames)
        
        generatedLayers = {
            'HAST': f"{self.base_path}/Wärmenetz/HAST.geojson",
            'Rücklauf': f"{self.base_path}/Wärmenetz/Rücklauf.geojson",
            'Vorlauf': f"{self.base_path}/Wärmenetz/Vorlauf.geojson",
            'Erzeugeranlagen': f"{self.base_path}/Wärmenetz/Erzeugeranlagen.geojson"
        }

        # Trigger the signal with the paths of the generated layers
        self.layers_imported.emit(generatedLayers)

    def on_generation_error(self, error_message):
        QMessageBox.critical(self, "Berechnungsfehler", error_message)
        self.progressBar.setRange(0, 1)  # Disables indeterministic mode

    def importNetData(self):
        fnames, _ = QFileDialog.getOpenFileNames(self, 'Netzdaten importieren', '', 'GeoJSON Files (*.geojson);;All Files (*)')
        if fnames:
            self.loadNetData(fnames)
    
    def calculate_map_center_and_zoom(self):
        if not self.layers:
            return [51.1657, 10.4515], 6  # Default values

        # Calculate the combined boundaries of all layers
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
        zoom = 17  # You may need to develop an algorithm to calculate an appropriate zoom level

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
        """ Aktualisiert die Kartenansicht in PyQt """
        map_file = "results/map.html"
        map_obj.save(map_file)
        mapView.load(QUrl.fromLocalFile(os.path.abspath(map_file)))

    def loadNetData(self, filenames, color="#{:06x}".format(random.randint(0, 0xFFFFFF))):
        if not isinstance(filenames, list):
            filenames = [filenames]

        # Pass the color if specified, otherwise a random color will be generated in the thread
        self.addGeoJsonLayer(self.m, filenames, color)

    # This function only starts the thread and returns nothing.
    def addGeoJsonLayer(self, m, filenames, color):
        # Terminate the previous thread if it is running
        if hasattr(self, 'netgenerationThread') and self.netgenerationThread.isRunning():
            self.netgenerationThread.terminate()
            self.netgenerationThread.wait()

        # Start a new thread for all files
        self.netgenerationThread = FileImportThread(m, filenames, color)
        self.netgenerationThread.calculation_done.connect(self.on_import_done)
        self.netgenerationThread.calculation_error.connect(self.on_import_error)
        self.netgenerationThread.start()
        self.progressBar.setRange(0, 0)

   # This slot is called when the thread is finished.
    def on_import_done(self, results):
        self.progressBar.setRange(0, 1)
        for filename, geojson_data in results.items():
            # Function to create a style_function with current context
            def create_style_function(color, weight, fillOpacity):
                return lambda feature: {
                    'fillColor': color,
                    'color': color,
                    'weight': 1.5,
                    'fillOpacity': 0.5,
                }

            # Add the layer to the map using the dynamic style_function
            geojson_layer = folium.GeoJson(
                geojson_data['gdf'],
                name=geojson_data['name'],
                style_function=create_style_function(geojson_data['style']['color'], geojson_data['style']['weight'], geojson_data['style']['fillOpacity'])
            )
            geojson_layer.add_to(self.m)

            # Add the layer to management
            self.layers[geojson_data['name']] = geojson_layer

            # Update the QListWidget
            if geojson_data['name'] not in [self.layerList.item(i).text() for i in range(self.layerList.count())]:
                listItem = QListWidgetItem(geojson_data['name'])
                listItem.setBackground(QColor(geojson_data['style']['color']))
                listItem.setForeground(QBrush(QColor('#FFFFFF')))
                self.layerList.addItem(listItem)

        self.updateMapView()

    def on_import_error(self, error_message):
        # Display an error message or log the error.
        self.progressBar.setRange(0, 1)
        print("Fehler beim Importieren der GeoJSON-Daten:", error_message)
        # Possibly show a dialog or update the status bar.

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
            # delete old layer
            del self.layers[layerName]
            
            # Recreate the layer with the new color
            self.loadNetData(layerName, new_color)

            # Update the color in the QListWidget
            self.updateListItemColor(layerName, new_color)

    def updateListItemColor(self, layerName, new_color):
        for index in range(self.layerList.count()):
            listItem = self.layerList.item(index)
            if listItem.text() == layerName:
                listItem.setBackground(QColor(new_color))
                listItem.setForeground(QBrush(QColor('#FFFFFF')))  # White text color for contrast
                break

    def createGeoJsonFromCsv(self, csv_file_path, geojson_file_path):
        # read csv-file
        df = pd.read_csv(csv_file_path, delimiter=';')

        # create GeoDataFrames
        gdf = gpd.GeoDataFrame(
            df, 
            geometry=[Point(xy) for xy in zip(df.UTM_X, df.UTM_Y)],
            crs="EPSG:25833"  # Adjust this to your specific coordinate system
        )

        # Convert to GeoJSON and save
        gdf.to_file(geojson_file_path, driver='GeoJSON')

        print(f"GeoJSON-Datei erfolgreich erstellt: {geojson_file_path}")

    def loadCsvCoordinates(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'CSV-Koordinaten laden', '', 'CSV Files (*.csv);;All Files (*)')
        if fname:
            # Path for the temporary GeoJSON file
            geojson_path = f"{self.base_path}/Gebäudedaten/Koordinaten.geojson"

            # Creating GeoJSON file from CSV file
            self.createGeoJsonFromCsv(fname, geojson_path)

            # Load GeoJSON file into the map
            self.addGeoJsonLayer(self.m, [geojson_path], color=None)
