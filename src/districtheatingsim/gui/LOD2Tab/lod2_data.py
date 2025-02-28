"""
Filename: lod2_data.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-28
Description: Contains the LOD2Tab.
"""

import sys
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

from districtheatingsim.lod2.filter_LOD2 import (
    spatial_filter_with_polygon, filter_LOD2_with_coordinates, 
    process_lod2, calculate_centroid_and_geocode
)
from districtheatingsim.lod2.heat_requirement_LOD2 import Building
from districtheatingsim.gui.LOD2Tab.lod2_dialogs import FilterDialog


class LOD2DataModel:
    """
    A model to manage and process LOD2 data for building energy simulations.
    """

    def __init__(self):
        """
        Initializes the LOD2DataModel with default values and loads necessary resources.
        """
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
        self.output_geojson_path = ""
        self.slp_building_types = []  # Für SLP-Gebäudetypen
        self.tabula_building_types = []  # Für TABULA-Gebäudetypen
        self.building_subtypes = {}
        self.try_filename = ""

        # Load the U-values DataFrame from the CSV file
        self.u_values_df = pd.read_csv(self.get_resource_path('data\\TABULA\\standard_u_values_TABULA.csv'), sep=";")
        self.populateComboBoxes()

    def set_base_path(self, base_path):
        """
        Set the base path for file operations.

        Args:
            base_path (str): The base path for file operations.
        """
        self.base_path = base_path

    def get_base_path(self):
        """
        Get the current base path.

        Returns:
            str: The current base path.
        """
        return self.base_path
    
    def filter_data(self, method, lod_geojson_path, filter_file_path, output_geojson_path):
        """
        Filter the LOD2 data based on the specified method.

        Args:
            method (str): The filtering method to use.
            lod_geojson_path (str): Path to the input GeoJSON file.
            filter_file_path (str): Path to the filter file.
            output_geojson_path (str): Path to save the filtered GeoJSON file.
        
        Raises:
            ValueError: If an unknown filter method is provided.
        """
        if method == "Filter by Polygon":
            spatial_filter_with_polygon(lod_geojson_path, filter_file_path, output_geojson_path)
        elif method == "Filter by Building Data CSV":
            filter_LOD2_with_coordinates(lod_geojson_path, filter_file_path, output_geojson_path)
        else:
            raise ValueError(f"Unknown filter method: {method}")

    def load_data(self, filename):
        """
        Load data from a GeoJSON file and store it in the model.

        Args:
            filename (str): The path to the GeoJSON file to load.

        Raises:
            Exception: If loading the data fails.
        """
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                geojson_data = json.load(file)

            self.building_info = {}
            for feature in geojson_data['features']:
                properties = feature['properties']
                parent_id = properties.get('parent_id')
                self.building_info[parent_id] = properties

            self.output_geojson_path = filename
        except Exception as e:
            raise Exception(f"Failed to load data from {filename}: {str(e)}")
        
    def save_data_as_geojson(self, path, data_from_view):
        """
        Save the collected data to a GeoJSON file.

        Args:
            path (str): The path where the GeoJSON file will be saved.
            data_from_view (list): The data collected from the view to be saved.

        Raises:
            Exception: If saving the data fails.
        """
        try:
            with open(self.output_geojson_path, 'r', encoding='utf-8') as file:
                geojson_data = json.load(file)

            for col, feature_data in enumerate(data_from_view):
                self.update_geojson_properties(geojson_data, feature_data, col)

            with open(path, 'w', encoding='utf-8') as file:
                json.dump(geojson_data, file, ensure_ascii=False, indent=2)

        except Exception as e:
            raise Exception(f"Failed to save data to {path}: {str(e)}")

    def update_geojson_properties(self, geojson_data, feature_data, col):
        """
        Updates the properties of the GeoJSON data with the collected data.

        Args:
            geojson_data (dict): The GeoJSON data structure.
            feature_data (dict): The updated feature data to be merged.
            col (int): The column index corresponding to the feature.
        """
        for feature in geojson_data['features']:
            properties = feature['properties']
            parent_id = properties.get('parent_id')

            if parent_id == list(self.building_info.keys())[col]:
                properties.update(feature_data)

    def process_data(self, output_geojson_path):
        """
        Process the loaded data to calculate required building parameters.

        Args:
            output_geojson_path (str): The path to the GeoJSON file that will store the processed data.
        """
        self.output_geojson_path = output_geojson_path

        self.building_info = process_lod2(self.output_geojson_path, self.standard_values)
        
        address_missing = any(info['Adresse'] is None for info in self.building_info.values())
        if address_missing:
            self.building_info = calculate_centroid_and_geocode(self.building_info)

        # Überprüfen und Laden der U-Werte für jedes Gebäude
        for parent_id, info in self.building_info.items():
            self.check_and_load_u_values(info)

    def populateComboBoxes(self):
        """
        Populates the building types and subtypes ComboBoxes with data from CSV files.
        """
        slp_df = pd.read_csv(self.get_resource_path('data\\BDEW profiles\\daily_coefficients.csv'), delimiter=';', dtype=str)
        u_values_df = pd.read_csv(self.get_resource_path('data\\TABULA\\standard_u_values_TABULA.csv'), sep=';')
        
        # Für SLP-Gebäudetyp
        self.slp_building_types = sorted(slp_df['Standardlastprofil'].str[:3].unique())
        self.building_subtypes = {}
        for building_type in self.slp_building_types:
            subtypes = slp_df[slp_df['Standardlastprofil'].str.startswith(building_type)]['Standardlastprofil'].str[-2:].unique()
            self.building_subtypes[building_type] = sorted(subtypes)

        # Für TABULA-Gebäudetyp (Stelle sicher, dass diese Daten korrekt aus dem richtigen Datensatz stammen)
        self.tabula_building_types = sorted(u_values_df['Typ'].unique().tolist())

    def get_building_types(self):
        """
        Get a list of building types for the ComboBox.

        Returns:
            list: A list of SLP building types.
        """
        return self.slp_building_types

    def get_u_values(self, building_type, building_state):
        """
        Gets the U-values based on the building type and state.

        Args:
            building_type (str): The type of the building.
            building_state (str): The state of the building.

        Returns:
            tuple: A tuple containing U-values for wall, roof, window, door, and ground.
        """
        u_values = self.u_values_df[(self.u_values_df['Typ'] == building_type) & (self.u_values_df['building_state'] == building_state)]
        return (
            u_values.iloc[0]['wall_u'] if not u_values.empty else None,
            u_values.iloc[0]['roof_u'] if not u_values.empty else None,
            u_values.iloc[0]['window_u'] if not u_values.empty else None,
            u_values.iloc[0]['door_u'] if not u_values.empty else None,
            u_values.iloc[0]['ground_u'] if not u_values.empty else None
        )
    
    def check_and_load_u_values(self, info):
        """
        Check if U-values are already in the dataset. 
        If not, load them based on TABULA information.

        Args:
            info (dict): A dictionary containing building information.
        """
        # Setzen von Standardwerten für Gebäudetyp und Zustand TABULA, falls nicht vorhanden
        if 'Typ' not in info or info['Typ'] is None:
            info['Typ'] = self.tabula_building_types[0]  # Standardwert setzen, z.B. den ersten TABULA-Typ
        if 'Gebäudezustand' not in info or info['Gebäudezustand'] is None:
            info['Gebäudezustand'] = 'Existing_state'  # Standardzustand setzen

        # Überprüfen, ob die U-Werte None sind und ob wir sie aus den TABULA-Daten laden müssen
        if info.get('wall_u') is None or \
           info.get('roof_u') is None or \
           info.get('window_u') is None or \
           info.get('door_u') is None or \
           info.get('ground_u') is None:
           
            # Ermitteln der U-Werte anhand von TABULA-Informationen
            building_type = info.get('Typ')
            building_state = info.get('Gebäudezustand')
            wall_u, roof_u, window_u, door_u, ground_u = self.get_u_values(building_type, building_state)
            
            # Setzen der Werte in den `info`-Daten
            info['wall_u'] = wall_u
            info['roof_u'] = roof_u
            info['window_u'] = window_u
            info['door_u'] = door_u
            info['ground_u'] = ground_u

    def calculate_heat_demand(self):
        """
        Calculate the heat demand for each building.
        """
        for parent_id, info in self.building_info.items():
            # Die U-Werte und andere relevante Informationen sollten direkt aus der Tabelle gelesen werden
            u_values = {
                'wall_u': info.get('wall_u', None),
                'roof_u': info.get('roof_u', None),
                'window_u': info.get('window_u', None),
                'door_u': info.get('door_u', None),
                'ground_u': info.get('ground_u', None),
            }

            print("TRY-Datei:", self.try_filename)

            # Berechnung der Wärmebedarfswerte basierend auf den aktuellen Werten im `info`-Daten
            building = Building(
                ground_area=info['Ground_Area'],
                wall_area=info['Wall_Area'],
                roof_area=info['Roof_Area'],
                building_volume=info['Volume'],
                u_type=info.get('Typ'),  # Aus der Tabelle geladener Wert
                building_state=info.get('Gebäudezustand'),  # Aus der Tabelle geladener Wert
                filename_TRY=self.try_filename,
                u_values=u_values
            )
            building.calc_yearly_heat_demand()
            
            # Speicherung der Ergebnisse im `info`-Daten
            info['Wärmebedarf'] = np.round(building.yearly_heat_demand,2)
            info['Warmwasseranteil'] = np.round(building.warm_water_share,2)

    def create_building_csv(self, path):
        """
        Create a CSV file with building data.

        Args:
            path (str): The path where the CSV file will be saved.

        Raises:
            Exception: If saving the CSV file fails.
        """
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
                    
            QMessageBox.information(None, "Speichern erfolgreich", f"Daten wurden erfolgreich gespeichert unter: {path}")
            
        except Exception as e:
            QMessageBox.critical(None, "Fehler beim Speichern", f"Ein Fehler ist beim Speichern aufgetreten: {str(e)}")

    def get_building_csv_row_data(self, info):
        """
        Get the row data for the building CSV.

        Args:
            info (dict): A dictionary containing building information.

        Returns:
            list: A list representing a row in the CSV file.
        """
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

class DataVisualizationPresenter(QObject):
    """
    The presenter class for managing the interaction between the model and the view in the LOD2 data visualization.
    """
    data_loaded = pyqtSignal(dict)

    def __init__(self, model, view, folder_manager, data_manager, config_manager):
        """
        Initializes the DataVisualizationPresenter with references to the model, view, folder manager, and data manager.

        Args:
            model (LOD2DataModel): The data model.
            view (LOD2DataVisualizationTab): The view component.
            folder_manager (FolderManager): The folder manager.
            data_manager (DataManager): The data manager.
        """
        super().__init__()
        self.model = model
        self.view = view
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        self.folder_manager.project_folder_changed.connect(self.on_project_folder_changed)
        self.on_project_folder_changed(self.folder_manager.variant_folder)

        self.connect_signals()

    def on_project_folder_changed(self, new_base_path):
        """
        Updates the base path in the model when the project folder changes.

        Args:
            new_base_path (str): The new base path.
        """
        self.model.set_base_path(new_base_path)
        self.model.populateComboBoxes()  # Populate ComboBox data

    def connect_signals(self):
        """
        Connects view signals to presenter slots.
        """
        self.view.data_selected.connect(self.highlight_building_3d)
        self.view.u_value_updated.connect(self.update_u_values)
        self.view.building_type_changed.connect(self.update_u_values)  # Neu: Reagiert auf Änderungen am Gebäudetyp
        self.view.building_state_changed.connect(self.update_u_values)  # Neu: Reagiert auf Änderungen am Gebäudezustand

    def load_data_from_file(self):
        """
        Loads data from a GeoJSON file.
        """
        path, _ = QFileDialog.getOpenFileName(self.view, "Öffnen", self.model.get_base_path(), "GeoJSON-Dateien (*.geojson)")
        if path:
            try:
                # Process the data (this includes functions like process_lod2 and calculate_centroid_and_geocode)
                self.model.process_data(path)
                
                # Überprüfen und Laden der U-Werte direkt nach dem Laden der Daten
                for parent_id, info in self.model.building_info.items():
                    self.model.check_and_load_u_values(info)
                
                # Update the view with the processed data
                self.view.update_table(
                    self.model.building_info, 
                    self.model.get_building_types(), 
                    self.model.tabula_building_types, 
                    self.model.building_subtypes
                )
                self.view.update_3d_view(self.model.building_info)
            
            except Exception as e:
                self.view.show_info_message("Error", f"Failed to load or process data: {str(e)}")

    def save_data_as_geojson(self):
        """
        Collects data from the view and passes it to the model for saving.
        """
        path, _ = QFileDialog.getSaveFileName(self.view, "Speichern unter", self.model.output_geojson_path, "GeoJSON-Dateien (*.geojson)")
        if path:
            try:
                # Daten aus der View (QTableWidget) sammeln
                data_from_view = self.collect_data_from_view()

                # Übergabe der Daten an das Model zur Speicherung
                self.model.save_data_as_geojson(path, data_from_view)

                QMessageBox.information(self.view, "Speichern erfolgreich", f"Daten wurden erfolgreich gespeichert unter: {path}")
            except Exception as e:
                QMessageBox.critical(self.view, "Fehler beim Speichern", f"Ein Fehler ist beim Speichern aufgetreten: {str(e)}")

    def collect_data_from_view(self):
        """
        Collects data from the QTableWidget in the view.

        Returns:
            list: A list of dictionaries representing the collected data.
        """
        data = []
        for col in range(self.view.tableWidget.columnCount()):
            column_data = {
                'Adresse': self.view.tableWidget.item(0, col).text().split(", ")[0],
                'Stadt': self.view.tableWidget.item(0, col).text().split(", ")[1],
                'Bundesland': self.view.tableWidget.item(0, col).text().split(", ")[2],
                'Land': self.view.tableWidget.item(0, col).text().split(", ")[3],
                'Koordinate_X': float(self.view.tableWidget.item(1, col).text()),
                'Koordinate_Y': float(self.view.tableWidget.item(2, col).text()),
                'Ground_Area': float(self.view.tableWidget.item(3, col).text()),
                'Wall_Area': float(self.view.tableWidget.item(4, col).text()),
                'Roof_Area': float(self.view.tableWidget.item(5, col).text()),
                'Volume': float(self.view.tableWidget.item(6, col).text()),
                'Stockwerke': int(self.view.tableWidget.item(7, col).text()) if self.view.tableWidget.item(7, col) else None,
                'Gebäudetyp': self.view.tableWidget.cellWidget(8, col).currentText(),
                'Subtyp': self.view.tableWidget.cellWidget(9, col).currentText(),
                'Typ': self.view.tableWidget.cellWidget(10, col).currentText(),
                'Gebäudezustand': self.view.tableWidget.cellWidget(11, col).currentText(),
                'ww_demand_kWh_per_m2': float(self.view.tableWidget.item(12, col).text()) if self.view.tableWidget.item(12, col) else None,
                'air_change_rate': float(self.view.tableWidget.item(13, col).text()) if self.view.tableWidget.item(13, col) else None,
                'fracture_windows': float(self.view.tableWidget.item(14, col).text()) if self.view.tableWidget.item(14, col) else None,
                'fracture_doors': float(self.view.tableWidget.item(15, col).text()) if self.view.tableWidget.item(15, col) else None,
                'Normaußentemperatur': float(self.view.tableWidget.item(16, col).text()) if self.view.tableWidget.item(16, col) else None,
                'room_temp': float(self.view.tableWidget.item(17, col).text()) if self.view.tableWidget.item(17, col) else None,
                'max_air_temp_heating': float(self.view.tableWidget.item(18, col).text()) if self.view.tableWidget.item(18, col) else None,
                'Typ_Heizflächen': self.view.tableWidget.item(24, col).text() if self.view.tableWidget.item(24, col) else None,
                'VLT_max': float(self.view.tableWidget.item(25, col).text()) if self.view.tableWidget.item(25, col) else None,
                'Steigung_Heizkurve': float(self.view.tableWidget.item(26, col).text()) if self.view.tableWidget.item(26, col) else None,
                'RLT_max': float(self.view.tableWidget.item(27, col).text()) if self.view.tableWidget.item(27, col) else None,
                'Wärmebedarf': float(self.view.tableWidget.item(28, col).text()) if self.view.tableWidget.item(28, col) else None,
                'Warmwasseranteil': float(self.view.tableWidget.item(29, col).text()) if self.view.tableWidget.item(29, col) else None,
                'wall_u': float(self.view.tableWidget.item(19, col).text()) if self.view.tableWidget.item(19, col) else None,
                'roof_u': float(self.view.tableWidget.item(20, col).text()) if self.view.tableWidget.item(20, col) else None,
                'window_u': float(self.view.tableWidget.item(21, col).text()) if self.view.tableWidget.item(21, col) else None,
                'door_u': float(self.view.tableWidget.item(22, col).text()) if self.view.tableWidget.item(22, col) else None,
                'ground_u': float(self.view.tableWidget.item(23, col).text()) if self.view.tableWidget.item(23, col) else None,
            }
            data.append(column_data)
        return data

    def show_filter_dialog(self):
        """
        Shows the filter dialog for LOD2 data filtering.
        """
        dialog = FilterDialog(self.model.get_base_path(), self.config_manager, self.view)
        if dialog.exec_() == QDialog.Accepted:
            filter_method = dialog.filterMethodComboBox.currentText()
            lod_geojson_path = dialog.inputLOD2geojsonLineEdit.text()

            if filter_method == "Filter by Polygon":
                filter_file_path = dialog.inputfilterPolygonLineEdit.text()
            elif filter_method == "Filter by Building Data CSV":
                filter_file_path = dialog.inputfilterBuildingDataLineEdit.text()
                
            output_geojson_path = dialog.outputLOD2geojsonLineEdit.text()

            self.model.filter_data(filter_method, lod_geojson_path, filter_file_path, output_geojson_path)
            self.model.process_data(output_geojson_path)

            # Überprüfen und Laden der U-Werte direkt nach dem Laden der Daten
            for parent_id, info in self.model.building_info.items():
                self.model.check_and_load_u_values(info)

            self.view.update_table(
                self.model.building_info, 
                self.model.get_building_types(), 
                self.model.tabula_building_types,  # Dieser Wert war vorher ausgelassen
                self.model.building_subtypes
            )
            self.view.update_3d_view(self.model.building_info)

    def calculate_heat_demand(self):
        """
        Calculates the heat demand for each building.
        """
        # takes the TRY file from the data manager, could also be implemented as a file dialog
        self.model.try_filename = self.data_manager.get_try_filename()
        self.model.calculate_heat_demand()
        self.view.update_table(self.model.building_info, self.model.get_building_types(), self.model.tabula_building_types, self.model.building_subtypes)

    def create_building_csv(self):
        """
        Creates a CSV file for building data.
        """
        path, _ = QFileDialog.getSaveFileName(self.view, "Speichern unter", self.model.get_base_path(), "CSV-Dateien (*.csv)")
        if path:
            self.model.create_building_csv(path)

    def highlight_building_3d(self, col):
        """
        Highlight the selected building in the 3D view.

        Args:
            col (int): The column index of the selected building.
        """
        parent_id = list(self.model.building_info.keys())[col]
        self.view.highlight_building_3d(parent_id)

    def update_building_subtypes(self, col):
        """
        Updates the subtypes ComboBox based on the selected building type.

        Args:
            col (int): The column index of the selected building.
        """
        building_type = self.view.get_combobox_building_type(col)
        subtypes = self.model.get_building_subtypes(building_type)
        self.view.update_subtype_combobox(col, subtypes)

    def update_u_values(self, col):
        """
        Update U-values when the user interacts with the ComboBoxes in the view.

        Args:
            col (int): The column index of the selected building.
        """
        # Aktuelle Auswahl für Gebäudetyp und Gebäudezustand TABULA abrufen
        building_type = self.view.get_tabula_building_type(col)
        building_state = self.view.get_building_state(col)

        # U-Werte basierend auf der Auswahl neu laden
        wall_u, roof_u, window_u, door_u, ground_u = self.model.get_u_values(building_type, building_state)

        # Aktualisieren der Werte im `info`-Daten
        parent_id = list(self.model.building_info.keys())[col]
        info = self.model.building_info[parent_id]
        info['wall_u'] = wall_u
        info['roof_u'] = roof_u
        info['window_u'] = window_u
        info['door_u'] = door_u
        info['ground_u'] = ground_u

        # Aktualisieren der View
        self.view.update_u_values(col, info)

class LOD2DataVisualization(QWidget):
    """
    The view class for LOD2 data visualization.
    """
    data_selected = pyqtSignal(int)
    u_value_updated = pyqtSignal(int)
    building_type_changed = pyqtSignal(int)
    building_state_changed = pyqtSignal(int)  # Neu: Signal für Änderungen am Gebäudezustand

    def __init__(self, parent=None):
        """
        Initializes the LOD2DataVisualization with UI components.

        Args:
            parent (QWidget, optional): The parent widget.
        """
        super().__init__(parent)
        self.comboBoxBuildingTypesItems = []
        self.building_types = []
        self.building_subtypes = {}
        self.initUI()
        self.visualization_3d = LOD2Visualization3D(self.canvas_3d)  # Initialize the 3D visualization handler

    def initUI(self):
        """
        Initializes the UI components of the LOD2DataVisualization.
        """
        main_layout = QVBoxLayout(self)
        data_vis_layout = QHBoxLayout()
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
        """
        Handles the event when a table column is selected.
        """
        selected_columns = self.tableWidget.selectionModel().selectedColumns()
        if selected_columns:
            col = selected_columns[0].column()
            self.data_selected.emit(col)  # Emit the signal to inform the presenter

    def initialize_u_values(self, building_info):
        """
        Initialize the U-values for all buildings in the table after loading data.

        Args:
            building_info (dict): A dictionary containing building information.
        """
        for col, (parent_id, info) in enumerate(building_info.items()):
            # Wir gehen sicher, dass die U-Werte neu geladen werden, wenn sie None sind
            self.update_u_values(col, info)

    def update_table(self, building_info, comboBoxBuildingTypesItems, building_types, building_subtypes):
        """
        Update the table with new data.

        Args:
            building_info (dict): A dictionary containing building information.
            comboBoxBuildingTypesItems (list): A list of items for the building types ComboBox.
            building_types (list): A list of building types.
            building_subtypes (dict): A dictionary mapping building types to their subtypes.
        """
        self.comboBoxBuildingTypesItems = comboBoxBuildingTypesItems
        self.building_types = building_types
        self.building_subtypes = building_subtypes

        self.tableWidget.setColumnCount(len(building_info))
        self.tableWidget.setHorizontalHeaderLabels([str(i + 1) for i in range(len(building_info))])

        for col, (parent_id, info) in enumerate(building_info.items()):
            self.update_table_column(col, info)

        # Initiale Ausgabe der U-Werte nach dem Aufbau der Tabelle
        self.initialize_u_values(building_info)

    def update_table_column(self, col, info):
        """
        Update a single column in the table.

        Args:
            col (int): The column index to update.
            info (dict): A dictionary containing building information.
        """
        self.tableWidget.setItem(0, col, QTableWidgetItem(str(f"{info['Adresse']}, {info['Stadt']}, {info['Bundesland']}, {info['Land']}")))
        self.tableWidget.setItem(1, col, QTableWidgetItem(str(info['Koordinate_X'])))
        self.tableWidget.setItem(2, col, QTableWidgetItem(str(info['Koordinate_Y'])))
        self.tableWidget.setItem(3, col, QTableWidgetItem(str(round(info['Ground_Area'], 1))))
        self.tableWidget.setItem(4, col, QTableWidgetItem(str(round(info['Wall_Area'], 1))))
        self.tableWidget.setItem(5, col, QTableWidgetItem(str(round(info['Roof_Area'], 1))))
        self.tableWidget.setItem(6, col, QTableWidgetItem(str(round(info['Volume'], 1))))
        self.tableWidget.setItem(7, col, QTableWidgetItem(str(info['Stockwerke'])))

        comboBoxSLPTypes = QComboBox()
        comboBoxSLPTypes.addItems(self.comboBoxBuildingTypesItems)
        comboBoxSLPTypes.setCurrentText(info['Gebäudetyp'])
        comboBoxSLPTypes.currentIndexChanged.connect(lambda idx, col=col: self.building_type_changed.emit(col))
        self.tableWidget.setCellWidget(8, col, comboBoxSLPTypes)

        comboBoxSLPSubtypes = QComboBox()
        comboBoxSLPSubtypes.addItems(self.building_subtypes.get(comboBoxSLPTypes.currentText(), []))
        comboBoxSLPSubtypes.setCurrentText(str(info['Subtyp']))
        self.tableWidget.setCellWidget(9, col, comboBoxSLPSubtypes)

        comboBoxBuildingTypes = QComboBox()
        comboBoxBuildingTypes.addItems(self.building_types)
        comboBoxBuildingTypes.setCurrentText(info.get('Gebäudetyp'))
        comboBoxBuildingTypes.currentIndexChanged.connect(lambda idx, col=col: self.building_type_changed.emit(col))
        self.tableWidget.setCellWidget(10, col, comboBoxBuildingTypes)

        comboBoxBuildingState = QComboBox()
        comboBoxBuildingState.addItems(["Existing_state", "Usual_Refurbishment", "Advanced_Refurbishment", "Individuell"])
        comboBoxBuildingState.setCurrentText(info.get('Gebäudezustand'))
        comboBoxBuildingState.currentIndexChanged.connect(lambda idx, col=col: self.building_state_changed.emit(col))
        self.tableWidget.setCellWidget(11, col, comboBoxBuildingState)

        self.set_default_or_existing_values(col, info)

    def update_subtype_combobox(self, col, subtypes):
        """
        Update the subtype ComboBox with the new subtypes.

        Args:
            col (int): The column index of the ComboBox.
            subtypes (list): A list of subtypes to populate the ComboBox.
        """
        comboBoxSubtypes = self.tableWidget.cellWidget(9, col)
        comboBoxSubtypes.clear()
        comboBoxSubtypes.addItems(subtypes)

    def update_u_values(self, col, info):
        """
        Update U-values in the table widget based on the current selections.

        Args:
            col (int): The column index to update.
            info (dict): A dictionary containing updated building information.
        """
        self.tableWidget.setItem(19, col, QTableWidgetItem(str(info.get('wall_u'))))
        self.tableWidget.setItem(20, col, QTableWidgetItem(str(info.get('roof_u'))))
        self.tableWidget.setItem(21, col, QTableWidgetItem(str(info.get('window_u'))))
        self.tableWidget.setItem(22, col, QTableWidgetItem(str(info.get('door_u'))))
        self.tableWidget.setItem(23, col, QTableWidgetItem(str(info.get('ground_u'))))

    def get_tabula_building_type(self, col):
        """
        Returns the currently selected TABULA building type from the ComboBox.

        Args:
            col (int): The column index of the building type ComboBox.

        Returns:
            str: The selected TABULA building type.
        """
        return self.tableWidget.cellWidget(10, col).currentText()

    def get_building_state(self, col):
        """
        Returns the currently selected building state from the ComboBox.

        Args:
            col (int): The column index of the building state ComboBox.

        Returns:
            str: The selected building state.
        """
        return self.tableWidget.cellWidget(11, col).currentText()

    def set_default_or_existing_values(self, col, info):
        """
        Set default or existing values in the table widget.

        Args:
            col (int): The column index to update.
            info (dict): A dictionary containing building information.
        """
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

    def get_combobox_building_type(self, col):
        """
        Returns the current building type from the ComboBox.

        Args:
            col (int): The column index of the building type ComboBox.

        Returns:
            str: The current building type selected in the ComboBox.
        """
        return self.tableWidget.cellWidget(8, col).currentText()

    def update_3d_view(self, building_info):
        """
        Delegate the update of the 3D view to the LOD2Visualization3D class.

        Args:
            building_info (dict): A dictionary containing building information.
        """
        self.visualization_3d.update_3d_view(building_info)

    def highlight_building_3d(self, parent_id):
        """
        Highlights a building in the 3D plot.

        Args:
            parent_id (str): The ID of the building to highlight.
        """
        self.visualization_3d.highlight_building_3d(parent_id)

    def show_info_message(self, title, message):
        """
        Displays an informational message box.

        Args:
            title (str): The title of the message box.
            message (str): The message to be displayed.
        """
        QMessageBox.information(self, title, message)

class LOD2Visualization3D:
    """
    A class for handling 3D visualization of LOD2 building data.
    """

    def __init__(self, canvas_3d):
        """
        Initialize with the 3D canvas.

        Args:
            canvas_3d (FigureCanvas): The canvas for rendering 3D plots.
        """
        self.figure_3d = canvas_3d.figure
        self.canvas_3d = canvas_3d
        self.building_data = {}  # To keep track of all buildings
        self.highlighted_building_id = None  # To keep track of the highlighted building

    def update_3d_view(self, building_info):
        """
        Update the 3D view with new building data.

        Args:
            building_info (dict): A dictionary containing building information.
        """
        self.building_data = building_info  # Store the current building data
        self.figure_3d.clear()
        ax = self.figure_3d.add_subplot(111, projection='3d')

        # Initialize bounds
        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')

        # Plot each building part and update the bounds
        for parent_id, info in building_info.items():
            color = 'red' if parent_id == self.highlighted_building_id else 'blue'
            min_x, min_y, min_z, max_x, max_y, max_z = self.plot_building_parts(
                ax, info, min_x, min_y, min_z, max_x, max_y, max_z, color)

        # Set plot limits based on calculated bounds
        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
        ax.set_zlim(min_z, max_z)

        # Set the aspect ratio for proper scaling
        ax.set_box_aspect([max_x - min_x, max_y - min_y, max_z - min_z])

        ax.set_xlabel('UTM_X')
        ax.set_ylabel('UTM_Y')
        ax.set_zlabel('Höhe')
        ax.set_title('3D-Visualisierung der LOD2-Daten')

        self.canvas_3d.draw()

    def plot_building_parts(self, ax, info, min_x, min_y, min_z, max_x, max_y, max_z, color):
        """
        Plots the building parts in the 3D plot and updates the bounds.

        Args:
            ax (Axes3D): The 3D axes object.
            info (dict): A dictionary containing building information.
            min_x (float): The minimum X value for bounding the plot.
            min_y (float): The minimum Y value for bounding the plot.
            min_z (float): The minimum Z value for bounding the plot.
            max_x (float): The maximum X value for bounding the plot.
            max_y (float): The maximum Y value for bounding the plot.
            max_z (float): The maximum Z value for bounding the plot.
            color (str): The color to use for the building parts.

        Returns:
            tuple: Updated bounding box values (min_x, min_y, min_z, max_x, max_y, max_z).
        """
        min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(
            ax, info.get('Ground', []), color, min_x, min_y, min_z, max_x, max_y, max_z)
        min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(
            ax, info.get('Wall', []), color, min_x, min_y, min_z, max_x, max_y, max_z)
        min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(
            ax, info.get('Roof', []), color, min_x, min_y, min_z, max_x, max_y, max_z)

        return min_x, min_y, min_z, max_x, max_y, max_z

    def plot_geometry(self, ax, geoms, color, min_x, min_y, min_z, max_x, max_y, max_z):
        """
        Plots the geometry in the 3D plot and updates the bounds.

        Args:
            ax (Axes3D): The 3D axes object.
            geoms (list or shapely.geometry): A list of geometries or a single geometry.
            color (str): The color to use for the geometry.
            min_x (float): The minimum X value for bounding the plot.
            min_y (float): The minimum Y value for bounding the plot.
            min_z (float): The minimum Z value for bounding the plot.
            max_x (float): The maximum X value for bounding the plot.
            max_y (float): The maximum Y value for bounding the plot.
            max_z (float): The maximum Z value for bounding the plot.

        Returns:
            tuple: Updated bounding box values (min_x, min_y, min_z, max_x, max_y, max_z).
        """
        if isinstance(geoms, (Polygon, MultiPolygon)):
            geoms = [geoms]

        for geom in geoms:
            if geom:
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

                # Update bounds
                min_x, min_y, min_z = min(min_x, min(x)), min(min_y, min(y)), min(min_z, min(z))
                max_x, max_y, max_z = max(max_x, max(x)), max(max_y, max(y)), max(max_z, max(z))

        return min_x, min_y, min_z, max_x, max_y, max_z

    def highlight_building_3d(self, parent_id):
        """
        Highlights a specific building in the 3D plot.

        Args:
            parent_id (str): The ID of the building to highlight.
        """
        # Check if the building is already highlighted
        if self.highlighted_building_id == parent_id:
            # Deselect the building by setting the highlighted_building_id to None
            self.highlighted_building_id = None
        else:
            # Highlight the new building
            self.highlighted_building_id = parent_id

        # Re-render the 3D view with the updated highlight
        self.update_3d_view(self.building_data)