# This code defines a `Building` class to calculate the heating demand and warm water demand for buildings. 
# It uses the building's physical dimensions, U-values for various components, and air change rate, 
# along with the weather data from a Test Reference Year (TRY) dataset, to estimate the annual heating and warm water needs. 
# The example demonstrates the usage for three buildings with specific dimensions and U-values, outputting their volumes and calculated heat demands.

import os
import sys

import pandas as pd

from lod2.filter_LOD2 import spatial_filter_with_polygon, process_lod2, calculate_centroid_and_geocode

def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist, ist der Basispfad der Temp-Ordner, wo PyInstaller alles extrahiert
        base_path = sys._MEIPASS
    else:
        # Wenn die Anwendung nicht eingefroren ist, ist der Basispfad der Ordner, in dem die Hauptdatei liegt
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return os.path.join(base_path, relative_path)

class Building:
    STANDARD_U_VALUES = {
        'ground_u': 0.31, 'wall_u': 0.23, 'roof_u': 0.19,
        'window_u': 1.3, 'door_u': 1.3, 'air_change_rate': 0.5,
        'floors': 4, 'fracture_windows': 0.10, 'fracture_doors': 0.01,
        'min_air_temp': -15, 'room_temp': 20, 'max_air_temp_heating': 15,
        'ww_demand_Wh_per_m2': 12800
    }

    def __init__(self, ground_area, wall_area, roof_area, building_volume, filename_TRY=get_resource_path("data\\TRY2015_511676144222_Jahr.dat"), u_type=None, building_state=None):
        self.ground_area = ground_area
        self.wall_area = wall_area
        self.roof_area = roof_area
        self.building_volume = building_volume
        self.filename_TRY = filename_TRY
        self.u_values = self.STANDARD_U_VALUES.copy()
        
        if u_type:
            self.u_values.update(self.load_u_values(u_type, building_state))

    def import_TRY(self):
        # Import TRY data for weather conditions
        col_widths = [8, 8, 3, 3, 3, 6, 5, 4, 5, 2, 5, 4, 5, 5, 4, 5, 3]  # Column widths for the data file
        col_names = ["RW", "HW", "MM", "DD", "HH", "t", "p", "WR", "WG", "N", "x", "RF", "B", "D", "A", "E", "IL"]  # Column names
        data = pd.read_fwf(self.filename_TRY, widths=col_widths, names=col_names, skiprows=34)  # Read the file
        self.temperature = data['t'].values  # Store temperature data as numpy array
    
    def calc_heat_demand(self):
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
        #print(f"Transmission heat loss per K: {self.total_heat_loss_per_K:.2f} W/K")

        # Calculate the maximum temperature difference
        self.dT_max_K = self.u_values["room_temp"] - self.u_values["min_air_temp"]
        #print(f"Maximum temperature difference: {self.dT_max_K} K")

        # Calculate transmission heat loss
        self.transmission_heat_loss = self.total_heat_loss_per_K * self.dT_max_K
        #print(f"Transmission heat loss: {self.transmission_heat_loss/1000:.2f} kW")

        # Calculate ventilation heat loss
        self.ventilation_heat_loss = 0.34 * self.u_values["air_change_rate"] * self.building_volume * self.dT_max_K
        #print(f"Ventilation heat loss: {self.ventilation_heat_loss/1000:.2f} kW")

        # Total maximum heating demand
        self.max_heating_demand = self.transmission_heat_loss + self.ventilation_heat_loss
        #print(f"Total heat loss: {self.max_heating_demand/1000:.2f} kW")

    def calc_yearly_heating_demand(self):
        # Load temperature data
        self.import_TRY()
        
         # Calculate the slope and y-intercept of the linear equation to model heating demand
        m = self.max_heating_demand / (self.u_values["min_air_temp"] - self.u_values["max_air_temp_heating"])  # Slope
        b = -m * self.u_values["max_air_temp_heating"]  # Intercept

        # Calculate heating demand for each hour and sum if temperature is below max_air_temp_heating
        self.yearly_heating_demand = sum(max(m * temp + b, 0) for temp in self.temperature if temp < self.u_values["max_air_temp_heating"]) / 1000

        #print(f"Annual heating demand: {self.yearly_heating_demand:.2f} kWh")

    def calc_yearly_warm_water_demand(self):
        # Calculate the annual warm water demand based on area and demand per square meter
        self.yearly_warm_water_demand = self.u_values["ww_demand_Wh_per_m2"] * self.ground_area * self.u_values["floors"] / 1000
        #print(f"Annual warm water demand: {self.yearly_warm_water_demand:.2f} kWh")

    def calc_yearly_heat_demand(self):
        self.calc_heat_demand()
        # Calculate both the yearly heating and warm water demand
        self.calc_yearly_heating_demand()
        self.calc_yearly_warm_water_demand()
        # Sum to get the total annual heat demand
        self.yearly_heat_demand = self.yearly_heating_demand + self.yearly_warm_water_demand
        #print(f"Total annual heat demand: {self.yearly_heat_demand:.2f} kWh")

    def load_u_values(self, u_type, building_state):                
        # Angenommen, die CSV-Datei heißt 'u_values.csv' und befindet sich im gleichen Verzeichnis
        df = pd.read_csv(get_resource_path('data\\standard_u_values_TABULA.csv'), sep=";")
        u_values_row = df[(df['Typ'] == u_type) & (df['building_state'] == building_state)]
        
        if not u_values_row.empty:
            # Umwandeln der ersten Zeile in ein Dictionary, ohne die Typ- und Gebäudezustandsspalte
            return u_values_row.iloc[0].drop(['Typ', 'building_state']).to_dict()
        else:
            print(f"Keine U-Werte für Typ '{u_type}' und Zustand '{building_state}' gefunden. Verwende Standardwerte.")
            return {}

def calculate_heat_demand_for_lod2_area(lod_geojson_path, polygon_shapefile_path, output_geojson_path, output_csv_path):
    # Verwenden der bereits definierte Funktion, um LOD2-Daten zu filtern
    spatial_filter_with_polygon(lod_geojson_path, polygon_shapefile_path, output_geojson_path)

    # Verwenden von process_lod2, um die gefilterten Daten zu verarbeiten und Gebäudeinformationen zu erhalten
    building_data = process_lod2(output_geojson_path)

    # Geocodiere die Daten
    building_data = calculate_centroid_and_geocode(building_data)

    # Iteriere über jedes Gebäude und berechne den Wärmebedarf
    for building_id, info in building_data.items():
        ground_area = info['Ground_Area']
        wall_area = info['Wall_Area']
        roof_area = info['Roof_Area']
        building_volume = info['Volume']
        
        if ground_area is not None and wall_area is not None and roof_area is not None and building_volume is not None:
            print(f"\nBuilding ID: {building_id}, {info['Adresse']}")
            print('Welchen Gebäudetyp hat das Gebäude?:')
            u_type = input()
            #u_type='DE.N.SFH.02.GEN'
            print('Welchen energetischen Zustand hat das Gebäude?:')
            building_state = input()
            #building_state = Existing_state
            #building_state = Usual_Refurbishment
            #building_state = Advanced_Refurbishment

            # Erstellen eines Building-Objekts mit den berechneten Flächen und Standardwerten
            building = Building(ground_area, wall_area, roof_area, building_volume, u_type=u_type, building_state=building_state)
            
            # Führen Sie die Wärmebedarfsberechnung durch
            building.calc_heat_demand()
            building.calc_yearly_heat_demand()
        else:
            print(f"Informationen für Gebäude {building_id} unvollständig. Überspringe Berechnung.")