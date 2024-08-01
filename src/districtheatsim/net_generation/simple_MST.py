"""
Filename: simple_MST.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: Contains the functions to process the spatial data to generate the MST.
"""

import pandas as pd
import geopandas as gpd
import math
import networkx as nx
from shapely.geometry import LineString, Point

from net_generation.A_Star_algorithm_net_generation import *
from net_generation.MST_processing import *

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
        set: A set of end points from the created perpendicular lines.
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
    """
    Generates return lines by creating offset points and finding their nearest lines.

    Args:
        layer (geopandas.GeoDataFrame): The layer of points to process.
        distance (float): The distance to offset the points.
        angle_degrees (float): The angle in degrees to offset the points.
        street_layer (geopandas.GeoDataFrame): The layer of street lines to find the nearest lines from.

    Returns:
        set: A set of end points from the created perpendicular lines.
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
    """
    Generates the flow line network using specified algorithms.

    Args:
        layer_points_fl (geopandas.GeoDataFrame): The layer of flow line points.
        layer_wea (geopandas.GeoDataFrame): The layer of additional points (e.g., heat exchangers).
        street_layer (geopandas.GeoDataFrame): The layer of street lines.
        algorithm (str, optional): The algorithm to use for network generation. Defaults to "MST".

    Returns:
        geopandas.GeoDataFrame: The generated network as a GeoDataFrame.
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
        # Creating the MST network from the endpoints
        all_points = add_intermediate_points(all_end_points_gdf, street_layer)
        mst_gdf = generate_mst(all_points)
        final_gdf = gpd.GeoDataFrame(pd.concat([mst_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))

    if algorithm == "Advanced MST":
        # Creating the MST network from the endpoints
        mst_gdf = generate_mst(all_end_points_gdf)
        adjusted_mst = adjust_segments_to_roads(mst_gdf, street_layer, all_end_points_gdf)
        final_gdf = gpd.GeoDataFrame(pd.concat([adjusted_mst, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))

    if algorithm == "A*-Star":
        road_graph = create_road_graph(street_layer)  # Created once and reused
        a_star_gdf = generate_a_star_network(road_graph, all_end_points_gdf)
        final_gdf = gpd.GeoDataFrame(pd.concat([a_star_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))
        final_gdf = simplify_network(final_gdf)

    return final_gdf

def generate_network_rl(layer_points_rl, layer_wea, fixed_distance_rl, fixed_angle_rl, street_layer, algorithm="MST"):
    """
    Generates the return line network using specified algorithms.

    Args:
        layer_points_rl (geopandas.GeoDataFrame): The layer of return line points.
        layer_wea (geopandas.GeoDataFrame): The layer of additional points (e.g., heat exchangers).
        fixed_distance_rl (float): The fixed distance for creating offset points.
        fixed_angle_rl (float): The fixed angle in degrees for creating offset points.
        street_layer (geopandas.GeoDataFrame): The layer of street lines.
        algorithm (str, optional): The algorithm to use for network generation. Defaults to "MST".

    Returns:
        geopandas.GeoDataFrame: The generated network as a GeoDataFrame.
    """
    perpendicular_lines = []
    offset_points_rl = []  # Stores the generated offset points for layer_points_rl
    offset_points_wea = []  # Stores the generated offset points for layer_wea

    # Creating the offset points and vertical lines for the return lines from layer_points_rl
    points_end_points = generate_return_lines(layer_points_rl, fixed_distance_rl, fixed_angle_rl, street_layer)
    for point in layer_points_rl.geometry:
        offset_point = create_offset_points(point, fixed_distance_rl, fixed_angle_rl)
        offset_points_rl.append(offset_point)  # Store the offset point
        nearest_line = find_nearest_line(offset_point, street_layer)
        if nearest_line is not None:
            perpendicular_line = create_perpendicular_line(offset_point, nearest_line)
            perpendicular_lines.append(perpendicular_line)

    # Creating the offset points and vertical lines for the return lines from layer_wea
    wea_end_points = generate_return_lines(layer_wea, fixed_distance_rl, fixed_angle_rl, street_layer)
    for point in layer_wea.geometry:
        offset_point = create_offset_points(point, fixed_distance_rl, fixed_angle_rl)
        offset_points_wea.append(offset_point)  # Store the offset point
        nearest_line = find_nearest_line(offset_point, street_layer)
        if nearest_line is not None:
            perpendicular_line = create_perpendicular_line(offset_point, nearest_line)
            perpendicular_lines.append(perpendicular_line)

    # Combining the endpoints and converting them into a GeoDataFrame
    all_end_points = points_end_points.union(wea_end_points)
    all_end_points_gdf = gpd.GeoDataFrame(geometry=list(all_end_points))

    if algorithm == "MST":
        # Creating the MST network from the endpoints
        mst_gdf = generate_mst(all_end_points_gdf)
        final_gdf = gpd.GeoDataFrame(pd.concat([mst_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))
    if algorithm == "pre_MST":
        # Creating the MST network from the endpoints
        all_points = add_intermediate_points(all_end_points_gdf, street_layer)
        mst_gdf = generate_mst(all_points)
        final_gdf = gpd.GeoDataFrame(pd.concat([mst_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))
    if algorithm == "Advanced MST":
        # Creating the MST network from the endpoints
        mst_gdf = generate_mst(all_end_points_gdf)
        adjusted_mst = adjust_segments_to_roads(mst_gdf, street_layer, all_end_points_gdf)
        final_gdf = gpd.GeoDataFrame(pd.concat([adjusted_mst, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))
    elif algorithm == "A*-Star":
        road_graph = create_road_graph(street_layer)
        a_star_gdf = generate_a_star_network(road_graph, all_end_points_gdf)
        final_gdf = gpd.GeoDataFrame(pd.concat([a_star_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))
        final_gdf = simplify_network(final_gdf)
    return final_gdf

def generate_mst(points):
    """
    Generates a Minimal Spanning Tree (MST) from a set of points.

    Args:
        points (geopandas.GeoDataFrame): The set of points to generate the MST from.

    Returns:
        geopandas.GeoDataFrame: The generated MST as a GeoDataFrame.
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