"""
Filename: lod2_data.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-27
Description: Contains the LOD2Tab.
"""

import os
import csv
import json
import pandas as pd
import numpy as np
from shapely.geometry import Polygon, MultiPolygon
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PyQt5.QtWidgets import (
    QVBoxLayout, QComboBox, QFileDialog, QWidget, QTableWidget, QTableWidgetItem, 
    QHeaderView, QDialog, QHBoxLayout, QScrollArea, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, QObject

from lod2.filter_LOD2 import (
    spatial_filter_with_polygon, filter_LOD2_with_coordinates, 
    process_lod2, calculate_centroid_and_geocode
)
from lod2.heat_requirement_LOD2 import Building
from gui.LOD2Tab.lod2_dialogs import FilterDialog


class LOD2DataModel:
    def __init__(self):
        self.building_info = {}
        self.standard_values = {
            'Stockwerke': 4,
            'ww_demand_kWh_per_m2': 12.8,
            'air_change_rate': 0.5,
            'fracture_windows': 0.10,
            'fracture_doors': 0.01,
            'Normaußentemperatur': -15,
            'room_temp': 20,
            'max_air_temp_heating': 15,
            'Typ_Heizflächen': 'HK',
            'VLT_max': 70,
            'Steigung_Heizkurve': 1.5,
            'RLT_max': 55
        }
        self.base_path = ""
        self.output_geojson_filename = ""

    def set_base_path(self, base_path):
        """Set the base path for file operations."""
        self.base_path = base_path

    def get_base_path(self):
        """Get the current base path."""
        return self.base_path

    def load_data(self, filename):
        """Load data from a GeoJSON file and store it in the model."""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                geojson_data = json.load(file)

            self.building_info = {}
            for feature in geojson_data['features']:
                properties = feature['properties']
                parent_id = properties.get('parent_id')
                self.building_info[parent_id] = properties

            self.output_geojson_filename = filename
        except Exception as e:
            raise Exception(f"Failed to load data from {filename}: {str(e)}")

    def save_data_as_geojson(self, path=None):
        """Save the current building data as a GeoJSON file."""
        try:
            if not path:
                path = self.output_geojson_filename

            with open(self.output_geojson_filename, 'r', encoding='utf-8') as file:
                geojson_data = json.load(file)

            for parent_id, info in self.building_info.items():
                for feature in geojson_data['features']:
                    if feature['properties'].get('parent_id') == parent_id:
                        feature['properties'].update(info)

            with open(path, 'w', encoding='utf-8') as file:
                json.dump(geojson_data, file, ensure_ascii=False, indent=2)

        except Exception as e:
            raise Exception(f"Failed to save data to {path}: {str(e)}")

    def process_data(self):
        """Process the loaded data to calculate required building parameters."""
        if not self.output_geojson_filename:
            raise Exception("No GeoJSON file loaded to process.")

        self.building_info = process_lod2(self.output_geojson_filename, self.standard_values)
        address_missing = any(info['Adresse'] is None for info in self.building_info.values())
        if address_missing:
            self.building_info = calculate_centroid_and_geocode(self.building_info)

    def calculate_heat_demand(self):
        """Calculate the heat demand for each building."""
        for parent_id, info in self.building_info.items():
            u_values = {
                'wall_u': info.get('wall_u', self.standard_values['wall_u']),
                'roof_u': info.get('roof_u', self.standard_values['roof_u']),
                'window_u': info.get('window_u', self.standard_values['window_u']),
                'door_u': info.get('door_u', self.standard_values['door_u']),
                'ground_u': info.get('ground_u', self.standard_values['ground_u']),
            }

            building = Building(
                ground_area=info['Ground_Area'],
                wall_area=info['Wall_Area'],
                roof_area=info['Roof_Area'],
                volume=info['Volume'],
                u_type=info.get('Typ'),
                building_state=info.get('Gebäudezustand'),
                filename_TRY=self.base_path,
                u_values=u_values
            )
            building.calc_yearly_heat_demand()
            info['Wärmebedarf'] = building.yearly_heat_demand
            info['Warmwasseranteil'] = building.warm_water_share

    def filter_data(self, method, *args):
        """Filter the LOD2 data based on the specified method."""
        if method == "Filter by Polygon":
            spatial_filter_with_polygon(*args)
        elif method == "Filter by Building Data CSV":
            filter_LOD2_with_coordinates(*args)
        else:
            raise ValueError(f"Unknown filter method: {method}")

    def create_building_csv(self, path):
        """Create a CSV file with building data."""
        try:
            with open(path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';')
                headers = [
                    'Land', 'Bundesland', 'Stadt', 'Adresse', 'Wärmebedarf', 'Gebäudetyp',
                    'Subtyp', 'WW_Anteil', 'Typ_Heizflächen', 'VLT_max', 'Steigung_Heizkurve',
                    'RLT_max', 'Normaußentemperatur', 'UTM_X', 'UTM_Y'
                ]
                writer.writerow(headers)

                for parent_id, info in self.building_info.items():
                    row_data = self.get_building_csv_row_data(info)
                    writer.writerow(row_data)
        except Exception as e:
            raise Exception(f"Failed to create CSV file at {path}: {str(e)}")

    def get_building_csv_row_data(self, info):
        """Get the row data for the building CSV."""
        return [
            info.get('Land', ''),
            info.get('Bundesland', ''),
            info.get('Stadt', ''),
            info.get('Adresse', ''),
            info.get('Wärmebedarf', 0),
            info.get('Gebäudetyp', ''),
            info.get('Subtyp', ''),
            info.get('Warmwasseranteil', 0),
            info.get('Typ_Heizflächen', ''),
            info.get('VLT_max', ''),
            info.get('Steigung_Heizkurve', ''),
            info.get('RLT_max', ''),
            info.get('Normaußentemperatur', ''),
            info.get('Koordinate_X', ''),
            info.get('Koordinate_Y', ''),
        ]


class DataVisualizationPresenter(QObject):
    data_loaded = pyqtSignal(dict)

    def __init__(self, model, view, data_manager):
        super().__init__()
        self.model = model
        self.view = view
        self.data_manager = data_manager

        self.data_manager.project_folder_changed.connect(self.on_project_folder_changed)
        self.on_project_folder_changed(self.data_manager.project_folder)

        self.connect_signals()

    def on_project_folder_changed(self, new_base_path):
        """Updates the base path in the model when the project folder changes."""
        self.model.set_base_path(new_base_path)

    def connect_signals(self):
        """Connects view signals to presenter slots."""
        self.view.data_selected.connect(self.highlight_building_3d)

    def load_data_from_file(self):
        """Loads data from a GeoJSON file."""
        path, _ = QFileDialog.getOpenFileName(self.view, "Öffnen", self.model.get_base_path(), "GeoJSON-Dateien (*.geojson)")
        if path:
            self.model.load_data(path)
            self.view.update_table(self.model.building_info)
            self.view.update_3d_view(self.model.building_info)

    def save_data_as_geojson(self):
        """Saves the data as a GeoJSON file."""
        path, _ = QFileDialog.getSaveFileName(self.view, "Speichern unter", self.model.get_base_path(), "GeoJSON-Dateien (*.geojson)")
        if path:
            self.model.save_data_as_geojson(path)
            self.view.show_info_message("Speichern erfolgreich", f"Daten wurden erfolgreich gespeichert unter: {path}")

    def show_filter_dialog(self):
        """Shows the filter dialog for LOD2 data filtering."""
        dialog = FilterDialog(self.model.get_base_path(), self.view)
        if dialog.exec_() == QDialog.Accepted:
            self.model.filter_data(
                dialog.filterMethodComboBox.currentText(),
                dialog.inputLOD2geojsonLineEdit.text(),
                dialog.inputfilterPolygonLineEdit.text(),
                dialog.inputfilterBuildingDataLineEdit.text(),
                dialog.outputLOD2geojsonLineEdit.text()
            )
            self.model.load_data(dialog.outputLOD2geojsonLineEdit.text())
            self.view.update_table(self.model.building_info)
            self.view.update_3d_view(self.model.building_info)

    def calculate_heat_demand(self):
        """Calculates the heat demand for each building."""
        self.model.calculate_heat_demand()
        self.view.update_table(self.model.building_info)

    def create_building_csv(self):
        """Creates a CSV file for building data."""
        path, _ = QFileDialog.getSaveFileName(self.view, "Speichern unter", self.model.get_base_path(), "CSV-Dateien (*.csv)")
        if path:
            self.model.create_building_csv(path)
            self.view.show_info_message("CSV-Erstellung erfolgreich", f"Gebäude-csv wurde erfolgreich erstellt: {path}")

    def highlight_building_3d(self, col):
        """Highlights the selected building in the 3D view."""
        parent_id = list(self.model.building_info.keys())[col]
        building_info = self.model.building_info[parent_id]
        self.view.highlight_building_3d(building_info)


class LOD2DataVisualizationTab(QWidget):
    data_selected = pyqtSignal(int)  # Signal to emit when a table column is selected

    def __init__(self, parent=None):
        super().__init__(parent)
        self.comboBoxBuildingTypesItems = []
        self.building_subtypes = {}  # Initialize as a dictionary
        self.initUI()

    def initUI(self):
        """Initializes the UI components of the LOD2DataVisualizationTab."""
        main_layout = QVBoxLayout(self)

        data_vis_layout = QHBoxLayout(self)
        main_layout.addLayout(data_vis_layout)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        data_vis_layout.addWidget(scroll_area)

        scroll_content = QWidget(scroll_area)
        scroll_area.setWidget(scroll_content)
        scroll_layout = QVBoxLayout(scroll_content)

        self.tableWidget = QTableWidget(self)
        self.tableWidget.setRowCount(30)
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setVerticalHeaderLabels([
            'Adresse', 'UTM_X (m)', 'UTM_Y (m)', 'Grundfläche (m²)', 'Wandfläche (m²)',
            'Dachfläche (m²)', 'Volumen (m³)', 'Stockwerke', 'Gebäudetyp SLP', 'Subtyp SLP',
            'Gebäudetyp TABULA', 'Gebäudezustand TABULA', 'WW-Bedarf (kWh/m²)', 'Luftwechselrate (1/h)',
            'Fensteranteil (%)', 'Türanteil (%)', 'Normaußentemperatur (°C)', 'Raumtemperatur (°C)',
            'Max. Heiz-Außentemperatur (°C)', 'U-Wert Wand (W/m²K)', 'U-Wert Dach (W/m²K)',
            'U-Wert Fenster (W/m²K)', 'U-Wert Tür (W/m²K)', 'U-Wert Boden (W/m²K)',
            'Typ_Heizflächen', 'VLT_max (°C)', 'Steigung_Heizkurve', 'RLT_max (°C)',
            'Wärmebedarf (kWh)', 'Warmwasseranteil (%)'
        ])
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tableWidget.setSortingEnabled(False)
        self.tableWidget.setMinimumSize(800, 400)
        scroll_layout.addWidget(self.tableWidget)

        self.figure_3d = plt.figure()
        self.canvas_3d = FigureCanvas(self.figure_3d)
        self.canvas_3d.setMinimumSize(400, 400)
        data_vis_layout.addWidget(self.canvas_3d)

        # Connect signals
        self.tableWidget.itemSelectionChanged.connect(self.on_table_column_select)

    def on_table_column_select(self):
        """Handles the event when a table column is selected."""
        selected_columns = self.tableWidget.selectionModel().selectedColumns()
        if selected_columns:
            col = selected_columns[0].column()
            self.data_selected.emit(col)

    def update_table(self, building_info):
        """Update the table with new data."""
        self.tableWidget.setColumnCount(len(building_info))
        self.tableWidget.setHorizontalHeaderLabels([str(i + 1) for i in range(len(building_info))])

        for col, (parent_id, info) in enumerate(building_info.items()):
            self.update_table_column(col, info)

    def update_table_column(self, col, info):
        """Update a single column in the table."""
        print(info)
        self.tableWidget.setItem(0, col, QTableWidgetItem(str(f"{info['Adresse']}, {info['Stadt']}, {info['Bundesland']}, {info['Land']}")))
        self.tableWidget.setItem(1, col, QTableWidgetItem(str(info['Koordinate_X'])))
        self.tableWidget.setItem(2, col, QTableWidgetItem(str(info['Koordinate_Y'])))
        self.tableWidget.setItem(3, col, QTableWidgetItem(str(round(info['Ground_Area'], 1))))
        self.tableWidget.setItem(4, col, QTableWidgetItem(str(round(info['Wall_Area'], 1))))
        self.tableWidget.setItem(5, col, QTableWidgetItem(str(round(info['Roof_Area'], 1))))
        self.tableWidget.setItem(6, col, QTableWidgetItem(str(round(info['Volume'], 1))))
        self.tableWidget.setItem(7, col, QTableWidgetItem(str(info['Stockwerke'])))

        comboBoxTypes = QComboBox()
        comboBoxTypes.addItems(self.comboBoxBuildingTypesItems)
        comboBoxTypes.setCurrentText(info['Gebäudetyp'])
        self.tableWidget.setCellWidget(8, col, comboBoxTypes)

        comboBoxSubtypes = QComboBox()
        comboBoxSubtypes.addItems(self.building_subtypes.get(comboBoxTypes.currentText(), []))
        comboBoxSubtypes.setCurrentText(info['Subtyp'])
        self.tableWidget.setCellWidget(9, col, comboBoxSubtypes)

        comboBoxBuildingTypes = QComboBox()
        comboBoxBuildingTypes.addItems(self.comboBoxBuildingTypesItems)
        self.tableWidget.setCellWidget(10, col, comboBoxBuildingTypes)

        comboBoxBuildingState = QComboBox()
        comboBoxBuildingState.addItems(["Existing_state", "Usual_Refurbishment", "Advanced_Refurbishment", "Individuell"])
        self.tableWidget.setCellWidget(11, col, comboBoxBuildingState)

        self.set_default_or_existing_values(col, info)

    def set_default_or_existing_values(self, col, info):
        """Set default or existing values in the table widget."""
        self.tableWidget.setItem(12, col, QTableWidgetItem(str(info['ww_demand_kWh_per_m2'])))
        self.tableWidget.setItem(13, col, QTableWidgetItem(str(info['air_change_rate'])))
        self.tableWidget.setItem(14, col, QTableWidgetItem(str(info['fracture_windows'])))
        self.tableWidget.setItem(15, col, QTableWidgetItem(str(info['fracture_doors'])))
        self.tableWidget.setItem(16, col, QTableWidgetItem(str(info['Normaußentemperatur'])))
        self.tableWidget.setItem(17, col, QTableWidgetItem(str(info['room_temp'])))
        self.tableWidget.setItem(18, col, QTableWidgetItem(str(info['max_air_temp_heating'])))
        self.tableWidget.setItem(19, col, QTableWidgetItem(str(info['wall_u'])))
        self.tableWidget.setItem(20, col, QTableWidgetItem(str(info['roof_u'])))
        self.tableWidget.setItem(21, col, QTableWidgetItem(str(info['window_u'])))
        self.tableWidget.setItem(22, col, QTableWidgetItem(str(info['door_u'])))
        self.tableWidget.setItem(23, col, QTableWidgetItem(str(info['ground_u'])))
        self.tableWidget.setItem(24, col, QTableWidgetItem(str(info['Typ_Heizflächen'])))
        self.tableWidget.setItem(25, col, QTableWidgetItem(str(info['VLT_max'])))
        self.tableWidget.setItem(26, col, QTableWidgetItem(str(info['Steigung_Heizkurve'])))
        self.tableWidget.setItem(27, col, QTableWidgetItem(str(info['RLT_max'])))
        self.tableWidget.setItem(28, col, QTableWidgetItem(str(info['Wärmebedarf'])))
        self.tableWidget.setItem(29, col, QTableWidgetItem(str(info['Warmwasseranteil'])))

    def update_3d_view(self, building_info):
        """Update the 3D view with new building data."""
        self.figure_3d.clear()
        ax = self.figure_3d.add_subplot(111, projection='3d')

        for parent_id, info in building_info.items():
            self.plot_building_parts(ax, info)

        ax.set_xlabel('UTM_X')
        ax.set_ylabel('UTM_Y')
        ax.set_zlabel('Höhe')
        ax.set_title('3D-Visualisierung der LOD2-Daten')

        self.canvas_3d.draw()

    def plot_building_parts(self, ax, info):
        """Plot the building parts in the 3D view."""
        self.plot_geometry(ax, info['Ground'], 'green')
        self.plot_geometry(ax, info['Wall'], 'blue')
        self.plot_geometry(ax, info['Roof'], 'brown')

    def plot_geometry(self, ax, geoms, color):
        """Plot geometry on the 3D axes."""
        if isinstance(geoms, (Polygon, MultiPolygon)):
            geoms = [geoms]

        for geom in geoms:
            if geom.geom_type == 'Polygon':
                x, y, z = zip(*geom.exterior.coords)
                verts = [list(zip(x, y, z))]
                poly_collection = Poly3DCollection(verts, facecolors=color, alpha=0.5)
                ax.add_collection3d(poly_collection)
            elif geom.geom_type == 'MultiPolygon':
                for poly in geom.geoms:
                    x, y, z = zip(*poly.exterior.coords)
                    verts = [list(zip(x, y, z))]
                    poly_collection = Poly3DCollection(verts, facecolors=color, alpha=0.5)
                    ax.add_collection3d(poly_collection)

    def highlight_building_3d(self, info):
        """Highlights a building in the 3D plot."""
        self.update_3d_view({info['parent_id']: info})  # Ensure the single building is highlighted

    def show_info_message(self, title, message):
        """Displays an informational message box."""
        QMessageBox.information(self, title, message)
