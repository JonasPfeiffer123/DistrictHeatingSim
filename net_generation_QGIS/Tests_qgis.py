from qgis.PyQt.QtCore import QVariant
from qgis.core import (QgsFeature, QgsField, QgsGeometry, QgsPointXY, QgsProject, QgsRasterLayer, QgsVectorLayer,
                       QgsApplication, QgsCoordinateReferenceSystem, QgsCoordinateTransform,QgsVectorFileWriter)

import networkx as nx
import math

import requests


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
    output_file = "Straßen.geojson"
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