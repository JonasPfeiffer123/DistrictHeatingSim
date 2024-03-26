import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, box
from shapely.ops import unary_union, cascaded_union


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

def spatial_filter_with_polygon(lod_geojson_path, polygon_shapefile_path, output_geojson_path):
    # Polygon-Shapefile laden
    polygon_gdf = gpd.read_file(polygon_shapefile_path)
    # LOD-Daten laden
    lod_gdf = gpd.read_file(lod_geojson_path)

    # CRS anpassen
    polygon_gdf = polygon_gdf.to_crs(lod_gdf.crs)

    # Überprüfen der Gültigkeit und Reparieren von Polygon-Geometrien
    polygon_gdf['geometry'] = polygon_gdf['geometry'].buffer(0)

    # 2D-Geometrien oder gepufferte Version für die Identifizierung der Objekt-IDs verwenden
    lod_gdf_2d = lod_gdf.copy()
    lod_gdf_2d['geometry'] = lod_gdf_2d['geometry'].buffer(0)
    
    # Identifiziere Objekte, die vollständig innerhalb des Polygons liegen, basierend auf der 2D-Repräsentation
    ids_within_polygon = lod_gdf_2d[lod_gdf_2d.within(polygon_gdf.unary_union)]['ID'].unique()

    # Filtere die ursprünglichen LOD-Daten basierend auf den identifizierten IDs
    filtered_lod_gdf = lod_gdf[lod_gdf['ID'].isin(ids_within_polygon)]

    # Gefilterte Daten in einer neuen GeoJSON-Datei speichern
    filtered_lod_gdf.to_file(output_geojson_path, driver='GeoJSON')


def calculate_polygon_area_3d(polygon):
    """Berechnet die Fläche eines 3D-Polygons durch Zerlegung in Dreiecke."""
    if isinstance(polygon, Polygon):
        coords = list(polygon.exterior.coords)
        # Entferne den letzten Punkt, wenn er mit dem ersten identisch ist (geschlossene Polygone in Shapely).
        if coords[0] == coords[-1]:
            coords.pop()
            
        # Berechne die Fläche, indem Dreiecke verwendet werden.
        area = 0.0
        origin = coords[0]  # Wähle den ersten Punkt als Ursprung
        
        for i in range(1, len(coords) - 1):
            # Berechne die Fläche des Dreiecks, das vom Ursprung und zwei aufeinanderfolgenden Punkten gebildet wird.
            area += calculate_triangle_area_3d(origin, coords[i], coords[i+1])
            
        return area
    else:
        return None

def calculate_triangle_area_3d(p1, p2, p3):
    """Berechnet die Fläche eines Dreiecks im 3D-Raum mithilfe der Heron-Formel."""
    a = calculate_distance_3d(p1, p2)
    b = calculate_distance_3d(p2, p3)
    c = calculate_distance_3d(p3, p1)
    s = (a + b + c) / 2  # Semiperimeter
    return np.sqrt(s * (s - a) * (s - b) * (s - c))  # Heron-Formel

def calculate_distance_3d(point1, point2):
    """Berechnet die Distanz zwischen zwei Punkten im 3D-Raum."""
    return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2 + (point1[2] - point2[2])**2)

def calculate_area_3d_for_feature(geometry):
    """Berechnet die 3D-Fläche für ein einzelnes Feature."""
    total_area = 0
    if isinstance(geometry, Polygon):
        total_area = calculate_polygon_area_3d(geometry)
    elif isinstance(geometry, MultiPolygon):
        for polygon in geometry.geoms:
            total_area += calculate_polygon_area_3d(polygon)
    return total_area

def process_lod2(file_path):
    # Lade die GeoJSON-Datei
    gdf = gpd.read_file(file_path)

    # Untersuche die ersten Einträge, um die Struktur der Daten zu verstehen
    print(gdf.head())

    # Berechne die Fläche für Gebäudegrundflächen
    ground_geoms = gdf[gdf['Geometr_3D'] == 'Ground']
    ground_areas = ground_geoms.area
    print(f"Flächen der Gebäudegrundflächen: {ground_areas} m²")

    # Iteriere über jede Zeile im GeoDataFrame und berechne die Fläche für Wand- und Dachflächen
    for feature_type in ['Wall', 'Roof']:
        print(f"\nFlächen der {feature_type}-Flächen:")
        features = gdf[gdf['Geometr_3D'] == feature_type]
        for _, row in features.iterrows():
            area = calculate_area_3d_for_feature(row['geometry'])
            print(f"ID: {row['ID']}, Dachorient: {row.get('Dachorient', 'N/A')}, Dachneig: {row.get('Dachneig', 'N/A')}, Fläche: {area:.2f} m²")

    # Mapping von Parent-IDs zu Child-Geometrien erstellen
    parent_to_children = {}

    # Gehe durch jede Zeile im GeoDataFrame
    for idx, row in gdf.iterrows():
        parent_id = row['Obj_Parent']
        if parent_id:
            if parent_id not in parent_to_children:
                parent_to_children[parent_id] = []
            parent_to_children[parent_id].append(row['geometry'])

    print("\nSumme Außenwandflächen:")
    # Für jedes Parent-Objekt die Flächen der Child-Geometrien berechnen
    for parent_id, children_geometries in parent_to_children.items():
        # Anfangsfläche für die Wände und Closures des Parent-Objekts ist 0
        wall_area = 0

        # Durchlaufe alle untergeordneten Geometrien und summiere ihre Flächen
        for child_geom in children_geometries:
            # Finde die entsprechende Zeile im GeoDataFrame für die aktuelle Geometrie
            child_row = gdf[gdf['geometry'] == child_geom].iloc[0]

            # Führe die Flächenberechnung basierend auf dem Typ der Geometrie durch
            if child_row['Geometr_3D'] == 'Wall':
                wall_area += calculate_area_3d_for_feature(child_geom)

        print(f"Parent ID: {parent_id}, Wall Area: {wall_area:.2f} m²")

#plot3D()
#test()
# Pfadangaben
#lod_geojson_path = 'C:/Users/username/heating_network_generation/project_data/Beispiel Görlitz/lod2_33498_5666_2_sn.geojson'
lod_geojson_path = 'C:/Users/username/heating_network_generation/project_data/Bautzen/lod2_33458_5668_2_sn.geojson'
#polygon_shapefile_path = 'C:/Users/username/heating_network_generation/project_data/Beispiel Görlitz/Gebäudedaten/Quartier_Konzept_vereinfacht.shp'
polygon_shapefile_path = 'C:/Users/username/heating_network_generation/project_data/Bautzen/filter_polygon.shp'
#output_geojson_path = 'C:/Users/username/heating_network_generation/project_data/Beispiel Görlitz/Gebäudedaten/filtered_LOD_quartier.geojson'
output_geojson_path = 'C:/Users/username/heating_network_generation/project_data/Bautzen/filtered_LOD_quartier.geojson'
# Rufe die Funktion auf, um den Filterprozess zu starten
spatial_filter_with_polygon(lod_geojson_path, polygon_shapefile_path, output_geojson_path)

#file_path = 'C:/Users/username/heating_network_generation/project_data/Beispiel Görlitz/Gebäudedaten/filtered_LOD_quartier.geojson'
file_path = 'C:/Users/username/heating_network_generation/project_data/Bautzen/filtered_LOD_quartier.geojson'
process_lod2(file_path)