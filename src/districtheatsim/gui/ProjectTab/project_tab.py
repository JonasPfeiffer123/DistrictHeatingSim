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

from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QTableWidgetItem, QWidget, QVBoxLayout, 
                             QMenuBar, QAction, QProgressBar, QLabel, QTableWidget, QHBoxLayout, QPushButton, 
                             QFileSystemModel, QTreeView, QSplitter, QMessageBox, QDialog, QLineEdit, QDialogButtonBox, 
                             QMenu, QGridLayout)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant

from gui.threads import GeocodingThread

class RowInputDialog(QDialog):
    def __init__(self, headers, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neue Zeile hinzufügen")
        self.layout = QGridLayout(self)
        self.fields = {}

        # Erzeuge die Eingabefelder mit Labels
        for i, header in enumerate(headers):
            label = QLabel(header)
            lineEdit = QLineEdit()
            lineEdit.setPlaceholderText(f"Geben Sie {header} ein")
            self.layout.addWidget(label, i, 0)
            self.layout.addWidget(lineEdit, i, 1)
            self.fields[header] = lineEdit

        # Dialog-Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(buttonBox, len(headers), 0, 1, 2)

    def get_input_data(self):
        return {header: field.text() for header, field in self.fields.items()}
    
class OSMImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OSM-Daten importieren")
        self.layout = QGridLayout(self)
        self.fields = {}

        # Definiere die Standardwerte für die Felder
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

        # Erzeuge die Eingabefelder mit Labels und Standardwerten
        for i, (header, value) in enumerate(self.default_values.items()):
            label = QLabel(header)
            lineEdit = QLineEdit(value)
            lineEdit.setPlaceholderText(f"Geben Sie {header} ein")
            self.layout.addWidget(label, i, 0)
            self.layout.addWidget(lineEdit, i, 1)
            self.fields[header] = lineEdit

        # Dialog-Buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(buttonBox, len(self.default_values), 0, 1, 2)

    def get_input_data(self):
        return {header: field.text() for header, field in self.fields.items()}

class ProjectModel:
    def __init__(self):
        self.base_path = None
        self.current_file_path = ''
        self.layers = {}

    def set_base_path(self, base_path):
        self.base_path = base_path

    def get_base_path(self):
        return self.base_path

    def load_csv(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter=';')
            headers = next(reader)
            data = [row for row in reader]
        return headers, data

    def save_csv(self, file_path, headers, data):
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(headers)
            writer.writerows(data)

    def create_csv(self, file_path, headers, default_data):
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(headers)
            writer.writerow(default_data)

    def create_csv_from_geojson(self, geojson_file_path, output_file_path, default_values):
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
    def __init__(self, model, view, data_manager):
        self.model = model
        self.view = view
        self.data_manager = data_manager

        # Connect to the data_manager's signal to update the base path
        self.data_manager.project_folder_changed.connect(self.on_project_folder_changed)

        self.view.treeView.doubleClicked.connect(self.on_tree_view_double_clicked)
        self.view.createCSVAction.triggered.connect(self.create_csv)
        self.view.openAction.triggered.connect(self.open_csv)
        self.view.saveAction.triggered.connect(self.save_csv)
        self.view.createCSVfromgeojsonAction.triggered.connect(self.create_csv_from_geojson)
        self.view.downloadAction.triggered.connect(self.open_geocode_addresses_dialog)

        # Initialize the base path
        self.on_project_folder_changed(self.data_manager.project_folder)

    def on_project_folder_changed(self, path):
        self.model.set_base_path(path)
        self.view.update_path_label(path)
        self.view.treeView.setRootIndex(self.view.treeView.model().index(path))

    def on_tree_view_double_clicked(self, index):
        file_path = self.view.get_selected_file_path(index)
        if file_path.endswith('.csv'):
            self.load_csv(file_path)
        # if file_path.endswith('.geojson'): ... etc could be added here

    def open_csv(self):
        fname, _ = QFileDialog.getOpenFileName(self.view, 'CSV öffnen', self.model.get_base_path(), 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.load_csv(fname)

    def load_csv(self, file_path):
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
        headers = [self.view.csvTable.horizontalHeaderItem(i).text() for i in range(self.view.csvTable.columnCount())]
        data = [[self.view.csvTable.item(row, column).text() if self.view.csvTable.item(row, column) else '' 
                for column in range(self.view.csvTable.columnCount())] for row in range(self.view.csvTable.rowCount())]
        file_path = self.model.current_file_path
        if file_path:
            self.model.save_csv(file_path, headers, data)
        else:
            self.view.show_error_message("Warnung", "Es wurde keine Datei zum Speichern ausgewählt oder erstellt.")

    def add_row(self):
        self.view.csvTable.insertRow(self.view.csvTable.rowCount())

    def del_row(self):
        currentRow = self.view.csvTable.currentRow()
        if currentRow > -1:
            self.view.csvTable.removeRow(currentRow)
        else:
            self.view.show_error_message("Warnung", "Bitte wählen Sie eine Zeile zum Löschen aus.")

    def create_csv(self):
        headers = ['Land', 'Bundesland', 'Stadt', 'Adresse', 'Wärmebedarf', 'Gebäudetyp', "Subtyp", 'WW_Anteil', 'Typ_Heizflächen', 'VLT_max', 'Steigung_Heizkurve', 'RLT_max', "Normaußentemperatur"]
        default_data = ['']*len(headers)
        fname, _ = QFileDialog.getSaveFileName(self.view, 'Gebäude-CSV erstellen', self.model.get_base_path(), 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.model.create_csv(fname, headers, default_data)
            self.load_csv(fname)

    def create_csv_from_geojson(self):
        geojson_file_path, _ = QFileDialog.getOpenFileName(self.view, "geoJSON auswählen", self.model.get_base_path(), "All Files (*)")
        if geojson_file_path:
            dialog = OSMImportDialog(self.view)
            if dialog.exec_() == QDialog.Accepted:
                # Werte aus dem Dialog abrufen
                default_values = dialog.get_input_data()

                try:
                    output_file_path = self.model.get_resource_path(f"Gebäudedaten/generated_building_data.csv")
                    self.model.create_csv_from_geojson(geojson_file_path, output_file_path, default_values)
                    self.load_csv(output_file_path)
                except Exception as e:
                    self.view.show_error_message("Fehler", str(e))

    def open_geocode_addresses_dialog(self):
        fname, _ = QFileDialog.getOpenFileName(self.view, 'CSV-Koordinaten laden', self.model.get_base_path(), 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.geocode_addresses(fname)

    def geocode_addresses(self, inputfilename):
        # Assuming GeocodingThread is correctly implemented elsewhere
        if hasattr(self, 'geocodingThread') and self.geocodingThread.isRunning():
            self.geocodingThread.terminate()
            self.geocodingThread.wait()
        self.geocodingThread = GeocodingThread(inputfilename)
        self.geocodingThread.calculation_done.connect(self.on_geocode_done)
        self.geocodingThread.calculation_error.connect(self.on_geocode_error)
        self.geocodingThread.start()
        self.view.progressBar.setRange(0, 0)

    def on_geocode_done(self, fname):
        self.view.progressBar.setRange(0, 1)

    def on_geocode_error(self, error_message):
        self.view.show_error_message("Fehler beim Geocoding", error_message)
        self.view.progressBar.setRange(0, 1)

# Vorschlag zur UI-Verbesserung und Erweiterung
class ProjectTabView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        mainLayout = QVBoxLayout()
        splitter = QSplitter()

        # Linker Bereich - Datei-Baum
        leftLayout = QVBoxLayout()
        self.pathLabel = QLabel("Projektordner: Kein Ordner ausgewählt")
        leftLayout.addWidget(self.pathLabel)
        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.treeView = QTreeView()
        self.treeView.setModel(self.model)
        leftWidget = QWidget()
        leftWidget.setLayout(leftLayout)
        leftLayout.addWidget(self.treeView)
        splitter.addWidget(leftWidget)

        # Rechter Bereich - Datei-Interaktion
        rightLayout = QVBoxLayout()

        # Menüleiste
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
        rightLayout.addWidget(self.menuBar)

        # CSV-Tabelle mit Inline-Bearbeitung und Kontextmenü
        self.csvTable = QTableWidget()
        self.csvTable.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.csvTable.setContextMenuPolicy(Qt.CustomContextMenu)
        self.csvTable.customContextMenuRequested.connect(self.show_context_menu)
        rightLayout.addWidget(self.csvTable)

        # Fortschrittsanzeige
        self.progressBar = QProgressBar(self)
        rightLayout.addWidget(self.progressBar)
        rightWidget = QWidget()
        rightWidget.setLayout(rightLayout)
        splitter.addWidget(rightWidget)
        splitter.setStretchFactor(1, 2)

        mainLayout.addWidget(splitter)
        self.setLayout(mainLayout)

    def show_context_menu(self, position):
        contextMenu = QMenu(self)
        addRowAction = QAction("Zeile hinzufügen", self)
        deleteRowAction = QAction("Zeile löschen", self)
        duplicateRowAction = QAction("Zeile duplizieren", self)  # Neue Aktion zum Duplizieren

        contextMenu.addAction(addRowAction)
        contextMenu.addAction(deleteRowAction)
        contextMenu.addAction(duplicateRowAction)  # Aktion dem Menü hinzufügen
        
        addRowAction.triggered.connect(self.add_row)
        deleteRowAction.triggered.connect(self.delete_row)
        duplicateRowAction.triggered.connect(self.duplicate_row)  # Verbindung der neuen Aktion

        contextMenu.exec_(self.csvTable.viewport().mapToGlobal(position))

    def add_row(self):
        headers = [self.csvTable.horizontalHeaderItem(i).text() for i in range(self.csvTable.columnCount())]
        dialog = RowInputDialog(headers, self)
        if dialog.exec_() == QDialog.Accepted:
            row_data = dialog.get_input_data()
            row = self.csvTable.rowCount()
            self.csvTable.insertRow(row)
            for i, header in enumerate(headers):
                self.csvTable.setItem(row, i, QTableWidgetItem(row_data[header]))

    def delete_row(self):
        currentRow = self.csvTable.currentRow()
        if currentRow > -1:
            self.csvTable.removeRow(currentRow)
        else:
            self.show_error_message("Warnung", "Bitte wählen Sie eine Zeile zum Löschen aus.")

    def duplicate_row(self):
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
        self.pathLabel.setText(f"Projektordner: {new_base_path}")

    def get_selected_file_path(self, index):
        return self.model.filePath(index)

    def show_error_message(self, title, message):
        QMessageBox.critical(self, title, message)

class ProjectTab(QMainWindow):
    def __init__(self, data_manager, parent=None):
        super().__init__()
        self.setWindowTitle("Project Tab Example")
        self.setGeometry(100, 100, 800, 600)

        self.model = ProjectModel()
        self.view = ProjectTabView()
        self.presenter = ProjectPresenter(self.model, self.view, data_manager)

        self.setCentralWidget(self.view)

#if __name__ == '__main__':
#    app = QApplication([])
#    data_manager = DataManager()  # This would come from the main GUI context
#    window = ProjectTab(data_manager)
#    window.show()
#    app.exec_()