"""
LOD2 Data Model Module
=====================

Data model for managing and processing LOD2 building data.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-02
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

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import pyqtSignal, QObject

from districtheatingsim.lod2.filter_LOD2 import (
    spatial_filter_with_polygon, filter_LOD2_with_coordinates, 
    process_lod2, calculate_centroid_and_geocode, process_roof
)
from districtheatingsim.lod2.heat_requirement_LOD2 import Building

from districtheatingsim.heat_generators.photovoltaics import Calculate_PV

def transform_coordinates(etrs89_x, etrs89_y):
    """
    Transform coordinates from ETRS89 to WGS84.

    Parameters
    ----------
    etrs89_x : float
        ETRS89 X coordinate in meters.
    etrs89_y : float
        ETRS89 Y coordinate in meters.

    Returns
    -------
    tuple
        Latitude and longitude in WGS84.
    """
    transformer = Transformer.from_crs("EPSG:25833", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(etrs89_x, etrs89_y)
    return lat, lon

class LOD2DataModel(QObject):
    """
    Data model for managing and processing LOD2 building data.
    """

    data_updated = pyqtSignal()

    def __init__(self):
        """Initialize LOD2 data model with default values."""
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
        self.slp_building_types = []
        self.tabula_building_types = []
        self.building_subtypes = {}
        self.try_filename = ""

        self.u_values_df = pd.read_csv(self.get_resource_path('data\\TABULA\\standard_u_values_TABULA.csv'), sep=";")
        self.populateComboBoxes()

    def populateComboBoxes(self):
        """Populate building types and subtypes ComboBoxes from CSV files."""
        slp_df = pd.read_csv(self.get_resource_path('data\\BDEW profiles\\daily_coefficients.csv'), delimiter=';', dtype=str)
        u_values_df = pd.read_csv(self.get_resource_path('data\\TABULA\\standard_u_values_TABULA.csv'), sep=';')
        
        self.slp_building_types = sorted(slp_df['Standardlastprofil'].str[:3].unique())
        self.building_subtypes = {}
        for building_type in self.slp_building_types:
            subtypes = slp_df[slp_df['Standardlastprofil'].str.startswith(building_type)]['Standardlastprofil'].str[-2:].unique()
            self.building_subtypes[building_type] = sorted([self.normalize_subtype(subtype) for subtype in subtypes])

        self.tabula_building_types = sorted(u_values_df['Typ'].unique().tolist())

    def normalize_subtype(self, subtype):
        """
        Normalize subtype to consistent string format.

        Parameters
        ----------
        subtype : str/int/float
            Subtype value.

        Returns
        -------
        str
            Normalized subtype as string.
        """
        subtype_str = str(int(float(subtype)))
        return subtype_str.zfill(2)

    def get_building_types(self):
        """
        Get list of building types for ComboBox.

        Returns
        -------
        list
            List of SLP building types.
        """
        return self.slp_building_types
    
    def get_building_subtypes(self, building_type):
        """
        Get subtypes for given building type.

        Parameters
        ----------
        building_type : str
            Building type.

        Returns
        -------
        list
            List of subtypes for building type.
        """
        return self.building_subtypes.get(building_type, [])

    def process_data(self, output_geojson_path):
        """
        Process loaded data to calculate building parameters.

        Parameters
        ----------
        output_geojson_path : str
            Path to GeoJSON file for processed data.
        """
        self.output_geojson_path = output_geojson_path

        self.building_info = process_lod2(self.output_geojson_path, self.standard_values)
        self.roof_info = process_roof(self.output_geojson_path)
        
        address_missing = any(info['Adresse'] is None for info in self.building_info.values())
        if address_missing:
            self.building_info = calculate_centroid_and_geocode(self.building_info)
            self.roof_info = calculate_centroid_and_geocode(self.roof_info)

        self.check_and_load_u_values()

    def update_data_value(self, row, key, value):
        """
        Update single building property and emit signal if changed.

        Parameters
        ----------
        row : int
            Building row index.
        key : str
            Attribute name to update.
        value : str/int/float
            New value.
        """
        parent_id = list(self.building_info.keys())[row]

        if key == 'Subtyp':
            value = self.normalize_subtype(value)

        if self.building_info[parent_id].get(key) != value:
            self.building_info[parent_id][key] = value

            if key in ["Typ", "Gebäudezustand"]:
                self.update_u_values(row)

            self.data_updated.emit()

    def get_u_values(self, building_type, building_state):
        """
        Get U-values based on building type and state.

        Parameters
        ----------
        building_type : str
            Building type.
        building_state : str
            Building state.

        Returns
        -------
        tuple
            U-values for wall, roof, window, door, and ground.
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
        """
        Update U-values based on building type and state.

        Parameters
        ----------
        row : int
            Building row index.
        """
        parent_id = list(self.building_info.keys())[row]
        
        building_type = self.building_info[parent_id].get("Typ")
        building_state = self.building_info[parent_id].get("Gebäudezustand")

        wall_u, roof_u, window_u, door_u, ground_u = self.get_u_values(building_type, building_state)

        self.building_info[parent_id]['wall_u'] = wall_u
        self.building_info[parent_id]['roof_u'] = roof_u
        self.building_info[parent_id]['window_u'] = window_u
        self.building_info[parent_id]['door_u'] = door_u
        self.building_info[parent_id]['ground_u'] = ground_u

        self.data_updated.emit()

    def check_and_load_u_values(self):
        """Check and load U-values if missing from dataset."""
        for parent_id, info in self.building_info.items():
            if 'Typ' not in info or info['Typ'] is None:
                info['Typ'] = self.tabula_building_types[0]
            if 'Gebäudezustand' not in info or info['Gebäudezustand'] is None:
                info['Gebäudezustand'] = 'Existing_state'

            if info.get('wall_u') is None or \
            info.get('roof_u') is None or \
            info.get('window_u') is None or \
            info.get('door_u') is None or \
            info.get('ground_u') is None:
            
                building_type = info.get('Typ')
                building_state = info.get('Gebäudezustand')
                wall_u, roof_u, window_u, door_u, ground_u = self.get_u_values(building_type, building_state)
                
                info['wall_u'] = wall_u
                info['roof_u'] = roof_u
                info['window_u'] = window_u
                info['door_u'] = door_u
                info['ground_u'] = ground_u

    def calculate_heat_demand(self):
        """Calculate heat demand for each building."""
        for parent_id, info in self.building_info.items():
            u_values = {
                'wall_u': info.get('wall_u', None),
                'roof_u': info.get('roof_u', None),
                'window_u': info.get('window_u', None),
                'door_u': info.get('door_u', None),
                'ground_u': info.get('ground_u', None),
            }

            building = Building(
                ground_area=info['Ground_Area'],
                wall_area=info['Wall_Area'],
                roof_area=info['Roof_Area'],
                building_volume=info['Volume'],
                u_type=info.get('Typ'),
                building_state=info.get('Gebäudezustand'),
                filename_TRY=self.try_filename,
                u_values=u_values
            )
            building.calc_yearly_heat_demand()
            
            info['Wärmebedarf'] = np.round(building.yearly_heat_demand,2)
            info['WW_Anteil'] = np.round(building.warm_water_share,2)

    def calculate_pv_data(self, output_filename):
        """
        Calculate PV data for each building and roof.

        Parameters
        ----------
        output_filename : str
            Output file path for PV results.
        """
        try:            
            results = []

            for parent_id, roof_info in self.roof_info.items():
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

                        yield_MWh, max_power, _ = Calculate_PV(
                            self.try_filename,
                            Gross_area=roof_area,
                            Longitude=longitude,
                            STD_Longitude=15,
                            Latitude=latitude,
                            Albedo=0.2,
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

            results_df = pd.DataFrame(results)
            results_df.to_csv(output_filename, index=False, sep=';')

            self.data_updated.emit()

        except Exception as e:
            raise Exception(f"Failed to calculate PV data: {str(e)}\n{traceback.format_exc()}")
    
    def get_resource_path(self, relative_path):
        """
        Get absolute path to resource.

        Parameters
        ----------
        relative_path : str
            Relative path to resource.

        Returns
        -------
        str
            Absolute path to resource.
        """
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        return os.path.join(base_path, relative_path)
    
    def set_base_path(self, base_path):
        """
        Set base path for file operations.

        Parameters
        ----------
        base_path : str
            Base path for file operations.
        """
        self.base_path = base_path

    def get_base_path(self):
        """
        Get current base path.

        Returns
        -------
        str
            Current base path.
        """
        return self.base_path
    
    def filter_data(self, method, lod_geojson_path, filter_file_path, output_geojson_path):
        """
        Filter LOD2 data based on specified method.

        Parameters
        ----------
        method : str
            Filtering method to use.
        lod_geojson_path : str
            Path to input GeoJSON file.
        filter_file_path : str
            Path to filter file.
        output_geojson_path : str
            Path to save filtered GeoJSON file.
        
        Raises
        ------
        ValueError
            If unknown filter method provided.
        """
        if method == "Filter by Polygon":
            spatial_filter_with_polygon(lod_geojson_path, filter_file_path, output_geojson_path)
        elif method == "Filter by Building Data CSV":
            filter_LOD2_with_coordinates(lod_geojson_path, filter_file_path, output_geojson_path)
        else:
            raise ValueError(f"Unknown filter method: {method}")

    def save_data_as_geojson(self, path):
        """
        Update existing GeoJSON file with current model data.

        Parameters
        ----------
        path : str
            Save path for GeoJSON file.

        Raises
        ------
        Exception
            If saving fails.
        """
        try:
            gdf = gpd.read_file(self.output_geojson_path)

            for idx, row in gdf.iterrows():
                parent_id = row.get("parent_id")

                if parent_id in self.building_info:
                    for key, value in self.building_info[parent_id].items():
                        if isinstance(value, list):
                            value = str(value)
                        gdf.at[idx, key] = value

            gdf.to_file(path, driver='GeoJSON', encoding='utf-8')

        except Exception as e:
            raise Exception(f"Failed to save data to {path}: {str(e)}\n{traceback.format_exc()}")
        
    def load_data(self, filename):
        """
        Load data from GeoJSON file.

        Parameters
        ----------
        filename : str
            Path to GeoJSON file to load.

        Raises
        ------
        Exception
            If loading fails.
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
            raise Exception(f"Failed to load data from {filename}: {str(e)}\n{traceback.format_exc()}")
        
    def create_building_csv(self, path):
        """
        Create CSV file with building data.

        Parameters
        ----------
        path : str
            Path where CSV file will be saved.

        Raises
        ------
        Exception
            If saving CSV file fails.
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
        Get row data for building CSV.

        Parameters
        ----------
        info : dict
            Dictionary containing building information.

        Returns
        -------
        list
            List representing CSV row.
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