import pandas as pd
import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, Point
from scipy.spatial import KDTree
import numpy as np
import time

def euclidean_distance(a, b):
    return Point(a).distance(Point(b))

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

### neue Implementierung ###
# Funktion zur Erstellung des KD-Baums aus den Knoten des Graphen
def create_kd_tree(G):
    coords = [(G.nodes[node]['pos'].x, G.nodes[node]['pos'].y) for node in G]
    kd_tree = KDTree(coords)
    return kd_tree, list(G.nodes)

# Erweitere create_road_graph um Koordinaten zu speichern
def create_road_graph(road_layer):
    G = nx.Graph()
    for idx, row in road_layer.iterrows():
        line = row.geometry
        nodes = list(line.coords)
        for start, end in zip(nodes[:-1], nodes[1:]):
            # Stelle sicher, dass die Knoten beim Erstellen die 'pos' Eigenschaft erhalten
            if start not in G:
                G.add_node(start, pos=Point(start))  # Hinzufügen der 'pos' Eigenschaft beim Knoten
            if end not in G:
                G.add_node(end, pos=Point(end))  # Hinzufügen der 'pos' Eigenschaft beim Knoten
            G.add_edge(start, end, weight=LineString([start, end]).length)
    return G

def find_nearest_node_kdtree(kd_tree, nodes, point):
    point_np = np.array([point.x, point.y])
    dist, idx = kd_tree.query([point_np], k=1)
    nearest_node = nodes[idx[0]]
    return nearest_node

def a_star_with_timeout(G, start, goal, timeout=10):
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
    G = nx.Graph()
    # Erstelle den Graphen aus den GeoDataFrame Linien
    for line in gdf.geometry:
        if isinstance(line, LineString):
            start, end = list(line.coords)[0], list(line.coords)[-1]
            G.add_edge(start, end)

    # Identifiziere alle Ein-Grad-Knoten
    to_remove = [node for node, degree in G.degree() if degree == 1]

    # Erstelle einen Satz der Punktkoordinaten, die nicht entfernt werden sollen
    protected_points = set()
    for point in points_fl.geometry:
        protected_points.add(tuple(point.coords[0]))
    for point in points_wea.geometry:
        protected_points.add(tuple(point.coords[0]))

    # Überprüfe, ob diese Knoten auf dem Graphen liegen und entferne sie, wenn sie nicht geschützt sind
    new_lines = []
    for line in gdf.geometry:
        start, end = tuple(list(line.coords)[0]), tuple(list(line.coords)[-1])
        if (start in to_remove and start not in protected_points) or (end in to_remove and end not in protected_points):
            continue  # Ignoriere die Linie, wenn der Start- oder Endknoten entfernt werden soll und nicht geschützt ist
        new_lines.append(line)  # Behalte die Linie im Graphen

    # Erstelle einen neuen GeoDataFrame mit den übrig gebliebenen Linien
    return gpd.GeoDataFrame(geometry=new_lines)

def are_collinear(p1, p2, p3, tolerance=np.pi/180 * 10):  # Toleranz von 10 Grad
    # Berechne die Winkel zwischen den Punkten
    angle1 = np.arctan2(p2[1] - p1[1], p2[0] - p1[0])
    angle2 = np.arctan2(p3[1] - p2[1], p3[0] - p2[0])
    # Prüfe, ob die Winkel innerhalb der Toleranz sind
    return abs(angle1 - angle2) < tolerance

def simplify_network(gdf):
    G = nx.Graph()
    # Füge Linien als Kanten in den Graphen ein, Knoten sind Endpunkte
    for line in gdf.geometry:
        if isinstance(line, LineString):
            start, end = tuple(line.coords[0]), tuple(line.coords[-1])
            G.add_edge(start, end, object=line)

    # Versuche, kollineare Segmente zu kombinieren
    to_remove = []
    to_add = []
    for node in G.nodes:
        neighbors = list(G.neighbors(node))
        if len(neighbors) == 2:
            # Überprüfe, ob die Segmente mit diesem Knoten als Zwischenpunkt kollinear sind
            if are_collinear(neighbors[0], node, neighbors[1]):
                # Erstelle eine neue Linie, die die beiden Segmente kombiniert
                new_line = LineString([neighbors[0], node, neighbors[1]])
                to_add.append((neighbors[0], neighbors[1], new_line))
                to_remove.extend([(neighbors[0], node), (node, neighbors[1])])

    # Update den Graphen
    for start, end in to_remove:
        G.remove_edge(start, end)
    for start, end, line in to_add:
        G.add_edge(start, end, object=line)

    # Erstelle ein neues GeoDataFrame aus den kombinierten Linien
    new_lines = [data['object'] for u, v, data in G.edges(data=True)]
    return gpd.GeoDataFrame(geometry=new_lines)