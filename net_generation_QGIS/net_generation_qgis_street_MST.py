from qgis.PyQt.QtCore import QVariant
from qgis.core import (QgsFeature, QgsField, QgsGeometry, QgsPointXY, QgsProject, QgsRasterLayer, QgsVectorLayer,
                       QgsWkbTypes, QgsVectorFileWriter)

import networkx as nx
import math

def import_osm_street_layer(osm_street_layer_geojson_file):
    layer = QgsVectorLayer(osm_street_layer_geojson_file, "Straßen", "ogr")
    if not layer.isValid():
        print("Layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(layer)
            
def import_osm_layer():
    """
    Importiert den OpenStreetMap-Layer und fügt ihn dem QGIS-Projekt hinzu.
    """
    try:
        osm_url = "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        osm_layer = QgsRasterLayer(osm_url, "OpenStreetMap", "wms")
        if not osm_layer.isValid():
            raise ValueError("OSM Layer ist ungültig.")
        QgsProject.instance().addMapLayer(osm_layer)
        print("OSM Layer wurde erfolgreich geladen.")
    except Exception as e:
        print(f"Fehler beim Laden des OSM Layers: {e}")

def create_data_layer(text_file_path, data_csv_file_name):
    """
    Erstellt einen Daten-Layer aus einer CSV-Datei.
    """
    try:
        csv_layer = QgsVectorLayer(f"file:///{text_file_path}?delimiter=;&crs=epsg:25833&type=csv&xField=UTM_X&yField=UTM_Y", data_csv_file_name, "delimitedtext")
        if not csv_layer.isValid():
            raise ValueError("CSV Layer ist ungültig.")
        QgsProject.instance().addMapLayer(csv_layer)
        print("Data-Layer wurde erfolgreich geladen.")
    except Exception as e:
        print(f"Fehler beim Laden des Data-Layers: {e}")

def create_point_layer(x_coord, y_coord):
    # Erstellen eines neuen Punktlayers
    point_layer = QgsVectorLayer("Point?crs=epsg:25833", "Erzeugerstandorte", "memory")

    # Erstellen eines neuen Features
    point_feature = QgsFeature()
    point_geometry = QgsGeometry.fromPointXY(QgsPointXY(x_coord, y_coord))
    point_feature.setGeometry(point_geometry)

    # Hinzufügen des Features zum Layer
    dp = point_layer.dataProvider()
    dp.addFeatures([point_feature])
    point_layer.updateExtents()

    # Exportieren des Layers als GeoJSON
    output_file = "Erzeugerstandorte.geojson"
    error = QgsVectorFileWriter.writeAsVectorFormat(point_layer, output_file, "utf-8", point_layer.crs(), "GeoJSON")

    if error[0] == QgsVectorFileWriter.NoError:
        print("Point-Layer erfolgreich als GeoJSON exportiert.")
    else:
        print("Fehler beim Exportieren des Point-Layers:", error[1])

    # Laden des gespeicherten GeoJSON-Layers
    geojson_layer = QgsVectorLayer(output_file, "Erzeugerstandorte", "ogr")

    # Hinzufügen des geladenen Layers zum Projekt
    if not geojson_layer.isValid():
        print("Point-Layer konnte nicht geladen werden.")
    else:
        QgsProject.instance().addMapLayer(geojson_layer)
        print("Point-Layer wurde erfolgreich geladen.")


def create_layer(layer_name, layer_type, crs_i):
    vl_i = QgsVectorLayer(f"{layer_type}?crs={crs_i}", layer_name, "memory")
    provider = vl_i.dataProvider()
    provider.addAttributes([QgsField("id", QVariant.Int)])
    vl_i.updateFields()
    vl_i.startEditing()
    return vl_i, provider


def create_offset_points(point, distance, angle_degrees):
    """
    Erzeugt einen versetzten Punkt basierend auf Distanz und Winkel.
    """
    angle_radians = math.radians(angle_degrees)
    dx = distance * math.cos(angle_radians)
    dy = distance * math.sin(angle_radians)
    return QgsPointXY(point.x() + dx, point.y() + dy)


def generate_lines(layer, distance, angle_degrees, provider):
    for point_feat in layer.getFeatures():
        original_point_geom = point_feat.geometry()
        original_point = original_point_geom.asPoint()
        offset_point = create_offset_points(original_point, distance, angle_degrees)
        offset_point_geom = QgsGeometry.fromPointXY(offset_point)
        line = original_point_geom.shortestLine(offset_point_geom)
        new_line = QgsFeature()
        new_line.setGeometry(line)
        provider.addFeatures([new_line])


def find_nearest_point(current_point, other_points):
    min_distance = float('inf')
    nearest_point = None

    for other_point in other_points:
        if other_point != current_point:
            distance = current_point.distance(other_point)
            if distance < min_distance:
                min_distance = distance
                nearest_point = other_point
    return nearest_point


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


def generate_rl_layer_points(layer, distance, angle_degrees, crs="EPSG:25833"):
    # Erstelle einen neuen Vektorlayer für die Offset-Punkte
    point_layer = QgsVectorLayer("Point?crs=" + crs, "Offset Points", "memory")
    pr = point_layer.dataProvider()
    pr.addAttributes([QgsField("id", QVariant.Int)])
    point_layer.updateFields()

    # Füge die Offset-Punkte als Features hinzu
    id_counter = 0
    for point_feat in layer.getFeatures():
        original_point = point_feat.geometry().asPoint()
        offset_point = create_offset_points(original_point, distance, angle_degrees)
        offset_feature = QgsFeature()
        offset_feature.setGeometry(QgsGeometry.fromPointXY(offset_point))
        offset_feature.setAttributes([id_counter])
        pr.addFeatures([offset_feature])
        id_counter += 1

    # Aktualisiere den Layer
    point_layer.updateExtents()
    return point_layer

def create_graph_from_layer(street_layer):
    G = nx.Graph()
    
    for feat in street_layer.getFeatures():
        geom = feat.geometry()
        
        if geom.type() == QgsWkbTypes.LineGeometry:
            if geom.isMultipart():
                lines = geom.asMultiPolyline()
            else:
                lines = [geom.asPolyline()]
            
            for line in lines:
                for i in range(len(line) - 1):
                    start = line[i]
                    end = line[i + 1]
                    
                    # Füge die Knoten und Kanten zum Graphen hinzu
                    G.add_node(tuple(start), pos=start)  # Verwenden von Tupeln als Knoten
                    G.add_node(tuple(end), pos=end)
                    G.add_edge(tuple(start), tuple(end))
    
    return G

def find_nearest_node(point, graph):
    min_distance = float('inf')
    nearest_node = None

    # Durchlaufe alle Knoten im Graphen und suche den nächsten Knoten
    for node, data in graph.nodes(data=True):
        if 'pos' in data:
            node_point = data['pos']
            distance = point.distance(node_point)
            if distance < min_distance:
                min_distance = distance
                nearest_node = node
        else:
            print(f"Fehler: Knoten {node} hat kein 'pos'-Attribut.")

    return nearest_node

def generate_street_based_mst(point_set, street_layer, provider):
    # Erstelle einen NetworkX Graphen basierend auf dem Straßenlayer
    street_graph = create_graph_from_layer(street_layer)
        
    # Zuweisen von Punkten zu den nächsten Straßenknoten
    point_to_node = {}
    for point in point_set:
        point_geom = QgsGeometry.fromPointXY(point)
        nearest_node = find_nearest_node(point, street_graph)
        nearest_node_geom = QgsGeometry.fromPointXY(QgsPointXY(nearest_node[0], nearest_node[1]))

        perpendicular_line = point_geom.shortestLine(nearest_node_geom)
        
        new_line = QgsFeature()
        new_line.setGeometry(perpendicular_line)
        provider.addFeatures([new_line])
        
        point_to_node[point] = nearest_node

    # Erstellen des MST unter Verwendung der nächsten Straßenknoten
    mst_graph = nx.minimum_spanning_tree(street_graph)
    
    for edge in mst_graph.edges(data=True):
        start_coord, end_coord = edge[0], edge[1]
        
        if start_coord in street_graph.nodes and end_coord in street_graph.nodes:
            start_point = QgsPointXY(*street_graph.nodes[start_coord]['pos'])
            end_point = QgsPointXY(*street_graph.nodes[end_coord]['pos'])
        
        # Erstelle ein Feature für die Kante
        line_feature = QgsFeature()
        line_feature.setGeometry(QgsGeometry.fromPolylineXY([start_point, end_point]))
        provider.addFeatures([line_feature])

def layer_to_point_set(layer):
    point_set = set()
    for feat in layer.getFeatures():
        geom = feat.geometry()
        if geom.type() == QgsWkbTypes.PointGeometry:
            if geom.isMultipart():
                points = geom.asMultiPoint()
            else:
                points = [geom.asPoint()]
            for point in points:
                point_set.add(QgsPointXY(point))
    return point_set

def merge_point_sets(set1, set2):
    return set1.union(set2)

def generate_network_fl(layer_points_fl, layer_wea_fl, provider , layer_lines):
    point_set_fl = layer_to_point_set(layer_points_fl)
    point_set_wea_fl = layer_to_point_set(layer_wea_fl)
    merged_set_fl = merge_point_sets(point_set_fl, point_set_wea_fl)
    generate_street_based_mst(merged_set_fl, layer_lines, provider)


# generate network for return lines
def generate_network_rl(layer_points_fl, layer_wea_fl, fixed_distance_rl, fixed_angle_rl, provider, layer_lines):
    layer_points_rl = generate_rl_layer_points(layer_points_fl, fixed_distance_rl, fixed_angle_rl)
    layer_wea_rl = generate_rl_layer_points(layer_wea_fl, fixed_distance_rl, fixed_angle_rl)
    
    point_set_rl = layer_to_point_set(layer_points_rl)
    point_set_wea_rl = layer_to_point_set(layer_wea_rl)
    merged_set_rl = merge_point_sets(point_set_rl, point_set_wea_rl)
    
    generate_street_based_mst(merged_set_rl, layer_lines, provider)