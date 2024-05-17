import sys
import os

import geopandas as gpd
import pandas as pd
import numpy as np
import csv
from math import radians, sin, cos, sqrt, atan2
from shapely.geometry import box, Point
from shapely.ops import transform
import pyproj

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QDialog, QComboBox, QPushButton, \
    QFormLayout, QHBoxLayout, QFileDialog, QProgressBar, QMessageBox, QLabel, QWidget, \
    QTableWidget, QTableWidgetItem
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal

from pyproj import Transformer

from gui.threads import GeocodingThread
from geocoding.geocodingETRS89 import get_coordinates
from osm.import_osm_data_geojson import build_query, download_data, save_to_file
from osm.Wärmeversorgungsgebiete import clustering_quartiere_hdbscan, postprocessing_hdbscan, allocate_overlapping_area
from lod2.scripts.filter_LOD2 import spatial_filter_with_polygon, process_lod2, calculate_centroid_and_geocode
from lod2.scripts.heat_requirement_DIN_EN_12831 import Building

# defines the map path
def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist, ist der Basispfad der Temp-Ordner, wo PyInstaller alles extrahiert
        base_path = sys._MEIPASS
    else:
        # Wenn die Anwendung nicht eingefroren ist, ist der Basispfad der Ordner, in dem die Hauptdatei liegt
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return os.path.join(base_path, relative_path)
   
class LayerGenerationDialog(QDialog):
    accepted_inputs = pyqtSignal(dict)

    def __init__(self, base_path, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.visualization_tab = None  # Placeholder for the reference to VisualizationTab
        self.setWindowFlags(Qt.Tool | Qt.WindowTitleHint | Qt.CustomizeWindowHint)  # Setzt das Fenster im Vordergrund, ohne es modal zu machen
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Wärmenetzgenerierung')
        self.setGeometry(300, 300, 700, 400)

        layout = QVBoxLayout(self)

        formLayout = QFormLayout()

        self.fileInput, self.fileButton = self.createFileInput(f"{self.base_path}\Raumanalyse\Straßen.geojson")
        self.dataInput, self.dataCsvButton = self.createFileInput(f"{self.base_path}\Gebäudedaten\data_output_ETRS89.csv")

        self.locationModeComboBox = QComboBox(self)
        self.locationModeComboBox.addItems(["Koordinaten direkt eingeben", "Adresse eingeben", "Koordinaten aus csv laden"])
        self.locationModeComboBox.currentIndexChanged.connect(self.toggleLocationInputMode)

        self.coordSystemComboBox = QComboBox(self)
        self.coordSystemComboBox.addItems(["EPSG:25833", "WGS84"])

        self.coordInput = QLineEdit(self)
        self.coordInput.setText("480198.58,5711044.00")
        self.coordInput.setToolTip("Eingabe in folgender Form: 'X-Koordinate, Y-Koordinate'")
        self.addCoordButton = QPushButton("Koordinate hinzufügen", self)
        self.addCoordButton.clicked.connect(self.addCoordFromInput)

        self.addressInput = QLineEdit(self)
        self.addressInput.setText("Deutschland,Sachsen,Bad Muskau,Gablenzer Straße 4")
        self.addressInput.setToolTip("Eingabe in folgender Form: 'Land,Bundesland,Stadt,Adresse'")
        self.geocodeButton = QPushButton("Adresse geocodieren", self)
        self.geocodeButton.clicked.connect(self.geocodeAndAdd)

        self.importCsvButton = QPushButton("Koordinaten aus CSV laden", self)
        self.importCsvButton.clicked.connect(self.importCoordsFromCSV)

        self.deleteCoordButton = QPushButton("Ausgewählte Koordinate löschen", self)
        self.deleteCoordButton.clicked.connect(self.deleteSelectedRow)

        self.coordTable = QTableWidget(self)
        self.coordTable.setColumnCount(2)
        self.coordTable.setHorizontalHeaderLabels(["X-Koordinate", "Y-Koordinate"])

        self.generationModeComboBox = QComboBox(self)
        self.generationModeComboBox.addItems(["Advanced MST", "MST"])
        self.generationModeComboBox.currentIndexChanged.connect(self.toggleLocationInputMode)

        formLayout.addRow("GeoJSON-Straßen-Layer:", self.createFileInputLayout(self.fileInput, self.fileButton))
        formLayout.addRow("Datei Gebäudestandorte:", self.createFileInputLayout(self.dataInput, self.dataCsvButton))
        formLayout.addRow("Modus für Erzeugerstandort:", self.locationModeComboBox)
        formLayout.addRow("Koordinatensystem:", self.coordSystemComboBox)
        formLayout.addRow("Koordinaten eingeben:", self.coordInput)
        formLayout.addRow(self.addCoordButton)
        formLayout.addRow("Adresse für Geocoding:", self.addressInput)
        formLayout.addRow(self.geocodeButton)
        formLayout.addRow(self.importCsvButton)
        formLayout.addRow("Koordinatentabelle:", self.coordTable)
        formLayout.addRow(self.deleteCoordButton)
        formLayout.addRow("Netzgenerierungsmodus:", self.generationModeComboBox)

        layout.addLayout(formLayout)

        self.okButton = QPushButton("OK", self)
        self.okButton.clicked.connect(self.onAccept)
        self.cancelButton = QPushButton("Abbrechen", self)
        self.cancelButton.clicked.connect(self.reject)

        layout.addWidget(self.okButton)
        layout.addWidget(self.cancelButton)

        self.toggleLocationInputMode(0)
        self.setLayout(layout)

    def setVisualizationTab(self, visualization_tab):
        self.visualization_tab = visualization_tab

    def toggleLocationInputMode(self, index):
        self.coordSystemComboBox.setEnabled(index == 0)
        self.coordInput.setEnabled(index == 0)
        self.addCoordButton.setEnabled(index == 0)
        self.addressInput.setEnabled(index == 1)
        self.geocodeButton.setEnabled(index == 1)
        self.importCsvButton.setEnabled(index == 2)

    def createFileInputLayout(self, lineEdit, button):
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def createFileInput(self, default_path):
        lineEdit = QLineEdit(default_path)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.openFileDialog(lineEdit))
        return lineEdit, button

    def openFileDialog(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", f"{self.base_path}", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def addCoordFromInput(self):
        coords = self.coordInput.text().split(',')
        if len(coords) == 2:
            x, y = map(str.strip, coords)
            source_crs = self.coordSystemComboBox.currentText()
            x_transformed, y_transformed = self.transform_coordinates(float(x), float(y), source_crs)
            self.insertRowInTable(x_transformed, y_transformed)

    def geocodeAndAdd(self):
        address = self.addressInput.text()
        if address:
            x, y = get_coordinates(address)  # Implementierung der Geocoding-Funktion nötig
            if x and y:
                self.insertRowInTable(str(x), str(y))

    def importCoordsFromCSV(self):
        filename, _ = QFileDialog.getOpenFileName(self, "CSV-Datei auswählen", f"{self.base_path}", "CSV Files (*.csv)")
        if filename:
            data = pd.read_csv(filename, delimiter=';', usecols=['UTM_X', 'UTM_Y'])
            for _, row in data.iterrows():
                self.insertRowInTable(str(row['UTM_X']), str(row['UTM_Y']))

    def transform_coordinates(self, x, y, source_crs):
        if source_crs == "WGS84":
            transformer = Transformer.from_crs("EPSG:4326", "EPSG:25833", always_xy=True)
        else:
            transformer = Transformer.from_crs("EPSG:25833", "EPSG:25833", always_xy=True)
        x_transformed, y_transformed = transformer.transform(x, y)
        return x_transformed, y_transformed

    def insertRowInTable(self, x, y):
        row_count = self.coordTable.rowCount()
        self.coordTable.insertRow(row_count)
        self.coordTable.setItem(row_count, 0, QTableWidgetItem(str(x)))
        self.coordTable.setItem(row_count, 1, QTableWidgetItem(str(y)))

    def deleteSelectedRow(self):
        selected_row = self.coordTable.currentRow()
        if selected_row >= 0:
            self.coordTable.removeRow(selected_row)

    def getInputs(self):
        coordinates = []
        for row in range(self.coordTable.rowCount()):
            x = self.coordTable.item(row, 0).text()
            y = self.coordTable.item(row, 1).text()
            if x and y:
                coordinates.append((float(x), float(y)))

        return {
            "streetLayer": self.fileInput.text(),
            "dataCsv": self.dataInput.text(),
            "coordinates": coordinates,
            "generation_mode": self.generationModeComboBox.currentText()
        }

    def onAccept(self):
        inputs = self.getInputs()
        self.accepted_inputs.emit(inputs)
        self.accept()

class DownloadOSMDataDialog(QDialog):
    def __init__(self, base_path, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.tags_to_download = []
        self.tagsLayoutList = []

        self.standard_tags = [
            {"highway": "primary"},
            {"highway": "secondary"},
            {"highway": "tertiary"},
            {"highway": "residential"},
            {"highway": "living_street"}
        ]

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Download OSM-Data")
        self.setGeometry(300, 300, 400, 400)

        layout = QVBoxLayout(self)

        # Stadtname Eingabefeld
        self.cityLabel = QLabel("Stadt, für die Straßendaten heruntergeladen werden sollen:")
        self.cityLineEdit = QLineEdit("Zittau")
        layout.addWidget(self.cityLabel)
        layout.addWidget(self.cityLineEdit)
        
        # Dateiname Eingabefeld
        self.filenameLabel = QLabel("Dateiname, unter dem die Straßendaten als geojson gespeichert werden sollen:")
        self.filenameLineEdit, fileButton = self.createFileInput(f"{self.base_path}\Raumanalyse\Straßen.geojson")
        layout.addWidget(self.filenameLabel)
        layout.addLayout(self.createFileInputLayout(self.filenameLineEdit, fileButton))

        # Dropdown-Menü für einzelne Standard-Tags
        self.standardTagsLabel = QLabel("Aktuell auswählbare Straßenarten:")
        self.standardTagsComboBox = QComboBox(self)
        for tag in self.standard_tags:
            key = next(iter(tag))
            value = tag[key]
            self.standardTagsComboBox.addItem(f"{key}: {value}")

        layout.addWidget(self.standardTagsLabel)
        layout.addWidget(self.standardTagsComboBox)

        # Button zum Laden eines ausgewählten Standard-Tags
        self.loadStandardTagButton = QPushButton("Standard-Tag hinzufügen", self)
        self.loadStandardTagButton.clicked.connect(self.loadSelectedStandardTag)
        layout.addWidget(self.loadStandardTagButton)

        # Tags-Auswahl
        self.tagsLayout = QFormLayout()
        layout.addLayout(self.tagsLayout)
        
        # Buttons zum Hinzufügen/Entfernen von Tags
        #self.addTagButton = QPushButton("Tag hinzufügen", self)
        #self.addTagButton.clicked.connect(self.addTagField)
        #layout.addWidget(self.addTagButton)

        self.removeTagButton = QPushButton("Tag entfernen", self)
        self.removeTagButton.clicked.connect(self.removeTagField)
        layout.addWidget(self.removeTagButton)

        # Abfrage-Button
        self.queryButton = QPushButton("Abfrage starten", self)
        self.queryButton.clicked.connect(self.startQuery)
        layout.addWidget(self.queryButton)
        
        # Buttons für OK und Abbrechen
        self.okButton = QPushButton("OK", self)
        self.okButton.clicked.connect(self.accept)
        layout.addWidget(self.okButton)

        self.cancelButton = QPushButton("Abbrechen", self)
        layout.addWidget(self.cancelButton)

    def createFileInput(self, default_path):
        lineEdit = QLineEdit(default_path)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def createFileInputLayout(self, lineEdit, button):
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def selectFile(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def addTagField(self, key="", value=""):
        # Sicherstellen, dass key und value immer Strings sind
        key = str(key) if key is not None else ""
        value = str(value) if value is not None else ""

        keyLineEdit = QLineEdit(key)
        valueLineEdit = QLineEdit(value)
        self.tagsLayout.addRow(keyLineEdit, valueLineEdit)

        self.tagsLayoutList.append((keyLineEdit, valueLineEdit))
        self.tags_to_download.append((key, value))
        print(self.tags_to_download)

    def removeTagField(self):
        if self.tags_to_download:
            keyLineEdit, valueLineEdit = self.tagsLayoutList.pop()
            self.tags_to_download.pop()
            self.tagsLayout.removeRow(keyLineEdit)
            print(self.tags_to_download)

    def loadAllStandardTags(self):
        for tag in self.standard_tags:
            key = next(iter(tag))
            value = tag[key]
            self.addTagField(key, value)

    def loadSelectedStandardTag(self):
        selected_tag_index = self.standardTagsComboBox.currentIndex()
        tag = self.standard_tags[selected_tag_index]
        key = next(iter(tag))
        value = tag[key]
        self.addTagField(key, value)
    
    def startQuery(self):
        # Daten sammeln
        #postal_code = self.postalCodeLineEdit.text()
        self.filename = self.filenameLineEdit.text()
        print(self.tags_to_download)
        
        city_name =self.cityLineEdit.text()

        # Erstelle die Overpass-Abfrage
        query = build_query(city_name, self.tags_to_download, element_type="way")
        # Lade die Daten herunter
        geojson_data = download_data(query, element_type="way")
        # Speichere die Daten als GeoJSON
        save_to_file(geojson_data, self.filename)
        gdf = gpd.read_file(self.filename, driver='GeoJSON').to_crs(epsg=25833)
        gdf.to_file(self.filename, driver='GeoJSON')

        QMessageBox.information(self, "Erfolg", f"Abfrageergebnisse gespeichert in {self.filename}")
            
        # Rufen Sie die loadNetData-Methode des Haupt-Tabs auf
        self.parent().loadNetData(self.filename)

class OSMBuildingQueryDialog(QDialog):
    def __init__(self, base_path, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        self.setWindowTitle("OSM Gebäudeabfrage")

        # Stadtname Eingabefeld
        self.cityLineEdit = QLineEdit(self)
        layout.addWidget(QLabel("Stadt, deren OSM-Gebäudedaten heruntergeladen werden sollen:"))
        layout.addWidget(self.cityLineEdit)

        # Dateiname Eingabefeld
        self.filenameLineEdit = QLineEdit(f"{self.base_path}\Raumanalyse\output_buildings.geojson", self)
        layout.addWidget(QLabel("Dateiname, unter dem die Gebäudedaten als geojson gespeichert werde sollen:"))
        layout.addWidget(self.filenameLineEdit)

        # Dropdown für Filteroptionen
        self.filterComboBox = QComboBox(self)
        self.filterComboBox.addItem("Kein Filter")
        self.filterComboBox.addItem("Filtern mit Koordinatenbereich")
        self.filterComboBox.addItem("Filtern mit zentralen Koordinaten und Radius als Abstand")
        self.filterComboBox.addItem("Filtern mit Adressen aus CSV")
        self.filterComboBox.addItem("Filtern mit Polygon-geoJSON")
        layout.addWidget(QLabel("Filteroptionen für die Gebäudedaten:"))
        layout.addWidget(self.filterComboBox)

        # Widgets für Koordinaten
        # Koordinaten Eingabefelder
        self.coordWidget = QWidget(self)
        coordLayout = QVBoxLayout(self.coordWidget)
        self.minLatLineEdit = QLineEdit(self)
        self.minLatLineEdit.setPlaceholderText("Minimale Breite")
        coordLayout.addWidget(QLabel("Minimale Breite:"))
        coordLayout.addWidget(self.minLatLineEdit)

        self.minLonLineEdit = QLineEdit(self)
        self.minLonLineEdit.setPlaceholderText("Minimale Länge")
        coordLayout.addWidget(QLabel("Minimale Länge:"))
        coordLayout.addWidget(self.minLonLineEdit)

        self.maxLatLineEdit = QLineEdit(self)
        self.maxLatLineEdit.setPlaceholderText("Maximale Breite")
        coordLayout.addWidget(QLabel("Maximale Breite:"))
        coordLayout.addWidget(self.maxLatLineEdit)

        self.maxLonLineEdit = QLineEdit(self)
        self.maxLonLineEdit.setPlaceholderText("Maximale Länge")
        coordLayout.addWidget(QLabel("Maximale Länge:"))
        coordLayout.addWidget(self.maxLonLineEdit)
        layout.addWidget(self.coordWidget)

        # Widgets für Koordinaten und Radius
        # Koordinaten
        self.coordRadiusWidget = QWidget(self)
        coordRadiusLayout = QVBoxLayout(self.coordRadiusWidget)
        self.centerLatLineEdit = QLineEdit(self)
        self.centerLatLineEdit.setPlaceholderText("Breite")
        coordRadiusLayout.addWidget(QLabel("Minimale Breite:"))
        coordRadiusLayout.addWidget(self.centerLatLineEdit)

        self.centerLonLineEdit = QLineEdit(self)
        self.centerLonLineEdit.setPlaceholderText("Minimale Länge")
        coordRadiusLayout.addWidget(QLabel("Minimale Länge:"))
        coordRadiusLayout.addWidget(self.centerLonLineEdit)

        # Radius
        self.radiusLineEdit = QLineEdit(self)
        self.radiusLineEdit.setPlaceholderText("Radius in Metern")
        coordRadiusLayout.addWidget(QLabel("Radius in Metern:"))
        coordRadiusLayout.addWidget(self.radiusLineEdit)
        layout.addWidget(self.coordRadiusWidget)

        # Widget für Adressen aus CSV
        self.csvWidget = QWidget(self)
        csvLayout = QVBoxLayout(self.csvWidget)
        self.addressCsvLineEdit, self.addressCsvButton = self.createFileInput(f"{self.base_path}/")
        csvLayout.addLayout(self.createFileInputLayout(self.addressCsvLineEdit, self.addressCsvButton))
        layout.addWidget(self.csvWidget)

        # Widget für Gebäude aus geoJSON
        self.geoJSONWidget = QWidget(self)
        geoJSONLayout = QVBoxLayout(self.geoJSONWidget)
        self.geoJSONLineEdit, self.geoJSONButton = self.createFileInput(f"{self.base_path}/")
        geoJSONLayout.addLayout(self.createFileInputLayout(self.geoJSONLineEdit, self.geoJSONButton))
        layout.addWidget(self.geoJSONWidget)

        # Abfrage-Button
        self.queryButton = QPushButton("Abfrage starten", self)
        self.queryButton.clicked.connect(self.startQuery)
        layout.addWidget(self.queryButton)

        # OK und Abbrechen Buttons
        self.okButton = QPushButton("OK", self)
        self.okButton.clicked.connect(self.accept)
        layout.addWidget(self.okButton)
        self.cancelButton = QPushButton("Abbrechen", self)
        self.cancelButton.clicked.connect(self.reject)
        layout.addWidget(self.cancelButton)

        # Verbinden Sie das Dropdown mit der Anzeige der entsprechenden Filteroptionen
        self.filterComboBox.currentIndexChanged.connect(self.showSelectedFilter)

        # Zu Beginn nur Standardmethode anzeigen
        self.showSelectedFilter()

    def createFileInput(self, default_path):
        lineEdit = QLineEdit(default_path)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def selectFile(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def createFileInputLayout(self, lineEdit, button):
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def showSelectedFilter(self):
        selected_filter = self.filterComboBox.currentText()
        self.coordWidget.setVisible(selected_filter == "Filtern mit Koordinatenbereich")
        self.coordRadiusWidget.setVisible(selected_filter == "Filtern mit zentralen Koordinaten und Radius als Abstand")
        self.csvWidget.setVisible(selected_filter == "Filtern mit Adressen aus CSV")
        self.geoJSONWidget.setVisible(selected_filter == "Filtern mit Polygon-geoJSON")

    def haversine(self, lat1, lon1, lat2, lon2):
        # Radius der Erde in Metern
        earth_radius = 6371000.0

        # Umrechnung von Grad in Radian
        lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])

        # Deltas der Koordinaten
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        # Haversine-Formel
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = earth_radius * c

        return distance

    def startQuery(self):
        city_name = self.cityLineEdit.text()
        filename = self.filenameLineEdit.text()
        selected_filter = self.filterComboBox.currentText()

        if not city_name or not filename:
            QMessageBox.warning(self, "Warnung", "Bitte geben Sie Stadtname und Ausgabedatei an.")
            return

        # Führen Sie hier Ihre Abfrage-Logik durch
        tags = {"building": "yes"}  # oder andere Tags
        query = build_query(city_name, tags, element_type="building")
        geojson_data = download_data(query, element_type="building")
        gdf = self.prepare_gdf(geojson_data)

        if selected_filter == "Filtern mit Koordinatenbereich":
            self.filter_with_bbox(gdf, filename)
        elif selected_filter == "Filtern mit zentralen Koordinaten und Radius als Abstand":
            self.filter_with_central_coords_and_radius(gdf, filename)
        elif selected_filter == "Filtern mit Adressen aus CSV":
            self.filter_with_csv_addresses(gdf, filename)
        elif selected_filter == "Filtern mit Polygon-geoJSON":
            self.filter_with_polygon(gdf, filename)
        else:
            gdf.to_file(filename, driver='GeoJSON')

        QMessageBox.information(self, "Erfolg", f"Abfrageergebnisse gespeichert in {filename}")
        # Rufen Sie die loadNetData-Methode des Haupt-Tabs auf
        self.parent().loadNetData(filename)

    def prepare_gdf(self, geojson_data):
        gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
        gdf.crs = "EPSG:4326"
        return gdf.to_crs(epsg=25833)

    def filter_with_bbox(self, gdf, filename):
        min_lat = float(self.minLatLineEdit.text())
        min_lon = float(self.minLonLineEdit.text())
        max_lat = float(self.maxLatLineEdit.text())
        max_lon = float(self.maxLonLineEdit.text())

        # Erstelle ein Bounding Box Polygon im WGS84 Koordinatensystem
        bbox_polygon_wgs84 = box(min_lon, min_lat, max_lon, max_lat)

        # Projektionstransformation vorbereiten von WGS84 (EPSG:4326) zu Zielkoordinatensystem des gdf
        project_to_target_crs = pyproj.Transformer.from_proj(
            pyproj.Proj(init='epsg:4326'),  # Quellkoordinatensystem (WGS84)
            pyproj.Proj(init='epsg:25833'),  # Zielkoordinatensystem des gdf
            always_xy=True
        )

        # Transformiere das Bounding Box Polygon ins Zielkoordinatensystem des gdf
        bbox_polygon_transformed = transform(project_to_target_crs.transform, bbox_polygon_wgs84)

        # Filtere die GeoDataFrame basierend auf dem transformierten Bounding Box Polygon
        gdf_filtered = gdf[gdf.intersects(bbox_polygon_transformed)]

        # Speichern der gefilterten GeoDataFrame
        gdf_filtered.to_file(filename, driver='GeoJSON')

    def filter_with_central_coords_and_radius(self, gdf, filename):
        center_lat = float(self.centerLatLineEdit.text())
        center_lon = float(self.centerLonLineEdit.text())
        radius = float(self.radiusLineEdit.text())  # Radius in Kilometern für geopy.distance

        center_point_wgs84 = Point(center_lon, center_lat)
        project = pyproj.Transformer.from_proj(
            pyproj.Proj(init='epsg:4326'),  # Quellkoordinatensystem (WGS84)
            pyproj.Proj(init='epsg:25833')  # Zielkoordinatensystem (hier beispielhaft EPSG:25833)
        )

        center_point_transformed = transform(project.transform, center_point_wgs84)
        gdf['distance'] = gdf.geometry.distance(center_point_transformed)
        radius_m = radius
        gdf_filtered = gdf[gdf['distance'] <= radius_m]
        gdf_filtered.to_file(filename, driver='GeoJSON')

    def filter_with_csv_addresses(self, gdf, filename):
        address_csv_file = self.addressCsvLineEdit.text()
        if address_csv_file:
            csv_df = pd.read_csv(address_csv_file, sep=';')
            addresses_from_csv = csv_df['Adresse'].tolist()
            gdf['full_address'] = gdf['addr:street'] + ' ' + gdf['addr:housenumber']
            gdf_filtered = gdf[gdf['full_address'].isin(addresses_from_csv)]
            gdf_filtered.to_file(filename, driver='GeoJSON')

    def filter_with_polygon(self, gdf, filename):
        geoJSON_file = self.geoJSONLineEdit.text()
        if geoJSON_file:
            # Polygon aus der geoJSON-Datei laden
            polygon_gdf = gpd.read_file(geoJSON_file)
            
            # Annahme: Das Polygon ist das erste Element im GeoDataFrame
            # Falls das Polygon-GeoJSON mehrere Polygone enthält, könnte hier eine Anpassung notwendig sein
            polygon = polygon_gdf.geometry.iloc[0]
            
            # Filtern der Gebäude, die innerhalb des Polygons liegen
            # Verwendung der 'within'-Methode, um zu überprüfen, ob ein Punkt/Gebäude innerhalb des Polygons liegt
            filtered_gdf = gdf[gdf.geometry.within(polygon)]

            filtered_gdf.to_file(filename, driver='GeoJSON')

class SpatialAnalysisDialog(QDialog):
    def __init__(self, base_path, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        self.setWindowTitle("Räumliche Analyse")
        self.setGeometry(300, 300, 600, 400)

        self.explanationLabel = QLabel("""Hier können Gebäude aus dem OSM-download räumlich geclustert werden. \nEs werden den Gebäuden zufällig Wärmebedarfe zugewiesen, wodurch sich für die einzelnen Cluster spez. Wärmebedarfe ergeben. \nAnhand eines intern definierten Schwellwerts lassen sich so Versorgungsgebiete definieren. \nIm Ergebnis werden alle generierten Cluster sowie die ermittelten Gebäude zur Wärmeversorgung mit Wärmenetzen ausgegeben. \nDiese Funktionen dienen lediglich der demonstration grundsätzlicher Möglichkeiten und könnte in Zukunft hin zur Nutzbarkeit ausgebaut werden.""")
        layout.addWidget(self.explanationLabel)

        # Gebäude-geojson
        self.geojsonWidget = QWidget(self)
        geojsonLayout = QVBoxLayout(self.geojsonWidget)
        self.geojsonLabel = QLabel("Dateiname der geojson mit den Gebäuden die geclustert werden sollen.")
        self.geojsonLineEdit, self.geojsonButton = self.createFileInput(f"{self.base_path}\Raumanalyse\output_buildings.geojson")
        geojsonLayout.addLayout(self.createFileInputLayout(self.geojsonLineEdit, self.geojsonButton))
        layout.addWidget(self.geojsonLabel)
        layout.addWidget(self.geojsonWidget)

        # Quartier-geojson
        self.geojsonareaWidget = QWidget(self)
        geojsonareaLayout = QVBoxLayout(self.geojsonareaWidget)
        self.geojsonareaLabel = QLabel("Dateiname der geojson in der die Polygone der ermittelten Quartiere/Cluster gespeichert werden sollen.")
        self.geojsonareaLineEdit, self.geojsonareaButton = self.createFileInput(f"{self.base_path}\Raumanalyse\quartiere.geojson")
        geojsonareaLayout.addLayout(self.createFileInputLayout(self.geojsonareaLineEdit, self.geojsonareaButton))
        layout.addWidget(self.geojsonareaLabel)
        layout.addWidget(self.geojsonareaWidget)

        # Wärmenetzgebiet-Gebäude-geojson
        self.geojsonfilteredbuildingsWidget = QWidget(self)
        geojsonfilteredbuildingsLayout = QVBoxLayout(self.geojsonfilteredbuildingsWidget)
        self.geojsonfilteredbuildingsLabel = QLabel("Dateiname der geojson in der die nach Wärmenetzversorgung gefilterten gebäude gespeichert werden sollen.")
        self.geojsonfilteredbuildingsLineEdit, self.geojsonfilteredbuildingsButton = self.createFileInput(f"{self.base_path}\Raumanalyse\waermenetz_buildings.geojson")
        geojsonfilteredbuildingsLayout.addLayout(self.createFileInputLayout(self.geojsonfilteredbuildingsLineEdit, self.geojsonfilteredbuildingsButton))
        layout.addWidget(self.geojsonfilteredbuildingsLabel)
        layout.addWidget(self.geojsonfilteredbuildingsWidget)

        # Abfrage-Button
        self.queryButton = QPushButton("Berechnung Starten", self)
        self.queryButton.clicked.connect(self.calculate)
        layout.addWidget(self.queryButton)

        # OK und Abbrechen Buttons
        self.okButton = QPushButton("OK", self)
        self.okButton.clicked.connect(self.accept)
        layout.addWidget(self.okButton)
        self.cancelButton = QPushButton("Abbrechen", self)
        self.cancelButton.clicked.connect(self.reject)
        layout.addWidget(self.cancelButton)


    def createFileInput(self, default_path):
        lineEdit = QLineEdit(default_path)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def selectFile(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def createFileInputLayout(self, lineEdit, button):
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def calculate_building_data(self, gdf, output_filename):
        # Berechnen der Fläche jedes Gebäudes in Quadratmetern
        gdf['area_sqm'] = gdf['geometry'].area
        # Hinzufügen der Spalte für spezifischen Wärmebedarf mit Zufallszahlen zwischen 50 und 200
        gdf['spez. Wärmebedarf [kWh/m²*a]'] = np.random.uniform(50, 200, gdf.shape[0])
        # Hinzufügen der Spalte für die Anzahl der Geschosse (konstanter Wert 3)
        gdf['Anzahl Geschosse'] = 3
        # Berechnen des Jahreswärmebedarfs
        gdf['Jahreswärmebedarf [kWh/a]'] = gdf['spez. Wärmebedarf [kWh/m²*a]'] * gdf['Anzahl Geschosse'] * gdf['area_sqm']
        # Speichern des erweiterten GeoDataFrame in eine neue GeoJSON-Datei
        gdf.to_file(output_filename, driver='GeoJSON')

        return gdf

    def calculate(self):
        geojson_file_buildings = self.geojsonLineEdit.text()
        geojson_file_areas = self.geojsonareaLineEdit.text()
        geojson_file_filtered_buildings = self.geojsonfilteredbuildingsLineEdit.text()
        gdf = gpd.read_file(geojson_file_buildings, driver='GeoJSON').to_crs(epsg=25833)
        ignore_types = ['ruins', 'greenhouse', 'shed', 'silo', 'slurry_tank', 
                    'toilets', 'hut', 'cabin', 'ger', 'static_caravan', 
                    'construction', 'cowshed', 'garage', 'garages', 'carport',
                    'farm_auxiliary', 'roof', 'digester']

        # Filtere Gebäude heraus, die ignorierten Typen entsprechen
        gdf = gdf[~gdf['building'].isin(ignore_types)]

        gdf = self.calculate_building_data(gdf, geojson_file_buildings)
        
        quartiere = clustering_quartiere_hdbscan(gdf)
        quartiere = postprocessing_hdbscan(quartiere)
        quartiere = allocate_overlapping_area(quartiere)
        quartiere.to_file(geojson_file_areas, driver='GeoJSON')

        # Filtern und speichern Sie Gebäude in Clustern mit der Versorgungsart "Wärmenetzversorgung"
        waermenetz_buildings = gdf[gdf['quartier_label'].isin(quartiere[quartiere['Versorgungsgebiet'] == 'Wärmenetzversorgung'].index)]

        # Lassen Sie nur die benötigte Geometriespalte (z.B. 'geometry') in waermenetz_buildings
        waermenetz_buildings = waermenetz_buildings[['geometry']]

        # Speichern Sie die gefilterten Gebäude in eine separate GeoJSON-Datei
        waermenetz_buildings.to_file(geojson_file_filtered_buildings, driver='GeoJSON')

        # Rufen Sie die loadNetData-Methode des Haupt-Tabs auf
        self.parent().loadNetData(geojson_file_filtered_buildings)
        self.parent().loadNetData(geojson_file_areas)

class GeocodeAddressesDialog(QDialog):
    def __init__(self, base_path, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Adressdaten geocodieren")
        self.setGeometry(300, 300, 600, 200)  # Anpassung der Fenstergröße
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)  # Abstand zwischen den Widgets
        layout.setContentsMargins(10, 10, 10, 10)  # Rand des Layouts

        font = QFont()
        font.setPointSize(10)  # Größere Schrift für bessere Lesbarkeit
        
        # Eingabefeld für die Eingabedatei
        self.inputfilenameLineEdit, inputFileButton = self.createFileInput(f"{self.base_path}\Gebäudedaten\data_input.csv", font)
        layout.addLayout(self.createFileInputLayout("Eingabedatei:", self.inputfilenameLineEdit, inputFileButton, font))
        
        # Eingabefeld für die Ausgabedatei
        self.outputfilenameLineEdit, outputFileButton = self.createFileInput(f"{self.base_path}\Gebäudedaten\data_output_ETRS89.csv", font)
        layout.addLayout(self.createFileInputLayout("Ausgabedatei:", self.outputfilenameLineEdit, outputFileButton, font))
        
        # Buttons für OK und Abbrechen in einem horizontalen Layout
        buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK", self)
        self.okButton.setFont(font)
        self.okButton.clicked.connect(self.onAccept)
        self.cancelButton = QPushButton("Abbrechen", self)
        self.cancelButton.setFont(font)
        self.cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(self.okButton)
        buttonLayout.addWidget(self.cancelButton)
        layout.addLayout(buttonLayout)

        # Verbesserte Fortschrittsanzeige
        self.progressBar = QProgressBar(self)
        self.progressBar.setFont(font)
        layout.addWidget(self.progressBar)

    def createFileInput(self, default_path, font):
        lineEdit = QLineEdit(default_path)
        lineEdit.setFont(font)
        button = QPushButton("Durchsuchen")
        button.setFont(font)
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def createFileInputLayout(self, label_text, lineEdit, button, font):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setFont(font)
        layout.addWidget(label)
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def selectFile(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def onAccept(self):
        # Daten sammeln
        self.inputfilename = self.inputfilenameLineEdit.text()
        self.outputfilename = self.outputfilenameLineEdit.text()
        
        # Abfrage erstellen und Daten herunterladen
        self.geocodeAdresses(self.inputfilename, self.outputfilename)

    # Die Methode des Dialogs, die die anderen Funktionen aufruft
    def geocodeAdresses(self, inputfilename, outputfilename):
        # Stellen Sie sicher, dass der vorherige Thread beendet wird
        if hasattr(self, 'geocodingThread') and self.geocodingThread.isRunning():
            self.geocodingThread.terminate()
            self.geocodingThread.wait()
        self.geocodingThread = GeocodingThread(inputfilename, outputfilename)
        self.geocodingThread.calculation_done.connect(self.on_generation_done)
        self.geocodingThread.calculation_error.connect(self.on_generation_error)
        self.geocodingThread.start()
        self.progressBar.setRange(0, 0)  # Aktiviert den indeterministischen Modus

    def on_generation_done(self, results):
        self.accept()

    def on_generation_error(self, error_message):
        QMessageBox.critical(self, "Fehler beim Geocoding", str(error_message))
        self.progressBar.setRange(0, 1)  # Deaktiviert den indeterministischen Modus

class ProcessLOD2DataDialog(QDialog):
    def __init__(self, base_path, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.initUI()
        self.comboBoxBuildingTypesItems = pd.read_csv(get_resource_path('lod2\data\standard_u_values_TABULA.csv'), sep=";")['Typ'].unique().tolist()

    def initUI(self):
        self.setWindowTitle("Verarbeitung LOD2-Daten")
        self.setGeometry(200, 200, 1200, 1000)  # Anpassung der Fenstergröße
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)  # Abstand zwischen den Widgets
        layout.setContentsMargins(10, 10, 10, 10)  # Rand des Layouts

        font = QFont()
        font.setPointSize(10)  # Größere Schrift für bessere Lesbarkeit
        
        # Eingabefeld für die Eingabe-LOD2-geojson
        self.inputLOD2geojsonLineEdit, inputLOD2geojsonButton = self.createFileInput(f"{self.base_path}\\Gebäudedaten\\lod2_data\\lod2_data.geojson", font)
        layout.addLayout(self.createFileInputLayout("Eingabe-LOD2-geojson:", self.inputLOD2geojsonLineEdit, inputLOD2geojsonButton, font))

        # Eingabefeld für die Eingabe-Filter-Polygon-shapefile
        self.inputfilterPolygonLineEdit, inputfilterPolygonButton = self.createFileInput(f"{self.base_path}\\Gebäudedaten\\lod2_data\\quartier_1.geojson", font)
        layout.addLayout(self.createFileInputLayout("Eingabe-Filter-Polygon-shapefile:", self.inputfilterPolygonLineEdit, inputfilterPolygonButton, font))

        # Eingabefeld für die Ausgabe-LOD2-geojson
        self.outputLOD2geojsonLineEdit, outputLOD2geojsonButton = self.createFileInput(f"{self.base_path}\\Gebäudedaten\\lod2_data\\filtered_LOD_quartier_1.geojson", font)
        layout.addLayout(self.createFileInputLayout("Ausgabe-LOD2-geojson:", self.outputLOD2geojsonLineEdit, outputLOD2geojsonButton, font))
        
        # Eingabefeld für die Ausgabe-csv
        #self.outputcsvLineEdit, outputcsvButton = self.createFileInput(f"{self.base_path}/Gebäudedaten/building_data.csv", font)
        #layout.addLayout(self.createFileInputLayout("Ausgabe-csv:", self.outputcsvLineEdit, outputcsvButton, font))

        self.loadDataButton = QPushButton("LOD2-Daten filtern und in Karte laden", self)
        self.loadDataButton.clicked.connect(self.processData)
        layout.addWidget(self.loadDataButton)

        self.loadDataButton = QPushButton("gefilterte Daten laden und anzeigen", self)
        self.loadDataButton.clicked.connect(self.loadData)
        layout.addWidget(self.loadDataButton)

        self.tableWidget = QTableWidget(self)
        self.tableWidget.setColumnCount(19)
        self.tableWidget.setHorizontalHeaderLabels(['Adresse', 'UTM_X', 'UTM_Y', 'Grundfläche', 'Wandfläche', 'Dachfläche', 'Volumen', 'Nutzungstyp', 'Typ', 'Gebäudezustand', 
                                                    'ww_demand_Wh_per_m2', 'air_change_rate', 'floors', 'fracture_windows', 'fracture_doors', 'min_air_temp', 
                                                    'room_temp', 'max_air_temp_heating', 'Jährlicher Wärmebedarf in kWh'])
        
        layout.addWidget(self.tableWidget)

        self.saveDataButton = QPushButton("Daten speichern", self)
        self.saveDataButton.clicked.connect(self.saveData)
        layout.addWidget(self.saveDataButton)

        self.loadDataButton = QPushButton("Daten laden", self)
        self.loadDataButton.clicked.connect(self.loadDataFromFile)
        layout.addWidget(self.loadDataButton)

        self.heatCalcButton = QPushButton("Wärmebedarf berechnen", self)
        self.heatCalcButton.clicked.connect(self.calculateHeatDemand)
        layout.addWidget(self.heatCalcButton)

        self.buildingCSVButton = QPushButton("Gebäude-csv für Netzgenerierung erstellen", self)
        self.buildingCSVButton.clicked.connect(self.createBuildingCSV)
        layout.addWidget(self.buildingCSVButton)
        
        # Buttons für OK und Abbrechen in einem horizontalen Layout
        buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK", self)
        self.okButton.setFont(font)
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Abbrechen", self)
        self.cancelButton.setFont(font)
        self.cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(self.okButton)
        buttonLayout.addWidget(self.cancelButton)
        layout.addLayout(buttonLayout)

        # Verbesserte Fortschrittsanzeige
        self.progressBar = QProgressBar(self)
        self.progressBar.setFont(font)
        layout.addWidget(self.progressBar)

    def createFileInput(self, default_path, font):
        lineEdit = QLineEdit(default_path)
        lineEdit.setFont(font)
        button = QPushButton("Durchsuchen")
        button.setFont(font)
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def createFileInputLayout(self, label_text, lineEdit, button, font):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setFont(font)
        layout.addWidget(label)
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def selectFile(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def processData(self):
        self.inputLOD2geojsonfilename = self.inputLOD2geojsonLineEdit.text()
        self.inputfilterPolygonfilename = self.inputfilterPolygonLineEdit.text()
        self.outputLOD2geojsonfilename = self.outputLOD2geojsonLineEdit.text()
        self.outputcsvfilename = f'{self.base_path}\Gebäudedaten\building_data.csv' # self.outputcsvLineEdit.text()
        spatial_filter_with_polygon(self.inputLOD2geojsonfilename, self.inputfilterPolygonfilename, self.outputLOD2geojsonfilename)
        # Rufen Sie die loadNetData-Methode des Haupt-Tabs auf
        self.parent().loadNetData(self.outputLOD2geojsonfilename)

    def loadData(self):
        STANDARD_VALUES = {
        'air_change_rate': 0.5, 'floors': 4, 'fracture_windows': 0.10, 'fracture_doors': 0.01,
        'min_air_temp': -15, 'room_temp': 20, 'max_air_temp_heating': 15, 'ww_demand_Wh_per_m2': 12800
        }
        # Annahme: Die process_lod2 Funktion wurde entsprechend erweitert, um Adressinformationen zu liefern
        self.outputLOD2geojsonfilename = self.outputLOD2geojsonLineEdit.text()
        building_info = calculate_centroid_and_geocode(process_lod2(self.outputLOD2geojsonfilename))

        self.tableWidget.setRowCount(len(building_info))  # Setze die Anzahl der Zeilen basierend auf den Daten

        for row, (parent_id, info) in enumerate(building_info.items()):
            self.tableWidget.setItem(row, 0, QTableWidgetItem(str(f"{info['Adresse']}, {info['Stadt']}, {info['Bundesland']}, {info['Land']}")))
            self.tableWidget.setItem(row, 1, QTableWidgetItem(str((info['Koordinaten'][0]))))
            self.tableWidget.setItem(row, 2, QTableWidgetItem(str((info['Koordinaten'][1]))))
            self.tableWidget.setItem(row, 3, QTableWidgetItem(str(round(info['Ground_Area'],1))))
            self.tableWidget.setItem(row, 4, QTableWidgetItem(str(round(info['Wall_Area'],1))))
            self.tableWidget.setItem(row, 5, QTableWidgetItem(str(round(info['Roof_Area'],1))))
            self.tableWidget.setItem(row, 6, QTableWidgetItem(str(round(info['Volume'],1))))
            self.tableWidget.setItem(row, 10, QTableWidgetItem(str(STANDARD_VALUES['ww_demand_Wh_per_m2'])))
            self.tableWidget.setItem(row, 11, QTableWidgetItem(str(STANDARD_VALUES['air_change_rate'])))
            self.tableWidget.setItem(row, 12, QTableWidgetItem(str(STANDARD_VALUES['floors'])))
            self.tableWidget.setItem(row, 13, QTableWidgetItem(str(STANDARD_VALUES['fracture_windows'])))
            self.tableWidget.setItem(row, 14, QTableWidgetItem(str(STANDARD_VALUES['fracture_doors'])))
            self.tableWidget.setItem(row, 15, QTableWidgetItem(str(STANDARD_VALUES['min_air_temp'])))
            self.tableWidget.setItem(row, 16, QTableWidgetItem(str(STANDARD_VALUES['room_temp'])))
            self.tableWidget.setItem(row, 17, QTableWidgetItem(str(STANDARD_VALUES['max_air_temp_heating'])))

            comboBoxTypes = QComboBox()
            comboBoxTypes.addItems(["HMF", "HEF", "GHD", "GBD"])  # Dropdown-Optionen
            self.tableWidget.setCellWidget(row, 7, comboBoxTypes)  # Korrigiere die Position für Nutzungstypen

            comboBoxBuildingTypes = QComboBox()
            comboBoxBuildingTypes.addItems(self.comboBoxBuildingTypesItems)  # Dropdown-Optionen
            self.tableWidget.setCellWidget(row, 8, comboBoxBuildingTypes)  # Korrigiere die Position für Nutzungstypen

            comboBoxBuildingState = QComboBox()
            comboBoxBuildingState.addItems(["Existing_state", "Usual_Refurbishment", "Advanced_Refurbishment"])  # Dropdown-Optionen
            self.tableWidget.setCellWidget(row, 9, comboBoxBuildingState)  # Korrigiere die Position für Nutzungstypen

    def saveData(self):
        path, _ = QFileDialog.getSaveFileName(self, "Speichern unter", "", "CSV-Dateien (*.csv)")
        if path:
            with open(path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=";")
                headers = [self.tableWidget.horizontalHeaderItem(i).text() for i in range(self.tableWidget.columnCount())]
                writer.writerow(headers)
                for row in range(self.tableWidget.rowCount()):
                    rowData = []
                    for column in range(self.tableWidget.columnCount()):
                        if column in [7, 8, 9]:  # Spalten mit QComboBox
                            comboBox = self.tableWidget.cellWidget(row, column)
                            rowData.append(comboBox.currentText())
                        else:
                            item = self.tableWidget.item(row, column)
                            rowData.append(item.text() if item else '')
                    writer.writerow(rowData)

    def loadDataFromFile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Öffnen", "", "CSV-Dateien (*.csv)")
        if path:
            with open(path, 'r', encoding='utf-8') as file:
                self.tableWidget.setRowCount(0)
                reader = csv.reader(file, delimiter=";")
                for rowIndex, row in enumerate(reader):
                    if rowIndex == 0:  # Überspringe die Kopfzeile
                        continue
                    self.tableWidget.insertRow(rowIndex - 1)
                    for columnIndex, value in enumerate(row):
                        if columnIndex in [7, 8, 9]:  # Spalten mit QComboBox
                            comboBox = self.createComboBox(columnIndex)
                            comboBox.setCurrentText(value)
                            self.tableWidget.setCellWidget(rowIndex - 1, columnIndex, comboBox)
                        else:
                            self.tableWidget.setItem(rowIndex - 1, columnIndex, QTableWidgetItem(value))

    def createComboBox(self, columnIndex):
        if columnIndex == 7:
            comboBoxItems = ["HMF", "HEF", "GHD", "GBD"]
        elif columnIndex == 8:
            comboBoxItems = self.comboBoxBuildingTypesItems
        else:  # columnIndex == 9
            comboBoxItems = ["Existing_state", "Usual_Refurbishment", "Advanced_Refurbishment"]
        comboBox = QComboBox()
        comboBox.addItems(comboBoxItems)
        return comboBox
    
    def calculateHeatDemand(self):
        for row in range(self.tableWidget.rowCount()):
            ground_area = float(self.tableWidget.item(row, 3).text())
            wall_area = float(self.tableWidget.item(row, 4).text())
            roof_area = float(self.tableWidget.item(row, 5).text())
            volume = float(self.tableWidget.item(row, 6).text())
            u_type = self.tableWidget.cellWidget(row, 8).currentText()  # Typ
            building_state = self.tableWidget.cellWidget(row, 9).currentText()  # Gebäudezustand

            building = Building(ground_area, wall_area, roof_area, volume, u_type=u_type, building_state=building_state)
            building.calc_yearly_heat_demand()
            
            print(building.yearly_heat_demand)
            self.tableWidget.setHorizontalHeaderLabels(['Adresse', 'UTM_X', 'UTM_Y','Grundfläche', 'Wandfläche', 'Dachfläche', 'Volumen', 'Nutzungstyp', 'Typ', 'Gebäudezustand', 
                                                    'ww_demand_Wh_per_m2', 'air_change_rate', 'floors', 'fracture_windows', 'fracture_doors', 'min_air_temp', 
                                                    'room_temp', 'max_air_temp_heating', 'Jährlicher Wärmebedarf in kWh'])
            self.tableWidget.setItem(row, 18, QTableWidgetItem(f"{building.yearly_heat_demand:.2f}"))  # Füge eine neue Spalte für die Ergebnisse hinzu

    def createBuildingCSV(self):
        # Standardwerte für die neuen Spalten
        standard_values = {
            'WW_Anteil': 0.2,  # Beispielwert, ersetze durch tatsächlichen Standardwert
            'Typ_Heizflächen': 'HK',  # Beispielwert
            'VLT_max': 70,  # Beispielwert
            'Steigung_Heizkurve': 1.5,  # Beispielwert
            'RLT_max': 55  # Beispielwert
        }

        path, _ = QFileDialog.getSaveFileName(self, "Speichern unter", "", "CSV-Dateien (*.csv)")
        if path:
            with open(path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';')
                # Schreibe die Kopfzeile
                headers = ['Land', 'Bundesland', 'Stadt', 'Adresse', 'Wärmebedarf', 'Gebäudetyp', 'WW_Anteil', 'Typ_Heizflächen', 'VLT_max', 'Steigung_Heizkurve', 'RLT_max', 'UTM_X', 'UTM_Y']
                writer.writerow(headers)

                # Durchlaufe jede Zeile der Tabelle und extrahiere die benötigten Werte
                for row in range(self.tableWidget.rowCount()):
                    land = self.tableWidget.item(row, 0).text().split(", ")[3]
                    bundesland = self.tableWidget.item(row, 0).text().split(", ")[2]
                    stadt = self.tableWidget.item(row, 0).text().split(", ")[1]
                    address = self.tableWidget.item(row, 0).text().split(", ")[0]
                    heat_demand = self.tableWidget.item(row, 18).text() if self.tableWidget.item(row, 18) else '0'  # Beispiel, wie du auf den Wärmebedarf zugreifst
                    building_type = self.tableWidget.cellWidget(row, 7).currentText()  # Zugriff auf den Wert der ComboBox
                    utm_x = self.tableWidget.item(row, 1).text()
                    utm_y = self.tableWidget.item(row, 2).text()

                    # Erstelle eine Zeile mit den extrahierten und Standardwerten
                    row_data = [
                        land,
                        bundesland,
                        stadt,
                        address,
                        heat_demand,
                        building_type,
                        standard_values['WW_Anteil'],
                        standard_values['Typ_Heizflächen'],
                        standard_values['VLT_max'],
                        standard_values['Steigung_Heizkurve'],
                        standard_values['RLT_max'],
                        utm_x,
                        utm_y
                    ]
                    # Schreibe die Zeile in die CSV-Datei
                    writer.writerow(row_data)
                print(f"Daten wurden gespeichert: {path}")