"""
OSMnx-based District Heating Network Generation
================================================

This module implements advanced district heating network generation using OpenStreetMap
data via OSMnx combined with Steiner Tree optimization and edge-splitting algorithms.

The workflow ensures optimal street-based routing while maintaining exact coordinate
precision for connection points to prevent network fragmentation.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-11-22

Key Features
------------
- Street network download from OpenStreetMap via OSMnx
- Steiner Tree approximation for minimal network topology
- Edge-splitting algorithm with exact coordinate matching
- Dead-end removal with connection endpoint protection
- Dual network generation (supply/return) with offset
- HAST cross-connections with full building metadata
- Generator cross-connection support

Technical Details
-----------------
The edge-splitting algorithm uses exact (x, y) coordinate tuples instead of
Shapely Point objects to prevent floating-point precision drift that can cause
network fragmentation. Connection endpoints are protected during dead-end removal
to maintain network connectivity.

See Also
--------
osmnx : OpenStreetMap network data retrieval
networkx : Graph algorithms including Steiner Tree
shapely : Geometric operations

Examples
--------
>>> from districtheatingsim.net_generation.osmnx_steiner_network import generate_osmnx_network
>>> 
>>> # Load building data
>>> buildings = gpd.read_file('buildings.csv')
>>> generator_coords = (480219, 5711597)
>>> 
>>> # Generate complete network
>>> result = generate_osmnx_network(
...     buildings=buildings,
...     generator_coords=generator_coords,
...     output_dir='output/',
...     return_offset=1.0
... )
>>> 
>>> print(f"Generated {result['n_supply_segments']} supply segments")
>>> print(f"Total length: {result['total_length_km']} km")
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import osmnx as ox
import networkx as nx
from shapely.geometry import Point, LineString
from collections import defaultdict
from typing import List, Tuple, Dict, Optional, Any
import os
import time
import logging
import traceback

# Configure logging
logger = logging.getLogger(__name__)

# Configure OSMnx
ox.settings.use_cache = True
ox.settings.log_console = False


def download_street_graph(
    buildings: gpd.GeoDataFrame,
    generator_coords: List[Tuple[float, float]],
    buffer_meters: float = 500.0,
    network_type: str = 'drive_service',
    target_crs: str = 'EPSG:25833',
    custom_filter: Optional[str] = None
) -> nx.MultiDiGraph:
    """
    Download street network from OpenStreetMap for given building area.
    
    Downloads the street network covering the building locations plus a buffer zone.
    The graph is projected to the specified coordinate reference system for metric
    calculations.
    
    Parameters
    ----------
    buildings : gpd.GeoDataFrame
        GeoDataFrame containing building geometries (Point) in projected CRS.
    generator_coords : list of tuple of float
        List of (x, y) coordinate tuples for heat generator locations in same CRS as buildings.
        Example: [(480219, 5711597)] or [(480219, 5711597), (480500, 5712000)]
    buffer_meters : float, optional
        Buffer distance in meters around buildings for network download.
        Default is 500.0 meters.
    network_type : str, optional
        Type of street network to download. Options include:
        
        - 'drive' : for cars (default roads)
        - 'drive_service' : includes service roads
        - 'walk' : for pedestrians
        - 'bike' : for bicycles
        - 'all' : all street types
        
        Default is 'drive_service'.
        Ignored if custom_filter is provided.
    custom_filter : str, optional
        Custom OSM filter string for precise highway type selection.
        Example: '["highway"~"primary|secondary|tertiary|residential|living_street|service"]'
        If provided, overrides network_type parameter.
        Default is None (uses network_type).
    target_crs : str, optional
        Target coordinate reference system for projection.
        Default is 'EPSG:25833' (UTM Zone 33N, Europe).
    
    Returns
    -------
    nx.MultiDiGraph
        NetworkX graph with street network, projected to target CRS.
        Node attributes include 'x' and 'y' coordinates in target CRS.
    
    Raises
    ------
    ValueError
        If buildings GeoDataFrame is empty or has invalid CRS.
    ConnectionError
        If OSMnx cannot download data from OpenStreetMap.
    
    Notes
    -----
    The function performs the following steps:
    
    1. Convert buildings to WGS84 (required for OSMnx)
    2. Create buffer polygon around all buildings
    3. Download street graph from OpenStreetMap
    4. Project graph to target CRS for metric calculations
    
    The buffer is converted from meters to degrees using approximate conversion
    (1 degree ≈ 111 km at equator). For more precise buffers, consider using
    projected CRS before conversion.
    
    Custom Filter Syntax:
        OSMnx uses regex patterns in custom filters. To filter for specific
        highway types (like your OSM download tags), use:
        
        - Single type: '["highway"="primary"]'
        - Multiple types: '["highway"~"primary|secondary|tertiary"]'
        - With service: '["highway"~"primary|secondary|tertiary|residential|living_street|service"]'
        
        This is more precise than network_type presets.
    
    Examples
    --------
    >>> buildings = gpd.read_file('buildings.shp')
    >>> generator_coords = [(480219, 5711597)]
    >>> 
    >>> # Using network_type (simple)
    >>> street_graph = download_street_graph(
    ...     buildings=buildings,
    ...     generator_coords=generator_coords,
    ...     buffer_meters=800.0,
    ...     network_type='drive'
    ... )
    >>> 
    >>> # Using custom_filter (precise control)
    >>> street_graph = download_street_graph(
    ...     buildings=buildings,
    ...     generator_coords=generator_coords,
    ...     buffer_meters=800.0,
    ...     custom_filter='["highway"~"primary|secondary|tertiary|residential|living_street|service"]'
    ... )
    >>> 
    >>> print(f"Downloaded {len(street_graph.nodes)} nodes")
    
    See Also
    --------
    osmnx.graph_from_polygon : OSMnx function for graph download
    osmnx.project_graph : OSMnx function for graph projection
    """
    if buildings.empty:
        raise ValueError("Buildings GeoDataFrame is empty")
    
    logger.info(f"Downloading street network with {buffer_meters}m buffer")
    
    # Convert buildings to WGS84 for OSMnx
    buildings_wgs84 = buildings.to_crs('EPSG:4326')
    
    # Convert generator coordinates to WGS84
    generator_points = [Point(coords[0], coords[1]) for coords in generator_coords]
    generator_gdf = gpd.GeoDataFrame(geometry=generator_points, crs=target_crs)
    generator_gdf_wgs84 = generator_gdf.to_crs('EPSG:4326')
    
    # Combine buildings and generators for polygon creation
    all_points_wgs84 = pd.concat([buildings_wgs84, generator_gdf_wgs84], ignore_index=True)
    
    # Create buffer polygon (convert meters to degrees approximately)
    buffer_degrees = buffer_meters / 111000.0
    area_polygon = all_points_wgs84.union_all().buffer(buffer_degrees)
    
    # Download street graph
    if custom_filter:
        logger.info(f"Using custom filter: {custom_filter}")
        street_graph = ox.graph_from_polygon(
            area_polygon,
            custom_filter=custom_filter,
            simplify=True
        )
    else:
        logger.info(f"Using network_type: {network_type}")
        street_graph = ox.graph_from_polygon(
            area_polygon,
            network_type=network_type,
            simplify=True
        )
    
    # Project to target CRS
    street_graph = ox.project_graph(street_graph, to_crs=target_crs)
    
    logger.info(f"Downloaded graph: {len(street_graph.nodes)} nodes, {len(street_graph.edges)} edges")
    
    return street_graph


def create_steiner_tree(
    street_graph: nx.MultiDiGraph,
    terminal_points: gpd.GeoDataFrame,
    weight: str = 'length'
) -> nx.Graph:
    """
    Create Steiner Tree connecting terminal points on street network.
    
    Computes an approximate minimum spanning tree that connects all terminal
    points using the street network. Uses the Kou approximation algorithm
    which provides a 2-approximation of the optimal Steiner Tree.
    
    Parameters
    ----------
    street_graph : nx.MultiDiGraph
        Street network graph from OSMnx with node coordinates.
    terminal_points : gpd.GeoDataFrame
        GeoDataFrame with terminal point geometries (buildings, generators).
    weight : str, optional
        Edge attribute to use as weight for optimization.
        Default is 'length' for shortest path by distance.
    
    Returns
    -------
    nx.Graph
        Undirected Steiner Tree subgraph connecting all terminals.
        Maintains same node and edge attributes as input graph.
    
    Raises
    ------
    ValueError
        If terminal_points is empty or street_graph has no nodes.
    KeyError
        If weight attribute not found in edge data.
    
    Notes
    -----
    Algorithm Steps:
    
    1. Find nearest street network node for each terminal point
    2. Create undirected version of street graph
    3. Compute Steiner Tree approximation using Kou algorithm
    4. Return minimal subgraph connecting all terminals
    
    The Kou algorithm has time complexity O(|T|² |E| log |V|) where:
    
    - T = number of terminal nodes
    - E = number of edges
    - V = number of vertices
    
    For large networks (>10000 nodes), consider preprocessing to extract
    relevant subgraph before computing Steiner Tree.
    
    Coordinate Precision:
        Node coordinates are preserved exactly from input graph.
        Important for subsequent edge-splitting operations.
    
    Examples
    --------
    >>> street_graph = download_street_graph(buildings)
    >>> terminals = gpd.GeoDataFrame(geometry=building_points)
    >>> steiner_tree = create_steiner_tree(
    ...     street_graph=street_graph,
    ...     terminal_points=terminals,
    ...     weight='length'
    ... )
    >>> print(f"Steiner Tree: {len(steiner_tree.nodes)} nodes, {len(steiner_tree.edges)} edges")
    
    See Also
    --------
    networkx.algorithms.approximation.steiner_tree : Steiner Tree algorithm
    osmnx.distance.nearest_nodes : Find nearest graph nodes
    """
    if terminal_points.empty:
        raise ValueError("Terminal points GeoDataFrame is empty")
    if len(street_graph.nodes) == 0:
        raise ValueError("Street graph has no nodes")
    
    logger.info(f"Creating Steiner Tree for {len(terminal_points)} terminals")
    
    # Find nearest nodes for each terminal
    terminal_nodes = []
    for idx, terminal in terminal_points.iterrows():
        nearest_node = ox.distance.nearest_nodes(
            street_graph,
            terminal.geometry.x,
            terminal.geometry.y
        )
        terminal_nodes.append(nearest_node)
    
    logger.debug(f"Mapped {len(terminal_nodes)} terminals to graph nodes")
    
    # Create Steiner Tree
    steiner_tree = nx.algorithms.approximation.steiner_tree(
        street_graph.to_undirected(),
        terminal_nodes,
        weight=weight
    )
    
    logger.info(f"Steiner Tree: {len(steiner_tree.nodes)} nodes, {len(steiner_tree.edges)} edges")
    
    return steiner_tree


def connect_terminals_with_edge_splitting(
    steiner_tree: nx.Graph,
    street_graph: nx.MultiDiGraph,
    terminal_points: gpd.GeoDataFrame,
    node_threshold: float = 0.1
) -> Tuple[List[Dict[str, Any]], Dict[Tuple, List[Dict[str, Any]]]]:
    """
    Connect terminal points to Steiner Tree using edge-splitting algorithm.
    
    Creates connections from each terminal to the nearest point on the Steiner Tree.
    If the nearest point is close to an existing node, connects to that node.
    Otherwise, marks the edge for splitting at the exact connection point.
    
    **CRITICAL**: Uses exact (x, y) coordinate tuples to prevent floating-point
    precision drift that causes network fragmentation.
    
    Parameters
    ----------
    steiner_tree : nx.Graph
        Steiner Tree graph connecting terminal node locations.
    street_graph : nx.MultiDiGraph
        Original street network graph with node coordinate data.
    terminal_points : gpd.GeoDataFrame
        GeoDataFrame containing terminal point geometries.
    node_threshold : float, optional
        Distance threshold in meters. If connection point is within this
        distance of an existing node, connect to node instead of splitting edge.
        Default is 0.1 meters.
    
    Returns
    -------
    connection_info : list of dict
        List of connection information for each terminal:
        
        - 'terminal_idx' : Index of terminal in input GeoDataFrame
        - 'terminal_coords' : (x, y) tuple of terminal location
        - 'network_coords' : (x, y) tuple of connection point on network
        - 'distance' : Distance from terminal to connection point
        - 'type' : 'node' or 'split' indicating connection type
        - 'edge' : Edge tuple (u, v) where connection is made
        
    edges_to_split : dict
        Dictionary mapping edge tuples to list of split point information:
        
        - key : (u, v) tuple identifying edge
        - value : list of dicts with 'split_coords' and 'terminal_idx'
    
    Raises
    ------
    ValueError
        If terminal_points or steiner_tree is empty.
    
    Notes
    -----
    Edge-Splitting Algorithm:
    
    1. Build edge dictionary with exact coordinate tuples
    2. For each terminal, find nearest point on each Steiner Tree edge
    3. Check if nearest point is close to existing node (< node_threshold)
    4. If yes: connection type = 'node', use node coordinates
    5. If no: connection type = 'split', store exact split coordinates
    6. Collect all split points per edge for later segmentation
    
    Coordinate Precision:
        **Uses (x, y) tuples instead of Point objects**
        Point objects cause floating-point drift during conversions:
        
        - Point → tuple → Point: coordinates may change slightly
        - Tuple → tuple: coordinates remain bit-identical
        
        This is CRITICAL for subsequent operations that match coordinates
        to connect networks without gaps.
    
    Examples
    --------
    >>> connection_info, edges_to_split = connect_terminals_with_edge_splitting(
    ...     steiner_tree=steiner_tree,
    ...     street_graph=street_graph,
    ...     terminal_points=buildings,
    ...     node_threshold=0.1
    ... )
    >>> print(f"Connections: {len(connection_info)}")
    >>> print(f"Edges to split: {len(edges_to_split)}")
    >>> 
    >>> # Check connection types
    >>> n_node = sum(1 for c in connection_info if c['type'] == 'node')
    >>> n_split = sum(1 for c in connection_info if c['type'] == 'split')
    >>> print(f"Node connections: {n_node}, Edge splits: {n_split}")
    
    See Also
    --------
    build_network_from_split_edges : Creates network segments from split information
    """
    if terminal_points.empty:
        raise ValueError("Terminal points GeoDataFrame is empty")
    if len(steiner_tree.edges) == 0:
        raise ValueError("Steiner tree has no edges")
    
    logger.info(f"Connecting {len(terminal_points)} terminals with edge-splitting")
    
    # Build edge dictionary with exact coordinate tuples
    edge_dict = {}
    for u, v in steiner_tree.edges():
        u_coords = (street_graph.nodes[u]['x'], street_graph.nodes[u]['y'])
        v_coords = (street_graph.nodes[v]['x'], street_graph.nodes[v]['y'])
        edge_dict[(u, v)] = {
            'line': LineString([u_coords, v_coords]),
            'u_coords': u_coords,
            'v_coords': v_coords
        }
    
    # Find connections and edges to split
    connection_info = []
    edges_to_split = defaultdict(list)
    
    for idx, terminal in terminal_points.iterrows():
        terminal_coords = (terminal.geometry.x, terminal.geometry.y)
        
        min_distance = float('inf')
        best_edge = None
        best_point = None
        best_type = None
        
        # Check all edges
        for edge_key, edge_data in edge_dict.items():
            edge_line = edge_data['line']
            nearest_point_on_edge = edge_line.interpolate(edge_line.project(Point(terminal_coords)))
            distance = Point(terminal_coords).distance(nearest_point_on_edge)
            
            if distance < min_distance:
                min_distance = distance
                best_edge = edge_key
                best_point = (nearest_point_on_edge.x, nearest_point_on_edge.y)
                
                # Check if close to node
                u_coords = edge_data['u_coords']
                v_coords = edge_data['v_coords']
                dist_to_u = Point(best_point).distance(Point(u_coords))
                dist_to_v = Point(best_point).distance(Point(v_coords))
                
                if dist_to_u < node_threshold:
                    best_point = u_coords
                    best_type = 'node'
                elif dist_to_v < node_threshold:
                    best_point = v_coords
                    best_type = 'node'
                else:
                    best_type = 'split'
        
        connection_info.append({
            'terminal_idx': idx,
            'terminal_coords': terminal_coords,
            'network_coords': best_point,
            'distance': min_distance,
            'type': best_type,
            'edge': best_edge
        })
        
        if best_type == 'split':
            edges_to_split[best_edge].append({
                'split_coords': best_point,
                'terminal_idx': idx
            })
    
    n_node_connections = sum(1 for c in connection_info if c['type'] == 'node')
    n_split_connections = sum(1 for c in connection_info if c['type'] == 'split')
    
    logger.info(f"Connections: {len(connection_info)} total ({n_node_connections} to nodes, {n_split_connections} splits)")
    logger.info(f"Edges to split: {len(edges_to_split)}")
    
    return connection_info, edges_to_split


def build_network_from_split_edges(
    steiner_tree: nx.Graph,
    street_graph: nx.MultiDiGraph,
    edges_to_split: Dict[Tuple, List[Dict[str, Any]]],
    crs: str = 'EPSG:25833'
) -> gpd.GeoDataFrame:
    """
    Build network segments from Steiner Tree with edge splitting.
    
    Creates LineString geometries for the main network, splitting edges at
    specified points to accommodate terminal connections. Maintains exact
    coordinate precision using tuples.
    
    Parameters
    ----------
    steiner_tree : nx.Graph
        Steiner Tree graph to convert to geometric network.
    street_graph : nx.MultiDiGraph
        Original street graph with node coordinate data.
    edges_to_split : dict
        Dictionary from connect_terminals_with_edge_splitting indicating
        which edges to split and where. Keys are edge tuples (u, v),
        values are lists of split point dictionaries.
    crs : str, optional
        Coordinate reference system for output GeoDataFrame.
        Default is 'EPSG:25833'.
    
    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame with LineString geometries representing network segments.
        Each row is one segment between nodes or split points.
    
    Notes
    -----
    Algorithm:
    
    1. For each edge in Steiner Tree:
       
       a. If edge not in edges_to_split: Create single LineString
       b. If edge in edges_to_split:
          
          - Sort split points by distance along edge
          - Create all_points = [start] + [splits] + [end]
          - Create segment between each consecutive pair
    
    2. Return GeoDataFrame with all segments
    
    The sorting ensures split points are in correct order along the edge,
    preventing overlapping or reversed segments.
    
    Examples
    --------
    >>> main_network = build_network_from_split_edges(
    ...     steiner_tree=steiner_tree,
    ...     street_graph=street_graph,
    ...     edges_to_split=edges_to_split,
    ...     crs='EPSG:25833'
    ... )
    >>> print(f"Network segments: {len(main_network)}")
    >>> print(f"Total length: {main_network.geometry.length.sum():.2f} m")
    
    See Also
    --------
    connect_terminals_with_edge_splitting : Generates edges_to_split dictionary
    """
    logger.info("Building network from split edges")
    
    main_network_lines = []
    
    # Build edge dictionary
    edge_dict = {}
    for u, v in steiner_tree.edges():
        u_coords = (street_graph.nodes[u]['x'], street_graph.nodes[u]['y'])
        v_coords = (street_graph.nodes[v]['x'], street_graph.nodes[v]['y'])
        edge_dict[(u, v)] = {
            'line': LineString([u_coords, v_coords]),
            'u_coords': u_coords,
            'v_coords': v_coords
        }
    
    # Process each edge
    for edge_key, edge_data in edge_dict.items():
        u_coords = edge_data['u_coords']
        v_coords = edge_data['v_coords']
        
        if edge_key in edges_to_split:
            # Sort split points along edge
            edge_line = edge_data['line']
            split_points = edges_to_split[edge_key]
            split_coords_with_distance = []
            for sp in split_points:
                dist_along = edge_line.project(Point(sp['split_coords']))
                split_coords_with_distance.append((dist_along, sp['split_coords']))
            split_coords_with_distance.sort()
            
            # Create segments
            all_points = [u_coords] + [sc for _, sc in split_coords_with_distance] + [v_coords]
            for i in range(len(all_points) - 1):
                segment = LineString([all_points[i], all_points[i+1]])
                main_network_lines.append(segment)
        else:
            # No split needed
            main_network_lines.append(LineString([u_coords, v_coords]))
    
    main_network_gdf = gpd.GeoDataFrame(geometry=main_network_lines, crs=crs)
    
    logger.info(f"Built network: {len(main_network_gdf)} segments")
    
    return main_network_gdf


def remove_dead_ends(
    network_gdf: gpd.GeoDataFrame,
    protected_endpoints: set,
    max_iterations: int = 10
) -> gpd.GeoDataFrame:
    """
    Remove dead-end segments while protecting connection endpoints.
    
    Iteratively removes network segments that end in dead ends (degree 1 nodes)
    while ensuring that connection endpoints for terminals are never removed.
    This optimizes the network by eliminating unnecessary branches.
    
    Parameters
    ----------
    network_gdf : gpd.GeoDataFrame
        GeoDataFrame with LineString geometries representing network segments.
    protected_endpoints : set of tuple
        Set of (x, y) coordinate tuples that must not be removed.
        Typically includes all terminal connection points.
    max_iterations : int, optional
        Maximum number of iterations for dead-end removal.
        Default is 10. Prevents infinite loops in unusual network topologies.
    
    Returns
    -------
    gpd.GeoDataFrame
        Cleaned network GeoDataFrame with dead ends removed.
        Maintains same CRS and structure as input.
    
    Notes
    -----
    Algorithm:
    
    1. Build endpoint degree count (number of segments touching each point)
    2. For each segment:
       
       - Check if start or end has degree = 1 (dead end)
       - Check if endpoint is in protected_endpoints
       - If dead end AND not protected: mark for removal
       - If not dead end OR protected: keep segment
    
    3. Update network, repeat until no more removals or max_iterations reached
    
    A node is considered a dead end if:
    
    - It has degree 1 (only one segment connected)
    - AND it is not in protected_endpoints
    
    Protection Strategy:
        By protecting connection endpoints, the algorithm ensures that
        all terminals remain connected to the network. Only truly unnecessary
        branches (e.g., extra street segments) are removed.
    
    Examples
    --------
    >>> # Protect all connection points
    >>> protected = set(conn['network_coords'] for conn in connection_info)
    >>> 
    >>> # Remove dead ends
    >>> cleaned_network = remove_dead_ends(
    ...     network_gdf=main_network,
    ...     protected_endpoints=protected,
    ...     max_iterations=10
    ... )
    >>> 
    >>> print(f"Before: {len(main_network)} segments")
    >>> print(f"After: {len(cleaned_network)} segments")
    >>> print(f"Removed: {len(main_network) - len(cleaned_network)} dead-end segments")
    
    See Also
    --------
    connect_terminals_with_edge_splitting : Generates connection points to protect
    """
    logger.info(f"Removing dead ends (protecting {len(protected_endpoints)} endpoints)")
    
    current_network = network_gdf.copy()
    
    for iteration in range(max_iterations):
        # Build degree count
        endpoint_degree = defaultdict(int)
        for geom in current_network.geometry:
            coords = list(geom.coords)
            start = tuple(coords[0])
            end = tuple(coords[-1])
            endpoint_degree[start] += 1
            endpoint_degree[end] += 1
        
        # Remove dead ends
        segments_to_keep = []
        removed_this_iteration = 0
        
        for geom in current_network.geometry:
            coords = list(geom.coords)
            start = tuple(coords[0])
            end = tuple(coords[-1])
            
            start_protected = start in protected_endpoints
            end_protected = end in protected_endpoints
            
            start_is_dead = (endpoint_degree[start] == 1 and not start_protected)
            end_is_dead = (endpoint_degree[end] == 1 and not end_protected)
            
            if start_is_dead or end_is_dead:
                removed_this_iteration += 1
            else:
                segments_to_keep.append(geom)
        
        if removed_this_iteration == 0:
            logger.info(f"Converged after {iteration + 1} iterations")
            break
        
        logger.debug(f"Iteration {iteration + 1}: Removed {removed_this_iteration} dead-end segments")
        current_network = gpd.GeoDataFrame(geometry=segments_to_keep, crs=current_network.crs)
    
    logger.info(f"Dead-end removal complete: {len(network_gdf)} → {len(current_network)} segments")
    
    return current_network


def create_connection_lines(
    connection_info: List[Dict[str, Any]],
    crs: str = 'EPSG:25833'
) -> gpd.GeoDataFrame:
    """
    Create connection line geometries from terminal to network attachment points.
    
    Converts connection information dictionaries into LineString geometries
    connecting each terminal to its attachment point on the main network.
    
    Parameters
    ----------
    connection_info : list of dict
        Connection information from connect_terminals_with_edge_splitting.
        Each dict must contain 'terminal_coords' and 'network_coords' tuples.
    crs : str, optional
        Coordinate reference system for output GeoDataFrame.
        Default is 'EPSG:25833'.
    
    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame with LineString geometries for each connection.
        One row per terminal connection.
    
    Examples
    --------
    >>> connection_lines = create_connection_lines(
    ...     connection_info=connection_info,
    ...     crs='EPSG:25833'
    ... )
    >>> print(f"Created {len(connection_lines)} connection lines")
    >>> print(f"Total connection length: {connection_lines.geometry.length.sum():.2f} m")
    """
    logger.info(f"Creating connection lines for {len(connection_info)} terminals")
    
    connection_lines = []
    for conn in connection_info:
        terminal_coords = conn['terminal_coords']
        network_coords = conn['network_coords']
        conn_line = LineString([terminal_coords, network_coords])
        connection_lines.append(conn_line)
    
    connections_gdf = gpd.GeoDataFrame(geometry=connection_lines, crs=crs)
    
    logger.info(f"Created {len(connections_gdf)} connection lines")
    
    return connections_gdf


def create_return_network(
    supply_network: gpd.GeoDataFrame,
    offset_x: float = 1.0,
    offset_y: float = 0.0
) -> gpd.GeoDataFrame:
    """
    Create return network by offsetting supply network geometries.
    
    Generates a parallel return network by translating all supply network
    segments by specified offset. This creates the dual-pipe system typical
    for district heating networks (supply and return).
    
    Parameters
    ----------
    supply_network : gpd.GeoDataFrame
        Supply network GeoDataFrame with LineString geometries.
    offset_x : float, optional
        Horizontal offset in meters. Default is 1.0 meter.
    offset_y : float, optional
        Vertical offset in meters. Default is 0.0 meters.
    
    Returns
    -------
    gpd.GeoDataFrame
        Return network GeoDataFrame with offset geometries.
        Maintains same structure and CRS as supply network.
    
    Notes
    -----
    The offset creates physical separation between supply and return pipes:
    
    - Prevents overlapping geometries in visualization
    - Represents realistic pipe placement in trenches
    - Enables separate hydraulic simulation
    
    Typical offset values:
    
    - 0.5 - 1.0 m: District heating networks
    - 0.2 - 0.5 m: Building service connections
    - 1.0 - 2.0 m: Large transmission mains
    
    Examples
    --------
    >>> return_network = create_return_network(
    ...     supply_network=supply_complete,
    ...     offset_x=1.0,
    ...     offset_y=0.0
    ... )
    >>> print(f"Return network: {len(return_network)} segments")
    
    See Also
    --------
    create_hast_connections : Creates cross-connections between supply and return
    """
    logger.info(f"Creating return network with offset ({offset_x}, {offset_y}) m")
    
    def offset_geometry(geom, dx=offset_x, dy=offset_y):
        coords = [(x + dx, y + dy) for x, y in geom.coords]
        return LineString(coords)
    
    return_network = supply_network.copy()
    return_network['geometry'] = return_network.geometry.apply(
        lambda geom: offset_geometry(geom, offset_x, offset_y)
    )
    
    logger.info(f"Created return network: {len(return_network)} segments")
    
    return return_network


def create_hast_connections(
    buildings: gpd.GeoDataFrame,
    offset_x: float = 1.0,
    offset_y: float = 0.0,
    include_building_data: bool = True
) -> gpd.GeoDataFrame:
    """
    Create HAST (Hausanschlussstation) cross-connections with building metadata.
    
    Generates cross-connections between supply and return networks at each
    building location. These represent building substations in district heating
    systems. Optionally includes all building metadata in the output.
    
    Parameters
    ----------
    buildings : gpd.GeoDataFrame
        Building locations with Point geometries and attribute data.
    offset_x : float, optional
        Horizontal offset matching return network. Default is 1.0 meter.
    offset_y : float, optional
        Vertical offset matching return network. Default is 0.0 meters.
    include_building_data : bool, optional
        If True, includes all building attributes in output GeoDataFrame.
        If False, only includes geometry, building_id, and length_m.
        Default is True.
    
    Returns
    -------
    gpd.GeoDataFrame
        HAST connections with LineString geometries and building metadata.
        Each connection links supply and return networks at building location.
        
        Always includes:
        
        - geometry : LineString from supply to return point
        - building_id : Index from input buildings GeoDataFrame
        - length_m : Length of connection line
        
        If include_building_data=True, also includes:
        
        - All columns from input buildings GeoDataFrame (except geometry)
        - Examples: Wärmebedarf, Gebäudetyp, VLT_max, RLT, Baujahr, etc.
    
    Notes
    -----
    HAST Structure:
        In district heating networks, HAST represents:
        
        - Hausanschlussstation (German): House connection station
        - Building substation with heat exchanger
        - Metering and control equipment
        - Connection point between district network and building
    
    The geometric connection is a horizontal line at the building location:
    
    - Start: (building_x, building_y) on supply network
    - End: (building_x + offset_x, building_y + offset_y) on return network
    
    Building Data:
        Including building metadata enables:
        
        - Heat demand assignment per consumer
        - Temperature requirements (supply/return)
        - Building-specific control strategies
        - Economic calculations per building
        - Renovation scenario analysis
    
    Examples
    --------
    >>> hast_connections = create_hast_connections(
    ...     buildings=buildings,
    ...     offset_x=1.0,
    ...     include_building_data=True
    ... )
    >>> 
    >>> print(f"Created {len(hast_connections)} HAST connections")
    >>> print(f"Columns: {list(hast_connections.columns)}")
    >>> 
    >>> # Access building data
    >>> if 'Wärmebedarf' in hast_connections.columns:
    ...     total_demand = hast_connections['Wärmebedarf'].sum()
    ...     print(f"Total heat demand: {total_demand:.0f} kW")
    
    See Also
    --------
    create_return_network : Creates offset return network
    create_generator_connection : Creates generator cross-connection
    """
    logger.info(f"Creating HAST connections for {len(buildings)} buildings")
    
    hast_lines = []
    for idx, building in buildings.iterrows():
        building_coords = (building.geometry.x, building.geometry.y)
        vorlauf_point = building_coords
        ruecklauf_point = (building_coords[0] + offset_x, building_coords[1] + offset_y)
        
        hast_line = LineString([vorlauf_point, ruecklauf_point])
        
        # Build properties dictionary
        hast_properties = {
            'geometry': hast_line,
            'building_id': idx,
            'length_m': hast_line.length
        }
        
        # Add all building attributes if requested
        if include_building_data:
            for col in buildings.columns:
                if col != 'geometry':
                    hast_properties[col] = building[col]
        
        hast_lines.append(hast_properties)
    
    hast_gdf = gpd.GeoDataFrame(hast_lines, crs=buildings.crs)
    
    logger.info(f"Created {len(hast_gdf)} HAST connections")
    if include_building_data:
        logger.debug(f"Included {len(hast_gdf.columns) - 1} building data columns")
    
    return hast_gdf


def create_generator_connection(
    generator_coords: Tuple[float, float],
    offset_x: float = 1.0,
    offset_y: float = 0.0,
    crs: str = 'EPSG:25833'
) -> gpd.GeoDataFrame:
    """
    Create Erzeugeranlage (generator) cross-connection.
    
    Generates cross-connection between supply and return networks at the
    heat generator location. Represents the central heat production facility.
    
    Parameters
    ----------
    generator_coords : tuple of float
        (x, y) coordinates of generator location in target CRS.
    offset_x : float, optional
        Horizontal offset matching return network. Default is 1.0 meter.
    offset_y : float, optional
        Vertical offset matching return network. Default is 0.0 meters.
    crs : str, optional
        Coordinate reference system. Default is 'EPSG:25833'.
    
    Returns
    -------
    gpd.GeoDataFrame
        Generator connection with LineString geometry.
        Includes generator_id and length_m attributes.
    
    Examples
    --------
    >>> generator_connection = create_generator_connection(
    ...     generator_coords=(480219, 5711597),
    ...     offset_x=1.0,
    ...     crs='EPSG:25833'
    ... )
    >>> print(f"Generator connection length: {generator_connection['length_m'].iloc[0]:.2f} m")
    
    See Also
    --------
    create_hast_connections : Creates building connections
    """
    logger.info(f"Creating generator connection at {generator_coords}")
    
    vorlauf_point = generator_coords
    ruecklauf_point = (generator_coords[0] + offset_x, generator_coords[1] + offset_y)
    
    erzeuger_line = LineString([vorlauf_point, ruecklauf_point])
    erzeuger_gdf = gpd.GeoDataFrame([{
        'geometry': erzeuger_line,
        'generator_id': 0,
        'length_m': erzeuger_line.length
    }], crs=crs)
    
    logger.info("Created generator connection")
    
    return erzeuger_gdf


def generate_osmnx_network(
    buildings: gpd.GeoDataFrame,
    generator_coords: List[Tuple[float, float]],
    output_dir: str,
    return_offset: float = 1.0,
    buffer_meters: float = 500.0,
    network_type: str = 'drive_service',
    custom_filter: Optional[str] = None,
    node_threshold: float = 0.1,
    remove_dead_ends_flag: bool = True,
    max_dead_end_iterations: int = 10,
    include_building_data: bool = True,
    export_geojson: bool = True,
    target_crs: str = 'EPSG:25833'
) -> Dict[str, Any]:
    """
    Generate complete district heating network using OSMnx and Steiner Tree.
    
    Main function that orchestrates the complete workflow for generating
    a street-based district heating network with optimal topology.
    
    Parameters
    ----------
    buildings : gpd.GeoDataFrame
        Building locations with Point geometries and optional attribute data.
        Must be in projected CRS (e.g., UTM).
    generator_coords : list of tuple of float
        List of (x, y) coordinate tuples for heat generator locations in same CRS as buildings.
        Can contain single or multiple generators.
        Example: [(480219, 5711597)] or [(480219, 5711597), (480500, 5712000)]
    output_dir : str
        Directory path for output GeoJSON files. Created if doesn't exist.
    return_offset : float, optional
        Horizontal offset in meters for return network. Default is 1.0 meter.
    buffer_meters : float, optional
        Buffer around buildings for street network download. Default is 500 meters.
    network_type : str, optional
        OSMnx network type. Default is 'drive_service'.
        Options: 'drive', 'drive_service', 'walk', 'bike', 'all'.
        Ignored if custom_filter is provided.
    custom_filter : str, optional
        Custom OSM filter for precise highway type selection.
        Example: '["highway"~"primary|secondary|tertiary|residential|living_street|service"]'
        If provided, overrides network_type parameter.
        Default is None (uses network_type).
    node_threshold : float, optional
        Distance threshold for node vs edge connection. Default is 0.1 meters.
    remove_dead_ends_flag : bool, optional
        Whether to remove dead-end segments. Default is True.
    max_dead_end_iterations : int, optional
        Maximum iterations for dead-end removal. Default is 10.
    include_building_data : bool, optional
        Include building metadata in HAST output. Default is True.
    export_geojson : bool, optional
        Export results to GeoJSON files. Default is True.
    target_crs : str, optional
        Target coordinate reference system. Default is 'EPSG:25833'.
    
    Returns
    -------
    dict
        Dictionary with network generation results:
        
        - 'supply_network' : GeoDataFrame with supply network
        - 'return_network' : GeoDataFrame with return network
        - 'hast_connections' : GeoDataFrame with HAST connections
        - 'generator_connection' : GeoDataFrame with generator connection(s)
        - 'connection_info' : List of connection information dicts
        - 'n_buildings' : Number of buildings
        - 'n_generators' : Number of generators
        - 'n_supply_segments' : Number of supply network segments
        - 'n_return_segments' : Number of return network segments
        - 'n_hast' : Number of HAST connections
        - 'total_length_km' : Total pipe length in kilometers
        - 'execution_time_s' : Execution time in seconds
        - 'output_files' : Dict with paths to output files (if exported)
    
    Raises
    ------
    ValueError
        If buildings GeoDataFrame is empty or has invalid CRS.
    FileNotFoundError
        If output_dir cannot be created.
    
    Notes
    -----
    Workflow Steps:
    
    1. Download street network from OpenStreetMap
    2. Add generator to terminals
    3. Create Steiner Tree on street network
    4. Connect terminals with edge-splitting algorithm
    5. Build main network from split edges
    6. Remove dead-end segments (optional)
    7. Create connection lines
    8. Combine supply network (main + connections)
    9. Create return network with offset
    10. Create HAST cross-connections with building data
    11. Create generator cross-connection
    12. Export to GeoJSON files (optional)
    
    Output Files (if export_geojson=True):
    
    - Vorlauf.geojson : Supply network
    - Ruecklauf.geojson : Return network
    - HAST.geojson : Building connections with metadata
    - Erzeugeranlagen.geojson : Generator connection
    
    Examples
    --------
    >>> import geopandas as gpd
    >>> from districtheatingsim.net_generation.osmnx_steiner_network import generate_osmnx_network
    >>> 
    >>> # Load building data
    >>> buildings = gpd.read_file('buildings.csv')
    >>> 
    >>> # Single generator
    >>> generator_coords = [(480219, 5711597)]
    >>> result = generate_osmnx_network(
    ...     buildings=buildings,
    ...     generator_coords=generator_coords,
    ...     output_dir='output/',
    ...     return_offset=1.0,
    ...     include_building_data=True
    ... )
    >>> 
    >>> # Multiple generators
    >>> generator_coords = [(480219, 5711597), (480500, 5712000)]
    >>> result = generate_osmnx_network(
    ...     buildings=buildings,
    ...     generator_coords=generator_coords,
    ...     output_dir='output/'
    ... )
    >>> 
    >>> # Generate with custom highway filter
    >>> result = generate_osmnx_network(
    ...     buildings=buildings,
    ...     generator_coords=[(480219, 5711597)],
    ...     output_dir='output/',
    ...     custom_filter='["highway"~"primary|secondary|tertiary|residential|living_street|service"]'
    ... )
    >>> 
    >>> # Print summary
    >>> print(f"Buildings: {result['n_buildings']}")
    >>> print(f"Supply segments: {result['n_supply_segments']}")
    >>> print(f"Total length: {result['total_length_km']:.2f} km")
    >>> print(f"Execution time: {result['execution_time_s']:.2f}s")
    >>> 
    >>> # Access network data
    >>> supply_network = result['supply_network']
    >>> hast_with_building_data = result['hast_connections']
    
    See Also
    --------
    download_street_graph : Downloads OSM street network
    create_steiner_tree : Creates optimal tree topology
    connect_terminals_with_edge_splitting : Connects terminals to network
    """
    logger.info("="*70)
    logger.info("OSMNX-BASED DISTRICT HEATING NETWORK GENERATION")
    logger.info("="*70)
    
    start_time = time.time()
    
    # Validate inputs
    if buildings.empty:
        raise ValueError("Buildings GeoDataFrame is empty")
    if buildings.crs is None:
        raise ValueError("Buildings GeoDataFrame must have a CRS defined")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Step 1: Download street graph
    logger.info("Step 1/12: Downloading street network")
    street_graph = download_street_graph(
        buildings=buildings,
        generator_coords=generator_coords,
        buffer_meters=buffer_meters,
        network_type=network_type,
        target_crs=target_crs,
        custom_filter=custom_filter
    )
    
    # Step 2: Add generators to terminals
    logger.info("Step 2/12: Preparing terminals")
    generator_points = [Point(coords[0], coords[1]) for coords in generator_coords]
    generator_gdf = gpd.GeoDataFrame(geometry=generator_points, crs=buildings.crs)
    all_terminals = pd.concat([buildings, generator_gdf], ignore_index=True)
    logger.info(f"Total terminals: {len(buildings)} buildings + {len(generator_coords)} generator(s) = {len(all_terminals)}")
    
    # Step 3: Create Steiner Tree
    logger.info("Step 3/12: Creating Steiner Tree")
    steiner_tree = create_steiner_tree(
        street_graph=street_graph,
        terminal_points=all_terminals,
        weight='length'
    )
    
    # Step 4: Connect terminals with edge-splitting
    logger.info("Step 4/12: Connecting terminals with edge-splitting")
    connection_info, edges_to_split = connect_terminals_with_edge_splitting(
        steiner_tree=steiner_tree,
        street_graph=street_graph,
        terminal_points=all_terminals,
        node_threshold=node_threshold
    )
    
    # Step 5: Build main network
    logger.info("Step 5/12: Building main network with split edges")
    main_network = build_network_from_split_edges(
        steiner_tree=steiner_tree,
        street_graph=street_graph,
        edges_to_split=edges_to_split,
        crs=target_crs
    )
    
    # Step 5b: Remove dead ends (optional)
    if remove_dead_ends_flag:
        logger.info("Step 5b/12: Removing dead ends")
        protected_endpoints = set(conn['network_coords'] for conn in connection_info)
        main_network = remove_dead_ends(
            network_gdf=main_network,
            protected_endpoints=protected_endpoints,
            max_iterations=max_dead_end_iterations
        )
    
    # Step 6: Create connection lines
    logger.info("Step 6/12: Creating connection lines")
    connections = create_connection_lines(
        connection_info=connection_info,
        crs=target_crs
    )
    
    # Step 7: Combine supply network
    logger.info("Step 7/12: Combining supply network")
    supply_network = gpd.GeoDataFrame(
        pd.concat([main_network, connections], ignore_index=True),
        crs=target_crs
    )
    logger.info(f"Supply network: {len(supply_network)} segments ({len(main_network)} main + {len(connections)} connections)")
    
    # Step 8: Create return network
    logger.info("Step 8/12: Creating return network")
    return_network = create_return_network(
        supply_network=supply_network,
        offset_x=return_offset,
        offset_y=0.0
    )
    
    # Step 9: Create HAST connections
    logger.info("Step 9/12: Creating HAST connections")
    hast_connections = create_hast_connections(
        buildings=buildings,
        offset_x=return_offset,
        offset_y=0.0,
        include_building_data=include_building_data
    )
    
    # Step 10: Create generator connections
    logger.info("Step 10/12: Creating generator connections")
    generator_connections_list = []
    for idx, gen_coords in enumerate(generator_coords):
        gen_conn = create_generator_connection(
            generator_coords=gen_coords,
            offset_x=return_offset,
            offset_y=0.0,
            crs=target_crs
        )
        # Add generator index
        gen_conn['generator_id'] = idx
        generator_connections_list.append(gen_conn)
    
    generator_connection = gpd.GeoDataFrame(
        pd.concat(generator_connections_list, ignore_index=True),
        crs=target_crs
    )
    logger.info(f"Created {len(generator_connection)} generator connection(s)")
    
    # Calculate statistics
    total_length_km = (
        supply_network.geometry.length.sum() + 
        return_network.geometry.length.sum()
    ) / 1000.0
    
    execution_time = time.time() - start_time
    
    # Step 11: Export to GeoJSON (optional)
    output_files = {}
    if export_geojson:
        logger.info("Step 11/12: Exporting to GeoJSON")
        
        supply_file = os.path.join(output_dir, "Vorlauf.geojson")
        return_file = os.path.join(output_dir, "Rücklauf.geojson")
        hast_file = os.path.join(output_dir, "HAST.geojson")
        erzeuger_file = os.path.join(output_dir, "Erzeugeranlagen.geojson")
        
        supply_network.to_file(supply_file, driver='GeoJSON')
        return_network.to_file(return_file, driver='GeoJSON')
        hast_connections.to_file(hast_file, driver='GeoJSON')
        generator_connection.to_file(erzeuger_file, driver='GeoJSON')
        
        output_files = {
            'vorlauf': supply_file,
            'ruecklauf': return_file,
            'hast': hast_file,
            'erzeuger': erzeuger_file
        }
        
        logger.info(f"✓ Exported to: {output_dir}")
    
    logger.info("Step 12/12: Complete")
    
    # Prepare result dictionary
    result = {
        'supply_network': supply_network,
        'return_network': return_network,
        'hast_connections': hast_connections,
        'generator_connection': generator_connection,
        'connection_info': connection_info,
        'n_buildings': len(buildings),
        'n_generators': len(generator_coords),
        'n_supply_segments': len(supply_network),
        'n_return_segments': len(return_network),
        'n_hast': len(hast_connections),
        'total_length_km': total_length_km,
        'execution_time_s': execution_time,
        'output_files': output_files
    }
    
    # Print summary
    logger.info("="*70)
    logger.info("GENERATION COMPLETE")
    logger.info("="*70)
    logger.info(f"Buildings: {result['n_buildings']}")
    logger.info(f"Generators: {result['n_generators']}")
    logger.info(f"Supply segments: {result['n_supply_segments']}")
    logger.info(f"Return segments: {result['n_return_segments']}")
    logger.info(f"HAST connections: {result['n_hast']}")
    logger.info(f"Total pipe length: {total_length_km:.2f} km")
    logger.info(f"Execution time: {execution_time:.2f}s")
    logger.info("="*70)
    
    return result


def generate_and_export_osmnx_layers(
    osm_street_layer_geojson_file_name: str,
    data_csv_file_name: str,
    coordinates: List[Tuple[float, float]],
    base_path: str,
    algorithm: str = "OSMnx",
    offset_angle: float = 0,
    offset_distance: float = 0.5,
    buffer_meters: float = 500.0,
    network_type: str = 'drive_service',
    custom_filter: Optional[str] = None,
    node_threshold: float = 0.1,
    remove_dead_ends_flag: bool = True,
    target_crs: str = 'EPSG:25833'
) -> None:
    """
    Generate OSMnx-based district heating network and export all layers as GeoJSON files.
    
    This function provides a complete workflow compatible with the GUI threading system,
    generating optimized street-based networks using OSMnx and Steiner Tree algorithms.
    It matches the interface of generate_and_export_layers() for drop-in replacement.
    
    Parameters
    ----------
    osm_street_layer_geojson_file_name : str
        Path to GeoJSON file containing OpenStreetMap street network data.
        Note: Not used in OSMnx mode as streets are downloaded directly from OSM.
    data_csv_file_name : str
        Path to CSV file containing building data with coordinates and attributes.
        Must include 'UTM_X' and 'UTM_Y' columns for spatial positioning.
    coordinates : List[Tuple[float, float]]
        List of coordinate tuples (x, y) for heat generator locations.
        Multiple generators are supported.
    base_path : str
        Base directory path for exporting generated network layers.
        Will create "Wärmenetz" subdirectory for organized file management.
    algorithm : str, optional
        Network generation algorithm identifier. Default is "OSMnx".
        Included for interface compatibility with generate_and_export_layers().
    offset_angle : float, optional
        Angle in degrees for parallel return line generation. Default is 0°.
        0° = eastward offset, 90° = northward offset.
        Converted to offset_x based on offset_distance.
    offset_distance : float, optional
        Distance in meters for parallel return line separation. Default is 0.5m.
        Applied as horizontal offset (offset_x) for return network.
    buffer_meters : float, optional
        Buffer around buildings for street network download. Default is 500 meters.
    network_type : str, optional
        OSMnx network type. Default is 'drive_service'.
        Options: 'drive', 'drive_service', 'walk', 'bike', 'all'.
        Ignored if custom_filter is provided.
    custom_filter : str, optional
        Custom OSM filter for precise highway type selection.
        Example: '["highway"~"primary|secondary|tertiary|residential|living_street|service"]'
        If provided, overrides network_type parameter.
    node_threshold : float, optional
        Distance threshold for node vs edge connection. Default is 0.1 meters.
    remove_dead_ends_flag : bool, optional
        Whether to remove dead-end segments. Default is True.
    target_crs : str, optional
        Target coordinate reference system. Default is 'EPSG:25833'.
    
    Returns
    -------
    None
        Function creates and exports GeoJSON files to specified directory structure.
    
    Notes
    -----
    Output File Structure:
        base_path/
        └── Wärmenetz/
            ├── Vorlauf.geojson      # Supply line network
            ├── Rücklauf.geojson     # Return line network
            ├── HAST.geojson         # Heat consumer connections with building data
            └── Erzeugeranlagen.geojson  # Heat generator connections
    
    Threading Compatibility:
        - Designed for use with NetGenerationThread in GUI
        - Same interface as generate_and_export_layers()
        - Error handling compatible with pyqtSignal error emission
        - Progress logging for user feedback
    
    Examples
    --------
    >>> # Basic usage matching generate_and_export_layers interface
    >>> generator_locations = [(480219, 5711597), (480500, 5712000)]
    >>> generate_and_export_osmnx_layers(
    ...     "streets.geojson",  # Not used, but required for interface
    ...     "buildings.csv",
    ...     generator_locations,
    ...     "output",
    ...     algorithm="OSMnx",
    ...     offset_distance=1.0
    ... )
    
    See Also
    --------
    generate_osmnx_network : Core network generation function
    generate_and_export_layers : Original MST/Steiner export function
    """
    logger.info("="*70)
    logger.info("OSMNX-BASED NETWORK GENERATION AND EXPORT")
    logger.info("="*70)
    
    try:
        # Load building data from CSV
        logger.info(f"Loading building data from: {data_csv_file_name}")
        df = pd.read_csv(data_csv_file_name, sep=';')
        
        # Validate required columns
        if 'UTM_X' not in df.columns or 'UTM_Y' not in df.columns:
            raise KeyError("CSV file must contain 'UTM_X' and 'UTM_Y' columns")
        
        # Create GeoDataFrame from building data
        buildings = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df.UTM_X, df.UTM_Y),
            crs=target_crs
        )
        logger.info(f"✓ Loaded {len(buildings)} buildings")
        
        # Validate generator coordinates
        if not coordinates or len(coordinates) == 0:
            raise ValueError("At least one generator location must be provided")
        
        logger.info(f"✓ Generator locations: {len(coordinates)}")
        
        # Create output directory structure
        output_dir = os.path.join(base_path, "Wärmenetz")
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"✓ Output directory: {output_dir}")
        
        # Calculate return network offset
        # Note: Currently using offset_distance as horizontal offset (offset_x)
        # Future enhancement: Calculate from offset_angle
        # offset_x = offset_distance * cos(radians(offset_angle))
        # offset_y = offset_distance * sin(radians(offset_angle))
        return_offset_x = offset_distance
        return_offset_y = 0.0
        
        logger.info(f"Network parameters:")
        logger.info(f"  - Buffer: {buffer_meters}m")
        logger.info(f"  - Network type: {network_type if not custom_filter else 'Custom filter'}")
        logger.info(f"  - Return offset: ({return_offset_x}, {return_offset_y})m")
        logger.info(f"  - Node threshold: {node_threshold}m")
        logger.info(f"  - Remove dead ends: {remove_dead_ends_flag}")
        
        # Generate complete network using OSMnx
        logger.info("")
        result = generate_osmnx_network(
            buildings=buildings,
            generator_coords=coordinates,
            output_dir=output_dir,
            return_offset=return_offset_x,
            buffer_meters=buffer_meters,
            network_type=network_type,
            custom_filter=custom_filter,
            node_threshold=node_threshold,
            remove_dead_ends_flag=remove_dead_ends_flag,
            max_dead_end_iterations=10,
            include_building_data=True,
            export_geojson=True,
            target_crs=target_crs
        )
        
        # Print final summary
        logger.info("")
        logger.info("="*70)
        logger.info("EXPORT COMPLETE")
        logger.info("="*70)
        logger.info(f"Exported files to: {output_dir}")
        logger.info(f"  - Vorlauf.geojson: {result['n_supply_segments']} segments")
        logger.info(f"  - Rücklauf.geojson: {result['n_return_segments']} segments")
        logger.info(f"  - HAST.geojson: {result['n_hast']} connections")
        logger.info(f"  - Erzeugeranlagen.geojson: {result['n_generators']} generator(s)")
        logger.info(f"Total pipe length: {result['total_length_km']:.2f} km")
        logger.info(f"Execution time: {result['execution_time_s']:.2f}s")
        logger.info("="*70)
        
    except FileNotFoundError as e:
        error_msg = f"File not found: {e}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    except KeyError as e:
        error_msg = f"Missing required data columns: {e}"
        logger.error(error_msg)
        raise KeyError(error_msg)
    except ValueError as e:
        error_msg = f"Invalid data or parameters: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except ConnectionError as e:
        error_msg = f"Failed to download OSM data: {e}"
        logger.error(error_msg)
        raise ConnectionError(error_msg)
    except Exception as e:
        error_msg = f"Network generation failed: {e}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise Exception(error_msg)
