"""
OpenStreetMap data import and GeoJSON conversion module.

Provides Overpass API integration for downloading OSM data and converting
it to GeoJSON format for district heating network planning.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import overpy
import json
from decimal import Decimal
import geojson

def build_query(city_name, tags, element_type="way"):
    """
    Build Overpass API query for OSM data download.

    :param city_name: City name for OSM query
    :type city_name: str
    :param tags: List of (key, value) tuples to filter OSM elements
    :type tags: list of tuple
    :param element_type: OSM element type ('way' or 'building')
    :type element_type: str
    :return: Overpass API query string
    :rtype: str
    """
    query = f"""
    [out:json][timeout:25];
    area[name="{city_name}"]->.searchArea;
    (
    """

    if element_type == "way":
        for key, value in tags:
            query += f'way["{key}"="{value}"](area.searchArea);'
    
    elif element_type == "building":
        query += 'relation["building"](area.searchArea);'
        query += 'way["building"](area.searchArea);'
    
    query += """
    );
    (._;>;);
    out body;
    """
    return query

def download_data(query, element_type):
    """
    Download OSM data via Overpass API and convert to GeoJSON.

    :param query: Overpass API query string
    :type query: str
    :param element_type: OSM element type ('way' or 'building')
    :type element_type: str
    :return: GeoJSON FeatureCollection with OSM data
    :rtype: geojson.FeatureCollection
    :raises OverpassError: If API query fails
    
    .. note::
        Ways create LineString geometries, buildings create Polygon/MultiPolygon.
    """
    api = overpy.Overpass()
    result = api.query(query)

    features = []

    if element_type == "way":  # for streets
        for way in result.ways:
            coordinates = [(node.lon, node.lat) for node in way.nodes]
            linestring = geojson.LineString(coordinates)
            properties = way.tags
            feature = geojson.Feature(geometry=linestring, properties=properties)
            features.append(feature)
    
    elif element_type == "building":  # for buildings
        for relation in result.relations:
            multipolygon = []
            for member in relation.members:
                if member.role == "outer" or member.role == "inner":
                    way = member.resolve()
                    coordinates = [(node.lon, node.lat) for node in way.nodes]
                    if coordinates[0] != coordinates[-1]:
                        coordinates.append(coordinates[0])
                    multipolygon.append(coordinates)

            properties = relation.tags
            feature = geojson.Feature(geometry=geojson.MultiPolygon([multipolygon]), properties=properties)
            features.append(feature)

        for way in result.ways:
            # Make sure the building is closed (first and last points the same)
            if way.nodes[0] != way.nodes[-1]:
                way.nodes.append(way.nodes[0])
            coordinates = [(node.lon, node.lat) for node in way.nodes]
            polygon = geojson.Polygon([coordinates])
            properties = way.tags
            feature = geojson.Feature(geometry=polygon, properties=properties)
            features.append(feature)

    return geojson.FeatureCollection(features)

def json_serial(obj):
    """
    JSON serializer for non-standard objects.

    :param obj: Object to serialize
    :type obj: any
    :return: Float representation for Decimal objects
    :rtype: float
    :raises TypeError: If object type is not serializable
    """
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

def save_to_file(geojson_data, filename):
    """
    Save GeoJSON data to file.

    :param geojson_data: GeoJSON data to save
    :type geojson_data: geojson.FeatureCollection
    :param filename: Output file path
    :type filename: str
    """
    with open(filename, 'w') as outfile:
        json.dump(geojson_data, outfile, indent=2, default=json_serial)