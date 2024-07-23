"""
Filename: simple_lod2_test.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
Description: Script for processing LOD2 data.

"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lod2.filter_LOD2 import filter_LOD2_with_OSM_and_adress, spatial_filter_with_polygon, process_lod2, filter_LOD2_with_coordinates
from lod2.heat_requirement_DIN_EN_12831 import calculate_heat_demand_for_lod2_area, Building

### aktuell sind die Pfade noch nicht enthalten ###
def test_lod2_adress_filter():
    csv_file_path = 'tests\\data\\data_input.csv'
    osm_geojson_path = 'tests\\data\\osm_buildings_data.geojson'
    lod_shapefile_path = 'tests\\data\\lod2\\lod2_33458_5668_2_sn.geojson'
    output_geojson_path = 'tests\\data\\lod2\\adress_filtered_lod2.geojson'

    filter_LOD2_with_OSM_and_adress(csv_file_path, osm_geojson_path, lod_shapefile_path, output_geojson_path)
    print("LOD2-Daten erfolgreich mit Adressen gefiltert.")

def test_lod2_shape_filter():
    # Pfadangaben
    lod_geojson_path = 'tests\\data\\lod2\\lod2_33458_5668_2_sn.geojson'
    polygon_shapefile_path = 'tests\\data\\lod2\\filter_polygon.geojson'
    output_geojson_path = 'tests\\data\\lod2\\polygon_filtered_lod2.geojson'

    spatial_filter_with_polygon(lod_geojson_path, polygon_shapefile_path, output_geojson_path)
    process_lod2(output_geojson_path)
    print("LOD2-Daten erfolgreich mit Polygon gefiltert.")

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

def test_lod2_building_caclulation():
    lod_geojson_path = 'tests\\data\\lod2\\lod2_33458_5668_2_sn.geojson'
    polygon_shapefile_path = 'tests\data\\lod2\\filter_polygon.geojson'
    output_geojson_path = 'tests\\data\\lod2\\polygon_filtered_lod2.geojson'
    output_csv_path = 'tests\\data\\lod2\\building_data.csv'

    calculate_heat_demand_for_lod2_area(lod_geojson_path, polygon_shapefile_path, output_geojson_path, output_csv_path)
    print("Berechnung der Wärmebedarfe der Gebäude auf Basis der LOD2-Daten erfolgreich")

def test_lod2_coordinate_filter():
    csv_file_path = 'tests\\data\\data_output_ETRS89.csv'
    lod_geojson_path = 'tests\\data\\lod2\\lod2_data.geojson'
    output_geojson_path = 'tests\\data\\lod2\\adress_coordinates_filtered_lod2.geojson'

    filter_LOD2_with_coordinates(lod_geojson_path, csv_file_path, output_geojson_path)
    print("LOD2-Daten erfolgreich mit Koordinaten der Adressen gefiltert.")

#test_lod2_adress_filter()
#test_lod2_shape_filter()
#test_building_calculation()
#test_lod2_building_caclulation()

test_lod2_coordinate_filter()
