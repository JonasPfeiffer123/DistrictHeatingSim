"""
Filename: MST_processing.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: Contains the functions needed to post-process the MST-results
"""

import geopandas as gpd
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points
import pandas as pd
import networkx as nx
from collections import defaultdict
import numpy as np
import os

def add_intermediate_points(points_gdf, street_layer, max_distance=200, point_interval=10):
    """
    Adds intermediate points between the given points and the nearest street lines.

    Args:
        points_gdf (geopandas.GeoDataFrame): GeoDataFrame containing the points.
        street_layer (geopandas.GeoDataFrame): GeoDataFrame containing the street lines.
        max_distance (int, optional): Maximum distance to consider for adding intermediate points. Defaults to 200.
        point_interval (int, optional): Interval distance between intermediate points. Defaults to 10.

    Returns:
        geopandas.GeoDataFrame: Updated GeoDataFrame with added intermediate points.
    """
    new_points = []
    for point in points_gdf.geometry:
        # Ensure the point is a valid geometry
        if point.is_empty:
            continue
        # Find the nearest street
        distances = street_layer.distance(point)
        nearest_street_index = distances.idxmin()
        nearest_street = street_layer.iloc[nearest_street_index].geometry

        # Ensure the nearest street is a valid geometry
        if nearest_street.is_empty:
            continue

        # Compute the nearest point on the street
        nearest_point_on_street = nearest_points(point, nearest_street)[1]

        print(nearest_point_on_street)

        # Add intermediate points if the point is within the specified distance
        if point.distance(nearest_point_on_street) <= max_distance:
            line = LineString([point, nearest_point_on_street])
            num_points = int(line.length / point_interval)
            for i in range(1, num_points):
                intermediate_point = line.interpolate(point_interval * i)
                print(intermediate_point)
                new_points.append(intermediate_point)
    
    # Create a GeoDataFrame with all new points
    new_points_gdf = gpd.GeoDataFrame(geometry=new_points)
    return pd.concat([points_gdf, new_points_gdf], ignore_index=True)

def adjust_segments_to_roads(mst_gdf, street_layer, all_end_points_gdf, threshold=5, output_dir="iterations"):
    """
    Adjusts the MST segments to follow the street lines more closely.

    Args:
        mst_gdf (geopandas.GeoDataFrame): GeoDataFrame containing the MST segments.
        street_layer (geopandas.GeoDataFrame): GeoDataFrame containing the street lines.
        all_end_points_gdf (geopandas.GeoDataFrame): GeoDataFrame containing all end points.
        threshold (int, optional): Distance threshold for adjustment. Defaults to 5.
        output_dir (str, optional): Directory to save iteration outputs. Defaults to "iterations".

    Returns:
        geopandas.GeoDataFrame: Updated GeoDataFrame with adjusted segments.
    """
    iteration = 0
    changes_made = True

    # Create the output directory if it does not exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    while changes_made:
        print(f"Iteration {iteration}")

        adjusted_lines = []
        changes_made = False

        for line in mst_gdf.geometry:
            if not line.is_valid:
                print(f"Invalid line geometry: {line}")
                continue

            midpoint = line.interpolate(0.5, normalized=True)
            nearest_line = street_layer.distance(midpoint).idxmin()
            nearest_street = street_layer.iloc[nearest_line].geometry
            point_on_street = nearest_points(midpoint, nearest_street)[1]

            distance_to_street = midpoint.distance(point_on_street)
            print(f"Distance to nearest street: {distance_to_street}")

            if distance_to_street > threshold:
                if point_on_street.equals(Point(line.coords[0])) or point_on_street.equals(Point(line.coords[1])):
                    print(f"Skipping adjustment due to identical points: {point_on_street}")
                    adjusted_lines.append(line)
                    continue
                
                new_line1 = LineString([line.coords[0], point_on_street.coords[0]])
                new_line2 = LineString([point_on_street.coords[0], line.coords[1]])
                
                if new_line1.is_valid and not new_line1.is_empty:
                    adjusted_lines.append(new_line1)
                else:
                    print(f"Invalid new_line1: {new_line1}")
                
                if new_line2.is_valid and not new_line2.is_empty:
                    adjusted_lines.append(new_line2)
                else:
                    print(f"Invalid new_line2: {new_line2}")
                
                changes_made = True
                print("Adjusting line segment")
            else:
                adjusted_lines.append(line)

        if not changes_made:
            print("No changes made, breaking out of the loop.")
            break

        mst_gdf = gpd.GeoDataFrame(geometry=adjusted_lines)
    
        iteration += 1
        if iteration > 1000:
            print("Reached iteration limit, breaking out of the loop.")
            break

    mst_gdf = simplify_network(mst_gdf)
    mst_gdf = extract_unique_points_and_create_mst(mst_gdf, all_end_points_gdf)

    return mst_gdf

def simplify_network(gdf, threshold=10):
    """
    Simplifies the network by merging nearby points and adjusting line segments accordingly.

    Args:
        gdf (geopandas.GeoDataFrame): GeoDataFrame containing the network segments.
        threshold (int, optional): Distance threshold for merging points. Defaults to 10.

    Returns:
        geopandas.GeoDataFrame: Updated GeoDataFrame with simplified network.
    """
    points = defaultdict(list)  # Dictionary to store points and their associated line indices
    simplified_lines = []

    # Extracting the endpoints of all lines and indexing them
    for idx, line in enumerate(gdf.geometry):
        start, end = line.boundary.geoms
        points[start].append(idx)
        points[end].append(idx)

    # Finding nearby points and merging them
    merged_points = {}
    for point in points:
        if point in merged_points:
            continue
        nearby_points = [p for p in points if p.distance(point) < threshold and p not in merged_points]
        if not nearby_points:
            merged_points[point] = point
        else:
            # Compute the centroid of the nearby points
            all_points = np.array([[p.x, p.y] for p in nearby_points])
            centroid = Point(np.mean(all_points, axis=0))
            for p in nearby_points:
                merged_points[p] = centroid

    # Creating new lines with adjusted endpoints
    for line in gdf.geometry:
        start, end = line.boundary.geoms
        new_start = merged_points.get(start, start)
        new_end = merged_points.get(end, end)
        simplified_lines.append(LineString([new_start, new_end]))

    return gpd.GeoDataFrame(geometry=simplified_lines)

def extract_unique_points_and_create_mst(gdf, all_end_points_gdf):
    """
    Extracts unique points from the network segments and creates a new MST.

    Args:
        gdf (geopandas.GeoDataFrame): GeoDataFrame containing the network segments.
        all_end_points_gdf (geopandas.GeoDataFrame): GeoDataFrame containing all end points.

    Returns:
        geopandas.GeoDataFrame: Updated GeoDataFrame with the new MST.
    """
    # Extract unique points from the line geometries
    all_points = []
    for line in gdf.geometry:
        if isinstance(line, LineString):
            all_points.extend(line.coords)
    
    # Add the points from all_end_points_gdf
    for point in all_end_points_gdf.geometry:
        if isinstance(point, Point):
            all_points.append((point.x, point.y))

    # Remove duplicate points
    unique_points = set(all_points)  # Removes duplicates
    unique_points = [Point(pt) for pt in unique_points]  # Convert back to Point objects
    
    # Create a GeoDataFrame from the unique points
    points_gdf = gpd.GeoDataFrame(geometry=unique_points)
    
    mst_gdf = generate_mst(points_gdf)
    
    return mst_gdf

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