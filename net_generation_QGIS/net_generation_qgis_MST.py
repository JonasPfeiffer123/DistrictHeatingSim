from qgis.PyQt.QtCore import QVariant
from qgis.core import (QgsFeature, QgsField, QgsGeometry, QgsPointXY, QgsProject, QgsRasterLayer, QgsVectorLayer,
                       QgsApplication, QgsCoordinateReferenceSystem, QgsCoordinateTransform,QgsVectorFileWriter)

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


# network generation with MST (Minimum Spanning Tree)
def generate_mst(all_end_points, provider):
    # create the MST-graph
    g = nx.Graph()

    for point in all_end_points:
        for other_point in all_end_points:
            if point != other_point:
                g.add_edge((point.x(), point.y()), (other_point.x(), other_point.y()), weight=point.distance(other_point))
    
    # calculate the MST
    mst = nx.minimum_spanning_tree(g)
    
    # adding the MST to the layer
    for edge in mst.edges(data=True):
        start_point = QgsPointXY(*edge[0])
        end_point = QgsPointXY(*edge[1])
        distance = edge[2]['weight']
        
        # Erstellen Sie ein Feature für die Kante
        line_feature = QgsFeature()
        line_feature.setGeometry(QgsGeometry.fromPolylineXY([start_point, end_point]))
        line_feature.setAttributes([distance])
        provider.addFeatures([line_feature])


# generate network for forward lines
def generate_network_fl(layer_points_fl, layer_wea, provider , layer_lines):
    # Verwenden Sie die Funktion für beide Layer
    points_end_points = process_layer_points(layer_points_fl, provider, layer_lines)
    wea_end_points = process_layer_points(layer_wea, provider, layer_lines)
    
    # Vereinigen Sie die Endpunkte und sortieren Sie sie
    all_end_points = sorted(points_end_points.union(wea_end_points), key=lambda p: (p.x(), p.y()))
    
    generate_mst(all_end_points, provider)


# generate network for return lines
def generate_network_rl(layer_points_rl, layer_wea, fixed_distance_rl, fixed_angle_rl, provider, layer_lines):
    # Verwenden Sie die Funktion für beide Layer
    # Generate return lines for both layers
    points_end_points = generate_return_lines(layer_points_rl, fixed_distance_rl, fixed_angle_rl, provider, layer_lines)
    points_end_wea = generate_return_lines(layer_wea, fixed_distance_rl, fixed_angle_rl, provider, layer_lines)
    
    # Vereinigen Sie die Endpunkte und sortieren Sie sie
    all_end_points = sorted(points_end_points.union(points_end_wea), key=lambda p: (p.x(), p.y()))
    
    generate_mst(all_end_points, provider)

