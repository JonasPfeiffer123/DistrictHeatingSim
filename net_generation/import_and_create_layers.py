import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

from net_generation.simple_MST import generate_network_fl, generate_network_rl, create_offset_points

def import_osm_street_layer(osm_street_layer_geojson_file):
    try:
        layer = gpd.read_file(osm_street_layer_geojson_file)
        print("Layer erfolgreich geladen.")
        return layer
    except Exception as e:
        print(f"Fehler beim Laden des Layers: {e}")
        return None

def generate_lines(layer, distance, angle_degrees, df=None):
    lines = []
    attributes = []

    for point in layer.geometry:
        # Umwandlung von Shapely-Geometrie in Koordinaten
        original_point = (point.x, point.y)

        # Initialisiere alle Attribute mit Standardwerten oder None
        attr = {
            'Land': None,
            'Bundesland': None,
            'Stadt': None,
            'Adresse': None,
            'Wärmebedarf': None,
            'Gebäudetyp': None,
            'WW_Anteil': None,
            'Typ_Heizflächen': None,
            'VLT_max': None,
            'Steigung_Heizkurve': None,
            'RLT_max': None
        }

        if df is not None:
            # Ermittlung der Attribute basierend auf der Koordinate
            match = df[(df['UTM_X'] == original_point[0]) & (df['UTM_Y'] == original_point[1])]
            if not match.empty:
                attr['Land'] = match['Land'].iloc[0]
                attr['Bundesland'] = match['Bundesland'].iloc[0]
                attr['Stadt'] = match['Stadt'].iloc[0]
                attr['Adresse'] = match['Adresse'].iloc[0]
                attr['Wärmebedarf'] = match['Wärmebedarf'].iloc[0]
                attr['Gebäudetyp'] = match['Gebäudetyp'].iloc[0]
                attr['WW_Anteil'] = match['WW_Anteil'].iloc[0]
                attr['Typ_Heizflächen'] = match['Typ_Heizflächen'].iloc[0]
                attr['VLT_max'] = match['VLT_max'].iloc[0]
                attr['Steigung_Heizkurve'] = match['Steigung_Heizkurve'].iloc[0]
                attr['RLT_max'] = match['RLT_max'].iloc[0]

        offset_point = create_offset_points(point, distance, angle_degrees)
        line = LineString([point, offset_point])
        
        lines.append(line)
        attributes.append(attr)

    # Erstellung eines GeoDataFrames mit den Linien und Attributen
    lines_gdf = gpd.GeoDataFrame(attributes, geometry=lines)
    return lines_gdf

def load_layers(osm_street_layer_geojson_file, data_csv_file_name, x_coord, y_coord):
    try:
        # Laden des Straßen-Layers als GeoDataFrame
        street_layer = gpd.read_file(osm_street_layer_geojson_file)

        # Laden der Datenpunkte aus einer CSV-Datei als DataFrame
        data_df = pd.read_csv(data_csv_file_name, sep=';')
        # Umwandlung der DataFrame in GeoDataFrame
        data_layer = gpd.GeoDataFrame(data_df, geometry=gpd.points_from_xy(data_df.UTM_X, data_df.UTM_Y))

        # Erzeugung des Erzeugerstandortes als GeoDataFrame
        producer_location = gpd.GeoDataFrame(geometry=[Point(x_coord, y_coord)], crs="EPSG:4326")

        return street_layer, data_layer, producer_location, data_df
    
    except Exception as e:
        print(f"Fehler beim Laden der Layer: {e}")
        return None, None, None, None

def generate_and_export_layers(osm_street_layer_geojson_file_name, data_csv_file_name, x_coord, y_coord, base_path, fixed_angle=0, fixed_distance=1):
    street_layer, layer_points, layer_WEA, df = load_layers(osm_street_layer_geojson_file_name, data_csv_file_name, x_coord, y_coord)
    
    # Verwenden Sie die angepassten Funktionen, um die Linien zu generieren
    vl_hast = generate_lines(layer_points, fixed_distance, fixed_angle, df)
    vl_rl = generate_network_rl(layer_points, layer_WEA, fixed_distance, fixed_angle, street_layer)
    vl_vl = generate_network_fl(layer_points, layer_WEA, street_layer)
    vl_erzeugeranlagen = generate_lines(layer_WEA, fixed_distance, fixed_angle)

    # Festlegen des CRS auf EPSG:25833
    vl_hast = vl_hast.set_crs("EPSG:25833")
    vl_rl = vl_rl.set_crs("EPSG:25833")
    vl_vl = vl_vl.set_crs("EPSG:25833")
    vl_erzeugeranlagen = vl_erzeugeranlagen.set_crs("EPSG:25833")
    
    # Export der GeoDataFrames als GeoJSON
    vl_hast.to_file(f"{base_path}/Wärmenetz/HAST.geojson", driver="GeoJSON")
    vl_rl.to_file(f"{base_path}/Wärmenetz/Rücklauf.geojson", driver="GeoJSON")
    vl_vl.to_file(f"{base_path}/Wärmenetz/Vorlauf.geojson", driver="GeoJSON")
    vl_erzeugeranlagen.to_file(f"{base_path}/Wärmenetz/Erzeugeranlagen.geojson", driver="GeoJSON")

