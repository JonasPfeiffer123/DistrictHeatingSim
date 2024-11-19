"""
Filename: 02_example_import_osm_data_geojson.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-18
Description: This script runs the OSM data import process to download street and building data.
The script imports the `build_query`, `download_data`, and `save_to_file` functions
from the `import_osm_data_geojson` module within the `districtheatingsim.osm` package
and executes them to download and save the OSM data.
Usage:
    Run this script directly to download and save the OSM data.
Functions:
    osm_street_query() -> None
        Downloads and saves OSM street data.
    osm_building_query() -> None
        Downloads and saves OSM building data.
Example:
    $ python 02_import_osm_data_geojson.py

"""

import traceback

from districtheatingsim.osm.import_osm_data_geojson import build_query, download_data, save_to_file

### OSM-Download von Straßendaten ###
def osm_street_query():
    city_name = "Zittau"
    tags = [
            ("highway", "primary"),
            ("highway", "secondary"),
            ("highway", "tertiary"),
            ("highway", "residential"),
            ("highway", "living_street")
        ]
    element_type = "way"

    query = build_query(city_name, tags, element_type)
    geojson_data = download_data(query, element_type)
    geojson_file_name = "examples\data\osm_street_data.geojson"

    save_to_file(geojson_data, geojson_file_name)
    print("Speichern der OSM-Straßendaten erfolgreich abgeschlossen.")

### OSM-Download von Gebäudedaten ###
def osm_building_query():
    city_name = "Zittau"
    tags = None
    element_type = "building"

    query = build_query(city_name, tags, element_type)
    geojson_data = download_data(query, element_type)
    geojson_file_name = "examples\data\osm_building_data.geojson"

    save_to_file(geojson_data, geojson_file_name)
    print("Speichern der OSM-Gebäudedaten erfolgreich abgeschlossen.")

if __name__ == '__main__':
    try:
        print("Running the OSM data import script.")

        osm_street_query()
        osm_building_query()

    except Exception as e:
        print("An error occurred:")
        print(traceback.format_exc())
        raise e