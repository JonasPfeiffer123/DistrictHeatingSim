"""
Filename: building_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
Description: Contains the BuildingTab.
"""

import json
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QMessageBox, QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import pyqtSignal

from heat_requirement import heat_requirement_VDI4655, heat_requirement_BDEW

class BuildingTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    def __init__(self, data_manager=None, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent

        if self.data_manager:
            # Connect to the data manager signal
            self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
            # Update the base path immediately with the current project folder
            self.updateDefaultPath(self.data_manager.project_folder)

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        self.geojson_path_label = QLabel("GeoJSON-Datei: Nicht ausgewählt", self)
        layout.addWidget(self.geojson_path_label)

        self.select_geojson_button = QPushButton("GeoJSON-Datei auswählen", self)
        self.select_geojson_button.clicked.connect(self.selectGeoJsonFile)
        layout.addWidget(self.select_geojson_button)

        self.process_button = QPushButton("Daten verarbeiten", self)
        self.process_button.clicked.connect(self.process_data)
        layout.addWidget(self.process_button)

        self.results_path_label = QLabel("Ergebnisse gespeichert in: Nicht verfügbar", self)
        layout.addWidget(self.results_path_label)

        self.table_widget = QTableWidget(self)
        layout.addWidget(self.table_widget)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(700, 700)  # Setze eine Mindestgröße für die Canvas
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Fügen Sie die Diagramme und Toolbars zum Container-Layout hinzu
        layout.addWidget(self.canvas)
        layout.addWidget(self.toolbar)
    
        self.setLayout(layout)

    def updateDefaultPath(self, path):
        self.base_path = path

    def selectGeoJsonFile(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'GeoJSON-Datei auswählen', self.base_path, 'GeoJSON Files (*.geojson);;All Files (*)')
        if fname:
            self.geojson_path = fname
            self.geojson_path_label.setText(f"GeoJSON-Datei: {fname}")
        else:
            self.geojson_path = None

    def process_data(self):
        if not hasattr(self, 'geojson_path') or not self.geojson_path:
            self.geojson_path = QFileDialog.getOpenFileName(self, 'GeoJSON-Datei auswählen', self.base_path, 'GeoJSON Files (*.geojson);;All Files (*)')[0]
            if not self.geojson_path:
                QMessageBox.warning(self, "Fehler", "Bitte wählen Sie zuerst eine GeoJSON-Datei aus.")
                return

        ergebnisse_path = QFileDialog.getSaveFileName(self, 'Ergebnisse speichern als', self.base_path, 'JSON Files (*.json);;All Files (*)')[0]
        if not ergebnisse_path:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie einen Speicherort für die Ergebnisse aus.")
            return

        # GeoJSON-Datei laden
        try:
            geojson = gpd.read_file(self.geojson_path)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Laden der GeoJSON-Datei: {e}")
            return

        min_supply_temperature_building = 60

        try:
            supply_temperature_buildings = geojson["VLT_max"].values.astype(float)
            return_temperature_buildings = geojson["RLT_max"].values.astype(float)
        except KeyError as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Auslesen der Temperaturdaten: {e}")
            return

        ### Definition Mindestvorlauftemperatur ###
        min_supply_temperature_building = np.full_like(supply_temperature_buildings, min_supply_temperature_building)

        yearly_time_steps, total_heat_W, max_heat_requirement_W, supply_temperature_curve, return_temperature_curve = self.generate_profiles_from_geojson(
            gdf_building=geojson, 
            TRY=self.parent.try_filename, 
            calc_method="Datensatz", 
            max_supply_temperature=supply_temperature_buildings, 
            max_return_temperature=return_temperature_buildings, 
            min_supply_temperature_building=min_supply_temperature_building
        )
        
        results = {}
        for idx, feature in geojson.iterrows():
            building_id = str(idx)  # Verwenden einer fortlaufenden Nummer als ID

            if yearly_time_steps is None:
                QMessageBox.critical(self, "Fehler", "Fehler bei der Berechnung der Profile.")
                return

            results[building_id] = {
                "lastgang_wärme": total_heat_W[idx].tolist(),
                "vorlauftemperatur": supply_temperature_curve[idx].tolist(),
                "rücklauftemperatur": return_temperature_curve[idx].tolist()
            }

        # Ergebnisse in eine separate JSON-Datei speichern
        try:
            with open(ergebnisse_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=4)
            self.results_path_label.setText(f"Ergebnisse gespeichert in: {ergebnisse_path}")
            QMessageBox.information(self, "Erfolg", f"Ergebnisse wurden in {ergebnisse_path} gespeichert.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern der Ergebnisse: {e}")

        self.display_results(geojson, results)

    def generate_profiles_from_geojson(self, gdf_building, TRY, building_type="HMF", calc_method="BDEW", max_supply_temperature=70, max_return_temperature=55, min_supply_temperature_building=60):
        ### define the heat requirement ###
        try:
            YEU_total_heat_kWh = gdf_building["Wärmebedarf"].values.astype(float)
        except KeyError:
            print("Herauslesen des Wärmebedarfs aus geojson nicht möglich.")
            return None

        total_heat_W = []
        max_heat_requirement_W = []
        yearly_time_steps = None

        # Assignment of building types to calculation methods
        building_type_to_method = {
            "EFH": "VDI4655",
            "MFH": "VDI4655",
            "HEF": "BDEW",
            "HMF": "BDEW",
            "GKO": "BDEW",
            "GHA": "BDEW",
            "GMK": "BDEW",
            "GBD": "BDEW",
            "GBH": "BDEW",
            "GWA": "BDEW",
            "GGA": "BDEW",
            "GBA": "BDEW",
            "GGB": "BDEW",
            "GPD": "BDEW",
            "GMF": "BDEW",
            "GHD": "BDEW",
        }

        for idx, YEU in enumerate(YEU_total_heat_kWh):
            if calc_method == "Datensatz":
                try:
                    current_building_type = gdf_building.at[idx, "Gebäudetyp"]
                    current_calc_method = building_type_to_method.get(current_building_type, "StandardMethode")
                except KeyError:
                    print("Gebäudetyp-Spalte nicht in gdf_HAST gefunden.")
                    current_calc_method = "StandardMethode"
            else:
                current_building_type = building_type
                current_calc_method = calc_method

            # Heat demand calculation based on building type and calculation method
            if current_calc_method == "VDI4655":
                YEU_heating_kWh, YEU_hot_water_kWh = YEU_total_heat_kWh * 0.8, YEU_total_heat_kWh * 0.2
                heating, hot_water = YEU_heating_kWh[idx], YEU_hot_water_kWh[idx]
                yearly_time_steps, electricity_kW, heating_kW, hot_water_kW, total_heat_kW, hourly_temperatures = heat_requirement_VDI4655.calculate(heating, hot_water, building_type=current_building_type, TRY=TRY)

            elif current_calc_method == "BDEW":
                yearly_time_steps, total_heat_kW, hourly_temperatures  = heat_requirement_BDEW.calculate(YEU, current_building_type, subtyp="03", TRY=TRY)

            total_heat_kW = np.where(total_heat_kW<0, 0, total_heat_kW)
            total_heat_W.append(total_heat_kW * 1000)
            max_heat_requirement_W.append(np.max(total_heat_kW * 1000))

        total_heat_W = np.array(total_heat_W)
        max_heat_requirement_W = np.array(max_heat_requirement_W)

        supply_temperature_curve, return_temperature_curve = self.calculate_temperature_curves(
            gdf_building, 
            max_supply_temperature, 
            max_return_temperature, 
            hourly_temperatures, 
            min_supply_temperature_building
        )

        return yearly_time_steps, total_heat_W, max_heat_requirement_W, supply_temperature_curve, return_temperature_curve
    
    def calculate_temperature_curves(self, gdf_building, max_supply_temperature, max_return_temperature, hourly_temperatures, min_supply_temperature_building, min_air_temperature=-12):
        # Calculation of the temperature curve based on the selected settings
        supply_temperature_curve = []
        return_temperature_curve = []

        # get slope of heat exchanger
        slope = -gdf_building["Steigung_Heizkurve"].values.astype(float)

        dT =  np.expand_dims(max_supply_temperature - max_return_temperature, axis=1)
        min_supply_temperature_building = np.expand_dims(min_supply_temperature_building, axis=1)

        for st, s in zip(max_supply_temperature, slope):
            # Calculation of the temperature curves for flow and return
            st_curve = np.where(hourly_temperatures <= min_air_temperature, st, st + (s * (hourly_temperatures - min_air_temperature)))
            
            supply_temperature_curve.append(st_curve)

        supply_temperature_curve = np.array(supply_temperature_curve)
        supply_temperature_curve = np.where(min_supply_temperature_building > supply_temperature_curve, min_supply_temperature_building, supply_temperature_curve)
        
        return_temperature_curve = supply_temperature_curve - dT

        return supply_temperature_curve, return_temperature_curve

    def display_results(self, geojson, results):
        # Display results in a table
        columns = list(geojson.columns) + ["lastgang_wärme", "vorlauftemperatur", "rücklauftemperatur"]
        self.table_widget.setColumnCount(len(columns))
        self.table_widget.setHorizontalHeaderLabels(columns)
        self.table_widget.setRowCount(len(geojson))

        for row_idx, feature in geojson.iterrows():
            for col_idx, (key, value) in enumerate(feature.items()):
                self.table_widget.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))
            self.table_widget.setItem(row_idx, len(geojson.columns), QTableWidgetItem(str(results[str(row_idx)]["lastgang_wärme"][:5]) + "..."))
            self.table_widget.setItem(row_idx, len(geojson.columns) + 1, QTableWidgetItem(str(results[str(row_idx)]["vorlauftemperatur"][:5]) + "..."))
            self.table_widget.setItem(row_idx, len(geojson.columns) + 2, QTableWidgetItem(str(results[str(row_idx)]["rücklauftemperatur"][:5]) + "..."))

        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.plot(results)

    def plot(self, results):
        # Clear previous figure
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        for key, value in results.items():
            ax.plot(value["lastgang_wärme"], label=f'Building {key}')
        ax.set_xlabel('Time (hours)')
        ax.set_ylabel('Heat Demand (W)')
        ax.legend(loc='upper center')
        ax.grid()
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
