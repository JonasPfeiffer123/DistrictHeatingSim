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

from geopy.geocoders import Nominatim
from pyproj import Transformer

from districtheatingsim.gui.LeafletTab.net_generation_threads import GeocodingThread, GeoJSONToCSVThread
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
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as file:
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
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as file:
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
            
            # Initialize geocoder and transformer once
            geolocator = Nominatim(user_agent="DistrictHeatingSim")
            transformer = Transformer.from_crs("epsg:25833", "epsg:4326", always_xy=True)
            
            with open(output_file_path, 'w', encoding='utf-8-sig', newline='') as csvfile:
                fieldnames = ["Land", "Bundesland", "Stadt", "Adresse", "Wärmebedarf", "Gebäudetyp", "Subtyp", "WW_Anteil", "Typ_Heizflächen", 
                              "VLT_max", "Steigung_Heizkurve", "RLT_max", "Normaußentemperatur", "UTM_X", "UTM_Y"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
                writer.writeheader()
                
                for i, feature in enumerate(data['features']):
                    centroid = self.calculate_centroid(feature['geometry']['coordinates'])
                    
                    # Reverse geocode each building individually
                    land = default_values.get("Land", "Deutschland")
                    bundesland = default_values.get("Bundesland", "")
                    stadt = default_values.get("Stadt", "")
                    adresse = default_values.get("Adresse", "")
                    
                    if centroid[0] is not None and centroid[1] is not None:
                        try:
                            # Transform UTM to WGS84
                            lon, lat = transformer.transform(centroid[0], centroid[1])
                            
                            # Reverse geocode with timeout
                            location = geolocator.reverse(f"{lat}, {lon}", language="de", timeout=10)
                            
                            if location and location.raw.get('address'):
                                address_data = location.raw['address']
                                
                                # Extract address components
                                land = address_data.get('country', land)
                                bundesland = address_data.get('state', bundesland)
                                stadt = address_data.get('city') or address_data.get('town') or address_data.get('village') or address_data.get('municipality') or stadt
                                
                                # Build street address
                                street_parts = []
                                if 'road' in address_data:
                                    street_parts.append(address_data['road'])
                                if 'house_number' in address_data:
                                    street_parts.append(address_data['house_number'])
                                
                                if street_parts:
                                    adresse = " ".join(street_parts)
                                
                                print(f"Gebäude {i+1}: {adresse}, {stadt}")
                        except Exception as e:
                            print(f"Reverse Geocoding für Gebäude {i+1} fehlgeschlagen: {e}")
                    
                    writer.writerow({
                        "Land": land,
                        "Bundesland": bundesland,
                        "Stadt": stadt,
                        "Adresse": adresse,
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
                "description": "Erstellen Sie die Gebäude-CSV hier im Tab 'Projektdefinition'. Die CSV kann manuell erstellt, aus GeoJSON importiert oder durch Geocoding mit Koordinaten angereichert werden.",
                "required_files": [
                    "..\\Definition Quartier IST\\Quartier IST.csv"
                ],
                "csv_creation_status": "not_checked",  # Will be updated dynamically
                "geocoding_status": "not_checked"      # Will be updated dynamically
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
                    "Wärmenetz\\Wärmenetz.geojson"
                ]
            },
            {
                "name": "Schritt 4: Thermohydraulische Berechnung",
                "description": "Führen Sie die Thermohydraulische Berechnung mit den generierten Netzdaten durch.",
                "required_files": [
                    "Wärmenetz\\Ergebnisse Netzinitialisierung.p",
                    "Wärmenetz\\Ergebnisse Netzinitialisierung.csv",
                    "Wärmenetz\\Konfiguration Netzinitialisierung.json",
                    "Lastgang\\Lastgang.csv"
                ],
                "check_dimensioned_network": True  # Special check for dimensioned flag in Wärmenetz.geojson
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
            for column, cell_value in enumerate(row_data):
                item = QTableWidgetItem(cell_value)
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
            # Extract sample coordinates from first building for reverse geocoding
            sample_coords = None
            try:
                with open(geojson_file_path, 'r') as f:
                    data = json.load(f)
                    if data.get('features') and len(data['features']) > 0:
                        first_feature = data['features'][0]
                        centroid = self.model.calculate_centroid(first_feature['geometry']['coordinates'])
                        if centroid[0] is not None and centroid[1] is not None:
                            sample_coords = centroid
            except Exception as e:
                print(f"Konnte keine Beispielkoordinaten extrahieren: {e}")
            
            dialog = OSMImportDialog(self.view, sample_utm_coords=sample_coords)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                default_values = dialog.get_input_data()
                standard_output_path = os.path.join(self.folder_manager.get_variant_folder(), self.config_manager.get_relative_path("OSM_building_data_path"))
                output_file_path = standard_output_path
                
                # Start conversion in thread
                if hasattr(self, 'geojson_conversion_thread') and self.geojson_conversion_thread.isRunning():
                    self.geojson_conversion_thread.stop()
                    self.geojson_conversion_thread.wait()
                
                self.geojson_conversion_thread = GeoJSONToCSVThread(
                    geojson_file_path, 
                    output_file_path, 
                    default_values,
                    self.model
                )
                self.geojson_conversion_thread.progress_update.connect(self.on_geojson_conversion_progress)
                self.geojson_conversion_thread.calculation_done.connect(self.on_geojson_conversion_done)
                self.geojson_conversion_thread.calculation_error.connect(self.on_geojson_conversion_error)
                self.geojson_conversion_thread.start()
                
                # Show progress bar
                self.view.progressBar.setRange(0, 0)  # Indeterminate until we know total
                self.view.statusLabel.setText("Konvertiere GeoJSON zu CSV mit Reverse Geocoding...")

    def on_geojson_conversion_progress(self, current, total, message):
        """
        Handle progress updates from GeoJSON conversion thread.
        
        Parameters
        ----------
        current : int
            Current building number.
        total : int
            Total number of buildings.
        message : str
            Progress message.
        """
        if total > 0:
            self.view.progressBar.setRange(0, total)
            self.view.progressBar.setValue(current)
        self.view.statusLabel.setText(message)
    
    def on_geojson_conversion_done(self, output_file_path):
        """
        Handle completion of GeoJSON conversion.
        
        Parameters
        ----------
        output_file_path : str
            Path to created CSV file.
        """
        self.view.progressBar.setRange(0, 1)
        self.view.progressBar.setValue(1)
        self.view.statusLabel.setText("Konvertierung abgeschlossen")
        self.load_csv(output_file_path)
        self.view.show_message("Erfolg", f"CSV-Datei wurde erfolgreich erstellt:\n{output_file_path}")
    
    def on_geojson_conversion_error(self, error_message):
        """
        Handle error during GeoJSON conversion.
        
        Parameters
        ----------
        error_message : str
            Error message.
        """
        self.view.progressBar.setRange(0, 1)
        self.view.progressBar.setValue(0)
        self.view.statusLabel.setText("Fehler bei der Konvertierung")
        self.view.show_error_message("Fehler", error_message)

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
        
        # Automatically reload the updated CSV file to show the new coordinates
        if fname and os.path.exists(fname):
            self.load_csv(fname)
            # Update the progress tracker to refresh CSV status (should now show "mit Koordinaten")
            self.update_progress_tracker()
            self.view.show_message("Erfolg", "Geocoding abgeschlossen. CSV-Datei wurde automatisch aktualisiert.")

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

    def check_network_dimensioned(self, network_file_path):
        """
        Check if network GeoJSON has state set to "dimensioned".
        
        Parameters
        ----------
        network_file_path : str
            Path to Wärmenetz.geojson file.
            
        Returns
        -------
        bool
            True if network is dimensioned, False otherwise.
        """
        if not os.path.exists(network_file_path):
            return False
            
        try:
            from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema
            
            geojson = NetworkGeoJSONSchema.import_from_file(network_file_path)
            
            # Check metadata for state == "dimensioned"
            metadata = geojson.get('metadata', {})
            state = metadata.get('state', '')
            return state == 'dimensioned'
            
        except Exception as e:
            print(f"Fehler beim Prüfen des Dimensionierungsstatus: {e}")
            return False

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
            
            # Update CSV creation and geocoding status for first step
            if os.path.exists(csv_file_path):
                first_step['csv_creation_status'] = 'completed'
                # Check if CSV has coordinates (UTM_X and UTM_Y columns)
                if csv_status == 'mit Koordinaten':
                    first_step['geocoding_status'] = 'completed'
                elif csv_status == 'ist vorhanden':
                    first_step['geocoding_status'] = 'pending'
                else:
                    first_step['geocoding_status'] = 'not_applicable'
            else:
                first_step['csv_creation_status'] = 'pending'
                first_step['geocoding_status'] = 'not_applicable'
            
            # Update all process steps
            for step in self.process_steps:
                full_paths = [os.path.join(base_path, path) for path in step['required_files']]
                generated_files = [file for file in full_paths if os.path.exists(file)]
                
                # Special check for dimensioned network flag in Wärmenetz.geojson
                if step.get('check_dimensioned_network', False):
                    network_file = os.path.join(base_path, "Wärmenetz\\Wärmenetz.geojson")
                    network_dimensioned = self.check_network_dimensioned(network_file)
                    
                    if not network_dimensioned:
                        # Add virtual missing file indicator
                        step['missing_files'] = [path for path in full_paths if not os.path.exists(path)]
                        step['missing_files'].append("Wärmenetz\\Wärmenetz.geojson (nicht dimensioniert)")
                        step['completed'] = False
                    else:
                        step['missing_files'] = [path for path in full_paths if not os.path.exists(path)]
                        step['completed'] = len(step['missing_files']) == 0
                else:
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

        # Status label for operations
        self.statusLabel = QLabel("")
        self.statusLabel.setStyleSheet("padding: 5px; color: #666666;")
        self.rightLayout.addWidget(self.statusLabel)

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
        addRowAction = QAction("Gebäude hinzufügen", self)
        deleteRowAction = QAction("Gebäude löschen", self)
        duplicateRowAction = QAction("Gebäude duplizieren", self)

        contextMenu.addAction(addRowAction)
        contextMenu.addAction(deleteRowAction)
        contextMenu.addAction(duplicateRowAction)
        
        addRowAction.triggered.connect(self.add_row)
        deleteRowAction.triggered.connect(self.delete_row)
        duplicateRowAction.triggered.connect(self.duplicate_row)

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
            self.show_error_message("Warnung", "Bitte wählen Sie ein Gebäude zum Löschen aus.")

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
            self.show_error_message("Warnung", "Bitte wählen Sie ein Gebäude zum Duplizieren aus.")

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