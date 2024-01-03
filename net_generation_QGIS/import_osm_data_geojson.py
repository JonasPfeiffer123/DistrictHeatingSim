import overpy
import json
from decimal import Decimal
import geojson

def download_osm_street_data(query, output_filename):
    # Overpass API initialisieren
    api = overpy.Overpass()

    # Overpass Abfrage senden
    result = api.query(query)
    
    # Transformer-Instanz für die Transformation erstellen
    #transformer = Transformer.from_crs("EPSG:4326", "EPSG:25833", always_xy=True)
    
    # GeoJSON Struktur vorbereiten
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    # Wege (Linien) aus dem Overpass Ergebnis hinzufügen
    for way in result.ways:
        # Liste für transformierte Koordinaten
        coords = []
        for node in way.nodes:
            # Koordinaten von WGS84 zu EPSG:25833 transformieren
            x, y = node.lon, node.lat
            # x, y = transformer.transform(node.lon, node.lat)
            coords.append([x, y])
        
        # Erstelle eine Linie für jeden Weg
        line = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            },
            "properties": way.tags
        }
        geojson["features"].append(line)

    # Funktion, um Decimal in JSON serialisierbar zu machen
    def decimal_default(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError("Object of type 'Decimal' is not JSON serializable")

    # GeoJSON Datei schreiben
    with open(output_filename, 'w') as outfile:
        json.dump(geojson, outfile, default=decimal_default)

# Hier setzen Sie Ihre Overpass-Abfrage ein
overpass_query = """
[out:json][timeout:25];
area[name="Zittau"]->.area_0;
(
  node["highway"="primary"](area.area_0);
  node["highway"="secondary"](area.area_0);
  node["highway"="tertiary"](area.area_0);
  node["highway"="residential"](area.area_0);
  node["highway"="road"](area.area_0);
  node["highway"="living_street"](area.area_0);
  way["highway"="primary"](area.area_0);
  way["highway"="secondary"](area.area_0);
  way["highway"="tertiary"](area.area_0);
  way["highway"="residential"](area.area_0);
  way["highway"="road"](area.area_0);
  way["highway"="living_street"](area.area_0);
  relation["highway"="primary"](area.area_0);
  relation["highway"="secondary"](area.area_0);
  relation["highway"="tertiary"](area.area_0);
  relation["highway"="residential"](area.area_0);
  relation["highway"="road"](area.area_0);
  relation["highway"="living_street"](area.area_0);
);
(._;>;);
out body;
"""

# Ausgabedateiname für GeoJSON-Datei
output_geojson_file = "C:/Users/username/heating_network_generation/Straßen Zittau.geojson"

# Download der Daten und Speichern als GeoJSON
#download_osm_street_data(overpass_query, output_geojson_file)

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
    save_to_file(geojson_data, "osm_data_script.geojson")

run_here()