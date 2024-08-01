"""
Filename: visualization_dialogs.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-01
Description: Contains the Dialogs for the VisualizationTab.
"""

import sys
import os

import geopandas as gpd
import pandas as pd
import numpy as np
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
from osm.heat_supply_areas import clustering_districts_hdbscan, postprocessing_hdbscan, allocate_overlapping_area

def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return os.path.join(base_path, relative_path)
   
class LayerGenerationDialog(QDialog):
    """
    Dialog for generating layers for the heat network visualization.
    """
    accepted_inputs = pyqtSignal(dict)

    def __init__(self, base_path, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.visualization_tab = None
        self.setWindowFlags(Qt.Tool | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.initUI()

    def initUI(self):
        """
        Initialize the user interface for the dialog.
        """
        self.setWindowTitle('Wärmenetzgenerierung')
        self.setGeometry(300, 300, 700, 400)

        layout = QVBoxLayout(self)

        formLayout = QFormLayout()
        formLayout.setSpacing(10)

        self.fileInput, self.fileButton = self.createFileInput(f"{self.base_path}\Raumanalyse\Straßen.geojson")
        self.dataInput, self.dataCsvButton = self.createFileInput(f"{self.base_path}\Gebäudedaten\data_input.csv")

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
        formLayout.addRow("", self.addCoordButton)
        formLayout.addRow("Adresse für Geocoding:", self.addressInput)
        formLayout.addRow("", self.geocodeButton)
        formLayout.addRow("", self.importCsvButton)
        formLayout.addRow("Koordinatentabelle:", self.coordTable)
        formLayout.addRow("", self.deleteCoordButton)
        formLayout.addRow("Netzgenerierungsmodus:", self.generationModeComboBox)

        layout.addLayout(formLayout)

        self.okButton = QPushButton("OK", self)
        self.okButton.clicked.connect(self.onAccept)
        self.cancelButton = QPushButton("Abbrechen", self)
        self.cancelButton.clicked.connect(self.reject)

        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch(1)
        buttonLayout.addWidget(self.okButton)
        buttonLayout.addWidget(self.cancelButton)
        
        layout.addLayout(buttonLayout)

        self.setStyleSheet("""
            QPushButton:disabled, QLineEdit:disabled, QComboBox:disabled {
                background-color: #f0f0f0;
                color: #a0a0a0;
            }
        """)

        self.toggleLocationInputMode(0)
        self.setLayout(layout)

    def setVisualizationTab(self, visualization_tab):
        """
        Set the reference to the VisualizationTab.

        Args:
            visualization_tab: The VisualizationTab instance.
        """
        self.visualization_tab = visualization_tab

    def toggleLocationInputMode(self, index):
        """
        Toggle input fields based on the selected location input mode.

        Args:
            index: The selected index of the location input mode.
        """
        self.coordSystemComboBox.setEnabled(index == 0)
        self.coordInput.setEnabled(index == 0)
        self.addCoordButton.setEnabled(index == 0)
        self.addressInput.setEnabled(index == 1)
        self.geocodeButton.setEnabled(index == 1)
        self.importCsvButton.setEnabled(index == 2)

    def createFileInputLayout(self, lineEdit, button):
        """
        Create a layout for file input.

        Args:
            lineEdit: The QLineEdit widget.
            button: The QPushButton widget.

        Returns:
            QHBoxLayout: The layout containing the file input widgets.
        """
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def createFileInput(self, default_path):
        """
        Create a file input field with a browse button.

        Args:
            default_path: The default file path.

        Returns:
            QLineEdit: The line edit for file path input.
            QPushButton: The browse button.
        """
        lineEdit = QLineEdit(default_path)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.openFileDialog(lineEdit))
        return lineEdit, button

    def openFileDialog(self, lineEdit):
        """
        Open a file dialog to select a file.

        Args:
            lineEdit: The QLineEdit widget to set the selected file path.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", f"{self.base_path}", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def addCoordFromInput(self):
        """
        Add coordinates from the input field to the table.
        """
        coords = self.coordInput.text().split(',')
        if len(coords) == 2:
            x, y = map(str.strip, coords)
            source_crs = self.coordSystemComboBox.currentText()
            x_transformed, y_transformed = self.transform_coordinates(float(x), float(y), source_crs)
            self.insertRowInTable(x_transformed, y_transformed)

    def geocodeAndAdd(self):
        """
        Geocode the address and add the coordinates to the table.
        """
        address = self.addressInput.text()
        if address:
            x, y = get_coordinates(address)
            if x and y:
                self.insertRowInTable(str(x), str(y))

    def importCoordsFromCSV(self):
        """
        Import coordinates from a CSV file.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "CSV-Datei auswählen", f"{self.base_path}", "CSV Files (*.csv)")
        if filename:
            data = pd.read_csv(filename, delimiter=';', usecols=['UTM_X', 'UTM_Y'])
            for _, row in data.iterrows():
                self.insertRowInTable(str(row['UTM_X']), str(row['UTM_Y']))

    def transform_coordinates(self, x, y, source_crs):
        """
        Transform coordinates from the source CRS to EPSG:25833.

        Args:
            x: The x-coordinate.
            y: The y-coordinate.
            source_crs: The source coordinate reference system.

        Returns:
            tuple: The transformed coordinates.
        """
        if source_crs == "WGS84":
            transformer = Transformer.from_crs("EPSG:4326", "EPSG:25833", always_xy=True)
        else:
            transformer = Transformer.from_crs("EPSG:25833", "EPSG:25833", always_xy=True)
        x_transformed, y_transformed = transformer.transform(x, y)
        return x_transformed, y_transformed

    def insertRowInTable(self, x, y):
        """
        Insert a row in the coordinates table.

        Args:
            x: The x-coordinate.
            y: The y-coordinate.
        """
        row_count = self.coordTable.rowCount()
        self.coordTable.insertRow(row_count)
        self.coordTable.setItem(row_count, 0, QTableWidgetItem(str(x)))
        self.coordTable.setItem(row_count, 1, QTableWidgetItem(str(y)))

    def deleteSelectedRow(self):
        """
        Delete the selected row from the coordinates table.
        """
        selected_row = self.coordTable.currentRow()
        if selected_row >= 0:
            self.coordTable.removeRow(selected_row)

    def getInputs(self):
        """
        Get the inputs from the dialog.

        Returns:
            dict: The inputs from the dialog.
        """
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
        """
        Handle the accept event.
        """
        inputs = self.getInputs()
        self.accepted_inputs.emit(inputs)
        self.accept()

class DownloadOSMDataDialog(QDialog):
    """
    Dialog for downloading OSM data.
    """
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
            {"highway": "living_street"},
            {"highway": "service"},
        ]

        self.initUI()

    def initUI(self):
        """
        Initialize the user interface for the dialog.
        """
        self.setWindowTitle("Download OSM-Data")
        self.setGeometry(300, 300, 400, 400)

        layout = QVBoxLayout(self)

        # City name input field
        self.cityLabel = QLabel("Stadt, für die Straßendaten heruntergeladen werden sollen:")
        self.cityLineEdit = QLineEdit("Zittau")
        layout.addWidget(self.cityLabel)
        layout.addWidget(self.cityLineEdit)
        
        # File name input field
        self.filenameLabel = QLabel("Dateiname, unter dem die Straßendaten als geojson gespeichert werden sollen:")
        self.filenameLineEdit, fileButton = self.createFileInput(f"{self.base_path}\Raumanalyse\Straßen.geojson")
        layout.addWidget(self.filenameLabel)
        layout.addLayout(self.createFileInputLayout(self.filenameLineEdit, fileButton))

        # Dropdown menu for selecting standard tags
        self.standardTagsLabel = QLabel("Aktuell auswählbare Straßenarten:")
        self.standardTagsComboBox = QComboBox(self)
        for tag in self.standard_tags:
            key = next(iter(tag))
            value = tag[key]
            self.standardTagsComboBox.addItem(f"{key}: {value}")

        layout.addWidget(self.standardTagsLabel)
        layout.addWidget(self.standardTagsComboBox)

        # Button to load a selected standard tag
        self.loadStandardTagButton = QPushButton("Standard-Tag hinzufügen", self)
        self.loadStandardTagButton.clicked.connect(self.loadSelectedStandardTag)
        layout.addWidget(self.loadStandardTagButton)

        # Tags selection
        self.tagsLayout = QFormLayout()
        layout.addLayout(self.tagsLayout)
        
        # Buttons to add/remove tags
        self.removeTagButton = QPushButton("Tag entfernen", self)
        self.removeTagButton.clicked.connect(self.removeTagField)
        layout.addWidget(self.removeTagButton)

        # Query button
        self.queryButton = QPushButton("Abfrage starten", self)
        self.queryButton.clicked.connect(self.startQuery)
        layout.addWidget(self.queryButton)
        
        # OK and Cancel buttons
        self.okButton = QPushButton("OK", self)
        self.okButton.clicked.connect(self.accept)
        layout.addWidget(self.okButton)

        self.cancelButton = QPushButton("Abbrechen", self)
        layout.addWidget(self.cancelButton)

    def createFileInput(self, default_path):
        """
        Create a file input field with a browse button.

        Args:
            default_path: The default file path.

        Returns:
            QLineEdit: The line edit for file path input.
            QPushButton: The browse button.
        """
        lineEdit = QLineEdit(default_path)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def createFileInputLayout(self, lineEdit, button):
        """
        Create a layout for file input.

        Args:
            lineEdit: The QLineEdit widget.
            button: The QPushButton widget.

        Returns:
            QHBoxLayout: The layout containing the file input widgets.
        """
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def selectFile(self, lineEdit):
        """
        Open a file dialog to select a file.

        Args:
            lineEdit: The QLineEdit widget to set the selected file path.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def addTagField(self, key="", value=""):
        """
        Add a tag field to the tags layout.

        Args:
            key: The tag key.
            value: The tag value.
        """
        key = str(key) if key is not None else ""
        value = str(value) if value is not None else ""

        keyLineEdit = QLineEdit(key)
        valueLineEdit = QLineEdit(value)
        self.tagsLayout.addRow(keyLineEdit, valueLineEdit)

        self.tagsLayoutList.append((keyLineEdit, valueLineEdit))
        self.tags_to_download.append((key, value))
        print(self.tags_to_download)

    def removeTagField(self):
        """
        Remove the last tag field from the tags layout.
        """
        if self.tags_to_download:
            keyLineEdit, valueLineEdit = self.tagsLayoutList.pop()
            self.tags_to_download.pop()
            self.tagsLayout.removeRow(keyLineEdit)
            print(self.tags_to_download)

    def loadAllStandardTags(self):
        """
        Load all standard tags into the tags layout.
        """
        for tag in self.standard_tags:
            key = next(iter(tag))
            value = tag[key]
            self.addTagField(key, value)

    def loadSelectedStandardTag(self):
        """
        Load the selected standard tag into the tags layout.
        """
        selected_tag_index = self.standardTagsComboBox.currentIndex()
        tag = self.standard_tags[selected_tag_index]
        key = next(iter(tag))
        value = tag[key]
        self.addTagField(key, value)
    
    def startQuery(self):
        """
        Start the query to download OSM data based on the selected tags and city name.
        """
        self.filename = self.filenameLineEdit.text()
        city_name = self.cityLineEdit.text()

        query = build_query(city_name, self.tags_to_download, element_type="way")
        geojson_data = download_data(query, element_type="way")
        save_to_file(geojson_data, self.filename)
        gdf = gpd.read_file(self.filename, driver='GeoJSON').to_crs(epsg=25833)
        gdf.to_file(self.filename, driver='GeoJSON')

        QMessageBox.information(self, "Erfolg", f"Abfrageergebnisse gespeichert in {self.filename}")
            
        self.parent().loadNetData(self.filename)

class OSMBuildingQueryDialog(QDialog):
    """
    Dialog for querying OSM building data.
    """
    def __init__(self, base_path, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.initUI()

    def initUI(self):
        """
        Initialize the user interface for the dialog.
        """
        layout = QVBoxLayout(self)
        self.setWindowTitle("OSM Gebäudeabfrage")

        self.cityLineEdit = QLineEdit(self)
        layout.addWidget(QLabel("Stadt, deren OSM-Gebäudedaten heruntergeladen werden sollen:"))
        layout.addWidget(self.cityLineEdit)

        self.filenameLineEdit = QLineEdit(f"{self.base_path}\Raumanalyse\output_buildings.geojson", self)
        layout.addWidget(QLabel("Dateiname, unter dem die Gebäudedaten als geojson gespeichert werde sollen:"))
        layout.addWidget(self.filenameLineEdit)

        self.filterComboBox = QComboBox(self)
        self.filterComboBox.addItem("Kein Filter")
        self.filterComboBox.addItem("Filtern mit Koordinatenbereich")
        self.filterComboBox.addItem("Filtern mit zentralen Koordinaten und Radius als Abstand")
        self.filterComboBox.addItem("Filtern mit Adressen aus CSV")
        self.filterComboBox.addItem("Filtern mit Polygon-geoJSON")
        layout.addWidget(QLabel("Filteroptionen für die Gebäudedaten:"))
        layout.addWidget(self.filterComboBox)

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

        self.coordRadiusWidget = QWidget(self)
        coordRadiusLayout = QVBoxLayout(self.coordRadiusWidget)
        self.centerLatLineEdit = QLineEdit(self)
        self.centerLatLineEdit.setPlaceholderText("Breite")
        coordRadiusLayout.addWidget(QLabel("Breite:"))
        coordRadiusLayout.addWidget(self.centerLatLineEdit)

        self.centerLonLineEdit = QLineEdit(self)
        self.centerLonLineEdit.setPlaceholderText("Länge")
        coordRadiusLayout.addWidget(QLabel("Länge:"))
        coordRadiusLayout.addWidget(self.centerLonLineEdit)

        self.radiusLineEdit = QLineEdit(self)
        self.radiusLineEdit.setPlaceholderText("Radius in Metern")
        coordRadiusLayout.addWidget(QLabel("Radius in Metern:"))
        coordRadiusLayout.addWidget(self.radiusLineEdit)
        layout.addWidget(self.coordRadiusWidget)

        self.csvWidget = QWidget(self)
        csvLayout = QVBoxLayout(self.csvWidget)
        self.addressCsvLineEdit, self.addressCsvButton = self.createFileInput(f"{self.base_path}/")
        csvLayout.addLayout(self.createFileInputLayout(self.addressCsvLineEdit, self.addressCsvButton))
        layout.addWidget(self.csvWidget)

        self.geoJSONWidget = QWidget(self)
        geoJSONLayout = QVBoxLayout(self.geoJSONWidget)
        self.geoJSONLineEdit, self.geoJSONButton = self.createFileInput(f"{self.base_path}/")
        geoJSONLayout.addLayout(self.createFileInputLayout(self.geoJSONLineEdit, self.geoJSONButton))
        layout.addWidget(self.geoJSONWidget)

        self.queryButton = QPushButton("Abfrage starten", self)
        self.queryButton.clicked.connect(self.startQuery)
        layout.addWidget(self.queryButton)

        self.okButton = QPushButton("OK", self)
        self.okButton.clicked.connect(self.accept)
        layout.addWidget(self.okButton)
        self.cancelButton = QPushButton("Abbrechen", self)
        self.cancelButton.clicked.connect(self.reject)
        layout.addWidget(self.cancelButton)

        self.filterComboBox.currentIndexChanged.connect(self.showSelectedFilter)

        self.showSelectedFilter()

    def createFileInput(self, default_path):
        """
        Create a file input field with a browse button.

        Args:
            default_path: The default file path.

        Returns:
            QLineEdit: The line edit for file path input.
            QPushButton: The browse button.
        """
        lineEdit = QLineEdit(default_path)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def selectFile(self, lineEdit):
        """
        Open a file dialog to select a file.

        Args:
            lineEdit: The QLineEdit widget to set the selected file path.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def createFileInputLayout(self, lineEdit, button):
        """
        Create a layout for file input.

        Args:
            lineEdit: The QLineEdit widget.
            button: The QPushButton widget.

        Returns:
            QHBoxLayout: The layout containing the file input widgets.
        """
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def showSelectedFilter(self):
        """
        Show the selected filter options based on the filter type.
        """
        selected_filter = self.filterComboBox.currentText()
        self.coordWidget.setVisible(selected_filter == "Filtern mit Koordinatenbereich")
        self.coordRadiusWidget.setVisible(selected_filter == "Filtern mit zentralen Koordinaten und Radius als Abstand")
        self.csvWidget.setVisible(selected_filter == "Filtern mit Adressen aus CSV")
        self.geoJSONWidget.setVisible(selected_filter == "Filtern mit Polygon-geoJSON")

    def haversine(self, lat1, lon1, lat2, lon2):
        """
        Calculate the great-circle distance between two points on the Earth.

        Args:
            lat1: Latitude of the first point.
            lon1: Longitude of the first point.
            lat2: Latitude of the second point.
            lon2: Longitude of the second point.

        Returns:
            float: The distance between the two points in meters.
        """
        earth_radius = 6371000.0
        lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = earth_radius * c
        return distance

    def startQuery(self):
        """
        Start the query to download and filter OSM building data.
        """
        city_name = self.cityLineEdit.text()
        filename = self.filenameLineEdit.text()
        selected_filter = self.filterComboBox.currentText()

        if not city_name or not filename:
            QMessageBox.warning(self, "Warnung", "Bitte geben Sie Stadtname und Ausgabedatei an.")
            return

        tags = {"building": "yes"}
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
        self.parent().loadNetData(filename)

    def prepare_gdf(self, geojson_data):
        """
        Prepare a GeoDataFrame from the GeoJSON data.

        Args:
            geojson_data: The GeoJSON data.

        Returns:
            GeoDataFrame: The prepared GeoDataFrame.
        """
        gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
        gdf.crs = "EPSG:4326"
        return gdf.to_crs(epsg=25833)

    def filter_with_bbox(self, gdf, filename):
        """
        Filter the GeoDataFrame using a bounding box.

        Args:
            gdf: The GeoDataFrame to filter.
            filename: The output file name.
        """
        min_lat = float(self.minLatLineEdit.text())
        min_lon = float(self.minLonLineEdit.text())
        max_lat = float(self.maxLatLineEdit.text())
        max_lon = float(self.maxLonLineEdit.text())

        bbox_polygon_wgs84 = box(min_lon, min_lat, max_lon, max_lat)
        project_to_target_crs = pyproj.Transformer.from_proj(
            pyproj.Proj(init='epsg:4326'),
            pyproj.Proj(init='epsg:25833'),
            always_xy=True
        )

        bbox_polygon_transformed = transform(project_to_target_crs.transform, bbox_polygon_wgs84)
        gdf_filtered = gdf[gdf.intersects(bbox_polygon_transformed)]
        gdf_filtered.to_file(filename, driver='GeoJSON')

    def filter_with_central_coords_and_radius(self, gdf, filename):
        """
        Filter the GeoDataFrame using central coordinates and a radius.

        Args:
            gdf: The GeoDataFrame to filter.
            filename: The output file name.
        """
        center_lat = float(self.centerLatLineEdit.text())
        center_lon = float(self.centerLonLineEdit.text())
        radius = float(self.radiusLineEdit.text())

        center_point_wgs84 = Point(center_lon, center_lat)
        project = pyproj.Transformer.from_proj(
            pyproj.Proj(init='epsg:4326'),
            pyproj.Proj(init='epsg:25833')
        )

        center_point_transformed = transform(project.transform, center_point_wgs84)
        gdf['distance'] = gdf.geometry.distance(center_point_transformed)
        radius_m = radius
        gdf_filtered = gdf[gdf['distance'] <= radius_m]
        gdf_filtered.to_file(filename, driver='GeoJSON')

    def filter_with_csv_addresses(self, gdf, filename):
        """
        Filter the GeoDataFrame using addresses from a CSV file.

        Args:
            gdf: The GeoDataFrame to filter.
            filename: The output file name.
        """
        address_csv_file = self.addressCsvLineEdit.text()
        if address_csv_file:
            csv_df = pd.read_csv(address_csv_file, sep=';')
            addresses_from_csv = csv_df['Adresse'].tolist()
            gdf['full_address'] = gdf['addr:street'] + ' ' + gdf['addr:housenumber']
            gdf_filtered = gdf[gdf['full_address'].isin(addresses_from_csv)]
            gdf_filtered.to_file(filename, driver='GeoJSON')

    def filter_with_polygon(self, gdf, filename):
        """
        Filter the GeoDataFrame using a polygon from a geoJSON file.

        Args:
            gdf: The GeoDataFrame to filter.
            filename: The output file name.
        """
        geoJSON_file = self.geoJSONLineEdit.text()
        if geoJSON_file:
            polygon_gdf = gpd.read_file(geoJSON_file)
            polygon = polygon_gdf.geometry.iloc[0]
            filtered_gdf = gdf[gdf.geometry.within(polygon)]
            filtered_gdf.to_file(filename, driver='GeoJSON')

class SpatialAnalysisDialog(QDialog):
    """
    Dialog for performing spatial analysis to cluster buildings into districts.
    """
    def __init__(self, base_path, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.initUI()

    def initUI(self):
        """
        Initialize the user interface for the dialog.
        """
        layout = QVBoxLayout(self)
        self.setWindowTitle("Clustering Quartiere")
        self.setGeometry(300, 300, 600, 400)

        self.explanationLabel = QLabel("""Hier können Gebäude aus dem OSM-download räumlich geclustert werden. \nEs werden den Gebäuden zufällig Wärmebedarfe zugewiesen, wodurch sich für die einzelnen Cluster spez. Wärmebedarfe ergeben. \nAnhand eines intern definierten Schwellwerts lassen sich so Versorgungsgebiete definieren. \nIm Ergebnis werden alle generierten Cluster sowie die ermittelten Gebäude zur Wärmeversorgung mit Wärmenetzen ausgegeben. \nDiese Funktionen dienen lediglich der demonstration grundsätzlicher Möglichkeiten und könnte in Zukunft hin zur Nutzbarkeit ausgebaut werden.""")
        layout.addWidget(self.explanationLabel)

        self.geojsonWidget = QWidget(self)
        geojsonLayout = QVBoxLayout(self.geojsonWidget)
        self.geojsonLabel = QLabel("Dateiname der geojson mit den Gebäuden die geclustert werden sollen.")
        self.geojsonLineEdit, self.geojsonButton = self.createFileInput(f"{self.base_path}\Raumanalyse\output_buildings.geojson")
        geojsonLayout.addLayout(self.createFileInputLayout(self.geojsonLineEdit, self.geojsonButton))
        layout.addWidget(self.geojsonLabel)
        layout.addWidget(self.geojsonWidget)

        self.geojsonareaWidget = QWidget(self)
        geojsonareaLayout = QVBoxLayout(self.geojsonareaWidget)
        self.geojsonareaLabel = QLabel("Dateiname der geojson in der die Polygone der ermittelten Quartiere/Cluster gespeichert werden sollen.")
        self.geojsonareaLineEdit, self.geojsonareaButton = self.createFileInput(f"{self.base_path}\Raumanalyse\quartiere.geojson")
        geojsonareaLayout.addLayout(self.createFileInputLayout(self.geojsonareaLineEdit, self.geojsonareaButton))
        layout.addWidget(self.geojsonareaLabel)
        layout.addWidget(self.geojsonareaWidget)

        self.geojsonfilteredbuildingsWidget = QWidget(self)
        geojsonfilteredbuildingsLayout = QVBoxLayout(self.geojsonfilteredbuildingsWidget)
        self.geojsonfilteredbuildingsLabel = QLabel("Dateiname der geojson in der die nach Wärmenetzversorgung gefilterten gebäude gespeichert werden sollen.")
        self.geojsonfilteredbuildingsLineEdit, self.geojsonfilteredbuildingsButton = self.createFileInput(f"{self.base_path}\Raumanalyse\waermenetz_buildings.geojson")
        geojsonfilteredbuildingsLayout.addLayout(self.createFileInputLayout(self.geojsonfilteredbuildingsLineEdit, self.geojsonfilteredbuildingsButton))
        layout.addWidget(self.geojsonfilteredbuildingsLabel)
        layout.addWidget(self.geojsonfilteredbuildingsWidget)

        self.queryButton = QPushButton("Berechnung Starten", self)
        self.queryButton.clicked.connect(self.calculate)
        layout.addWidget(self.queryButton)

        self.okButton = QPushButton("OK", self)
        self.okButton.clicked.connect(self.accept)
        layout.addWidget(self.okButton)
        self.cancelButton = QPushButton("Abbrechen", self)
        self.cancelButton.clicked.connect(self.reject)
        layout.addWidget(self.cancelButton)


    def createFileInput(self, default_path):
        """
        Create a file input field with a browse button.

        Args:
            default_path: The default file path.

        Returns:
            QLineEdit: The line edit for file path input.
            QPushButton: The browse button.
        """
        lineEdit = QLineEdit(default_path)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def selectFile(self, lineEdit):
        """
        Open a file dialog to select a file.

        Args:
            lineEdit: The QLineEdit widget to set the selected file path.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def createFileInputLayout(self, lineEdit, button):
        """
        Create a layout for file input.

        Args:
            lineEdit: The QLineEdit widget.
            button: The QPushButton widget.

        Returns:
            QHBoxLayout: The layout containing the file input widgets.
        """
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def calculate_building_data(self, gdf, output_filename):
        """
        Calculate additional building data for the GeoDataFrame.

        Args:
            gdf: The GeoDataFrame containing the building data.
            output_filename: The output file name.

        Returns:
            GeoDataFrame: The updated GeoDataFrame with additional building data.
        """
        gdf['area_sqm'] = gdf['geometry'].area
        gdf['spez. Wärmebedarf [kWh/m²*a]'] = np.random.uniform(50, 200, gdf.shape[0])
        gdf['Anzahl Geschosse'] = 3
        gdf['Jahreswärmebedarf [kWh/a]'] = gdf['spez. Wärmebedarf [kWh/m²*a]'] * gdf['Anzahl Geschosse'] * gdf['area_sqm']
        gdf.to_file(output_filename, driver='GeoJSON')

        return gdf

    def calculate(self):
        """
        Perform the spatial analysis to cluster buildings into districts.
        """
        geojson_file_buildings = self.geojsonLineEdit.text()
        geojson_file_areas = self.geojsonareaLineEdit.text()
        geojson_file_filtered_buildings = self.geojsonfilteredbuildingsLineEdit.text()
        gdf = gpd.read_file(geojson_file_buildings, driver='GeoJSON').to_crs(epsg=25833)
        ignore_types = ['ruins', 'greenhouse', 'shed', 'silo', 'slurry_tank', 
                    'toilets', 'hut', 'cabin', 'ger', 'static_caravan', 
                    'construction', 'cowshed', 'garage', 'garages', 'carport',
                    'farm_auxiliary', 'roof', 'digester']

        gdf = gdf[~gdf['building'].isin(ignore_types)]
        gdf = self.calculate_building_data(gdf, geojson_file_buildings)
        
        quartiere = clustering_districts_hdbscan(gdf)
        quartiere = postprocessing_hdbscan(quartiere)
        quartiere = allocate_overlapping_area(quartiere)
        quartiere.to_file(geojson_file_areas, driver='GeoJSON')

        waermenetz_buildings = gdf[gdf['quartier_label'].isin(quartiere[quartiere['Versorgungsgebiet'] == 'Wärmenetzversorgung'].index)]
        waermenetz_buildings = waermenetz_buildings[['geometry']]
        waermenetz_buildings.to_file(geojson_file_filtered_buildings, driver='GeoJSON')

        self.parent().loadNetData(geojson_file_filtered_buildings)
        self.parent().loadNetData(geojson_file_areas)

class GeocodeAddressesDialog(QDialog):
    """
    Dialog for geocoding addresses from a CSV file.
    """
    def __init__(self, base_path, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.initUI()

    def initUI(self):
        """
        Initialize the user interface for the dialog.
        """
        self.setWindowTitle("Adressdaten geocodieren")
        self.setGeometry(300, 300, 600, 200)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        font = QFont()
        font.setPointSize(10)
        
        self.inputfilenameLineEdit, inputFileButton = self.createFileInput(f"{self.base_path}\Gebäudedaten\data_input.csv", font)
        layout.addLayout(self.createFileInputLayout("Eingabedatei:", self.inputfilenameLineEdit, inputFileButton, font))
        
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

        self.progressBar = QProgressBar(self)
        self.progressBar.setFont(font)
        layout.addWidget(self.progressBar)

    def createFileInput(self, default_path, font):
        """
        Create a file input field with a browse button.

        Args:
            default_path: The default file path.
            font: The font for the input field and button.

        Returns:
            QLineEdit: The line edit for file path input.
            QPushButton: The browse button.
        """
        lineEdit = QLineEdit(default_path)
        lineEdit.setFont(font)
        button = QPushButton("Durchsuchen")
        button.setFont(font)
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def createFileInputLayout(self, label_text, lineEdit, button, font):
        """
        Create a layout for file input.

        Args:
            label_text: The label text for the input field.
            lineEdit: The QLineEdit widget.
            button: The QPushButton widget.
            font: The font for the input field and button.

        Returns:
            QHBoxLayout: The layout containing the file input widgets.
        """
        layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setFont(font)
        layout.addWidget(label)
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def selectFile(self, lineEdit):
        """
        Open a file dialog to select a file.

        Args:
            lineEdit: The QLineEdit widget to set the selected file path.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def onAccept(self):
        """
        Handle the accept event to start geocoding addresses.
        """
        self.inputfilename = self.inputfilenameLineEdit.text()
        self.geocodeAdresses(self.inputfilename)

    def geocodeAdresses(self, inputfilename):
        """
        Geocode addresses from the input CSV file.

        Args:
            inputfilename: The path to the input CSV file.
        """
        if hasattr(self, 'geocodingThread') and self.geocodingThread.isRunning():
            self.geocodingThread.terminate()
            self.geocodingThread.wait()
        self.geocodingThread = GeocodingThread(inputfilename)
        self.geocodingThread.calculation_done.connect(self.on_generation_done)
        self.geocodingThread.calculation_error.connect(self.on_generation_error)
        self.geocodingThread.start()
        self.progressBar.setRange(0, 0)

    def on_generation_done(self, results):
        """
        Handle the completion of the geocoding process.

        Args:
            results: The results of the geocoding process.
        """
        self.accept()

    def on_generation_error(self, error_message):
        """
        Handle errors during the geocoding process.

        Args:
            error_message: The error message.
        """
        QMessageBox.critical(self, "Fehler beim Geocoding", str(error_message))
        self.progressBar.setRange(0, 1)