"""
Project Tab Dialogs Module
==========================

Dialog windows for project tab functionality including data input and progress display.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from PyQt6.QtWidgets import (QVBoxLayout, QLabel, QDialog, QLineEdit, QDialogButtonBox, 
                             QGridLayout, QFrame, QScrollArea, QPushButton, QProgressBar, 
                             QTableWidget, QTableWidgetItem, QHBoxLayout, QCheckBox)
from PyQt6.QtCore import Qt
from geopy.geocoders import Nominatim
from pyproj import Transformer

class RowInputDialog(QDialog):
    """
    Dialog for adding new table rows with input fields.
    """
    def __init__(self, headers, parent=None):
        """
        Initialize row input dialog.

        :param headers: Column headers for input fields.
        :type headers: list
        :param parent: Parent widget.
        :type parent: QWidget
        """
        super().__init__(parent)
        self.setWindowTitle("Neue Zeile hinzufügen")
        self.layout = QGridLayout(self)
        self.fields = {}

        # Create input fields with labels
        for i, header in enumerate(headers):
            label = QLabel(header)
            lineEdit = QLineEdit()
            lineEdit.setPlaceholderText(f"Geben Sie {header} ein")
            self.layout.addWidget(label, i, 0)
            self.layout.addWidget(lineEdit, i, 1)
            self.fields[header] = lineEdit

        # Dialog buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(buttonBox, len(headers), 0, 1, 2)

    def get_input_data(self):
        """
        Get input data from dialog fields.

        :return: Mapping of headers to input values.
        :rtype: dict
        """
        return {header: field.text() for header, field in self.fields.items()}
    
class OSMImportDialog(QDialog):
    """
    Dialog for OSM data import with default building parameters.
    """
    def __init__(self, parent=None, sample_utm_coords=None):
        """
        Initialize OSM import dialog.

        :param parent: Parent widget.
        :type parent: QWidget
        :param sample_utm_coords: Sample (UTM_X, UTM_Y) coordinates for reverse geocoding.
        :type sample_utm_coords: tuple
        """
        super().__init__(parent)
        self.setWindowTitle("OSM-Daten importieren")
        self.layout = QGridLayout(self)
        self.fields = {}
        self.sample_utm_coords = sample_utm_coords

        # Define the default values for the fields
        self.default_values = {
            "Land": "Deutschland",
            "Bundesland": "",
            "Stadt": "",
            "Adresse": "",
            "Wärmebedarf": "30000",
            "Gebäudetyp": "HMF",
            "Subtyp": "05",
            "WW_Anteil": "0.2",
            "Typ_Heizflächen": "HK",
            "VLT_max": "70",
            "Steigung_Heizkurve": "1.5",
            "RLT_max": "55",
            "Normaußentemperatur": "-15"
        }

        # Add checkbox for auto-fill
        if sample_utm_coords:
            self.auto_fill_checkbox = QCheckBox("Adressdaten automatisch aus Koordinaten ermitteln")
            self.auto_fill_checkbox.setChecked(True)
            self.auto_fill_checkbox.stateChanged.connect(self._on_auto_fill_changed)
            self.layout.addWidget(self.auto_fill_checkbox, 0, 0, 1, 2)
            row_offset = 1
        else:
            row_offset = 0

        # Create input fields with labels and default values
        for i, (header, value) in enumerate(self.default_values.items()):
            label = QLabel(header)
            lineEdit = QLineEdit(value)
            lineEdit.setPlaceholderText(f"Geben Sie {header} ein")
            self.layout.addWidget(label, i + row_offset, 0)
            self.layout.addWidget(lineEdit, i + row_offset, 1)
            self.fields[header] = lineEdit

        # Auto-fill address fields if coordinates provided
        if sample_utm_coords and self.auto_fill_checkbox.isChecked():
            self._reverse_geocode_and_fill()

        # Dialog buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(buttonBox, len(self.default_values) + row_offset, 0, 1, 2)

    def _on_auto_fill_changed(self, state):
        """
        Handle auto-fill checkbox state change.

        :param state: Checkbox state.
        :type state: int
        """
        if state == Qt.CheckState.Checked.value and self.sample_utm_coords:
            self._reverse_geocode_and_fill()
        elif state == Qt.CheckState.Unchecked.value:
            # Clear address fields
            self.fields["Land"].setText("Deutschland")
            self.fields["Bundesland"].setText("")
            self.fields["Stadt"].setText("")
            self.fields["Adresse"].setText("")

    def _reverse_geocode_and_fill(self):
        """
        Reverse geocode UTM coordinates and fill address fields.
        """
        if not self.sample_utm_coords:
            return

        try:
            utm_x, utm_y = self.sample_utm_coords
            
            # Transform UTM to WGS84
            transformer = Transformer.from_crs("epsg:25833", "epsg:4326", always_xy=True)
            lon, lat = transformer.transform(utm_x, utm_y)
            
            # Reverse geocode
            geolocator = Nominatim(user_agent="DistrictHeatingSim")
            location = geolocator.reverse(f"{lat}, {lon}", language="de")
            
            if location and location.raw.get('address'):
                address = location.raw['address']
                
                # Fill fields from geocoding result
                if 'country' in address:
                    self.fields["Land"].setText(address['country'])
                
                if 'state' in address:
                    self.fields["Bundesland"].setText(address['state'])
                
                # Try different keys for city
                city = address.get('city') or address.get('town') or address.get('village') or address.get('municipality') or ""
                if city:
                    self.fields["Stadt"].setText(city)
                
                # Build street address
                street_parts = []
                if 'road' in address:
                    street_parts.append(address['road'])
                if 'house_number' in address:
                    street_parts.append(address['house_number'])
                
                if street_parts:
                    self.fields["Adresse"].setText(" ".join(street_parts))
                
                print(f"Reverse geocoding erfolgreich: {location.address}")
            else:
                print("Keine Adressinformationen gefunden")
                
        except Exception as e:
            print(f"Fehler beim Reverse Geocoding: {e}")

    def get_input_data(self):
        """
        Get OSM import parameters.

        :return: Mapping of parameters to input values.
        :rtype: dict
        """
        return {header: field.text() for header, field in self.fields.items()}
    
class ProcessDetailsDialog(QDialog):
    """
    Dialog displaying detailed project progress information.
    """
    def __init__(self, process_steps, parent=None):
        """
        Initialize process details dialog.

        :param process_steps: List of process step dictionaries with progress info.
        :type process_steps: list
        :param parent: Parent widget.
        :type parent: QWidget
        """
        super().__init__(parent)
        self.setWindowTitle("Projektfortschritt - Details")
        self.setMinimumSize(800, 800)
        
        self.process_steps = process_steps

        # Main layout for the dialog
        main_layout = QVBoxLayout(self)
        
        # Scrollable area for process steps
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        
        # Container widget and layout for process steps
        process_widget = QFrame()
        process_layout = QVBoxLayout(process_widget)
        
        for step in self.process_steps:
            # Each process step will have its own section
            step_layout = QVBoxLayout()
            step_label = QLabel(f"{step['name']}")
            step_layout.addWidget(step_label)

            # Status and required files
            progress = self.get_step_progress(step)
            progress_bar = QProgressBar()
            progress_bar.setValue(int(progress))
            progress_bar.setTextVisible(True)
            step_layout.addWidget(progress_bar)

            # Description of the step
            description_label = QLabel(f"Beschreibung: {step['description']}")
            step_layout.addWidget(description_label)

            # Show CSV creation and geocoding status for first step
            if 'csv_creation_status' in step and 'geocoding_status' in step:
                # CSV Creation Status
                csv_status_text = self.get_status_text(step['csv_creation_status'])
                csv_status_color = self.get_status_color(step['csv_creation_status'])
                csv_label = QLabel(f"CSV-Erstellung: {csv_status_text}")
                csv_label.setStyleSheet(f"color: {csv_status_color}; font-weight: bold;")
                step_layout.addWidget(csv_label)
                
                # Geocoding Status
                geocoding_status_text = self.get_status_text(step['geocoding_status'])
                geocoding_status_color = self.get_status_color(step['geocoding_status'])
                geocoding_label = QLabel(f"Geocoding: {geocoding_status_text}")
                geocoding_label.setStyleSheet(f"color: {geocoding_status_color}; font-weight: bold;")
                step_layout.addWidget(geocoding_label)

            # Show missing files if any
            if len(step.get("missing_files", [])) > 0:
                for missing_file in step["missing_files"]:
                    missing_label = QLabel(f"Fehlende Datei: {missing_file}")
                    missing_label.setStyleSheet("color: red;")
                    step_layout.addWidget(missing_label)
            else:
                completed_label = QLabel("Alle Dateien vorhanden")
                completed_label.setStyleSheet("color: green;")
                step_layout.addWidget(completed_label)

            # Optionally, add file sizes and modification times if available
            if "file_sizes" in step:
                for i, size in enumerate(step["file_sizes"]):
                    size_label = QLabel(f"Dateigröße: {size}")
                    step_layout.addWidget(size_label)

            if "file_modification_times" in step:
                for i, mod_time in enumerate(step["file_modification_times"]):
                    mod_time_label = QLabel(f"Zuletzt geändert: {mod_time}")
                    step_layout.addWidget(mod_time_label)
            
            # Add the step layout to the process layout
            step_frame = QFrame()
            step_frame.setLayout(step_layout)
            process_layout.addWidget(step_frame)

        # Set the widget for the scroll area
        scroll_area.setWidget(process_widget)
        main_layout.addWidget(scroll_area)

        # Close button
        close_button = QPushButton("Schließen")
        close_button.clicked.connect(self.accept)
        main_layout.addWidget(close_button)

    def get_step_progress(self, step):
        """
        Calculate step completion percentage based on required files.

        :param step: Process step information.
        :type step: dict
        :return: Completion percentage (0-100).
        :rtype: float
        """
        total_files = len(step["required_files"])
        missing_files = len(step.get("missing_files", []))
        return ((total_files - missing_files) / total_files) * 100

    def get_status_text(self, status):
        """
        Get human-readable status text.

        :param status: Status code.
        :type status: str
        :return: Human-readable status text.
        :rtype: str
        """
        status_mapping = {
            'completed': 'Abgeschlossen',
            'pending': 'Ausstehend',
            'not_applicable': 'Nicht verfügbar',
            'not_checked': 'Nicht geprüft'
        }
        return status_mapping.get(status, 'Unbekannt')

    def get_status_color(self, status):
        """
        Get color for status display.

        :param status: Status code.
        :type status: str
        :return: CSS color value.
        :rtype: str
        """
        color_mapping = {
            'completed': 'green',
            'pending': 'orange',
            'not_applicable': 'gray',
            'not_checked': 'gray'
        }
        return color_mapping.get(status, 'black')

class BuildingCSVDialog(QDialog):
    """
    Dialog for tabular input and editing of Quartier IST.csv building data.
    """
    def __init__(self, headers, data=None, parent=None):
        """
        Initialize dialog for building CSV creation/editing.

        :param headers: Column headers for table.
        :type headers: list
        :param data: Initial table data.
        :type data: list of lists
        :param parent: Parent widget.
        :type parent: QWidget
        """
        super().__init__(parent)
        self.setWindowTitle("Gebäudedaten bearbeiten")
        self.resize(1200, 600)
        self.headers = headers
        self.data = data if data is not None else []
        self.initUI()

    def initUI(self):
        """
        Initialize user interface components.
        """
        layout = QVBoxLayout(self)
        label = QLabel("Geben Sie die Gebäudedaten für das Quartier ein:")
        layout.addWidget(label)

        self.table = QTableWidget(self)
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        self.table.setRowCount(len(self.data))
        
        # Enhanced table formatting
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        
        for row_idx, row_data in enumerate(self.data):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                self.table.setItem(row_idx, col_idx, item)
        layout.addWidget(self.table)

        # Buttons for row operations
        button_layout = QHBoxLayout()
        add_row_btn = QPushButton("Zeile hinzufügen")
        del_row_btn = QPushButton("Zeile löschen")
        add_row_btn.clicked.connect(self.add_row)
        del_row_btn.clicked.connect(self.del_row)
        button_layout.addWidget(add_row_btn)
        button_layout.addWidget(del_row_btn)
        layout.addLayout(button_layout)

        # Dialog buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

    def add_row(self):
        """
        Add new row to table.
        """
        self.table.insertRow(self.table.rowCount())

    def del_row(self):
        """
        Delete selected row from table.
        """
        currentRow = self.table.currentRow()
        if currentRow > -1:
            self.table.removeRow(currentRow)

    def get_table_data(self):
        """
        Get table data as list of lists.

        :return: Table data.
        :rtype: list of lists
        """
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        data = []
        for r in range(rows):
            row_data = []
            for c in range(cols):
                item = self.table.item(r, c)
                row_data.append(item.text() if item else "")
            data.append(row_data)
        return data