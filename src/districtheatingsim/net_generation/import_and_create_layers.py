"""
Filename: import_and_create_layers.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-26
Description: Imports the spatial data and processes them into layers.
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

from districtheatingsim.net_generation.simple_MST import generate_network_fl, generate_network_rl, create_offset_points

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

def generate_lines(layer, distance, angle_degrees, df=None):
    """
    Generates lines offset from the given points by a specified distance and angle.

    Args:
        layer (geopandas.GeoDataFrame): GeoDataFrame containing the points to offset.
        distance (float): Distance to offset the points.
        angle_degrees (float): Angle in degrees to offset the points.
        df (pandas.DataFrame, optional): DataFrame containing additional attributes for the points. Defaults to None.

    Returns:
        geopandas.GeoDataFrame: GeoDataFrame with the generated lines and attributes.
    """
    lines = []
    attributes = []

    for point in layer.geometry:
        # Converting Shapely geometry to coordinates
        original_point = (point.x, point.y)

        # Initialize all attributes with default values or None
        attr = {
            'Land': None,
            'Bundesland': None,
            'Stadt': None,
            'Adresse': None,
            'Wärmebedarf': None,
            'Gebäudetyp': None,
            'Subtyp': None,
            'WW_Anteil': None,
            'Typ_Heizflächen': None,
            'VLT_max': None,
            'Steigung_Heizkurve': None,
            'RLT_max': None,
            'Normaußentemperatur': None
        }

        if df is not None:
            # Determine attributes based on coordinates
            match = df[(df['UTM_X'] == original_point[0]) & (df['UTM_Y'] == original_point[1])]
            if not match.empty:
                attr['Land'] = match['Land'].iloc[0]
                attr['Bundesland'] = match['Bundesland'].iloc[0]
                attr['Stadt'] = match['Stadt'].iloc[0]
                attr['Adresse'] = match['Adresse'].iloc[0]
                attr['Wärmebedarf'] = match['Wärmebedarf'].iloc[0]
                attr['Gebäudetyp'] = match['Gebäudetyp'].iloc[0]
                attr['Subtyp'] = match['Subtyp'].iloc[0]
                attr['WW_Anteil'] = match['WW_Anteil'].iloc[0]
                attr['Typ_Heizflächen'] = match['Typ_Heizflächen'].iloc[0]
                attr['VLT_max'] = match['VLT_max'].iloc[0]
                attr['Steigung_Heizkurve'] = match['Steigung_Heizkurve'].iloc[0]
                attr['RLT_max'] = match['RLT_max'].iloc[0]
                attr['Normaußentemperatur'] = match['Normaußentemperatur'].iloc[0]

        offset_point = create_offset_points(point, distance, angle_degrees)
        line = LineString([point, offset_point])
        
        lines.append(line)
        attributes.append(attr)

    # Creation of a GeoDataFrame with the lines and attributes
    lines_gdf = gpd.GeoDataFrame(attributes, geometry=lines)
    return lines_gdf

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
        street_layer = gpd.read_file(osm_street_layer_geojson_file)
        # Load the data as a DataFrame
        data_df = pd.read_csv(data_csv_file_name, sep=';')
        print(f"Data successfully loaded. Data: {data_df}")
        # Convert the DataFrame into a GeoDataFrame
        data_layer = gpd.GeoDataFrame(data_df, geometry=gpd.points_from_xy(data_df.UTM_X, data_df.UTM_Y))
        print(f"Data layer successfully created. Data layer: {data_layer}")
        # Create the producer location as a GeoDataFrame
        points = [Point(x, y) for x, y in coordinates]
        producer_location = gpd.GeoDataFrame(geometry=points, crs="EPSG:4326")

        return street_layer, data_layer, producer_location, data_df
    
    except Exception as e:
        print(f"Error loading the layers: {e}")
        return None, None, None, None

def generate_and_export_layers(osm_street_layer_geojson_file_name, data_csv_file_name, coordinates, base_path, fixed_angle=0, fixed_distance=1, algorithm="MST"):
    """
    Generates the layers for the network and exports them as GeoJSON files.

    Args:
        osm_street_layer_geojson_file_name (str): Path to the GeoJSON file containing the OSM street layer.
        data_csv_file_name (str): Path to the CSV file containing data.
        coordinates (list of tuples): List of tuples containing the coordinates of the producer locations.
        base_path (str): Base path for exporting the generated layers.
        fixed_angle (int, optional): Angle in degrees to offset the points. Defaults to 0.
        fixed_distance (int, optional): Distance to offset the points. Defaults to 1.
        algorithm (str, optional): Algorithm to use for generating the network. Defaults to "MST".
    """
    street_layer, layer_points, layer_WEA, df = load_layers(osm_street_layer_geojson_file_name, data_csv_file_name, coordinates)
    
    # Use the custom functions to generate the lines
    vl_heat_exchanger = generate_lines(layer_points, fixed_distance, fixed_angle, df)
    vl_return_lines = generate_network_rl(layer_points, layer_WEA, fixed_distance, fixed_angle, street_layer, algorithm=algorithm)
    vl_flow_lines = generate_network_fl(layer_points, layer_WEA, street_layer, algorithm=algorithm)
    vl_heat_producer = generate_lines(layer_WEA, fixed_distance, fixed_angle)

    # Setting the CRS to EPSG:25833
    vl_heat_exchanger = vl_heat_exchanger.set_crs("EPSG:25833")
    vl_return_lines = vl_return_lines.set_crs("EPSG:25833")
    vl_flow_lines = vl_flow_lines.set_crs("EPSG:25833")
    vl_heat_producer = vl_heat_producer.set_crs("EPSG:25833")
    
    # Export the GeoDataFrames as GeoJSON
    vl_heat_exchanger.to_file(f"{base_path}/Wärmenetz/HAST.geojson", driver="GeoJSON")
    vl_return_lines.to_file(f"{base_path}/Wärmenetz/Rücklauf.geojson", driver="GeoJSON")
    vl_flow_lines.to_file(f"{base_path}/Wärmenetz/Vorlauf.geojson", driver="GeoJSON")
    vl_heat_producer.to_file(f"{base_path}/Wärmenetz/Erzeugeranlagen.geojson", driver="GeoJSON")