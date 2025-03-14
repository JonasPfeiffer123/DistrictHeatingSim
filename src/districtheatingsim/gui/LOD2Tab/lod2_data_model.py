"""
Filename: lod2_data_model.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-02
Description: Contains the LOD2DataModel class for managing and processing LOD2 data.
"""

import sys
import os
import csv
import pandas as pd
import numpy as np
import geopandas as gpd
import traceback
from pyproj import Transformer
import traceback

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import pyqtSignal, QObject

from districtheatingsim.lod2.filter_LOD2 import (
    spatial_filter_with_polygon, filter_LOD2_with_coordinates, 
    process_lod2, calculate_centroid_and_geocode, process_roof
)
from districtheatingsim.lod2.heat_requirement_LOD2 import Building

from districtheatingsim.heat_generators.photovoltaics import Calculate_PV

def transform_coordinates(etrs89_x, etrs89_y):
    """
    Transforms coordinates from ETRS89 (EPSG:25833) to WGS84 (EPSG:4326).

    Args:
        etrs89_x (float): ETRS89 X coordinate (in meters).
        etrs89_y (float): ETRS89 Y coordinate (in meters).

    Returns:
        tuple: Latitude and Longitude in WGS84.
    """
    transformer = Transformer.from_crs("EPSG:25833", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(etrs89_x, etrs89_y)
    return lat, lon

class LOD2DataModel(QObject):
    """
    A model to manage and process LOD2 data for building energy simulations.
    """

    data_updated = pyqtSignal()  # Signal für Änderungen

    def __init__(self):
        """
        Initializes the LOD2DataModel with default values and loads necessary resources.
        """
        super().__init__()
        self.building_info = {}

        self.standard_values = {
            'Gebäudetyp': 'HMF',
            'Subtyp': '03',
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
            self.building_subtypes[building_type] = sorted([self.normalize_subtype(subtype) for subtype in subtypes])

        # Für TABULA-Gebäudetyp (Stelle sicher, dass diese Daten korrekt aus dem richtigen Datensatz stammen)
        self.tabula_building_types = sorted(u_values_df['Typ'].unique().tolist())

    def normalize_subtype(self, subtype):
        """
        Normalize the subtype to a consistent string format.

        Args:
            subtype (str/int/float): The subtype value.

        Returns:
            str: The normalized subtype value as a string.
        """
        subtype_str = str(int(float(subtype)))  # Convert to int first to handle float values like 3.0
        return subtype_str.zfill(2)  # Ensure the subtype has two digits

    def get_building_types(self):
        """
        Get a list of building types for the ComboBox.

        Returns:
            list: A list of SLP building types.
        """
        return self.slp_building_types
    
    def get_building_subtypes(self, building_type):
        """
        Get the subtypes for a given building type.

        Args:
            building_type (str): The building type.

        Returns:
            list: A list of subtypes for the given building type.
        """
        return self.building_subtypes.get(building_type, [])

    def process_data(self, output_geojson_path):
        """
        Process the loaded data to calculate required building parameters.

        Args:
            output_geojson_path (str): The path to the GeoJSON file that will store the processed data.
        """
        self.output_geojson_path = output_geojson_path

        self.building_info = process_lod2(self.output_geojson_path, self.standard_values)
        self.roof_info = process_roof(self.output_geojson_path)
        
        address_missing = any(info['Adresse'] is None for info in self.building_info.values())
        if address_missing:
            self.building_info = calculate_centroid_and_geocode(self.building_info)
            self.roof_info = calculate_centroid_and_geocode(self.roof_info)

        # Überprüfen und Laden der U-Werte für jedes Gebäude
        self.check_and_load_u_values()

    def update_data_value(self, row, key, value):
        """
        Aktualisiert eine einzelne Eigenschaft eines Gebäudes und sendet nur ein Signal, wenn sich der Wert tatsächlich geändert hat.

        Args:
            row (int): Zeilenindex des Gebäudes.
            key (str): Attributname, das aktualisiert wird.
            value (str/int/float): Neuer Wert.
        """
        parent_id = list(self.building_info.keys())[row]

        # Normalize value if key is 'Subtyp'
        if key == 'Subtyp':
            value = self.normalize_subtype(value)

        # Prüfen, ob sich der Wert tatsächlich geändert hat, bevor wir eine Aktualisierung senden
        if self.building_info[parent_id].get(key) != value:
            self.building_info[parent_id][key] = value

            # Falls sich Gebäudetyp oder Zustand geändert hat, U-Werte aktualisieren
            if key in ["Typ", "Gebäudezustand"]:
                self.update_u_values(row)

            # which value is changed
            self.data_updated.emit()  # Signal senden nur wenn sich Werte geändert haben

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
    
    def update_u_values(self, row):
        """ Aktualisiert die U-Werte basierend auf Gebäudetyp und Zustand. """
        parent_id = list(self.building_info.keys())[row]
        
        # Werte auslesen
        building_type = self.building_info[parent_id].get("Typ")
        building_state = self.building_info[parent_id].get("Gebäudezustand")

        # Neue U-Werte abrufen
        wall_u, roof_u, window_u, door_u, ground_u = self.get_u_values(building_type, building_state)

        # Werte im Model aktualisieren
        self.building_info[parent_id]['wall_u'] = wall_u
        self.building_info[parent_id]['roof_u'] = roof_u
        self.building_info[parent_id]['window_u'] = window_u
        self.building_info[parent_id]['door_u'] = door_u
        self.building_info[parent_id]['ground_u'] = ground_u

        # Signal senden, dass sich die Daten geändert haben
        self.data_updated.emit()

    def check_and_load_u_values(self):
        """
        Check if U-values are already in the dataset. 
        If not, load them based on TABULA information.
        """

        for parent_id, info in self.building_info.items():
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
            info['WW_Anteil'] = np.round(building.warm_water_share,2)

    def calculate_pv_data(self, output_filename):
        """
        Calculate PV data for each building and roof.
        """
        try:            
            results = []

            # Loop through each building and each roof for calculation
            for parent_id, roof_info in self.roof_info.items():
                # Transform coordinates from ETRS89 to WGS84
                latitude, longitude = transform_coordinates(
                    roof_info['Koordinate_X'], roof_info['Koordinate_Y']
                )

                for roof in roof_info.get('Roofs', []):
                    roof_areas = roof['Area'] if isinstance(roof['Area'], list) else [roof['Area']]
                    roof_slopes = roof['Roof_Slope'] if isinstance(roof['Roof_Slope'], list) else [roof['Roof_Slope']]
                    roof_orientations = roof['Roof_Orientation'] if isinstance(roof['Roof_Orientation'], list) else [roof['Roof_Orientation']]

                    for i in range(len(roof_areas)):
                        roof_area = float(roof_areas[i])
                        roof_slope = float(roof_slopes[i])
                        roof_orientation = float(roof_orientations[i])

                        # Calculate PV for the current roof segment
                        yield_MWh, max_power, _ = Calculate_PV(
                            self.try_filename,
                            Gross_area=roof_area,
                            Longitude=longitude,
                            STD_Longitude=15,  # Replace with the correct standard longitude
                            Latitude=latitude,
                            Albedo=0.2,  # Example albedo value, adjust as necessary
                            East_West_collector_azimuth_angle=roof_orientation,
                            Collector_tilt_angle=roof_slope
                        )

                        results.append({
                            'Building': roof_info['Adresse'],
                            'Latitude': latitude,
                            'Longitude': longitude,
                            'Roof Area (m²)': roof_area,
                            'Slope (°)': roof_slope,
                            'Orientation (°)': roof_orientation,
                            'Yield (MWh)': yield_MWh,
                            'Max Power (kW)': max_power
                        })
            
            self.pv_results = results

            # Save results to CSV
            results_df = pd.DataFrame(results)
            results_df.to_csv(output_filename, index=False, sep=';')

            self.data_updated.emit()  # Signal, dass die Daten aktualisiert wurden

        except Exception as e:
            # traceback zu Exception hinzufügen
            raise Exception(f"Failed to calculate PV data: {str(e)}\n{traceback.format_exc()}")
    
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

    def save_data_as_geojson(self, path):
        """
        Aktualisiert eine vorhandene GeoJSON-Datei mit den neuesten Modelldaten.

        Args:
            path (str): Der Speicherpfad für die GeoJSON-Datei.

        Raises:
            Exception: Falls ein Fehler beim Speichern auftritt.
        """
        try:
            # Bestehendes GeoJSON laden
            gdf = gpd.read_file(self.output_geojson_path)

            # GeoJSON-Properties mit den aktuellen Modelldaten updaten
            for idx, row in gdf.iterrows():
                parent_id = row.get("parent_id")

                if parent_id in self.building_info:
                    for key, value in self.building_info[parent_id].items():
                        # Listen in Zeichenketten umwandeln
                        if isinstance(value, list):
                            value = str(value)
                        gdf.at[idx, key] = value  # Daten aktualisieren

            # Aktualisierte GeoJSON-Datei speichern
            gdf.to_file(path, driver='GeoJSON', encoding='utf-8')

        except Exception as e:
            raise Exception(f"Failed to save data to {path}: {str(e)}\n{traceback.format_exc()}")
        
    def load_data(self, filename):
        """
        Load data from a GeoJSON file and store it in the model.

        Args:
            filename (str): The path to the GeoJSON file to load.

        Raises:
            Exception: If loading the data fails.
        """
        try:
            gdf = gpd.read_file(filename)

            self.building_info = {}
            for idx, row in gdf.iterrows():
                properties = row['properties']
                parent_id = properties.get('parent_id')
                self.building_info[parent_id] = properties

            self.output_geojson_path = filename
        except Exception as e:
            # add traceback to exception message
            raise Exception(f"Failed to load data from {filename}: {str(e)}\n{traceback.format_exc()}")
        
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