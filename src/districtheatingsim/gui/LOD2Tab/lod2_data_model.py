"""
Filename: lod2_data_model.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-28
Description: Contains the LOD2DataModel class for managing and processing LOD2 data.
"""

import sys
import os
import csv
import json
import pandas as pd
import numpy as np

from PyQt5.QtWidgets import QMessageBox

from districtheatingsim.lod2.filter_LOD2 import (
    spatial_filter_with_polygon, filter_LOD2_with_coordinates, 
    process_lod2, calculate_centroid_and_geocode
)
from districtheatingsim.lod2.heat_requirement_LOD2 import Building

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