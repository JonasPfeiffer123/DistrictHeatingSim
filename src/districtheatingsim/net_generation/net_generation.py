"""
Network generation for district heating using graph algorithms.

Implements MST, Advanced MST, and Steiner tree algorithms for cost-optimal
network topologies with street alignment and parallel line generation.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import pandas as pd
import geopandas as gpd
import math
from shapely.geometry import LineString, Point
from typing import Optional, Tuple, List, Dict, Any, Union

from districtheatingsim.net_generation.minimal_spanning_tree import generate_mst, adjust_segments_to_roads

def create_offset_points(point: Point, distance: float, angle_degrees: float) -> Point:
    """
    Create point offset by specified distance and angle.

    :param point: Original point
    :type point: Point
    :param distance: Offset distance [m]
    :type distance: float
    :param angle_degrees: Offset angle (0°=East, 90°=North)
    :type angle_degrees: float
    :return: Offset point
    :rtype: Point
    
    .. note::
        Uses polar transformation: dx=distance*cos(θ), dy=distance*sin(θ).
    """
    angle_radians = math.radians(angle_degrees)
    dx = distance * math.cos(angle_radians)
    dy = distance * math.sin(angle_radians)
    return Point(point.x + dx, point.y + dy)

def offset_lines_by_angle(lines_gdf: gpd.GeoDataFrame, distance: float, 
                         angle_degrees: float) -> gpd.GeoDataFrame:
    """
    Offset all LineStrings by fixed distance and angle.

    :param lines_gdf: LineStrings to offset (typically supply lines)
    :type lines_gdf: gpd.GeoDataFrame
    :param distance: Offset distance [m] (typical 0.5-2.0m)
    :type distance: float
    :param angle_degrees: Offset angle (0°=East, 90°=North)
    :type angle_degrees: float
    :return: Offset LineStrings with preserved CRS
    :rtype: gpd.GeoDataFrame
    
    .. note::
        Creates parallel return lines from supply lines. Maintains topology and connectivity.
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
    Find nearest line to a point.

    :param point: Point to find nearest line for
    :type point: Point
    :param line_layer: LineStrings to search (typically streets)
    :type line_layer: gpd.GeoDataFrame
    :return: Nearest LineString or None if no lines found
    :rtype: Optional[LineString]
    
    .. note::
        O(n) complexity. Uses Euclidean distance. Returns None on empty layer.
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
    Create perpendicular connection from point to nearest point on line.

    :param point: Point to connect (typically building)
    :type point: Point
    :param line: Line to connect to (typically street)
    :type line: LineString
    :return: Connection LineString (shortest path)
    :rtype: LineString
    
    .. note::
        Uses line.project() and line.interpolate() for optimal connection geometry.
    """
    nearest_point_on_line = line.interpolate(line.project(point))
    return LineString([point, nearest_point_on_line])

def process_layer_points(layer: gpd.GeoDataFrame, 
                        layer_lines: gpd.GeoDataFrame) -> Tuple[List[LineString], set]:
    """
    Process points to create perpendicular connections and extract street endpoints.

    :param layer: Points to process (buildings, generators)
    :type layer: gpd.GeoDataFrame
    :param layer_lines: LineStrings for connections (streets)
    :type layer_lines: gpd.GeoDataFrame
    :return: Tuple of (connection_lines, unique_street_endpoints)
    :rtype: Tuple[List[LineString], set]
    
    .. note::
        Returns street connection points as set for network optimization input.
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
    Generate optimal district heating network with supply and return lines.

    :param heat_consumer_layer: Consumer locations (buildings)
    :type heat_consumer_layer: gpd.GeoDataFrame
    :param heat_generator_layer: Generator locations (plants)
    :type heat_generator_layer: gpd.GeoDataFrame
    :param osm_street_layer: Street network for routing
    :type osm_street_layer: gpd.GeoDataFrame
    :param algorithm: MST, Advanced MST, or Steiner (default MST)
    :type algorithm: str
    :param offset_distance: Return line offset [m] (default 0.5)
    :type offset_distance: float
    :param offset_angle: Offset angle [degrees] (default 0)
    :type offset_angle: float
    :return: Tuple of (supply_network, return_network)
    :rtype: Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]
    :raises ValueError: If unknown algorithm specified
    
    .. note::
        MST=fastest tree, Advanced MST=road-aligned, Steiner=minimal length.
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
    Generate connection lines with building attributes.

    :param layer: Building Point locations
    :type layer: gpd.GeoDataFrame
    :param offset_distance: Connection line offset [m]
    :type offset_distance: float
    :param offset_angle: Connection angle [degrees]
    :type offset_angle: float
    :param df: Building attributes with UTM_X, UTM_Y columns (optional)
    :type df: Optional[pd.DataFrame]
    :return: Connection LineStrings with building attributes
    :rtype: gpd.GeoDataFrame
    
    .. note::
        Attributes: Land, Stadt, Adresse, Wärmebedarf, Gebäudetyp, VLT_max, etc.
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
                # Extract all available building attributes (check if column exists first)
                if 'Land' in match.columns:
                    attr['Land'] = match['Land'].iloc[0]
                if 'Bundesland' in match.columns:
                    attr['Bundesland'] = match['Bundesland'].iloc[0]
                if 'Stadt' in match.columns:
                    attr['Stadt'] = match['Stadt'].iloc[0]
                if 'Adresse' in match.columns:
                    attr['Adresse'] = match['Adresse'].iloc[0]
                if 'Wärmebedarf' in match.columns:
                    attr['Wärmebedarf'] = match['Wärmebedarf'].iloc[0]
                if 'Gebäudetyp' in match.columns:
                    attr['Gebäudetyp'] = match['Gebäudetyp'].iloc[0]
                if 'Subtyp' in match.columns:
                    attr['Subtyp'] = match['Subtyp'].iloc[0]
                if 'WW_Anteil' in match.columns:
                    attr['WW_Anteil'] = match['WW_Anteil'].iloc[0]
                if 'Typ_Heizflächen' in match.columns:
                    attr['Typ_Heizflächen'] = match['Typ_Heizflächen'].iloc[0]
                if 'VLT_max' in match.columns:
                    attr['VLT_max'] = match['VLT_max'].iloc[0]
                if 'Steigung_Heizkurve' in match.columns:
                    attr['Steigung_Heizkurve'] = match['Steigung_Heizkurve'].iloc[0]
                if 'RLT_max' in match.columns:
                    attr['RLT_max'] = match['RLT_max'].iloc[0]
                if 'Normaußentemperatur' in match.columns:
                    attr['Normaußentemperatur'] = match['Normaußentemperatur'].iloc[0]

        # Create connection line geometry
        offset_point = create_offset_points(point, offset_distance, offset_angle)
        line = LineString([point, offset_point])
        
        lines.append(line)
        attributes.append(attr)

    # Create GeoDataFrame with lines and comprehensive attributes
    lines_gdf = gpd.GeoDataFrame(attributes, geometry=lines)
    return lines_gdf