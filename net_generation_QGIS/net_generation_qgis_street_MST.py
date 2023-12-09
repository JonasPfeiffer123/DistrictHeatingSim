from qgis.PyQt.QtCore import QVariant
from qgis.core import (QgsFeature, QgsField, QgsGeometry, QgsPointXY, QgsProject, QgsRasterLayer, QgsVectorLayer,
                       QgsWkbTypes, QgsVectorFileWriter, QgsSpatialIndex)

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

def create_graph_from_layer(street_layer, point_set, threshold):
    G = nx.Graph()
    street_index = QgsSpatialIndex()  # räumlicher Index für Straßen
    point_index = QgsSpatialIndex()  # räumlicher Index für Punkte
    point_features = []

    # Erstelle Features für jeden Punkt im point_set und füge sie zum Punkt-Index hinzu
    for idx, point in enumerate(point_set):
        feat = QgsFeature(idx)
        feat.setGeometry(QgsGeometry.fromPointXY(point))
        point_features.append(feat)
        point_index.insertFeature(feat)

    # Füge alle Liniengeometrien zum Straßen-Index hinzu
    for feat in street_layer.getFeatures():
        street_index.insertFeature(feat)

    for feat in street_layer.getFeatures():
        geom = feat.geometry()
        if geom.type() == QgsWkbTypes.LineGeometry:
            if geom.isMultipart():
                lines = geom.asMultiPolyline()
            else:
                lines = [geom.asPolyline()]

            for line in lines:
                for i in range(len(line) - 1):
                    start = QgsPointXY(*line[i])
                    end = QgsPointXY(*line[i+1])

                    # Finde den nächstgelegenen Punkt zum Linienstart und -ende
                    start_nearest_ids = point_index.nearestNeighbor(start, 1)
                    end_nearest_ids = point_index.nearestNeighbor(end, 1)
                    start_nearest_point = point_features[start_nearest_ids[0]].geometry().asPoint()
                    end_nearest_point = point_features[end_nearest_ids[0]].geometry().asPoint()

                    # Prüfe, ob der Start- oder Endpunkt innerhalb der Distanzschwelle liegt
                    if (start.distance(start_nearest_point) <= threshold or
                        end.distance(end_nearest_point) <= threshold):
                        G.add_node(tuple(start), pos=start)
                        G.add_node(tuple(end), pos=end)
                        G.add_edge(tuple(start), tuple(end))

    return G

def find_nearest_node_within_threshold(point, graph, threshold):
    min_distance = float('inf')
    nearest_node = None
    for node in graph.nodes:
        node_point = QgsPointXY(graph.nodes[node]['pos'])
        distance = point.distance(node_point)
        if distance < min_distance and distance <= threshold:
            min_distance = distance
            nearest_node = node
    return nearest_node, min_distance if nearest_node else None

def generate_street_based_mst(point_set, street_layer, provider, distance_threshold=20):
    street_graph = create_graph_from_layer(street_layer, point_set, distance_threshold)

    g = nx.Graph()

    nearest_nodes = set()
    for point in point_set:
        nearest_node, node_distance = find_nearest_node_within_threshold(point, street_graph, distance_threshold)
        if nearest_node:
            nearest_node_as_point = QgsPointXY(nearest_node[0], nearest_node[1])
            nearest_nodes.add(nearest_node_as_point)
            g.add_edge(tuple(point), tuple(nearest_node_as_point), weight=node_distance)

    # Erstelle den MST nur mit den nächstgelegenen Knotenpunkten
    mst_graph = nx.minimum_spanning_tree(g)

    for edge in mst_graph.edges(data=True):
        start_point, end_point = edge[0], edge[1]
        # Überprüfen Sie, ob die Kante bereits existiert, um Doppelverbindungen zu vermeiden
        if not g.has_edge(start_point, end_point):
            line_feature = QgsFeature()
            line_feature.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(*start_point), QgsPointXY(*end_point)]))
            provider.addFeatures([line_feature])

    all_mst_points = sorted(point_set.union(nearest_nodes), key=lambda p: (p.x(), p.y()))

    for point in all_mst_points:
        for other_point in all_mst_points:
            if point != other_point:
                g.add_edge((point.x(), point.y()), (other_point.x(), other_point.y()), weight=point.distance(other_point))

    # Erstellen des MST unter Verwendung der nächsten Straßenknoten
    mst_graph = nx.minimum_spanning_tree(g)
    
    # adding the MST to the layer
    for edge in mst_graph.edges(data=True):
        start_point = QgsPointXY(*edge[0])
        end_point = QgsPointXY(*edge[1])
        distance = edge[2]['weight']
        
        # Erstellen Sie ein Feature für die Kante
        line_feature = QgsFeature()
        line_feature.setGeometry(QgsGeometry.fromPolylineXY([start_point, end_point]))
        line_feature.setAttributes([distance])
        provider.addFeatures([line_feature])

# generate network for forward lines
def generate_network_fl(layer_points_fl, layer_wea, provider , street_layer):
    # Verwenden Sie die Funktion für beide Layer
    points_end_points = process_layer_points(layer_points_fl, provider, street_layer)
    wea_end_points = process_layer_points(layer_wea, provider, street_layer)
    
    # Vereinigen Sie die Endpunkte und sortieren Sie sie
    all_end_points = points_end_points.union(wea_end_points)

    generate_street_based_mst(all_end_points, street_layer, provider)


# generate network for return lines
def generate_network_rl(layer_points_rl, layer_wea, fixed_distance_rl, fixed_angle_rl, provider, street_layer):
    # Verwenden Sie die Funktion für beide Layer
    # Generate return lines for both layers
    points_end_points = generate_return_lines(layer_points_rl, fixed_distance_rl, fixed_angle_rl, provider, street_layer)
    points_end_wea = generate_return_lines(layer_wea, fixed_distance_rl, fixed_angle_rl, provider, street_layer)
    
    # Vereinigen Sie die Endpunkte und sortieren Sie sie
    all_end_points = points_end_points.union(points_end_wea)
    
    generate_street_based_mst(all_end_points, street_layer, provider)
