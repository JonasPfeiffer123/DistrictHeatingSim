"""
OSM area-selection helpers (GUI-free).
======================================

Pure geometry helpers shared by the OSM street and building download dialogs:
resolve a user-selected area (city name, buildings CSV, GeoJSON polygon, or a
polygon drawn on the map) into a WGS84 shapely geometry, and build the OSMnx
highway filter string.

These were extracted from the two near-identical worker methods in
``gui/LeafletTab/osm_dialogs.py`` so the logic lives in one tested place and so the
download threads no longer touch the GUI: a missing CSV column now raises
``ValueError`` (caught by the download thread → error signal) instead of calling
``QMessageBox`` from a worker thread.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

# Rough metres-per-degree near central Europe, used to convert a metric buffer to
# the degree buffer applied in WGS84. Matches the original dialog code.
_METERS_PER_DEGREE = 111000.0

# Area-type labels (must match the dialog combo box entries).
AREA_CITY = "Stadt/Ortsname"
AREA_CSV = "Bereich um Gebäude aus CSV"
AREA_GEOJSON = "Polygon aus GeoJSON"
AREA_DRAWN = "Polygon auf Karte zeichnen"


def build_highway_filter(selected_types) -> str:
    """
    Build an OSMnx ``custom_filter`` string from selected highway types.

    :param selected_types: Highway type keys (e.g. ``["primary", "residential"]``).
    :type selected_types: list[str]
    :return: OSMnx filter, e.g. ``'["highway"~"primary|residential"]'``; with no
        types selected, the unrestricted ``'["highway"]'``.
    :rtype: str
    """
    if selected_types:
        types_str = "|".join(selected_types)
        return f'["highway"~"{types_str}"]'
    return '["highway"]'


def polygon_from_csv(csv_file, project_crs, buffer_m):
    """
    Build a buffered WGS84 polygon around building points from a CSV file.

    :param csv_file: Path to a ``;``-delimited CSV with ``UTM_X``/``UTM_Y`` columns.
    :type csv_file: str
    :param project_crs: CRS of the CSV coordinates (e.g. ``"EPSG:25833"``).
    :type project_crs: str
    :param buffer_m: Buffer radius around the points, in metres.
    :type buffer_m: float
    :return: WGS84 (EPSG:4326) polygon covering the buffered points.
    :rtype: shapely.geometry.base.BaseGeometry
    :raises ValueError: If the CSV lacks ``UTM_X``/``UTM_Y`` columns.
    """
    import geopandas as gpd
    import pandas as pd

    df = pd.read_csv(csv_file, delimiter=';')
    if 'UTM_X' not in df.columns or 'UTM_Y' not in df.columns:
        raise ValueError("CSV muss 'UTM_X' und 'UTM_Y' Spalten enthalten.")

    geometry = gpd.points_from_xy(df['UTM_X'], df['UTM_Y'])
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=project_crs)

    # Convert to WGS84 and buffer in degrees (approximate, matches original code).
    gdf_wgs84 = gdf.to_crs('EPSG:4326')
    buffer_deg = buffer_m / _METERS_PER_DEGREE
    return gdf_wgs84.unary_union.buffer(buffer_deg)


def polygon_from_geojson(geojson_file):
    """
    Read a polygon GeoJSON file and return it as a single WGS84 geometry.

    :param geojson_file: Path to a GeoJSON file containing one or more polygons.
    :type geojson_file: str
    :return: WGS84 (EPSG:4326) union of the file's geometries.
    :rtype: shapely.geometry.base.BaseGeometry
    """
    import geopandas as gpd

    gdf = gpd.read_file(geojson_file)
    if gdf.crs != 'EPSG:4326':
        gdf = gdf.to_crs('EPSG:4326')
    return gdf.unary_union


def resolve_area_polygon(area_params, buffer_m):
    """
    Resolve an area-selection parameter dict to a WGS84 polygon.

    Dispatches on ``area_params['area_type']``: a buildings CSV (buffered by
    ``buffer_m``), a GeoJSON polygon file, or a polygon drawn on the map. The
    city-name area type produces no polygon (the caller downloads by place name).

    :param area_params: Area-selection parameters with at least ``area_type`` and
        the file path for the selected type (``csv_file`` / ``polygon_file`` /
        ``drawn_polygon_file``) plus ``project_crs`` for CSV.
    :type area_params: dict
    :param buffer_m: Buffer radius (metres) applied for the CSV area type.
    :type buffer_m: float
    :return: WGS84 polygon for the selected area.
    :rtype: shapely.geometry.base.BaseGeometry
    :raises ValueError: For the city-name or an unknown area type (no polygon).
    """
    area_type = area_params['area_type']

    if area_type == AREA_CSV:
        return polygon_from_csv(
            area_params['csv_file'],
            area_params.get('project_crs', 'EPSG:25833'),
            buffer_m,
        )
    if area_type == AREA_GEOJSON:
        return polygon_from_geojson(area_params['polygon_file'])
    if area_type == AREA_DRAWN:
        return polygon_from_geojson(area_params['drawn_polygon_file'])

    raise ValueError(f"Kein Polygon für Bereichstyp: {area_type}")
