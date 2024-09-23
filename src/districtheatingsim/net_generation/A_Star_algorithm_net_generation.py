"""
Filename: A_Star_algorithm_net_generation.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
Description: Contains functions for generating an A-Star based network

Additional Information: Currently not working.
"""

import pandas as pd
import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, Point
from scipy.spatial import KDTree
import numpy as np
import time

def euclidean_distance(a, b):
    """
    Calculates the Euclidean distance between two points.

    Args:
        a (tuple): Coordinates of the first point.
        b (tuple): Coordinates of the second point.

    Returns:
        float: Euclidean distance between the points.
    """
    return Point(a).distance(Point(b))

def connect_components(gdf, points_gdf):
    """
    Connects disjoint components in the graph represented by the GeoDataFrame.

    Args:
        gdf (geopandas.GeoDataFrame): GeoDataFrame containing line geometries.
        points_gdf (geopandas.GeoDataFrame): GeoDataFrame containing point geometries.

    Returns:
        geopandas.GeoDataFrame: Updated GeoDataFrame with connected components.
    """
    G = nx.Graph()
    # Add all lines as edges in the graph
    for line in gdf.geometry:
        nodes = list(line.coords)
        for start, end in zip(nodes[:-1], nodes[1:]):
            G.add_edge(start, end)

    # Mark relevant points in `points_gdf`
    relevant_points = {tuple(point.coords[0]): True for point in points_gdf.geometry}

    # Identify components
    components = list(nx.connected_components(G))
    if len(components) <= 1:
        print("The network is already fully connected.")
        return gdf

    # Determine the largest component
    largest_component = max(components, key=len)

    # Connect smaller components containing relevant points to the largest component
    new_lines = []
    for component in components:
        if component != largest_component:
            # Check if the component contains relevant points
            relevant_component = any(node in relevant_points for node in component)
            if relevant_component:
                # Connect each relevant point of the smaller component to the largest component
                for node in component:
                    if node in relevant_points:  # Only connect relevant points
                        closest_node = None
                        min_distance = float('inf')
                        node_point = Point(node)
                        for target_node in largest_component:
                            target_point = Point(target_node)
                            distance = node_point.distance(target_point)
                            if distance < min_distance:
                                min_distance = distance
                                closest_node = target_node
                        if closest_node:
                            new_line = LineString([node, closest_node])
                            new_lines.append(new_line)

    # Add the new lines to the GeoDataFrame
    new_lines_gdf = gpd.GeoDataFrame(geometry=new_lines)
    updated_gdf = gpd.GeoDataFrame(pd.concat([gdf, new_lines_gdf], ignore_index=True))
    return updated_gdf

### New Implementation ###
def create_kd_tree(G):
    """
    Creates a KDTree from the nodes of the graph.

    Args:
        G (networkx.Graph): The input graph.

    Returns:
        tuple: KDTree of node coordinates and list of nodes.
    """
    coords = [(G.nodes[node]['pos'].x, G.nodes[node]['pos'].y) for node in G]
    kd_tree = KDTree(coords)
    return kd_tree, list(G.nodes)

def create_road_graph(road_layer):
    """
    Creates a graph from the road layer.

    Args:
        road_layer (geopandas.GeoDataFrame): GeoDataFrame containing the road layer.

    Returns:
        networkx.Graph: Graph representation of the road layer.
    """
    G = nx.Graph()
    for idx, row in road_layer.iterrows():
        line = row.geometry
        nodes = list(line.coords)
        for start, end in zip(nodes[:-1], nodes[1:]):
            # Ensure nodes have 'pos' attribute when created
            if start not in G:
                G.add_node(start, pos=Point(start))  # Add 'pos' attribute to the node
            if end not in G:
                G.add_node(end, pos=Point(end))  # Add 'pos' attribute to the node
            G.add_edge(start, end, weight=LineString([start, end]).length)
    return G

def find_nearest_node_kdtree(kd_tree, nodes, point):
    """
    Finds the nearest node in the graph to the given point using KDTree.

    Args:
        kd_tree (scipy.spatial.KDTree): KDTree of node coordinates.
        nodes (list): List of nodes in the graph.
        point (shapely.geometry.Point): The point to find the nearest node to.

    Returns:
        tuple: Coordinates of the nearest node.
    """
    point_np = np.array([point.x, point.y])
    dist, idx = kd_tree.query([point_np], k=1)
    nearest_node = nodes[idx[0]]
    return nearest_node

def a_star_with_timeout(G, start, goal, timeout=10):
    """
    Executes the A* search algorithm with a timeout.

    Args:
        G (networkx.Graph): The input graph.
        start (tuple): Coordinates of the start node.
        goal (tuple): Coordinates of the goal node.
        timeout (int, optional): Timeout in seconds. Defaults to 10.

    Returns:
        list: Path found by the A* algorithm, or None if no path found or timeout occurred.
    """
    start_time = time.time()
    try:
        path = nx.astar_path(G, start, goal, heuristic=euclidean_distance)
    except nx.NetworkXNoPath:
        return None
    if time.time() - start_time > timeout:
        print("A* search timed out")
        return None
    return path

def generate_a_star_network(G, points_gdf):
    """
    Generates a network using the A* algorithm.

    Args:
        G (networkx.Graph): The input graph.
        points_gdf (geopandas.GeoDataFrame): GeoDataFrame containing the points to connect.

    Returns:
        geopandas.GeoDataFrame: GeoDataFrame with the generated network lines.
    """
    kd_tree, nodes = create_kd_tree(G)
    path_lines = []
    for i, point1 in points_gdf.iterrows():
        start = find_nearest_node_kdtree(kd_tree, nodes, Point(point1.geometry.coords[0]))
        for j, point2 in points_gdf.iterrows():
            if i != j:
                goal = find_nearest_node_kdtree(kd_tree, nodes, Point(point2.geometry.coords[0]))
                path = a_star_with_timeout(G, start, goal)
                if path and len(path) > 1:
                    path_line = LineString(path)
                    path_lines.append(path_line)
    return gpd.GeoDataFrame(geometry=path_lines)

def remove_unnecessary_nodes(gdf, points_fl, points_wea):
    """
    Removes unnecessary nodes from the network.

    Args:
        gdf (geopandas.GeoDataFrame): GeoDataFrame containing the network lines.
        points_fl (geopandas.GeoDataFrame): GeoDataFrame containing the flow points.
        points_wea (geopandas.GeoDataFrame): GeoDataFrame containing the weather points.

    Returns:
        geopandas.GeoDataFrame: GeoDataFrame with the simplified network.
    """
    G = nx.Graph()
    # Create the graph from the GeoDataFrame lines
    for line in gdf.geometry:
        if isinstance(line, LineString):
            start, end = list(line.coords)[0], list(line.coords)[-1]
            G.add_edge(start, end)

    # Identify all degree-one nodes
    to_remove = [node for node, degree in G.degree() if degree == 1]

    # Create a set of point coordinates that should not be removed
    protected_points = set()
    for point in points_fl.geometry:
        protected_points.add(tuple(point.coords[0]))
    for point in points_wea.geometry:
        protected_points.add(tuple(point.coords[0]))

    # Check if these nodes lie on the graph and remove them if they are not protected
    new_lines = []
    for line in gdf.geometry:
        start, end = tuple(list(line.coords)[0]), tuple(list(line.coords)[-1])
        if (start in to_remove and start not in protected_points) or (end in to_remove and end not in protected_points):
            continue  # Ignore the line if the start or end node should be removed and is not protected
        new_lines.append(line)  # Keep the line in the graph

    # Create a new GeoDataFrame with the remaining lines
    return gpd.GeoDataFrame(geometry=new_lines)

def are_collinear(p1, p2, p3, tolerance=np.pi/180 * 10):  # Tolerance of 10 degrees
    """
    Checks if three points are collinear within a specified tolerance.

    Args:
        p1 (tuple): Coordinates of the first point.
        p2 (tuple): Coordinates of the second point.
        p3 (tuple): Coordinates of the third point.
        tolerance (float, optional): Tolerance in radians. Defaults to np.pi/180*10.

    Returns:
        bool: True if the points are collinear within the tolerance, False otherwise.
    """
    # Calculate the angles between the points
    angle1 = np.arctan2(p2[1] - p1[1], p2[0] - p1[0])
    angle2 = np.arctan2(p3[1] - p2[1], p3[0] - p2[0])
    # Check if the angles are within the tolerance
    return abs(angle1 - angle2) < tolerance

def simplify_network(gdf):
    """
    Simplifies the network by combining collinear segments.

    Args:
        gdf (geopandas.GeoDataFrame): GeoDataFrame containing the network lines.

    Returns:
        geopandas.GeoDataFrame: GeoDataFrame with the simplified network.
    """
    G = nx.Graph()
    # Add lines as edges in the graph, nodes are endpoints
    for line in gdf.geometry:
        if isinstance(line, LineString):
            start, end = tuple(line.coords[0]), tuple(line.coords[-1])
            G.add_edge(start, end, object=line)

    # Try to combine collinear segments
    to_remove = []
    to_add = []
    for node in G.nodes:
        neighbors = list(G.neighbors(node))
        if len(neighbors) == 2:
            # Check if the segments with this node as an intermediate point are collinear
            if are_collinear(neighbors[0], node, neighbors[1]):
                # Create a new line combining the two segments
                new_line = LineString([neighbors[0], node, neighbors[1]])
                to_add.append((neighbors[0], neighbors[1], new_line))
                to_remove.extend([(neighbors[0], node), (node, neighbors[1])])

    # Update the graph
    for start, end in to_remove:
        G.remove_edge(start, end)
    for start, end, line in to_add:
        G.add_edge(start, end, object=line)

    # Create a new GeoDataFrame from the combined lines
    new_lines = [data['object'] for u, v, data in G.edges(data=True)]
    return gpd.GeoDataFrame(geometry=new_lines)