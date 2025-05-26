"""
Filename: import_and_create_layers.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-26
Description: Imports the spatial data and processes them into layers.
"""

import traceback
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from districtheatingsim.net_generation.simple_MST import generate_network, generate_connection_lines

def import_osm_street_layer(osm_street_layer_geojson_file):
    """
    Imports the OSM street layer from a GeoJSON file.

    Args:
        osm_street_layer_geojson_file (str): Path to the GeoJSON file containing the OSM street layer.

    Returns:
        geopandas.GeoDataFrame: The imported street layer as a GeoDataFrame.
    """
    try:
        layer = gpd.read_file(osm_street_layer_geojson_file)
        print("Layer successfully loaded.")
        return layer
    except Exception as e:
        print(f"Error loading the layer: {e}")
        return None

def load_layers(osm_street_layer_geojson_file, data_csv_file_name, coordinates):
    """
    Loads the street layer, data layer, and producer location from files.

    Args:
        osm_street_layer_geojson_file (str): Path to the GeoJSON file containing the OSM street layer.
        data_csv_file_name (str): Path to the CSV file containing data.
        coordinates (list of tuples): List of tuples containing the coordinates of the producer locations.

    Returns:
        tuple: Tuple containing the street layer, data layer, producer location, and data DataFrame.
    """
    try:
        # Load the street layer as a GeoDataFrame
        osm_street_layer = gpd.read_file(osm_street_layer_geojson_file)
        #print(f"Street layer successfully loaded. Layer: {osm_street_layer}")
        # Load the data as a DataFrame
        heat_consumer_df = pd.read_csv(data_csv_file_name, sep=';')
        #print(f"Data successfully loaded. Data: {heat_consumer_df}")
        # Convert the DataFrame into a GeoDataFrame
        heat_consumer_layer = gpd.GeoDataFrame(heat_consumer_df, geometry=gpd.points_from_xy(heat_consumer_df.UTM_X, heat_consumer_df.UTM_Y))
        #print(f"Data layer successfully created. Data layer: {heat_consumer_layer}")
        # Create the producer location as a GeoDataFrame
        heat_generator_locations = [Point(x, y) for x, y in coordinates]
        #print(f"Points: {heat_generator_locations}")
        # Create a GeoDataFrame for the producer location
        heat_generator_layer = gpd.GeoDataFrame(geometry=heat_generator_locations, crs="EPSG:4326")
        #print(f"Producer location successfully created. Producer location: {heat_generator_layer}")

        return osm_street_layer, heat_consumer_layer, heat_generator_layer, heat_consumer_df

    except Exception as e:
        print(f"Error loading the layers: {e}")
        traceback.print_exc()
        return None, None, None, None

def generate_and_export_layers(osm_street_layer_geojson_file_name, data_csv_file_name, coordinates, base_path, algorithm="MST", offset_angle=0, offset_distance=0.5):
    """
    Generates the layers for the network and exports them as GeoJSON files.

    Args:
        osm_street_layer_geojson_file_name (str): Path to the GeoJSON file containing the OSM street layer.
        data_csv_file_name (str): Path to the CSV file containing data.
        coordinates (list of tuples): List of tuples containing the coordinates of the producer locations.
        base_path (str): Base path for exporting the generated layers.
        algorithm (str, optional): Algorithm to use for generating the network. Defaults to "MST".
        offset_angle (int, optional): Angle in degrees to offset the points. Defaults to 0.
        offset_distance (int, optional): Distance to offset the points. Defaults to 0.5.
    Returns:
        None: The function exports the generated layers as GeoJSON files.

    """
    osm_street_layer, heat_consumer_layer, heat_generator_layer, heat_consumer_df = load_layers(osm_street_layer_geojson_file_name, data_csv_file_name, coordinates)
    
    # Generate flow and return lines using the specified algorithm
    flow_lines_gdf, return_lines_gdf = generate_network(heat_consumer_layer, heat_generator_layer, osm_street_layer, algorithm=algorithm, offset_distance=offset_distance, offset_angle=offset_angle)

    # Generate heat consumer and producer lines
    heat_consumer_gdf = generate_connection_lines(heat_consumer_layer, offset_distance, offset_angle, heat_consumer_df)
    heat_producer_gdf = generate_connection_lines(heat_generator_layer, offset_distance, offset_angle)

    # Setting the CRS to EPSG:25833
    heat_consumer_gdf = heat_consumer_gdf.set_crs("EPSG:25833")
    return_lines_gdf = return_lines_gdf.set_crs("EPSG:25833")
    flow_lines_gdf = flow_lines_gdf.set_crs("EPSG:25833")
    heat_producer_gdf = heat_producer_gdf.set_crs("EPSG:25833")
    
    # Export the GeoDataFrames as GeoJSON
    heat_consumer_gdf.to_file(f"{base_path}\\Wärmenetz\\HAST.geojson", driver="GeoJSON")
    return_lines_gdf.to_file(f"{base_path}\\Wärmenetz\\Rücklauf.geojson", driver="GeoJSON")
    flow_lines_gdf.to_file(f"{base_path}\\Wärmenetz\\Vorlauf.geojson", driver="GeoJSON")
    heat_producer_gdf.to_file(f"{base_path}\\Wärmenetz\\Erzeugeranlagen.geojson", driver="GeoJSON")