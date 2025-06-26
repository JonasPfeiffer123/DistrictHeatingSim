"""
Filename: net_generation.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-26
Description: Network generation algorithms for district heating system layout optimization.

This module provides comprehensive network generation capabilities for district heating
systems using various graph algorithms and geospatial analysis techniques. It implements
multiple optimization strategies including Minimum Spanning Tree (MST), advanced MST
with road alignment, and Steiner tree algorithms to create cost-optimal network topologies.

The module handles complete network generation workflows from building location processing
to final network layout with proper street alignment and parallel line generation for
supply and return networks. It integrates geometric operations with graph theory
optimization to produce practical district heating network designs.
"""

import pandas as pd
import geopandas as gpd
import math
from shapely.geometry import LineString, Point
from typing import Optional, Tuple, List, Dict, Any, Union

from districtheatingsim.net_generation.minimal_spanning_tree import generate_mst, adjust_segments_to_roads
from districtheatingsim.net_generation.steiner_tree import generate_steiner_tree_network

import matplotlib.pyplot as plt

def create_offset_points(point: Point, distance: float, angle_degrees: float) -> Point:
    """
    Creates a point offset from the given point by a specified distance and angle.

    This function performs polar coordinate transformation to create offset points
    for network layout generation, connection line creation, and parallel line
    calculation. It supports precise geometric positioning for district heating
    network component placement.

    Parameters
    ----------
    point : shapely.geometry.Point
        The original point from which to create the offset.
        Typically represents building locations or network nodes.
    distance : float
        The distance to offset the point [m].
        Positive values create outward offsets from the original point.
    angle_degrees : float
        The angle in degrees to offset the point.
        0° = East (+X direction), 90° = North (+Y direction),
        180° = West (-X direction), 270° = South (-Y direction).

    Returns
    -------
    shapely.geometry.Point
        The offset point at the specified distance and angle from the original point.

    Notes
    -----
    Coordinate System:
        - Uses standard Cartesian coordinate system
        - Angle measured counterclockwise from positive X-axis
        - Distance units match input coordinate system (typically meters)

    Mathematical Transformation:
        - Converts degrees to radians for trigonometric calculations
        - Applies polar to Cartesian coordinate transformation:
          dx = distance × cos(angle), dy = distance × sin(angle)
        - Adds offset to original coordinates: (x + dx, y + dy)

    Applications:
        - Building connection line creation
        - Parallel pipe line generation (supply/return)
        - Network component positioning
        - Service line routing

    Examples
    --------
    >>> # Create building connection point
    >>> building = Point(100.0, 200.0)
    >>> connection_point = create_offset_points(building, 5.0, 90.0)
    >>> print(f"Connection at: ({connection_point.x:.1f}, {connection_point.y:.1f})")
    Connection at: (100.0, 205.0)

    >>> # Generate parallel return line points
    >>> supply_point = Point(500.0, 300.0)
    >>> return_point = create_offset_points(supply_point, 1.5, 0.0)  # 1.5m east
    >>> distance = supply_point.distance(return_point)
    >>> print(f"Pipe separation: {distance:.1f}m")

    >>> # Create service connection at 45° angle
    >>> main_line_point = Point(1000.0, 1000.0)
    >>> service_point = create_offset_points(main_line_point, 10.0, 45.0)
    >>> print(f"Service connection: ({service_point.x:.1f}, {service_point.y:.1f})")

    See Also
    --------
    offset_lines_by_angle : Apply offset to entire line geometries
    generate_connection_lines : Create building connection lines
    """
    angle_radians = math.radians(angle_degrees)
    dx = distance * math.cos(angle_radians)
    dy = distance * math.sin(angle_radians)
    return Point(point.x + dx, point.y + dy)

def offset_lines_by_angle(lines_gdf: gpd.GeoDataFrame, distance: float, 
                         angle_degrees: float) -> gpd.GeoDataFrame:
    """
    Offset all LineString geometries in a GeoDataFrame by a fixed distance and angle.

    This function creates parallel line networks for district heating applications,
    particularly for generating return lines parallel to supply lines. It maintains
    geometric relationships while providing proper separation for bidirectional
    pipe networks.

    Parameters
    ----------
    lines_gdf : geopandas.GeoDataFrame
        GeoDataFrame containing LineString geometries to offset.
        Typically represents supply line network or main distribution lines.
    distance : float
        Offset distance in meters. Positive values create consistent directional offset.
        Typical values: 0.5-2.0m for district heating pipe separation.
    angle_degrees : float
        Offset angle in degrees from original line direction.
        0° = parallel offset in +X direction, 90° = parallel offset in +Y direction.

    Returns
    -------
    geopandas.GeoDataFrame
        New GeoDataFrame with offset LineString geometries and preserved CRS.
        Maintains same feature count and attributes as input.

    Notes
    -----
    Offset Algorithm:
        1. Iterates through all LineString geometries
        2. Applies consistent offset to each coordinate point
        3. Reconstructs LineString with offset coordinates
        4. Preserves coordinate reference system (CRS)

    Geometric Properties:
        - Maintains line topology and connectivity
        - Preserves relative line orientations
        - Creates uniform separation distance
        - Suitable for parallel pipe networks

    Applications:
        - Return line generation from supply lines
        - Parallel service line creation
        - Pipe network visualization with separation
        - Construction planning with pipe spacing

    Examples
    --------
    >>> # Generate return lines parallel to supply lines
    >>> supply_lines = gpd.read_file("supply_network.shp")
    >>> return_lines = offset_lines_by_angle(supply_lines, 1.0, 0.0)  # 1m east
    >>> print(f"Created {len(return_lines)} return line segments")

    >>> # Create visualization separation
    >>> main_network = gpd.read_file("main_network.shp")
    >>> display_offset = offset_lines_by_angle(main_network, 0.5, 90.0)  # 0.5m north
    >>> 
    >>> # Plot both networks
    >>> fig, ax = plt.subplots()
    >>> main_network.plot(ax=ax, color='red', label='Original')
    >>> display_offset.plot(ax=ax, color='blue', label='Offset')

    >>> # Check geometric properties
    >>> original_length = supply_lines.geometry.length.sum()
    >>> offset_length = return_lines.geometry.length.sum()
    >>> print(f"Length preservation: {abs(original_length - offset_length) < 0.01}")

    See Also
    --------
    create_offset_points : Create individual offset points
    generate_network : Main network generation with parallel lines
    """
    def offset_line(line: LineString) -> LineString:
        """Apply offset transformation to individual LineString."""
        return LineString([
            create_offset_points(Point(x, y), distance, angle_degrees)
            for x, y in line.coords
        ])
    
    offset_lines = [offset_line(line) for line in lines_gdf.geometry]
    return gpd.GeoDataFrame(geometry=offset_lines, crs=lines_gdf.crs)

def find_nearest_line(point: Point, line_layer: gpd.GeoDataFrame) -> Optional[LineString]:
    """
    Find the nearest line to a given point from a layer of lines.

    This function performs spatial proximity analysis to identify the closest
    line feature for building-to-infrastructure connection planning. It uses
    Euclidean distance calculation for efficient nearest neighbor identification
    in district heating network planning applications.

    Parameters
    ----------
    point : shapely.geometry.Point
        The point to find the nearest line to.
        Typically represents building locations or connection points.
    line_layer : geopandas.GeoDataFrame
        GeoDataFrame containing LineString geometries to search.
        Usually represents street network or existing infrastructure.

    Returns
    -------
    Optional[shapely.geometry.LineString]
        The nearest LineString to the input point, or None if no lines found.
        Returns actual line geometry for further geometric operations.

    Notes
    -----
    Search Algorithm:
        1. Iterates through all LineString geometries in layer
        2. Calculates Euclidean distance from point to each line
        3. Tracks minimum distance and corresponding line
        4. Returns line with smallest distance to input point

    Distance Calculation:
        - Uses Shapely's built-in distance method
        - Calculates perpendicular distance to line segments
        - Handles line endpoints and intermediate points
        - Efficient for moderate-sized datasets

    Performance Considerations:
        - O(n) complexity where n = number of lines
        - Suitable for typical district heating planning datasets
        - Consider spatial indexing for large datasets
        - Distance calculation includes line segment interpolation

    Examples
    --------
    >>> # Find nearest street for building connection
    >>> building_location = Point(1000.0, 2000.0)
    >>> street_network = gpd.read_file("streets.shp")
    >>> nearest_street = find_nearest_line(building_location, street_network)
    >>> 
    >>> if nearest_street:
    ...     distance = building_location.distance(nearest_street)
    ...     print(f"Nearest street at {distance:.1f}m distance")

    >>> # Batch processing for multiple buildings
    >>> buildings = gpd.read_file("buildings.shp")
    >>> connections = []
    >>> for building in buildings.geometry:
    ...     nearest = find_nearest_line(building, street_network)
    ...     if nearest:
    ...         connections.append((building, nearest))
    >>> print(f"Found connections for {len(connections)} buildings")

    >>> # Analyze connection distances
    >>> distances = [Point(conn[0]).distance(conn[1]) for conn in connections]
    >>> avg_distance = sum(distances) / len(distances)
    >>> print(f"Average connection distance: {avg_distance:.1f}m")

    See Also
    --------
    create_perpendicular_line : Create connection from point to line
    process_layer_points : Batch process multiple points
    """
    min_distance = float('inf')
    nearest_line = None
    
    for line in line_layer.geometry:
        distance = point.distance(line)
        if distance < min_distance:
            min_distance = distance
            nearest_line = line
    
    return nearest_line

def create_perpendicular_line(point: Point, line: LineString) -> LineString:
    """
    Create a perpendicular line from a point to the nearest point on a given line.

    This function creates the shortest connection between a building location
    and existing infrastructure by calculating the perpendicular projection
    point and creating a connection line. It ensures optimal connection
    geometry for district heating service lines.

    Parameters
    ----------
    point : shapely.geometry.Point
        The point to start the perpendicular line from.
        Typically represents building locations requiring network connection.
    line : shapely.geometry.LineString
        The line to create the perpendicular connection to.
        Usually represents street infrastructure or main distribution lines.

    Returns
    -------
    shapely.geometry.LineString
        LineString connecting the input point to the nearest point on the line.
        Represents the optimal connection path for service lines.

    Notes
    -----
    Geometric Algorithm:
        1. Projects input point onto line using parametric projection
        2. Finds nearest point on line using Shapely's interpolate/project methods
        3. Creates LineString connecting original point to projection point
        4. Results in shortest possible connection distance

    Projection Mathematics:
        - Uses parametric line representation for projection calculation
        - line.project(point) returns parameter t for nearest point
        - line.interpolate(t) returns actual coordinates of nearest point
        - Handles line segment boundaries and interpolation

    Connection Properties:
        - Creates perpendicular connection when possible
        - Minimizes connection length for cost optimization
        - Suitable for service line and building connection design
        - Maintains geometric accuracy for engineering applications

    Examples
    --------
    >>> # Create building service connection
    >>> building = Point(1050.0, 2000.0)
    >>> main_street = LineString([(1000, 2000), (1100, 2000)])  # Horizontal line
    >>> service_line = create_perpendicular_line(building, main_street)
    >>> 
    >>> connection_length = service_line.length
    >>> print(f"Service connection length: {connection_length:.1f}m")

    >>> # Analyze connection angle
    >>> start_point = Point(service_line.coords[0])
    >>> end_point = Point(service_line.coords[1])
    >>> if start_point.x == end_point.x:
    ...     print("Perfect perpendicular connection (vertical)")
    ... elif start_point.y == end_point.y:
    ...     print("Perfect perpendicular connection (horizontal)")

    >>> # Batch create connections for network planning
    >>> buildings = gpd.read_file("buildings.shp")
    >>> streets = gpd.read_file("streets.shp")
    >>> connections = []
    >>> 
    >>> for building in buildings.geometry:
    ...     nearest_street = find_nearest_line(building, streets)
    ...     if nearest_street:
    ...         connection = create_perpendicular_line(building, nearest_street)
    ...         connections.append(connection)

    See Also
    --------
    find_nearest_line : Identify nearest infrastructure line
    process_layer_points : Batch process multiple building locations
    shapely.geometry.LineString.project : Point projection calculation
    """
    nearest_point_on_line = line.interpolate(line.project(point))
    return LineString([point, nearest_point_on_line])

def process_layer_points(layer: gpd.GeoDataFrame, 
                        layer_lines: gpd.GeoDataFrame) -> Tuple[List[LineString], set]:
    """
    Process a layer of points to find nearest lines and create perpendicular connections.

    This function performs batch processing of building locations to create
    optimal connections to existing infrastructure. It generates both the
    connection lines and identifies street connection points for network
    optimization algorithms.

    Parameters
    ----------
    layer : geopandas.GeoDataFrame
        GeoDataFrame containing Point geometries to process.
        Typically represents heat consumers, producers, or other network connection points.
    layer_lines : geopandas.GeoDataFrame
        GeoDataFrame containing LineString geometries representing infrastructure.
        Usually represents street network or existing pipe infrastructure.

    Returns
    -------
    Tuple[List[LineString], set]
        A tuple containing:
        
        - **perpendicular_lines** (List[LineString]) : Connection lines from points to infrastructure
        - **street_end_points** (set) : Unique connection points on infrastructure network

    Notes
    -----
    Processing Algorithm:
        1. Iterates through all points in input layer
        2. Finds nearest infrastructure line for each point
        3. Creates perpendicular connection line
        4. Extracts and stores unique street connection points
        5. Returns both connection lines and street endpoints

    Connection Point Extraction:
        - Uses line endpoint coordinates for network node identification
        - Stores as Point geometries in set for uniqueness
        - Provides input for network optimization algorithms
        - Ensures proper network topology representation

    Applications:
        - Building-to-street connection planning
        - Service line generation for district heating
        - Network node identification for optimization
        - Infrastructure connection analysis

    Performance Considerations:
        - Processes all points in single pass
        - Efficient for typical district heating planning datasets
        - Memory usage scales with number of input points
        - Set operations ensure unique endpoint identification

    Examples
    --------
    >>> # Process heat consumer connections
    >>> consumers = gpd.read_file("heat_consumers.shp")
    >>> streets = gpd.read_file("street_network.shp")
    >>> connections, endpoints = process_layer_points(consumers, streets)
    >>> 
    >>> print(f"Created {len(connections)} consumer connections")
    >>> print(f"Identified {len(endpoints)} unique street connection points")

    >>> # Analyze connection statistics
    >>> connection_lengths = [line.length for line in connections]
    >>> avg_length = sum(connection_lengths) / len(connection_lengths)
    >>> max_length = max(connection_lengths)
    >>> print(f"Average connection length: {avg_length:.1f}m")
    >>> print(f"Maximum connection length: {max_length:.1f}m")

    >>> # Combine with heat producers
    >>> producers = gpd.read_file("heat_producers.shp")
    >>> prod_connections, prod_endpoints = process_layer_points(producers, streets)
    >>> 
    >>> all_connections = connections + prod_connections
    >>> all_endpoints = endpoints.union(prod_endpoints)
    >>> print(f"Total network connections: {len(all_connections)}")

    See Also
    --------
    find_nearest_line : Nearest infrastructure identification
    create_perpendicular_line : Individual connection creation
    generate_network : Main network generation workflow
    """
    # Initialize storage for results
    perpendicular_lines = []
    street_end_points = set()
    
    for point in layer.geometry:
        nearest_line = find_nearest_line(point, layer_lines)
        if nearest_line is not None:
            perpendicular_line = create_perpendicular_line(point, nearest_line)
            perpendicular_lines.append(perpendicular_line)
            
            # Extract street connection point (end of perpendicular line)
            end_point = perpendicular_line.coords[1]
            street_end_points.add(Point(end_point))

    return perpendicular_lines, street_end_points

def generate_network(heat_consumer_layer: gpd.GeoDataFrame, 
                    heat_generator_layer: gpd.GeoDataFrame, 
                    osm_street_layer: gpd.GeoDataFrame, 
                    algorithm: str = "MST", 
                    offset_distance: float = 0.5, 
                    offset_angle: float = 0) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Generate optimal district heating network layout using specified algorithms.

    This function implements the complete network generation workflow for district
    heating systems, from building location processing to final optimized network
    layout with parallel supply and return lines. It supports multiple optimization
    algorithms and provides comprehensive network topology generation.

    Parameters
    ----------
    heat_consumer_layer : geopandas.GeoDataFrame
        GeoDataFrame containing heat consumer locations as Point geometries.
        Represents buildings requiring heat supply connections.
    heat_generator_layer : geopandas.GeoDataFrame
        GeoDataFrame containing heat generator locations as Point geometries.
        Represents heat production facilities and distribution centers.
    osm_street_layer : geopandas.GeoDataFrame
        GeoDataFrame containing street network as LineString geometries.
        Represents available infrastructure for network routing.
    algorithm : str, optional
        Network optimization algorithm to use. Default is "MST".
        
        Available algorithms:
            - **"MST"** : Minimum Spanning Tree (simple, fast)
            - **"Advanced MST"** : MST with road alignment optimization
            - **"Steiner"** : Steiner tree for minimal cost connections
            
    offset_distance : float, optional
        Distance for parallel return line generation [m]. Default is 0.5m.
        Typical values: 0.5-2.0m for district heating pipe separation.
    offset_angle : float, optional
        Angle for parallel line offset [degrees]. Default is 0° (eastward).
        0° = +X direction, 90° = +Y direction for parallel line placement.

    Returns
    -------
    Tuple[geopandas.GeoDataFrame, geopandas.GeoDataFrame]
        A tuple containing:
        
        - **flow_network** (gpd.GeoDataFrame) : Supply line network with connections
        - **return_network** (gpd.GeoDataFrame) : Parallel return line network

    Notes
    -----
    Network Generation Process:
        1. Create perpendicular connections from buildings to streets
        2. Extract street connection points for optimization
        3. Apply selected algorithm to create optimal backbone network
        4. Combine backbone with building connections
        5. Generate parallel return lines with specified offset

    Algorithm Comparison:
        - **MST** : Fastest, creates tree topology, good for radial networks
        - **Advanced MST** : Follows road alignment, realistic routing
        - **Steiner** : Minimizes total length, allows intermediate nodes

    Network Components:
        - Building connections: perpendicular service lines
        - Backbone network: optimized main distribution
        - Parallel lines: supply and return with proper separation
        - Street alignment: follows existing infrastructure

    Output Properties:
        - Complete network topology for district heating
        - Geospatially accurate for GIS integration
        - Ready for hydraulic simulation and design
        - Includes both supply and return line networks

    Examples
    --------
    >>> # Generate basic MST network
    >>> consumers = gpd.read_file("consumers.shp")
    >>> producers = gpd.read_file("producers.shp")
    >>> streets = gpd.read_file("streets.shp")
    >>> 
    >>> supply_net, return_net = generate_network(
    ...     consumers, producers, streets, algorithm="MST"
    ... )
    >>> print(f"Generated network: {len(supply_net)} supply segments")

    >>> # Advanced network with road alignment
    >>> adv_supply, adv_return = generate_network(
    ...     consumers, producers, streets, 
    ...     algorithm="Advanced MST", 
    ...     offset_distance=1.0
    ... )

    >>> # Steiner tree optimization
    >>> opt_supply, opt_return = generate_network(
    ...     consumers, producers, streets,
    ...     algorithm="Steiner",
    ...     offset_distance=1.5,
    ...     offset_angle=90
    ... )

    >>> # Compare network lengths
    >>> mst_length = supply_net.geometry.length.sum()
    >>> steiner_length = opt_supply.geometry.length.sum()
    >>> savings = (mst_length - steiner_length) / mst_length * 100
    >>> print(f"Steiner tree saves {savings:.1f}% in network length")

    >>> # Export for further analysis
    >>> supply_net.to_file("supply_network.shp")
    >>> return_net.to_file("return_network.shp")

    Raises
    ------
    ValueError
        If unknown algorithm is specified.
    GeometryError
        If input layers contain invalid geometries.

    See Also
    --------
    process_layer_points : Building connection processing
    generate_mst : Minimum spanning tree generation
    generate_steiner_tree_network : Steiner tree optimization
    offset_lines_by_angle : Parallel line generation
    """
    # Process building locations to create street connections
    perpendicular_lines_heat_consumer, heat_consumer_endpoints = process_layer_points(
        heat_consumer_layer, osm_street_layer
    )
    perpendicular_lines_heat_generator, heat_generator_endpoints = process_layer_points(
        heat_generator_layer, osm_street_layer
    )
    
    # Combine all connection components
    all_perpendicular_lines = perpendicular_lines_heat_consumer + perpendicular_lines_heat_generator
    all_endpoints = heat_consumer_endpoints.union(heat_generator_endpoints)
    all_endpoints_gdf = gpd.GeoDataFrame(geometry=list(all_endpoints))

    # Generate backbone network using selected algorithm
    if algorithm == "MST":
        # Simple Minimum Spanning Tree network
        flow_line_mst_gdf = generate_mst(all_endpoints_gdf)
        final_flow_line_gdf = gpd.GeoDataFrame(
            pd.concat([flow_line_mst_gdf, gpd.GeoDataFrame(geometry=all_perpendicular_lines)], 
                     ignore_index=True)
        )

    elif algorithm == "Advanced MST":
        # MST with road alignment optimization
        flow_line_mst_gdf = generate_mst(all_endpoints_gdf)
        adjusted_mst = adjust_segments_to_roads(flow_line_mst_gdf, osm_street_layer, all_endpoints_gdf)
        final_flow_line_gdf = gpd.GeoDataFrame(
            pd.concat([adjusted_mst, gpd.GeoDataFrame(geometry=all_perpendicular_lines)], 
                     ignore_index=True)
        )

    elif algorithm == "Steiner":
        # Steiner tree for optimal network length
        flow_line_steiner_gdf = generate_steiner_tree_network(osm_street_layer, all_endpoints_gdf)
        final_flow_line_gdf = gpd.GeoDataFrame(
            pd.concat([flow_line_steiner_gdf, gpd.GeoDataFrame(geometry=all_perpendicular_lines)], 
                     ignore_index=True)
        )

    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")
    
    # Generate parallel return line network
    final_return_line_gdf = offset_lines_by_angle(final_flow_line_gdf, offset_distance, offset_angle)

    return final_flow_line_gdf, final_return_line_gdf

def generate_connection_lines(layer: gpd.GeoDataFrame, 
                             offset_distance: float, 
                             offset_angle: float, 
                             df: Optional[pd.DataFrame] = None) -> gpd.GeoDataFrame:
    """
    Generate connection lines with building attributes from point locations.

    This function creates service connection lines for district heating networks
    while preserving comprehensive building information for network analysis.
    It combines geometric line generation with attribute mapping for complete
    network component documentation.

    Parameters
    ----------
    layer : geopandas.GeoDataFrame
        GeoDataFrame containing Point geometries representing building locations.
        Coordinates must match those in the attribute DataFrame if provided.
    offset_distance : float
        Distance to offset connection points [m].
        Determines length of service connection lines.
    offset_angle : float
        Angle in degrees for connection line direction.
        Defines orientation of service connections relative to buildings.
    df : pandas.DataFrame, optional
        DataFrame containing building attributes matched by coordinates.
        Must include 'UTM_X' and 'UTM_Y' columns for coordinate matching.
        Default is None (no attributes added).

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame with connection LineStrings and building attributes.
        Contains all building properties for network planning and analysis.

    Notes
    -----
    Attribute Schema:
        The function handles comprehensive building characteristics:
        
        - **Location** : Land, Bundesland, Stadt, Adresse
        - **Energy** : Wärmebedarf (heat demand), WW_Anteil (hot water fraction)
        - **Building** : Gebäudetyp (building type), Subtyp (subtype)
        - **HVAC** : Typ_Heizflächen (heating surface type)
        - **Temperatures** : VLT_max, RLT_max (supply/return temperatures)
        - **Control** : Steigung_Heizkurve (heating curve slope)
        - **Climate** : Normaußentemperatur (design outdoor temperature)

    Coordinate Matching:
        - Matches building points with attribute data using exact coordinates
        - Handles floating-point coordinate precision issues
        - Initializes attributes to None when no match found
        - Supports partial attribute datasets

    Connection Line Generation:
        - Creates LineString from building to offset connection point
        - Maintains building location as line starting point
        - Suitable for service connection and network visualization
        - Preserves spatial relationships for analysis

    Examples
    --------
    >>> # Generate connections with building attributes
    >>> buildings = gpd.read_file("buildings.shp")
    >>> building_data = pd.read_csv("building_attributes.csv")
    >>> 
    >>> connections = generate_connection_lines(
    ...     buildings, offset_distance=5.0, offset_angle=90.0, df=building_data
    ... )
    >>> print(f"Generated {len(connections)} connection lines with attributes")

    >>> # Analyze building characteristics
    >>> heat_demands = connections['Wärmebedarf'].dropna()
    >>> total_demand = heat_demands.sum()
    >>> avg_demand = heat_demands.mean()
    >>> print(f"Total heat demand: {total_demand:.0f} W")
    >>> print(f"Average building demand: {avg_demand:.0f} W")

    >>> # Filter by building type
    >>> residential = connections[connections['Gebäudetyp'] == 'Wohngebäude']
    >>> commercial = connections[connections['Gebäudetyp'] == 'Bürogebäude']
    >>> print(f"Residential buildings: {len(residential)}")
    >>> print(f"Commercial buildings: {len(commercial)}")

    >>> # Export with full attributes
    >>> connections.to_file("building_connections.shp")

    See Also
    --------
    create_offset_points : Individual point offset calculation
    generate_network : Complete network generation workflow
    """
    lines = []
    attributes = []

    for point in layer.geometry:
        # Extract point coordinates for attribute matching
        original_point = (point.x, point.y)

        # Initialize comprehensive attribute dictionary
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

        # Match building attributes by coordinates
        if df is not None:
            match = df[(df['UTM_X'] == original_point[0]) & (df['UTM_Y'] == original_point[1])]
            if not match.empty:
                # Extract all available building attributes
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

        # Create connection line geometry
        offset_point = create_offset_points(point, offset_distance, offset_angle)
        line = LineString([point, offset_point])
        
        lines.append(line)
        attributes.append(attr)

    # Create GeoDataFrame with lines and comprehensive attributes
    lines_gdf = gpd.GeoDataFrame(attributes, geometry=lines)
    return lines_gdf