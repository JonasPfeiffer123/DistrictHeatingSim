# This code defines a `Building` class to calculate the heating demand and warm water demand for buildings. 
# It uses the building's physical dimensions, U-values for various components, and air change rate, 
# along with the weather data from a Test Reference Year (TRY) dataset, to estimate the annual heating and warm water needs. 
# The example demonstrates the usage for three buildings with specific dimensions and U-values, outputting their volumes and calculated heat demands.


import pandas as pd
from math import sqrt

class Building:
    def __init__(self, ground_area, wall_area, roof_area, building_volume, fracture_windows, fracture_doors, floors,
                 ground_u=1.5, wall_u=1.7, roof_u=1.2, window_u=1.6, door_u=2.5, air_change_rate=0.5,
                 min_air_temp=-15, room_temp=20, max_air_temp_heating=15, ww_demand_Wh_per_m2=12800):
        # Initialize building parameters: areas, volume, U-values (thermal transmittance), etc.
        self.ground_area = ground_area
        self.wall_area = wall_area
        self.roof_area = roof_area
        self.building_volume = building_volume  # Building volume in cubic meters
        self.fracture_windows = fracture_windows  # Fraction of wall area covered by windows
        self.fracture_doors = fracture_doors  # Fraction of wall area covered by doors
        self.floors = floors  # Number of floors
        # U-values for various components
        self.ground_u = ground_u
        self.wall_u = wall_u
        self.roof_u = roof_u
        self.window_u = window_u
        self.door_u = door_u
        self.air_change_rate = air_change_rate  # Air change rate in h-1
        # Temperature settings
        self.min_air_temp = min_air_temp
        self.room_temp = room_temp
        self.max_air_temp_heating = max_air_temp_heating
        # Warm water demand
        self.ww_demand_Wh_per_m2 = ww_demand_Wh_per_m2
        # Filename for TRY (Test Reference Year) data
        self.filename_TRY = "heat_requirement/TRY_511676144222/TRY2015_511676144222_Jahr.dat"

    def import_TRY(self):
        # Import TRY data for weather conditions
        col_widths = [8, 8, 3, 3, 3, 6, 5, 4, 5, 2, 5, 4, 5, 5, 4, 5, 3]  # Column widths for the data file
        col_names = ["RW", "HW", "MM", "DD", "HH", "t", "p", "WR", "WG", "N", "x", "RF", "B", "D", "A", "E", "IL"]  # Column names
        data = pd.read_fwf(self.filename_TRY, widths=col_widths, names=col_names, skiprows=34)  # Read the file
        self.temperature = data['t'].values  # Store temperature data as numpy array
    
    def calc_heat_demand(self):
        # Calculate the areas of windows and doors and the actual wall area excluding windows and doors
        self.window_area = self.wall_area * self.fracture_windows
        self.door_area = self.wall_area * self.fracture_doors
        self.real_wall_area = self.wall_area - self.window_area - self.door_area

        # Calculate heat loss per K for each component
        heat_loss_per_K = {
            'wall': self.real_wall_area * self.wall_u,
            'ground': self.ground_area * self.ground_u,
            'roof': self.roof_area * self.roof_u,
            'window': self.window_area * self.window_u,
            'door': self.door_area * self.door_u
        }

        self.total_heat_loss_per_K = sum(heat_loss_per_K.values())
        print(f"Transmission heat loss per K: {self.total_heat_loss_per_K:.2f} W/K")

        # Calculate the maximum temperature difference
        self.dT_max_K = self.room_temp - self.min_air_temp
        print(f"Maximum temperature difference: {self.dT_max_K} K")

        # Calculate transmission heat loss
        self.transmission_heat_loss = self.total_heat_loss_per_K * self.dT_max_K
        print(f"Transmission heat loss: {self.transmission_heat_loss/1000:.2f} kW")

        # Calculate ventilation heat loss
        self.ventilation_heat_loss = 0.34 * self.air_change_rate * self.building_volume * self.dT_max_K
        print(f"Ventilation heat loss: {self.ventilation_heat_loss/1000:.2f} kW")

        # Total maximum heating demand
        self.max_heating_demand = self.transmission_heat_loss + self.ventilation_heat_loss
        print(f"Total heat loss: {self.max_heating_demand/1000:.2f} kW")

    def calc_yearly_heating_demand(self):
        # Load temperature data
        self.import_TRY()
        
         # Calculate the slope and y-intercept of the linear equation to model heating demand
        m = self.max_heating_demand / (self.min_air_temp - self.max_air_temp_heating)  # Slope
        b = -m * self.max_air_temp_heating  # Intercept

        # Calculate heating demand for each hour and sum if temperature is below max_air_temp_heating
        self.yearly_heating_demand = sum(max(m * temp + b, 0) for temp in self.temperature if temp < self.max_air_temp_heating) / 1000

        print(f"Annual heating demand: {self.yearly_heating_demand:.2f} kWh")

    def calc_yearly_warm_water_demand(self):
        # Calculate the annual warm water demand based on area and demand per square meter
        self.yearly_warm_water_demand = self.ww_demand_Wh_per_m2 * self.ground_area * self.floors / 1000
        print(f"Annual warm water demand: {self.yearly_warm_water_demand:.2f} kWh")

    def calc_yearly_heat_demand(self):
        # Calculate both the yearly heating and warm water demand
        self.calc_yearly_heating_demand()
        self.calc_yearly_warm_water_demand()
        # Sum to get the total annual heat demand
        self.yearly_heat_demand = self.yearly_heating_demand + self.yearly_warm_water_demand
        print(f"Total annual heat demand: {self.yearly_heat_demand:.2f} kWh")

### Example building measurements for buildings on Dresdner Straße in Bautzen ###
ground_area_1 = 748.65680
ground_area_2 = 534.66489
ground_area_3 = 740.18520

wall_area_1 = 2203.07
wall_area_2 = 1564.57
wall_area_3 = 2240.53

roof_area_1 = 930.44
roof_area_2 = 667.91
roof_area_3 = 925.43

# Calculate the building height by subtracting the ground height from the eaves height
height_1 = 225.65 - 211.646 # H_Traufe - H_Boden
height_2 = 222.034 - 209.435 # H_Traufe - H_Boden
height_3 = 223.498 - 210.599 # H_Traufe - H_Boden

# Calculate building volume using height and ground area
building_volume_1 = height_1 * ground_area_1
building_volume_2 = height_2 * ground_area_2
building_volume_3 = height_3 * ground_area_3

print(building_volume_1, building_volume_2, building_volume_3)

# Instantiate buildings with the given parameters and U-values
building1 = Building(ground_area=ground_area_1, wall_area=wall_area_1, roof_area=roof_area_1, building_volume=building_volume_1, fracture_windows=0.10, fracture_doors=0.01, floors=4, ground_u=0.31, wall_u=0.23, roof_u=0.19, window_u=1.3, door_u=1.3)
building2 = Building(ground_area=ground_area_2, wall_area=wall_area_2, roof_area=roof_area_2, building_volume=building_volume_2, fracture_windows=0.10, fracture_doors=0.01, floors=4, ground_u=0.31, wall_u=0.23, roof_u=0.19, window_u=1.3, door_u=1.3)
building3 = Building(ground_area=ground_area_3, wall_area=wall_area_3, roof_area=roof_area_3, building_volume=building_volume_3, fracture_windows=0.10, fracture_doors=0.01, floors=4, ground_u=0.31, wall_u=0.23, roof_u=0.19, window_u=1.3, door_u=1.3)

print("\nBuilding 1: Dresdner Str. 30")
building1.calc_heat_demand()
building1.calc_yearly_heat_demand()

print("\nBuilding 2: Dresdner Str. 26")
building2.calc_heat_demand()
building2.calc_yearly_heat_demand()

print("\nBuilding 3: Dresdner Str. 28")
building3.calc_heat_demand()
building3.calc_yearly_heat_demand()