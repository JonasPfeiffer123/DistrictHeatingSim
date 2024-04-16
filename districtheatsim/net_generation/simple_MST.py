import pandas as pd
import geopandas as gpd
import math
import networkx as nx
from shapely.geometry import LineString, Point

# help function
def create_offset_points(point, distance, angle_degrees):
    angle_radians = math.radians(angle_degrees)
    dx = distance * math.cos(angle_radians)
    dy = distance * math.sin(angle_radians)
    return Point(point.x + dx, point.y + dy)

def find_nearest_line(point, line_layer):
    min_distance = float('inf')
    nearest_line = None
    for line in line_layer.geometry:
        distance = point.distance(line)
        if distance < min_distance:
            min_distance = distance
            nearest_line = line
    return nearest_line

def create_perpendicular_line(point, line):
    nearest_point_on_line = line.interpolate(line.project(point))
    return LineString([point, nearest_point_on_line])

def process_layer_points(layer, layer_lines):
    street_end_points = set()
    for point in layer.geometry:
        nearest_line = find_nearest_line(point, layer_lines)
        if nearest_line is not None:
            perpendicular_line = create_perpendicular_line(point, nearest_line)
            end_point = perpendicular_line.coords[1]  # End point of the vertical line
            street_end_points.add(Point(end_point))
    return street_end_points

def generate_return_lines(layer, distance, angle_degrees, layer_lines):
    street_end_points = set()
    for point in layer.geometry:
        offset_point = create_offset_points(point, distance, angle_degrees)
        nearest_line = find_nearest_line(offset_point, layer_lines)
        if nearest_line is not None:
            street_end_point = create_perpendicular_line(offset_point, nearest_line).coords[1]
            street_end_points.add(Point(street_end_point))
    return street_end_points

# MST network generation
def generate_mst(points):
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

def generate_network_fl(layer_points_fl, layer_wea, layer_lines):
    perpendicular_lines = []
    
    # Creating the offset points and vertical lines for the flow lines from layer_points_fl
    points_end_points = process_layer_points(layer_points_fl, layer_lines)
    for point in layer_points_fl.geometry:
        nearest_line = find_nearest_line(point, layer_lines)
        if nearest_line is not None:
            perpendicular_line = create_perpendicular_line(point, nearest_line)
            perpendicular_lines.append(perpendicular_line)

    # Creating the offset points and vertical lines for the flow lines from layer_wea
    wea_end_points = process_layer_points(layer_wea, layer_lines)
    for point in layer_wea.geometry:
        nearest_line = find_nearest_line(point, layer_lines)
        if nearest_line is not None:
            perpendicular_line = create_perpendicular_line(point, nearest_line)
            perpendicular_lines.append(perpendicular_line)

    # Combining the endpoints and converting them into a GeoDataFrame
    all_end_points = points_end_points.union(wea_end_points)
    all_end_points_gdf = gpd.GeoDataFrame(geometry=list(all_end_points))

    # Creating the MST network from the endpoints
    mst_gdf = generate_mst(all_end_points_gdf)

    # Adding the vertical lines to the MST GeoDataFrame
    final_gdf = gpd.GeoDataFrame(pd.concat([mst_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))
    return final_gdf


def generate_network_rl(layer_points_rl, layer_wea, fixed_distance_rl, fixed_angle_rl, layer_lines):
    perpendicular_lines = []
    
    # Creating the offset points and vertical lines for the return lines from layer_points_rl
    points_end_points = generate_return_lines(layer_points_rl, fixed_distance_rl, fixed_angle_rl, layer_lines)
    for point in layer_points_rl.geometry:
        offset_point = create_offset_points(point, fixed_distance_rl, fixed_angle_rl)
        nearest_line = find_nearest_line(offset_point, layer_lines)
        if nearest_line is not None:
            perpendicular_line = create_perpendicular_line(offset_point, nearest_line)
            perpendicular_lines.append(perpendicular_line)

    # Creating the offset points and vertical lines for the return lines from layer_wea
    wea_end_points = generate_return_lines(layer_wea, fixed_distance_rl, fixed_angle_rl, layer_lines)
    for point in layer_wea.geometry:
        offset_point = create_offset_points(point, fixed_distance_rl, fixed_angle_rl)
        nearest_line = find_nearest_line(offset_point, layer_lines)
        if nearest_line is not None:
            perpendicular_line = create_perpendicular_line(offset_point, nearest_line)
            perpendicular_lines.append(perpendicular_line)

    # Combining the endpoints and converting them into a GeoDataFrame
    all_end_points = points_end_points.union(wea_end_points)
    all_end_points_gdf = gpd.GeoDataFrame(geometry=list(all_end_points))

    # Creating the MST network from the endpoints
    mst_gdf = generate_mst(all_end_points_gdf)

    # Adding the vertical lines to the MST GeoDataFrame
    final_gdf = gpd.GeoDataFrame(pd.concat([mst_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))
    return final_gdf

