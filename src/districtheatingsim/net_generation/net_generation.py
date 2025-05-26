"""
Filename: net_generation.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-26
Description: Contains the functions to generate the heat network based on the given layers.
"""

import pandas as pd
import geopandas as gpd
import math
from shapely.geometry import LineString, Point

from districtheatingsim.net_generation.minimal_spanning_tree import generate_mst, adjust_segments_to_roads
from districtheatingsim.net_generation.steiner_tree import generate_steiner_tree_network

import matplotlib.pyplot as plt

def create_offset_points(point, distance, angle_degrees):
    """
    Creates a point offset from the given point by a specified distance and angle.

    Args:
        point (shapely.geometry.Point): The original point.
        distance (float): The distance to offset the point.
        angle_degrees (float): The angle in degrees to offset the point.

    Returns:
        shapely.geometry.Point: The offset point.
    """
    angle_radians = math.radians(angle_degrees)
    dx = distance * math.cos(angle_radians)
    dy = distance * math.sin(angle_radians)
    return Point(point.x + dx, point.y + dy)

def offset_lines_by_angle(lines_gdf, distance, angle_degrees):
    """
    Verschiebt alle Punkte jeder LineString-Geometrie im GeoDataFrame um einen festen Abstand und Winkel.
    Args:
        lines_gdf (gpd.GeoDataFrame): GeoDataFrame mit LineStrings.
        distance (float): Abstand in Metern.
        angle_degrees (float): Winkel in Grad (0 = x-Achse, 90 = y-Achse).
    Returns:
        gpd.GeoDataFrame: Neues GeoDataFrame mit verschobenen Linien.
    """
    def offset_line(line):
        return LineString([
            create_offset_points(Point(x, y), distance, angle_degrees)
            for x, y in line.coords
        ])
    offset_lines = [offset_line(line) for line in lines_gdf.geometry]
    return gpd.GeoDataFrame(geometry=offset_lines, crs=lines_gdf.crs)

def find_nearest_line(point, line_layer):
    """
    Finds the nearest line to a given point from a layer of lines.

    Args:
        point (shapely.geometry.Point): The point to find the nearest line to.
        line_layer (geopandas.GeoDataFrame): The layer of lines to search.

    Returns:
        shapely.geometry.LineString: The nearest line to the point.
    """
    min_distance = float('inf')
    nearest_line = None
    for line in line_layer.geometry:
        distance = point.distance(line)
        if distance < min_distance:
            min_distance = distance
            nearest_line = line
    return nearest_line

def create_perpendicular_line(point, line):
    """
    Creates a perpendicular line from a given point to the nearest point on the given line.

    Args:
        point (shapely.geometry.Point): The point to start the perpendicular line from.
        line (shapely.geometry.LineString): The line to create the perpendicular line to.

    Returns:
        shapely.geometry.LineString: The perpendicular line.
    """
    nearest_point_on_line = line.interpolate(line.project(point))
    return LineString([point, nearest_point_on_line])

def process_layer_points(layer, layer_lines):
    """
    Processes a layer of points to find their nearest lines and create perpendicular lines.

    Args:
        layer (geopandas.GeoDataFrame): The layer of points to process.
        layer_lines (geopandas.GeoDataFrame): The layer of lines to find the nearest lines from.

    Returns:
        list: A list of perpendicular lines created from the points.
        set: A set of end points from the created perpendicular lines.
    """
    # Initialize a list to store the perpendicular lines
    perpendicular_lines = []
    # Create a set to store unique end points
    street_end_points = set()
    for point in layer.geometry:
        nearest_line = find_nearest_line(point, layer_lines)
        if nearest_line is not None:
            perpendicular_line = create_perpendicular_line(point, nearest_line)
            perpendicular_lines.append(perpendicular_line)
            end_point = perpendicular_line.coords[1]  # End point of the vertical line
            street_end_points.add(Point(end_point))

    return perpendicular_lines, street_end_points

def generate_network(heat_consumer_layer, heat_generator_layer, osm_street_layer, algorithm="MST", offset_distance=0.5, offset_angle=0):
    """
    Generates the heat network using specified algorithms.

    Args:
        heat_consumer_layer (geopandas.GeoDataFrame): The layer of heat consumers.
        heat_generator_layer (geopandas.GeoDataFrame): The layer of heat generators.
        osm_street_layer (geopandas.GeoDataFrame): The layer of street lines.
        algorithm (str, optional): The algorithm to use for network generation. Defaults to "MST".

    """

    # 2. Get the perpendicular lines and endpoints for heat consumers and generators
    perpendicular_lines_heat_consumer, heat_consumer_endpoints = process_layer_points(heat_consumer_layer, osm_street_layer)
    perpendicular_lines_heat_generator, heat_generator_endpoints = process_layer_points(heat_generator_layer, osm_street_layer)
    all_perpendicular_lines = perpendicular_lines_heat_consumer + perpendicular_lines_heat_generator
    all_endpoints = heat_consumer_endpoints.union(heat_generator_endpoints)
    all_endpoints_gdf = gpd.GeoDataFrame(geometry=list(all_endpoints))

    # 3. Create the final GeoDataFrame for the flow lines
    if algorithm == "MST":
        # Creating the MST network from the endpoints
        flow_line_mst_gdf = generate_mst(all_endpoints_gdf)
        # Adding the vertical lines to the MST GeoDataFrame
        final_flow_line_gdf = gpd.GeoDataFrame(pd.concat([flow_line_mst_gdf, gpd.GeoDataFrame(geometry=all_perpendicular_lines)], ignore_index=True))

    elif algorithm == "Advanced MST":
        # Creating the MST network from the endpoints
        flow_line_mst_gdf = generate_mst(all_endpoints_gdf)
        adjusted_mst = adjust_segments_to_roads(flow_line_mst_gdf, osm_street_layer, all_endpoints_gdf)
        final_flow_line_gdf = gpd.GeoDataFrame(pd.concat([adjusted_mst, gpd.GeoDataFrame(geometry=all_perpendicular_lines)], ignore_index=True))

    elif algorithm == "Steiner":
        # Creating the Steiner tree network from the endpoints
        flow_line_steiner_gdf = generate_steiner_tree_network(osm_street_layer, all_endpoints_gdf)
        final_flow_line_gdf = gpd.GeoDataFrame(pd.concat([flow_line_steiner_gdf, gpd.GeoDataFrame(geometry=all_perpendicular_lines)], ignore_index=True))

    else:
        raise ValueError("Unknown algorithm: " + str(algorithm))
    
    # 4. Calculate parallel offset lines for the flow lines as return lines
    final_return_line_gdf = offset_lines_by_angle(final_flow_line_gdf, offset_distance, offset_angle)

    # Plotting the flow and return lines using GeoDataFrame's plot method
    #ax = final_flow_line_gdf.plot(color='red', linewidth=1, label='Flow Lines')
    #final_return_line_gdf.plot(ax=ax, color='blue', linewidth=1, label='Return Lines')
    #plt.legend()
    #plt.show()

    return final_flow_line_gdf, final_return_line_gdf

def generate_connection_lines(layer, offset_distance, offset_angle, df=None):
    """
    Generates lines offset from the given points by a specified distance and angle.

    Args:
        layer (geopandas.GeoDataFrame): GeoDataFrame containing the points to offset.
        offset_distance (float): Distance to offset the points.
        offset_angle (float): Angle in degrees to offset the points.
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

        offset_point = create_offset_points(point, offset_distance, offset_angle)
        line = LineString([point, offset_point])
        
        lines.append(line)
        attributes.append(attr)

    # Creation of a GeoDataFrame with the lines and attributes
    lines_gdf = gpd.GeoDataFrame(attributes, geometry=lines)
    return lines_gdf