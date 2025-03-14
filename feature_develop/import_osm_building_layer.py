#from import_osm_data_geojson import download_data
import geopandas as gpd
import pandas as pd
import numpy as np


def import_and_filter_building():
    # This is where you insert your overpass query
    overpass_query = """
    [out:json][timeout:25];
    area[name="Zittau"]->.area_0;
    (
    relation["building"](area.area_0);
    way["building"](area.searchArea);
    );
    (._;>;);
    out body;
    """
    # Output filename for GeoJSON file
    geojson_file = "C:/Users/jp66tyda/heating_network_generation/net_generation_QGIS/Gebäude Zittau.geojson"
    # Download the data and save as GeoJSON
    #download_data(overpass_query, geojson_file)
    # Reading the GeoJSON file
    gdf = gpd.read_file(geojson_file)
    gdf['full_address'] = gdf['addr:street'] + ' ' + gdf['addr:housenumber']
    # Reading the CSV file
    csv_file = "C:/Users/jp66tyda/heating_network_generation/geocoding/data_output_Beleg1_ETRS89.csv"
    csv_df = pd.read_csv(csv_file, sep=';')
    # Create list of addresses from CSV file
    addresses_from_csv = csv_df['Adresse'].tolist()
    # Filter the GeoJSON data based on the addresses from the CSV file
    filtered_gdf = gdf[gdf['full_address'].isin(addresses_from_csv)]
    # Display the filtered GeoDataFrame
    filtered_gdf
    # Save the filtered GeoDataFrame
    filtered_gdf.to_file('C:/Users/jp66tyda/heating_network_generation/net_generation_QGIS/Beispiel Beleg 1/gefilterte Gebäude Zittau Beleg 1.geojson', driver='GeoJSON')

#import_and_filter_building()

def filter_building_data(geojson_file, output_file):
    # Reading the GeoJSON file
    gdf = gpd.read_file(geojson_file)

    # List of building types to ignore
    ignore_types = ['ruins', 'greenhouse', 'shed', 'silo', 'slurry_tank', 
                    'toilets', 'hut', 'cabin', 'ger', 'static_caravan', 
                    'construction', 'cowshed', 'garage', 'garages', 'carport',
                    'farm_auxiliary', 'roof', 'digester']

    # Filter out buildings that match ignored types
    filtered_gdf = gdf[~gdf['building'].isin(ignore_types)]

    # Output the filtered data
    print(filtered_gdf['building'])

    # Export the filtered data to a new GeoJSON file
    filtered_gdf.to_file(output_file, driver='GeoJSON')

def calculate_building_data(geojson_file, output_file):
    # Reading the GeoJSON file
    gdf = gpd.read_file(geojson_file)
    # Convert the coordinates
    gdf = gdf.to_crs(epsg=25833)
    # Calculate the area of ​​each building in square meters
    gdf['area_sqm'] = gdf['geometry'].area
    # Adding specific heat demand column with random numbers between 50 and 200
    gdf['spez. Wärmebedarf [kWh/m²*a]'] = np.random.uniform(50, 200, gdf.shape[0])
    # Add column for number of floors (constant value 3)
    gdf['Anzahl Geschosse'] = 3
    # Calculate the annual heat requirement
    gdf['Jahreswärmebedarf [kWh/a]'] = gdf['spez. Wärmebedarf [kWh/m²*a]'] * gdf['Anzahl Geschosse'] * gdf['area_sqm']
    # Save the extended GeoDataFrame to a new GeoJSON file
    gdf.to_file(output_file, driver='GeoJSON')

#filter_building_data('osm_data/output_buildings.geojson', 'osm_data/output_buildings_filtered.geojson')
#calculate_building_data('osm_data/output_buildings_filtered.geojson', 'osm_data/output_buildings_filtered_calculated')