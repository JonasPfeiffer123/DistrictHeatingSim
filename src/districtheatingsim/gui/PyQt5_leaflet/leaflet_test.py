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
import os

from PyQt5.QtWidgets import QApplication, QVBoxLayout, QPushButton, QWidget, QFileDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QObject, pyqtSlot
from PyQt5.QtWebChannel import QWebChannel

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

class LeafletTab(QWidget):
    def __init__(self):
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