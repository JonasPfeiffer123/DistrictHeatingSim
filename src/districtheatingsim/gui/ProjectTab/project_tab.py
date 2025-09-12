"""
Project Tab Module
==================

Project management tab with MVP architecture for CSV file editing and project tracking.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-20
"""

import os
import sys
import csv
import json

from PyQt6.QtWidgets import (QMainWindow, QFileDialog, QTableWidgetItem, QWidget, QVBoxLayout, QHBoxLayout,
                             QMenuBar, QProgressBar, QLabel, QTableWidget, QFrame,
                             QTreeView, QSplitter, QMessageBox, QDialog, QMenu, QPushButton, QInputDialog, QSizePolicy)
from PyQt6.QtGui import QAction, QFileSystemModel
from PyQt6.QtCore import Qt, QTimer

from districtheatingsim.gui.LeafletTab.net_generation_threads import GeocodingThread
from districtheatingsim.gui.ProjectTab.project_tab_dialogs import RowInputDialog, OSMImportDialog, ProcessDetailsDialog

class ProjectModel:
    """
    Model for managing project data including CSV and GeoJSON file operations.
    """
    def __init__(self):
        self.base_path = None
        self.current_file_path = ''
        self.layers = {}

    def set_base_path(self, base_path):
        """
        Set project base path.

        Parameters
        ----------
        base_path : str
            Project base path.
        """
        self.base_path = base_path

    def get_base_path(self):
        """
        Get project base path.

        Returns
        -------
        str
            Current base path.
        """
        return self.base_path

    def load_csv(self, file_path):
        """
        Load CSV file data.

        Parameters
        ----------
        file_path : str
            Path to CSV file.

        Returns
        -------
        tuple
            Headers and data lists.
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter=';')
            headers = next(reader)
            data = [row for row in reader]
        return headers, data

    def save_csv(self, file_path, headers, data):
        """
        Save data to CSV file.

        Parameters
        ----------
        file_path : str
            Output file path.
        headers : list
            Column headers.
        data : list of lists
            Table data.
        """
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(headers)
            writer.writerows(data)

    def create_csv(self, file_path, headers, default_data):
        """
        Create new CSV file with default data.

        Parameters
        ----------
        file_path : str
            Output file path.
        headers : list
            Column headers.
        default_data : list
            Default row data.
        """
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(headers)
            writer.writerow(default_data)

    def create_csv_from_geojson(self, geojson_file_path, output_file_path, default_values):
        """
        Create CSV from GeoJSON data with default values.

        Parameters
        ----------
        geojson_file_path : str
            Input GeoJSON file path.
        output_file_path : str
            Output CSV file path.
        default_values : dict
            Default values for building parameters.

        Returns
        -------
        str
            Output file path.
        """
        try:
            with open(geojson_file_path, 'r') as geojson_file:
                data = json.load(geojson_file)
            with open(output_file_path, 'w', encoding='utf-8', newline='') as csvfile:
                fieldnames = ["Land", "Bundesland", "Stadt", "Adresse", "Wärmebedarf", "Gebäudetyp", "Subtyp", "WW_Anteil", "Typ_Heizflächen", 
                              "VLT_max", "Steigung_Heizkurve", "RLT_max", "Normaußentemperatur", "UTM_X", "UTM_Y"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
                writer.writeheader()
                for feature in data['features']:
                    centroid = self.calculate_centroid(feature['geometry']['coordinates'])
                    writer.writerow({
                        "Land": default_values["Land"],
                        "Bundesland": default_values["Bundesland"],
                        "Stadt": default_values["Stadt"],
                        "Adresse": default_values["Adresse"],
                        "Wärmebedarf": default_values["Wärmebedarf"],
                        "Gebäudetyp": default_values["Gebäudetyp"],
                        "Subtyp": default_values["Subtyp"],
                        "WW_Anteil": default_values["WW_Anteil"],
                        "Typ_Heizflächen": default_values["Typ_Heizflächen"],
                        "VLT_max": default_values["VLT_max"],
                        "Steigung_Heizkurve": default_values["Steigung_Heizkurve"],
                        "RLT_max": default_values["RLT_max"],
                        "Normaußentemperatur": default_values["Normaußentemperatur"],
                        "UTM_X": centroid[0],
                        "UTM_Y": centroid[1]
                    })
            return output_file_path
        except Exception as e:
            raise Exception(f"Fehler beim Erstellen der CSV-Datei: {str(e)}")

    def calculate_centroid(self, coordinates):
        """
        Calculate centroid of coordinate array.

        Parameters
        ----------
        coordinates : list
            Coordinate array.

        Returns
        -------
        tuple
            Centroid coordinates (x, y).
        """
        x_sum = 0
        y_sum = 0
        total_points = 0
        if isinstance(coordinates[0], float):
            x_sum += coordinates[0]
            y_sum += coordinates[1]
            total_points += 1
        else:
            for item in coordinates:
                x, y = self.calculate_centroid(item)
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

    def get_resource_path(self, relative_path):
        """
        Get absolute resource path for dev and PyInstaller.

        Parameters
        ----------
        relative_path : str
            Relative path to resource.

        Returns
        -------
        str
            Absolute resource path.
        """
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

class ProjectPresenter:
    """
    Presenter managing interaction between ProjectModel and ProjectTabView.
    """
    def __init__(self, model, view, folder_manager, data_manager, config_manager):
        """
        Initialize project presenter.

        Parameters
        ----------
        model : ProjectModel
            Data model.
        view : ProjectTabView
            View component.
        folder_manager : object
            Folder manager.
        data_manager : object
            Data manager.
        config_manager : object
            Configuration manager.
        """
        self.model = model
        self.view = view
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        # Define process steps for project tracking
        self.process_steps = [
            {
                "name": "Schritt 1: Gebäudedaten Quartier definieren",
                "description": "Erstellen Sie die Gebäude-CSV hier im Tab 'Projektdefinition'.",
                "required_files": [
                    "..\\Definition Quartier IST\\Quartier IST.csv"
                ]
            },
            {
                "name": "Schritt 2: Gebäude-Lastgang generieren",
                "description": "Generieren Sie den Gebäude-Lastgang im Tab 'Wärmebedarf Gebäude' ",
                "required_files": [
                    "Lastgang\\Gebäude Lastgang.json"
                ]
            },
            {
                "name": "Schritt 3: Straßendaten herunterladen",
                "description": "Führen Sie eine OSM-Straßenabfrage im Tab 'Wärmenetz generieren' durch.",
                "required_files": [
                    "..\\Eingangsdaten allgemein\\Straßen.geojson"
                ]
            },
            {
                "name": "Schritt 3: Wärmenetz Daten erstellen",
                "description": "Generieren Sie das Wärmenetz im Tab 'Wärmenetz generieren'.",
                "required_files": [
                    "Wärmenetz\\Erzeugeranlagen.geojson",
                    "Wärmenetz\\HAST.geojson",
                    "Wärmenetz\\Vorlauf.geojson",
                    "Wärmenetz\\Rücklauf.geojson"
                ]
            },
            {
                "name": "Schritt 4: Thermohydraulische Berechnung",
                "description": "Führen Sie die Thermohydraulische Berechnung mit den generierten Netzdaten durch.",
                "required_files": [
                    "Wärmenetz\\Ergebnisse Netzinitialisierung.p",
                    "Wärmenetz\\Ergebnisse Netzinitialisierung.csv",
                    "Wärmenetz\\Konfiguration Netzinitialisierung.json",
                    "Wärmenetz\\dimensioniertes Wärmenetz.geojson",
                    "Lastgang\\Lastgang.csv"
                ]
            },
            {
                "name": "Schritt 5: Erzeugermix auslegen und berechnen",
                "description": "Berechnen sie den Erzeugermix und speichern sie die Ergebnisse.",
                "required_files": [
                    "Ergebnisse\\calculated_heat_generation.csv",
                    "Ergebnisse\\Ergebnisse.json"
                ]
            }
        ]

        # Connect signals and initialize (only after view is set)
        self.folder_manager.project_folder_changed.connect(self.on_variant_folder_changed)

        # Progress update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress_tracker)
        self.timer.start(50000)

    def connect_view_signals(self):
        """Connect view signals after view is created."""
        if self.view:
            self.view.treeView.doubleClicked.connect(self.on_tree_view_double_clicked)
            # Initial update after view is available
            if self.folder_manager.variant_folder:
                self.on_variant_folder_changed(self.folder_manager.variant_folder)
            self.update_progress_tracker()

    def on_variant_folder_changed(self, path):
        """
        Handle project folder change.

        Parameters
        ----------
        path : str
            New project folder path.
        """
        if path:
            self.model.set_base_path(path)
            if self.view:  # Only update if view exists
                self.view.update_tree_view(os.path.dirname(path))
        if self.view:  # Only update progress if view exists
            self.update_progress_tracker()

    def on_tree_view_double_clicked(self, index):
        """Handle tree view double-click events."""
        file_path = self.view.get_selected_file_path(index)
        
        if os.path.isdir(file_path):
            if "Variante" in os.path.basename(file_path):
                self.folder_manager.set_variant_folder(file_path)
            else:
                self.folder_manager.set_project_folder(file_path)
        elif file_path.endswith('.csv'):
            self.load_csv(file_path)

    def import_csv(self):
        """Open CSV file dialog and load selected file."""
        standard_path = os.path.join(self.folder_manager.get_variant_folder(), self.config_manager.get_relative_path("current_building_data_path"))
        fname, _ = QFileDialog.getOpenFileName(self.view, 'CSV öffnen', standard_path, 'CSV Files (*.csv);;All Files (*)')
        if fname and fname.strip():  # Check for valid file path
            self.load_csv(fname)

    def load_csv(self, file_path):
        """
        Load CSV file into table view.

        Parameters
        ----------
        file_path : str
            Path to CSV file.
        """
        headers, data = self.model.load_csv(file_path)
        self.model.current_file_path = file_path
        self.view.csvTable.setRowCount(0)
        self.view.csvTable.setColumnCount(len(headers))
        self.view.csvTable.setHorizontalHeaderLabels(headers)
        for row_data in data:
            row = self.view.csvTable.rowCount()
            self.view.csvTable.insertRow(row)
            for column, data in enumerate(row_data):
                item = QTableWidgetItem(data)
                self.view.csvTable.setItem(row, column, item)

    def save_csv(self, show_dialog=True):
        """Save current table data to CSV file. If show_dialog is False, use default path and suppress messages."""
        headers = [self.view.csvTable.horizontalHeaderItem(i).text() for i in range(self.view.csvTable.columnCount())]
        data = [[self.view.csvTable.item(row, column).text() if self.view.csvTable.item(row, column) else '' 
                for column in range(self.view.csvTable.columnCount())] for row in range(self.view.csvTable.rowCount())]
        file_path = self.model.current_file_path
        if not file_path:
            # Use default path if no file is open
            file_path = os.path.join(self.folder_manager.get_variant_folder(), self.config_manager.get_relative_path("current_building_data_path"))
            self.model.current_file_path = file_path
        try:
            self.model.save_csv(file_path, headers, data)
            if show_dialog:
                self.view.show_message("Erfolg", f"CSV-Datei wurde in {file_path} gespeichert.")
        except Exception as e:
            if show_dialog:
                self.view.show_error_message("Fehler", str(e))

    def add_row(self):
        """Add new empty row to table."""
        self.view.csvTable.insertRow(self.view.csvTable.rowCount())

    def del_row(self):
        """Delete selected row from table."""
        currentRow = self.view.csvTable.currentRow()
        if currentRow > -1:
            self.view.csvTable.removeRow(currentRow)
        else:
            self.view.show_error_message("Warnung", "Bitte wählen Sie eine Zeile zum Löschen aus.")

    def create_csv(self, fname=None, show_dialog=True):
        """Create new CSV file with default building data headers. If show_dialog is False, use default path and suppress dialog."""
        headers = ['Land', 'Bundesland', 'Stadt', 'Adresse', 'Wärmebedarf', 'Gebäudetyp', "Subtyp", 'WW_Anteil', 'Typ_Heizflächen', 'VLT_max', 'Steigung_Heizkurve', 'RLT_max', "Normaußentemperatur"]
        default_data = ['']*len(headers)
        if not fname:
            fname = os.path.join(self.folder_manager.get_variant_folder(), self.config_manager.get_relative_path("current_building_data_path"))
            if show_dialog:
                fname_dialog, _ = QFileDialog.getSaveFileName(self.view, 'Gebäude-CSV erstellen', fname, 'CSV Files (*.csv);;All Files (*)')
                if fname_dialog and fname_dialog.strip():  # Check for valid file path
                    fname = fname_dialog
                else:
                    return  # User cancelled dialog
        if fname and fname.strip():  # Additional check for valid filename
            self.model.create_csv(fname, headers, default_data)
            self.load_csv(fname)
            if show_dialog:
                self.view.show_message("Erfolg", f"CSV-Datei wurde in {fname} erstellt.")

    def create_csv_from_geojson(self):
        """Create CSV from GeoJSON with user-defined building parameters."""
        standard_path = os.path.join(self.folder_manager.get_variant_folder(), self.config_manager.get_relative_path("OSM_buldings_path"))
        geojson_file_path, _ = QFileDialog.getOpenFileName(self.view, "geoJSON auswählen", standard_path, "All Files (*)")
        if geojson_file_path and geojson_file_path.strip():  # Check for valid file path
            dialog = OSMImportDialog(self.view)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                default_values = dialog.get_input_data()
                try:
                    standard_output_path = os.path.join(self.folder_manager.get_variant_folder(), self.config_manager.get_relative_path("OSM_building_data_path"))
                    output_file_path = standard_output_path
                    self.model.create_csv_from_geojson(geojson_file_path, output_file_path, default_values)
                    self.load_csv(output_file_path)
                except Exception as e:
                    self.view.show_error_message("Fehler", str(e))

    def geocode_current_csv(self):
        """Geocode the currently loaded CSV file."""
        if hasattr(self.model, 'current_file_path') and self.model.current_file_path:
            # Save current table data first
            self.save_csv(show_dialog=False)
            # Then geocode the saved file
            self.geocode_addresses(self.model.current_file_path)
        else:
            self.view.show_error_message("Fehler", "Keine CSV-Datei geladen. Bitte laden Sie zuerst eine CSV-Datei oder erstellen Sie eine neue.")

    def open_geocode_addresses_dialog(self):
        """Open file dialog for geocoding CSV selection."""
        standard_path = os.path.join(self.folder_manager.get_variant_folder(), self.config_manager.get_relative_path("current_building_data_path"))
        fname, _ = QFileDialog.getOpenFileName(self.view, 'CSV-Koordinaten laden', standard_path, 'CSV Files (*.csv);;All Files (*)')
        if fname and fname.strip():  # Check for valid file path
            self.geocode_addresses(fname)

    def geocode_addresses(self, inputfilename):
        """
        Start geocoding thread for address processing.

        Parameters
        ----------
        inputfilename : str
            Path to CSV file for geocoding.
        """
        if hasattr(self, 'geocodingThread') and self.geocodingThread.isRunning():
            self.geocodingThread.terminate()
            self.geocodingThread.wait()
        self.geocodingThread = GeocodingThread(inputfilename)
        self.geocodingThread.calculation_done.connect(self.on_geocode_done)
        self.geocodingThread.calculation_error.connect(self.on_geocode_error)
        self.geocodingThread.start()
        self.view.progressBar.setRange(0, 0)

    def on_geocode_done(self, fname):
        """
        Handle geocoding completion.

        Parameters
        ----------
        fname : str
            Output filename.
        """
        self.view.progressBar.setRange(0, 1)

    def on_geocode_error(self, error_message):
        """
        Handle geocoding errors.

        Parameters
        ----------
        error_message : str
            Error message to display.
        """
        self.view.show_error_message("Fehler beim Geocoding", error_message)
        self.view.progressBar.setRange(0, 1)

    def update_progress(self, progress, csv_status=None):
        """
        Update progress bar value and CSV status label.

        Parameters
        ----------
        progress : float
            Progress percentage.
        csv_status : str, optional
            Status text for Quartier IST.csv
        """
        self.projectProgressBar.setValue(int(progress))
        if csv_status is not None:
            self.csv_status_label.setText(f"Quartier IST.csv Status: {csv_status}")

    def check_csv_status(self, csv_file_path):
        """
        Check detailed CSV status: missing, available without coordinates, or with coordinates.
        
        Parameters
        ----------
        csv_file_path : str
            Path to CSV file to check.
            
        Returns
        -------
        str
            Status: 'fehlt', 'ist vorhanden', or 'mit Koordinaten'
        """
        if not os.path.exists(csv_file_path):
            return 'fehlt'
            
        try:
            with open(csv_file_path, 'r', encoding='utf-8', errors='ignore') as file:
                # Use semicolon delimiter to match the CSV format
                reader = csv.DictReader(file, delimiter=';')
                headers = reader.fieldnames
                
                if not headers:
                    return 'ist vorhanden'
                
                # Check if UTM coordinate columns exist
                coord_columns = ['UTM_X', 'UTM_Y']
                has_coord_headers = all(col in headers for col in coord_columns)
                
                if not has_coord_headers:
                    return 'ist vorhanden'
                
                # Check if coordinate columns have data
                for row in reader:
                    if 'UTM_X' in row and 'UTM_Y' in row and row['UTM_X'] and row['UTM_Y']:
                        if row['UTM_X'].strip() and row['UTM_Y'].strip():
                            try:
                                x_val = float(row['UTM_X'])
                                y_val = float(row['UTM_Y'])
                                return 'mit Koordinaten'  # Found at least one valid coordinate pair
                            except ValueError:
                                continue
                    # Only check first few rows for performance
                    break
                    
                return 'ist vorhanden'  # Has headers but no valid coordinate data
                
        except Exception as e:
            # If we can't read the CSV, assume it exists but is problematic
            return 'ist vorhanden'

    def update_progress_tracker(self):
        """Update project progress and CSV status label based on file existence and content."""
        if not self.view:  # Skip if view not available yet
            return
            
        base_path = self.model.get_base_path()

        # CSV Status: check first process step (Quartier IST.csv) with detailed analysis
        csv_status = "unbekannt"
        if base_path:
            # Check first process step for Quartier IST.csv
            first_step = self.process_steps[0]
            csv_file_path = os.path.join(base_path, first_step['required_files'][0])
            csv_status = self.check_csv_status(csv_file_path)
            
            # Update all process steps
            for step in self.process_steps:
                full_paths = [os.path.join(base_path, path) for path in step['required_files']]
                generated_files = [file for file in full_paths if os.path.exists(file)]
                step['completed'] = len(generated_files) == len(full_paths)
                step['missing_files'] = [path for path in full_paths if not os.path.exists(path)]
        else:
            for step in self.process_steps:
                step['completed'] = False
                step['missing_files'] = step['required_files']

        total_steps = len(self.process_steps)
        completed_steps = sum(1 for step in self.process_steps if step['completed'])
        overall_progress = (completed_steps / total_steps) * 100

        self.view.update_progress(overall_progress, csv_status=csv_status)
        self.view.set_process_steps(self.process_steps)

class ProjectTabView(QWidget):
    """
    View component for project tab UI with file browser and CSV editor.
    """
    def __init__(self, presenter=None, parent=None):
        """
        Initialize project tab view.

        Parameters
        ----------
        presenter : ProjectPresenter, optional
            Presenter instance for signal connections.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.presenter = presenter
        self.initUI()

    def initUI(self):
        """Initialize user interface components."""
        mainLayout = QVBoxLayout()
        splitter = QSplitter()

        # Left area - file browser and progress
        self.leftLayout = QVBoxLayout()
        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.treeView = QTreeView()
        self.treeView.setModel(self.model)
        self.treeView.setMinimumWidth(500)
        self.treeView.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Projektfortschritt oben
        self.progressLayout = QHBoxLayout()
        self.progressLabel = QLabel("Projektfortschritt:")
        self.progressLayout.addWidget(self.progressLabel)

        self.projectProgressBar = QProgressBar(self)
        self.progressLayout.addWidget(self.projectProgressBar)

        # Details Button
        self.detailsButton = QPushButton("Details Projektfortschritt anzeigen", self)
        self.detailsButton.setToolTip("Details zu den einzelnen Schritten anzeigen")
        self.detailsButton.clicked.connect(self.showDetailsDialog)
        self.progressLayout.addWidget(self.detailsButton)

        self.leftLayout.addLayout(self.progressLayout)

        # CSV-Status oben
        self.csv_status_label = QLabel("❓ Quartier IST.csv: Status unbekannt")
        self.csv_status_label.setStyleSheet("font-weight: bold; color: #757575; background-color: #f5f5f5; padding: 8px; border-radius: 4px; border-left: 4px solid #757575; margin-bottom: 10px;")
        self.leftLayout.addWidget(self.csv_status_label)


        # Button-Bar für alle Aktionen
        button_layout = QHBoxLayout()
        self.csv_import_button = QPushButton("CSV importieren")
        self.csv_import_button.setToolTip("Bestehende Gebäude-CSV importieren und ins Projekt kopieren")
        button_layout.addWidget(self.csv_import_button)

        self.csv_create_button = QPushButton("CSV erstellen")
        self.csv_create_button.setToolTip("Neue Gebäude-CSV erstellen")
        button_layout.addWidget(self.csv_create_button)

        self.csv_save_button = QPushButton("CSV speichern")
        self.csv_save_button.setToolTip("CSV aus Tabelle speichern")
        button_layout.addWidget(self.csv_save_button)
        self.csv_from_osm_button = QPushButton("CSV aus OSM-GeoJSON")
        self.csv_from_osm_button.setToolTip("Gebäude-CSV aus OSM-GeoJSON generieren")
        button_layout.addWidget(self.csv_from_osm_button)
        self.geocode_button = QPushButton("Geokoordinaten berechnen")
        self.geocode_button.setToolTip("Aktuelle CSV-Datei geocodieren und Koordinaten hinzufügen")
        button_layout.addWidget(self.geocode_button)
        button_frame = QFrame()
        button_frame.setLayout(button_layout)
        button_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.leftLayout.addWidget(button_frame)

        leftWidget = QWidget()
        leftWidget.setLayout(self.leftLayout)
        self.leftLayout.addWidget(self.treeView)

        splitter.addWidget(leftWidget)

        # Right area - CSV editor
        self.rightLayout = QVBoxLayout()
        # Menüleiste entfällt, alle Aktionen sind Buttons
        self.csvTable = QTableWidget()
        self.csvTable.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed)
        self.csvTable.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.csvTable.customContextMenuRequested.connect(self.show_context_menu)
        
        # Enhanced table formatting
        self.csvTable.setAlternatingRowColors(True)
        self.csvTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.csvTable.setSortingEnabled(True)
        self.csvTable.horizontalHeader().setStretchLastSection(True)
        
        # Set row height for better visibility
        self.csvTable.verticalHeader().setDefaultSectionSize(35)
        self.csvTable.verticalHeader().setMinimumSectionSize(30)
        
        self.rightLayout.addWidget(self.csvTable)

        self.progressBar = QProgressBar(self)
        self.rightLayout.addWidget(self.progressBar)
        rightWidget = QWidget()
        rightWidget.setLayout(self.rightLayout)
        splitter.addWidget(rightWidget)
        splitter.setStretchFactor(1, 2)

        mainLayout.addWidget(splitter)
        self.setLayout(mainLayout)

        # Button-Signale verbinden
        if self.presenter:
            self.csv_create_button.clicked.connect(self.presenter.create_csv)
            self.csv_import_button.clicked.connect(self.presenter.import_csv)
            self.csv_save_button.clicked.connect(lambda: self.presenter.save_csv(show_dialog=True))
            self.csv_from_osm_button.clicked.connect(self.presenter.create_csv_from_geojson)
            self.geocode_button.clicked.connect(self.presenter.geocode_current_csv)

    def update_tree_view(self, path):
        """
        Update file tree view root path.

        Parameters
        ----------
        path : str
            New root path.
        """
        self.treeView.setRootIndex(self.treeView.model().index(path))
        for column in range(self.model.columnCount()):
            self.treeView.resizeColumnToContents(column)

    def show_context_menu(self, position):
        """
        Show table context menu.

        Parameters
        ----------
        position : QPoint
            Menu position.
        """
        contextMenu = QMenu(self)
        addRowAction = QAction("Zeile hinzufügen", self)
        deleteRowAction = QAction("Zeile löschen", self)
        duplicateRowAction = QAction("Zeile duplizieren", self)
        addColumnAction = QAction("Spalte hinzufügen", self)
        deleteColumnAction = QAction("Spalte löschen", self)
        duplicatColumnAction = QAction("Spalte duplizieren", self)

        contextMenu.addAction(addRowAction)
        contextMenu.addAction(deleteRowAction)
        contextMenu.addAction(duplicateRowAction)
        contextMenu.addAction(addColumnAction)
        contextMenu.addAction(deleteColumnAction)
        contextMenu.addAction(duplicatColumnAction)
        
        addRowAction.triggered.connect(self.add_row)
        deleteRowAction.triggered.connect(self.delete_row)
        duplicateRowAction.triggered.connect(self.duplicate_row)
        addColumnAction.triggered.connect(self.add_column)
        deleteColumnAction.triggered.connect(self.delete_column)
        duplicatColumnAction.triggered.connect(self.duplicate_column)

        contextMenu.exec(self.csvTable.viewport().mapToGlobal(position))

    def add_row(self):
        """Add new table row with input dialog."""
        headers = [self.csvTable.horizontalHeaderItem(i).text() for i in range(self.csvTable.columnCount())]
        dialog = RowInputDialog(headers, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            row_data = dialog.get_input_data()
            row = self.csvTable.rowCount()
            self.csvTable.insertRow(row)
            for i, header in enumerate(headers):
                self.csvTable.setItem(row, i, QTableWidgetItem(row_data[header]))

    def delete_row(self):
        """Delete selected table row."""
        currentRow = self.csvTable.currentRow()
        if currentRow > -1:
            self.csvTable.removeRow(currentRow)
        else:
            self.show_error_message("Warnung", "Bitte wählen Sie eine Zeile zum Löschen aus.")

    def duplicate_row(self):
        """Duplicate selected table row."""
        currentRow = self.csvTable.currentRow()
        if currentRow > -1:
            row = self.csvTable.rowCount()
            self.csvTable.insertRow(row)
            for column in range(self.csvTable.columnCount()):
                item = self.csvTable.item(currentRow, column)
                newItem = QTableWidgetItem(item.text() if item else '')
                self.csvTable.setItem(row, column, newItem)
        else:
            self.show_error_message("Warnung", "Bitte wählen Sie eine Zeile zum Duplizieren aus.")

    def add_column(self):
        """Add new table column."""
        column_count = self.csvTable.columnCount()
        column_name, ok = QInputDialog.getText(self, "Spalte hinzufügen", "Name der neuen Spalte:")
        if ok and column_name:
            self.csvTable.insertColumn(column_count)
            self.csvTable.setHorizontalHeaderItem(column_count, QTableWidgetItem(column_name))

    def delete_column(self):
        """Delete selected table column."""
        currentColumn = self.csvTable.currentColumn()
        if currentColumn > -1:
            self.csvTable.removeColumn(currentColumn)
        else:
            self.show_error_message("Warnung", "Bitte wählen Sie eine Spalte zum Löschen aus.")
    
    def duplicate_column(self):
        """Duplicate selected table column."""
        currentColumn = self.csvTable.currentColumn()
        if currentColumn > -1:
            column_count = self.csvTable.columnCount()
            new_column_index = column_count
            self.csvTable.insertColumn(new_column_index)
            header_item = self.csvTable.horizontalHeaderItem(currentColumn)
            new_header_item = QTableWidgetItem(header_item.text() if header_item else '')
            self.csvTable.setHorizontalHeaderItem(new_column_index, new_header_item)
            for row in range(self.csvTable.rowCount()):
                item = self.csvTable.item(row, currentColumn)
                new_item = QTableWidgetItem(item.text() if item else '')
                self.csvTable.setItem(row, new_column_index, new_item)
        else:
            self.show_error_message("Warnung", "Bitte wählen Sie eine Spalte zum Duplizieren aus.")

    def get_selected_file_path(self, index):
        """
        Get selected file path from tree view.

        Parameters
        ----------
        index : QModelIndex
            Tree view index.

        Returns
        -------
        str
            Selected file path.
        """
        return self.model.filePath(index)

    def show_error_message(self, title, message):
        """
        Display error message dialog.

        Parameters
        ----------
        title : str
            Dialog title.
        message : str
            Error message.
        """
        QMessageBox.critical(self, title, message)

    def update_progress(self, progress, csv_status=None):
        """
        Update progress bar value and CSV status label with color-coded status.

        Parameters
        ----------
        progress : float
            Progress percentage.
        csv_status : str, optional
            Status text for Quartier IST.csv: 'fehlt', 'geladen', 'geocodiert'
        """
        self.projectProgressBar.setValue(int(progress))
        if csv_status is not None:
            # Define status with icons and colors
            status_config = {
                'fehlt': {
                    'text': '❌ Quartier IST.csv: Datei fehlt',
                    'style': 'font-weight: bold; color: #d32f2f; background-color: #ffebee; padding: 8px; border-radius: 4px; border-left: 4px solid #d32f2f;'
                },
                'ist vorhanden': {
                    'text': '⚠️ Quartier IST.csv: Ist vorhanden (ohne Koordinaten)',
                    'style': 'font-weight: bold; color: #f57c00; background-color: #fff3e0; padding: 8px; border-radius: 4px; border-left: 4px solid #f57c00;'
                },
                'mit Koordinaten': {
                    'text': '✅ Quartier IST.csv: Mit Koordinaten (vollständig)',
                    'style': 'font-weight: bold; color: #388e3c; background-color: #e8f5e8; padding: 8px; border-radius: 4px; border-left: 4px solid #388e3c;'
                },
                'unbekannt': {
                    'text': '❓ Quartier IST.csv: Status unbekannt',
                    'style': 'font-weight: bold; color: #757575; background-color: #f5f5f5; padding: 8px; border-radius: 4px; border-left: 4px solid #757575;'
                }
            }
            
            config = status_config.get(csv_status, status_config['unbekannt'])
            self.csv_status_label.setText(config['text'])
            self.csv_status_label.setStyleSheet(config['style'])

    def showDetailsDialog(self):
        """Show process step details dialog."""
        dialog = ProcessDetailsDialog(self.process_steps, self)
        dialog.exec()

    def set_process_steps(self, process_steps):
        """
        Set process steps data for details dialog.

        Parameters
        ----------
        process_steps : list
            List of process step dictionaries.
        """
        self.process_steps = process_steps

    def show_message(self, title, message):
        """
        Display information message dialog.

        Parameters
        ----------
        title : str
            Dialog title.
        message : str
            Information message.
        """
        QMessageBox.information(self, title, message)

class ProjectTab(QMainWindow):
    """
    Main project tab window integrating MVP components.
    
    Central interface for project management with file operations
    and progress tracking functionality.
    """
    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        """
        Initialize project tab with MVP architecture.

        Parameters
        ----------
        folder_manager : object
            Folder manager.
        data_manager : object
            Data manager.
        config_manager : object
            Configuration manager.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__()
        self.setWindowTitle("Project Tab Example")
        self.setGeometry(100, 100, 800, 600)

        self.model = ProjectModel()
        self.presenter = ProjectPresenter(self.model, None, folder_manager, data_manager, config_manager)
        self.view = ProjectTabView(presenter=self.presenter)
        self.presenter.view = self.view
        self.presenter.connect_view_signals()

        self.setCentralWidget(self.view)