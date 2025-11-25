"""
Leaflet Dialogs Module
=====================

Dialog widgets for network generation, OSM data download, and building queries.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-10
"""

import os
import json
import traceback

import geopandas as gpd
import pandas as pd
from math import radians, sin, cos, sqrt, atan2
from shapely.geometry import box, Point
from shapely.ops import transform
import pyproj

from PyQt6.QtWidgets import QVBoxLayout, QLineEdit, QDialog, QComboBox, QPushButton, \
    QFormLayout, QHBoxLayout, QFileDialog, QMessageBox, QLabel, QWidget, \
    QTableWidget, QTableWidgetItem, QGroupBox, QCheckBox, QProgressDialog
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QClipboard

from pyproj import Transformer

from districtheatingsim.gui.LeafletTab.net_generation_threads import GeocodingThread, OSMStreetDownloadThread, OSMBuildingDownloadThread
from districtheatingsim.geocoding.geocoding import get_coordinates
from districtheatingsim.osm.import_osm_data_geojson import build_query, download_data, save_to_file
   
class LayerGenerationDialog(QDialog):
    """
    Dialog for generating layers for heat network visualization.
    """
    accepted_inputs = pyqtSignal(dict)
    request_map_coordinate = pyqtSignal()

    def __init__(self, base_path, config_manager, parent=None):
        """
        Initialize layer generation dialog.

        Parameters
        ----------
        base_path : str
            Base path for file operations.
        config_manager : ConfigManager
            Configuration manager instance.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.base_path = base_path
        self.visualization_tab = None
        self.config_manager = config_manager
        self.waiting_for_map_click = False
        self.custom_filter = '["highway"~"primary|secondary|tertiary|residential|living_street|service"]'  # Default filter
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.initUI()

    def initUI(self):
        """Initialize user interface components."""
        self.setWindowTitle('Wärmenetzgenerierung')
        self.setGeometry(300, 300, 800, 800)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Data Input Section
        dataGroup = QGroupBox("Dateneingabe")
        dataLayout = QFormLayout()
        dataLayout.setSpacing(10)

        self.dataInput, self.dataCsvButton = self.createFileInput(os.path.abspath(os.path.join(self.base_path, self.config_manager.get_relative_path('current_building_data_path'))))
        dataLayout.addRow("Gebäudestandorte (CSV):", self.createFileInputLayout(self.dataInput, self.dataCsvButton))
        
        self.generationModeComboBox = QComboBox(self)
        self.generationModeComboBox.addItems(["OSMnx", "Advanced MST", "MST"])
        self.generationModeComboBox.currentIndexChanged.connect(self.toggleGenerationMode)
        dataLayout.addRow("Netzgenerierungsmodus:", self.generationModeComboBox)

        self.fileInput, self.fileButton = self.createFileInput(os.path.abspath(os.path.join(self.base_path, self.config_manager.get_relative_path('OSM_streets_path'))))
        self.streetLayerLabel = QLabel("GeoJSON-Straßen-Layer:")
        self.streetLayerWidget = self.createFileInputLayout(self.fileInput, self.fileButton)
        dataLayout.addRow(self.streetLayerLabel, self.streetLayerWidget)
        
        # OSMnx Advanced Settings (collapsible)
        self.osmnxAdvancedWidget = QWidget()
        osmnxAdvancedLayout = QVBoxLayout(self.osmnxAdvancedWidget)
        osmnxAdvancedLayout.setContentsMargins(0, 5, 0, 5)
        
        # Toggle button for advanced settings
        self.osmnxAdvancedToggle = QPushButton("▶ Erweiterte OSMnx-Einstellungen")
        self.osmnxAdvancedToggle.setFlat(True)
        self.osmnxAdvancedToggle.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 5px;
                border: none;
                background-color: transparent;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.osmnxAdvancedToggle.clicked.connect(self.toggleOSMnxAdvancedSettings)
        osmnxAdvancedLayout.addWidget(self.osmnxAdvancedToggle)
        
        # Content widget (initially hidden)
        self.osmnxAdvancedContent = QWidget()
        osmnxContentLayout = QVBoxLayout(self.osmnxAdvancedContent)
        osmnxContentLayout.setContentsMargins(20, 5, 0, 5)
        
        filterLabel = QLabel("Straßentypen für OSMnx-Filter:")
        filterLabel.setStyleSheet("font-weight: bold; color: #333333; margin-top: 5px;")
        osmnxContentLayout.addWidget(filterLabel)
        
        # Highway type checkboxes
        self.highwayCheckboxes = {}
        highway_types = [
            ("primary", "Hauptstraßen (primary)"),
            ("secondary", "Nebenstraßen (secondary)"),
            ("tertiary", "Tertiärstraßen (tertiary)"),
            ("residential", "Wohnstraßen (residential)"),
            ("living_street", "Verkehrsberuhigte Bereiche (living_street)"),
            ("service", "Erschließungsstraßen (service)")
        ]
        
        for key, label in highway_types:
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)  # All checked by default
            checkbox.stateChanged.connect(self.updateFilters)
            self.highwayCheckboxes[key] = checkbox
            osmnxContentLayout.addWidget(checkbox)
        
        # Select/Deselect all buttons
        selectButtonLayout = QHBoxLayout()
        selectAllBtn = QPushButton("Alle auswählen")
        selectAllBtn.clicked.connect(lambda: self.setAllHighwayCheckboxes(True))
        selectButtonLayout.addWidget(selectAllBtn)
        
        deselectAllBtn = QPushButton("Alle abwählen")
        deselectAllBtn.clicked.connect(lambda: self.setAllHighwayCheckboxes(False))
        selectButtonLayout.addWidget(deselectAllBtn)
        osmnxContentLayout.addLayout(selectButtonLayout)
        
        self.osmnxAdvancedContent.setVisible(False)  # Initially collapsed
        osmnxAdvancedLayout.addWidget(self.osmnxAdvancedContent)
        
        dataLayout.addRow("", self.osmnxAdvancedWidget)
        
        dataGroup.setLayout(dataLayout)
        layout.addWidget(dataGroup)

        # Generator Coordinates Section
        coordGroup = QGroupBox("Erzeugerstandorte")
        coordLayout = QVBoxLayout()
        coordLayout.setSpacing(10)

        # Input mode selection
        modeLayout = QFormLayout()
        self.locationModeComboBox = QComboBox(self)
        self.locationModeComboBox.addItems(["Koordinaten direkt eingeben", "Adresse eingeben", "Koordinaten aus CSV laden"])
        self.locationModeComboBox.currentIndexChanged.connect(self.toggleLocationInputMode)
        modeLayout.addRow("Eingabemodus:", self.locationModeComboBox)
        coordLayout.addLayout(modeLayout)

        # Coordinate input
        coordInputLayout = QFormLayout()
        self.coordSystemComboBox = QComboBox(self)
        self.coordSystemComboBox.addItems(["EPSG:25833", "WGS84"])
        coordInputLayout.addRow("Koordinatensystem:", self.coordSystemComboBox)

        self.coordInput = QLineEdit(self)
        self.coordInput.setText("499827.8585093066,55666161.599635682") # Görlitz
        self.coordInput.setToolTip("Eingabe in folgender Form: 'X-Koordinate, Y-Koordinate'")
        coordInputLayout.addRow("Koordinaten:", self.coordInput)
        
        # Button layout for coordinate input
        coordButtonLayout = QHBoxLayout()
        self.addCoordButton = QPushButton("Koordinate hinzufügen", self)
        self.addCoordButton.clicked.connect(self.addCoordFromInput)
        coordButtonLayout.addWidget(self.addCoordButton)
        
        self.mapPickerButton = QPushButton("Aus Karte wählen", self)
        self.mapPickerButton.clicked.connect(self.activateMapPicker)
        self.mapPickerButton.setToolTip("Klicken Sie auf die Karte, um Koordinaten auszuwählen")
        coordButtonLayout.addWidget(self.mapPickerButton)
        
        coordInputLayout.addRow("", coordButtonLayout)
        coordLayout.addLayout(coordInputLayout)

        # Address input
        addressInputLayout = QFormLayout()
        self.addressInput = QLineEdit(self)
        self.addressInput.setText("Deutschland,Sachsen,Bad Muskau,Gablenzer Straße 4")
        self.addressInput.setToolTip("Eingabe in folgender Form: 'Land,Bundesland,Stadt,Adresse'")
        addressInputLayout.addRow("Adresse:", self.addressInput)
        
        self.geocodeButton = QPushButton("Adresse geocodieren", self)
        self.geocodeButton.clicked.connect(self.geocodeAndAdd)
        addressInputLayout.addRow("", self.geocodeButton)
        coordLayout.addLayout(addressInputLayout)

        # CSV import
        csvImportLayout = QHBoxLayout()
        self.importCsvButton = QPushButton("Koordinaten aus CSV laden", self)
        self.importCsvButton.clicked.connect(self.importCoordsFromCSV)
        csvImportLayout.addWidget(self.importCsvButton)
        csvImportLayout.addStretch()
        coordLayout.addLayout(csvImportLayout)

        # Coordinate table
        tableLabel = QLabel("Erzeugerkoordinaten:")
        coordLayout.addWidget(tableLabel)
        
        self.coordTable = QTableWidget(self)
        self.coordTable.setColumnCount(2)
        self.coordTable.setHorizontalHeaderLabels(["X-Koordinate (UTM)", "Y-Koordinate (UTM)"])
        self.coordTable.setColumnWidth(0, 200)
        self.coordTable.setColumnWidth(1, 200)
        self.coordTable.setMinimumHeight(150)
        self.coordTable.setMaximumHeight(200)
        coordLayout.addWidget(self.coordTable)

        # Table action buttons
        tableButtonLayout = QHBoxLayout()
        self.copyButton = QPushButton("Koordinaten kopieren", self)
        self.copyButton.clicked.connect(self.copyCoordinates)
        self.copyButton.setToolTip("Kopiert alle Koordinaten in die Zwischenablage")
        tableButtonLayout.addWidget(self.copyButton)
        
        self.pasteButton = QPushButton("Koordinaten einfügen", self)
        self.pasteButton.clicked.connect(self.pasteCoordinates)
        self.pasteButton.setToolTip("Fügt Koordinaten aus der Zwischenablage ein")
        tableButtonLayout.addWidget(self.pasteButton)
        
        self.saveButton = QPushButton("Als CSV speichern", self)
        self.saveButton.clicked.connect(self.saveCoordinatesToCSV)
        self.saveButton.setToolTip("Speichert Koordinaten als CSV-Datei")
        tableButtonLayout.addWidget(self.saveButton)
        
        self.deleteCoordButton = QPushButton("Ausgewählte löschen", self)
        self.deleteCoordButton.clicked.connect(self.deleteSelectedRow)
        tableButtonLayout.addWidget(self.deleteCoordButton)
        
        self.clearButton = QPushButton("Alle löschen", self)
        self.clearButton.clicked.connect(self.clearAllCoordinates)
        tableButtonLayout.addWidget(self.clearButton)
        
        coordLayout.addLayout(tableButtonLayout)
        
        coordGroup.setLayout(coordLayout)
        layout.addWidget(coordGroup)

        # Dialog buttons
        self.okButton = QPushButton("OK", self)
        self.okButton.clicked.connect(self.onAccept)
        self.cancelButton = QPushButton("Abbrechen", self)
        self.cancelButton.clicked.connect(self.reject)

        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch(1)
        buttonLayout.addWidget(self.okButton)
        buttonLayout.addWidget(self.cancelButton)
        
        layout.addLayout(buttonLayout)

        # Styling
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton:disabled, QLineEdit:disabled, QComboBox:disabled {
                background-color: #f0f0f0;
                color: #a0a0a0;
            }
            QPushButton {
                padding: 5px 10px;
            }
        """)

        self.toggleLocationInputMode(0)
        self.toggleGenerationMode(0)
        self.setLayout(layout)

    def setVisualizationTab(self, visualization_tab):
        """
        Set visualization tab reference.

        Parameters
        ----------
        visualization_tab : QWidget
            VisualizationTab instance.
        """
        self.visualization_tab = visualization_tab

    def toggleLocationInputMode(self, index):
        """
        Toggle input fields based on location mode.

        Parameters
        ----------
        index : int
            Selected mode index.
        """
        # Mode 0: Direct coordinate input
        self.coordSystemComboBox.setEnabled(index == 0)
        self.coordInput.setEnabled(index == 0)
        self.addCoordButton.setEnabled(index == 0)
        
        # Mode 1: Address geocoding
        self.addressInput.setEnabled(index == 1)
        self.geocodeButton.setEnabled(index == 1)
        
        # Mode 2: CSV import
        self.importCsvButton.setEnabled(index == 2)

    def toggleGenerationMode(self, index):
        """
        Toggle street layer visibility based on generation mode.

        Parameters
        ----------
        index : int
            Selected generation mode index.
        """
        # Street layer only needed for non-OSMnx modes
        is_osmnx = (self.generationModeComboBox.currentText() == "OSMnx")
        self.streetLayerLabel.setVisible(not is_osmnx)
        self.fileInput.setVisible(not is_osmnx)
        self.fileButton.setVisible(not is_osmnx)
        
        # Show OSMnx advanced settings only for OSMnx mode
        self.osmnxAdvancedWidget.setVisible(is_osmnx)

    def toggleOSMnxAdvancedSettings(self):
        """Toggle visibility of OSMnx advanced settings."""
        is_visible = self.osmnxAdvancedContent.isVisible()
        self.osmnxAdvancedContent.setVisible(not is_visible)
        
        # Update button text with arrow
        if is_visible:
            self.osmnxAdvancedToggle.setText("▶ Erweiterte OSMnx-Einstellungen")
        else:
            self.osmnxAdvancedToggle.setText("▼ Erweiterte OSMnx-Einstellungen")
    
    def setAllHighwayCheckboxes(self, checked):
        """Set all highway checkboxes to checked or unchecked.
        
        Parameters
        ----------
        checked : bool
            True to check all, False to uncheck all.
        """
        for checkbox in self.highwayCheckboxes.values():
            checkbox.setChecked(checked)
    
    def updateFilters(self):
        """Update custom filter string based on selected highway types."""
        selected_types = [key for key, checkbox in self.highwayCheckboxes.items() if checkbox.isChecked()]
        
        if selected_types:
            # Build filter string like: ["highway"~"primary|secondary|tertiary"]
            filter_string = '|'.join(selected_types)
            self.custom_filter = f'["highway"~"{filter_string}"]'
        else:
            # No types selected - use None to fall back to default
            self.custom_filter = None

    def createFileInputLayout(self, lineEdit, button):
        """
        Create file input layout.

        Parameters
        ----------
        lineEdit : QLineEdit
            File path input widget.
        button : QPushButton
            Browse button widget.

        Returns
        -------
        QHBoxLayout
            Layout containing file input widgets.
        """
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def createFileInput(self, default_path):
        """
        Create file input widget with browse button.

        Parameters
        ----------
        default_path : str
            Default file path.

        Returns
        -------
        tuple
            Line edit and button widgets.
        """
        lineEdit = QLineEdit(default_path)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.openFileDialog(lineEdit))
        return lineEdit, button

    def openFileDialog(self, lineEdit):
        """
        Open file dialog and update line edit.

        Parameters
        ----------
        lineEdit : QLineEdit
            Widget to update with selected file path.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", f"{self.base_path}", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def addCoordFromInput(self):
        """Add coordinates from input field to table."""
        coords = self.coordInput.text().split(',')
        if len(coords) == 2:
            x, y = map(str.strip, coords)
            source_crs = self.coordSystemComboBox.currentText()
            x_transformed, y_transformed = self.transform_coordinates(float(x), float(y), source_crs)
            self.insertRowInTable(x_transformed, y_transformed)

    def geocodeAndAdd(self):
        """Geocode address and add coordinates to table."""
        address = self.addressInput.text()
        if address:
            x, y = get_coordinates(address)
            if x and y:
                self.insertRowInTable(str(x), str(y))

    def importCoordsFromCSV(self):
        """Import coordinates from CSV file."""
        filename, _ = QFileDialog.getOpenFileName(self, "CSV-Datei auswählen", f"{self.base_path}", "CSV Files (*.csv)")
        if filename:
            data = pd.read_csv(filename, delimiter=';', usecols=['UTM_X', 'UTM_Y'])
            for _, row in data.iterrows():
                self.insertRowInTable(str(row['UTM_X']), str(row['UTM_Y']))

    def transform_coordinates(self, x, y, source_crs):
        """
        Transform coordinates to EPSG:25833.

        Parameters
        ----------
        x : float
            X-coordinate.
        y : float
            Y-coordinate.
        source_crs : str
            Source coordinate system.

        Returns
        -------
        tuple
            Transformed coordinates.
        """
        if source_crs == "WGS84":
            transformer = Transformer.from_crs("EPSG:4326", "EPSG:25833", always_xy=True)
        else:
            transformer = Transformer.from_crs("EPSG:25833", "EPSG:25833", always_xy=True)
        x_transformed, y_transformed = transformer.transform(x, y)
        return x_transformed, y_transformed

    def insertRowInTable(self, x, y):
        """
        Insert coordinate row in table.

        Parameters
        ----------
        x : str
            X-coordinate.
        y : str
            Y-coordinate.
        """
        row_count = self.coordTable.rowCount()
        self.coordTable.insertRow(row_count)
        self.coordTable.setItem(row_count, 0, QTableWidgetItem(str(x)))
        self.coordTable.setItem(row_count, 1, QTableWidgetItem(str(y)))

    def deleteSelectedRow(self):
        """Delete selected row from coordinates table."""
        selected_row = self.coordTable.currentRow()
        if selected_row >= 0:
            self.coordTable.removeRow(selected_row)

    def clearAllCoordinates(self):
        """Clear all coordinates from table."""
        reply = QMessageBox.question(self, 'Bestätigung', 
                                    'Möchten Sie wirklich alle Koordinaten löschen?',
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.coordTable.setRowCount(0)

    def copyCoordinates(self):
        """Copy all coordinates to clipboard."""
        if self.coordTable.rowCount() == 0:
            QMessageBox.information(self, "Information", "Keine Koordinaten zum Kopieren vorhanden.")
            return
        
        coordinates_text = ""
        for row in range(self.coordTable.rowCount()):
            x = self.coordTable.item(row, 0).text()
            y = self.coordTable.item(row, 1).text()
            coordinates_text += f"{x},{y}\n"
        
        clipboard = QClipboard()
        clipboard.setText(coordinates_text.strip())
        QMessageBox.information(self, "Erfolg", f"{self.coordTable.rowCount()} Koordinate(n) in die Zwischenablage kopiert.")

    def pasteCoordinates(self):
        """Paste coordinates from clipboard."""
        clipboard = QClipboard()
        text = clipboard.text().strip()
        
        if not text:
            QMessageBox.warning(self, "Warnung", "Zwischenablage ist leer.")
            return
        
        lines = text.split('\n')
        added_count = 0
        
        for line in lines:
            line = line.strip()
            if ',' in line:
                parts = line.split(',')
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].strip())
                        y = float(parts[1].strip())
                        self.insertRowInTable(x, y)
                        added_count += 1
                    except ValueError:
                        continue
        
        if added_count > 0:
            QMessageBox.information(self, "Erfolg", f"{added_count} Koordinate(n) eingefügt.")
        else:
            QMessageBox.warning(self, "Warnung", "Keine gültigen Koordinaten in der Zwischenablage gefunden.")

    def saveCoordinatesToCSV(self):
        """Save coordinates to CSV file."""
        if self.coordTable.rowCount() == 0:
            QMessageBox.information(self, "Information", "Keine Koordinaten zum Speichern vorhanden.")
            return
        
        # Ask user what format to save
        msgBox = QMessageBox(self)
        msgBox.setWindowTitle("Speicherformat wählen")
        msgBox.setText("In welchem Format möchten Sie die Koordinaten speichern?")
        coordButton = msgBox.addButton("Nur Koordinaten", QMessageBox.ButtonRole.ActionRole)
        addressButton = msgBox.addButton("Mit Adresse", QMessageBox.ButtonRole.ActionRole)
        cancelButton = msgBox.addButton("Abbrechen", QMessageBox.ButtonRole.RejectRole)
        msgBox.exec()
        
        clicked_button = msgBox.clickedButton()
        
        if clicked_button == cancelButton:
            return
        
        filename, _ = QFileDialog.getSaveFileName(self, "CSV-Datei speichern", 
                                                  os.path.join(self.base_path, "erzeuger_koordinaten.csv"),
                                                  "CSV Files (*.csv)")
        if not filename:
            return
        
        try:
            data = []
            for row in range(self.coordTable.rowCount()):
                x = self.coordTable.item(row, 0).text()
                y = self.coordTable.item(row, 1).text()
                
                if clicked_button == addressButton:
                    # Try to reverse geocode
                    address = self.reverse_geocode(float(x), float(y))
                    data.append({'UTM_X': x, 'UTM_Y': y, 'Adresse': address})
                else:
                    data.append({'UTM_X': x, 'UTM_Y': y})
            
            df = pd.DataFrame(data)
            df.to_csv(filename, sep=';', index=False, encoding='utf-8-sig')
            QMessageBox.information(self, "Erfolg", f"Koordinaten erfolgreich gespeichert:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern der Datei:\n{str(e)}")

    def reverse_geocode(self, x, y):
        """Simple reverse geocoding (returns formatted coordinates if geocoding fails)."""
        try:
            # Transform to WGS84 for geocoding
            transformer = Transformer.from_crs("EPSG:25833", "EPSG:4326", always_xy=True)
            lon, lat = transformer.transform(x, y)
            
            # Use Nominatim for reverse geocoding
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent="districtheatingsim")
            location = geolocator.reverse(f"{lat}, {lon}", language='de', timeout=5)
            
            if location:
                return location.address
            else:
                return f"Lat: {lat:.6f}, Lon: {lon:.6f}"
        except:
            return f"UTM X: {x:.2f}, Y: {y:.2f}"

    def activateMapPicker(self):
        """Activate map coordinate picker mode."""
        if not self.visualization_tab:
            QMessageBox.warning(self, "Warnung", "Keine Kartenverbindung verfügbar.")
            return
        
        self.waiting_for_map_click = True
        self.mapPickerButton.setEnabled(False)
        self.mapPickerButton.setText("Warte auf Kartenklick...")
        self.mapPickerButton.setStyleSheet("background-color: #ffc107; color: black;")
        
        # Emit signal to activate map picker mode
        self.request_map_coordinate.emit()
    
    def receiveMapCoordinates(self, lat, lon):
        """Receive coordinates from map click.
        
        Parameters
        ----------
        lat : float
            Latitude (WGS84).
        lon : float
            Longitude (WGS84).
        """
        if not self.waiting_for_map_click:
            return
        
        # Reset button state immediately
        self.waiting_for_map_click = False
        self.mapPickerButton.setEnabled(True)
        self.mapPickerButton.setText("Aus Karte wählen")
        # Reset to default button style (remove the yellow background)
        self.mapPickerButton.setStyleSheet("background-color: none;")
        
        try:
            # Transform from WGS84 to EPSG:25833
            transformer = Transformer.from_crs("EPSG:4326", "EPSG:25833", always_xy=True)
            x, y = transformer.transform(lon, lat)
            
            # Update input field
            self.coordInput.setText(f"{x},{y}")
            
            # Automatically add to table
            self.insertRowInTable(x, y)
            
            QMessageBox.information(self, "Erfolg", 
                                   f"Koordinate aus Karte übernommen:\nUTM X: {x:.2f}\nUTM Y: {y:.2f}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler bei der Koordinatentransformation:\n{str(e)}")

    def getInputs(self):
        """
        Get dialog inputs.

        Returns
        -------
        dict
            Dictionary containing input values.
        """
        coordinates = []
        for row in range(self.coordTable.rowCount()):
            x = self.coordTable.item(row, 0).text()
            y = self.coordTable.item(row, 1).text()
            if x and y:
                coordinates.append((float(x), float(y)))

        # Update custom filter one last time before returning
        self.updateFilters()

        return {
            "streetLayer": self.fileInput.text(),
            "dataCsv": self.dataInput.text(),
            "coordinates": coordinates,
            "generation_mode": self.generationModeComboBox.currentText(),
            "custom_filter": self.custom_filter
        }

    def onAccept(self):
        """Handle accept event."""
        inputs = self.getInputs()
        self.accepted_inputs.emit(inputs)
        self.accept()

class DownloadOSMDataDialog(QDialog):
    """
    Dialog for downloading OSM street data with OSMnx.
    """
    def __init__(self, base_path, config_manager, parent, parent_pres):
        """
        Initialize OSM data download dialog.

        Parameters
        ----------
        base_path : str
            Base path for file operations.
        config_manager : ConfigManager
            Configuration manager instance.
        parent : QWidget
            Parent widget.
        parent_pres : object
            Parent presenter instance.
        """
        super().__init__(parent)
        self.base_path = base_path
        self.config_manager = config_manager
        self.parent_pres = parent_pres
        self.visualization_tab = None
        self.waiting_for_polygon = False
        self.custom_filter = '["highway"~"primary|secondary|tertiary|residential|living_street|service"]'
        self.download_thread = None
        self.progress_dialog = None
        
        # Set window flags to allow interaction with map while dialog is open
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        
        self.initUI()

    def initUI(self):
        """Initialize user interface components."""
        self.setWindowTitle("OSM Straßendaten herunterladen")
        self.setGeometry(300, 300, 600, 700)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Area selection group
        areaGroup = QGroupBox("Bereichsauswahl")
        areaLayout = QVBoxLayout()
        
        self.areaTypeComboBox = QComboBox(self)
        self.areaTypeComboBox.addItems([
            "Stadt/Ortsname",
            "Bereich um Gebäude aus CSV",
            "Polygon aus GeoJSON",
            "Polygon auf Karte zeichnen"
        ])
        self.areaTypeComboBox.currentIndexChanged.connect(self.toggleAreaType)
        areaLayout.addWidget(QLabel("Bereichstyp:"))
        areaLayout.addWidget(self.areaTypeComboBox)
        
        # City name input
        self.cityWidget = QWidget()
        cityLayout = QVBoxLayout(self.cityWidget)
        cityLayout.setContentsMargins(0, 5, 0, 0)
        self.cityLineEdit = QLineEdit("Zittau")
        cityLayout.addWidget(QLabel("Stadt/Ortsname:"))
        cityLayout.addWidget(self.cityLineEdit)
        areaLayout.addWidget(self.cityWidget)
        
        # CSV buildings input
        self.csvWidget = QWidget()
        csvLayout = QVBoxLayout(self.csvWidget)
        csvLayout.setContentsMargins(0, 5, 0, 0)
        self.csvLineEdit, self.csvButton = self.createFileInput(
            os.path.join(self.base_path, self.config_manager.get_relative_path('current_building_data_path'))
        )
        csvLayout.addWidget(QLabel("CSV-Datei mit Gebäudestandorten:"))
        csvLayout.addLayout(self.createFileInputLayout(self.csvLineEdit, self.csvButton))
        
        # Buffer distance
        bufferLayout = QHBoxLayout()
        self.bufferLineEdit = QLineEdit("500")
        self.bufferLineEdit.setMaximumWidth(100)
        bufferLayout.addWidget(QLabel("Puffer um Gebäude (Meter):"))
        bufferLayout.addWidget(self.bufferLineEdit)
        bufferLayout.addStretch()
        csvLayout.addLayout(bufferLayout)
        areaLayout.addWidget(self.csvWidget)
        
        # Polygon GeoJSON input
        self.polygonWidget = QWidget()
        polygonLayout = QVBoxLayout(self.polygonWidget)
        polygonLayout.setContentsMargins(0, 5, 0, 0)
        self.polygonLineEdit, self.polygonButton = self.createFileInput(f"{self.base_path}/")
        polygonLayout.addWidget(QLabel("GeoJSON-Datei mit Polygon:"))
        polygonLayout.addLayout(self.createFileInputLayout(self.polygonLineEdit, self.polygonButton))
        areaLayout.addWidget(self.polygonWidget)
        
        # Map polygon drawing
        self.mapDrawWidget = QWidget()
        mapDrawLayout = QVBoxLayout(self.mapDrawWidget)
        mapDrawLayout.setContentsMargins(0, 5, 0, 0)
        
        infoLabel = QLabel("Zeichnen Sie ein Polygon auf der Karte, um den Downloadbereich festzulegen.")
        infoLabel.setWordWrap(True)
        infoLabel.setStyleSheet("color: #666666; font-style: italic;")
        mapDrawLayout.addWidget(infoLabel)
        
        self.drawPolygonButton = QPushButton("Polygon auf Karte zeichnen", self)
        self.drawPolygonButton.clicked.connect(self.activateMapPolygonDrawing)
        mapDrawLayout.addWidget(self.drawPolygonButton)
        
        self.polygonStatusLabel = QLabel("Status: Kein Polygon gezeichnet")
        self.polygonStatusLabel.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        mapDrawLayout.addWidget(self.polygonStatusLabel)
        
        areaLayout.addWidget(self.mapDrawWidget)
        
        areaGroup.setLayout(areaLayout)
        layout.addWidget(areaGroup)

        # Street type selection - shared by both methods
        self.streetTypeGroup = QGroupBox("Straßentypen")
        streetTypeLayout = QVBoxLayout()
        
        filterLabel = QLabel("Wählen Sie die herunterzuladenden Straßentypen:")
        filterLabel.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        streetTypeLayout.addWidget(filterLabel)
        
        self.highwayCheckboxes = {}
        highway_types = [
            ("primary", "Hauptstraßen (primary)"),
            ("secondary", "Nebenstraßen (secondary)"),
            ("tertiary", "Tertiärstraßen (tertiary)"),
            ("residential", "Wohnstraßen (residential)"),
            ("living_street", "Verkehrsberuhigte Bereiche (living_street)"),
            ("service", "Erschließungsstraßen (service)")
        ]
        
        for key, label in highway_types:
            checkbox = QCheckBox(label)
            # Default: primary, secondary, tertiary, residential, living_street, service checked
            checkbox.setChecked(key in ["primary", "secondary", "tertiary", "residential", "living_street", "service"])
            checkbox.stateChanged.connect(self.updateFilters)
            self.highwayCheckboxes[key] = checkbox
            streetTypeLayout.addWidget(checkbox)
        
        # Select/Deselect all buttons
        selectButtonLayout = QHBoxLayout()
        selectAllBtn = QPushButton("Alle auswählen")
        selectAllBtn.clicked.connect(lambda: self.setAllHighwayCheckboxes(True))
        selectButtonLayout.addWidget(selectAllBtn)
        
        deselectAllBtn = QPushButton("Alle abwählen")
        deselectAllBtn.clicked.connect(lambda: self.setAllHighwayCheckboxes(False))
        selectButtonLayout.addWidget(deselectAllBtn)
        streetTypeLayout.addLayout(selectButtonLayout)
        
        self.streetTypeGroup.setLayout(streetTypeLayout)
        layout.addWidget(self.streetTypeGroup)

        # Output file
        fileGroup = QGroupBox("Ausgabedatei")
        fileLayout = QVBoxLayout()
        
        self.filenameLineEdit, fileButton = self.createFileInput(
            os.path.abspath(os.path.join(self.base_path, self.config_manager.get_relative_path('OSM_streets_path')))
        )
        fileLayout.addWidget(QLabel("Speicherpfad für GeoJSON:"))
        fileLayout.addLayout(self.createFileInputLayout(self.filenameLineEdit, fileButton))
        
        fileGroup.setLayout(fileLayout)
        layout.addWidget(fileGroup)

        # Action buttons
        buttonLayout = QHBoxLayout()
        
        self.queryButton = QPushButton("Download starten", self)
        self.queryButton.clicked.connect(self.startQuery)
        self.queryButton.setStyleSheet("font-weight: bold; padding: 8px;")
        buttonLayout.addWidget(self.queryButton)
        
        self.okButton = QPushButton("OK", self)
        self.okButton.clicked.connect(self.accept)
        buttonLayout.addWidget(self.okButton)
        
        self.cancelButton = QPushButton("Abbrechen", self)
        self.cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(self.cancelButton)
        
        layout.addLayout(buttonLayout)

        # Styling
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                padding: 5px 10px;
            }
        """)

        # Initialize visibility
        self.toggleAreaType(0)
        self.updateFilters()

    def setVisualizationTab(self, visualization_tab):
        """Set visualization tab reference for map interaction."""
        self.visualization_tab = visualization_tab

    def toggleDownloadMethod(self, index):
        """Toggle visibility based on download method."""
        is_osmnx = (self.methodComboBox.currentText() == "OSMnx (empfohlen)")
        
        # For Overpass API, only city name is supported
        if not is_osmnx:
            self.areaTypeComboBox.setCurrentIndex(0)
            self.areaTypeComboBox.setEnabled(False)
        else:
            self.areaTypeComboBox.setEnabled(True)

    def toggleAreaType(self, index):
        """Toggle visibility based on area selection type."""
        area_type = self.areaTypeComboBox.currentText()
        
        self.cityWidget.setVisible(area_type == "Stadt/Ortsname")
        self.csvWidget.setVisible(area_type == "Bereich um Gebäude aus CSV")
        self.polygonWidget.setVisible(area_type == "Polygon aus GeoJSON")
        self.mapDrawWidget.setVisible(area_type == "Polygon auf Karte zeichnen")

    def setAllHighwayCheckboxes(self, checked):
        """Set all highway checkboxes to checked or unchecked."""
        for checkbox in self.highwayCheckboxes.values():
            checkbox.setChecked(checked)

    def updateFilters(self):
        """Update OSMnx filter based on selected highway types."""
        selected_types = [key for key, checkbox in self.highwayCheckboxes.items() if checkbox.isChecked()]
        
        # Update OSMnx custom filter
        if selected_types:
            types_str = "|".join(selected_types)
            self.custom_filter = f'["highway"~"{types_str}"]'
        else:
            self.custom_filter = '["highway"]'

    def activateMapPolygonDrawing(self):
        """Activate polygon drawing mode on map."""
        if not self.visualization_tab:
            QMessageBox.warning(self, "Warnung", "Keine Kartenverbindung verfügbar.")
            return
        
        self.waiting_for_polygon = True
        self.drawPolygonButton.setEnabled(False)
        self.drawPolygonButton.setText("Warte auf Polygon...")
        self.drawPolygonButton.setStyleSheet("background-color: #ffc107; color: black; padding: 5px 10px;")
        self.polygonStatusLabel.setText("Status: Zeichnen Sie jetzt ein Polygon auf der Karte")
        self.polygonStatusLabel.setStyleSheet("color: #ffc107; font-weight: bold;")
        
        # Connect signal for when polygon is ready
        if hasattr(self.visualization_tab.view, 'geoJsonReceiver'):
            # Disconnect first to avoid duplicate connections
            try:
                self.visualization_tab.view.geoJsonReceiver.polygon_ready.disconnect(self.onPolygonReady)
            except:
                pass
            
            self.visualization_tab.view.geoJsonReceiver.polygon_ready.connect(self.onPolygonReady)
            print("DEBUG: polygon_ready signal connected to onPolygonReady")
            
            # Activate polygon capture mode via JavaScript
            js_code = "window.enablePolygonCaptureMode();"
            self.visualization_tab.view.web_view.page().runJavaScript(js_code)

    def onPolygonReady(self):
        """Called when polygon has been drawn on the map."""
        print("DEBUG: onPolygonReady() called in dialog!")
        
        if not self.waiting_for_polygon:
            print("DEBUG: Not waiting for polygon, ignoring signal")
            return
        
        # Reset button state
        self.waiting_for_polygon = False
        self.drawPolygonButton.setEnabled(True)
        self.drawPolygonButton.setText("Neues Polygon zeichnen")
        self.drawPolygonButton.setStyleSheet("padding: 5px 10px;")
        self.polygonStatusLabel.setText("Status: Polygon gezeichnet ✓ (kann bearbeitet werden)")
        self.polygonStatusLabel.setStyleSheet("color: #51cf66; font-weight: bold;")
        
        QMessageBox.information(self, "Polygon gezeichnet", 
            "Polygon wurde erfolgreich gezeichnet!\n\n" +
            "Sie können es jetzt auf der Karte bearbeiten (verschieben, Punkte hinzufügen/entfernen).\n" +
            "Klicken Sie auf 'Download starten', um das Polygon zu verwenden.")

    def getCapturedPolygonFromMap(self):
        """Get the captured polygon from the map via JavaScript.
        
        Returns
        -------
        str or None
            Path to temporary GeoJSON file with polygon, or None if no polygon.
        """
        result = {'geojson': None}
        
        def handle_result(geojson_str):
            if geojson_str:
                try:
                    result['geojson'] = json.loads(geojson_str)
                except Exception as e:
                    pass
        
        # Get polygon from JavaScript
        if hasattr(self.visualization_tab.view, 'web_view'):
            js_code = """
                (function() {
                    var polygon = window.getCapturedPolygon();
                    return polygon ? JSON.stringify(polygon) : null;
                })();
            """
            self.visualization_tab.view.web_view.page().runJavaScript(js_code, handle_result)
            
            # Wait a bit for the callback (simple blocking approach)
            from PyQt6.QtCore import QEventLoop, QTimer
            loop = QEventLoop()
            QTimer.singleShot(100, loop.quit)
            loop.exec()
            
            if result['geojson']:
                # Save to temp file
                temp_file = os.path.join(self.base_path, "_temp_download_polygon.geojson")
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(result['geojson'], f)
                return temp_file
        
        return None

    def clearCapturedPolygon(self):
        """Clear the captured polygon from the map."""
        if hasattr(self.visualization_tab.view, 'web_view'):
            js_code = "window.clearCapturedPolygon();"
            self.visualization_tab.view.web_view.page().runJavaScript(js_code)

    def createFileInput(self, default_path):
        """
        Create file input widget with browse button.

        Parameters
        ----------
        default_path : str
            Default file path.

        Returns
        -------
        tuple
            Line edit and button widgets.
        """
        lineEdit = QLineEdit(default_path)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def createFileInputLayout(self, lineEdit, button):
        """
        Create file input layout.

        Parameters
        ----------
        lineEdit : QLineEdit
            File path input widget.
        button : QPushButton
            Browse button widget.

        Returns
        -------
        QHBoxLayout
            Layout containing file input widgets.
        """
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def selectFile(self, lineEdit):
        """
        Open file dialog and update line edit.

        Parameters
        ----------
        lineEdit : QLineEdit
            Widget to update with selected file path.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", self.base_path, "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def addTagField(self, key="", value=""):
        """
        Add tag field to layout.

        Parameters
        ----------
        key : str, optional
            Tag key.
        value : str, optional
            Tag value.
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
        """Remove last tag field from layout."""
        if self.tags_to_download:
            keyLineEdit, valueLineEdit = self.tagsLayoutList.pop()
            self.tags_to_download.pop()
            self.tagsLayout.removeRow(keyLineEdit)
            print(self.tags_to_download)

    def loadAllStandardTags(self):
        """Load all standard tags into layout."""
        for tag in self.standard_tags:
            key = next(iter(tag))
            value = tag[key]
            self.addTagField(key, value)

    def loadSelectedStandardTag(self):
        """Load selected standard tag into layout."""
        selected_tag_index = self.standardTagsComboBox.currentIndex()
        tag = self.standard_tags[selected_tag_index]
        key = next(iter(tag))
        value = tag[key]
        self.addTagField(key, value)
    
    def startQuery(self):
        """Start OSM data query and download."""
        print("DEBUG: startQuery() called")
        filename = self.filenameLineEdit.text()
        
        if not filename:
            QMessageBox.warning(self, "Warnung", "Bitte geben Sie einen Dateinamen an.")
            return
        
        print(f"DEBUG: Output filename: {filename}")
        
        # Get all GUI values BEFORE starting thread (GUI access not allowed in threads!)
        area_type = self.areaTypeComboBox.currentText()
        self.last_area_type = area_type  # Store for cleanup in completion handler
        
        # Prepare parameters based on area type
        area_params = {
            'area_type': area_type,
            'city_name': self.cityLineEdit.text() if area_type == "Stadt/Ortsname" else None,
            'csv_file': self.csvLineEdit.text() if area_type == "Bereich um Gebäude aus CSV" else None,
            'buffer_dist': float(self.bufferLineEdit.text()) if area_type == "Bereich um Gebäude aus CSV" else None,
            'polygon_file': self.polygonLineEdit.text() if area_type == "Polygon aus GeoJSON" else None,
            'drawn_polygon_file': None
        }
        
        # Handle drawn polygon - get file path NOW before thread
        if area_type == "Polygon auf Karte zeichnen":
            print("DEBUG: Getting drawn polygon file before thread start...")
            try:
                drawn_polygon = self.getCapturedPolygonFromMap()
                print(f"DEBUG: getCapturedPolygonFromMap returned: {drawn_polygon}")
                if not drawn_polygon or not os.path.exists(drawn_polygon):
                    print(f"DEBUG: Polygon file invalid or doesn't exist: {drawn_polygon}")
                    QMessageBox.warning(self, "Warnung", 
                        "Bitte zeichnen Sie zuerst ein Polygon auf der Karte.\n\n" +
                        "Klicken Sie auf 'Polygon auf Karte zeichnen' und zeichnen Sie den gewünschten Bereich.")
                    return
                area_params['drawn_polygon_file'] = drawn_polygon
                print(f"DEBUG: Drawn polygon file set: {drawn_polygon}")
            except Exception as e:
                print(f"DEBUG: Exception in getCapturedPolygonFromMap: {e}")
                print(traceback.format_exc())
                QMessageBox.critical(self, "Fehler", f"Fehler beim Abrufen des Polygons:\n{str(e)}")
                return
        
        # Validate inputs before starting thread
        if area_type == "Stadt/Ortsname" and not area_params['city_name']:
            QMessageBox.warning(self, "Warnung", "Bitte geben Sie einen Stadtname an.")
            return
        elif area_type == "Bereich um Gebäude aus CSV":
            if not area_params['csv_file'] or not os.path.exists(area_params['csv_file']):
                QMessageBox.warning(self, "Warnung", "Bitte wählen Sie eine gültige CSV-Datei.")
                return
        elif area_type == "Polygon aus GeoJSON":
            if not area_params['polygon_file'] or not os.path.exists(area_params['polygon_file']):
                QMessageBox.warning(self, "Warnung", "Bitte wählen Sie eine gültige GeoJSON-Datei.")
                return
        
        # Update custom filter before passing to thread
        self.updateFilters()
        area_params['custom_filter'] = self.custom_filter
        
        # Disable download button during download
        self.queryButton.setEnabled(False)
        self.queryButton.setText("Download läuft...")
        
        # Create progress dialog
        self.progress_dialog = QProgressDialog("Download wird vorbereitet...", "Abbrechen", 0, 0, self)
        self.progress_dialog.setWindowTitle("OSM Straßendaten Download")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        self.progress_dialog.canceled.connect(self._onDownloadCanceled)
        
        try:
            print("DEBUG: Creating OSMnx download thread...")
            
            # Create and start download thread
            self.download_thread = OSMStreetDownloadThread(self._performOSMnxDownload, filename, area_params)
            
            self.download_thread.download_done.connect(self._onDownloadComplete)
            self.download_thread.download_error.connect(self._onDownloadError)
            print("DEBUG: Starting download thread...")
            self.download_thread.start()
            
            self.progress_dialog.setLabelText("Download läuft... Bitte warten.")
                
        except Exception as e:
            print(f"DEBUG: Exception in startQuery: {e}")
            print(traceback.format_exc())
            self.queryButton.setEnabled(True)
            self.queryButton.setText("Download starten")
            if self.progress_dialog:
                self.progress_dialog.close()
            QMessageBox.critical(self, "Fehler", f"Fehler beim Start des Downloads:\n{str(e)}\n\n{traceback.format_exc()}")

    def _onDownloadCanceled(self):
        """Handle download cancellation."""
        print("DEBUG: Download canceled by user")
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.terminate()
            self.download_thread.wait()
        self.queryButton.setEnabled(True)
        self.queryButton.setText("Download starten")

    def _onDownloadComplete(self, filepath):
        """Handle successful download completion."""
        print(f"DEBUG: Download complete! File: {filepath}")
        
        # Clear drawn polygon from map if it was used
        if hasattr(self, 'last_area_type') and self.last_area_type == "Polygon auf Karte zeichnen":
            print("DEBUG: Clearing drawn polygon from map")
            self.clearCapturedPolygon()
        
        if self.progress_dialog:
            self.progress_dialog.close()
        
        self.queryButton.setEnabled(True)
        self.queryButton.setText("Download starten")
        
        QMessageBox.information(self, "Erfolg", 
            f"Download abgeschlossen!\n\nDatei gespeichert: {filepath}")
        
        # Add to map
        print("DEBUG: Adding layer to map")
        self.parent_pres.add_geojson_layer([filepath])
        self.accept()

    def _onDownloadError(self, error_message):
        """Handle download error."""
        print(f"DEBUG: Download error: {error_message}")
        
        if self.progress_dialog:
            self.progress_dialog.close()
        
        self.queryButton.setEnabled(True)
        self.queryButton.setText("Download starten")
        QMessageBox.critical(self, "Fehler", error_message)

    def _performOSMnxDownload(self, filename, area_params):
        """Perform OSMnx download (runs in thread).
        
        Parameters
        ----------
        filename : str
            Output file path.
        area_params : dict
            Dictionary with area type and file paths (no GUI access!).
            
        Returns
        -------
        str
            Path to the saved file.
        """
        print(f"DEBUG: _performOSMnxDownload started with filename: {filename}")
        try:
            result = self.downloadWithOSMnx(filename, area_params)
            print(f"DEBUG: _performOSMnxDownload completed successfully: {result}")
            return result
        except Exception as e:
            print(f"DEBUG: _performOSMnxDownload exception: {e}")
            print(traceback.format_exc())
            raise

    def downloadWithOSMnx(self, filename, area_params):
        """Download street network using OSMnx.
        
        Parameters
        ----------
        filename : str
            Output file path.
        area_params : dict
            Dictionary with area type and file paths (no GUI access!).
        """
        print("DEBUG: downloadWithOSMnx started")
        import osmnx as ox
        import geopandas as gpd
        from shapely.geometry import box as shp_box
        from pyproj import Transformer
        
        area_type = area_params['area_type']
        custom_filter = area_params['custom_filter']
        print(f"DEBUG: Area type: {area_type}")
        print(f"DEBUG: Custom filter: {custom_filter}")
        
        # Get area/polygon based on selection
        if area_type == "Stadt/Ortsname":
            city_name = area_params['city_name']
            print(f"DEBUG: Downloading for city: {city_name}")
            
            print("DEBUG: Calling ox.graph_from_place...")
            # Download by place name
            G = ox.graph_from_place(city_name, network_type='all', custom_filter=custom_filter)
            print(f"DEBUG: Graph downloaded, nodes: {len(G.nodes)}, edges: {len(G.edges)}")
            
        elif area_type == "Bereich um Gebäude aus CSV":
            print("DEBUG: CSV mode selected")
            csv_file = area_params['csv_file']
            buffer_dist = area_params['buffer_dist']
            
            print(f"DEBUG: Reading CSV file: {csv_file}")
            print(f"DEBUG: Buffer distance: {buffer_dist}")
            
            # Read CSV and create buffer
            import pandas as pd
            df = pd.read_csv(csv_file, delimiter=';')
            print(f"DEBUG: CSV loaded, {len(df)} rows")
            
            if 'UTM_X' not in df.columns or 'UTM_Y' not in df.columns:
                QMessageBox.warning(self, "Warnung", "CSV muss 'UTM_X' und 'UTM_Y' Spalten enthalten.")
                return
            
            print("DEBUG: Creating GeoDataFrame from CSV...")
            # Create GeoDataFrame
            geometry = gpd.points_from_xy(df['UTM_X'], df['UTM_Y'])
            gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:25833')
            
            # Convert to WGS84 for OSMnx
            print("DEBUG: Converting to WGS84...")
            gdf_wgs84 = gdf.to_crs('EPSG:4326')
            
            # Create buffer around all points
            print("DEBUG: Creating buffer polygon...")
            combined = gdf_wgs84.unary_union
            
            # Buffer in degrees (approximate)
            buffer_deg = buffer_dist / 111000.0  # rough conversion
            polygon = combined.buffer(buffer_deg)
            
            # Download by polygon
            print("DEBUG: Calling ox.graph_from_polygon for CSV buffer...")
            G = ox.graph_from_polygon(polygon, network_type='all', custom_filter=custom_filter)
            print(f"DEBUG: Graph downloaded, nodes: {len(G.nodes)}, edges: {len(G.edges)}")
            
        elif area_type == "Polygon aus GeoJSON":
            print("DEBUG: GeoJSON polygon mode selected")
            polygon_file = area_params['polygon_file']
            
            print(f"DEBUG: Reading GeoJSON file: {polygon_file}")
            # Read polygon
            gdf_polygon = gpd.read_file(polygon_file)
            print(f"DEBUG: GeoJSON loaded, {len(gdf_polygon)} features")
            
            # Ensure WGS84
            if gdf_polygon.crs != 'EPSG:4326':
                print("DEBUG: Converting GeoJSON to WGS84...")
                gdf_polygon = gdf_polygon.to_crs('EPSG:4326')
            
            print("DEBUG: Creating union polygon...")
            polygon = gdf_polygon.unary_union
            
            # Download by polygon
            print("DEBUG: Calling ox.graph_from_polygon for GeoJSON...")
            G = ox.graph_from_polygon(polygon, network_type='all', custom_filter=custom_filter)
            print(f"DEBUG: Graph downloaded, nodes: {len(G.nodes)}, edges: {len(G.edges)}")
            
        elif area_type == "Polygon auf Karte zeichnen":
            print("DEBUG: Drawn polygon mode selected")
            # Get polygon file path from params (already retrieved in main thread)
            polygon_file = area_params['drawn_polygon_file']
            
            print(f"DEBUG: Reading drawn polygon from: {polygon_file}")
            # Read polygon from temp file
            gdf_polygon = gpd.read_file(polygon_file)
            print(f"DEBUG: Polygon loaded, {len(gdf_polygon)} features")
            
            if gdf_polygon.crs != 'EPSG:4326':
                print("DEBUG: Converting polygon to WGS84...")
                gdf_polygon = gdf_polygon.to_crs('EPSG:4326')
            
            print("DEBUG: Creating union polygon...")
            polygon = gdf_polygon.unary_union
            
            print("DEBUG: Calling ox.graph_from_polygon for drawn polygon...")
            G = ox.graph_from_polygon(polygon, network_type='all', custom_filter=custom_filter)
            print(f"DEBUG: Graph downloaded, nodes: {len(G.nodes)}, edges: {len(G.edges)}")
        
        print("DEBUG: Converting graph to GeoDataFrame...")
        # Convert to GeoDataFrame
        gdf_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
        print(f"DEBUG: GeoDataFrame created, {len(gdf_edges)} edges")
        
        print("DEBUG: Converting to EPSG:25833...")
        # Convert to EPSG:25833
        gdf_edges = gdf_edges.to_crs('EPSG:25833')
        
        print(f"DEBUG: Saving to file: {filename}")
        # Save to file
        gdf_edges.to_file(filename, driver='GeoJSON')
        print("DEBUG: File saved successfully")
        
        return filename


class OSMBuildingQueryDialog(QDialog):
    """
    Dialog for querying OSM building data with multiple area selection modes.
    """
    def __init__(self, base_path, config_manager, parent, parent_pres, visualization_tab=None):
        """
        Initialize OSM building query dialog.

        Parameters
        ----------
        base_path : str
            Base path for file operations.
        config_manager : ConfigManager
            Configuration manager instance.
        parent : QWidget
            Parent widget.
        parent_pres : object
            Parent presenter instance.
        visualization_tab : LeafletTab, optional
            Reference to visualization tab for polygon drawing.
        """
        super().__init__(parent)
        self.base_path = base_path
        self.config_manager = config_manager
        self.parent_pres = parent_pres
        self.visualization_tab = visualization_tab
        self.waiting_for_polygon = False
        self.download_thread = None
        self.progress_dialog = None
        
        # Set window flags to allow interaction with map while dialog is open
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        
        self.initUI()

    def initUI(self):
        """Initialize user interface components."""
        layout = QVBoxLayout(self)
        self.setWindowTitle("OSM Gebäudedaten herunterladen")

        # === Bereichsauswahl ===
        area_group = QGroupBox("Bereichsauswahl")
        area_layout = QVBoxLayout()
        
        area_layout.addWidget(QLabel("Bereichstyp:"))
        self.areaTypeComboBox = QComboBox(self)
        self.areaTypeComboBox.addItem("Bereich um Gebäude aus CSV")
        self.areaTypeComboBox.addItem("Polygon aus GeoJSON")
        self.areaTypeComboBox.addItem("Polygon auf Karte zeichnen")
        self.areaTypeComboBox.currentIndexChanged.connect(self.toggleAreaType)
        area_layout.addWidget(self.areaTypeComboBox)
        
        area_layout.addWidget(QLabel("Wählen Sie den Bereich aus, für den Sie Gebäudedaten herunterladen möchten."))
        
        # CSV buildings with buffer
        self.csvWidget = QWidget()
        csv_layout = QVBoxLayout(self.csvWidget)
        csv_layout.addWidget(QLabel("CSV-Datei mit Gebäuden (UTM_X, UTM_Y):"))
        csv_browse_layout = QHBoxLayout()
        self.csvLineEdit = QLineEdit(self)
        self.csvBrowseButton = QPushButton("Durchsuchen", self)
        self.csvBrowseButton.clicked.connect(lambda: self.browseFile(self.csvLineEdit, "CSV-Dateien (*.csv)"))
        csv_browse_layout.addWidget(self.csvLineEdit)
        csv_browse_layout.addWidget(self.csvBrowseButton)
        csv_layout.addLayout(csv_browse_layout)
        csv_layout.addWidget(QLabel("Es werden nur Gebäude an den exakten Koordinaten heruntergeladen."))
        area_layout.addWidget(self.csvWidget)
        
        # GeoJSON polygon
        self.polygonWidget = QWidget()
        polygon_layout = QVBoxLayout(self.polygonWidget)
        polygon_layout.addWidget(QLabel("GeoJSON-Datei mit Polygon:"))
        polygon_browse_layout = QHBoxLayout()
        self.polygonLineEdit = QLineEdit(self)
        self.polygonBrowseButton = QPushButton("Durchsuchen", self)
        self.polygonBrowseButton.clicked.connect(lambda: self.browseFile(self.polygonLineEdit, "GeoJSON-Dateien (*.geojson *.json)"))
        polygon_browse_layout.addWidget(self.polygonLineEdit)
        polygon_browse_layout.addWidget(self.polygonBrowseButton)
        polygon_layout.addLayout(polygon_browse_layout)
        area_layout.addWidget(self.polygonWidget)
        
        # Draw polygon on map
        self.drawPolygonWidget = QWidget()
        draw_polygon_layout = QVBoxLayout(self.drawPolygonWidget)
        draw_polygon_layout.addWidget(QLabel("Zeichnen Sie ein Polygon auf der Karte, um den Downloadbereich festzulegen."))
        self.drawPolygonButton = QPushButton("Neues Polygon zeichnen", self)
        self.drawPolygonButton.clicked.connect(self.activateMapPolygonDrawing)
        draw_polygon_layout.addWidget(self.drawPolygonButton)
        self.polygonStatusLabel = QLabel("")
        draw_polygon_layout.addWidget(self.polygonStatusLabel)
        area_layout.addWidget(self.drawPolygonWidget)
        
        area_group.setLayout(area_layout)
        layout.addWidget(area_group)
        
        # === Ausgabedatei ===
        output_group = QGroupBox("Ausgabedatei")
        output_layout = QVBoxLayout()
        output_layout.addWidget(QLabel("Speicherpfad für GeoJSON:"))
        output_browse_layout = QHBoxLayout()
        default_path = os.path.join(self.base_path, self.config_manager.get_relative_path('OSM_buldings_path'))
        self.filenameLineEdit = QLineEdit(default_path, self)
        self.filenameBrowseButton = QPushButton("Durchsuchen", self)
        self.filenameBrowseButton.clicked.connect(lambda: self.browseSaveFile(self.filenameLineEdit))
        output_browse_layout.addWidget(self.filenameLineEdit)
        output_browse_layout.addWidget(self.filenameBrowseButton)
        output_layout.addLayout(output_browse_layout)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # === Action Buttons ===
        button_layout = QHBoxLayout()
        self.downloadButton = QPushButton("Download starten", self)
        self.downloadButton.clicked.connect(self.startQuery)
        button_layout.addWidget(self.downloadButton)
        
        self.cancelButton = QPushButton("Abbrechen", self)
        self.cancelButton.clicked.connect(self.reject)
        button_layout.addWidget(self.cancelButton)
        layout.addLayout(button_layout)
        
        # Initialize visibility
        self.toggleAreaType()
        
        # Connect to polygon_ready signal if visualization_tab available
        if self.visualization_tab and hasattr(self.visualization_tab, 'view') and hasattr(self.visualization_tab.view, 'geoJsonReceiver'):
            self.visualization_tab.view.geoJsonReceiver.polygon_ready.connect(self.onPolygonReady)

    def toggleAreaType(self):
        """Show/hide widgets based on selected area type."""
        area_type = self.areaTypeComboBox.currentText()
        
        self.csvWidget.setVisible(area_type == "Bereich um Gebäude aus CSV")
        self.polygonWidget.setVisible(area_type == "Polygon aus GeoJSON")
        self.drawPolygonWidget.setVisible(area_type == "Polygon auf Karte zeichnen")

    def browseFile(self, line_edit, file_filter):
        """
        Open file dialog for selecting input file.
        
        Parameters
        ----------
        line_edit : QLineEdit
            Line edit to update with selected path.
        file_filter : str
            File filter string for dialog.
        """
        filename, _ = QFileDialog.getOpenFileName(
            self, "Datei auswählen", self.base_path, file_filter
        )
        if filename:
            line_edit.setText(filename)

    def browseSaveFile(self, line_edit):
        """
        Open file dialog for selecting output file.
        
        Parameters
        ----------
        line_edit : QLineEdit
            Line edit to update with selected path.
        """
        filename, _ = QFileDialog.getSaveFileName(
            self, "Speicherort wählen", line_edit.text(), "GeoJSON-Dateien (*.geojson)"
        )
        if filename:
            line_edit.setText(filename)

    def activateMapPolygonDrawing(self):
        """Activate polygon drawing mode on the map."""
        if not self.visualization_tab:
            QMessageBox.warning(self, "Fehler", "Keine Kartenverbindung verfügbar.")
            return
        
        self.waiting_for_polygon = True
        self.drawPolygonButton.setText("Warte auf Polygon...")
        self.drawPolygonButton.setStyleSheet("background-color: #ffeb3b;")
        self.polygonStatusLabel.setText("Zeichnen Sie jetzt ein Polygon auf der Karte...")
        self.polygonStatusLabel.setStyleSheet("color: #ff9800;")
        
        # Connect signal
        try:
            self.visualization_tab.view.geoJsonReceiver.polygon_ready.disconnect(self.onPolygonReady)
        except:
            pass
        self.visualization_tab.view.geoJsonReceiver.polygon_ready.connect(self.onPolygonReady)
        
        # Enable drawing mode via JavaScript
        if hasattr(self.visualization_tab.view, 'web_view'):
            self.visualization_tab.view.web_view.page().runJavaScript("window.enablePolygonCaptureMode();")

    def onPolygonReady(self):
        """Handle polygon ready signal from map."""
        if not self.waiting_for_polygon:
            return
        
        self.waiting_for_polygon = False
        self.drawPolygonButton.setText("Neues Polygon zeichnen")
        self.drawPolygonButton.setStyleSheet("")
        self.polygonStatusLabel.setText("✓ Polygon gezeichnet (kann bearbeitet werden)")
        self.polygonStatusLabel.setStyleSheet("color: #4caf50;")
        
        QMessageBox.information(self, "Polygon gezeichnet",
            "Das Polygon wurde erfolgreich gezeichnet.\n\n" +
            "Sie können es noch bearbeiten (Punkte verschieben, hinzufügen oder löschen).\n\n" +
            "Klicken Sie auf 'Download starten', um das Polygon zu verwenden.")

    def getCapturedPolygonFromMap(self):
        """Get the captured polygon from the map via JavaScript.
        
        Returns
        -------
        str or None
            Path to temporary GeoJSON file with polygon, or None if no polygon.
        """
        print("DEBUG: getCapturedPolygonFromMap called")
        result = {'geojson': None}
        
        def handle_result(geojson_str):
            print(f"DEBUG: JavaScript callback received: {geojson_str[:100] if geojson_str else None}...")
            if geojson_str:
                try:
                    result['geojson'] = json.loads(geojson_str)
                    print(f"DEBUG: Successfully parsed GeoJSON")
                except Exception as e:
                    print(f"DEBUG: Failed to parse GeoJSON: {e}")
        
        if hasattr(self.visualization_tab.view, 'web_view'):
            print("DEBUG: Executing JavaScript to get polygon...")
            js_code = """
                (function() {
                    var polygon = window.getCapturedPolygon();
                    return polygon ? JSON.stringify(polygon) : null;
                })();
            """
            self.visualization_tab.view.web_view.page().runJavaScript(js_code, handle_result)
            
            print("DEBUG: Waiting for JavaScript callback...")
            from PyQt6.QtCore import QEventLoop, QTimer
            loop = QEventLoop()
            QTimer.singleShot(100, loop.quit)
            loop.exec()
            
            print(f"DEBUG: Event loop finished, result: {result}")
            if result['geojson']:
                print("DEBUG: Writing GeoJSON to temp file...")
                temp_file = os.path.join(self.base_path, "_temp_building_polygon.geojson")
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(result['geojson'], f)
                print(f"DEBUG: Temp file written: {temp_file}")
                return temp_file
            else:
                print("DEBUG: No GeoJSON data received")
        else:
            print("DEBUG: web_view not available")
        
        print("DEBUG: Returning None")
        return None

    def clearCapturedPolygon(self):
        """Clear the captured polygon from the map."""
        if hasattr(self.visualization_tab.view, 'web_view'):
            self.visualization_tab.view.web_view.page().runJavaScript("window.clearCapturedPolygon();")

    def startQuery(self):
        """Start OSM building data query and download."""
        print("DEBUG: Building startQuery called")
        filename = self.filenameLineEdit.text()
        print(f"DEBUG: Building filename: {filename}")
        
        if not filename:
            QMessageBox.warning(self, "Warnung", "Bitte geben Sie einen Dateinamen an.")
            return
        
        # Get all GUI values BEFORE starting thread (GUI access not allowed in threads!)
        area_type = self.areaTypeComboBox.currentText()
        self.last_area_type = area_type  # Store for cleanup in completion handler
        print(f"DEBUG: Area type: {area_type}")
        
        # Prepare parameters based on area type
        area_params = {
            'area_type': area_type,
            'csv_file': self.csvLineEdit.text() if area_type == "Bereich um Gebäude aus CSV" else None,
            'polygon_file': self.polygonLineEdit.text() if area_type == "Polygon aus GeoJSON" else None,
            'drawn_polygon_file': None
        }
        
        # Handle drawn polygon specially - get file path NOW before thread
        if area_type == "Polygon auf Karte zeichnen":
            print("DEBUG: Getting drawn polygon file before thread start...")
            try:
                drawn_polygon = self.getCapturedPolygonFromMap()
                print(f"DEBUG: getCapturedPolygonFromMap returned: {drawn_polygon}")
                if not drawn_polygon or not os.path.exists(drawn_polygon):
                    print(f"DEBUG: Polygon file invalid or doesn't exist: {drawn_polygon}")
                    QMessageBox.warning(self, "Warnung", 
                        "Bitte zeichnen Sie zuerst ein Polygon auf der Karte.\n\n" +
                        "Klicken Sie auf 'Neues Polygon zeichnen' und zeichnen Sie den gewünschten Bereich.")
                    return
                area_params['drawn_polygon_file'] = drawn_polygon
                print(f"DEBUG: Drawn polygon file set: {drawn_polygon}")
            except Exception as e:
                print(f"DEBUG: Exception in getCapturedPolygonFromMap: {e}")
                print(traceback.format_exc())
                QMessageBox.critical(self, "Fehler", f"Fehler beim Abrufen des Polygons:\n{str(e)}")
                return
        
        # Validate other inputs before starting thread
        if area_type == "Bereich um Gebäude aus CSV":
            if not area_params['csv_file'] or not os.path.exists(area_params['csv_file']):
                QMessageBox.warning(self, "Warnung", "Bitte wählen Sie eine gültige CSV-Datei.")
                return
        elif area_type == "Polygon aus GeoJSON":
            if not area_params['polygon_file'] or not os.path.exists(area_params['polygon_file']):
                QMessageBox.warning(self, "Warnung", "Bitte wählen Sie eine gültige GeoJSON-Datei.")
                return
        
        # Create progress dialog
        self.progress_dialog = QProgressDialog("Download wird vorbereitet...", "Abbrechen", 0, 0, self)
        self.progress_dialog.setWindowTitle("OSM Building Download")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.canceled.connect(self._onDownloadCanceled)
        self.progress_dialog.show()
        
        # Disable download button during download
        self.downloadButton.setEnabled(False)
        self.downloadButton.setText("Download läuft...")
        
        try:
            print("DEBUG: Creating building download thread...")
            # Create and start download thread - pass area_params instead of reading GUI in thread
            self.download_thread = OSMBuildingDownloadThread(self._performBuildingDownload, filename, area_params)
            self.download_thread.download_done.connect(self._onDownloadComplete)
            self.download_thread.download_error.connect(self._onDownloadError)
            
            print("DEBUG: Starting building download thread...")
            self.progress_dialog.setLabelText("Download läuft...")
            self.download_thread.start()
            print("DEBUG: Building download thread started")
        except Exception as e:
            print(f"DEBUG: Exception in startQuery: {e}")
            print(traceback.format_exc())
            if self.progress_dialog:
                self.progress_dialog.close()
            self.downloadButton.setEnabled(True)
            self.downloadButton.setText("Download starten")
            QMessageBox.critical(self, "Fehler", f"Fehler beim Start des Downloads:\n{str(e)}\n\n{traceback.format_exc()}")

    def _onDownloadCanceled(self):
        """Handle progress dialog cancellation."""
        print("DEBUG: Building download canceled by user")
        if hasattr(self, 'download_thread') and self.download_thread.isRunning():
            self.download_thread.terminate()
            self.download_thread.wait()
        self.downloadButton.setEnabled(True)
        self.downloadButton.setText("Download starten")

    def _onDownloadComplete(self, filepath, building_count):
        """Handle successful download completion."""
        print(f"DEBUG: Building download complete: {filepath}, {building_count} buildings")
        
        # Clear drawn polygon from map if it was used
        if hasattr(self, 'last_area_type') and self.last_area_type == "Polygon auf Karte zeichnen":
            print("DEBUG: Clearing drawn polygon from map")
            self.clearCapturedPolygon()
        
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        self.downloadButton.setEnabled(True)
        self.downloadButton.setText("Download starten")
        
        QMessageBox.information(self, "Erfolg", 
            f"Download abgeschlossen!\n\n" +
            f"{building_count} Gebäude gespeichert in:\n{filepath}")
        
        # Add to map
        self.parent_pres.add_geojson_layer([filepath])
        self.accept()

    def _onDownloadError(self, error_message):
        """Handle download error."""
        print(f"DEBUG: Building download error: {error_message}")
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        self.downloadButton.setEnabled(True)
        self.downloadButton.setText("Download starten")
        QMessageBox.critical(self, "Fehler", error_message)

    def _performBuildingDownload(self, filename, area_params):
        """Perform building download (runs in thread).
        
        Parameters
        ----------
        filename : str
            Output file path.
        area_params : dict
            Dictionary with area type and file paths (no GUI access in thread!)
            
        Returns
        -------
        tuple
            (filepath, building_count)
        """
        print("DEBUG: _performBuildingDownload called")
        try:
            result = self.downloadBuildings(filename, area_params)
            print(f"DEBUG: _performBuildingDownload success: {result}")
            return result
        except Exception as e:
            print(f"DEBUG: _performBuildingDownload exception: {e}")
            print(traceback.format_exc())
            raise

    def downloadBuildings(self, filename, area_params):
        """Download building data using Overpass API.
        
        Parameters
        ----------
        filename : str
            Output file path.
        area_params : dict
            Dictionary with area type and file paths.
        """
        print("DEBUG: downloadBuildings called")
        import geopandas as gpd
        from shapely.geometry import box as shp_box
        from pyproj import Transformer
        
        area_type = area_params['area_type']
        print(f"DEBUG: Building area type: {area_type}")
        
        # Get polygon based on selection
        polygon = None
        
        if area_type == "Bereich um Gebäude aus CSV":
            print("DEBUG: Building CSV mode")
            csv_file = area_params['csv_file']
            
            print(f"DEBUG: Reading building CSV: {csv_file}")
            # Read CSV with building coordinates
            df = pd.read_csv(csv_file, delimiter=';')
            print(f"DEBUG: CSV loaded, {len(df)} buildings")
            
            if 'UTM_X' not in df.columns or 'UTM_Y' not in df.columns:
                QMessageBox.warning(self, "Warnung", "CSV muss 'UTM_X' und 'UTM_Y' Spalten enthalten.")
                return
            
            print("DEBUG: Creating building GeoDataFrame...")
            # Create GeoDataFrame with building points
            geometry = gpd.points_from_xy(df['UTM_X'], df['UTM_Y'])
            gdf_buildings = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:25833')
            
            # Convert to WGS84
            print("DEBUG: Converting to WGS84...")
            gdf_wgs84 = gdf_buildings.to_crs('EPSG:4326')
            
            # Create small buffer around points to capture buildings (5m radius)
            # This accounts for coordinate precision and building size
            print("DEBUG: Creating buffer polygon...")
            buffer_deg = 5.0 / 111000.0  # ~5 meters
            polygon = gdf_wgs84.unary_union.buffer(buffer_deg)
            
        elif area_type == "Polygon aus GeoJSON":
            print("DEBUG: Building GeoJSON mode")
            polygon_file = area_params['polygon_file']
            
            print(f"DEBUG: Reading building polygon: {polygon_file}")
            # Read polygon
            gdf_polygon = gpd.read_file(polygon_file)
            print(f"DEBUG: Polygon loaded, {len(gdf_polygon)} features")
            
            # Ensure WGS84
            if gdf_polygon.crs != 'EPSG:4326':
                print("DEBUG: Converting polygon to WGS84...")
                gdf_polygon = gdf_polygon.to_crs('EPSG:4326')
            
            polygon = gdf_polygon.unary_union
            
        elif area_type == "Polygon auf Karte zeichnen":
            print("DEBUG: Building drawn polygon mode")
            # Get polygon file path from params (already retrieved in main thread)
            polygon_file = area_params['drawn_polygon_file']
            
            print(f"DEBUG: Reading drawn polygon: {polygon_file}")
            # Read polygon from temp file
            gdf_polygon = gpd.read_file(polygon_file)
            print(f"DEBUG: Polygon loaded, {len(gdf_polygon)} features")
            
            if gdf_polygon.crs != 'EPSG:4326':
                print("DEBUG: Converting to WGS84...")
                gdf_polygon = gdf_polygon.to_crs('EPSG:4326')
            
            polygon = gdf_polygon.unary_union
        
        print("DEBUG: Getting polygon bounds...")
        # Download buildings using Overpass API
        bounds = polygon.bounds  # (minx, miny, maxx, maxy)
        print(f"DEBUG: Bounds: {bounds}")
        
        # Build Overpass query for buildings within polygon
        print("DEBUG: Building Overpass query...")
        query = f"""
        [out:json][timeout:180];
        (
          way["building"]({bounds[1]},{bounds[0]},{bounds[3]},{bounds[2]});
          relation["building"]({bounds[1]},{bounds[0]},{bounds[3]},{bounds[2]});
        );
        out body;
        >;
        out skel qt;
        """
        
        print("DEBUG: Calling Overpass API...")
        # Download data
        geojson_data = download_data(query, element_type="building")
        print(f"DEBUG: Overpass API returned data")
        
        print("DEBUG: Converting to GeoDataFrame...")
        # Convert to GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(geojson_data['features'], crs='EPSG:4326')
        print(f"DEBUG: GeoDataFrame created, {len(gdf)} buildings")
        
        print("DEBUG: Filtering buildings within polygon...")
        # Filter to only buildings within the actual polygon (not just bounding box)
        gdf_filtered = gdf[gdf.geometry.intersects(polygon)]
        print(f"DEBUG: Filtered to {len(gdf_filtered)} buildings")
        
        print(f"DEBUG: Saving to file: {filename}")
        # Save to file
        gdf_filtered.to_file(filename, driver='GeoJSON')
        print("DEBUG: File saved successfully")
        
        print(f"DEBUG: downloadBuildings returning: {filename}, {len(gdf_filtered)} buildings")
        return (filename, len(gdf_filtered))
