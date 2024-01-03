import os
import random
import geopandas as gpd

from PyQt5.QtCore import pyqtSignal, QUrl
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMenuBar, QAction, QFileDialog, \
    QHBoxLayout, QListWidget, QDialog, QProgressBar, QColorDialog, QListWidgetItem
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWebEngineWidgets import QWebEngineView

import folium

from gui.dialogs import LayerGenerationDialog
from net_generation.import_and_create_layers import generate_and_export_layers

class VisualizationTab(QWidget):
    layers_imported = pyqtSignal(dict)

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.layers = {}
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        # Initialisieren der Karte
        self.m = folium.Map(location=[51.1657, 10.4515], zoom_start=6)
        self.mapView = QWebEngineView()
        # Erstellen der Menüleiste in tab1
        self.menuBar = QMenuBar(self)
        self.menuBar.setFixedHeight(30)  # Setzen Sie eine spezifische Höhe
        fileMenu = self.menuBar.addMenu('Datei')

        # Erstellen und Hinzufügen der Aktion "Import Netzdaten"
        importAction = QAction('Import Netzdaten', self)
        importAction.triggered.connect(self.importNetData)
        fileMenu.addAction(importAction)

        generateAction = QAction('Layer generieren', self)
        generateAction.triggered.connect(self.openLayerGenerationDialog)
        fileMenu.addAction(generateAction)

        # Fügen Sie die Menüleiste dem Layout von tab1 hinzu
        layout.addWidget(self.menuBar)
        
        # Fügen Sie das QWebEngineView-Widget zum Layout von tab1 hinzu
        self.updateMapView()

        layout.addWidget(self.mapView)

        ### Liste importierter Layer ###
        self.layerList = QListWidget(self)
        self.layerList.setMaximumHeight(100)  # Setzen Sie eine maximale Höhe

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

    def connect_signals(self, calculation_tab):
        calculation_tab.data_added.connect(self.updateMapViewWithData)

    def updateMapViewWithData(self, map_data):
        for data in map_data:
            # Hinzufügen der Daten zur Karte
            self.loadNetData(data)
        self.updateMapView()

    def openLayerGenerationDialog(self):
        dialog = LayerGenerationDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            inputs = dialog.getInputs()
            self.generateAndImportLayers(inputs)

    def generateAndImportLayers(self, inputs):
        # Hier rufen Sie Ihre Funktion generate_and_export_layers auf
        generate_and_export_layers(inputs["streetLayer"], inputs["dataCsv"], 
                                float(inputs["xCoord"]), float(inputs["yCoord"]))

        # Automatisches Importieren der generierten Layer
        # Die Pfade zu den generierten Dateien müssen angegeben werden
        generatedLayers = {
            'HAST': "C:/Users/username/heating_network_generation/net_generation/HAST.geojson",
            'Rücklauf': "C:/Users/username/heating_network_generation/net_generation/Rücklauf.geojson",
            'Vorlauf': "C:/Users/username/heating_network_generation/net_generation/Vorlauf.geojson",
            'Erzeugeranlagen': "C:/Users/username/heating_network_generation/net_generation/Erzeugeranlagen.geojson"
        }

        for layerName, layerFile in generatedLayers.items():
            self.loadNetData(layerFile)

        # Auslösen des Signals mit den Pfaden der generierten Layer
        self.layers_imported.emit(generatedLayers)

    def importNetData(self):
        fnames, _ = QFileDialog.getOpenFileNames(self, 'Netzdaten importieren', '', 'GeoJSON Files (*.geojson);;All Files (*)')
        if fnames:
            layerNames = {}
            for fname in fnames:
                self.loadNetData(fname)
                basename = os.path.basename(fname)
                layerNames[basename.split('.')[0]] = fname  # Beispiel: 'HAST' : 'path/to/HAST.geojson'
            self.layers_imported.emit(layerNames)
            self.updateMapView()
    
    def calculate_map_center_and_zoom(self):
        if not self.layers:  # Wenn keine Layer vorhanden sind
            return [51.1657, 10.4515], 6  # Standardwerte

        # Berechnen der kombinierten Grenzen aller Layer
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
        zoom = 15  # Sie müssen möglicherweise einen Algorithmus entwickeln, um ein geeignetes Zoomlevel zu berechnen

        return [center_x, center_y], zoom
    
    def updateMapView(self):
        center, zoom = self.calculate_map_center_and_zoom()
        self.m = folium.Map(location=center, zoom_start=zoom)
        for layer in self.layers.values():
            self.m.add_child(layer)
        self.update_map_view(self.mapView, self.m)

    def loadNetData(self, filename, color=None):
        if color is None:
            color = "#{:06x}".format(random.randint(0, 0xFFFFFF))  # Zufällige Farbe, falls keine angegeben

        layer = self.addGeoJsonLayer(self.m, filename, color)
        if layer is not None:
            self.layers[filename] = layer

            # Überprüfen, ob der Layer bereits in der Liste ist
            if filename not in [self.layerList.item(i).text() for i in range(self.layerList.count())]:
                # Fügen Sie den Layer-Namen zum QListWidget hinzu, wenn er neu ist
                listItem = QListWidgetItem(filename)
                listItem.setBackground(QColor(color))  # Setzen Sie die Hintergrundfarbe
                listItem.setForeground(QBrush(QColor('#FFFFFF')))  # Setzen Sie eine kontrastreiche Textfarbe
                self.layerList.addItem(listItem)

            self.updateMapView()

    def load_geojson_data(self, filename):
        """ Lädt GeoJSON-Daten und gibt ein Geopandas DataFrame zurück """
        return gpd.read_file(filename)

    def update_map_view(self, mapView, map_obj):
        """ Aktualisiert die Kartenansicht in PyQt """
        map_file = 'results/map.html'
        map_obj.save(map_file)
        mapView.load(QUrl.fromLocalFile(os.path.abspath(map_file)))

    def addGeoJsonLayer(self, m, filename, color):
        gdf = self.load_geojson_data(filename)
        geojson_layer = folium.GeoJson(
            gdf,
            name=os.path.basename(filename),
            style_function=lambda feature: {
                'fillColor': color,
                'color': color,
                'weight': 1.5,
                'fillOpacity': 0.5,
            }
        )
        geojson_layer.add_to(m)
        return geojson_layer

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
            # Entfernen des alten Layers
            del self.layers[layerName]
            
            # Neuerstellen des Layers mit der neuen Farbe
            self.loadNetData(layerName, new_color)

            # Aktualisieren Sie die Farbe im QListWidget
            self.updateListItemColor(layerName, new_color)

    def updateListItemColor(self, layerName, new_color):
        for index in range(self.layerList.count()):
            listItem = self.layerList.item(index)
            if listItem.text() == layerName:
                listItem.setBackground(QColor(new_color))
                listItem.setForeground(QBrush(QColor('#FFFFFF')))  # Weiße Textfarbe für Kontrast
                break