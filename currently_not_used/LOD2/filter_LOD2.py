import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry import box

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from matplotlib import cm

def plot3D():
    ### 1 ###
    # Daten generieren
    x = np.random.standard_normal(100)
    y = np.random.standard_normal(100)
    z = np.random.standard_normal(100)

    # Plot initialisieren
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')  # Diese Zeile direkt für 3D-Unterstützung verwenden

    # Scatter-Plot
    ax.scatter(x, y, z)

    # Titel und Achsenbeschriftungen
    ax.set_title('3D Scatter Plot')
    ax.set_xlabel('X Axis')
    ax.set_ylabel('Y Axis')
    ax.set_zlabel('Z Axis')

    plt.show()
    
    ### 2 ###
    # Gitter für die Plot-Daten generieren
    X = np.linspace(-5, 5, 100)
    Y = np.linspace(-5, 5, 100)
    X, Y = np.meshgrid(X, Y)
    Z = np.sin(np.sqrt(X**2 + Y**2))

    # Plot initialisieren
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')  # Diese Zeile direkt für 3D-Unterstützung verwenden

    # Oberflächenplot
    surf = ax.plot_surface(X, Y, Z, cmap=cm.coolwarm)

    # Titel und Achsenbeschriftungen
    ax.set_title('3D Surface Plot')
    ax.set_xlabel('X Axis')
    ax.set_ylabel('Y Axis')
    ax.set_zlabel('Z Axis')

    # Farblegende hinzufügen
    fig.colorbar(surf, shrink=0.5, aspect=5)

    plt.show()

def test():
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
    csv_file_path = 'C:/Users/username/heating_network_generation/project_data/Beispiel Zittau/Gebäudedaten/data_input.csv'
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

    # Gefilterte Daten in einer neuen geoJSON speichern
    filtered_lod_gdf.to_file(output_geojson_path, driver='GeoJSON')
    
def spatial_filter_with_polygon():
    # Pfadangaben
    lod_shapefile_path = 'C:/Users/username/heating_network_generation/project_data/Beispiel Görlitz/Gebäudedaten/lod2_33498_5666_2_sn_shape/lod2_33498_5666_2_sn.shp'
    polygon_shapefile_path = 'C:/Users/username/heating_network_generation/project_data/Beispiel Görlitz/Gebäudedaten/Quartier_Konzept_vereinfacht.shp'  # Pfad zur Polygon-Shapefile
    output_geojson_path = 'C:/Users/username/heating_network_generation/project_data/Beispiel Görlitz/Gebäudedaten/filtered_LOD_quartier.geojson'

    # Polygon-Shapefile laden
    polygon_gdf = gpd.read_file(polygon_shapefile_path)
    print(polygon_gdf.head())

    # LOD-Daten laden
    lod_gdf = gpd.read_file(lod_shapefile_path)
    print(lod_gdf.head())

    polygon_gdf = polygon_gdf.to_crs(lod_gdf.crs)

    fig, ax = plt.subplots()
    polygon_gdf.plot(ax=ax, color='red', alpha=0.5)
    lod_gdf.plot(ax=ax, color='blue', alpha=0.5)
    plt.show()

    # Überprüfen der Gültigkeit und Reparieren von Polygon-Geometrien
    polygon_gdf['geometry'] = polygon_gdf['geometry'].buffer(0)

    # Gegebenenfalls für LOD2-Daten wiederholen
    lod_gdf['geometry'] = lod_gdf['geometry'].buffer(0)

    # Räumlichen Filter anwenden: behalte nur Gebäude, die innerhalb des Polygons liegen
    filtered_lod_gdf = lod_gdf[lod_gdf.intersects(polygon_gdf.unary_union)]

    # Gefilterte Daten in einer neuen geoJSON speichern
    filtered_lod_gdf.to_file(output_geojson_path, driver='GeoJSON')
    lod_gdf.to_file("C:/Users/username/heating_network_generation/project_data/Beispiel Görlitz/Gebäudedaten/lod2_33498_5666_2_sn_shape/lod2_33498_5666_2_sn.geojson", driver='GeoJSON')

#plot3D()

#test()
    
# Rufe die Funktion auf, um den Filterprozess zu starten
spatial_filter_with_polygon()