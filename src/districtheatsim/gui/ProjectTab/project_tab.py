"""
Filename: project_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-27
Description: Contains the ProjectTab as MVP model.
"""

import os
import sys
import csv
import json

from PyQt5.QtWidgets import (QMainWindow, QFileDialog, QTableWidgetItem, QWidget, QVBoxLayout, 
                             QMenuBar, QAction, QProgressBar, QLabel, QTableWidget, QFileSystemModel, 
                             QTreeView, QSplitter, QMessageBox, QDialog, QLineEdit, QDialogButtonBox, 
                             QMenu, QGridLayout)
from PyQt5.QtCore import Qt, QTimer

from gui.VisualizationTab.net_generation_threads import GeocodingThread

class RowInputDialog(QDialog):
    """
    Dialog for adding a new row in a table.

    Args:
        headers (list): List of headers for the table columns.
        parent (QWidget, optional): The parent widget. Defaults to None.
    """
    def __init__(self, headers, parent=None):
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
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(buttonBox, len(headers), 0, 1, 2)

    def get_input_data(self):
        """
        Retrieve the input data from the dialog.

        Returns:
            dict: A dictionary mapping headers to input field values.
        """
        return {header: field.text() for header, field in self.fields.items()}
    
class OSMImportDialog(QDialog):
    """
    Dialog for importing OSM data with user-defined default values.

    Args:
        parent (QWidget, optional): The parent widget. Defaults to None.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OSM-Daten importieren")
        self.layout = QGridLayout(self)
        self.fields = {}

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

        # Create input fields with labels and default values
        for i, (header, value) in enumerate(self.default_values.items()):
            label = QLabel(header)
            lineEdit = QLineEdit(value)
            lineEdit.setPlaceholderText(f"Geben Sie {header} ein")
            self.layout.addWidget(label, i, 0)
            self.layout.addWidget(lineEdit, i, 1)
            self.fields[header] = lineEdit

        # Dialog buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(buttonBox, len(self.default_values), 0, 1, 2)

    def get_input_data(self):
        """
        Retrieve the input data from the dialog.

        Returns:
            dict: A dictionary mapping headers to input field values.
        """
        return {header: field.text() for header, field in self.fields.items()}

class ProjectModel:
    """
    Model class for managing project data.

    This class handles the loading, saving, and processing of CSV and GeoJSON files.

    Attributes:
        base_path (str): The base path of the project.
        current_file_path (str): The current file path being worked on.
        layers (dict): Dictionary of layers within the project.
    """
    def __init__(self):
        self.base_path = None
        self.current_file_path = ''
        self.layers = {}

    def set_base_path(self, base_path):
        """
        Set the base path of the project.

        Args:
            base_path (str): The base path of the project.
        """
        self.base_path = base_path

    def get_base_path(self):
        """
        Get the base path of the project.

        Returns:
            str: The base path.
        """
        return self.base_path

    def load_csv(self, file_path):
        """
        Load a CSV file.

        Args:
            file_path (str): The path to the CSV file.

        Returns:
            tuple: A tuple containing headers (list) and data (list of lists).
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter=';')
            headers = next(reader)
            data = [row for row in reader]
        return headers, data

    def save_csv(self, file_path, headers, data):
        """
        Save data to a CSV file.

        Args:
            file_path (str): The path to the CSV file.
            headers (list): The headers for the CSV file.
            data (list of lists): The data to save.
        """
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(headers)
            writer.writerows(data)

    def create_csv(self, file_path, headers, default_data):
        """
        Create a new CSV file with default data.

        Args:
            file_path (str): The path to the CSV file.
            headers (list): The headers for the CSV file.
            default_data (list): The default data to write in the CSV file.
        """
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(headers)
            writer.writerow(default_data)

    def create_csv_from_geojson(self, geojson_file_path, output_file_path, default_values):
        """
        Create a CSV file from a GeoJSON file with default values.

        Args:
            geojson_file_path (str): The path to the GeoJSON file.
            output_file_path (str): The path to save the CSV file.
            default_values (dict): A dictionary of default values to populate in the CSV file.

        Returns:
            str: The path to the output CSV file.
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
        Calculate the centroid of given coordinates.

        Args:
            coordinates (list): A list of coordinates.

        Returns:
            tuple: The centroid coordinates as a tuple (x, y).
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
        Get the absolute path to the resource, works for dev and for PyInstaller.

        Args:
            relative_path (str): The relative path to the resource.

        Returns:
            str: The absolute path to the resource.
        """
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

class ProjectPresenter:
    """
    Presenter class for managing the interaction between the ProjectModel and ProjectTabView.

    Args:
        model (ProjectModel): The data model for the project.
        view (ProjectTabView): The view for the project tab.
        data_manager (DataManager): Manages the data and state of the application.
    """
    def __init__(self, model, view, folder_manager, data_manager, config_manager):
        self.model = model
        self.view = view
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        # Define process steps
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
            },
            {
                "name": "Schritt 6: Dokumentation erstellen",
                "description": "Erstellen Sie die endgültige Dokumentation und PDF-Berichte.",
                "required_files": [
                    "Ergebnisse\\Ergebnisse.pdf"
                ]
            }
        ]

        # Connect to the data_manager's signal to update the base path
        self.folder_manager.project_folder_changed.connect(self.on_variant_folder_changed)

        # Connect view signals to presenter methods
        self.view.treeView.doubleClicked.connect(self.on_tree_view_double_clicked)
        self.view.createCSVAction.triggered.connect(self.create_csv)
        self.view.openAction.triggered.connect(self.open_csv)
        self.view.saveAction.triggered.connect(self.save_csv)
        self.view.createCSVfromgeojsonAction.triggered.connect(self.create_csv_from_geojson)
        self.view.downloadAction.triggered.connect(self.open_geocode_addresses_dialog)

        # Initialize the base path
        self.on_variant_folder_changed(self.folder_manager.variant_folder)
        self.update_progress_tracker()

        # Optional: Set up a timer to update the progress periodically
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress_tracker)
        self.timer.start(50000)  # Update every 50 seconds

    def on_variant_folder_changed(self, path):
        """
        Handle the event when the project folder changes.

        Args:
            path (str): The new project folder path.
        """
        self.model.set_base_path(path)
        self.view.update_path_label(path)
        self.view.treeView.setRootIndex(self.view.treeView.model().index(os.path.dirname(path)))
        self.update_progress_tracker()

    def on_tree_view_double_clicked(self, index):
        """
        Handle the event when an item in the tree view is double-clicked.
        """
        file_path = self.view.get_selected_file_path(index)
        
        if os.path.isdir(file_path):
            # Prüfe, ob der Ordner eine Variante oder ein Projekt ist
            if "Variante" in os.path.basename(file_path):
                # Variante öffnen
                self.folder_manager.set_variant_folder(file_path)
            else:
                # Projekt öffnen und die Varianten darin anzeigen
                self.folder_manager.set_project_folder(file_path)
        elif file_path.endswith('.csv'):
            # CSV-Datei laden
            self.load_csv(file_path)

    def open_csv(self):
        """
        Open a CSV file and load it into the table.
        """
        fname, _ = QFileDialog.getOpenFileName(self.view, 'CSV öffnen', self.model.get_base_path(), 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.load_csv(fname)

    def load_csv(self, file_path):
        """
        Load a CSV file and display its contents in the table.

        Args:
            file_path (str): The path to the CSV file.
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

    def save_csv(self):
        """
        Save the current table data to a CSV file.
        """
        headers = [self.view.csvTable.horizontalHeaderItem(i).text() for i in range(self.view.csvTable.columnCount())]
        data = [[self.view.csvTable.item(row, column).text() if self.view.csvTable.item(row, column) else '' 
                for column in range(self.view.csvTable.columnCount())] for row in range(self.view.csvTable.rowCount())]
        file_path = self.model.current_file_path
        if file_path:
            self.model.save_csv(file_path, headers, data)
        else:
            self.view.show_error_message("Warnung", "Es wurde keine Datei zum Speichern ausgewählt oder erstellt.")

    def add_row(self):
        """
        Add a new empty row to the table.
        """
        self.view.csvTable.insertRow(self.view.csvTable.rowCount())

    def del_row(self):
        """
        Delete the currently selected row from the table.
        """
        currentRow = self.view.csvTable.currentRow()
        if currentRow > -1:
            self.view.csvTable.removeRow(currentRow)
        else:
            self.view.show_error_message("Warnung", "Bitte wählen Sie eine Zeile zum Löschen aus.")

    def create_csv(self):
        """
        Create a new CSV file with default headers and data.
        """
        headers = ['Land', 'Bundesland', 'Stadt', 'Adresse', 'Wärmebedarf', 'Gebäudetyp', "Subtyp", 'WW_Anteil', 'Typ_Heizflächen', 'VLT_max', 'Steigung_Heizkurve', 'RLT_max', "Normaußentemperatur"]
        default_data = ['']*len(headers)
        fname, _ = QFileDialog.getSaveFileName(self.view, 'Gebäude-CSV erstellen', self.model.get_base_path(), 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.model.create_csv(fname, headers, default_data)
            self.load_csv(fname)

    def create_csv_from_geojson(self):
        """
        Create a CSV file from GeoJSON data with user-defined default values.
        """
        geojson_file_path, _ = QFileDialog.getOpenFileName(self.view, "geoJSON auswählen", self.model.get_base_path(), "All Files (*)")
        if geojson_file_path:
            dialog = OSMImportDialog(self.view)
            if dialog.exec_() == QDialog.Accepted:
                # Get values from the dialog
                default_values = dialog.get_input_data()

                try:
                    output_file_path = self.config_manager.get_resource_path("OSM_building_data_path")
                    self.model.create_csv_from_geojson(geojson_file_path, output_file_path, default_values)
                    self.load_csv(output_file_path)
                except Exception as e:
                    self.view.show_error_message("Fehler", str(e))

    def open_geocode_addresses_dialog(self):
        """
        Open a dialog to select a CSV file for geocoding addresses.
        """
        fname, _ = QFileDialog.getOpenFileName(self.view, 'CSV-Koordinaten laden', self.model.get_base_path(), 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.geocode_addresses(fname)

    def geocode_addresses(self, inputfilename):
        """
        Start a geocoding thread to process the selected CSV file.

        Args:
            inputfilename (str): The path to the CSV file for geocoding.
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
        Handle the completion of the geocoding process.

        Args:
            fname (str): The filename of the geocoded data.
        """
        self.view.progressBar.setRange(0, 1)

    def on_geocode_error(self, error_message):
        """
        Handle errors that occur during the geocoding process.

        Args:
            error_message (str): The error message to display.
        """
        self.view.show_error_message("Fehler beim Geocoding", error_message)
        self.view.progressBar.setRange(0, 1)

    def update_progress_tracker(self):
        """
        Update the progress based on the number of detected files.
        """
        # Check base path of the project
        base_path = self.model.get_base_path()

        # Create list of full paths to check file existence and map to process steps
        for step in self.process_steps:
            full_paths = [os.path.join(base_path, path) for path in step['required_files']]
            generated_files = [file for file in full_paths if os.path.exists(file)]
            step['completed'] = len(generated_files) == len(full_paths)
            step['missing_files'] = [path for path in full_paths if not os.path.exists(path)]

        # Calculate overall progress
        total_steps = len(self.process_steps)
        completed_steps = sum(1 for step in self.process_steps if step['completed'])
        overall_progress = (completed_steps / total_steps) * 100

        # Update the view with the current progress and steps
        self.view.update_progress(overall_progress)
        self.view.update_process_steps(self.process_steps)

class ProjectTabView(QWidget):
    """
    View class for the Project Tab.

    This class defines the user interface elements and layout for interacting with the project data.

    Args:
        parent (QWidget, optional): The parent widget. Defaults to None.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        """
        Initialize the user interface.
        """
        mainLayout = QVBoxLayout()
        splitter = QSplitter()

        # Left area - File tree
        self.leftLayout = QVBoxLayout()
        self.pathLabel = QLabel("Projektordner: Kein Ordner ausgewählt")
        self.leftLayout.addWidget(self.pathLabel)
        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.treeView = QTreeView()
        self.treeView.setModel(self.model)
        leftWidget = QWidget()
        leftWidget.setLayout(self.leftLayout)
        self.leftLayout.addWidget(self.treeView)

        # Add progress bar and label under the tree view
        self.progressLabel = QLabel("Projektfortschritt:")
        self.leftLayout.addWidget(self.progressLabel)

        self.projectProgressBar = QProgressBar(self)
        self.leftLayout.addWidget(self.projectProgressBar)

        self.processStepsLayout = QVBoxLayout()
        self.leftLayout.addLayout(self.processStepsLayout)

        splitter.addWidget(leftWidget)

        # Right area - File interaction
        self.rightLayout = QVBoxLayout()

        # Menu bar
        self.initMenuBar()

        # CSV table with inline editing and context menu
        self.csvTable = QTableWidget()
        self.csvTable.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.csvTable.setContextMenuPolicy(Qt.CustomContextMenu)
        self.csvTable.customContextMenuRequested.connect(self.show_context_menu)
        self.rightLayout.addWidget(self.csvTable)

        # Progress bar
        self.progressBar = QProgressBar(self)
        self.rightLayout.addWidget(self.progressBar)
        rightWidget = QWidget()
        rightWidget.setLayout(self.rightLayout)
        splitter.addWidget(rightWidget)
        splitter.setStretchFactor(1, 2)

        mainLayout.addWidget(splitter)
        self.setLayout(mainLayout)

    def initMenuBar(self):
        """
        Initialize the menu bar with actions.
        """
        self.menuBar = QMenuBar(self)
        self.menuBar.setFixedHeight(30)

        fileMenu = self.menuBar.addMenu('Datei')
        self.createCSVAction = QAction('CSV erstellen', self)
        self.createCSVfromgeojsonAction = QAction('Gebäude-CSV aus OSM-geojson erstellen', self)
        self.downloadAction = QAction('Adressdaten geocodieren', self)
        self.openAction = QAction('CSV laden', self)
        self.saveAction = QAction('CSV speichern', self)

        fileMenu.addAction(self.createCSVAction)
        fileMenu.addAction(self.openAction)
        fileMenu.addAction(self.saveAction)
        fileMenu.addAction(self.createCSVfromgeojsonAction)
        fileMenu.addAction(self.downloadAction)

        self.rightLayout.addWidget(self.menuBar)

    def show_context_menu(self, position):
        """
        Show a context menu at the given position in the table.

        Args:
            position (QPoint): The position in the table to show the menu.
        """
        contextMenu = QMenu(self)
        addRowAction = QAction("Zeile hinzufügen", self)
        deleteRowAction = QAction("Zeile löschen", self)
        duplicateRowAction = QAction("Zeile duplizieren", self)  # New action to duplicate

        contextMenu.addAction(addRowAction)
        contextMenu.addAction(deleteRowAction)
        contextMenu.addAction(duplicateRowAction)  # Add action to menu
        
        addRowAction.triggered.connect(self.add_row)
        deleteRowAction.triggered.connect(self.delete_row)
        duplicateRowAction.triggered.connect(self.duplicate_row)  # Connect new action

        contextMenu.exec_(self.csvTable.viewport().mapToGlobal(position))

    def add_row(self):
        """
        Add a new row to the table using a dialog to input data.
        """
        headers = [self.csvTable.horizontalHeaderItem(i).text() for i in range(self.csvTable.columnCount())]
        dialog = RowInputDialog(headers, self)
        if dialog.exec_() == QDialog.Accepted:
            row_data = dialog.get_input_data()
            row = self.csvTable.rowCount()
            self.csvTable.insertRow(row)
            for i, header in enumerate(headers):
                self.csvTable.setItem(row, i, QTableWidgetItem(row_data[header]))

    def delete_row(self):
        """
        Delete the currently selected row from the table.
        """
        currentRow = self.csvTable.currentRow()
        if currentRow > -1:
            self.csvTable.removeRow(currentRow)
        else:
            self.show_error_message("Warnung", "Bitte wählen Sie eine Zeile zum Löschen aus.")

    def duplicate_row(self):
        """
        Duplicate the currently selected row in the table.
        """
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

    def update_path_label(self, new_base_path):
        """
        Update the label displaying the current project folder path.

        Args:
            new_base_path (str): The new base path of the project.
        """
        self.pathLabel.setText(f"Geöffnete Variante: {new_base_path}")

    def get_selected_file_path(self, index):
        """
        Get the file path of the selected item in the tree view.

        Args:
            index (QModelIndex): The index of the selected item.

        Returns:
            str: The file path of the selected item.
        """
        return self.model.filePath(index)

    def show_error_message(self, title, message):
        """
        Display an error message dialog.

        Args:
            title (str): The title of the error message dialog.
            message (str): The error message to display.
        """
        QMessageBox.critical(self, title, message)

    def update_process_steps(self, process_steps):
        """
        Update the process steps layout with the current progress and missing files.
        """
        # Clear the current layout
        for i in reversed(range(self.processStepsLayout.count())): 
            widget = self.processStepsLayout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Add the process steps with status
        for step in process_steps:
            step_label = QLabel(f"{step['name']}: {'Abgeschlossen' if step['completed'] else 'Ausstehend'}")
            self.processStepsLayout.addWidget(step_label)

            if not step['completed']:
                for missing_file in step['missing_files']:
                    missing_file_label = QLabel(f"Fehlende Datei: {missing_file}")
                    missing_file_label.setStyleSheet("color: red;")
                    self.processStepsLayout.addWidget(missing_file_label)

    def update_progress(self, progress):
        """
        Update the progress bar and label with the current progress.
        """
        self.projectProgressBar.setValue(int(progress))
        self.progressLabel.setText(f"Projektfortschritt: {int(progress)}%")

class ProjectTab(QMainWindow):
    """
    Main window class for the Project Tab.

    This class integrates the ProjectModel, ProjectPresenter, and ProjectTabView into a single window.

    Args:
        data_manager (DataManager): Manages the data and state of the application.
        parent (QWidget, optional): The parent widget. Defaults to None.
    """
    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        super().__init__()
        self.setWindowTitle("Project Tab Example")
        self.setGeometry(100, 100, 800, 600)

        self.model = ProjectModel()
        self.view = ProjectTabView()
        self.presenter = ProjectPresenter(self.model, self.view, folder_manager, data_manager, config_manager)

        self.setCentralWidget(self.view)