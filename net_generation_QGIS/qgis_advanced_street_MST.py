from qgis.core import (QgsFeature, QgsGeometry, QgsPointXY, QgsWkbTypes, QgsSpatialIndex)

import networkx as nx

from import_and_create_layers_qgis import create_offset_points

def find_nearest_line(point_geom, line_layer):
    min_distance = float('inf')
    nearest_line_feat = None

    for line_feat in line_layer.getFeatures():
        line_geom = line_feat.geometry()
        distance = point_geom.distance(line_geom)
        if distance < min_distance:
            min_distance = distance
            nearest_line_feat = line_feat
    return nearest_line_feat


def create_perpendicular_line(point_geom, line_geom, provider):
    closest_point = line_geom.closestSegmentWithContext(point_geom.asPoint())[1]
    closest_point_geom = QgsGeometry.fromPointXY(QgsPointXY(closest_point))

    perpendicular_line = point_geom.shortestLine(closest_point_geom)
    
    new_line = QgsFeature()
    new_line.setGeometry(perpendicular_line)
    provider.addFeatures([new_line])
    
    return QgsPointXY(closest_point)


def process_layer_points(layer, provider, layer_lines):
    street_end_points = set()
    for point_feat in layer.getFeatures():
        point_geom = point_feat.geometry()
        nearest_line_feat = find_nearest_line(point_geom, layer_lines)

        if nearest_line_feat:
            nearest_line_geom = nearest_line_feat.geometry()
            street_end_point = create_perpendicular_line(point_geom, nearest_line_geom, provider)
            street_end_points.add(street_end_point)
    return street_end_points


# generate the offset points and perpendicular lines for return lines
def generate_return_lines(layer, distance, angle_degrees, provider, layer_lines):
    street_end_points = set()
    for point_feat in layer.getFeatures():
        original_point = point_feat.geometry().asPoint()
        
        offset_point = create_offset_points(original_point, distance, angle_degrees)
        offset_point_geom = QgsGeometry.fromPointXY(offset_point)
        
        nearest_line_feat = find_nearest_line(offset_point_geom, layer_lines)
        
        if nearest_line_feat:
            nearest_line_geom = nearest_line_feat.geometry()
            street_end_point = create_perpendicular_line(offset_point_geom, nearest_line_geom, provider)
            street_end_points.add(street_end_point)
    return street_end_points

######## net creation ##############
def create_network_graph(street_layer):
    G = nx.Graph()
    for feat in street_layer.getFeatures():
        geom = feat.geometry()
        if geom.type() == QgsWkbTypes.LineGeometry:
            # Annahme: Ihre Straßengeometrien sind als Polylinien
            points = geom.asPolyline()
            for i in range(len(points) - 1):
                p1 = points[i]
                p2 = points[i + 1]
                weight = QgsGeometry.fromPointXY(p1).distance(QgsGeometry.fromPointXY(p2))
                G.add_edge((p1.x(), p1.y()), (p2.x(), p2.y()), weight=weight)
    return G

def find_path(graph, start_point, end_point):
    # Konvertieren Sie QgsPointXY in Tupel für die Verwendung mit NetworkX
    start_point_tuple = (start_point.x(), start_point.y())
    end_point_tuple = (end_point.x(), end_point.y())

    try:
        # Verwenden Sie die NetworkX-Funktion, um den kürzesten Pfad zu finden
        path = nx.shortest_path(graph, source=start_point_tuple, target=end_point_tuple, weight='weight')
        return path
    except nx.NetworkXNoPath:
        print("Kein Pfad zwischen {} und {} gefunden.".format(start_point, end_point))
        return None
    except nx.NodeNotFound as e:
        print(e)
        return None

def add_path_to_layer(path, provider):
    # Konvertieren Sie den Pfad in eine Liniengeometrie und fügen Sie ihn dem Layer hinzu
    if path:
        line_points = [QgsPointXY(p[0], p[1]) for p in path]
        line = QgsGeometry.fromPolylineXY(line_points)
        feat = QgsFeature()
        feat.setGeometry(line)
        provider.addFeatures([feat])

def add_points_to_graph(graph, points_set):
    # Füge jeden Punkt als Knoten im Graphen hinzu
    for point in points_set:
        graph.add_node((point.x(), point.y()), pos=point)

def generate_paths_between_points(street_layer, points_set, provider):
    graph = create_network_graph(street_layer)
    add_points_to_graph(graph, points_set)

    # Erstellen Sie Pfade zwischen allen Punkten im Set
    for start_point in points_set:
        for end_point in points_set:
            if start_point != end_point:
                path = find_path(graph, start_point, end_point)
                add_path_to_layer(path, provider)

# generate network for forward lines
def generate_network_fl(layer_points_fl, layer_wea, provider , street_layer):
    # Verwenden Sie die Funktion für beide Layer
    points_end_points = process_layer_points(layer_points_fl, provider, street_layer)
    wea_end_points = process_layer_points(layer_wea, provider, street_layer)
    
    # Vereinigen Sie die Endpunkte und sortieren Sie sie
    all_end_points = points_end_points.union(wea_end_points)

    generate_paths_between_points(street_layer, all_end_points, provider)


# generate network for return lines
def generate_network_rl(layer_points_rl, layer_wea, fixed_distance_rl, fixed_angle_rl, provider, street_layer):
    # Verwenden Sie die Funktion für beide Layer
    # Generate return lines for both layers
    points_end_points = generate_return_lines(layer_points_rl, fixed_distance_rl, fixed_angle_rl, provider, street_layer)
    points_end_wea = generate_return_lines(layer_wea, fixed_distance_rl, fixed_angle_rl, provider, street_layer)
    
    # Vereinigen Sie die Endpunkte und sortieren Sie sie
    all_end_points = points_end_points.union(points_end_wea)
    
    generate_paths_between_points(street_layer, all_end_points, provider)
