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
from districtheatsim.gui.utilities import CheckableComboBox, convert_to_serializable

def get_resource_path(relative_path):
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

class BuildingTab(QWidget):
    """
    The BuildingTab widget for managing building data and displaying results.
    """
    
    data_added = pyqtSignal(object)

    def __init__(self, data_manager=None, parent=None):
        """
        Initializes the BuildingTab.
        
        Args:
            data_manager: The data manager.
            parent: The parent widget.
        """
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent

        self.initUI()

        if self.data_manager:
            self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
            self.updateDefaultPath(self.data_manager.project_folder)

    def initUI(self):
        """
        Initializes the UI elements of the BuildingTab.
        """
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

        self.data_type_combobox.view().pressed.connect(self.plot)
        self.building_combobox.view().pressed.connect(self.plot)

    def initMenuBar(self):
        """
        Initializes the menu bar of the BuildingTab.
        """
        self.menubar = QMenuBar(self)
        self.menubar.setFixedHeight(30)

        # Add actions directly to the menubar
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

    def updateDefaultPath(self, path):
        """
        Updates the default path for saving files.
        
        Args:
            path (str): The new default path.
        """
        self.base_path = path
        self.output_path_edit.setText(f"{self.base_path}/Lastgang/Gebäude Lastgang.json")

    def browseOutputFile(self):
        """
        Opens a file dialog to select the output JSON file.
        """
        fname, _ = QFileDialog.getSaveFileName(self, 'Save JSON File As', f"{self.base_path}/Lastgang", 'JSON Files (*.json);;All Files (*)')
        if fname:
            self.output_path_edit.setText(fname)

    def loadCsvFile(self):
        """
        Opens a file dialog to load a CSV file.
        """
        fname, _ = QFileDialog.getOpenFileName(self, 'Select CSV File', f"{self.base_path}/Gebäudedaten", 'CSV Files (*.csv);;All Files (*)')
        if fname:
            try:
                self.data = pd.read_csv(fname, delimiter=';', dtype={'Subtyp': str})
                self.populateComboBoxes()
                self.showCSVTable()
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Laden der CSV-Datei: {e}")

    def saveCsvFile(self):
        """
        Opens a file dialog to save the CSV file.
        """
        fname, _ = QFileDialog.getSaveFileName(self, 'Save CSV File As', f"{self.base_path}/Gebäudedaten", 'CSV Files (*.csv);;All Files (*)')
        if fname:
            try:
                self.data.to_csv(fname, index=False, sep=';')
                QMessageBox.information(self, "Erfolg", f"CSV-Datei wurde in {fname} gespeichert.")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern der CSV-Datei: {e}")

    def loadJsonFile(self):
        """
        Opens a file dialog to load a JSON file.
        """
        fname, _ = QFileDialog.getOpenFileName(self, 'Select JSON File', f"{self.base_path}/Lastgang", 'JSON Files (*.json);;All Files (*)')
        if fname:
            try:
                with open(fname, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)

                    self.results = {k: v for k, v in loaded_data.items() if isinstance(v, dict) and 'lastgang_wärme' in v}

                    df = pd.DataFrame.from_dict({k: v for k, v in loaded_data.items() if k.isdigit()}, orient='index')

                    # Update the table with loaded data
                    self.data = df
                    self.populateComboBoxes()
                    self.showCSVTable()

                self.building_combobox.clear()
                for key in self.results.keys():
                    self.building_combobox.addItem(f'Building {key}')
                    item = self.building_combobox.model().item(self.building_combobox.count() - 1, 0)
                    item.setCheckState(Qt.Checked)

                self.plot()
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Laden der JSON-Datei: {e}")

    def calculateHeatDemand(self):
        """
        Calculates the heat demand profiles and saves the results to a JSON file.
        """
        json_path = self.output_path_edit.text()
        if not json_path:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie einen Speicherort für die Ergebnisse aus.")
            return

        data = self.getTableData()
        if data.empty:
            QMessageBox.warning(self, "Fehler", "Die Tabelle enthält keine Daten.")
            return

        yearly_time_steps, total_heat_W, heating_heat_W, warmwater_heat_W, max_heat_requirement_W, supply_temperature_curve, return_temperature_curve, hourly_air_temperatures = generate_profiles_from_csv(
            data=data, 
            TRY=self.parent.try_filename, 
            calc_method="Datensatz"
        )

        self.results = {}
        for idx in range(len(data)):
            building_id = str(idx)

            if yearly_time_steps is None:
                QMessageBox.critical(self, "Fehler", "Fehler bei der Berechnung der Profile.")
                return

            self.results[building_id] = {
                "zeitschritte": [convert_to_serializable(ts) for ts in yearly_time_steps],
                "außentemperatur": hourly_air_temperatures.tolist(),
                "lastgang_wärme": total_heat_W[idx].tolist(),
                "heating_wärme": heating_heat_W[idx].tolist(),
                "warmwater_wärme": warmwater_heat_W[idx].tolist(),
                "vorlauftemperatur": supply_temperature_curve[idx].tolist(),
                "rücklauftemperatur": return_temperature_curve[idx].tolist(),
                "heizlast": max_heat_requirement_W.tolist()
            }

            for key, value in data.iloc[idx].items():
                self.results[building_id][key] = convert_to_serializable(value)

        data.reset_index(drop=True, inplace=True)
        data_dict = data.applymap(convert_to_serializable).to_dict(orient='index')

        combined_data = {str(idx): {**data_dict[idx], **self.results[str(idx)]} for idx in range(len(data))}

        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, indent=4)
            QMessageBox.information(self, "Erfolg", f"Ergebnisse wurden in {json_path} gespeichert.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern der Ergebnisse: {e}")

        self.building_combobox.clear()
        for key in self.results.keys():
            self.building_combobox.addItem(f'Building {key}')
            item = self.building_combobox.model().item(self.building_combobox.count() - 1, 0)
            item.setCheckState(Qt.Checked)

        self.plot()

    def showCSVTable(self):
        """
        Displays the loaded CSV data in the table widget.
        """
        self.table_widget.setColumnCount(len(self.data.columns))
        self.table_widget.setRowCount(len(self.data.index))
        self.table_widget.setHorizontalHeaderLabels(self.data.columns)

        for i in range(len(self.data.index)):
            for j in range(len(self.data.columns)):
                if self.data.columns[j] in ["Gebäudetyp", "Subtyp"]:
                    combobox = QComboBox()
                    if self.data.columns[j] == "Gebäudetyp":
                        combobox.addItems(self.building_types)
                        combobox.setCurrentText(str(self.data.iat[i, j]))
                        self.table_widget.setCellWidget(i, j, combobox)
                    else:
                        current_building_type = str(self.data.iat[i, self.data.columns.get_loc("Gebäudetyp")])
                        if current_building_type:
                            subtypes = self.building_subtypes.get(current_building_type[:3], [])
                            combobox.addItems(subtypes)
                            #print(f"Row {i}, Building Type {current_building_type[:3]}: Subtypes {subtypes}")
                        else:
                            print(f"Error: Gebäudetyp for row {i} is None")
                        combobox.setCurrentText(str(self.data.iat[i, j]))
                        self.table_widget.setCellWidget(i, j, combobox)
                else:
                    self.table_widget.setItem(i, j, QTableWidgetItem(str(self.data.iat[i, j])))

        self.table_widget.resizeColumnsToContents()
        self.table_widget.resizeRowsToContents()
        self.table_widget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def getTableData(self):
        """
        Retrieves the data from the table widget.
        
        Returns:
            pd.DataFrame: The data from the table widget.
        """
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

        # Ensure 'Subtyp' is always a string
        if 'Subtyp' in df.columns:
            df['Subtyp'] = df['Subtyp'].astype(str)

        # Convert data types for other columns
        for column in df.columns:
            if column != 'Subtyp':  # Skip conversion for 'Subtyp'
                try:
                    df[column] = pd.to_numeric(df[column], errors='ignore')
                except Exception as e:
                    print(f"Could not convert column {column}: {e}")

        return df

    def populateComboBoxes(self):
        """
        Populates the building type and subtype combo boxes.
        """
        df = pd.read_csv(get_resource_path('data\\BDEW profiles\\daily_coefficients.csv'), delimiter=';', dtype=str)
        building_types = df['Standardlastprofil'].str[:3].unique()
        self.building_types = sorted(building_types)
        self.building_subtypes = {}
        for building_type in self.building_types:
            subtypes = df[df['Standardlastprofil'].str.startswith(building_type)]['Standardlastprofil'].str[-2:].unique()
            self.building_subtypes[building_type] = sorted(subtypes)

    def plot(self):
        """
        Plots the selected data types for the selected buildings.
        """
        self.figure.clear()
        ax1 = self.figure.add_subplot(111)
        ax2 = ax1.twinx()

        selected_data_types = self.data_type_combobox.checkedItems()
        selected_buildings = self.building_combobox.checkedItems()

        for building in selected_buildings:
            key = building.split()[-1]
            value = self.results[key]

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QMainWindow()
    building_tab = BuildingTab()
    window.setCentralWidget(building_tab)
    window.setWindowTitle("Building Tab")
    window.show()
    sys.exit(app.exec_())