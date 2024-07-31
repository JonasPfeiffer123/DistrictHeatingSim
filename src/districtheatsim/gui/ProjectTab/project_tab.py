"""
Filename: project_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-29
Description: Contains the ProjectTab.
"""

import csv
import json
import os
import sys

from PyQt5.QtCore import pyqtSignal, QDir
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMenuBar, QAction, QProgressBar, \
    QLabel, QTableWidget, QHBoxLayout, QPushButton, QFileDialog, QTableWidgetItem, QMessageBox, \
    QFileSystemModel, QTreeView, QSplitter

from gui.threads import GeocodingThread

# defines the map path
def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist, ist der Basispfad der Temp-Ordner, wo PyInstaller alles extrahiert
        base_path = sys._MEIPASS
    else:
        # Wenn die Anwendung nicht eingefroren ist, ist der Basispfad der Ordner, in dem die Hauptdatei liegt
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

# Tab class
class ProjectTab(QWidget):
    layers_imported = pyqtSignal(dict)

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.layers = {}
        self.base_path = None
        self.current_file_path = ''

        # Initialisierung der UI-Elemente vor dem Hinzufügen von Signal-Slots
        self.initUI()

        # Verbindung des Signals mit der Slot-Funktion nach der UI-Initialisierung
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.project_folder)

    def initUI(self):
        mainLayout = QVBoxLayout()

        # Splitter Layout für anpassbare Größen
        splitter = QSplitter()

        # Linke Seite des Layouts
        leftLayout = QVBoxLayout()

        # Projektpfad-Anzeige
        self.pathLabel = QLabel("Projektordner: " + (self.base_path if self.base_path else "Kein Ordner ausgewählt"))
        leftLayout.addWidget(self.pathLabel)

        # Datei-Baumansicht
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.treeView = QTreeView()
        self.treeView.setModel(self.model)
        self.treeView.setRootIndex(self.model.index(self.base_path if self.base_path else QDir.rootPath()))
        self.treeView.doubleClicked.connect(self.on_treeView_doubleClicked)

        leftWidget = QWidget()
        leftWidget.setLayout(leftLayout)
        leftLayout.addWidget(self.treeView)

        splitter.addWidget(leftWidget)

        # Rechte Seite des Layouts für die anderen Widgets
        rightLayout = QVBoxLayout()

        # Menüleiste für CSV-Editor und Geocoding
        self.menuBar = QMenuBar(self)
        self.menuBar.setFixedHeight(30)
        fileMenu = self.menuBar.addMenu('Datei')

        csvEditAction = QAction('CSV erstellen/bearbeiten', self)
        csvEditAction.triggered.connect(self.createCSV)
        fileMenu.addAction(csvEditAction)

        createCSVfromgeojsonAction = QAction('Gebäude-CSV aus OSM-geojson erstellen', self)
        createCSVfromgeojsonAction.triggered.connect(self.createCsvFromGeoJson)
        fileMenu.addAction(createCSVfromgeojsonAction)

        downloadAction = QAction('Adressdaten geocodieren', self)
        downloadAction.triggered.connect(self.openGeocodeAdressesDialog)
        fileMenu.addAction(downloadAction)

        rightLayout.addWidget(self.menuBar)

        # CSV Editor
        self.csvTable = QTableWidget()
        rightLayout.addWidget(self.csvTable)

        # Buttons zum Hinzufügen und Löschen von Zeilen
        buttonLayout = QHBoxLayout()
        addButton = QPushButton("Zeile hinzufügen")
        addButton.clicked.connect(self.addRow)
        delButton = QPushButton("Zeile löschen")
        delButton.clicked.connect(self.delRow)
        buttonLayout.addWidget(addButton)
        buttonLayout.addWidget(delButton)
        rightLayout.addLayout(buttonLayout)

        # Buttons zum Öffnen und Speichern der CSV
        buttonLayout2 = QHBoxLayout()
        openButton = QPushButton("CSV öffnen")
        openButton.clicked.connect(self.openCSV)
        saveButton = QPushButton("CSV speichern")
        saveButton.clicked.connect(self.saveCSV)
        buttonLayout2.addWidget(openButton)
        buttonLayout2.addWidget(saveButton)
        rightLayout.addLayout(buttonLayout2)

        # Fortschrittsbalken für Geocoding
        self.progressBar = QProgressBar(self)
        rightLayout.addWidget(self.progressBar)

        rightWidget = QWidget()
        rightWidget.setLayout(rightLayout)

        splitter.addWidget(rightWidget)
        splitter.setStretchFactor(1, 2)

        mainLayout.addWidget(splitter)
        self.setLayout(mainLayout)

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path
        self.pathLabel.setText("Projektordner: " + new_base_path)
        self.treeView.setRootIndex(self.model.index(self.base_path))

    def on_treeView_doubleClicked(self, index):
        file_path = self.model.filePath(index)
        if file_path.endswith('.csv'):
            self.loadCSV(file_path)

    def openCSV(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'CSV öffnen', self.base_path, 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.loadCSV(fname)

    def loadCSV(self, fname):
        self.current_file_path = fname
        with open(fname, 'r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter=';')
            headers = next(reader)
            self.csvTable.setRowCount(0)
            self.csvTable.setColumnCount(len(headers))
            self.csvTable.setHorizontalHeaderLabels(headers)

            for row_data in reader:
                row = self.csvTable.rowCount()
                self.csvTable.insertRow(row)
                for column, data in enumerate(row_data):
                    item = QTableWidgetItem(data)
                    self.csvTable.setItem(row, column, item)

    def addRow(self):
        rowCount = self.csvTable.rowCount()
        self.csvTable.insertRow(rowCount)

    def delRow(self):
        currentRow = self.csvTable.currentRow()
        if currentRow > -1:
            self.csvTable.removeRow(currentRow)
        else:
            QMessageBox.warning(self, "Warnung", "Bitte wählen Sie eine Zeile zum Löschen aus.", QMessageBox.Ok)

    def saveCSV(self):
        if self.current_file_path:
            with open(self.current_file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';')
                headers = [self.csvTable.horizontalHeaderItem(i).text() for i in range(self.csvTable.columnCount())]
                writer.writerow(headers)

                for row in range(self.csvTable.rowCount()):
                    row_data = [self.csvTable.item(row, column).text() if self.csvTable.item(row, column) else '' for column in range(self.csvTable.columnCount())]
                    if any(row_data):
                        writer.writerow(row_data)
        else:
            QMessageBox.warning(self, "Warnung", "Es wurde keine Datei zum Speichern ausgewählt oder erstellt.", QMessageBox.Ok)

    def createCSV(self):
        headers = ['Land', 'Bundesland', 'Stadt', 'Adresse', 'Wärmebedarf', 'Gebäudetyp', "Subtyp", 'WW_Anteil', 'Typ_Heizflächen', 'VLT_max', 'Steigung_Heizkurve', 'RLT_max', "Normaußentemperatur"]
        default_data = ['']*len(headers)

        fname, _ = QFileDialog.getSaveFileName(self, 'Gebäude-CSV erstellen', self.base_path, 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.current_file_path = fname
            with open(fname, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';')
                writer.writerow(headers)
                writer.writerows([default_data])  # Hinzufügen einer leeren Datenzeile

            self.loadCSV(fname)

    def createCsvFromGeoJson(self):
        try:
            geojson_file_path, _ = QFileDialog.getOpenFileName(self, "geoJSON auswählen", self.base_path, "All Files (*)")
            if not geojson_file_path:
                return  # Nichts tun, wenn keine Datei ausgewählt wurde
            
            csv_file = f"{self.base_path}\Gebäudedaten\generated_building_data.csv"
            
            with open(geojson_file_path, 'r') as geojson_file:
                data = json.load(geojson_file)
            
            with open(csv_file, 'w', encoding='utf-8', newline='') as csvfile:
                fieldnames = ["Land", "Bundesland", "Stadt", "Adresse", "Wärmebedarf", "Gebäudetyp", "Subtyp", "WW_Anteil", "Typ_Heizflächen", 
                            "VLT_max", "Steigung_Heizkurve", "RLT_max", "Normaußentemperatur", "UTM_X", "UTM_Y"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
                writer.writeheader()

                for feature in data['features']:
                    if feature['geometry']['type'] == 'MultiPolygon':
                        for polygon_coords in feature['geometry']['coordinates']:
                            centroid = self.calculateCentroid(polygon_coords)
                            writer.writerow({
                                "Land": "",
                                "Bundesland": "",
                                "Stadt": "",
                                "Adresse": "",
                                "Wärmebedarf": 30000,
                                "Gebäudetyp": "HMF",
                                "Subtyp": "05",
                                "WW_Anteil": 0.2,
                                "Typ_Heizflächen": "HK",
                                "VLT_max": 70,
                                "Steigung_Heizkurve": 1.5,
                                "RLT_max": 55,
                                "Normaußentemperatur": -15,
                                "UTM_X": centroid[0],
                                "UTM_Y": centroid[1]
                            })
                    elif feature['geometry']['type'] == 'Polygon':
                        centroid = self.calculateCentroid(feature['geometry']['coordinates'])
                        writer.writerow({
                                "Land": "",
                                "Bundesland": "",
                                "Stadt": "",
                                "Adresse": "",
                                "Wärmebedarf": 30000,
                                "Gebäudetyp": "HMF",
                                "Subtyp": "05",
                                "WW_Anteil": 0.2,
                                "Typ_Heizflächen": "HK",
                                "VLT_max": 70,
                                "Steigung_Heizkurve": 1.5,
                                "RLT_max": 55,
                                "Normaußentemperatur": -15,
                                "UTM_X": centroid[0],
                                "UTM_Y": centroid[1]
                            })

            self.loadCSV(csv_file)

            QMessageBox.information(self, "Info", f"CSV-Datei wurde erfolgreich erstellt und unter {self.base_path}/Gebäudedaten/generated_building_data.csv gespeichert")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Ein Fehler ist aufgetreten: {str(e)}")
    
    def calculateCentroid(self, coordinates):
        x_sum = 0
        y_sum = 0
        total_points = 0

        if isinstance(coordinates[0], float):
            x_sum += coordinates[0]
            y_sum += coordinates[1]
            total_points += 1
        else:
            for item in coordinates:
                x, y = self.calculateCentroid(item)
                if x is not None and y is not None:
                    x_sum += x
                    y_sum += y
                    total_points += 1

        if total_points > 0:
            centroid_x = x_sum / total_points
            centroid_y = y_sum / total_points
            return centroid_x, centroid_y
        else:
            return None, None

    def setProjectFolderPath(self, path):
        self.base_path = path
        self.updateDefaultPath(path)

    def openGeocodeAdressesDialog(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'CSV-Koordinaten laden', self.base_path, 'CSV Files (*.csv);;All Files (*)')
        if fname:
            # Abfrage erstellen und Daten herunterladen
            self.geocodeAdresses(fname)

    # Die Methode des Dialogs, die die anderen Funktionen aufruft
    def geocodeAdresses(self, inputfilename):
        # Stellen Sie sicher, dass der vorherige Thread beendet wird
        if hasattr(self, 'geocodingThread') and self.geocodingThread.isRunning():
            self.geocodingThread.terminate()
            self.geocodingThread.wait()
        self.geocodingThread = GeocodingThread(inputfilename)
        self.geocodingThread.calculation_done.connect(self.on_generation_done_geocode_Adress)
        self.geocodingThread.calculation_error.connect(self.on_generation_error_geocode_Adress)
        self.geocodingThread.start()
        self.progressBar.setRange(0, 0)  # Aktiviert den indeterministischen Modus

    def on_generation_done_geocode_Adress(self, fname):
        self.progressBar.setRange(0, 1)

    def on_generation_error_geocode_Adress(self, error_message):
        QMessageBox.critical(self, "Fehler beim Geocoding", str(error_message))
        self.progressBar.setRange(0, 1)  # Deaktiviert den indeterministischen Modus