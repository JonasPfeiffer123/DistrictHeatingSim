"""
Filename: simple_osm_test.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
Description: Script for testing the OSM functions.

"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import geopandas as gpd

from osm.import_osm_data_geojson import build_query, download_data, save_to_file
from osm.Wärmeversorgungsgebiete import clustering_districts_hdbscan, postprocessing_hdbscan, allocate_overlapping_area

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
    save_to_file(geojson_data, "tests\data\osm_street_data.geojson")
    print("Speichern der OSM-Straßendaten erfolgreich abgeschlossen.")

### OSM-Download von Gebäudedaten ###
def osm_building_query():
    city_name = "Zittau"
    tags = None
    element_type = "building"
    query = build_query(city_name, tags, element_type)
    geojson_data = download_data(query, element_type)
    save_to_file(geojson_data, "tests\data\osm_building_data.geojson")
    print("Speichern der OSM-Gebäudedaten erfolgreich abgeschlossen.")

### Clustering in Wärmeversorgungsgebiete ###
def osm_clustering():
    # Load your GeoJSON dataset
    gdf = gpd.read_file("tests\data\osm_building_data.geojson", driver='GeoJSON').to_crs(epsg=25833)

    # Funktion um Beispielhaft Gebäudedaten zuzuweisen, die zur Klassifizierung benötigt werden
    def calculate_building_data(gdf, output_filename):
            # Calculate the area of ​​each building in square meters
            gdf['area_sqm'] = gdf['geometry'].area
            # Adding specific heat demand column with random numbers between 50 and 200
            gdf['spez. Wärmebedarf [kWh/m²*a]'] = np.random.uniform(50, 200, gdf.shape[0])
            # Add column for number of floors (constant value 3)
            gdf['Anzahl Geschosse'] = 3
            # Calculate the annual heat requirement
            gdf['Jahreswärmebedarf [kWh/a]'] = gdf['spez. Wärmebedarf [kWh/m²*a]'] * gdf['Anzahl Geschosse'] * gdf['area_sqm']
            # Save the extended GeoDataFrame to a new GeoJSON file
            gdf.to_file(output_filename, driver='GeoJSON')

            return gdf

    gdf = calculate_building_data(gdf, 'tests\data\osm_building_data_calculated.geojson')
    print("Berechnung der Gebäudedaten erfolgreich abgeschlossen.")

    quarters = clustering_districts_hdbscan(gdf)
    #Export result as GeoJSON file
    quarters.to_file('tests\data\quartiere_hdbscan.geojson', driver='GeoJSON')
    print("Clustering der Quartiere mit hdbscan erfolgreich abgeschlossen.")

    # Merge neighborhoods with the same type of supply
    quarters_joined = postprocessing_hdbscan(quarters)
    # Saving the post-processed data
    quarters_joined.to_file('tests\data\quartiere_postprocessed.geojson', driver='GeoJSON')
    print("Postprocessing der Quartiere erfolgreich abgeschlossen.")

    # Apply allocate_overlapping_area approach
    quarters_overlayed = allocate_overlapping_area(quarters_joined)
    quarters_overlayed.to_file('tests\data\quartiere_allocated.geojson', driver='GeoJSON')
    print("Allocating overlapping areas der Quartiere erfolgreich abgeschlossen.")


osm_street_query()
osm_building_query()
osm_clustering()