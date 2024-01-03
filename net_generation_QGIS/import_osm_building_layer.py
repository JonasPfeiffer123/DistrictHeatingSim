from net_generation_QGIS.import_osm_data_geojson import download_osm_street_data
import geopandas as gpd
import pandas as pd
import numpy as np


def import_and_filter_building():
    # Hier setzen Sie Ihre Overpass-Abfrage ein
    overpass_query = """
    [out:json][timeout:25];
    area[name="Zittau"]->.area_0;
    (
    relation["building"](area.area_0);
    );
    (._;>;);
    out body;
    """
    # Ausgabedateiname für GeoJSON-Datei
    geojson_file = "C:/Users/username/heating_network_generation/net_generation_QGIS/Gebäude Zittau.geojson"

    # Download der Daten und Speichern als GeoJSON
    #download_osm_street_data(overpass_query, geojson_file)

    # Einlesen der GeoJSON-Datei
    gdf = gpd.read_file(geojson_file)
    gdf['full_address'] = gdf['addr:street'] + ' ' + gdf['addr:housenumber']


    ### Beleg 1 ###
    # Einlesen der CSV-Datei
    csv_file = "C:/Users/username/heating_network_generation/geocoding/data_output_Beleg1_ETRS89.csv"
    csv_df = pd.read_csv(csv_file, sep=';')

    # Liste der Adressen aus der CSV-Datei erstellen
    addresses_from_csv = csv_df['Adresse'].tolist()

    # Filtern der GeoJSON-Daten auf Basis der Adressen aus der CSV-Datei
    filtered_gdf = gdf[gdf['full_address'].isin(addresses_from_csv)]

    # Anzeigen der gefilterten GeoDataFrame
    filtered_gdf

    # Speichern der gefilterten GeoDataFrame
    filtered_gdf.to_file('C:/Users/username/heating_network_generation/net_generation_QGIS/Beispiel Beleg 1/gefilterte Gebäude Zittau Beleg 1.geojson', driver='GeoJSON')


    ### Beleg 2 ###
    # Einlesen der CSV-Datei
    csv_file = "C:/Users/username/heating_network_generation/geocoding/data_output_Beleg2_ETRS89.csv"
    csv_df = pd.read_csv(csv_file, sep=';')

    # Liste der Adressen aus der CSV-Datei erstellen
    addresses_from_csv = csv_df['Adresse'].tolist()

    # Filtern der GeoJSON-Daten auf Basis der Adressen aus der CSV-Datei
    filtered_gdf = gdf[gdf['full_address'].isin(addresses_from_csv)]

    # Anzeigen der gefilterten GeoDataFrame
    filtered_gdf

    # Speichern der gefilterten GeoDataFrame
    filtered_gdf.to_file('C:/Users/username/heating_network_generation/net_generation_QGIS/Beispiel Beleg 2/gefilterte Gebäude Zittau Beleg 2.geojson', driver='GeoJSON')

#import_and_filter_building()

def filter_building_data(geojson_file, output_file):
    # Einlesen der GeoJSON-Datei
    gdf = gpd.read_file(geojson_file)

    # Liste der Gebäudetypen, die ignoriert werden sollen
    ignore_types = ['ruins', 'greenhouse', 'shed', 'silo', 'slurry_tank', 
                    'toilets', 'hut', 'cabin', 'ger', 'static_caravan', 
                    'construction', 'cowshed', 'garage', 'garages', 'carport',
                    'farm_auxiliary', 'roof', 'digester']

    # Filtere Gebäude heraus, die ignorierten Typen entsprechen
    filtered_gdf = gdf[~gdf['building'].isin(ignore_types)]

    # Ausgabe der gefilterten Daten
    print(filtered_gdf['building'])

    # Exportiere die gefilterten Daten in eine neue GeoJSON-Datei
    filtered_gdf.to_file(output_file, driver='GeoJSON')

def calculate_building_data(geojson_file, output_file):
    # Einlesen der GeoJSON-Datei
    gdf = gpd.read_file(geojson_file)

    # Umrechnen der Koordinaten
    gdf = gdf.to_crs(epsg=25833)
    
    # Berechnen der Fläche jedes Gebäudes in Quadratmetern
    gdf['area_sqm'] = gdf['geometry'].area

    # Hinzufügen der Spalte für spezifischen Wärmebedarf mit Zufallszahlen zwischen 50 und 200
    gdf['spez. Wärmebedarf [kWh/m²*a]'] = np.random.uniform(50, 200, gdf.shape[0])

    # Hinzufügen der Spalte für die Anzahl der Geschosse (konstanter Wert 3)
    gdf['Anzahl Geschosse'] = 3

    # Berechnen des Jahreswärmebedarfs
    gdf['Jahreswärmebedarf [kWh/a]'] = gdf['spez. Wärmebedarf [kWh/m²*a]'] * gdf['Anzahl Geschosse'] * gdf['area_sqm']

    # Speichern des erweiterten GeoDataFrame in eine neue GeoJSON-Datei
    gdf.to_file(output_file, driver='GeoJSON')



#calculate_building_data('C:/Users/username/heating_network_generation/net_generation_QGIS/Beispiel Beleg 1/gefilterte Gebäude Zittau Beleg 1.geojson', 
#                        'C:/Users/username/heating_network_generation/net_generation_QGIS/Beispiel Beleg 1/gefilterte Gebäude Zittau Beleg 1 berechnet.geojson')
#calculate_building_data('C:/Users/username/heating_network_generation/net_generation_QGIS/Beispiel Beleg 2/gefilterte Gebäude Zittau Beleg 2.geojson', 
#                        'C:/Users/username/heating_network_generation/net_generation_QGIS/Beispiel Beleg 2/gefilterte Gebäude Zittau Beleg 2 berechnet.geojson')

#calculate_building_data('C:/Users/username/heating_network_generation/net_generation_QGIS/Gebäude Zittau.geojson', 
#                        'C:/Users/username/heating_network_generation/net_generation_QGIS/Gebäude Zittau berechnet.geojson')

filter_building_data('C:/Users/username/heating_network_generation/net_generation_QGIS/Gebäude Zittau.geojson',
                     'C:/Users/username/heating_network_generation/net_generation_QGIS/Gebäude Zittau gefiltert.geojson')

calculate_building_data('C:/Users/username/heating_network_generation/net_generation_QGIS/Gebäude Zittau gefiltert.geojson', 
                        'C:/Users/username/heating_network_generation/net_generation_QGIS/Gebäude Zittau gefiltert berechnet.geojson')