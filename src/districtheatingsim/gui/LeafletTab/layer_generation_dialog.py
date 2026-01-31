"""
Layer Generation Dialog Module
===============================

This module provides dialog interfaces for heat network layer generation,
including OSM data handling and building coordinate management.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import os
import pandas as pd

from PyQt6.QtWidgets import QVBoxLayout, QLineEdit, QDialog, QComboBox, QPushButton, \
    QFormLayout, QHBoxLayout, QFileDialog, QMessageBox, QLabel, QWidget, \
    QTableWidget, QTableWidgetItem, QGroupBox, QCheckBox, QProgressDialog
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QClipboard

from pyproj import Transformer

from districtheatingsim.geocoding.geocoding import get_coordinates
   
class LayerGenerationDialog(QDialog):
    """
    Dialog for generating layers for heat network visualization.
    """
    accepted_inputs = pyqtSignal(dict)
    request_map_coordinate = pyqtSignal()

    def __init__(self, base_path, config_manager, parent=None):
        """
        Initialize layer generation dialog.

        :param base_path: Base path for file operations
        :type base_path: str
        :param config_manager: Configuration manager instance
        :type config_manager: ConfigManager
        :param parent: Parent widget
        :type parent: QWidget or None
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
        """
        Initialize user interface components.
        
        Creates the complete dialog layout including data input section,
        coordinate management, and OSMnx advanced settings.
        """
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

        :param visualization_tab: VisualizationTab instance
        :type visualization_tab: QWidget
        """
        self.visualization_tab = visualization_tab

    def toggleLocationInputMode(self, index):
        """
        Toggle input fields based on location mode.

        :param index: Selected mode index
        :type index: int
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

        :param index: Selected generation mode index
        :type index: int
        """
        # Street layer only needed for non-OSMnx modes
        is_osmnx = (self.generationModeComboBox.currentText() == "OSMnx")
        self.streetLayerLabel.setVisible(not is_osmnx)
        self.fileInput.setVisible(not is_osmnx)
        self.fileButton.setVisible(not is_osmnx)
        
        # Show OSMnx advanced settings only for OSMnx mode
        self.osmnxAdvancedWidget.setVisible(is_osmnx)

    def toggleOSMnxAdvancedSettings(self):
        """
        Toggle visibility of OSMnx advanced settings.
        
        Switches between expanded and collapsed state of the advanced
        settings panel and updates the toggle button text accordingly.
        """
        is_visible = self.osmnxAdvancedContent.isVisible()
        self.osmnxAdvancedContent.setVisible(not is_visible)
        
        # Update button text with arrow
        if is_visible:
            self.osmnxAdvancedToggle.setText("▶ Erweiterte OSMnx-Einstellungen")
        else:
            self.osmnxAdvancedToggle.setText("▼ Erweiterte OSMnx-Einstellungen")
    
    def setAllHighwayCheckboxes(self, checked):
        """
        Set all highway checkboxes to checked or unchecked.
        
        :param checked: True to check all, False to uncheck all
        :type checked: bool
        """
        for checkbox in self.highwayCheckboxes.values():
            checkbox.setChecked(checked)
    
    def updateFilters(self):
        """
        Update custom filter string based on selected highway types.
        
        Builds an OSMnx-compatible filter string from the selected
        highway type checkboxes for network generation.
        """
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

        :param lineEdit: File path input widget
        :type lineEdit: QLineEdit
        :param button: Browse button widget
        :type button: QPushButton
        :return: Layout containing file input widgets
        :rtype: QHBoxLayout
        """
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def createFileInput(self, default_path):
        """
        Create file input widget with browse button.

        :param default_path: Default file path
        :type default_path: str
        :return: Line edit and button widgets
        :rtype: tuple
        """
        lineEdit = QLineEdit(default_path)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.openFileDialog(lineEdit))
        return lineEdit, button

    def openFileDialog(self, lineEdit):
        """
        Open file dialog and update line edit.

        :param lineEdit: Widget to update with selected file path
        :type lineEdit: QLineEdit
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", f"{self.base_path}", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def addCoordFromInput(self):
        """
        Add coordinates from input field to table.
        
        Parses coordinate input, transforms to EPSG:25833 if needed,
        and adds the coordinate pair to the table.
        """
        coords = self.coordInput.text().split(',')
        if len(coords) == 2:
            x, y = map(str.strip, coords)
            source_crs = self.coordSystemComboBox.currentText()
            x_transformed, y_transformed = self.transform_coordinates(float(x), float(y), source_crs)
            self.insertRowInTable(x_transformed, y_transformed)

    def geocodeAndAdd(self):
        """
        Geocode address and add coordinates to table.
        
        Converts the address input to coordinates using geocoding
        service and adds result to coordinate table.
        """
        address = self.addressInput.text()
        if address:
            x, y = get_coordinates(address)
            if x and y:
                self.insertRowInTable(str(x), str(y))

    def importCoordsFromCSV(self):
        """
        Import coordinates from CSV file.
        
        Opens file dialog to select CSV with UTM_X and UTM_Y columns
        and imports all coordinates to the table.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "CSV-Datei auswählen", f"{self.base_path}", "CSV Files (*.csv)")
        if filename:
            data = pd.read_csv(filename, delimiter=';', usecols=['UTM_X', 'UTM_Y'])
            for _, row in data.iterrows():
                self.insertRowInTable(str(row['UTM_X']), str(row['UTM_Y']))

    def transform_coordinates(self, x, y, source_crs):
        """
        Transform coordinates to EPSG:25833.

        :param x: X-coordinate
        :type x: float
        :param y: Y-coordinate
        :type y: float
        :param source_crs: Source coordinate system
        :type source_crs: str
        :return: Transformed coordinates
        :rtype: tuple
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

        :param x: X-coordinate
        :type x: str
        :param y: Y-coordinate
        :type y: str
        """
        row_count = self.coordTable.rowCount()
        self.coordTable.insertRow(row_count)
        self.coordTable.setItem(row_count, 0, QTableWidgetItem(str(x)))
        self.coordTable.setItem(row_count, 1, QTableWidgetItem(str(y)))

    def deleteSelectedRow(self):
        """
        Delete selected row from coordinates table.
        
        Removes the currently selected coordinate row from the table.
        """
        selected_row = self.coordTable.currentRow()
        if selected_row >= 0:
            self.coordTable.removeRow(selected_row)

    def clearAllCoordinates(self):
        """
        Clear all coordinates from table.
        
        Shows confirmation dialog and removes all coordinate rows
        from the table if confirmed.
        """
        reply = QMessageBox.question(self, 'Bestätigung', 
                                    'Möchten Sie wirklich alle Koordinaten löschen?',
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.coordTable.setRowCount(0)

    def copyCoordinates(self):
        """
        Copy all coordinates to clipboard.
        
        Exports all coordinate pairs from the table to the system
        clipboard in comma-separated format.
        """
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
        """
        Paste coordinates from clipboard.
        
        Parses coordinate data from clipboard and adds valid coordinate
        pairs to the table.
        """
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
        """
        Save coordinates to CSV file.
        
        Prompts user for save format (with or without addresses) and
        exports coordinates to a CSV file.
        """
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
        """
        Simple reverse geocoding (returns formatted coordinates if geocoding fails).
        
        :param x: UTM X coordinate
        :type x: float
        :param y: UTM Y coordinate
        :type y: float
        :return: Address string or formatted coordinates
        :rtype: str
        """
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
        """
        Activate map coordinate picker mode.
        
        Enables interactive coordinate selection from the map view
        and updates button state to indicate waiting status.
        """
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
        """
        Receive coordinates from map click.
        
        :param lat: Latitude (WGS84)
        :type lat: float
        :param lon: Longitude (WGS84)
        :type lon: float
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

        :return: Dictionary containing input values
        :rtype: dict
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
        """
        Handle accept event.
        
        Collects all input data and emits the accepted_inputs signal
        before closing the dialog.
        """
        inputs = self.getInputs()
        self.accepted_inputs.emit(inputs)
        self.accept()