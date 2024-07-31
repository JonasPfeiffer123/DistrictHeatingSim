"""
Filename: heat_requirement_LOD2.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: This code defines a `Building` class to calculate the heating demand and warm water demand for buildings. 
             It uses the building's physical dimensions, U-values for various components, and air change rate, 
             along with the weather data from a Test Reference Year (TRY) dataset, to estimate the annual heating and warm water needs. 
             The example demonstrates the usage for three buildings with specific dimensions and U-values, outputting their volumes and calculated heat demands.
"""

import os
import sys

import pandas as pd

from lod2.filter_LOD2 import spatial_filter_with_polygon, process_lod2, calculate_centroid_and_geocode

def get_resource_path(relative_path):
    """
    Get the absolute path to the resource, works for dev and for PyInstaller.

    Args:
        relative_path (str): The relative path to the resource.

    Returns:
        str: The absolute path to the resource.
    """
    if getattr(sys, 'frozen', False):
        # If the application is frozen, the base path is the temp folder where PyInstaller extracts everything
        base_path = sys._MEIPASS
    else:
        # If the application is not frozen, the base path is the directory where the main file is located
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

class Building:
    """
    A class to represent a building and calculate its heating and warm water demands.

    Attributes:
        ground_area (float): Ground area of the building.
        wall_area (float): Wall area of the building.
        roof_area (float): Roof area of the building.
        building_volume (float): Volume of the building.
        filename_TRY (str): Filename of the TRY dataset.
        u_values (dict): U-values for various building components.
    """

    STANDARD_U_VALUES = {
        'ground_u': 0.31, 'wall_u': 0.23, 'roof_u': 0.19,
        'window_u': 1.3, 'door_u': 1.3, 'air_change_rate': 0.5,
        'floors': 4, 'fracture_windows': 0.10, 'fracture_doors': 0.01,
        'min_air_temp': -12, 'room_temp': 20, 'max_air_temp_heating': 15,
        'ww_demand_kWh_per_m2': 12.8
    }

    def __init__(self, ground_area, wall_area, roof_area, building_volume, filename_TRY=get_resource_path("data\\TRY2015_511676144222_Jahr.dat"), u_type=None, building_state=None, u_values=None):
        """
        Initializes the Building object.

        Args:
            ground_area (float): Ground area of the building.
            wall_area (float): Wall area of the building.
            roof_area (float): Roof area of the building.
            building_volume (float): Volume of the building.
            filename_TRY (str, optional): Filename of the TRY dataset. Defaults to 'data\\TRY2015_511676144222_Jahr.dat'.
            u_type (str, optional): Type of the building.
            building_state (str, optional): State of the building.
            u_values (dict, optional): Custom U-values for the building components.
        """
        self.ground_area = ground_area
        self.wall_area = wall_area
        self.roof_area = roof_area
        self.building_volume = building_volume
        self.filename_TRY = filename_TRY
        self.u_values = self.STANDARD_U_VALUES.copy()
        
        if u_values:
            self.u_values.update(u_values)
        elif u_type and building_state:
            self.u_values.update(self.load_u_values(u_type, building_state))

    def import_TRY(self):
        """
        Imports TRY data for weather conditions.
        """
        col_widths = [8, 8, 3, 3, 3, 6, 5, 4, 5, 2, 5, 4, 5, 5, 4, 5, 3]  # Column widths for the data file
        col_names = ["RW", "HW", "MM", "DD", "HH", "t", "p", "WR", "WG", "N", "x", "RF", "B", "D", "A", "E", "IL"]  # Column names
        data = pd.read_fwf(self.filename_TRY, widths=col_widths, names=col_names, skiprows=34)  # Read the file
        self.temperature = data['t'].values  # Store temperature data as numpy array
    
    def calc_heat_demand(self):
        """
        Calculates the heat demand for the building.
        """
        # Calculate the areas of windows and doors and the actual wall area excluding windows and doors
        self.window_area = self.wall_area * self.u_values["fracture_windows"]
        self.door_area = self.wall_area * self.u_values["fracture_doors"]
        self.real_wall_area = self.wall_area - self.window_area - self.door_area

        # Calculate heat loss per K for each component
        heat_loss_per_K = {
            'wall': self.real_wall_area * self.u_values["wall_u"],
            'ground': self.ground_area * self.u_values["ground_u"],
            'roof': self.roof_area * self.u_values["roof_u"],
            'window': self.window_area * self.u_values["window_u"],
            'door': self.door_area * self.u_values["door_u"]
        }

        self.total_heat_loss_per_K = sum(heat_loss_per_K.values())

        # Calculate the maximum temperature difference
        self.dT_max_K = self.u_values["room_temp"] - self.u_values["min_air_temp"]

        # Calculate transmission heat loss
        self.transmission_heat_loss = self.total_heat_loss_per_K * self.dT_max_K

        # Calculate ventilation heat loss
        self.ventilation_heat_loss = 0.34 * self.u_values["air_change_rate"] * self.building_volume * self.dT_max_K

        # Total maximum heating demand
        self.max_heating_demand = self.transmission_heat_loss + self.ventilation_heat_loss

    def calc_yearly_heating_demand(self):
        """
        Calculates the yearly heating demand for the building.
        """
        # Load temperature data
        self.import_TRY()
        
        # Calculate the slope and y-intercept of the linear equation to model heating demand
        m = self.max_heating_demand / (self.u_values["min_air_temp"] - self.u_values["max_air_temp_heating"])  # Slope
        b = -m * self.u_values["max_air_temp_heating"]  # Intercept

        # Calculate heating demand for each hour and sum if temperature is below max_air_temp_heating
        self.yearly_heating_demand = sum(max(m * temp + b, 0) for temp in self.temperature if temp < self.u_values["max_air_temp_heating"]) / 1000

    def calc_yearly_warm_water_demand(self):
        """
        Calculates the yearly warm water demand for the building.
        """
        # Calculate the annual warm water demand based on area and demand per square meter
        self.yearly_warm_water_demand = self.u_values["ww_demand_kWh_per_m2"] * self.ground_area * self.u_values["floors"]

    def calc_yearly_heat_demand(self):
        """
        Calculates the total yearly heat demand for the building.
        """
        self.calc_heat_demand()
        self.calc_yearly_heating_demand()
        self.calc_yearly_warm_water_demand()
        # Sum to get the total annual heat demand
        self.yearly_heat_demand = self.yearly_heating_demand + self.yearly_warm_water_demand
        # Calculate warm water share
        self.warm_water_share = (self.yearly_warm_water_demand / self.yearly_heat_demand) * 100

    def load_u_values(self, u_type, building_state):
        """
        Loads U-values for the building based on type and state.

        Args:
            u_type (str): Type of the building.
            building_state (str): State of the building.

        Returns:
            dict: U-values for the building components.
        """
        # Assuming the CSV file is named 'u_values.csv' and located in the same directory
        df = pd.read_csv(get_resource_path('lod2\\data\\standard_u_values_TABULA.csv'), sep=";")
        u_values_row = df[(df['Typ'] == u_type) & (df['building_state'] == building_state)]
        
        if not u_values_row.empty:
            # Convert the first row to a dictionary, excluding the Type and building_state columns
            return u_values_row.iloc[0].drop(['Typ', 'building_state']).to_dict()
        else:
            print(f"No U-values found for type '{u_type}' and state '{building_state}'. Using standard values.")
            return {}

def calculate_heat_demand_for_lod2_area(lod_geojson_path, polygon_shapefile_path, output_geojson_path, output_csv_path):
    """
    Calculates the heat demand for buildings in a given LOD2 area.

    Args:
        lod_geojson_path (str): Path to the LOD2 GeoJSON file.
        polygon_shapefile_path (str): Path to the polygon shapefile for spatial filtering.
        output_geojson_path (str): Path to the output GeoJSON file.
        output_csv_path (str): Path to the output CSV file.
    """
    # Use the already defined function to filter LOD2 data
    spatial_filter_with_polygon(lod_geojson_path, polygon_shapefile_path, output_geojson_path)

    # Use process_lod2 to process the filtered data and get building information
    building_data = process_lod2(output_geojson_path)

    # Geocode the data
    building_data = calculate_centroid_and_geocode(building_data)

    # Iterate over each building and calculate the heat demand
    for building_id, info in building_data.items():
        ground_area = info['Ground_Area']
        wall_area = info['Wall_Area']
        roof_area = info['Roof_Area']
        building_volume = info['Volume']
        
        if ground_area is not None and wall_area is not None and roof_area is not None and building_volume is not None:
            print(f"\nBuilding ID: {building_id}, {info['Adresse']}")
            print('Welchen Gebäudetyp hat das Gebäude?:')
            u_type = input()
            print('Welchen energetischen Zustand hat das Gebäude?:')
            building_state = input()

            # Create a Building object with the calculated areas and standard values
            building = Building(ground_area, wall_area, roof_area, building_volume, u_type=u_type, building_state=building_state)
            
            # Perform the heat demand calculation
            building.calc_heat_demand()
            building.calc_yearly_heat_demand()
        else:
            print(f"Informationen für Gebäude {building_id} unvollständig. Überspringe Berechnung.")