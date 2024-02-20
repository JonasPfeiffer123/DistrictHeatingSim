import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon

# Funktion, um Polygone/MultiPolygone aus einer GeometryCollection zu extrahieren
def extract_polygons(geom):
    if geom.geom_type == 'Polygon':
        return geom
    elif geom.geom_type == 'MultiPolygon':
        return geom
    elif geom.geom_type == 'GeometryCollection':
        polys = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
        all_polygons = []
        for poly in polys:
            if isinstance(poly, Polygon):
                all_polygons.append(poly)
            elif isinstance(poly, MultiPolygon):
                for sub_poly in poly.geoms:
                    all_polygons.append(sub_poly)
        if all_polygons:
            return MultiPolygon(all_polygons)
    return None

# Pfadangaben
csv_file_path = 'C:/Users/username/heating_network_generation/project_data/Beispiel Zittau/Gebäudedaten/data_input_zi.csv'
osm_geojson_path = 'C:/Users/username/heating_network_generation/project_data/Beispiel Zittau/Raumanalyse/buildings_zittau.geojson'
lod_shapefile_path = 'H:/Arbeit/1 SMWK-NEUES Bearbeitung/LoD2_Shape/lod2_33486_5636_2_sn_shape/lod2_33486_5636_2_sn.shp'
output_geojson_path = 'filtered_LOD.geojson'

# OSM-Gebäudedaten laden und nach Adressen filtern
osm_gdf = gpd.read_file(osm_geojson_path)

# CSV mit Adressen einlesen und eine Liste der Zieladressen erstellen
df = pd.read_csv(csv_file_path, delimiter=';')
df['VollständigeAdresse'] = df['Stadt'] + ', ' + df['Adresse']
address_list = df['VollständigeAdresse'].unique().tolist()

# Filtern der OSM-Daten basierend auf der Adressliste
osm_gdf_filtered = osm_gdf[osm_gdf.apply(lambda x: f"{x['addr:city']}, {x['addr:street']} {x.get('addr:housenumber', '')}".strip() in address_list, axis=1)]

# LOD-Daten laden
lod_gdf = gpd.read_file(lod_shapefile_path)

# Räumlichen Join durchführen, um Übereinstimmungen zu finden (nur IDs extrahieren)
joined_gdf = gpd.sjoin(lod_gdf, osm_gdf_filtered, how='inner', predicate='intersects')

# IDs der übereinstimmenden LOD-Objekte extrahieren
matching_ids = joined_gdf.index.tolist()

# Original-LOD-Daten basierend auf den extrahierten IDs filtern
filtered_lod_gdf = lod_gdf[lod_gdf.index.isin(matching_ids)]

# Gefilterte Daten in einer neuen Shapefile speichern
filtered_lod_gdf.to_file(output_geojson_path, driver='GeoJSON')
