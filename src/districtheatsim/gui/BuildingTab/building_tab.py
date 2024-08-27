"""
Filename: building_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: Contains the BuildingTab.
"""

import os
import sys
import json
import pandas as pd

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QMessageBox, QApplication, 
                             QMainWindow, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QScrollArea,
                             QMenuBar, QAction, QLineEdit)
from PyQt5.QtCore import pyqtSignal, Qt

from heat_requirement.heat_requirement_calculation_csv import generate_profiles_from_csv
from gui.utilities import CheckableComboBox, convert_to_serializable

class BuildingModel:
    def __init__(self):
        self.base_path = None
        self.data = None
        self.results = None

    def set_base_path(self, base_path):
        self.base_path = base_path

    def get_base_path(self):
        return self.base_path

    def load_csv(self, file_path):
        try:
            self.data = pd.read_csv(file_path, delimiter=';', dtype={'Subtyp': str})
        except Exception as e:
            raise Exception(f"Fehler beim Laden der CSV-Datei: {e}")

    def save_csv(self, file_path):
        if self.data is not None:
            try:
                self.data.to_csv(file_path, index=False, sep=';')
            except Exception as e:
                raise Exception(f"Fehler beim Speichern der CSV-Datei: {e}")

    def load_json(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                self.results = {k: v for k, v in loaded_data.items() if isinstance(v, dict) and 'lastgang_wärme' in v}
        except Exception as e:
            raise Exception(f"Fehler beim Laden der JSON-Datei: {e}")

    def save_json(self, file_path, combined_data):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, indent=4)
        except Exception as e:
            raise Exception(f"Fehler beim Speichern der Ergebnisse: {e}")

    def calculate_heat_demand(self, data, try_filename):
        return generate_profiles_from_csv(data=data, TRY=try_filename, calc_method="Datensatz")

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
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_path, relative_path)
    
class BuildingPresenter:
    def __init__(self, model, view, data_manager, parent=None):
        self.model = model
        self.view = view
        self.data_manager = data_manager
        self.parent = parent

        # Connect to the data_manager's signal to update the base path
        self.data_manager.project_folder_changed.connect(self.update_default_path)

        # Connect UI signals to their respective slots
        self.view.load_csv_signal.connect(self.load_csv)
        self.view.save_csv_signal.connect(self.save_csv)
        self.view.calculate_heat_demand_signal.connect(self.calculate_heat_demand)
        self.view.load_json_signal.connect(self.load_json)
        self.view.update_path_signal.connect(self.update_default_path)

        # Handle combobox changes and plotting
        self.view.data_type_combobox.view().pressed.connect(self.on_combobox_selection_changed)
        self.view.building_combobox.view().pressed.connect(self.on_combobox_selection_changed)

        # Initialize the base path
        self.update_default_path(self.data_manager.project_folder)

    def update_default_path(self, path):
        self.model.set_base_path(path)
        self.view.update_output_path(self.model.get_base_path())

    def load_csv(self, file_path):
        try:
            self.model.load_csv(file_path)
            self.view.populate_table(self.model.data)
        except Exception as e:
            self.view.show_error_message("Fehler", str(e))

    def save_csv(self, file_path):
        try:
            self.model.save_csv(file_path)
            self.view.show_message("Erfolg", f"CSV-Datei wurde in {file_path} gespeichert.")
        except Exception as e:
            self.view.show_error_message("Fehler", str(e))

    def load_json(self, file_path):
        try:
            self.model.load_json(file_path)
            self.view.populate_building_combobox(self.model.results)
            self.view.plot(self.model.results)
        except Exception as e:
            self.view.show_error_message("Fehler", str(e))

    def calculate_heat_demand(self, output_path):
        data = self.view.get_table_data()
        if data.empty:
            self.view.show_error_message("Fehler", "Die Tabelle enthält keine Daten.")
            return

        try:
            try_filename = self.parent.try_filename  # Access try_filename from the parent
            results = self.model.calculate_heat_demand(data, try_filename)
            self.model.results = self.format_results(results, data)
            combined_data = self.combine_data_with_results(data, self.model.results)
            self.model.save_json(output_path, combined_data)
            self.view.show_message("Erfolg", f"Ergebnisse wurden in {output_path} gespeichert.")
            self.view.populate_building_combobox(self.model.results)
            self.view.plot(self.model.results)
        except Exception as e:
            self.view.show_error_message("Fehler", str(e))

    def format_results(self, results, data):
        formatted_results = {}
        for idx in range(len(data)):
            building_id = str(idx)
            formatted_results[building_id] = {
                "zeitschritte": [convert_to_serializable(ts) for ts in results[0]],
                "außentemperatur": results[-1].tolist(),
                "lastgang_wärme": results[1][idx].tolist(),
                "heating_wärme": results[2][idx].tolist(),
                "warmwater_wärme": results[3][idx].tolist(),
                "vorlauftemperatur": results[4][idx].tolist(),
                "rücklauftemperatur": results[5][idx].tolist(),
                "heizlast": results[-2].tolist(),
            }
            for key, value in data.iloc[idx].items():
                formatted_results[building_id][key] = convert_to_serializable(value)
        return formatted_results

    def combine_data_with_results(self, data, results):
        data.reset_index(drop=True, inplace=True)
        data_dict = data.applymap(convert_to_serializable).to_dict(orient='index')
        combined_data = {str(idx): {**data_dict[idx], **results[str(idx)]} for idx in range(len(data))}
        return combined_data

    def on_combobox_selection_changed(self):
        self.view.plot(self.model.results)

class BuildingTabView(QWidget):
    load_csv_signal = pyqtSignal(str)
    save_csv_signal = pyqtSignal(str)
    calculate_heat_demand_signal = pyqtSignal(str)
    load_json_signal = pyqtSignal(str)
    update_path_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        container_widget = QWidget()
        scroll_area.setWidget(container_widget)

        self.main_layout = QVBoxLayout(container_widget)
        self.initMenuBar()

        self.table_widget = QTableWidget(self)
        self.main_layout.addWidget(self.table_widget)

        # Add output path widgets
        self.output_path_layout = QVBoxLayout()
        self.output_path_label = QLabel("Output JSON File:")
        self.output_path_edit = QLineEdit(f"")
        self.output_path_button = QPushButton("Browse")
        self.output_path_button.clicked.connect(self.browseOutputFile)

        self.output_path_layout.addWidget(self.output_path_label)
        self.output_path_layout.addWidget(self.output_path_edit)
        self.output_path_layout.addWidget(self.output_path_button)
        self.main_layout.addLayout(self.output_path_layout)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(400, 400)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.main_layout.addWidget(self.canvas)
        self.main_layout.addWidget(self.toolbar)

        self.data_type_combobox = CheckableComboBox(self)
        self.data_type_combobox.addItem("Heat Demand")
        self.data_type_combobox.addItem("Heating Demand")
        self.data_type_combobox.addItem("Warmwater Demand")
        self.data_type_combobox.addItem("Supply Temperature")
        self.data_type_combobox.addItem("Return Temperature")

        item = self.data_type_combobox.model().item(0)
        item.setCheckState(Qt.Checked)
        
        self.building_combobox = CheckableComboBox(self)
        
        self.main_layout.addWidget(QLabel("Select Data Types"))
        self.main_layout.addWidget(self.data_type_combobox)
        self.main_layout.addWidget(QLabel("Select Buildings"))
        self.main_layout.addWidget(self.building_combobox)

        container_widget.setLayout(self.main_layout)
        final_layout = QVBoxLayout(self)
        final_layout.addWidget(scroll_area)
        self.setLayout(final_layout)

    def initMenuBar(self):
        self.menubar = QMenuBar(self)
        self.menubar.setFixedHeight(30)

        load_csv_action = QAction("CSV laden", self)
        load_csv_action.triggered.connect(self.loadCsvFile)
        self.menubar.addAction(load_csv_action)

        save_csv_action = QAction("CSV speichern", self)
        save_csv_action.triggered.connect(self.saveCsvFile)
        self.menubar.addAction(save_csv_action)

        calculate_action = QAction("Gebäudelastgänge berechnen", self)
        calculate_action.triggered.connect(self.calculateHeatDemand)
        self.menubar.addAction(calculate_action)

        load_json_action = QAction("Gebäudelastgänge laden", self)
        load_json_action.triggered.connect(self.loadJsonFile)
        self.menubar.addAction(load_json_action)

        self.main_layout.setMenuBar(self.menubar)

    def browseOutputFile(self):
        fname, _ = QFileDialog.getSaveFileName(self, 'Save JSON File As', f"{self.output_path_edit.text()}", 'JSON Files (*.json);;All Files (*)')
        if fname:
            self.output_path_edit.setText(fname)

    def loadCsvFile(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Select CSV File', f"{self.output_path_edit.text()}", 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.load_csv_signal.emit(fname)

    def saveCsvFile(self):
        fname, _ = QFileDialog.getSaveFileName(self, 'Save CSV File As', f"{self.output_path_edit.text()}", 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.save_csv_signal.emit(fname)

    def loadJsonFile(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Select JSON File', f"{self.output_path_edit.text()}", 'JSON Files (*.json);;All Files (*)')
        if fname:
            self.load_json_signal.emit(fname)

    def calculateHeatDemand(self):
        output_path = self.output_path_edit.text()
        self.calculate_heat_demand_signal.emit(output_path)

    def populate_table(self, data):
        self.table_widget.setColumnCount(len(data.columns))
        self.table_widget.setRowCount(len(data.index))
        self.table_widget.setHorizontalHeaderLabels(data.columns)

        for i in range(len(data.index)):
            for j in range(len(data.columns)):
                if data.columns[j] in ["Gebäudetyp", "Subtyp"]:
                    combobox = QComboBox()
                    combobox.addItem(str(data.iat[i, j]))
                    self.table_widget.setCellWidget(i, j, combobox)
                else:
                    self.table_widget.setItem(i, j, QTableWidgetItem(str(data.iat[i, j])))

        self.table_widget.resizeColumnsToContents()
        self.table_widget.resizeRowsToContents()
        self.table_widget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def get_table_data(self):
        rows = self.table_widget.rowCount()
        columns = self.table_widget.columnCount()
        data = []

        for row in range(rows):
            row_data = []
            for column in range(columns):
                if self.table_widget.cellWidget(row, column):
                    row_data.append(self.table_widget.cellWidget(row, column).currentText())
                else:
                    item = self.table_widget.item(row, column)
                    if item and item.text():
                        row_data.append(item.text())
                    else:
                        row_data.append(None)
            data.append(row_data)

        df = pd.DataFrame(data, columns=[self.table_widget.horizontalHeaderItem(i).text() for i in range(columns)])
        if 'Subtyp' in df.columns:
            df['Subtyp'] = df['Subtyp'].astype(str)
        return df

    def populate_building_combobox(self, results):
        self.building_combobox.clear()
        for key in results.keys():
            self.building_combobox.addItem(f'Building {key}')
            item = self.building_combobox.model().item(self.building_combobox.count() - 1, 0)
            item.setCheckState(Qt.Checked)

    def plot(self, results=None):
        if results is None:
            return

        self.figure.clear()
        ax1 = self.figure.add_subplot(111)
        ax2 = ax1.twinx()

        selected_data_types = self.data_type_combobox.checkedItems()
        selected_buildings = self.building_combobox.checkedItems()

        for building in selected_buildings:
            key = building.split()[-1]
            value = results[key]

            if "Heat Demand" in selected_data_types:
                ax1.plot(value["lastgang_wärme"], label=f'Building {key} Heat Demand')
            if "Heating Demand" in selected_data_types:
                ax1.plot(value["heating_wärme"], label=f'Building {key} Heating Demand', linestyle='--')
            if "Warmwater Demand" in selected_data_types:
                ax1.plot(value["warmwater_wärme"], label=f'Building {key} Warmwater Demand', linestyle=':')
            if "Supply Temperature" in selected_data_types:
                ax2.plot(value["vorlauftemperatur"], label=f'Building {key} Supply Temp', linestyle='-.')
            if "Return Temperature" in selected_data_types:
                ax2.plot(value["rücklauftemperatur"], label=f'Building {key} Return Temp', linestyle='-.')

        ax1.set_xlabel('Time (hours)')
        ax1.set_ylabel('Heat Demand (W)')
        ax2.set_ylabel('Temperature (°C)')
        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')
        ax1.grid()

        self.canvas.draw()

    def show_error_message(self, title, message):
        QMessageBox.critical(self, title, message)

    def show_message(self, title, message):
        QMessageBox.information(self, title, message)

    def update_output_path(self, path):
        self.output_path_edit.setText(f"{path}/Lastgang/Gebäude Lastgang.json")

class BuildingTab(QMainWindow):
    def __init__(self, data_manager, parent=None):
        super().__init__()
        self.setWindowTitle("Building Tab Example")
        self.setGeometry(100, 100, 800, 600)

        self.model = BuildingModel()
        self.view = BuildingTabView()
        self.presenter = BuildingPresenter(self.model, self.view, data_manager, parent)

        self.setCentralWidget(self.view)