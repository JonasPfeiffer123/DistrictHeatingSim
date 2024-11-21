"""
Filename: 11_example_lod2.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-21
Description: Example for the calculation of heat demand for LOD2 buildings.
Usage:
    Run the script to calculate the heat demand for a set of buildings based on LOD2 data.
    The script also demonstrates how to filter LOD2 data based on addresses and polygons.
Functions:
    test_building_calculation: Calculate the heat demand for a set of buildings based on building measurements.
    test_lod2_adress_filter: Filter LOD2 data based on addresses.
    test_lod2_polygon_filter: Filter LOD2 data based on polygons.
    test_lod2_building_caclulation: Calculate the heat demand for buildings based on LOD2 data.
Examples:
    $ python 11_example_lod2.py

"""

from districtheatingsim.lod2.filter_LOD2 import spatial_filter_with_polygon, filter_LOD2_with_coordinates
from districtheatingsim.lod2.heat_requirement_LOD2 import calculate_heat_demand_for_lod2_area, Building

def test_building_calculation():
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
    
    # import TRY data for Germany
    TRY_filename = "examples\data\TRY\TRY_511676144222\TRY2015_511676144222_Jahr.dat"

    # TABULA U-Values for Germany
    u_type = "DE.N.MFH.10.GEN" # various types of buildings, e.g. DE.N.MFH.10.GEN, DE.N.MFH.09.GEN, DE.N.MFH.11.GEN or other building types
    building_state = "Existing_state" # Existing_state, Usual_refurbishement, Advanced_refurbishment
    u_values = None 
        
    # Instantiate buildings with the given parameters and U-values
    building1 = Building(ground_area=ground_area_1, wall_area=wall_area_1, roof_area=roof_area_1, building_volume=building_volume_1, filename_TRY=TRY_filename, u_type=u_type, building_state=building_state, u_values=u_values)
    building2 = Building(ground_area=ground_area_2, wall_area=wall_area_2, roof_area=roof_area_2, building_volume=building_volume_2, filename_TRY=TRY_filename, u_type=u_type, building_state=building_state, u_values=u_values)
    building3 = Building(ground_area=ground_area_3, wall_area=wall_area_3, roof_area=roof_area_3, building_volume=building_volume_3, filename_TRY=TRY_filename, u_type=u_type, building_state=building_state, u_values=u_values)

    # self.yearly_heating_demand
    # self.yearly_warm_water_demand
    # self.yearly_heat_demand
    # self.warm_water_share

    print("\nBuilding 1: Address: Dresdner Str. 30")
    building1.calc_heat_demand()
    building1.calc_yearly_heat_demand()

    print(f"Building 1: Yearly Heat Demand: {building1.yearly_heat_demand:.2f} kWh")
    print(f"Building 1: Yearly Warm Water Demand: {building1.yearly_warm_water_demand:.2f} kWh")
    print(f"Building 1: Yearly Heating Demand: {building1.yearly_heating_demand:.2f} kWh")
    print(f"Building 1: Warm Water Share: {building1.warm_water_share:.2f} %")

    print("\nBuilding 2: Address: Dresdner Str. 26")
    building2.calc_heat_demand()
    building2.calc_yearly_heat_demand()

    print(f"Building 2: Yearly Heat Demand: {building2.yearly_heat_demand:.2f} kWh")
    print(f"Building 2: Yearly Warm Water Demand: {building2.yearly_warm_water_demand:.2f} kWh")
    print(f"Building 2: Yearly Heating Demand: {building2.yearly_heating_demand:.2f} kWh")
    print(f"Building 2: Warm Water Share: {building2.warm_water_share:.2f} %")

    print("\nBuilding 3: Address: Dresdner Str. 28")
    building3.calc_heat_demand()
    building3.calc_yearly_heat_demand()

    print(f"Building 3: Yearly Heat Demand: {building3.yearly_heat_demand:.2f} kWh")
    print(f"Building 3: Yearly Warm Water Demand: {building3.yearly_warm_water_demand:.2f} kWh")
    print(f"Building 3: Yearly Heating Demand: {building3.yearly_heating_demand:.2f} kWh")
    print(f"Building 3: Warm Water Share: {building3.warm_water_share:.2f} %")

def test_lod2_adress_filter():
    filter_file_path = 'examples\\data\\data_ETRS89.csv'
    lod_geojson_path = 'examples\\data\\LOD2\\LOD2_data.geojson'
    output_geojson_path = 'examples\\data\\LOD2\\adress_filtered_lod2.geojson'

    filter_LOD2_with_coordinates(lod_geojson_path, filter_file_path, output_geojson_path)

    print("\nLOD2-Daten erfolgreich mit Adressen gefiltert.")

def test_lod2_polygon_filter():
    lod_geojson_path = 'examples\\data\\LOD2\\LOD2_data.geojson'
    polygon_geojson_path = 'examples\\data\\LOD2\\filter_polygon.geojson'
    output_geojson_path = 'examples\\data\\LOD2\\polygon_filtered_lod2.geojson'

    spatial_filter_with_polygon(lod_geojson_path, polygon_geojson_path, output_geojson_path)

    print("\nLOD2-Daten erfolgreich mit Polygon gefiltert.")

# improvements in LOD2 data processing needed for this test, currently not working
def test_lod2_building_caclulation():
    lod_geojson_path = 'examples\\data\\LOD2\\LOD2_data.geojson'
    polygon_shapefile_path = 'examples\data\\lod2\\filter_polygon.geojson'
    output_geojson_path = 'examples\\data\\LOD2\\polygon_filtered_lod2.geojson'
    output_csv_path = 'examples\\data\\LOD2\\LOD2_building_data.csv'

    calculate_heat_demand_for_lod2_area(lod_geojson_path, polygon_shapefile_path, output_geojson_path, output_csv_path)

    print("\nBerechnung der Wärmebedarfe der Gebäude auf Basis der LOD2-Daten erfolgreich")

if __name__ == '__main__':
    test_building_calculation()
    test_lod2_adress_filter()
    test_lod2_polygon_filter()
    #test_lod2_building_caclulation()
