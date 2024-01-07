import overpy
import json
from decimal import Decimal
import geojson

def build_query(city_name, tags):
    # Basis-Query, die nach der Stadt sucht
    query = f"""
    [out:json][timeout:25];
    area[name="{city_name}"]->.searchArea;
    (
    """
    # Fügt jedes Tag-Paar zur Query hinzu, aber für way-Elemente
    for key, value in tags.items():
        query += f'way["{key}"="{value}"](area.searchArea);\n'
    
    # Schließt die Query
    query += """
    );
    out body;
    >;
    out skel qt;
    """
    return query

# Die Funktion zum Herunterladen der Daten
def download_data(query):
    api = overpy.Overpass()
    result = api.query(query)

    # Konvertieren Sie die Overpass-Resultate in GeoJSON-Features
    features = []
    for way in result.ways:
        # Extrahieren Sie die Koordinaten der Knotenpunkte, die den Weg bilden
        coordinates = [(node.lon, node.lat) for node in way.nodes]
        
        # Erstellen Sie ein LineString-Feature für den Weg
        linestring = geojson.LineString(coordinates)
        properties = way.tags
        feature = geojson.Feature(geometry=linestring, properties=properties)
        features.append(feature)

    # Erstellen eines GeoJSON FeatureCollections
    feature_collection = geojson.FeatureCollection(features)
    return feature_collection

def json_serial(obj):
    """JSON serializer für Objekte, die nicht serienmäßig serialisierbar sind."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Objekt vom Typ {type(obj).__name__} ist nicht JSON serialisierbar")

def save_to_file(geojson_data, filename):
    with open(filename, 'w') as outfile:
        json.dump(geojson_data, outfile, indent=2, default=json_serial)

def run_here():
    city_name = "Zittau"
    tags = {"highway": "primary"}
    query = build_query(city_name, tags)
    geojson_data = download_data(query)
    save_to_file(geojson_data, "osm_data/osm_data_script.geojson")

#run_here()