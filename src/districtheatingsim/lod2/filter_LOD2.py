"""
Filename: filter_LOD2.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: Contains functions to filter LOD2 data.
"""

import numpy as np
import pandas as pd
import geopandas as gpd

from shapely.geometry import Polygon, MultiPolygon, Point

from geopy.geocoders import Nominatim

def filter_LOD2_with_OSM_and_adress(csv_file_path, osm_geojson_path, lod_shapefile_path, output_geojson_path):
    """
    Filters LOD2 data based on addresses in a CSV file and OSM GeoJSON data.

    Args:
        csv_file_path (str): Path to the CSV file containing addresses.
        osm_geojson_path (str): Path to the OSM GeoJSON file.
        lod_shapefile_path (str): Path to the LOD shapefile.
        output_geojson_path (str): Path to save the filtered LOD data as GeoJSON.

    Returns:
        None
    """
    osm_gdf = gpd.read_file(osm_geojson_path)
    df = pd.read_csv(csv_file_path, delimiter=';')
    df['VollständigeAdresse'] = df['Stadt'] + ', ' + df['Adresse']
    address_list = df['VollständigeAdresse'].unique().tolist()

    osm_gdf_filtered = osm_gdf[osm_gdf.apply(lambda x: f"{x['addr:city']}, {x['addr:street']} {x.get('addr:housenumber', '')}".strip() in address_list, axis=1)]
    lod_gdf = gpd.read_file(lod_shapefile_path)
    joined_gdf = gpd.sjoin(lod_gdf, osm_gdf_filtered, how='inner', predicate='intersects')

    matching_ids = joined_gdf.index.tolist()
    filtered_lod_gdf = lod_gdf[lod_gdf.index.isin(matching_ids)]

    filtered_lod_gdf.to_file(output_geojson_path, driver='GeoJSON')

def filter_LOD2_with_coordinates(lod_geojson_path, csv_file_path, output_geojson_path):
    """
    Filters LOD2 data based on coordinates in a CSV file.

    Args:
        lod_geojson_path (str): Path to the LOD GeoJSON file.
        csv_file_path (str): Path to the CSV file containing coordinates.
        output_geojson_path (str): Path to save the filtered LOD data as GeoJSON.

    Returns:
        None
    """
    df = pd.read_csv(csv_file_path, delimiter=';')
    lod_gdf = gpd.read_file(lod_geojson_path)

    geometry = [Point(xy) for xy in zip(df.UTM_X, df.UTM_Y)]
    csv_gdf = gpd.GeoDataFrame(df, geometry=geometry)
    csv_gdf.set_crs(lod_gdf.crs, inplace=True)

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

    filtered_lod_gdf = lod_gdf[lod_gdf['ID'].isin(parent_ids) | lod_gdf['Obj_Parent'].isin(parent_ids)]
    csv_gdf['Koordinate_X'] = csv_gdf.geometry.x
    csv_gdf['Koordinate_Y'] = csv_gdf.geometry.y

    filtered_lod_gdf = filtered_lod_gdf.merge(csv_gdf.drop(columns='geometry'), how='left', left_on='ID', right_on='parent_id')
    filtered_lod_gdf.to_file(output_geojson_path, driver='GeoJSON')

def spatial_filter_with_polygon(lod_geojson_path, polygon_shapefile_path, output_geojson_path):
    """
    Filters LOD2 data within a given polygon.

    Args:
        lod_geojson_path (str): Path to the LOD GeoJSON file.
        polygon_shapefile_path (str): Path to the polygon shapefile.
        output_geojson_path (str): Path to save the filtered LOD data as GeoJSON.

    Returns:
        None
    """
    polygon_gdf = gpd.read_file(polygon_shapefile_path)
    lod_gdf = gpd.read_file(lod_geojson_path)

    polygon_gdf = polygon_gdf.to_crs(lod_gdf.crs)
    polygon_gdf['geometry'] = polygon_gdf['geometry'].buffer(0)

    lod_gdf_2d = lod_gdf.copy()
    lod_gdf_2d['geometry'] = lod_gdf_2d['geometry'].buffer(0)
    
    ids_within_polygon = lod_gdf_2d[lod_gdf_2d.within(polygon_gdf.unary_union)]['ID'].unique()
    filtered_lod_gdf = lod_gdf[lod_gdf['ID'].isin(ids_within_polygon)]

    filtered_lod_gdf.to_file(output_geojson_path, driver='GeoJSON')
    print(f"Filtered LOD2 data saved to {output_geojson_path}")

def calculate_polygon_area_3d(polygon):
    """
    Calculates the area of a 3D polygon by decomposing it into triangles.

    Args:
        polygon (shapely.geometry.Polygon): The polygon to calculate the area for.

    Returns:
        float: The area of the polygon.
    """
    if isinstance(polygon, Polygon):
        coords = list(polygon.exterior.coords)
        if coords[0] == coords[-1]:
            coords.pop()
            
        area = 0.0
        origin = coords[0]
        
        for i in range(1, len(coords) - 1):
            area += calculate_triangle_area_3d(origin, coords[i], coords[i+1])
            
        return area
    else:
        return None

def calculate_triangle_area_3d(p1, p2, p3):
    """
    Calculates the area of a triangle in 3D space using Heron's formula.

    Args:
        p1 (tuple): The first point of the triangle.
        p2 (tuple): The second point of the triangle.
        p3 (tuple): The third point of the triangle.

    Returns:
        float: The area of the triangle.
    """
    a = calculate_distance_3d(p1, p2)
    b = calculate_distance_3d(p2, p3)
    c = calculate_distance_3d(p3, p1)
    s = (a + b + c) / 2

    if s * (s - a) * (s - b) * (s - c) < 0:
        print(f"Ungültige Dreiecksseitenlängen: a={a}, b={b}, c={c}")
        return 0.0

    return np.sqrt(max(s * (s - a) * (s - b) * (s - c), 0))

def calculate_distance_3d(point1, point2):
    """
    Calculates the distance between two points in 3D space.

    Args:
        point1 (tuple): The first point (x, y, z).
        point2 (tuple): The second point (x, y, z).

    Returns:
        float: The distance between the points.
    """
    return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2 + (point1[2] - point2[2])**2)

def calculate_area_3d_for_feature(geometry):
    """
    Calculates the 3D area for a single feature.

    Args:
        geometry (shapely.geometry.Geometry): The geometry to calculate the area for.

    Returns:
        float: The area of the geometry.
    """
    total_area = 0
    if isinstance(geometry, Polygon):
        total_area = calculate_polygon_area_3d(geometry)
    elif isinstance(geometry, MultiPolygon):
        for polygon in geometry.geoms:
            total_area += calculate_polygon_area_3d(polygon)
    return total_area

def calculate_area_from_wall_coordinates(wall_geometries):
    """
    Calculates the ground area from wall coordinates.

    Args:
        wall_geometries (list): List of wall geometries.

    Returns:
        float: The calculated ground area.
    """
    if not wall_geometries:
        return 0

    all_points = []
    for geom in wall_geometries:
        if isinstance(geom, Polygon):
            all_points.extend(list(geom.exterior.coords))
        elif isinstance(geom, MultiPolygon):
            for poly in geom.geoms:
                all_points.extend(list(poly.exterior.coords))

    if len(all_points) < 3:
        return 0

    ground_polygon = Polygon([(p[0], p[1]) for p in all_points])
    return ground_polygon.area

def process_lod2(file_path, STANDARD_VALUES):
    """
    Processes LOD2 data and calculates areas and volumes.

    Args:
        file_path (str): Path to the LOD2 file.
        STANDARD_VALUES (dict): Dictionary of standard values for building properties.

    Returns:
        dict: Dictionary with processed building information.
    """
    gdf = gpd.read_file(file_path)
    building_info = {}

    for _, row in gdf.iterrows():
        parent_id = row['Obj_Parent'] if row['Obj_Parent'] is not None else row['ID']
        
        if parent_id not in building_info:
            building_info[parent_id] = {
                'Ground': [], 'Wall': [], 'Roof': [], 'H_Traufe': None, 'H_Boden': None,
                'Adresse': None, 'Stadt': None, 'Bundesland': None, 'Land': None, 'Koordinate_X': None, 'Koordinate_Y': None,
                'Gebäudetyp': None, 'Subtyp': None, 'Typ': None, 'Gebäudezustand': None, 'ww_demand_kWh_per_m2': None, 
                'air_change_rate': None, 'Stockwerke': None, 'fracture_windows': None, 'fracture_doors': None, 
                'Normaußentemperatur': None, 'room_temp': None, 'max_air_temp_heating': None, 'Wärmebedarf': None, 'WW_Anteil': None,
                'Typ_Heizflächen': None, 'VLT_max': None, 'Steigung_Heizkurve': None, 'RLT_max': None,
                'wall_u': None, 'roof_u': None, 'window_u': None, 'door_u': None, 'ground_u': None
            }

        if row['Geometr_3D'] in ['Ground', 'Wall', 'Roof']:
            building_info[parent_id][row['Geometr_3D']].append(row['geometry'])
        
        if 'H_Traufe' in row and (building_info[parent_id]['H_Traufe'] is None or building_info[parent_id]['H_Traufe'] != row['H_Traufe']):
            building_info[parent_id]['H_Traufe'] = row['H_Traufe']
        if 'H_Boden' in row and (building_info[parent_id]['H_Boden'] is None or building_info[parent_id]['H_Boden'] != row['H_Boden']):
            building_info[parent_id]['H_Boden'] = row['H_Boden']

        if 'Adresse' in row and pd.notna(row['Adresse']):
            building_info[parent_id]['Adresse'] = row['Adresse']
            building_info[parent_id]['Stadt'] = row['Stadt']
            building_info[parent_id]['Bundesland'] = row['Bundesland']
            building_info[parent_id]['Land'] = row['Land']
            building_info[parent_id]['Koordinate_X'] = row['Koordinate_X']
            building_info[parent_id]['Koordinate_Y'] = row['Koordinate_Y']
        
        # Check for additional fields
        if 'Stockwerke' in row and pd.notna(row['Stockwerke']):
            building_info[parent_id]['Stockwerke'] = row['Stockwerke']
        if 'Gebäudetyp' in row and pd.notna(row['Gebäudetyp']):
            building_info[parent_id]['Gebäudetyp'] = row['Gebäudetyp']
        if 'Subtyp' in row and pd.notna(row['Subtyp']):
            building_info[parent_id]['Subtyp'] = normalize_subtype(row['Subtyp'])
        if 'Typ' in row and pd.notna(row['Typ']):
            building_info[parent_id]['Typ'] = row['Typ']
        if 'Gebäudezustand' in row and pd.notna(row['Gebäudezustand']):
            building_info[parent_id]['Gebäudezustand'] = row['Gebäudezustand']
        if 'ww_demand_kWh_per_m2' in row and pd.notna(row['ww_demand_kWh_per_m2']):
            building_info[parent_id]['ww_demand_kWh_per_m2'] = row['ww_demand_kWh_per_m2']
        if 'air_change_rate' in row and pd.notna(row['air_change_rate']):
            building_info[parent_id]['air_change_rate'] = row['air_change_rate']
        if 'fracture_windows' in row and pd.notna(row['fracture_windows']):
            building_info[parent_id]['fracture_windows'] = row['fracture_windows']
        if 'fracture_doors' in row and pd.notna(row['fracture_doors']):
            building_info[parent_id]['fracture_doors'] = row['fracture_doors']
        if 'Normaußentemperatur' in row and pd.notna(row['Normaußentemperatur']):
            building_info[parent_id]['Normaußentemperatur'] = row['Normaußentemperatur']
        if 'room_temp' in row and pd.notna(row['room_temp']):
            building_info[parent_id]['room_temp'] = row['room_temp']
        if 'max_air_temp_heating' in row and pd.notna(row['max_air_temp_heating']):
            building_info[parent_id]['max_air_temp_heating'] = row['max_air_temp_heating']
        if 'Wärmebedarf' in row and pd.notna(row['Wärmebedarf']):
            building_info[parent_id]['Wärmebedarf'] = row['Wärmebedarf']
        if 'WW_Anteil' in row and pd.notna(row['WW_Anteil']):
            building_info[parent_id]['WW_Anteil'] = row['WW_Anteil']

        # New fields
        if 'Typ_Heizflächen' in row and pd.notna(row['Typ_Heizflächen']):
            building_info[parent_id]['Typ_Heizflächen'] = row['Typ_Heizflächen']
        if 'VLT_max' in row and pd.notna(row['VLT_max']):
            building_info[parent_id]['VLT_max'] = row['VLT_max']
        if 'Steigung_Heizkurve' in row and pd.notna(row['Steigung_Heizkurve']):
            building_info[parent_id]['Steigung_Heizkurve'] = row['Steigung_Heizkurve']
        if 'RLT_max' in row and pd.notna(row['RLT_max']):
            building_info[parent_id]['RLT_max'] = row['RLT_max']

        # U-Werte
        if 'wall_u' in row and pd.notna(row['wall_u']):
            building_info[parent_id]['wall_u'] = row['wall_u']
        if 'roof_u' in row and pd.notna(row['roof_u']):
            building_info[parent_id]['roof_u'] = row['roof_u']
        if 'window_u' in row and pd.notna(row['window_u']):
            building_info[parent_id]['window_u'] = row['window_u']
        if 'door_u' in row and pd.notna(row['door_u']):
            building_info[parent_id]['door_u'] = row['door_u']
        if 'ground_u' in row and pd.notna(row['ground_u']):
            building_info[parent_id]['ground_u'] = row['ground_u']

    for parent_id, info in building_info.items():
        info['Ground_Area'] = sum(calculate_area_3d_for_feature(geom) for geom in info['Ground'])
        info['Wall_Area'] = sum(calculate_area_3d_for_feature(geom) for geom in info['Wall'])
        info['Roof_Area'] = sum(calculate_area_3d_for_feature(geom) for geom in info['Roof'])

        if not info['Ground_Area'] or np.isnan(info['Ground_Area']):
            info['Ground_Area'] = calculate_area_from_wall_coordinates(info['Wall'])

        h_traufe = info['H_Traufe']
        h_boden = info['H_Boden']
        if h_traufe and h_boden:
            info['Volume'] = (h_traufe - h_boden) * info['Ground_Area']
        else:
            if info['Stockwerke'] and info['Ground_Area']:
                durchschnittliche_stockwerkshoehe = 3.0
                info['Volume'] = info['Stockwerke'] * durchschnittliche_stockwerkshoehe * info['Ground_Area']
            else:
                info['Volume'] = None

        for key, value in STANDARD_VALUES.items():
            if key not in info or info[key] is None:
                info[key] = value

    return building_info

def normalize_subtype(subtype):
    """
    Normalize the subtype to a consistent string format.

    Args:
        subtype (str/int/float): The subtype value.

    Returns:
        str: The normalized subtype value as a string.
    """
    subtype_str = str(int(float(subtype)))  # Convert to int first to handle float values like 3.0
    return subtype_str.zfill(2)  # Ensure the subtype has two digits

def geocode(lat, lon):
    """
    Geocodes latitude and longitude to an address.

    Args:
        lat (float): Latitude.
        lon (float): Longitude.

    Returns:
        str: Address.
    """
    geolocator = Nominatim(user_agent="LOD2_heating_demand")
    location = geolocator.reverse((lat, lon), exactly_one=True)
    return location.address if location else "Adresse konnte nicht gefunden werden"

def calculate_centroid_and_geocode(building_info):
    """
    Calculates the centroid and geocodes the building information.

    Args:
        building_info (dict): Dictionary with building information.

    Returns:
        dict: Updated building information with centroid and address.
    """
    for parent_id, info in building_info.items():
        if 'Ground' in info and info['Ground']:
            ground_union = gpd.GeoSeries(info['Ground']).unary_union
            centroid = ground_union.centroid

            gdf = gpd.GeoDataFrame([{'geometry': centroid}], crs="EPSG:25833")
            info['Koordinate_X'] = gdf.geometry.iloc[0].x
            info['Koordinate_Y'] = gdf.geometry.iloc[0].y

            gdf = gdf.to_crs(epsg=4326)
            centroid_transformed = gdf.geometry.iloc[0]
            lat, lon = centroid_transformed.y, centroid_transformed.x

            address_components = geocode(lat, lon)

            # Überprüfen, ob die Adresse genügend Komponenten hat
            address_parts = address_components.split(", ")
            address_parts = address_parts[::-1]  # Reverse the list to assign from the end

            land = address_parts[0] if len(address_parts) > 0 else None
            bundesland = address_parts[1] if len(address_parts) > 1 else None
            plz = address_parts[2] if len(address_parts) > 2 else None
            stadt = address_parts[3] if len(address_parts) > 3 else None
            stadtteil = address_parts[4] if len(address_parts) > 4 else None
            strasse = address_parts[5] if len(address_parts) > 5 else None
            hausnummer = address_parts[6] if len(address_parts) > 6 else None

            info['Land'] = land
            info['Bundesland'] = bundesland
            info['PLZ'] = plz
            info['Stadt'] = stadt
            info['Stadtteil'] = stadtteil
            info['Adresse'] = f"{strasse} {hausnummer}" if strasse and hausnummer else None

        else:
            print(f"Keine Ground-Geometrie für Gebäude {parent_id} gefunden. Überspringe.")
            info['Koordinaten'] = None
            info['Land'] = None
            info['Bundesland'] = None
            info['PLZ'] = None
            info['Stadt'] = None
            info['Stadtteil'] = None
            info['Adresse'] = None

    return building_info

def calculate_normal_and_angles(roof_geom):
    """
    Calculate the normal vector, slope (inclination), azimuth (orientation),
    and area of each polygon within a MultiPolygon geometry.

    Args:
        roof_geom (shapely.geometry.Polygon or shapely.geometry.MultiPolygon): 
            The geometry of the roof, which can be either a Polygon or MultiPolygon.

    Returns:
        list of tuples: A list where each tuple contains the normal vector, the slope in degrees,
                        the azimuth in degrees, and the area of each polygon.
    """

    def calculate_single_polygon(polygon):
        """Helper function to calculate properties for a single polygon."""
        coords = list(polygon.exterior.coords)
        if len(coords) < 3:
            return None, None, None, None

        # Berechnung des Normalenvektors für die ersten drei Punkte
        p1 = np.array(coords[0])
        p2 = np.array(coords[1])
        p3 = np.array(coords[2])
        v1 = p2 - p1
        v2 = p3 - p1
        normal = np.cross(v1, v2)
        normal = normal / np.linalg.norm(normal)
        
        # Neigungswinkel
        inclination = np.degrees(np.arccos(normal[2]))
        
        # Azimutwinkel
        azimuth = np.degrees(np.arctan2(normal[1], normal[0]))

        # Fläche des Polygons
        area = polygon.area

        return normal, inclination, azimuth, area

    results = []

    if isinstance(roof_geom, MultiPolygon):
        # Iterate over each polygon in the MultiPolygon
        for polygon in roof_geom.geoms:
            result = calculate_single_polygon(polygon)
            if result:
                results.append(result)

    elif isinstance(roof_geom, Polygon):
        # Handle the case where the geometry is just a single Polygon
        result = calculate_single_polygon(roof_geom)
        if result:
            results.append(result)

    return results

def process_roof(file_path):
    """
    Processes LOD2 data and calculates roof area, slope, and orientation for PV calculation,
    including wall geometries.
    """
    gdf = gpd.read_file(file_path)

    building_info = {}

    for _, row in gdf.iterrows():
        parent_id = row['Obj_Parent'] if 'Obj_Parent' in row and row['Obj_Parent'] is not None else row['ID']
        
        if parent_id not in building_info:
            building_info[parent_id] = {
                'Ground': [], 'Wall': [], 'Roofs': [],
                'Koordinate_X': None, 'Koordinate_Y': None,
                'Adresse': None, 'Stadt': None, 'Bundesland': None, 'Land': None
            }

        if row['Geometr_3D'] == 'Ground':
            building_info[parent_id]['Ground'].append(row['geometry'])
        elif row['Geometr_3D'] == 'Wall':
            building_info[parent_id]['Wall'].append(row['geometry'])
        elif row['Geometr_3D'] == 'Roof':
            # Berechnung von Normalvektor, Dachneigung und -ausrichtung für jedes Teilpolygon im Dachsegment
            roof_segments = calculate_normal_and_angles(row['geometry'])
            
            for normal, roof_slope, roof_orientation, area in roof_segments:
                # Speicherung der Ergebnisse in einer Liste von Dächern
                roof_data = {
                    'geometry': row['geometry'],
                    'Roof_Slope': roof_slope,
                    'Roof_Orientation': roof_orientation,
                    'Area': area,
                    'Normal_Vector': normal,
                    'parent_id': parent_id  # Hinzufügen des parent_id
                }
                building_info[parent_id]['Roofs'].append(roof_data)

        if 'Adresse' in row and pd.notna(row['Adresse']):
            building_info[parent_id]['Adresse'] = row['Adresse']
            building_info[parent_id]['Stadt'] = row['Stadt']
            building_info[parent_id]['Bundesland'] = row['Bundesland']
            building_info[parent_id]['Land'] = row['Land']
            building_info[parent_id]['Koordinate_X'] = row['Koordinate_X']
            building_info[parent_id]['Koordinate_Y'] = row['Koordinate_Y']

    for parent_id, info in building_info.items():
        info['Ground_Area'] = sum(calculate_area_3d_for_feature(geom) for geom in info['Ground'])
        info['Wall_Area'] = sum(calculate_area_3d_for_feature(geom) for geom in info['Wall'])
        info['Roof_Area'] = sum(roof['Area'] for roof in info['Roofs'])

        if not info['Ground_Area'] or np.isnan(info['Ground_Area']):
            info['Ground_Area'] = calculate_area_from_wall_coordinates(info['Ground'])

    return building_info
