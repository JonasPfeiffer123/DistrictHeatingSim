from qgis.PyQt.QtCore import QVariant
from qgis.core import (QgsFeature, QgsField, QgsGeometry, QgsPointXY, QgsProject, QgsRasterLayer, QgsVectorLayer,
                       QgsApplication, QgsCoordinateReferenceSystem, QgsCoordinateTransform,QgsVectorFileWriter)

import networkx as nx
import math

import requests


def import_osm_layer():
    # URL für den OpenStreetMap XYZ-Tile-Service
    osm_url = "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png"

    # Erstellen eines Rasterlayers für OSM
    osm_layer = QgsRasterLayer(osm_url, "OpenStreetMap", "wms")

    # Hinzufügen des Layers zum Projekt
    if osm_layer.isValid():
        QgsProject.instance().addMapLayer(osm_layer)
        print("OSM Layer wurde erfolgreich geladen.")
    else:
        print("OSM Layer konnte nicht geladen werden.")


def import_street_layer(area, values):
    stadt_name = area
    overpass_url = "https://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    area[name="{stadt_name}"]->.searchArea;
    (
      relation(area.searchArea)["name"="{stadt_name}"];
    );
    out body;
    """
    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()

    # Extrahieren der Relation-ID
    relation_id = data['elements'][0]['id'] if data['elements'] else None
    print("Relation-ID:", relation_id)
    
    params = {
        # 'OSM_TYPE': 'relation',
        # 'OSM_ID': relation_id,
        'AREA': area,
        'KEY': 'highway',
        'SERVER': 'https://lz4.overpass-api.de/api/interpreter',
        'TIMEOUT': 25,
        'VALUE': values 
    }
    query = processing.run("quickosm:buildqueryaroundarea", params)
    file = processing.run("native:filedownloader", {'URL':query['OUTPUT_URL'], 'OUTPUT':'TEMPORARY_OUTPUT'})

    # Ausgsabe des filedownloader Algorithmus
    downloaded_file = file['OUTPUT']

    # Linienlayer erstellen
    lines_layer = QgsVectorLayer(downloaded_file + "|layername=lines", "OSM Lines", "ogr")

    # Exportieren des Layers als GeoJSON
    output_file = "geoJSON_Straßen.geojson"
    # Setzen Sie das gewünschte CRS
    crs = QgsCoordinateReferenceSystem("EPSG:25833")
    error = QgsVectorFileWriter.writeAsVectorFormat(lines_layer, output_file, "utf-8", crs, "GeoJSON")

    if error[0] == QgsVectorFileWriter.NoError:
        print("Layer erfolgreich als GeoJSON exportiert.")
    else:
        print("Fehler beim Exportieren des Layers:", error[1])

    # Laden des gespeicherten GeoJSON-Layers
    geojson_layer = QgsVectorLayer(output_file, "Straßen", "ogr")
    
    # Fügen Sie den Linienlayer zum Projekt hinzu, wenn er gültig ist
    if geojson_layer.isValid():
        QgsProject.instance().addMapLayer(geojson_layer)
        print("Streetlayer wurde erfolgreich geladen.")
    else:
        print("Streetlayer konnte nicht geladen werden.")


def create_data_layer(text_file_path):
    # Erstellen Sie einen Layer aus der Textdatei
    # Hier wird angenommen, dass Ihre Datei Koordinaten in Spalten mit den Namen 'Longitude' und 'Latitude' enthält
    csv_layer = QgsVectorLayer(f"file:///{text_file_path}?delimiter=;&crs=epsg:25833&type=csv&xField=UTM_X&yField=UTM_Y", "Beispieldaten_ETRS89", "delimitedtext")
    if not csv_layer.isValid():
        print("Layer konnte nicht geladen werden.")
    else:
        QgsProject.instance().addMapLayer(csv_layer)
        print("Layer wurde erfolgreich geladen.")

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
    output_file = "geoJSON_Erzeugerstandorte.geojson"
    error = QgsVectorFileWriter.writeAsVectorFormat(point_layer, output_file, "utf-8", point_layer.crs(), "GeoJSON")

    if error[0] == QgsVectorFileWriter.NoError:
        print("Layer erfolgreich als GeoJSON exportiert.")
    else:
        print("Fehler beim Exportieren des Layers:", error[1])

    # Laden des gespeicherten GeoJSON-Layers
    geojson_layer = QgsVectorLayer(output_file, "Erzeugerstandorte", "ogr")

    # Hinzufügen des geladenen Layers zum Projekt
    if not geojson_layer.isValid():
        print("Layer konnte nicht geladen werden.")
    else:
        QgsProject.instance().addMapLayer(geojson_layer)
        print("Layer wurde erfolgreich geladen.")


def create_layer(layer_name, layer_type, crs_i):
    vl_i = QgsVectorLayer(f"{layer_type}?crs={crs_i}", layer_name, "memory")
    provider = vl_i.dataProvider()
    provider.addAttributes([QgsField("id", QVariant.Int)])
    vl_i.updateFields()
    vl_i.startEditing()
    return vl_i, provider


def create_offset_points(point, distance, angle_degrees):
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
                distance = point.distance(other_point)
                g.add_edge((point.x(), point.y()), (other_point.x(), other_point.y()), weight=distance)
    
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

