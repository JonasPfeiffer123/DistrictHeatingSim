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

    #mode = "MST"
    mode = "A*STAR"
    if mode == "MST":
        # Creating the MST network from the endpoints
        mst_gdf = generate_mst(all_end_points_gdf)
        # Adding the vertical lines to the MST GeoDataFrame
        final_gdf = gpd.GeoDataFrame(pd.concat([mst_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))

    if mode == "A*STAR":
        road_graph = create_road_graph(layer_lines)  # Wird einmal erstellt und kann wiederverwendet werden
        a_star_gdf = generate_a_star_network(road_graph, all_end_points_gdf)
        final_gdf = gpd.GeoDataFrame(pd.concat([a_star_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))
        check_connectivity(final_gdf)
        final_gdf = connect_components(final_gdf, all_end_points_gdf)
        check_connectivity(final_gdf)

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

    #mode = "MST"
    mode = "A*STAR"
    if mode == "MST":
        # Creating the MST network from the endpoints
        mst_gdf = generate_mst(all_end_points_gdf)
        # Adding the vertical lines to the MST GeoDataFrame
        final_gdf = gpd.GeoDataFrame(pd.concat([mst_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))

    if mode == "A*STAR":
        road_graph = create_road_graph(layer_lines)  # Wird einmal erstellt und kann wiederverwendet werden
        a_star_gdf = generate_a_star_network(road_graph, all_end_points_gdf)
        final_gdf = gpd.GeoDataFrame(pd.concat([a_star_gdf, gpd.GeoDataFrame(geometry=perpendicular_lines)], ignore_index=True))
        check_connectivity(final_gdf)
        final_gdf = connect_components(final_gdf, all_end_points_gdf)
        check_connectivity(final_gdf)

    return final_gdf

def find_nearest_node(graph, point, threshold=200):
    nearest_nodes = []
    node_distances = []
    for node in graph.nodes:
        node_point = Point(node)
        distance = point.distance(node_point)
        if distance <= threshold:
            nearest_nodes.append(node)
            node_distances.append(distance)
    if not nearest_nodes:
        print(f"Kein naher Knoten für Punkt {point} innerhalb des Thresholds gefunden. Überprüfe die Daten oder erhöhe den Threshold.")
        return None  # Rückgabe von None, um weitere Fehler zu vermeiden
    # Wähle den Knoten mit der geringsten Distanz
    min_distance_idx = node_distances.index(min(node_distances))
    return nearest_nodes[min_distance_idx]

def create_road_graph(road_layer):
    G = nx.Graph()
    for idx, row in road_layer.iterrows():
        line = row.geometry
        nodes = list(line.coords)
        for start, end in zip(nodes[:-1], nodes[1:]):
            G.add_edge(start, end, weight=LineString([start, end]).length)
            if start not in G:
                G.add_node(start)
            if end not in G:
                G.add_node(end)
    return G

def generate_a_star_network(G, points_gdf):
    print(G)
    print(points_gdf)
    path_lines = []
    for i, point1 in points_gdf.iterrows():
        start = find_nearest_node(G, Point(point1.geometry.coords[0]))
        if start is None:
            print(f"Kein Knoten gefunden an Punkt {i}")
            continue  # Kein Startknoten gefunden, überspringe diesen Punkt
        for j, point2 in points_gdf.iterrows():
            if i != j:
                goal = find_nearest_node(G, Point(point2.geometry.coords[0]))
                if goal is None or start == goal:
                    continue  # Kein Zielknoten gefunden oder Start und Ziel sind identisch
                try:
                    path = nx.astar_path(G, start, goal, heuristic=euclidean_distance)
                    if len(path) > 1:
                        path_line = LineString(path)
                        path_lines.append(path_line)
                    else:
                        print(f"Pfad zwischen Punkt {i} und Punkt {j} ist zu kurz für eine LineString.")
                except (nx.NetworkXNoPath, ValueError) as e:
                    print(f"Kein Pfad gefunden oder Fehler aufgetreten zwischen Punkt {i} und Punkt {j}: {e}")
    return gpd.GeoDataFrame(geometry=path_lines)

def euclidean_distance(a, b):
    return Point(a).distance(Point(b))

def check_connectivity(gdf):
    G = nx.Graph()
    for line in gdf.geometry:
        nodes = list(line.coords)
        for start, end in zip(nodes[:-1], nodes[1:]):
            G.add_edge(start, end)

    # Prüfen, ob der Graph verbunden ist
    if not nx.is_connected(G):
        print("Das Netzwerk ist nicht vollständig verbunden.")
        # Hier könnten weitere Schritte folgen, um das Netzwerk zu verbinden
    else:
        print("Das Netzwerk ist vollständig verbunden.")

def connect_components(gdf, points_gdf):
    G = nx.Graph()
    # Füge alle Linien als Kanten in den Graphen ein
    for line in gdf.geometry:
        nodes = list(line.coords)
        for start, end in zip(nodes[:-1], nodes[1:]):
            G.add_edge(start, end)

    # Markiere relevante Punkte in `points_gdf`
    relevant_points = {tuple(point.coords[0]): True for point in points_gdf.geometry}

    # Identifiziere Komponenten
    components = list(nx.connected_components(G))
    if len(components) <= 1:
        print("Das Netzwerk ist bereits vollständig verbunden.")
        return gdf

    # Bestimme die größte Komponente
    largest_component = max(components, key=len)

    # Verbinde kleinere Komponenten, die relevante Punkte enthalten, mit der größten Komponente
    new_lines = []
    for component in components:
        if component != largest_component:
            # Prüfe, ob die Komponente relevante Punkte enthält
            relevant_component = any(node in relevant_points for node in component)
            if relevant_component:
                # Verbinde jeden relevanten Punkt der kleineren Komponente mit der größten Komponente
                for node in component:
                    if node in relevant_points:  # Nur relevante Punkte verbinden
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

    # Füge die neuen Linien zum GeoDataFrame hinzu
    new_lines_gdf = gpd.GeoDataFrame(geometry=new_lines)
    updated_gdf = gpd.GeoDataFrame(pd.concat([gdf, new_lines_gdf], ignore_index=True))
    return updated_gdf
