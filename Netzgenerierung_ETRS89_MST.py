from qgis.PyQt.QtCore import QVariant
from qgis.core import (QgsFeature, QgsField, QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer, QgsVectorFileWriter)
import networkx as nx
import math

# prepare the environment
layer_points = QgsProject.instance().mapLayersByName('Beispieldaten_ETRS89')[0]
layer_lines = QgsProject.instance().mapLayersByName('Straßen Zittau')[0]
layer_WEA = QgsProject.instance().mapLayersByName('Erzeugerstandorte')[0]

def create_layer(layer_name, layer_type, crs):
    vl = QgsVectorLayer(f"{layer_type}?crs={crs}", layer_name, "memory")
    provider = vl.dataProvider()
    provider.addAttributes([QgsField("id", QVariant.Int)])
    vl.updateFields()
    vl.startEditing()
    return vl, provider

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

def process_layer_points(layer, provider):
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
def generate_return_lines(layer, distance, angle_degrees, provider):
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
def generate_MST(all_end_points, provider):
    # create the MST-graph
    G = nx.Graph()

    for point in all_end_points:
        for other_point in all_end_points:
            if point != other_point:
                distance = point.distance(other_point)
                G.add_edge((point.x(), point.y()), (other_point.x(), other_point.y()), weight=distance)
    
    #calculate the MST
    mst = nx.minimum_spanning_tree(G)
    
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
def generate_Network_fl(layer_points, layer_WEA, provider):
    # Verwenden Sie die Funktion für beide Layer
    points_end_points = process_layer_points(layer_points, provider)
    wea_end_points = process_layer_points(layer_WEA, provider)
    
    # Vereinigen Sie die Endpunkte und sortieren Sie sie
    all_end_points = sorted(points_end_points.union(wea_end_points), key=lambda p: (p.x(), p.y()))
    
    generate_MST(all_end_points, provider) 

# generate network for return lines
def generate_Network_rl(layer_points, layer_WEA, fixed_distance, fixed_angle, provider):
    # Verwenden Sie die Funktion für beide Layer
    # Generate return lines for both layers
    points_end_points = generate_return_lines(layer_points, fixed_distance, fixed_angle, provider)
    points_end_WEA = generate_return_lines(layer_WEA, fixed_distance, fixed_angle, provider)
    
    # Vereinigen Sie die Endpunkte und sortieren Sie sie
    all_end_points = sorted(points_end_points.union(points_end_WEA), key=lambda p: (p.x(), p.y()))
    
    generate_MST(all_end_points, provider)
    
# create the layers
crs = layer_points.crs().toWkt()
vl_hast, provider_hast = create_layer("HAST", "Linestring", crs)
vl_ruecklauf, provider_ruecklauf = create_layer("Rücklauf", "Linestring", crs)
vl_vorlauf, provider_vorlauf = create_layer("Vorlauf", "Linestring", crs)
vl_erzeugeranlagen, provider_erzeugeranlagen = create_layer("Erzeugeranlagen", "Linestring", crs)

# Set your desired offset distance between forward and return lines here
fixed_angle = 0
fixed_distance = 1

# generate heat exchanger coordinates
generate_lines(layer_points, fixed_distance, fixed_angle, provider_hast)

# generate heat generator coordinates
generate_lines(layer_WEA, fixed_distance, fixed_angle, provider_erzeugeranlagen)

# generate network - fl stands for forward lines, rl for return lines
generate_Network_fl(layer_points, layer_WEA, provider_vorlauf)
generate_Network_rl(layer_points, layer_WEA, fixed_distance, fixed_angle, provider_ruecklauf)


# commit changes for all layers
for vl in [vl_hast, vl_ruecklauf, vl_vorlauf, vl_erzeugeranlagen]:
    vl.commitChanges()
    vl.updateExtents()
    vl.triggerRepaint()

# write layers as GeoJSON
output_files = ["HAST.geojson", "Rücklauf.geojson", "Vorlauf.geojson", "Erzeugeranlagen.geojson"]
colors = ["green", "blue", "red", "black"]

for vl, color, output_file in zip([vl_hast, vl_ruecklauf, vl_vorlauf, vl_erzeugeranlagen], colors, output_files):
    error = QgsVectorFileWriter.writeAsVectorFormat(vl, output_file, "utf-8", vl.crs(), "GeoJSON")
    if error[0] == QgsVectorFileWriter.NoError:
        print(f"Schreiben des Layers {vl.name()} als GeoJSON war erfolgreich!")
        vlayer = QgsVectorLayer(output_file, vl.name(), "ogr")
        
        # coloring the different layers
        symbol = QgsLineSymbol.createSimple({'line_color': color, 'line_width': '0.75'})
        renderer = QgsSingleSymbolRenderer(symbol)
        vlayer.setRenderer(renderer)
        if not vlayer.isValid():
            print(f"Layer {vl.name()} konnte nicht geladen werden!")
        else:
            QgsProject.instance().addMapLayer(vlayer)
            print(f"Layer {vl.name()} wurde erfolgreich geladen!")
    else:
        print(f"Fehler beim Schreiben des Layers {vl.name()}: ", error[1])
