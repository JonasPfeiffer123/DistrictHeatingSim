"""
Filename: steiner_tree.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-26
Description: Generates a Steiner tree for the given points and street layer.
"""

import networkx as nx
from networkx.algorithms.approximation import steiner_tree
import geopandas as gpd
from shapely.geometry import LineString, Point
import matplotlib.pyplot as plt
from shapely.ops import nearest_points
import random

def create_road_graph(street_layer, precision=4):
    """
    Erstellt einen NetworkX-Graphen aus dem Straßennetz.
    """
    G = nx.Graph()
    for line in street_layer.geometry:
        if isinstance(line, LineString):
            coords = [ (round(x, precision), round(y, precision)) for x, y in line.coords ]
            for i in range(len(coords) - 1):
                p1 = coords[i]
                p2 = coords[i + 1]
                G.add_edge(p1, p2, weight=Point(p1).distance(Point(p2)))
    
    # Plotten des Graphen (optional)
    #nx.draw(G, pos={n: n for n in G.nodes()}, with_labels=False, node_size=50, node_color='blue', edge_color='gray')
    #plt.show()

    return G

def map_points_to_graph_nodes(road_graph, points_gdf, precision=4):
    """
    Mappt die Punkte auf die nächsten Kanten im Straßengraphen.
    Fügt den projizierten Punkt als Knoten ein und ersetzt die Kante durch zwei neue Kanten.
    Achtung: Fügt Kanten nur ein, wenn Start- und Endpunkt verschieden sind.
    """
    terminals = []
    for point in points_gdf.geometry:
        min_dist = float('inf')
        nearest_edge = None
        nearest_proj = None
        for u, v in road_graph.edges():
            line = LineString([u, v])
            proj = line.interpolate(line.project(point))
            dist = point.distance(proj)
            if dist < min_dist:
                min_dist = dist
                nearest_edge = (u, v)
                nearest_proj = proj

        # Runde die Koordinaten, um Floating-Point-Probleme zu vermeiden
        proj_coords = (round(nearest_proj.x, precision), round(nearest_proj.y, precision))
        u_rounded = (round(nearest_edge[0][0], precision), round(nearest_edge[0][1], precision))
        v_rounded = (round(nearest_edge[1][0], precision), round(nearest_edge[1][1], precision))

        # Prüfe, ob der projizierte Punkt schon Knoten ist
        if proj_coords not in road_graph.nodes:
            # Entferne die alte Kante (achte auf Rundung!)
            if road_graph.has_edge(u_rounded, v_rounded):
                road_graph.remove_edge(u_rounded, v_rounded)
            # Füge den projizierten Punkt als Knoten ein
            road_graph.add_node(proj_coords)
            # Füge zwei neue Kanten ein, aber nur wenn die Punkte verschieden sind
            if u_rounded != proj_coords and not road_graph.has_edge(u_rounded, proj_coords):
                road_graph.add_edge(u_rounded, proj_coords, weight=Point(u_rounded).distance(Point(proj_coords)))
            if v_rounded != proj_coords and not road_graph.has_edge(proj_coords, v_rounded):
                road_graph.add_edge(proj_coords, v_rounded, weight=Point(v_rounded).distance(Point(proj_coords)))
        terminals.append(proj_coords)

    # Debug: Prüfe, ob alle Terminals im Graphen sind
    """
    for t in terminals:
        if t not in road_graph.nodes:
            print(f"Terminal NICHT im Graphen: {t}")
        else:
            print(f"Terminal korrekt im Graphen: {t}")

    # Prüfe, ob der Graph zusammenhängend ist und in welchen Komponenten die Terminals liegen
    if not nx.is_connected(road_graph):
        print("WARNUNG: Der Graph ist nicht zusammenhängend!")
        components = list(nx.connected_components(road_graph))
        for i, comp in enumerate(components):
            print(f"Komponente {i}: {len(comp)} Knoten")
        for t in terminals:
            for i, comp in enumerate(components):
                if t in comp:
                    print(f"Terminal {t} liegt in Komponente {i}")
    else:
        print("Graph ist zusammenhängend.")
    """

    return terminals

def filter_to_largest_component(road_graph, terminals):
    """
    Filtert den Graphen und die Terminals auf die größte zusammenhängende Komponente.
    """
    components = list(nx.connected_components(road_graph))
    largest = max(components, key=len)
    filtered_terminals = [t for t in terminals if t in largest]
    subgraph = road_graph.subgraph(largest).copy()
    if len(filtered_terminals) < len(terminals):
        print("WARNUNG: Nicht alle Terminals liegen in der größten Komponente und werden ignoriert!")
    return subgraph, filtered_terminals

def generate_steiner_tree_network(street_layer, points_gdf):
    road_graph = create_road_graph(street_layer)
    terminals = map_points_to_graph_nodes(road_graph, points_gdf)

    # Filter auf größte Komponente
    road_graph, terminals = filter_to_largest_component(road_graph, terminals)
    if len(terminals) < 2:
        raise ValueError("Zu wenige Terminals in der größten Komponente!")

    # Berechnung des Steinerbaums
    steiner_subgraph = steiner_tree(road_graph, terminals, weight='weight')

    # plotten des Steinerbaums (optional)
    fig, ax = plt.subplots(figsize=(10, 10))

    # Plot gesamtes Straßennetz (grau)
    for u, v in road_graph.edges():
        line = LineString([u, v])
        xs, ys = zip(*line.coords)
        ax.plot(xs, ys, color='lightgray', linewidth=1, zorder=1)

    # Plot Steinerbaum (rot)
    for u, v in steiner_subgraph.edges():
        line = LineString([u, v])
        xs, ys = zip(*line.coords)
        ax.plot(xs, ys, color='red', linewidth=2, zorder=2)

    # Plot Terminals (blaue Kreuze)
    for t in terminals:
        ax.plot(t[0], t[1], marker='x', color='blue', markersize=10, label='Terminal', zorder=3)

    # Umwandlung in GeoDataFrame:
    lines = [LineString([Point(u), Point(v)]) for u, v in steiner_subgraph.edges()]
    return gpd.GeoDataFrame(geometry=lines)