"""
Leaflet Dialogs Module
=====================

Dialog widgets for network generation, OSM data download, and building queries.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-10
"""

import os

import geopandas as gpd
import pandas as pd
from math import radians, sin, cos, sqrt, atan2
from shapely.geometry import box, Point
from shapely.ops import transform
import pyproj

from PyQt6.QtWidgets import QVBoxLayout, QLineEdit, QDialog, QComboBox, QPushButton, \
    QFormLayout, QHBoxLayout, QFileDialog, QMessageBox, QLabel, QWidget, \
    QTableWidget, QTableWidgetItem, QGroupBox, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QClipboard

from pyproj import Transformer

from districtheatingsim.gui.LeafletTab.net_generation_threads import GeocodingThread
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
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowTitleHint | Qt.WindowType.CustomizeWindowHint)
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
            checkbox.stateChanged.connect(self.updateCustomFilter)
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
    
    def updateCustomFilter(self):
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
        self.updateCustomFilter()

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
    Dialog for downloading OSM data.
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
        """Initialize user interface components."""
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
        self.filenameLineEdit, fileButton = self.createFileInput(os.path.abspath(os.path.join(self.base_path, self.config_manager.get_relative_path('OSM_streets_path'))))
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
        self.filename = self.filenameLineEdit.text()
        city_name = self.cityLineEdit.text()

        query = build_query(city_name, self.tags_to_download, element_type="way")
        geojson_data = download_data(query, element_type="way")
        save_to_file(geojson_data, self.filename)
        gdf = gpd.read_file(self.filename, driver='GeoJSON').to_crs(epsg=25833)
        gdf.to_file(self.filename, driver='GeoJSON')

        QMessageBox.information(self, "Erfolg", f"Abfrageergebnisse gespeichert in {self.filename}")
            
        self.parent_pres.add_geojson_layer([self.filename])

class OSMBuildingQueryDialog(QDialog):
    """
    Dialog for querying OSM building data.
    """
    def __init__(self, base_path, config_manager, parent, parent_pres):
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
        """
        super().__init__(parent)
        self.base_path = base_path
        self.config_manager = config_manager
        self.parent_pres = parent_pres
        self.initUI()

    def initUI(self):
        """Initialize user interface components."""
        layout = QVBoxLayout(self)
        self.setWindowTitle("OSM Gebäudeabfrage")

        self.cityLineEdit = QLineEdit(self)
        layout.addWidget(QLabel("Stadt, deren OSM-Gebäudedaten heruntergeladen werden sollen:"))
        layout.addWidget(self.cityLineEdit)

        self.filenameLineEdit = QLineEdit(os.path.join(self.base_path, self.config_manager.get_relative_path('OSM_buldings_path')), self)
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

    def showSelectedFilter(self):
        """Show selected filter options based on filter type."""
        selected_filter = self.filterComboBox.currentText()
        self.coordWidget.setVisible(selected_filter == "Filtern mit Koordinatenbereich")
        self.coordRadiusWidget.setVisible(selected_filter == "Filtern mit zentralen Koordinaten und Radius als Abstand")
        self.csvWidget.setVisible(selected_filter == "Filtern mit Adressen aus CSV")
        self.geoJSONWidget.setVisible(selected_filter == "Filtern mit Polygon-geoJSON")

    def haversine(self, lat1, lon1, lat2, lon2):
        """
        Calculate great-circle distance between two points.

        Parameters
        ----------
        lat1 : float
            Latitude of first point.
        lon1 : float
            Longitude of first point.
        lat2 : float
            Latitude of second point.
        lon2 : float
            Longitude of second point.

        Returns
        -------
        float
            Distance in meters.
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
        """Start OSM building data query and download."""
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
        self.parent_pres.add_geojson_layer([filename])

    def prepare_gdf(self, geojson_data):
        """
        Prepare GeoDataFrame from GeoJSON data.

        Parameters
        ----------
        geojson_data : dict
            GeoJSON data.

        Returns
        -------
        GeoDataFrame
            Prepared GeoDataFrame.
        """
        gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
        gdf.crs = "EPSG:4326"
        return gdf.to_crs(epsg=25833)

    def filter_with_bbox(self, gdf, filename):
        """
        Filter GeoDataFrame using bounding box.

        Parameters
        ----------
        gdf : GeoDataFrame
            GeoDataFrame to filter.
        filename : str
            Output filename.
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
        Filter GeoDataFrame using central coordinates and radius.

        Parameters
        ----------
        gdf : GeoDataFrame
            GeoDataFrame to filter.
        filename : str
            Output filename.
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
        Filter GeoDataFrame using addresses from CSV file.

        Parameters
        ----------
        gdf : GeoDataFrame
            GeoDataFrame to filter.
        filename : str
            Output filename.
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
        Filter GeoDataFrame using polygon from GeoJSON file.

        Parameters
        ----------
        gdf : GeoDataFrame
            GeoDataFrame to filter.
        filename : str
            Output filename.
        """
        geoJSON_file = self.geoJSONLineEdit.text()
        if geoJSON_file:
            polygon_gdf = gpd.read_file(geoJSON_file)
            polygon = polygon_gdf.geometry.iloc[0]
            filtered_gdf = gdf[gdf.geometry.within(polygon)]
            filtered_gdf.to_file(filename, driver='GeoJSON')