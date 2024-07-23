"""
Filename: simple_MST.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
Description: Contains the functions to process the spatial data to generate the MST.

"""

import pandas as pd
import geopandas as gpd
import math
import networkx as nx
from shapely.geometry import LineString, Point

from net_generation.A_Star_algorithm_net_generation import *
from net_generation.MST_processing import *

# help function
def create_offset_points(point, distance, angle_degrees):
    """_summary_

    Args:
        point (_type_): _description_
        distance (_type_): _description_
        angle_degrees (_type_): _description_

    Returns:
        _type_: _description_
    """
    angle_radians = math.radians(angle_degrees)
    dx = distance * math.cos(angle_radians)
    dy = distance * math.sin(angle_radians)
    return Point(point.x + dx, point.y + dy)

def find_nearest_line(point, line_layer):
    """_summary_

    Args:
        point (_type_): _description_
        line_layer (_type_): _description_

    Returns:
        _type_: _description_
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
    """_summary_

    Args:
        point (_type_): _description_
        line (_type_): _description_

    Returns:
        _type_: _description_
    """
    nearest_point_on_line = line.interpolate(line.project(point))
    return LineString([point, nearest_point_on_line])

def process_layer_points(layer, layer_lines):
    """_summary_

    Args:
        layer (_type_): _description_
        layer_lines (_type_): _description_

    Returns:
        _type_: _description_
    """
    street_end_points = set()
    for point in layer.geometry:
        nearest_line = find_nearest_line(point, layer_lines)
        if nearest_line is not None:
            perpendicular_line = create_perpendicular_line(point, nearest_line)
            end_point = perpendicular_line.coords[1]  # End point of the vertical line
            street_end_points.add(Point(end_point))
    return street_end_points

def generate_return_lines(layer, distance, angle_degrees, street_layer):
    """_summary_

    Args:
        layer (_type_): _description_
        distance (_type_): _description_
        angle_degrees (_type_): _description_
        street_layer (_type_): _description_

    Returns:
        _type_: _description_
    """
    street_end_points = set()
    for point in layer.geometry:
        offset_point = create_offset_points(point, distance, angle_degrees)
        nearest_line = find_nearest_line(offset_point, street_layer)
        if nearest_line is not None:
            street_end_point = create_perpendicular_line(offset_point, nearest_line).coords[1]
            street_end_points.add(Point(street_end_point))
    return street_end_points

def generate_network_fl(layer_points_fl, layer_wea, street_layer, algorithm="MST"):
    """_summary_

    Args:
        layer_points_fl (_type_): _description_
        layer_wea (_type_): _description_
        street_layer (_type_): _description_
        algorithm (str, optional): _description_. Defaults to "MST".

    Returns:
        _type_: _description_
    """
    perpendicular_lines = []
    
    # Creating the offset points and vertical lines for the flow lines from layer_points_fl
    points_end_points = process_layer_points(layer_points_fl, street_layer)
    for point in layer_points_fl.geometry:
        nearest_line = find_nearest_line(point, street_layer)
        if nearest_line is not None:
            perpendicular_line = create_perpendicular_line(point, nearest_line)
            perpendicular_lines.append(perpendicular_line)

    # Creating the offset points and vertical lines for the flow lines from layer_wea
    wea_end_points = process_layer_points(layer_wea, street_layer)
    for point in layer_wea.geometry:
        nearest_line = find_nearest_line(point, street_layer)
        if nearest_line is not None:
            perpendicular_line = create_perpendicular_line(point, nearest_line)
            perpendicular_lines.append(perpendicular_line)

    # Combining the endpoints and converting them into a GeoDataFrame
    all_end_points = points_end_points.union(wea_end_points)
    all_end_points_gdf = gpd.GeoDataFrame(geometry=list(all_end_points))

    if algorithm == "MST":
        # Creating the MST network from the endpoints
        mst_gdf = generate_mst(all_end_points_gdf)
        # Adding the vertical lines to the MST GeoDataFrame
        final_gdf = gpd.GeoDataFrame(pd.concat([mst_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))

    if algorithm == "pre_MST":
        # Erstelle das MST-Netzwerk aus den Endpunkten
        all_points = add_intermediate_points(all_end_points_gdf, street_layer)
        mst_gdf = generate_mst(all_points)
        final_gdf = gpd.GeoDataFrame(pd.concat([mst_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))

    if algorithm == "Advanced MST":
        # Erstelle das MST-Netzwerk aus den Endpunkten
        mst_gdf = generate_mst(all_end_points_gdf)
        adjusted_mst = adjust_segments_to_roads(mst_gdf, street_layer, all_end_points_gdf)
        final_gdf = gpd.GeoDataFrame(pd.concat([adjusted_mst, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))

    if algorithm == "A*-Star":
        road_graph = create_road_graph(street_layer)  # Wird einmal erstellt und kann wiederverwendet werden
        a_star_gdf = generate_a_star_network(road_graph, all_end_points_gdf)
        final_gdf = gpd.GeoDataFrame(pd.concat([a_star_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))
        final_gdf = simplify_network(final_gdf)

    return final_gdf

def generate_network_rl(layer_points_rl, layer_wea, fixed_distance_rl, fixed_angle_rl, street_layer, algorithm="MST"):
    """_summary_

    Args:
        layer_points_rl (_type_): _description_
        layer_wea (_type_): _description_
        fixed_distance_rl (_type_): _description_
        fixed_angle_rl (_type_): _description_
        street_layer (_type_): _description_
        algorithm (str, optional): _description_. Defaults to "MST".

    Returns:
        _type_: _description_
    """
    perpendicular_lines = []
    offset_points_rl = []  # Speichert die generierten Offset-Punkte für layer_points_rl
    offset_points_wea = []  # Speichert die generierten Offset-Punkte für layer_wea

    # Erstelle die Offset-Punkte und senkrechten Linien für die Rücklaufleitungen von layer_points_rl
    points_end_points = generate_return_lines(layer_points_rl, fixed_distance_rl, fixed_angle_rl, street_layer)
    for point in layer_points_rl.geometry:
        offset_point = create_offset_points(point, fixed_distance_rl, fixed_angle_rl)
        offset_points_rl.append(offset_point)  # Speichere den Offset-Punkt
        nearest_line = find_nearest_line(offset_point, street_layer)
        if nearest_line is not None:
            perpendicular_line = create_perpendicular_line(offset_point, nearest_line)
            perpendicular_lines.append(perpendicular_line)

    # Erstelle die Offset-Punkte und senkrechten Linien für die Rücklaufleitungen von layer_wea
    wea_end_points = generate_return_lines(layer_wea, fixed_distance_rl, fixed_angle_rl, street_layer)
    for point in layer_wea.geometry:
        offset_point = create_offset_points(point, fixed_distance_rl, fixed_angle_rl)
        offset_points_wea.append(offset_point)  # Speichere den Offset-Punkt
        nearest_line = find_nearest_line(offset_point, street_layer)
        if nearest_line is not None:
            perpendicular_line = create_perpendicular_line(offset_point, nearest_line)
            perpendicular_lines.append(perpendicular_line)

    # Kombiniere die Endpunkte und konvertiere sie in ein GeoDataFrame
    all_end_points = points_end_points.union(wea_end_points)
    all_end_points_gdf = gpd.GeoDataFrame(geometry=list(all_end_points))

    if algorithm == "MST":
        # Erstelle das MST-Netzwerk aus den Endpunkten
        mst_gdf = generate_mst(all_end_points_gdf)
        final_gdf = gpd.GeoDataFrame(pd.concat([mst_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))
    if algorithm == "pre_MST":
        # Erstelle das MST-Netzwerk aus den Endpunkten
        all_points = add_intermediate_points(all_end_points_gdf, street_layer)
        mst_gdf = generate_mst(all_points)
        final_gdf = gpd.GeoDataFrame(pd.concat([mst_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))
    if algorithm == "Advanced MST":
        # Erstelle das MST-Netzwerk aus den Endpunkten
        mst_gdf = generate_mst(all_end_points_gdf)
        adjusted_mst = adjust_segments_to_roads(mst_gdf, street_layer, all_end_points_gdf)
        final_gdf = gpd.GeoDataFrame(pd.concat([adjusted_mst, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))
    elif algorithm == "A*-Star":
        road_graph = create_road_graph(street_layer)
        a_star_gdf = generate_a_star_network(road_graph, all_end_points_gdf)
        final_gdf = gpd.GeoDataFrame(pd.concat([a_star_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))
        final_gdf = simplify_network(final_gdf)
    return final_gdf

# MST network generation
def generate_mst(points):
    """Generates a Minimal Spanning Tree from a Set of Points

    Args:
        points (_type_): _description_

    Returns:
        _type_: _description_
    """
    g = nx.Graph()
    for i, point1 in points.iterrows():
        for j, point2 in points.iterrows():
            if i != j:
                distance = point1.geometry.distance(point2.geometry)
                g.add_edge(i, j, weight=distance)
    mst = nx.minimum_spanning_tree(g)
    lines = [LineString([points.geometry[edge[0]], points.geometry[edge[1]]]) for edge in mst.edges()]
    mst_gdf = gpd.GeoDataFrame(geometry=lines)
    return mst_gdf