from import_osm_street_layer_geojson import download_osm_street_data
import geopandas as gpd
import pandas as pd

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
    
def calculate_building_area(geojson_file):
    gdf = gpd.read_file(geojson_file)
    #gdf = gdf.to_crs(epsg=3395)
    gdf = gdf.to_crs(epsg=25833)
    
    # Berechnen der Fläche jedes Gebäudes in Quadratmetern
    gdf['area_sqm'] = gdf['geometry'].area
    print(gdf['area_sqm'])



calculate_building_area('C:/Users/username/heating_network_generation/net_generation_QGIS/Beispiel Beleg 1/gefilterte Gebäude Zittau Beleg 1.geojson')
calculate_building_area('C:/Users/username/heating_network_generation/net_generation_QGIS/Beispiel Beleg 2/gefilterte Gebäude Zittau Beleg 2.geojson')