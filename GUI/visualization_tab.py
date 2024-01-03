import os
import random
import geopandas as gpd

from PyQt5.QtCore import pyqtSignal, QUrl
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMenuBar, QAction, QFileDialog, \
    QHBoxLayout, QListWidget, QDialog, QProgressBar, QColorDialog, QListWidgetItem, QMessageBox
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWebEngineWidgets import QWebEngineView

import folium

from gui.dialogs import LayerGenerationDialog, DownloadOSMDataDialog, GeocodeAdressesDialog
from gui.threads import NetGenerationThread, FileImportThread

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

        downloadAction = QAction('Layer generieren', self)
        downloadAction.triggered.connect(self.openLayerGenerationDialog)
        fileMenu.addAction(downloadAction)

        downloadAction = QAction('Download OSM-Daten', self)
        downloadAction.triggered.connect(self.openDownloadOSMDataDialog)
        fileMenu.addAction(downloadAction)

        downloadAction = QAction('Adressdaten geocodieren', self)
        downloadAction.triggered.connect(self.openGeocodeAdressesDialog)
        fileMenu.addAction(downloadAction)

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

    def openDownloadOSMDataDialog(self):
        dialog = DownloadOSMDataDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            pass

    def openGeocodeAdressesDialog(self):
        dialog = GeocodeAdressesDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            pass

    def openLayerGenerationDialog(self):
        dialog = LayerGenerationDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            inputs = dialog.getInputs()
            self.generateAndImportLayers(inputs)

    def generateAndImportLayers(self, inputs):
        # Stellen Sie sicher, dass der vorherige Thread beendet wird
        if hasattr(self, 'netgenerationThread') and self.netgenerationThread.isRunning():
            self.netgenerationThread.terminate()
            self.netgenerationThread.wait()
        self.netgenerationThread = NetGenerationThread(inputs)
        self.netgenerationThread.calculation_done.connect(self.on_generation_done)
        self.netgenerationThread.calculation_error.connect(self.on_generation_error)
        self.netgenerationThread.start()
        self.progressBar.setRange(0, 0)  # Aktiviert den indeterministischen Modus

    def on_generation_done(self, results):
        self.progressBar.setRange(0, 1)
        filenames = ["C:/Users/jp66tyda/heating_network_generation/net_generation/HAST.geojson", "C:/Users/jp66tyda/heating_network_generation/net_generation/Rücklauf.geojson",
                     "C:/Users/jp66tyda/heating_network_generation/net_generation/Vorlauf.geojson", "C:/Users/jp66tyda/heating_network_generation/net_generation/Erzeugeranlagen.geojson"]
        self.loadNetData(filenames)
        
        generatedLayers = {
            'HAST': "C:/Users/jp66tyda/heating_network_generation/net_generation/HAST.geojson",
            'Rücklauf': "C:/Users/jp66tyda/heating_network_generation/net_generation/Rücklauf.geojson",
            'Vorlauf': "C:/Users/jp66tyda/heating_network_generation/net_generation/Vorlauf.geojson",
            'Erzeugeranlagen': "C:/Users/jp66tyda/heating_network_generation/net_generation/Erzeugeranlagen.geojson"
        }

        # Auslösen des Signals mit den Pfaden der generierten Layer
        self.layers_imported.emit(generatedLayers)

    def on_generation_error(self, error_message):
        QMessageBox.critical(self, "Berechnungsfehler", error_message)
        self.progressBar.setRange(0, 1)  # Deaktiviert den indeterministischen Modus

    def importNetData(self):
        fnames, _ = QFileDialog.getOpenFileNames(self, 'Netzdaten importieren', '', 'GeoJSON Files (*.geojson);;All Files (*)')
        if fnames:
            self.loadNetData(fnames)
    
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
        zoom = 17  # Sie müssen möglicherweise einen Algorithmus entwickeln, um ein geeignetes Zoomlevel zu berechnen

        return [center_x, center_y], zoom
    
    def updateMapView(self):
        center, zoom = self.calculate_map_center_and_zoom()
        self.m = folium.Map(location=center, zoom_start=zoom)
        for layer in self.layers.values():
            self.m.add_child(layer)
        self.update_map_view(self.mapView, self.m)

    def update_map_view(self, mapView, map_obj):
        """ Aktualisiert die Kartenansicht in PyQt """
        map_file = 'results/map.html'
        map_obj.save(map_file)
        mapView.load(QUrl.fromLocalFile(os.path.abspath(map_file)))

    def loadNetData(self, filenames, color=None):
        if not isinstance(filenames, list):
            filenames = [filenames]

        # Übergeben Sie die Farbe, falls angegeben, ansonsten wird eine zufällige Farbe im Thread generiert
        self.addGeoJsonLayer(self.m, filenames, color)


    # Diese Funktion startet nur den Thread und gibt nichts zurück.
    def addGeoJsonLayer(self, m, filenames, color):
        # Beenden Sie den vorherigen Thread, falls er läuft
        if hasattr(self, 'netgenerationThread') and self.netgenerationThread.isRunning():
            self.netgenerationThread.terminate()
            self.netgenerationThread.wait()

        # Starten Sie einen neuen Thread für alle Dateien
        self.netgenerationThread = FileImportThread(m, filenames, color)
        self.netgenerationThread.calculation_done.connect(self.on_import_done)
        self.netgenerationThread.calculation_error.connect(self.on_import_error)
        self.netgenerationThread.start()
        self.progressBar.setRange(0, 0)

    # Dieser Slot wird aufgerufen, wenn der Thread fertig ist.
    def on_import_done(self, results):
        self.progressBar.setRange(0, 1)
        for filename, geojson_data in results.items():
            # Generieren Sie eine zufällige Farbe für jeden Layer
            color = "#{:06x}".format(random.randint(0, 0xFFFFFF))

            # Fügen Sie den Layer zur Karte hinzu
            geojson_layer = folium.GeoJson(
                geojson_data['gdf'],
                name=geojson_data['name'],
                style_function=lambda feature, color=color: {
                    'fillColor': color,
                    'color': color,
                    'weight': 1.5,
                    'fillOpacity': 0.5,
                }
            )
            geojson_layer.add_to(self.m)

            # Fügen Sie den Layer hier zur Verwaltung hinzu
            self.layers[geojson_data['name']] = geojson_layer

            # Aktualisieren Sie das QListWidget
            if geojson_data['name'] not in [self.layerList.item(i).text() for i in range(self.layerList.count())]:
                listItem = QListWidgetItem(geojson_data['name'])
                listItem.setBackground(QColor(color))
                listItem.setForeground(QBrush(QColor('#FFFFFF')))
                self.layerList.addItem(listItem)

        self.updateMapView()

    def on_import_error(self, error_message):
        # Zeigen Sie eine Fehlermeldung an oder loggen Sie den Fehler.
        self.progressBar.setRange(0, 1)
        print("Fehler beim Importieren der GeoJSON-Daten:", error_message)
        # Zeigen Sie möglicherweise einen Dialog an oder aktualisieren Sie die Statusleiste.

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