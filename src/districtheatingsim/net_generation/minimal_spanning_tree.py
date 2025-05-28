"""
Filename: minimal_spanning_tree.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-26
Description: Contains the functions to generate a Minimal Spanning Tree (MST) from a set of points and adjust the segments to follow street lines.
"""

import geopandas as gpd
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points
import networkx as nx
from collections import defaultdict
import numpy as np

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

def adjust_segments_to_roads(mst_gdf, street_layer, all_end_points_gdf, threshold=5, min_improvement=0.5):
    """
    Iteratively adjusts the MST segments so that they follow the street network more closely.
    The goal is to "snap" the MST lines to the nearest street if their midpoint is further than `threshold` away.

    Args:
        mst_gdf (geopandas.GeoDataFrame): GeoDataFrame containing the MST segments (LineStrings).
        street_layer (geopandas.GeoDataFrame): GeoDataFrame containing the street lines.
        all_end_points_gdf (geopandas.GeoDataFrame): GeoDataFrame containing all end points (for later MST rebuild).
        threshold (int, optional): Distance threshold for adjustment. Defaults to 5.

    Returns:
        geopandas.GeoDataFrame: Updated GeoDataFrame with adjusted segments.
    """
    iteration = 0
    changes_made = True

    # Track how often each segment (by its hash) is adjusted
    segment_change_counter = {}
    blacklist = set()  # Segments that should not be changed anymore

    def line_hash(line):
        # Hash based on rounded coordinates for stability
        coords = tuple((round(x, 3), round(y, 3)) for x, y in line.coords)
        return hash(coords)

    # Main loop: repeat until no more changes or iteration limit reached
    while changes_made:
        print(f"\n--- Iteration {iteration} ---")
        adjusted_lines = []
        changes_made = False
        changed_this_iter = set()

        for idx, line in enumerate(mst_gdf.geometry):
            if not line.is_valid:
                print(f"  [!] Invalid line geometry: {line}")
                continue

            seg_id = line_hash(line)
            if seg_id in blacklist:
                adjusted_lines.append(line)
                continue

            midpoint = line.interpolate(0.5, normalized=True)
            nearest_line = street_layer.distance(midpoint).idxmin()
            nearest_street = street_layer.iloc[nearest_line].geometry
            point_on_street = nearest_points(midpoint, nearest_street)[1]
            distance_to_street = midpoint.distance(point_on_street)

            if distance_to_street > threshold:
                if point_on_street.equals(Point(line.coords[0])) or point_on_street.equals(Point(line.coords[1])):
                    print(f"    Skipping adjustment (projected point is endpoint): {point_on_street}")
                    adjusted_lines.append(line)
                    continue

                # Calculate original distance for improvement check
                orig_distance = distance_to_street

                new_line1 = LineString([line.coords[0], point_on_street.coords[0]])
                new_line2 = LineString([point_on_street.coords[0], line.coords[1]])

                for new_line in [new_line1, new_line2]:
                    if new_line.is_valid and not new_line.is_empty:
                        new_midpoint = new_line.interpolate(0.5, normalized=True)
                        nearest_line_new = street_layer.distance(new_midpoint).idxmin()
                        nearest_street_new = street_layer.iloc[nearest_line_new].geometry
                        point_on_street_new = nearest_points(new_midpoint, nearest_street_new)[1]
                        new_distance = new_midpoint.distance(point_on_street_new)
                        improvement = orig_distance - new_distance
                        if improvement < min_improvement:
                            print(f"    Improvement only {improvement:.2f} m (< {min_improvement} m), accepting line as is and blacklisting.")
                            blacklist.add(line_hash(new_line))
                        adjusted_lines.append(new_line)
                    else:
                        print(f"    [!] Invalid new_line: {new_line}")

                changes_made = True
                changed_this_iter.add(seg_id)
                segment_change_counter[seg_id] = segment_change_counter.get(seg_id, 0) + 1
                print(f"    Adjusted line {idx} (ID {seg_id}), total adjustments: {segment_change_counter[seg_id]}")
            else:
                adjusted_lines.append(line)

        print(f"  Adjusted {len(changed_this_iter)} segments this iteration.")
        if changed_this_iter:
            print(f"    Changed segment IDs: {list(changed_this_iter)}")
            most_changed = sorted(segment_change_counter.items(), key=lambda x: -x[1])[:3]
            print(f"    Most changed segments so far: {most_changed}")

        if not changes_made:
            print("No changes made, breaking out of the loop.")
            break

        mst_gdf = gpd.GeoDataFrame(geometry=adjusted_lines)
        iteration += 1
        if iteration > 50:
            print("Reached iteration limit, breaking out of the loop.")
            break

    print("\nAdjustment finished. Now simplifying and rebuilding MST...")
    mst_gdf = simplify_network(mst_gdf)
    mst_gdf = extract_unique_points_and_create_mst(mst_gdf, all_end_points_gdf)

    print("Adjustment and MST rebuild complete.")
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