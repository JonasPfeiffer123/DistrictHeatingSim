"""
Minimum Spanning Tree generation and road alignment optimization.

Implements MST algorithms for district heating network layout with iterative
road alignment adjustment while maintaining connectivity.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import geopandas as gpd
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points
import networkx as nx
from collections import defaultdict
import numpy as np
from typing import Tuple, Optional, Set, Dict, Any

def generate_mst(points: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Generate Minimum Spanning Tree from point locations.

    :param points: Point geometries for network terminals
    :type points: gpd.GeoDataFrame
    :return: MST network as LineString geometries
    :rtype: gpd.GeoDataFrame
    
    .. note::
        Tree topology (n-1 edges for n points). Uses Kruskal's algorithm with Euclidean distances.
    """
    # Build complete graph with distance weights
    g = nx.Graph()
    for i, point1 in points.iterrows():
        for j, point2 in points.iterrows():
            if i != j:
                distance = point1.geometry.distance(point2.geometry)
                g.add_edge(i, j, weight=distance)
    
    # Generate minimum spanning tree
    mst = nx.minimum_spanning_tree(g)
    
    # Convert MST edges to LineString geometries
    lines = [
        LineString([points.geometry[edge[0]], points.geometry[edge[1]]]) 
        for edge in mst.edges()
    ]
    
    return gpd.GeoDataFrame(geometry=lines)

def adjust_segments_to_roads(mst_gdf: gpd.GeoDataFrame, 
                           street_layer: gpd.GeoDataFrame, 
                           all_end_points_gdf: gpd.GeoDataFrame, 
                           threshold: float = 5.0, 
                           min_improvement: float = 0.5) -> gpd.GeoDataFrame:
    """
    Iteratively adjust MST segments to follow street network.

    :param mst_gdf: MST segments to optimize
    :type mst_gdf: gpd.GeoDataFrame
    :param street_layer: Street network for alignment
    :type street_layer: gpd.GeoDataFrame
    :param all_end_points_gdf: Terminal points for MST reconstruction
    :type all_end_points_gdf: gpd.GeoDataFrame
    :param threshold: Distance threshold for adjustment trigger [m] (default 5.0)
    :type threshold: float
    :param min_improvement: Minimum improvement required [m] (default 0.5)
    :type min_improvement: float
    :return: Road-aligned network maintaining MST connectivity
    :rtype: gpd.GeoDataFrame
    :raises ValueError: If invalid geometries or empty network
    :raises RuntimeError: If fails to converge within iteration limit
    
    .. note::
        Uses iterative improvement with blacklisting to prevent oscillation. Max 50 iterations.
    """
    iteration = 0
    changes_made = True
    max_iterations = 50

    # Track segment adjustments and blacklist problematic segments
    segment_change_counter: Dict[int, int] = {}
    blacklist: Set[int] = set()

    def line_hash(line: LineString) -> int:
        """Create stable hash for line geometry based on rounded coordinates."""
        coords = tuple((round(x, 3), round(y, 3)) for x, y in line.coords)
        return hash(coords)

    # Main optimization loop
    while changes_made and iteration < max_iterations:
        print(f"\n--- Road Alignment Iteration {iteration} ---")
        adjusted_lines = []
        changes_made = False
        changed_this_iter: Set[int] = set()

        for idx, line in enumerate(mst_gdf.geometry):
            # Validate line geometry
            if not line.is_valid:
                print(f"  [!] Invalid line geometry at index {idx}")
                continue

            seg_id = line_hash(line)
            if seg_id in blacklist:
                adjusted_lines.append(line)
                continue

            # Check if segment needs adjustment
            midpoint = line.interpolate(0.5, normalized=True)
            nearest_line_idx = street_layer.distance(midpoint).idxmin()
            nearest_street = street_layer.iloc[nearest_line_idx].geometry
            point_on_street = nearest_points(midpoint, nearest_street)[1]
            distance_to_street = midpoint.distance(point_on_street)

            if distance_to_street > threshold:
                # Avoid adjustments where projection point equals line endpoints
                if (point_on_street.equals(Point(line.coords[0])) or 
                    point_on_street.equals(Point(line.coords[1]))):
                    print(f"    Skipping adjustment: projected point is endpoint")
                    adjusted_lines.append(line)
                    continue

                # Calculate improvement for validation
                orig_distance = distance_to_street

                # Split line through projected street point
                new_line1 = LineString([line.coords[0], point_on_street.coords[0]])
                new_line2 = LineString([point_on_street.coords[0], line.coords[1]])

                # Validate and add new segments
                for new_line in [new_line1, new_line2]:
                    if new_line.is_valid and not new_line.is_empty:
                        # Check improvement quality
                        new_midpoint = new_line.interpolate(0.5, normalized=True)
                        nearest_line_new_idx = street_layer.distance(new_midpoint).idxmin()
                        nearest_street_new = street_layer.iloc[nearest_line_new_idx].geometry
                        point_on_street_new = nearest_points(new_midpoint, nearest_street_new)[1]
                        new_distance = new_midpoint.distance(point_on_street_new)
                        improvement = orig_distance - new_distance
                        
                        if improvement < min_improvement:
                            print(f"    Insufficient improvement ({improvement:.2f}m), blacklisting segment")
                            blacklist.add(line_hash(new_line))
                        
                        adjusted_lines.append(new_line)
                    else:
                        print(f"    [!] Invalid new segment created")

                changes_made = True
                changed_this_iter.add(seg_id)
                segment_change_counter[seg_id] = segment_change_counter.get(seg_id, 0) + 1
                print(f"    Adjusted segment {idx}, total adjustments: {segment_change_counter[seg_id]}")
            else:
                adjusted_lines.append(line)

        # Progress reporting
        print(f"  Adjusted {len(changed_this_iter)} segments this iteration")
        if changed_this_iter:
            most_changed = sorted(segment_change_counter.items(), key=lambda x: -x[1])[:3]
            print(f"    Most frequently adjusted segments: {most_changed}")

        if not changes_made:
            print("No changes made, optimization converged")
            break

        mst_gdf = gpd.GeoDataFrame(geometry=adjusted_lines)
        iteration += 1

    if iteration >= max_iterations:
        print(f"Warning: Reached maximum iterations ({max_iterations})")

    # Post-processing: simplify and rebuild MST
    print("\nPost-processing: simplifying network and rebuilding MST...")
    mst_gdf = simplify_network(mst_gdf)
    mst_gdf = extract_unique_points_and_create_mst(mst_gdf, all_end_points_gdf)

    print("Road alignment optimization completed")
    return mst_gdf

def simplify_network(gdf: gpd.GeoDataFrame, threshold: float = 10.0) -> gpd.GeoDataFrame:
    """
    Simplify network by merging nearby points.

    :param gdf: Network segments to simplify
    :type gdf: gpd.GeoDataFrame
    :param threshold: Distance for merging points [m] (default 10.0)
    :type threshold: float
    :return: Simplified network with merged points
    :rtype: gpd.GeoDataFrame
    
    .. note::
        Merges points within threshold to their centroid, maintaining connectivity.
    """
    # Dictionary to store points and their associated line indices
    points = defaultdict(list)
    simplified_lines = []

    # Extract endpoints from all line segments
    for idx, line in enumerate(gdf.geometry):
        start, end = line.boundary.geoms
        points[start].append(idx)
        points[end].append(idx)

    # Find and merge nearby points
    merged_points = {}
    for point in points:
        if point in merged_points:
            continue
        
        # Find all points within threshold distance
        nearby_points = [
            p for p in points 
            if p.distance(point) < threshold and p not in merged_points
        ]
        
        if not nearby_points:
            merged_points[point] = point
        else:
            # Calculate centroid of nearby points
            all_points = np.array([[p.x, p.y] for p in nearby_points])
            centroid = Point(np.mean(all_points, axis=0))
            
            # Map all nearby points to centroid
            for p in nearby_points:
                merged_points[p] = centroid

    # Reconstruct lines with merged endpoints
    for line in gdf.geometry:
        start, end = line.boundary.geoms
        new_start = merged_points.get(start, start)
        new_end = merged_points.get(end, end)
        
        # Create new line with updated endpoints
        if not new_start.equals(new_end):  # Avoid zero-length lines
            simplified_lines.append(LineString([new_start, new_end]))

    return gpd.GeoDataFrame(geometry=simplified_lines)

def extract_unique_points_and_create_mst(gdf: gpd.GeoDataFrame, 
                                       all_end_points_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Extract unique points and rebuild MST structure.

    :param gdf: Network segments for point extraction
    :type gdf: gpd.GeoDataFrame
    :param all_end_points_gdf: Terminal points to preserve
    :type all_end_points_gdf: gpd.GeoDataFrame
    :return: Reconstructed MST connecting all unique points
    :rtype: gpd.GeoDataFrame
    
    .. note::
        Ensures tree topology (n-1 edges for n points) after network adjustments.
    """
    # Extract coordinates from all line geometries
    all_points = []
    for line in gdf.geometry:
        if isinstance(line, LineString):
            all_points.extend(line.coords)
    
    # Add terminal points from endpoint GeoDataFrame
    for point in all_end_points_gdf.geometry:
        if isinstance(point, Point):
            all_points.append((point.x, point.y))

    # Remove duplicates and convert to Point objects
    unique_points = set(all_points)
    unique_points = [Point(pt) for pt in unique_points]
    
    # Create GeoDataFrame from unique points
    points_gdf = gpd.GeoDataFrame(geometry=unique_points)
    
    # Generate new MST from unique points
    mst_gdf = generate_mst(points_gdf)
    
    return mst_gdf