"""
Filename: lod2_dialogs.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-03-07
Description: Contains the Dialogs for the LOD2Tab. These are the LOD2DownloadDialog and FilterDialog.
"""

import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon, GeometryCollection

def convert_shapefiles_to_geojson(kommune_folder, geojson_folder, target_crs="EPSG:25833"):
    """Konvertiert alle Shapefiles in GeoJSON mit Transformation ins Ziel-CRS."""
    os.makedirs(geojson_folder, exist_ok=True)

    all_geojsons = []
    for root, _, files in os.walk(kommune_folder):
        for file in files:
            if file.endswith(".shp"):
                shp_path = os.path.join(root, file)
                try:
                    gdf = gpd.read_file(shp_path)

                    # Geometrie vereinheitlichen
                    def convert_geometry(geom):
                        if isinstance(geom, GeometryCollection):
                            polygons = [g for g in geom.geoms if isinstance(g, Polygon)]
                            return MultiPolygon(polygons) if len(polygons) > 1 else polygons[0] if polygons else None
                        elif isinstance(geom, Polygon):
                            return MultiPolygon([geom])
                        return geom

                    gdf["geometry"] = gdf["geometry"].apply(convert_geometry)
                    gdf = gdf[gdf["geometry"].notnull()]

                    # CRS setzen, falls nicht vorhanden
                    if gdf.crs is None:
                        gdf.set_crs(target_crs, inplace=True)

                    gdf = gdf.to_crs(target_crs)

                    # GeoJSON speichern
                    geojson_path = os.path.join(geojson_folder, f"{os.path.splitext(file)[0]}.geojson")
                    gdf.to_file(geojson_path, driver="GeoJSON")
                    all_geojsons.append(geojson_path)

                except Exception as e:
                    print(f"Fehler beim Konvertieren von {shp_path}: {e}")

    return all_geojsons


def merge_geojsons(geojson_folder, output_filename, target_crs="EPSG:25833"):
    """Fügt alle GeoJSONs einer Gemeinde zusammen."""
    all_gdfs = []
    for root, _, files in os.walk(geojson_folder):
        for file in files:
            if file.endswith(".geojson"):
                file_path = os.path.join(root, file)
                try:
                    gdf = gpd.read_file(file_path)
                    all_gdfs.append(gdf)
                except Exception as e:
                    print(f"Fehler beim Laden von {file_path}: {e}")

    if all_gdfs:
        merged_gdf = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True))
        merged_gdf = merged_gdf.to_crs(target_crs)
        merged_gdf.to_file(output_filename, driver="GeoJSON")
        print(f"GeoJSON gespeichert unter: {output_filename}")
    else:
        print("Keine GeoJSON-Dateien gefunden.")

# Beispielaufruf
if __name__ == "__main__":
    # Standardpfade (du kannst sie dynamisch setzen, falls nötig)
    EXTRACT_DIR = "extracted"
    GEOJSON_DIR = "geojson"
    TARGET_CRS = "EPSG:25833" # UTM Zone 33N

    landkreis = "Landkreis Görlitz"
    gemeinde = "Stadt Bad Muskau"
    kommune_folder = os.path.join(EXTRACT_DIR, f"{landkreis}_{gemeinde}")
    geojson_folder = os.path.join(GEOJSON_DIR, f"{landkreis}_{gemeinde}")

    # Schritt 1: Konvertiere Shapefiles zu GeoJSON
    convert_shapefiles_to_geojson(kommune_folder, geojson_folder, TARGET_CRS)

    # Schritt 2: Füge alle GeoJSONs zusammen
    merge_geojsons(geojson_folder, filename=f"{landkreis}_{gemeinde}_LOD2_data.geojson", target_crs=TARGET_CRS)