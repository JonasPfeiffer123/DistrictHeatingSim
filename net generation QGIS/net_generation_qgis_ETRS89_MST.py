from qgis.core import (QgsFeature, QgsField, QgsGeometry, QgsPointXY, QgsProject, QgsRasterLayer, QgsVectorLayer,
                       QgsApplication, QgsCoordinateReferenceSystem, QgsCoordinateTransform,QgsVectorFileWriter)

from net_generation_qgis_functions import *

import_osm_layer()

# area = 'Zittau'
# relation_id = 418117 # Zittau
# values = 'primary|secondary|tertiary|residential'
# values = ['primary', 'secondary', 'tertiary', 'residential']
# import_street_layer(area, values)

# Pfad zur Textdatei
text_file_path = "data_output_ETRS89.csv"
create_data_layer(text_file_path)
    
# Koordinaten für den Punkt
x_coord = 486267.307  # Longitude
y_coord = 5637294.910  # Latitude

create_point_layer(x_coord, y_coord)

# prepare the environment
layer_points = QgsProject.instance().mapLayersByName('data_output_ETRS89')[0]
layer_lines = QgsProject.instance().mapLayersByName('Straßen')[0]
layer_WEA = QgsProject.instance().mapLayersByName('Erzeugerstandorte')[0]

# create the layers
crs = layer_points.crs().toWkt()
vl_hast, provider_hast = create_layer("HAST", "Linestring", crs)
vl_rl, provider_rl = create_layer("Rücklauf", "Linestring", crs)
vl_vl, provider_vl = create_layer("Vorlauf", "Linestring", crs)
vl_erzeugeranlagen, provider_erzeugeranlagen = create_layer("Erzeugeranlagen", "Linestring", crs)

# Set your desired offset distance between forward and return lines here
fixed_angle = 0
fixed_distance = 1

# generate heat exchanger coordinates
generate_lines(layer_points, fixed_distance, fixed_angle, provider_hast)

# generate heat generator coordinates
generate_lines(layer_WEA, fixed_distance, fixed_angle, provider_erzeugeranlagen)

# generate network - fl stands for forward lines, rl for return lines
generate_network_fl(layer_points, layer_WEA, provider_vl, layer_lines)
generate_network_rl(layer_points, layer_WEA, fixed_distance, fixed_angle, provider_rl, layer_lines)


# commit changes for all layers
for vl in [vl_hast, vl_rl, vl_vl, vl_erzeugeranlagen]:
    vl.commitChanges()
    vl.updateExtents()
    vl.triggerRepaint()

# write layers as GeoJSON
output_files = ["geoJSON_HAST.geojson", "geoJSON_Rücklauf.geojson", "geoJSON_Vorlauf.geojson", "geoJSON_Erzeugeranlagen.geojson"]
colors = ["green", "blue", "red", "black"]

for vl, color, output_file in zip([vl_hast, vl_rl, vl_vl, vl_erzeugeranlagen], colors, output_files):
    error = QgsVectorFileWriter.writeAsVectorFormat(vl, output_file, "utf-8", vl.crs(), "GeoJSON")
    if error[0] == QgsVectorFileWriter.NoError:
        print(f"Schreiben des Layers {vl.name()} als GeoJSON war erfolgreich!")
        v_layer = QgsVectorLayer(output_file, vl.name(), "ogr")
        
        # coloring the different layers
        symbol = QgsLineSymbol.createSimple({'line_color': color, 'line_width': '0.75'})
        renderer = QgsSingleSymbolRenderer(symbol)
        v_layer.setRenderer(renderer)
        if not v_layer.isValid():
            print(f"Layer {vl.name()} konnte nicht geladen werden!")
        else:
            QgsProject.instance().addMapLayer(v_layer)
            print(f"Layer {vl.name()} wurde erfolgreich geladen!")
    else:
        print(f"Fehler beim Schreiben des Layers {vl.name()}: ", error[1])
