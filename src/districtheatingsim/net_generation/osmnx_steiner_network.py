"""
OSMnx-based district heating network generation using OpenStreetMap data,
Steiner Tree optimization, and edge-splitting algorithms for optimal street-based routing.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
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
    
    :param buildings: Building geometries (Point) in projected CRS
    :type buildings: gpd.GeoDataFrame
    :param generator_coords: List of (x, y) heat generator coordinates in same CRS
    :type generator_coords: List[Tuple[float, float]]
    :param buffer_meters: Buffer distance in meters around buildings
    :type buffer_meters: float
    :param network_type: OSM network type ('drive', 'drive_service', 'walk', 'bike', 'all')
    :type network_type: str
    :param target_crs: Target coordinate reference system
    :type target_crs: str
    :param custom_filter: Custom OSM filter string (overrides network_type)
    :type custom_filter: Optional[str]
    :return: Street network graph projected to target CRS
    :rtype: nx.MultiDiGraph
    :raises ValueError: If buildings is empty or has invalid CRS
    :raises ConnectionError: If OSMnx cannot download data from OpenStreetMap
    
    .. note::
       Custom filters use regex: '["highway"~"primary|secondary|tertiary|residential|service"]'
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
    Create Steiner Tree connecting terminal points on street network using Kou approximation.
    
    :param street_graph: Street network graph from OSMnx with node coordinates
    :type street_graph: nx.MultiDiGraph
    :param terminal_points: Terminal point geometries (buildings, generators)
    :type terminal_points: gpd.GeoDataFrame
    :param weight: Edge attribute for optimization (default 'length')
    :type weight: str
    :return: Undirected Steiner Tree subgraph connecting all terminals
    :rtype: nx.Graph
    :raises ValueError: If terminal_points is empty or street_graph has no nodes
    :raises KeyError: If weight attribute not found in edge data
    
    .. note::
       Kou algorithm complexity: O(|T|² |E| log |V|). Node coordinates preserved for edge-splitting.
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
    
    :param steiner_tree: Steiner Tree graph connecting terminal nodes
    :type steiner_tree: nx.Graph
    :param street_graph: Original street network with node coordinates
    :type street_graph: nx.MultiDiGraph
    :param terminal_points: Terminal point geometries
    :type terminal_points: gpd.GeoDataFrame
    :param node_threshold: Distance threshold for node vs edge connection (meters)
    :type node_threshold: float
    :return: (connection_info, edges_to_split) tuple
    :rtype: Tuple[List[Dict[str, Any]], Dict[Tuple, List[Dict[str, Any]]]]
    :raises ValueError: If terminal_points or steiner_tree is empty
    
    .. note::
       Uses exact (x, y) tuples instead of Point objects to prevent floating-point drift.
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
    
    :param steiner_tree: Steiner Tree graph to convert
    :type steiner_tree: nx.Graph
    :param street_graph: Original street graph with node coordinates
    :type street_graph: nx.MultiDiGraph
    :param edges_to_split: Dictionary of edges to split with split point info
    :type edges_to_split: Dict[Tuple, List[Dict[str, Any]]]
    :param crs: Coordinate reference system for output
    :type crs: str
    :return: Network segments as LineString geometries
    :rtype: gpd.GeoDataFrame
    
    .. note::
       Split points sorted by distance along edge to prevent overlapping segments.
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
    
    :param network_gdf: Network segments as LineString geometries
    :type network_gdf: gpd.GeoDataFrame
    :param protected_endpoints: Set of (x, y) coordinate tuples to protect
    :type protected_endpoints: set
    :param max_iterations: Maximum iterations for dead-end removal
    :type max_iterations: int
    :return: Cleaned network with dead ends removed
    :rtype: gpd.GeoDataFrame
    
    .. note::
       Nodes with degree 1 are removed unless in protected_endpoints.
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
    Create connection line geometries from terminals to network attachment points.
    
    :param connection_info: Connection information from edge-splitting algorithm
    :type connection_info: List[Dict[str, Any]]
    :param crs: Coordinate reference system for output
    :type crs: str
    :return: Connection lines as LineString geometries
    :rtype: gpd.GeoDataFrame
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
    
    :param supply_network: Supply network with LineString geometries
    :type supply_network: gpd.GeoDataFrame
    :param offset_x: Horizontal offset in meters
    :type offset_x: float
    :param offset_y: Vertical offset in meters
    :type offset_y: float
    :return: Return network with offset geometries
    :rtype: gpd.GeoDataFrame
    
    .. note::
       Typical offsets: 0.5-1.0m (district heating), 0.2-0.5m (building connections).
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
    
    :param buildings: Building locations with Point geometries and attributes
    :type buildings: gpd.GeoDataFrame
    :param offset_x: Horizontal offset matching return network (meters)
    :type offset_x: float
    :param offset_y: Vertical offset matching return network (meters)
    :type offset_y: float
    :param include_building_data: Include all building attributes in output
    :type include_building_data: bool
    :return: HAST connections with LineStrings and metadata
    :rtype: gpd.GeoDataFrame
    
    .. note::
       HAST = building substation connecting district network to building heating system.
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
    Create Erzeugeranlage (generator) cross-connection between supply and return.
    
    :param generator_coords: (x, y) coordinates of generator location
    :type generator_coords: Tuple[float, float]
    :param offset_x: Horizontal offset matching return network (meters)
    :type offset_x: float
    :param offset_y: Vertical offset matching return network (meters)
    :type offset_y: float
    :param crs: Coordinate reference system
    :type crs: str
    :return: Generator connection with LineString geometry
    :rtype: gpd.GeoDataFrame
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
    
    :param buildings: Building locations with Point geometries in projected CRS
    :type buildings: gpd.GeoDataFrame
    :param generator_coords: List of (x, y) generator coordinates in same CRS
    :type generator_coords: List[Tuple[float, float]]
    :param output_dir: Directory for output GeoJSON files
    :type output_dir: str
    :param return_offset: Horizontal offset for return network (meters)
    :type return_offset: float
    :param buffer_meters: Buffer around buildings for street download
    :type buffer_meters: float
    :param network_type: OSM network type ('drive', 'drive_service', etc.)
    :type network_type: str
    :param custom_filter: Custom OSM filter (overrides network_type)
    :type custom_filter: Optional[str]
    :param node_threshold: Distance threshold for node vs edge connection
    :type node_threshold: float
    :param remove_dead_ends_flag: Remove dead-end segments
    :type remove_dead_ends_flag: bool
    :param max_dead_end_iterations: Maximum iterations for dead-end removal
    :type max_dead_end_iterations: int
    :param include_building_data: Include building metadata in HAST output
    :type include_building_data: bool
    :param export_geojson: Export results to GeoJSON files
    :type export_geojson: bool
    :param target_crs: Target coordinate reference system
    :type target_crs: str
    :return: Dictionary with network GeoDataFrames and statistics
    :rtype: Dict[str, Any]
    :raises ValueError: If buildings is empty or has invalid CRS
    :raises FileNotFoundError: If output_dir cannot be created
    
    .. note::
       Exports unified Wärmenetz.geojson with supply, return, HAST, and generator networks.
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
        
        # Export in unified format
        try:
            from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema
            
            unified_geojson = NetworkGeoJSONSchema.create_network_geojson(
                flow_lines=supply_network,
                return_lines=return_network,
                building_connections=hast_connections,
                generator_connections=generator_connection,
                state="designed"
            )
            # Use default filename for unified network
            unified_filename = "Wärmenetz.geojson"
            unified_path = os.path.join(output_dir, unified_filename)
            NetworkGeoJSONSchema.export_to_file(unified_geojson, unified_path)
            logger.info(f"✓ Exported unified format: {unified_filename}")
            
            output_files = {'unified': unified_path}
        except Exception as e:
            logger.warning(f"Failed to export unified format: {e}")
            output_files = {}
        
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
    Generate OSMnx-based district heating network and export as GeoJSON files.
    
    :param osm_street_layer_geojson_file_name: OSM street network (not used in OSMnx mode)
    :type osm_street_layer_geojson_file_name: str
    :param data_csv_file_name: Building data CSV with UTM_X and UTM_Y columns
    :type data_csv_file_name: str
    :param coordinates: List of (x, y) generator coordinates
    :type coordinates: List[Tuple[float, float]]
    :param base_path: Base directory for export (creates Wärmenetz subdirectory)
    :type base_path: str
    :param algorithm: Network generation algorithm identifier
    :type algorithm: str
    :param offset_angle: Angle for return line offset (degrees)
    :type offset_angle: float
    :param offset_distance: Distance for return line separation (meters)
    :type offset_distance: float
    :param buffer_meters: Buffer around buildings for street download
    :type buffer_meters: float
    :param network_type: OSM network type
    :type network_type: str
    :param custom_filter: Custom OSM filter (overrides network_type)
    :type custom_filter: Optional[str]
    :param node_threshold: Distance threshold for node vs edge connection
    :type node_threshold: float
    :param remove_dead_ends_flag: Remove dead-end segments
    :type remove_dead_ends_flag: bool
    :param target_crs: Target coordinate reference system
    :type target_crs: str
    :raises FileNotFoundError: If CSV file not found
    :raises KeyError: If required CSV columns missing
    :raises ValueError: If invalid data or parameters
    :raises ConnectionError: If OSM download fails
    
    .. note::
       GUI-compatible interface matching generate_and_export_layers() for threading.
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
        logger.info(f"Exported unified network to: {output_dir}/Wärmenetz.geojson")
        logger.info(f"  - Flow lines: {result['n_supply_segments']} segments")
        logger.info(f"  - Return lines: {result['n_return_segments']} segments")
        logger.info(f"  - Building connections: {result['n_hast']} connections")
        logger.info(f"  - Generator connections: {result['n_generators']} generator(s)")
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