"""
Filename: lod2_dialogs.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-03-07
Description: Contains the Dialogs for the LOD2Tab. These are the LOD2DownloadDialog and FilterDialog.
"""

import os
import sys
import json

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QFileDialog,
                                QFormLayout, QMessageBox)
from PyQt5.QtGui import QFont

from districtheatingsim.lod2.lod2_download import get_lod2_links, download_lod2_files
from districtheatingsim.lod2.process_lod2 import convert_shapefiles_to_geojson, merge_geojsons

LOD2_JSON_FILE = "/src/districtheatingsim/data/LOD2/landkreise_gemeinden.json"  # Pfad zur JSON-Datei mit Landkreisen & Gemeinden

def get_resource_path(relative_path):
    """
    Get the absolute path to the resource, works for dev and for PyInstaller.

    Args:
        relative_path (str): The relative path to the resource.

    Returns:
        str: The absolute path to the resource.
    """
    if getattr(sys, 'frozen', False):
        # If the application is frozen, the base path is the temp folder where PyInstaller extracts everything
        base_path = sys._MEIPASS
    else:
        # If the application is not frozen, the base path is the directory where the main file is located
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

class LOD2DownloadDialog(QDialog):
    def __init__(self, folder_manager, config_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LOD2 Daten herunterladen")
        self.setGeometry(300, 200, 400, 250)

        self.folder_manager = folder_manager
        self.config_manager = config_manager

        lod2_json_path  = get_resource_path("..\\data\\LOD2\\landkreise_gemeinden.json")

        with open(lod2_json_path, "r", encoding="utf-8") as f:
            self.lod2_data = json.load(f)

        # Speicherorte über `folder_manager` holen
        self.download_dir = os.path.join(self.folder_manager.project_folder, "Eingangsdaten allgemein\\LOD2\\downloads")
        self.extract_dir = os.path.join(self.folder_manager.project_folder, "Eingangsdaten allgemein\\LOD2\\extracted")
        self.geojson_dir = os.path.join(self.folder_manager.project_folder, "Eingangsdaten allgemein\\LOD2\\geojson")
        
        # UI-Elemente für Landkreise, Gemeinden, Paketauswahl
        self.landkreis_dropdown = QComboBox()
        self.landkreis_dropdown.addItems(sorted(self.lod2_data.keys()))
        self.landkreis_dropdown.currentTextChanged.connect(self.update_gemeinde_dropdown)

        self.gemeinde_dropdown = QComboBox()
        self.update_gemeinde_dropdown(self.landkreis_dropdown.currentText())

        self.lod2_package_dropdown = QComboBox()
        self.lod2_package_dropdown.addItem("LOD2_Shape")

        self.crs_dropdown = QComboBox()
        self.crs_dropdown.addItems(["EPSG:25833"])

        self.download_button = QPushButton("Download starten")
        self.download_button.clicked.connect(self.start_download)

        # Layout für den Dialog
        form_layout = QFormLayout()
        form_layout.addRow(QLabel("Landkreis:"), self.landkreis_dropdown)
        form_layout.addRow(QLabel("Gemeinde:"), self.gemeinde_dropdown)
        form_layout.addRow(QLabel("LOD2-Paket:"), self.lod2_package_dropdown)
        form_layout.addRow(QLabel("Ziel-CRS:"), self.crs_dropdown)
        self.layout = QVBoxLayout()
        self.layout.addLayout(form_layout)
        self.layout.addWidget(self.download_button)
        self.setLayout(self.layout)

    def update_gemeinde_dropdown(self, landkreis):
        """ Aktualisiert das Dropdown der Gemeinden basierend auf dem Landkreis. """
        self.gemeinde_dropdown.clear()
        if landkreis in self.lod2_data:
            gemeinden = self.lod2_data[landkreis]["gemeinden"]
            self.gemeinde_dropdown.addItems(sorted(gemeinden.keys()))

    def start_download(self):
        """ Startet den Download und verarbeitet die LOD2-Daten weiter. """
        landkreis = self.landkreis_dropdown.currentText()
        gemeinde = self.gemeinde_dropdown.currentText()

        # Download- und Entpackpfade setzen
        extract_folder = os.path.join(self.extract_dir, f"{landkreis}_{gemeinde}")
        geojson_folder = os.path.join(self.geojson_dir, f"{landkreis}_{gemeinde}")
        
        # Schritt 1: Download starten
        get_lod2_links(landkreis, gemeinde, self.download_dir)
        download_lod2_files(landkreis, gemeinde, self.download_dir, extract_folder)

        QMessageBox.information(self, "Fertig", "LOD2-Daten erfolgreich heruntergeladen und entpackt! Konvertierung zu GeoJSON startet...")

        # Schritt 2: Shapefiles -> GeoJSON konvertieren
        self.target_crs = self.crs_dropdown.currentText()
        geojson_files = convert_shapefiles_to_geojson(extract_folder, geojson_folder, self.target_crs)

        if not geojson_files:
            QMessageBox.critical(self, "Fehler", "Keine Shapefiles gefunden oder Fehler bei der Konvertierung!")
            return

        # Schritt 3: GeoJSONs mergen
        merged_geojson_path = os.path.join(self.geojson_dir, f"{landkreis}_{gemeinde}_LOD2.geojson")
        merge_geojsons(geojson_folder, merged_geojson_path, self.target_crs)

        QMessageBox.information(self, "Fertig", f"GeoJSON-Daten gespeichert unter: {merged_geojson_path}")

        self.accept()


class FilterDialog(QDialog):
    """
    A dialog window for filtering LOD2 data based on different input files and methods.

    Attributes:
        base_path (str): The base path for default file locations.
        inputLOD2geojsonLineEdit (QLineEdit): Line edit for input LOD2 geojson file path.
        inputLOD2geojsonButton (QPushButton): Button to browse for input LOD2 geojson file.
        inputfilterPolygonLineEdit (QLineEdit): Line edit for input filter polygon file path.
        inputfilterPolygonButton (QPushButton): Button to browse for input filter polygon file.
        inputfilterBuildingDataLineEdit (QLineEdit): Line edit for input filter building data csv file path.
        inputfilterBuildingDataButton (QPushButton): Button to browse for input filter building data csv file.
        outputLOD2geojsonLineEdit (QLineEdit): Line edit for output LOD2 geojson file path.
        outputLOD2geojsonButton (QPushButton): Button to browse for output LOD2 geojson file.
        filterMethodComboBox (QComboBox): Combo box to select the filter method.
    """
    def __init__(self, base_path, config_manager, parent=None):
        """
        Initializes the FilterDialog.

        Args:
            base_path (str): The base path for default file locations.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.base_path = base_path
        self.config_manager = config_manager

        self.initUI()

    def initUI(self):
        self.setWindowTitle("LOD2-Daten filtern")
        self.setGeometry(300, 300, 600, 400)
        
        layout = QVBoxLayout(self)
        font = QFont()
        font.setPointSize(10)

        self.inputLOD2geojsonLineEdit, self.inputLOD2geojsonButton = self.createFileInput(os.path.abspath(os.path.join(self.base_path, self.config_manager.get_relative_path("LOD2_Data_path"))), font)
        layout.addLayout(self.createFileInputLayout("Eingabe-LOD2-geojson:", self.inputLOD2geojsonLineEdit, self.inputLOD2geojsonButton, font))

        self.inputfilterPolygonLineEdit, self.inputfilterPolygonButton = self.createFileInput(os.path.join(self.base_path, self.config_manager.get_relative_path("area_polygon_file_path")), font)
        layout.addLayout(self.createFileInputLayout("Eingabe-Filter-Polygon-shapefile:", self.inputfilterPolygonLineEdit, self.inputfilterPolygonButton, font))

        self.inputfilterBuildingDataLineEdit, self.inputfilterBuildingDataButton = self.createFileInput(os.path.abspath(os.path.join(self.base_path, self.config_manager.get_relative_path("current_building_data_path"))), font)
        layout.addLayout(self.createFileInputLayout("Eingabe-Filter-Gebäude-csv:", self.inputfilterBuildingDataLineEdit, self.inputfilterBuildingDataButton, font))

        self.outputLOD2geojsonLineEdit, self.outputLOD2geojsonButton = self.createFileInput(os.path.join(self.base_path, self.config_manager.get_relative_path("LOD2_area_path")), font)
        layout.addLayout(self.createFileInputLayout("Ausgabe-LOD2-geojson:", self.outputLOD2geojsonLineEdit, self.outputLOD2geojsonButton, font))

        self.filterMethodComboBox = QComboBox(self)
        self.filterMethodComboBox.addItems(["Filter by Building Data CSV", "Filter by Polygon"])
        self.filterMethodComboBox.currentIndexChanged.connect(self.updateFilterInputVisibility)
        layout.addWidget(self.filterMethodComboBox)

        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Abbrechen")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        self.updateFilterInputVisibility()

    def createFileInput(self, default_path, font):
        """
        Creates a file input widget with a QLineEdit and a QPushButton.

        Args:
            default_path (str): The default path to be displayed in the QLineEdit.
            font (QFont): The font to be used for the widgets.

        Returns:
            tuple: A tuple containing the QLineEdit and QPushButton.
        """
        lineEdit = QLineEdit(default_path)
        lineEdit.setFont(font)
        button = QPushButton("Durchsuchen")
        button.setFont(font)
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def createFileInputLayout(self, label_text, lineEdit, button, font):
        """
        Creates a horizontal layout for the file input widgets.

        Args:
            label_text (str): The text for the QLabel.
            lineEdit (QLineEdit): The QLineEdit for file input.
            button (QPushButton): The QPushButton for browsing files.
            font (QFont): The font to be used for the QLabel.

        Returns:
            QHBoxLayout: The horizontal layout containing the label, line edit, and button.
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
        Opens a file dialog to select a file and sets the selected file path to the QLineEdit.

        Args:
            lineEdit (QLineEdit): The QLineEdit to set the selected file path.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", lineEdit.text(), "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def updateFilterInputVisibility(self):
        """
        Updates the visibility of the file input widgets based on the selected filter method.
        """
        filter_method = self.filterMethodComboBox.currentText()
        if filter_method == "Filter by Polygon":
            self.inputfilterPolygonLineEdit.show()
            self.inputfilterBuildingDataLineEdit.hide()
            self.inputfilterPolygonButton.show()
            self.inputfilterBuildingDataButton.hide()
        elif filter_method == "Filter by Building Data CSV":
            self.inputfilterPolygonLineEdit.hide()
            self.inputfilterBuildingDataLineEdit.show()
            self.inputfilterPolygonButton.hide()
            self.inputfilterBuildingDataButton.show()