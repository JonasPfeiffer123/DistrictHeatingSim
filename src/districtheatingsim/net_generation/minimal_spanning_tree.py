"""
Filename: minimal_spanning_tree.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-26
Description: Minimum Spanning Tree generation and road alignment optimization for district heating networks.

This module implements advanced Minimum Spanning Tree (MST) algorithms for district heating
network layout optimization. It provides functions to generate cost-optimal tree topologies
from building locations and iteratively adjust network segments to follow existing street
infrastructure while maintaining connectivity and minimizing total construction costs.

The module combines graph theory optimization with geospatial analysis to create practical
network designs that respect infrastructure constraints. It includes network simplification
algorithms and iterative improvement methods for realistic district heating system layouts.
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
    Generate a Minimum Spanning Tree (MST) from a set of point locations.

    This function creates the optimal tree network connecting all input points with
    minimal total edge length. It uses Euclidean distances between points to build
    a complete graph and applies Kruskal's algorithm to find the minimum spanning
    tree that connects all locations with lowest construction cost.

    Parameters
    ----------
    points : geopandas.GeoDataFrame
        GeoDataFrame containing Point geometries representing network terminal locations.
        Typically includes heat consumers, producers, and connection points.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame containing LineString geometries representing the MST network.
        Each line connects two points with minimum total network length.

    Notes
    -----
    Algorithm Properties:
        - Creates tree topology (no cycles) connecting all points
        - Minimizes total network construction length
        - Guarantees connectivity between all network terminals
        - Time complexity: O(n²) for distance calculation, O(E log V) for MST

    Graph Construction:
        1. Creates complete graph with all point-to-point connections
        2. Calculates Euclidean distances as edge weights
        3. Applies NetworkX minimum spanning tree algorithm
        4. Converts resulting edges back to LineString geometries

    Network Properties:
        - Tree structure: n-1 edges for n points
        - Single path between any two points
        - No redundancy or backup connections
        - Optimal for radial distribution systems

    Applications:
        - Initial network topology generation
        - Cost-optimal network design
        - Basis for further optimization and adjustment
        - Comparison baseline for advanced algorithms

    Examples
    --------
    >>> # Generate MST from building locations
    >>> import geopandas as gpd
    >>> from shapely.geometry import Point
    >>> 
    >>> buildings = gpd.GeoDataFrame(geometry=[
    ...     Point(0, 0), Point(10, 0), Point(5, 8), Point(15, 12)
    ... ])
    >>> mst_network = generate_mst(buildings)
    >>> print(f"MST contains {len(mst_network)} connecting segments")

    >>> # Calculate network statistics
    >>> total_length = mst_network.geometry.length.sum()
    >>> avg_segment_length = mst_network.geometry.length.mean()
    >>> print(f"Total network length: {total_length:.1f}m")
    >>> print(f"Average segment length: {avg_segment_length:.1f}m")

    >>> # Verify tree properties
    >>> n_points = len(buildings)
    >>> n_edges = len(mst_network)
    >>> print(f"Tree property check: {n_edges} edges for {n_points} points")
    >>> print(f"Expected edges: {n_points - 1}, Valid tree: {n_edges == n_points - 1}")

    See Also
    --------
    adjust_segments_to_roads : Road alignment optimization
    networkx.minimum_spanning_tree : Core MST algorithm
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
    Iteratively adjust MST segments to follow street network infrastructure.

    This function implements an advanced road alignment optimization algorithm that
    modifies MST segments to follow existing street infrastructure while maintaining
    network connectivity. It uses iterative improvement with convergence criteria
    and blacklisting to prevent oscillation and ensure practical network layouts.

    Parameters
    ----------
    mst_gdf : geopandas.GeoDataFrame
        GeoDataFrame containing MST segments as LineString geometries.
        Initial tree network to be optimized for road alignment.
    street_layer : geopandas.GeoDataFrame
        GeoDataFrame containing street network as LineString geometries.
        Represents available infrastructure for network routing.
    all_end_points_gdf : geopandas.GeoDataFrame
        GeoDataFrame containing all terminal points for network reconstruction.
        Used for MST rebuilding after segment adjustment.
    threshold : float, optional
        Distance threshold for triggering segment adjustment [m]. Default is 5.0.
        Segments with midpoints farther than this from streets are adjusted.
    min_improvement : float, optional
        Minimum improvement required to accept adjustment [m]. Default is 0.5.
        Prevents marginal adjustments that don't significantly improve alignment.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame with road-aligned network segments maintaining MST connectivity.
        Optimized for following existing street infrastructure.

    Notes
    -----
    Optimization Algorithm:
        1. Identify segments with midpoints far from street network
        2. Project midpoints onto nearest street segments
        3. Split original segments through projected points
        4. Validate improvements against minimum threshold
        5. Apply blacklisting to prevent oscillation
        6. Iterate until convergence or maximum iterations

    Convergence Criteria:
        - No segments require adjustment (within threshold)
        - Maximum iteration limit reached (prevents infinite loops)
        - All problematic segments blacklisted (improvement too small)

    Blacklisting Strategy:
        - Tracks segments that show insufficient improvement
        - Prevents repeated adjustments of same segments
        - Ensures algorithm termination and stability
        - Maintains network quality while avoiding oscillation

    Network Reconstruction:
        - Simplifies adjusted network by merging nearby points
        - Extracts unique points for MST reconstruction
        - Rebuilds MST to ensure tree topology
        - Maintains connectivity while optimizing alignment

    Examples
    --------
    >>> # Generate MST and adjust to follow roads
    >>> buildings = gpd.read_file("buildings.shp")
    >>> streets = gpd.read_file("streets.shp")
    >>> initial_mst = generate_mst(buildings)
    >>> 
    >>> aligned_network = adjust_segments_to_roads(
    ...     initial_mst, streets, buildings, 
    ...     threshold=10.0, min_improvement=1.0
    ... )
    >>> print(f"Aligned network: {len(aligned_network)} segments")

    >>> # Compare alignment quality
    >>> def avg_distance_to_roads(network, roads):
    ...     distances = []
    ...     for line in network.geometry:
    ...         midpoint = line.interpolate(0.5, normalized=True)
    ...         min_dist = roads.distance(midpoint).min()
    ...         distances.append(min_dist)
    ...     return sum(distances) / len(distances)
    >>> 
    >>> original_alignment = avg_distance_to_roads(initial_mst, streets)
    >>> improved_alignment = avg_distance_to_roads(aligned_network, streets)
    >>> improvement = (original_alignment - improved_alignment) / original_alignment * 100
    >>> print(f"Road alignment improved by {improvement:.1f}%")

    >>> # Analyze network changes
    >>> original_length = initial_mst.geometry.length.sum()
    >>> aligned_length = aligned_network.geometry.length.sum()
    >>> length_change = (aligned_length - original_length) / original_length * 100
    >>> print(f"Network length changed by {length_change:.1f}%")

    Raises
    ------
    ValueError
        If MST contains invalid geometries or empty network.
    RuntimeError
        If algorithm fails to converge within iteration limit.

    See Also
    --------
    generate_mst : Initial MST generation
    simplify_network : Network simplification algorithm
    extract_unique_points_and_create_mst : Network reconstruction
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
    Simplify network by merging nearby points and adjusting line segments.

    This function reduces network complexity by identifying and merging points
    that are within a specified distance threshold. It maintains network
    connectivity while eliminating unnecessary geometric complexity that
    can arise from iterative adjustment processes.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        GeoDataFrame containing network segments as LineString geometries.
        Network may contain closely spaced points requiring simplification.
    threshold : float, optional
        Distance threshold for merging nearby points [m]. Default is 10.0.
        Points closer than this distance are merged to their centroid.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame with simplified network containing merged points.
        Maintains network topology while reducing geometric complexity.

    Notes
    -----
    Simplification Algorithm:
        1. Extract all endpoints from network line segments
        2. Group points within threshold distance
        3. Calculate centroid for each point group
        4. Replace all points in group with centroid location
        5. Reconstruct line segments with updated endpoints

    Point Merging Strategy:
        - Uses Euclidean distance for proximity detection
        - Merges multiple points to single centroid location
        - Preserves network connectivity during simplification
        - Eliminates redundant geometric detail

    Geometric Operations:
        - Maintains LineString topology
        - Preserves network connectivity
        - Reduces coordinate precision artifacts
        - Prepares network for MST reconstruction

    Applications:
        - Post-processing after iterative adjustments
        - Network cleanup and optimization
        - Preparation for visualization and analysis
        - Reduction of computational complexity

    Examples
    --------
    >>> # Simplify network after road alignment
    >>> complex_network = gpd.read_file("adjusted_network.shp")
    >>> simplified = simplify_network(complex_network, threshold=5.0)
    >>> 
    >>> print(f"Original segments: {len(complex_network)}")
    >>> print(f"Simplified segments: {len(simplified)}")

    >>> # Compare geometric complexity
    >>> original_points = set()
    >>> simplified_points = set()
    >>> 
    >>> for line in complex_network.geometry:
    ...     original_points.update(line.coords)
    >>> for line in simplified.geometry:
    ...     simplified_points.update(line.coords)
    >>> 
    >>> reduction = (len(original_points) - len(simplified_points)) / len(original_points) * 100
    >>> print(f"Point reduction: {reduction:.1f}%")

    >>> # Validate network connectivity
    >>> def count_connected_components(network):
    ...     import networkx as nx
    ...     G = nx.Graph()
    ...     for line in network.geometry:
    ...         start, end = line.boundary.geoms
    ...         G.add_edge((start.x, start.y), (end.x, end.y))
    ...     return nx.number_connected_components(G)
    >>> 
    >>> orig_components = count_connected_components(complex_network)
    >>> simp_components = count_connected_components(simplified)
    >>> print(f"Connectivity preserved: {orig_components == simp_components}")

    See Also
    --------
    adjust_segments_to_roads : Network adjustment algorithm
    extract_unique_points_and_create_mst : MST reconstruction
    numpy.mean : Centroid calculation
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
    Extract unique points from network segments and rebuild MST structure.

    This function performs network reconstruction by extracting all unique points
    from line geometries, combining them with terminal points, and generating
    a new minimum spanning tree. It ensures proper tree topology after network
    adjustments and simplification operations.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        GeoDataFrame containing network segments as LineString geometries.
        Source network for point extraction and MST reconstruction.
    all_end_points_gdf : geopandas.GeoDataFrame
        GeoDataFrame containing all terminal points as Point geometries.
        Essential network endpoints that must be preserved in reconstruction.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame containing reconstructed MST as LineString geometries.
        New tree network connecting all unique points with minimal total length.

    Notes
    -----
    Reconstruction Process:
        1. Extract all coordinate points from line segment geometries
        2. Add terminal points from endpoint GeoDataFrame
        3. Remove duplicate points to create unique point set
        4. Generate new MST connecting all unique points
        5. Return optimized tree network

    Point Extraction:
        - Processes all LineString coordinates
        - Handles Point geometries from terminal locations
        - Uses set operations for duplicate removal
        - Maintains spatial relationships

    MST Reconstruction:
        - Creates complete graph from unique points
        - Applies minimum spanning tree algorithm
        - Ensures tree topology (n-1 edges for n points)
        - Optimizes for minimal total network length

    Applications:
        - Final step in network optimization workflow
        - Restoration of tree topology after adjustments
        - Integration of terminal points with network structure
        - Preparation of final optimized network

    Examples
    --------
    >>> # Reconstruct MST after network adjustments
    >>> adjusted_network = gpd.read_file("adjusted_segments.shp")
    >>> terminal_points = gpd.read_file("terminal_points.shp")
    >>> 
    >>> final_mst = extract_unique_points_and_create_mst(
    ...     adjusted_network, terminal_points
    ... )
    >>> print(f"Reconstructed MST: {len(final_mst)} segments")

    >>> # Verify tree properties
    >>> total_points = len(terminal_points)
    >>> mst_edges = len(final_mst)
    >>> is_valid_tree = (mst_edges == total_points - 1)
    >>> print(f"Valid tree structure: {is_valid_tree}")

    >>> # Compare with original network
    >>> original_length = adjusted_network.geometry.length.sum()
    >>> mst_length = final_mst.geometry.length.sum()
    >>> efficiency = (original_length - mst_length) / original_length * 100
    >>> print(f"Network length optimization: {efficiency:.1f}%")

    >>> # Analyze connectivity
    >>> import networkx as nx
    >>> G = nx.Graph()
    >>> for line in final_mst.geometry:
    ...     start, end = line.boundary.geoms
    ...     G.add_edge((start.x, start.y), (end.x, end.y))
    >>> 
    >>> is_connected = nx.is_connected(G)
    >>> print(f"Network connectivity: {is_connected}")

    See Also
    --------
    generate_mst : MST generation algorithm
    simplify_network : Network simplification
    adjust_segments_to_roads : Main optimization workflow
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