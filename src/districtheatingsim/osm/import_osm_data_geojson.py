"""
Filename: import_osm_data_geojson.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: Script with OSM download functionality.
"""

import overpy
import json
from decimal import Decimal
import geojson

def build_query(city_name, tags, element_type="way"):
    """
    Build an Overpass API query to download OSM data for a specific city and element type.

    Parameters
    ----------
    city_name : str
        Name of the city for which to download OSM data.
    tags : list of tuple
        List of (key, value) tuples to filter OSM elements.
    element_type : str, optional
        Type of OSM element to query. Can be "way" or "building". Default is "way".

    Returns
    -------
    str
        The Overpass API query string.

    Examples
    --------
    >>> build_query("Berlin", [("highway", "primary")], "way")
    '[out:json][timeout:25];\\narea[name="Berlin"]->.searchArea;\\n(\\nway["highway"="primary"](area.searchArea);\\n);\\n(._;>;);\\nout body;\\n'
    
    >>> build_query("Munich", [], "building")
    '[out:json][timeout:25];\\narea[name="Munich"]->.searchArea;\\n(\\nrelation["building"](area.searchArea);way["building"](area.searchArea);\\n);\\n(._;>;);\\nout body;\\n'
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
    Download OSM data using the Overpass API and convert it to GeoJSON format.

    Parameters
    ----------
    query : str
        The Overpass API query string.
    element_type : str
        Type of OSM element to process. Can be "way" or "building".

    Returns
    -------
    geojson.FeatureCollection
        A GeoJSON FeatureCollection containing the downloaded OSM data.

    Raises
    ------
    OverpassError
        If the Overpass API query fails or times out.
    
    Notes
    -----
    - For "way" elements, creates LineString geometries
    - For "building" elements, creates Polygon or MultiPolygon geometries
    - Automatically closes building polygons if they are not already closed
    - Preserves all OSM tags as properties in the GeoJSON features

    Examples
    --------
    >>> query = build_query("Berlin", [("highway", "primary")], "way")
    >>> geojson_data = download_data(query, "way")
    >>> len(geojson_data['features'])
    42
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
    JSON serializer for objects not serializable by default.

    This function is used as a default serializer for the json.dump() function
    to handle Decimal objects that are not JSON serializable by default.

    Parameters
    ----------
    obj : any
        The object to serialize.

    Returns
    -------
    float
        The serialized float representation of the object if it's a Decimal.

    Raises
    ------
    TypeError
        If the object type is not serializable.

    Examples
    --------
    >>> from decimal import Decimal
    >>> json_serial(Decimal('3.14'))
    3.14
    
    >>> json_serial("not_a_decimal")
    Traceback (most recent call last):
        ...
    TypeError: Object of type str is not JSON serializable
    """
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

def save_to_file(geojson_data, filename):
    """
    Save GeoJSON data to a file.

    Parameters
    ----------
    geojson_data : geojson.FeatureCollection
        The GeoJSON data to save.
    filename : str
        The file path where the GeoJSON data will be saved.

    Returns
    -------
    None

    Raises
    ------
    IOError
        If the file cannot be written to the specified location.
    PermissionError
        If there are insufficient permissions to write to the file.

    Examples
    --------
    >>> geojson_data = geojson.FeatureCollection([])
    >>> save_to_file(geojson_data, "output.geojson")
    
    Notes
    -----
    The file is saved with proper JSON indentation (2 spaces) and uses
    the json_serial function to handle Decimal objects.
    """
    with open(filename, 'w') as outfile:
        json.dump(geojson_data, outfile, indent=2, default=json_serial)