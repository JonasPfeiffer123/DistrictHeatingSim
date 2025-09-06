"""
LOD2 Dialogs Module
==================

Dialog widgets for LOD2 data download and filtering operations.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-03-07
"""

import os
import json

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QFileDialog,
                                QFormLayout, QMessageBox)
from PyQt6.QtGui import QFont

from districtheatingsim.lod2.lod2_download import get_lod2_links, download_lod2_files
from districtheatingsim.lod2.process_lod2 import convert_shapefiles_to_geojson, merge_geojsons
from districtheatingsim.utilities.utilities import get_resource_path

class LOD2DownloadDialog(QDialog):
    """
    Dialog for downloading and processing LOD2 building data.
    """
    
    def __init__(self, folder_manager, config_manager, parent=None):
        """
        Initialize LOD2 download dialog.

        Parameters
        ----------
        folder_manager : FolderManager
            Project folder manager.
        config_manager : ConfigManager
            Configuration manager.
        parent : QWidget, optional
            Parent widget.
        """
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
        """
        Update municipality dropdown based on selected district.

        Parameters
        ----------
        landkreis : str
            Selected district name.
        """
        self.gemeinde_dropdown.clear()
        if landkreis in self.lod2_data:
            gemeinden = self.lod2_data[landkreis]["gemeinden"]
            self.gemeinde_dropdown.addItems(sorted(gemeinden.keys()))

    def start_download(self):
        """Start LOD2 data download and processing workflow."""
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
    Dialog for filtering LOD2 data based on different input methods.
    """
    
    def __init__(self, base_path, config_manager, parent=None):
        """
        Initialize filter dialog.

        Parameters
        ----------
        base_path : str
            Base path for default file locations.
        config_manager : ConfigManager
            Configuration manager.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.base_path = base_path
        self.config_manager = config_manager

        self.initUI()

    def initUI(self):
        """Initialize user interface components."""
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
        Create file input widget with line edit and browse button.

        Parameters
        ----------
        default_path : str
            Default file path.
        font : QFont
            Font for widgets.

        Returns
        -------
        tuple
            Line edit and button widgets.
        """
        lineEdit = QLineEdit(default_path)
        lineEdit.setFont(font)
        button = QPushButton("Durchsuchen")
        button.setFont(font)
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def createFileInputLayout(self, label_text, lineEdit, button, font):
        """
        Create horizontal layout for file input widgets.

        Parameters
        ----------
        label_text : str
            Label text.
        lineEdit : QLineEdit
            File input line edit.
        button : QPushButton
            Browse button.
        font : QFont
            Font for label.

        Returns
        -------
        QHBoxLayout
            Horizontal layout with label, line edit, and button.
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
        Open file dialog and update line edit with selected file path.

        Parameters
        ----------
        lineEdit : QLineEdit
            Line edit to update with selected file path.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", lineEdit.text(), "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def updateFilterInputVisibility(self):
        """Update visibility of file input widgets based on selected filter method."""
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