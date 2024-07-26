"""
Filename: building_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-26
Description: Contains the BuildingTab.
"""

import json
import numpy as np
import pandas as pd

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QMessageBox, QApplication, 
                             QMainWindow, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QScrollArea,
                             QMenuBar, QAction, QDialog, QDialogButtonBox, QLineEdit)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QStandardItemModel

from heat_requirement.heat_requirement_calculation_csv import generate_profiles_from_csv

def convert_to_serializable(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict()
    elif isinstance(obj, pd.Series):
        return obj.to_dict()
    else:
        return obj

class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super(CheckableComboBox, self).__init__(parent)
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QStandardItemModel(self))

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)

    def checkedItems(self):
        checked_items = []
        for index in range(self.count()):
            item = self.model().item(index)
            if item.checkState() == Qt.Checked:
                checked_items.append(item.text())
        return checked_items


class BuildingTab(QWidget):
    data_added = pyqtSignal(object)

    def __init__(self, data_manager=None, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent

        if self.data_manager:
            self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
            self.updateDefaultPath(self.data_manager.project_folder)

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
        self.menubar = QMenuBar(self)
        self.menubar.setFixedHeight(30)

        file_menu = self.menubar.addMenu("Datei")
        
        filter_action = QAction("Gebäudelastgänge berechnen", self)
        filter_action.triggered.connect(self.showFilterDialog)
        file_menu.addAction(filter_action)

        load_json_action = QAction("Gebäudelastgänge laden", self)
        load_json_action.triggered.connect(self.loadJsonFile)
        file_menu.addAction(load_json_action)

        self.main_layout.setMenuBar(self.menubar)

    def updateDefaultPath(self, path):
        self.base_path = path

    def showFilterDialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Filter Options")
        dialog.resize(400, 400)
        
        layout = QVBoxLayout(dialog)
        
        input_label = QLabel("Input CSV File:")
        self.input_edit = QLineEdit(f"{self.base_path}/Gebäudedaten")
        input_button = QPushButton("Browse")
        input_button.clicked.connect(self.browseInputFile)

        output_label = QLabel("Output JSON File:")
        self.output_edit = QLineEdit(f"{self.base_path}/Lastgang/Gebäude Lastgang.json")
        output_button = QPushButton("Browse")
        output_button.clicked.connect(self.browseOutputFile)

        layout.addWidget(input_label)
        layout.addWidget(self.input_edit)
        layout.addWidget(input_button)
        layout.addWidget(output_label)
        layout.addWidget(self.output_edit)
        layout.addWidget(output_button)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, dialog)
        buttons.accepted.connect(lambda: self.process_data(self.input_edit.text(), self.output_edit.text()))
        buttons.rejected.connect(dialog.reject)
        
        layout.addWidget(buttons)
        dialog.setLayout(layout)
        dialog.exec_()

    def browseInputFile(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Select CSV File', f"{self.base_path}/Gebäudedaten", 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.input_edit.setText(fname)

    def browseOutputFile(self):
        fname, _ = QFileDialog.getSaveFileName(self, 'Save JSON File As', f"{self.base_path}/Lastgang", 'JSON Files (*.json);;All Files (*)')
        if fname:
            self.output_edit.setText(fname)

    def loadJsonFile(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Select JSON File', f"{self.base_path}/Lastgang", 'JSON Files (*.json);;All Files (*)')
        if fname:
            try:
                with open(fname, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)

                    # Ensure results contain the necessary keys
                    self.results = {k: v for k, v in loaded_data.items() if isinstance(v, dict) and 'lastgang_wärme' in v}

                    # Process the loaded data to form a DataFrame
                    df = pd.DataFrame.from_dict({k: v for k, v in loaded_data.items() if k.isdigit()}, orient='index')

                self.display_results(df)

                self.building_combobox.clear()
                for key in self.results.keys():
                    self.building_combobox.addItem(f'Building {key}')
                    item = self.building_combobox.model().item(self.building_combobox.count() - 1, 0)
                    item.setCheckState(Qt.Checked)

                self.plot()
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Laden der JSON-Datei: {e}")

    def process_data(self, csv_path=None, json_path=None):
        if not csv_path:
            csv_path = self.input_edit.text()
        if not json_path:
            json_path = self.output_edit.text()

        if not csv_path:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie zuerst eine CSV-Datei aus.")
            return

        if not json_path:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie einen Speicherort für die Ergebnisse aus.")
            return

        try:
            data = pd.read_csv(csv_path, delimiter=';', dtype={'Subtyp': str})
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Laden der CSV-Datei: {e}")
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
                #"zeitschritte": yearly_time_steps.tolist(),
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

        self.display_results(data)

    def display_results(self, geojson):
        columns = list(geojson.columns) + ["lastgang_wärme", "heating_wärme", "warmwater_wärme", "vorlauftemperatur", "rücklauftemperatur"]
        self.table_widget.setColumnCount(len(columns))
        self.table_widget.setHorizontalHeaderLabels(columns)
        self.table_widget.setRowCount(len(geojson))

        for row_idx, feature in geojson.iterrows():
            for col_idx, (key, value) in enumerate(feature.items()):
                if isinstance(value, list):
                    value = str(value[:5]) + "..."  # Convert list to a short string representation
                self.table_widget.setItem(int(row_idx), int(col_idx), QTableWidgetItem(str(value)))

        for row_idx in range(len(geojson)):
            lastgang_wärme = self.results[str(row_idx)]["lastgang_wärme"]
            heating_wärme = self.results[str(row_idx)]["heating_wärme"]
            warmwater_wärme = self.results[str(row_idx)]["warmwater_wärme"]
            vorlauftemperatur = self.results[str(row_idx)]["vorlauftemperatur"]
            rücklauftemperatur = self.results[str(row_idx)]["rücklauftemperatur"]

            self.table_widget.setItem(int(row_idx), len(geojson.columns), QTableWidgetItem(str(lastgang_wärme[:5]) + "..."))
            self.table_widget.setItem(int(row_idx), len(geojson.columns) + 1, QTableWidgetItem(str(heating_wärme[:5]) + "..."))
            self.table_widget.setItem(int(row_idx), len(geojson.columns) + 2, QTableWidgetItem(str(warmwater_wärme[:5]) + "..."))
            self.table_widget.setItem(int(row_idx), len(geojson.columns) + 3, QTableWidgetItem(str(vorlauftemperatur[:5]) + "..."))
            self.table_widget.setItem(int(row_idx), len(geojson.columns) + 4, QTableWidgetItem(str(rücklauftemperatur[:5]) + "..."))

        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.plot()

    def plot(self):
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
    import sys
    app = QApplication(sys.argv)
    window = QMainWindow()
    building_tab = BuildingTab()
    window.setCentralWidget(building_tab)
    window.setWindowTitle("Building Tab")
    window.show()
    sys.exit(app.exec_())