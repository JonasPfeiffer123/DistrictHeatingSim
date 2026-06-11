"""
OSM Dialogs Module
==================

This module provides dialog interfaces for OSM data download and building
queries through interactive user interfaces.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import os
import traceback

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from districtheatingsim.gui.LeafletTab.net_generation_threads import OSMBuildingDownloadThread, OSMStreetDownloadThread
from districtheatingsim.gui.LeafletTab.osm_dialogs_base import OSMDownloadDialogBase
from districtheatingsim.osm.area_selection import build_highway_filter, resolve_area_polygon
from districtheatingsim.osm.import_osm_data_geojson import download_data


class DownloadOSMDataDialog(OSMDownloadDialogBase):
    """
    Dialog for downloading OSM street data with OSMnx.
    """
    _temp_polygon_filename = "_temp_download_polygon.geojson"

    def __init__(self, base_path, config_manager, parent, parent_pres, project_crs: str = "EPSG:25833"):
        """
        Initialize OSM data download dialog.

        Sets up the dialog with configuration for downloading OpenStreetMap
        street data using different methods and area selection types.

        :param base_path: Base path for file operations
        :type base_path: str
        :param config_manager: Configuration manager instance
        :type config_manager: ConfigManager
        :param parent: Parent widget
        :type parent: QWidget
        :param parent_pres: Parent presenter instance
        :type parent_pres: object
        :param project_crs: Projected CRS for downloaded data
        :type project_crs: str
        """
        super().__init__(base_path, config_manager, parent, parent_pres, project_crs=project_crs)
        self.custom_filter = '["highway"~"primary|secondary|tertiary|residential|living_street|service"]'
        self.initUI()

    def initUI(self):
        """
        Initialize user interface components.
        
        Creates and arranges all UI elements including area selection,
        method selection, filter options, and download controls.
        """
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
        self._download_button = self.queryButton  # used by base cancel/error handlers
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

    def toggleDownloadMethod(self, index):
        """
        Toggle visibility based on download method.
        
        Enables or disables area selection options depending on whether
        OSMnx or Overpass API is selected.
        
        :param index: Index of selected method
        :type index: int
        """
        is_osmnx = (self.methodComboBox.currentText() == "OSMnx (empfohlen)")
        
        # For Overpass API, only city name is supported
        if not is_osmnx:
            self.areaTypeComboBox.setCurrentIndex(0)
            self.areaTypeComboBox.setEnabled(False)
        else:
            self.areaTypeComboBox.setEnabled(True)

    def toggleAreaType(self, index):
        """
        Toggle visibility based on area selection type.
        
        Shows the appropriate input widgets based on the selected area
        type (city name, CSV, GeoJSON, or map drawing).
        
        :param index: Index of selected area type
        :type index: int
        """
        area_type = self.areaTypeComboBox.currentText()
        
        self.cityWidget.setVisible(area_type == "Stadt/Ortsname")
        self.csvWidget.setVisible(area_type == "Bereich um Gebäude aus CSV")
        self.polygonWidget.setVisible(area_type == "Polygon aus GeoJSON")
        self.mapDrawWidget.setVisible(area_type == "Polygon auf Karte zeichnen")

    def setAllHighwayCheckboxes(self, checked):
        """
        Set all highway checkboxes to checked or unchecked.
        
        Applies the same checked state to all highway type filters.
        
        :param checked: Target checked state
        :type checked: bool
        """
        for checkbox in self.highwayCheckboxes.values():
            checkbox.setChecked(checked)

    def updateFilters(self):
        """
        Update OSMnx filter based on selected highway types.
        
        Builds a custom OSMnx filter string from the checked highway
        type checkboxes for network data download.
        """
        selected_types = [key for key, checkbox in self.highwayCheckboxes.items() if checkbox.isChecked()]
        self.custom_filter = build_highway_filter(selected_types)

    def activateMapPolygonDrawing(self):
        """
        Activate polygon drawing mode on map.
        
        Enables the interactive polygon drawing functionality on the Leaflet
        map and connects signals for polygon completion.
        """
        if not self._begin_polygon_capture():
            QMessageBox.warning(self, "Warnung", "Keine Kartenverbindung verfügbar.")
            return

        self.drawPolygonButton.setEnabled(False)
        self.drawPolygonButton.setText("Warte auf Polygon...")
        self.drawPolygonButton.setStyleSheet("background-color: #ffc107; color: black; padding: 5px 10px;")
        self.polygonStatusLabel.setText("Status: Zeichnen Sie jetzt ein Polygon auf der Karte")
        self.polygonStatusLabel.setStyleSheet("color: #ffc107; font-weight: bold;")

    def onPolygonReady(self):
        """
        Called when polygon has been drawn on the map.
        
        Updates UI state and notifies the user that the polygon is ready
        and can be edited before starting the download.
        """
        
        if not self.waiting_for_polygon:
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

    def createFileInput(self, default_path):
        """
        Create file input widget with browse button.

        Creates a QLineEdit and QPushButton combination for file path
        input with browse dialog functionality.

        :param default_path: Default file path
        :type default_path: str
        :return: Line edit and button widgets
        :rtype: tuple
        """
        lineEdit = QLineEdit(default_path)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def createFileInputLayout(self, lineEdit, button):
        """
        Create file input layout.

        Combines file path input widget and browse button into a horizontal
        layout for consistent UI presentation.

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

    def selectFile(self, lineEdit):
        """
        Open file dialog and update line edit.

        Displays a file selection dialog and updates the provided line edit
        widget with the selected file path.

        :param lineEdit: Widget to update with selected file path
        :type lineEdit: QLineEdit
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", self.base_path, "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def addTagField(self, key="", value=""):
        """
        Add tag field to layout.

        Creates and adds a new key-value pair input row for OSM tag
        specification in the query dialog.

        :param key: Tag key
        :type key: str
        :param value: Tag value
        :type value: str
        """
        key = str(key) if key is not None else ""
        value = str(value) if value is not None else ""

        keyLineEdit = QLineEdit(key)
        valueLineEdit = QLineEdit(value)
        self.tagsLayout.addRow(keyLineEdit, valueLineEdit)

        self.tagsLayoutList.append((keyLineEdit, valueLineEdit))
        self.tags_to_download.append((key, value))

    def removeTagField(self):
        """
        Remove last tag field from layout.
        
        Removes the most recently added tag key-value pair from the
        tag specification form.
        """
        if self.tags_to_download:
            keyLineEdit, valueLineEdit = self.tagsLayoutList.pop()
            self.tags_to_download.pop()
            self.tagsLayout.removeRow(keyLineEdit)

    def loadAllStandardTags(self):
        """
        Load all standard tags into layout.
        
        Populates the tag specification form with all predefined
        standard OSM tags for building queries.
        """
        for tag in self.standard_tags:
            key = next(iter(tag))
            value = tag[key]
            self.addTagField(key, value)

    def loadSelectedStandardTag(self):
        """
        Load selected standard tag into layout.
        
        Adds the currently selected standard tag from the dropdown
        to the tag specification form.
        """
        selected_tag_index = self.standardTagsComboBox.currentIndex()
        tag = self.standard_tags[selected_tag_index]
        key = next(iter(tag))
        value = tag[key]
        self.addTagField(key, value)
    
    def startQuery(self):
        """
        Start OSM data query and download.
        
        Initiates the OpenStreetMap street data download process based on
        selected area type, method, and filter settings.
        """
        filename = self.filenameLineEdit.text()
        
        if not filename:
            QMessageBox.warning(self, "Warnung", "Bitte geben Sie einen Dateinamen an.")
            return
        
        
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
            'drawn_polygon_file': None,
            'project_crs': self.project_crs
        }
        
        # Handle drawn polygon - get file path NOW before thread
        if area_type == "Polygon auf Karte zeichnen":
            try:
                drawn_polygon = self.getCapturedPolygonFromMap()
                if not drawn_polygon or not os.path.exists(drawn_polygon):
                    QMessageBox.warning(self, "Warnung", 
                        "Bitte zeichnen Sie zuerst ein Polygon auf der Karte.\n\n" +
                        "Klicken Sie auf 'Polygon auf Karte zeichnen' und zeichnen Sie den gewünschten Bereich.")
                    return
                area_params['drawn_polygon_file'] = drawn_polygon
            except Exception as e:
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
            
            # Create and start download thread
            self.download_thread = OSMStreetDownloadThread(self._performOSMnxDownload, filename, area_params)
            
            self.download_thread.download_done.connect(self._onDownloadComplete)
            self.download_thread.download_error.connect(self._onDownloadError)
            self.download_thread.start()
            
            self.progress_dialog.setLabelText("Download läuft... Bitte warten.")
                
        except Exception as e:
            self.queryButton.setEnabled(True)
            self.queryButton.setText("Download starten")
            if self.progress_dialog:
                self.progress_dialog.close()
            QMessageBox.critical(self, "Fehler", f"Fehler beim Start des Downloads:\n{str(e)}\n\n{traceback.format_exc()}")

    def _onDownloadComplete(self, filepath):
        """
        Handle successful download completion.
        
        Processes successful street network download, cleans up UI state,
        adds the layer to the map, and notifies the user.
        
        :param filepath: Path to the downloaded GeoJSON file
        :type filepath: str
        """
        
        # Clear drawn polygon from map if it was used
        if hasattr(self, 'last_area_type') and self.last_area_type == "Polygon auf Karte zeichnen":
            self.clearCapturedPolygon()
        
        if self.progress_dialog:
            self.progress_dialog.close()
        
        self.queryButton.setEnabled(True)
        self.queryButton.setText("Download starten")
        
        QMessageBox.information(self, "Erfolg", 
            f"Download abgeschlossen!\n\nDatei gespeichert: {filepath}")
        
        # Add to map
        self.parent_pres.add_geojson_layer([filepath])
        self.accept()

    def _performOSMnxDownload(self, filename, area_params):
        """
        Perform OSMnx download (runs in thread).
        
        Executes OSMnx street network download in a background thread.
        No GUI access allowed in this method.
        
        :param filename: Output file path
        :type filename: str
        :param area_params: Dictionary with area type and file paths (no GUI access!)
        :type area_params: dict
        :return: Path to the saved file
        :rtype: str
        """
        try:
            return self.downloadWithOSMnx(filename, area_params)
        except Exception:
            raise

    def downloadWithOSMnx(self, filename, area_params):
        """
        Download street network using OSMnx.
        
        Downloads OpenStreetMap street network data using the OSMnx library
        based on various area selection methods (city name, CSV buffer, polygon).
        
        :param filename: Output file path
        :type filename: str
        :param area_params: Dictionary with area type and file paths (no GUI access!)
        :type area_params: dict
        """
        import osmnx as ox

        area_type = area_params['area_type']
        custom_filter = area_params['custom_filter']

        # Get the street network either by place name or by resolved polygon.
        if area_type == "Stadt/Ortsname":
            city_name = area_params['city_name']
            G = ox.graph_from_place(city_name, network_type='all', custom_filter=custom_filter)
        else:
            # CSV / GeoJSON / drawn polygon → WGS84 polygon (raises ValueError on a
            # malformed CSV; caught by the download thread → error signal).
            polygon = resolve_area_polygon(area_params, buffer_m=area_params.get('buffer_dist'))
            G = ox.graph_from_polygon(polygon, network_type='all', custom_filter=custom_filter)

        # Convert to GeoDataFrame
        gdf_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
        
        # Convert to project CRS
        gdf_edges = gdf_edges.to_crs(area_params.get('project_crs', 'EPSG:25833'))
        
        # Save to file
        gdf_edges.to_file(filename, driver='GeoJSON')
        
        return filename


class OSMBuildingQueryDialog(OSMDownloadDialogBase):
    """
    Dialog for querying OSM building data with multiple area selection modes.
    """
    _temp_polygon_filename = "_temp_building_polygon.geojson"

    def __init__(self, base_path, config_manager, parent, parent_pres, visualization_tab=None,
                 project_crs: str = "EPSG:25833"):
        """
        Initialize OSM building query dialog.

        Sets up the dialog for downloading OpenStreetMap building data
        with multiple area selection modes and configuration options.

        :param base_path: Base path for file operations
        :type base_path: str
        :param config_manager: Configuration manager instance
        :type config_manager: ConfigManager
        :param parent: Parent widget
        :type parent: QWidget
        :param parent_pres: Parent presenter instance
        :type parent_pres: object
        :param visualization_tab: Reference to visualization tab for polygon drawing
        :type visualization_tab: LeafletTab
        :param project_crs: Projected CRS for downloaded data
        :type project_crs: str
        """
        super().__init__(base_path, config_manager, parent, parent_pres,
                         project_crs=project_crs, visualization_tab=visualization_tab)
        self.initUI()

    def initUI(self):
        """
        Initialize user interface components.
        
        Creates and arranges all UI elements for area selection, tag
        specification, default values, and download controls.
        """
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
        self._download_button = self.downloadButton  # used by base cancel/error handlers
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
        """
        Show/hide widgets based on selected area type.
        
        Displays the appropriate input widgets for the selected area
        selection method (CSV, GeoJSON, or map drawing).
        """
        area_type = self.areaTypeComboBox.currentText()
        
        self.csvWidget.setVisible(area_type == "Bereich um Gebäude aus CSV")
        self.polygonWidget.setVisible(area_type == "Polygon aus GeoJSON")
        self.drawPolygonWidget.setVisible(area_type == "Polygon auf Karte zeichnen")

    def browseFile(self, line_edit, file_filter):
        """
        Open file dialog for selecting input file.
        
        Displays a file selection dialog with the specified filter and
        updates the line edit widget with the chosen file path.
        
        :param line_edit: Line edit to update with selected path
        :type line_edit: QLineEdit
        :param file_filter: File filter string for dialog
        :type file_filter: str
        """
        filename, _ = QFileDialog.getOpenFileName(
            self, "Datei auswählen", self.base_path, file_filter
        )
        if filename:
            line_edit.setText(filename)

    def browseSaveFile(self, line_edit):
        """
        Open file dialog for selecting output file.
        
        Displays a save file dialog for GeoJSON output and updates
        the line edit widget with the chosen file path.
        
        :param line_edit: Line edit to update with selected path
        :type line_edit: QLineEdit
        """
        filename, _ = QFileDialog.getSaveFileName(
            self, "Speicherort wählen", line_edit.text(), "GeoJSON-Dateien (*.geojson)"
        )
        if filename:
            line_edit.setText(filename)

    def activateMapPolygonDrawing(self):
        """
        Activate polygon drawing mode on the map.
        
        Enables interactive polygon drawing on the Leaflet map for
        defining the area for building data download.
        """
        if not self._begin_polygon_capture():
            QMessageBox.warning(self, "Fehler", "Keine Kartenverbindung verfügbar.")
            return

        self.drawPolygonButton.setText("Warte auf Polygon...")
        self.drawPolygonButton.setStyleSheet("background-color: #ffeb3b;")
        self.polygonStatusLabel.setText("Zeichnen Sie jetzt ein Polygon auf der Karte...")
        self.polygonStatusLabel.setStyleSheet("color: #ff9800;")

    def onPolygonReady(self):
        """
        Handle polygon ready signal from map.
        
        Updates UI state when the polygon drawing is completed on the map,
        allowing the user to proceed with the download.
        """
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

    def startQuery(self):
        """Start OSM building data query and download."""
        filename = self.filenameLineEdit.text()
        
        if not filename:
            QMessageBox.warning(self, "Warnung", "Bitte geben Sie einen Dateinamen an.")
            return
        
        # Get all GUI values BEFORE starting thread (GUI access not allowed in threads!)
        area_type = self.areaTypeComboBox.currentText()
        self.last_area_type = area_type  # Store for cleanup in completion handler
        
        # Prepare parameters based on area type
        area_params = {
            'area_type': area_type,
            'csv_file': self.csvLineEdit.text() if area_type == "Bereich um Gebäude aus CSV" else None,
            'polygon_file': self.polygonLineEdit.text() if area_type == "Polygon aus GeoJSON" else None,
            'drawn_polygon_file': None,
            'project_crs': self.project_crs
        }
        
        # Handle drawn polygon specially - get file path NOW before thread
        if area_type == "Polygon auf Karte zeichnen":
            try:
                drawn_polygon = self.getCapturedPolygonFromMap()
                if not drawn_polygon or not os.path.exists(drawn_polygon):
                    QMessageBox.warning(self, "Warnung", 
                        "Bitte zeichnen Sie zuerst ein Polygon auf der Karte.\n\n" +
                        "Klicken Sie auf 'Neues Polygon zeichnen' und zeichnen Sie den gewünschten Bereich.")
                    return
                area_params['drawn_polygon_file'] = drawn_polygon
            except Exception as e:
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
            # Create and start download thread - pass area_params instead of reading GUI in thread
            self.download_thread = OSMBuildingDownloadThread(self._performBuildingDownload, filename, area_params)
            self.download_thread.download_done.connect(self._onDownloadComplete)
            self.download_thread.download_error.connect(self._onDownloadError)
            
            self.progress_dialog.setLabelText("Download läuft...")
            self.download_thread.start()
        except Exception as e:
            if self.progress_dialog:
                self.progress_dialog.close()
            self.downloadButton.setEnabled(True)
            self.downloadButton.setText("Download starten")
            QMessageBox.critical(self, "Fehler", f"Fehler beim Start des Downloads:\n{str(e)}\n\n{traceback.format_exc()}")

    def _onDownloadComplete(self, filepath, building_count):
        """
        Handle successful download completion.
        
        Processes successful building data download, cleans up UI state,
        adds the layer to the map, and notifies the user of the results.
        
        :param filepath: Path to the downloaded GeoJSON file
        :type filepath: str
        :param building_count: Number of buildings downloaded
        :type building_count: int
        """
        
        # Clear drawn polygon from map if it was used
        if hasattr(self, 'last_area_type') and self.last_area_type == "Polygon auf Karte zeichnen":
            self.clearCapturedPolygon()
        
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        self.downloadButton.setEnabled(True)
        self.downloadButton.setText("Download starten")
        
        QMessageBox.information(self, "Erfolg", 
            "Download abgeschlossen!\n\n" +
            f"{building_count} Gebäude gespeichert in:\n{filepath}")
        
        # Add to map
        self.parent_pres.add_geojson_layer([filepath])
        self.accept()

    def _performBuildingDownload(self, filename, area_params):
        """
        Perform building download (runs in thread).
        
        Executes building data download in a background thread using
        Overpass API. No GUI access allowed in this method.
        
        :param filename: Output file path
        :type filename: str
        :param area_params: Dictionary with area type and file paths (no GUI access in thread!)
        :type area_params: dict
        :return: (filepath, building_count)
        :rtype: tuple
        """
        try:
            return self.downloadBuildings(filename, area_params)
        except Exception:
            raise

    def downloadBuildings(self, filename, area_params):
        """
        Download building data using Overpass API.
        
        Downloads OpenStreetMap building data using the Overpass API based
        on various area selection methods (CSV buffer, GeoJSON polygon, map drawing).
        
        :param filename: Output file path
        :type filename: str
        :param area_params: Dictionary with area type and file paths
        :type area_params: dict
        """
        import geopandas as gpd

        # CSV / GeoJSON / drawn polygon → WGS84 polygon. Buildings near CSV points
        # are captured with a small 5 m buffer. Raises ValueError on a malformed
        # CSV (caught by the download thread → error signal).
        polygon = resolve_area_polygon(area_params, buffer_m=5.0)

        # Download buildings using Overpass API
        bounds = polygon.bounds  # (minx, miny, maxx, maxy)
        
        # Build Overpass query for buildings within polygon
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
        
        # Download data
        geojson_data = download_data(query, element_type="building")
        
        # Convert to GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(geojson_data['features'], crs='EPSG:4326')
        
        # Filter to only buildings within the actual polygon (not just bounding box)
        gdf_filtered = gdf[gdf.geometry.intersects(polygon)]
        
        # Convert to project CRS
        gdf_filtered = gdf_filtered.to_crs(area_params.get('project_crs', 'EPSG:25833'))
        
        # Save to file
        gdf_filtered.to_file(filename, driver='GeoJSON')
        
        return (filename, len(gdf_filtered))
