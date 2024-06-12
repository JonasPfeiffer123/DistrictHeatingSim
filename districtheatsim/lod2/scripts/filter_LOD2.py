import numpy as np
import pandas as pd
import geopandas as gpd

from shapely.geometry import Polygon, MultiPolygon, Point

from geopy.geocoders import Nominatim

def filter_LOD2_with_OSM_and_adress(csv_file_path, osm_geojson_path, lod_shapefile_path, output_geojson_path):
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


def filter_LOD2_with_coordinates(lod_geojson_path, csv_file_path, output_geojson_path):
    # CSV mit Adressen einlesen und eine Liste der Zieladressen erstellen
    df = pd.read_csv(csv_file_path, delimiter=';')

    # LOD-Daten laden
    lod_gdf = gpd.read_file(lod_geojson_path)

    # Erstellen einer Geopandas GeoDataFrame aus den CSV-Koordinaten
    geometry = [Point(xy) for xy in zip(df.UTM_X, df.UTM_Y)]
    csv_gdf = gpd.GeoDataFrame(df, geometry=geometry)
    csv_gdf.set_crs(lod_gdf.crs, inplace=True)

    # Filtern der LOD2-Daten basierend auf den Koordinaten in der CSV-Datei und "Ground" Geometrien
    parent_ids = set()
    ground_geometries = lod_gdf[lod_gdf['Geometr_3D'] == 'Ground']
    csv_gdf['parent_id'] = None

    for idx, csv_row in csv_gdf.iterrows():
        point = csv_row.geometry
        for ground_idx, ground_row in ground_geometries.iterrows():
            if point.within(ground_row['geometry']):
                parent_id = ground_row['ID']
                parent_ids.add(parent_id)
                csv_gdf.at[idx, 'parent_id'] = parent_id
                break

    # Alle Parent- und zugehörigen Child-Objekte übernehmen
    filtered_lod_gdf = lod_gdf[lod_gdf['ID'].isin(parent_ids) | lod_gdf['Obj_Parent'].isin(parent_ids)]

    # Koordinaten als separate Spalten hinzufügen
    csv_gdf['Koordinate_X'] = csv_gdf.geometry.x
    csv_gdf['Koordinate_Y'] = csv_gdf.geometry.y

    # Informationen aus der CSV zu den gefilterten LOD2-Daten hinzufügen
    filtered_lod_gdf = filtered_lod_gdf.merge(csv_gdf.drop(columns='geometry'), how='left', left_on='ID', right_on='parent_id')

    # Gefilterte Daten in einer neuen GeoJSON-Datei speichern
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

    # Initialisiere ein Dictionary, um die Ergebnisse für jedes Gebäude zu speichern
    building_info = {}

    for _, row in gdf.iterrows():
        # Benutze 'ID' als Fallback, wenn 'Obj_Parent' None ist
        parent_id = row['Obj_Parent'] if row['Obj_Parent'] is not None else row['ID']
        
        if parent_id not in building_info:
            building_info[parent_id] = {'Ground': [], 'Wall': [], 'Roof': [], 'H_Traufe': None, 'H_Boden': None,
                                        'Adresse': None, 'Stadt': None, 'Bundesland': None, 'Land': None, 'Koordinate_X': None, 'Koordinate_Y': None}

        # Extrahiere und speichere Geometrien und Höheninformationen
        if row['Geometr_3D'] in ['Ground', 'Wall', 'Roof']:
            building_info[parent_id][row['Geometr_3D']].append(row['geometry'])
        
        # Setze Höhen, falls noch nicht gesetzt oder aktualisiere, falls unterschiedlich (sollte theoretisch nicht passieren)
        if 'H_Traufe' in row and (building_info[parent_id]['H_Traufe'] is None or building_info[parent_id]['H_Traufe'] != row['H_Traufe']):
            building_info[parent_id]['H_Traufe'] = row['H_Traufe']
        if 'H_Boden' in row and (building_info[parent_id]['H_Boden'] is None or building_info[parent_id]['H_Boden'] != row['H_Boden']):
            building_info[parent_id]['H_Boden'] = row['H_Boden']

        # Überprüfe, ob Adressinformationen vorhanden sind
        if 'Adresse' in row and pd.notna(row['Adresse']):
            building_info[parent_id]['Adresse'] = row['Adresse']
            building_info[parent_id]['Stadt'] = row['Stadt']
            building_info[parent_id]['Bundesland'] = row['Bundesland']
            building_info[parent_id]['Land'] = row['Land']
            building_info[parent_id]['Koordinate_X'] = row['Koordinate_X']
            building_info[parent_id]['Koordinate_Y'] = row['Koordinate_Y']

    # Berechne die Flächen und Volumina für jedes Gebäude
    for parent_id, info in building_info.items():
        info['Ground_Area'] = sum(calculate_area_3d_for_feature(geom) for geom in info['Ground'])
        info['Wall_Area'] = sum(calculate_area_3d_for_feature(geom) for geom in info['Wall'])
        info['Roof_Area'] = sum(calculate_area_3d_for_feature(geom) for geom in info['Roof'])
        h_traufe = info['H_Traufe']
        h_boden = info['H_Boden']
        info['Volume'] = (h_traufe - h_boden) * info['Ground_Area'] if h_traufe and h_boden else None

    return building_info

def geocode(lat, lon):
    geolocator = Nominatim(user_agent="LOD2_heating_demand")  # Setze den user_agent auf den Namen deiner Anwendung
    location = geolocator.reverse((lat, lon), exactly_one=True)
    return location.address if location else "Adresse konnte nicht gefunden werden"

def calculate_centroid_and_geocode(building_info):
    for parent_id, info in building_info.items():
        if 'Ground' in info and info['Ground']:
            # Vereinigung aller Ground-Geometrien und Berechnung des Zentrums
            ground_union = gpd.GeoSeries(info['Ground']).unary_union
            centroid = ground_union.centroid

            # Erstellen eines GeoDataFrame für die Umrechnung
            gdf = gpd.GeoDataFrame([{'geometry': centroid}], crs="EPSG:25833")
            # Ergänzung der Koordinaten im building_info Dictionary
            info['Koordinate_X'] = gdf.geometry.iloc[0].x
            info['Koordinate_Y'] = gdf.geometry.iloc[0].y

            # Umrechnung von EPSG:25833 nach EPSG:4326
            gdf = gdf.to_crs(epsg=4326)

            # Zugriff auf den umgerechneten Punkt
            centroid_transformed = gdf.geometry.iloc[0]
            lat, lon = centroid_transformed.y, centroid_transformed.x

            # Geokodierung und Adressdaten extrahieren
            address_components = geocode(lat, lon)
            
            # Extrahiere die gewünschten Teile der Adresse
            land = address_components.split(", ")[6]
            bundesland = address_components.split(", ")[4]
            stadt = address_components.split(", ")[3]
            strasse = address_components.split(", ")[2]
            hausnummer = address_components.split(", ")[1]

            # Ergänzung der Adresse im building_info Dictionary
            info['Land'] = land
            info['Bundesland'] = bundesland
            info['Stadt'] = stadt
            info['Adresse'] = f"{strasse} {hausnummer}"

        else:
            print(f"Keine Ground-Geometrie für Gebäude {parent_id} gefunden. Überspringe.")
            info['Koordinaten'] = None
            info['Land'] = None
            info['Bundesland'] = None
            info['Stadt'] = None
            info['Adresse'] = None

    return building_info