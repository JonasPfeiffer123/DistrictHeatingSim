"""
Elevation data utilities for district heating network generation.

Provides functions to query terrain elevation (Höhe über NN) for UTM-projected
coordinates, either from a local GeoTIFF digital elevation model (DGM) or via
the OpenTopoData REST API as an online fallback.  The elevation values are then
written as Z-coordinates into Shapely/GeoPandas geometries so that pandapipes
can use them as ``height_m`` on network junctions.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import logging
from typing import Dict, List, Optional, Tuple

import geopandas as gpd
import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, Point

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _transform_utm_to_wgs84(points_utm: List[Tuple[float, float]],
                              crs_utm: str) -> List[Tuple[float, float]]:
    """Transform UTM points to (lon, lat) WGS84 tuples.

    :param points_utm: List of (x, y) coordinate pairs in *crs_utm*
    :param crs_utm: EPSG string of the projected input CRS (e.g. ``"EPSG:25833"``)
    :return: List of (lon, lat) WGS84 pairs
    """
    transformer = Transformer.from_crs(crs_utm, "EPSG:4326", always_xy=True)
    return [transformer.transform(x, y) for x, y in points_utm]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def query_elevation_from_geotiff(points_utm: List[Tuple[float, float]],
                                  dem_path: str,
                                  crs_utm: str = "EPSG:25833") -> List[float]:
    """Read terrain elevations from a local GeoTIFF digital elevation model.

    Uses ``rasterio`` to sample the raster at the given projected coordinates.
    The raster CRS is detected automatically; coordinates are re-projected if
    the raster CRS differs from *crs_utm*.

    :param points_utm: List of (x, y) coordinate pairs in the projected CRS
    :type points_utm: List[Tuple[float, float]]
    :param dem_path: File system path to the GeoTIFF DEM
    :type dem_path: str
    :param crs_utm: EPSG string of the input CRS (default ``"EPSG:25833"``)
    :type crs_utm: str
    :return: Elevation in metres above sea level for each input point.
             Points that fall outside the raster extent are set to ``0.0``.
    :rtype: List[float]
    :raises ImportError: If ``rasterio`` is not installed
    :raises FileNotFoundError: If *dem_path* does not exist
    """
    try:
        import rasterio
        from rasterio.crs import CRS as RasterioCRS
    except ImportError as exc:
        raise ImportError(
            "rasterio is required for GeoTIFF elevation lookup. "
            "Install it with: pip install rasterio"
        ) from exc

    with rasterio.open(dem_path) as src:
        dem_crs = src.crs.to_string()

        # Re-project input coords to raster CRS if necessary
        if dem_crs != RasterioCRS.from_string(crs_utm).to_string():
            transformer = Transformer.from_crs(crs_utm, dem_crs, always_xy=True)
            query_coords = [transformer.transform(x, y) for x, y in points_utm]
        else:
            query_coords = points_utm

        elevations: List[float] = []
        nodata = src.nodata

        for x, y in query_coords:
            try:
                row, col = src.index(x, y)
                value = src.read(1)[row, col]
                if nodata is not None and np.isclose(value, nodata):
                    logger.warning("DEM nodata at (%.1f, %.1f) — using 0.0 m", x, y)
                    elevations.append(0.0)
                else:
                    elevations.append(float(value))
            except Exception:
                logger.warning("Point (%.1f, %.1f) outside DEM extent — using 0.0 m", x, y)
                elevations.append(0.0)

    return elevations


def query_elevation_from_api(points_utm: List[Tuple[float, float]],
                              crs_utm: str = "EPSG:25833",
                              dataset: str = "eudem25m") -> List[float]:
    """Query terrain elevations from the OpenTopoData REST API (online fallback).

    Transforms UTM coordinates to WGS84, then queries
    ``https://api.opentopodata.org/v1/<dataset>`` in batches of 100.
    No API key required for the public instance.

    :param points_utm: List of (x, y) coordinate pairs in the projected CRS
    :type points_utm: List[Tuple[float, float]]
    :param crs_utm: EPSG string of the input CRS (default ``"EPSG:25833"``)
    :type crs_utm: str
    :param dataset: OpenTopoData dataset name.
                    ``"eudem25m"`` (Europe, 25 m) is used by default.
                    Other options: ``"srtm30m"``, ``"aster30m"``.
    :type dataset: str
    :return: Elevation in metres above sea level for each input point.
             Returns ``0.0`` for points that could not be resolved.
    :rtype: List[float]
    :raises requests.exceptions.RequestException: On network errors
    """
    import requests

    wgs84_pts = _transform_utm_to_wgs84(points_utm, crs_utm)
    elevations: List[float] = [0.0] * len(points_utm)

    batch_size = 100
    url = f"https://api.opentopodata.org/v1/{dataset}"

    for start in range(0, len(wgs84_pts), batch_size):
        batch = wgs84_pts[start:start + batch_size]
        locations = "|".join(f"{lat},{lon}" for lon, lat in batch)

        try:
            resp = requests.get(url, params={"locations": locations}, timeout=30)
            resp.raise_for_status()
            results = resp.json().get("results", [])

            for j, result in enumerate(results):
                elev = result.get("elevation")
                if elev is not None:
                    elevations[start + j] = float(elev)
                else:
                    logger.warning("No elevation returned for point %d — using 0.0 m",
                                   start + j)
        except Exception as exc:
            logger.error("OpenTopoData API error for batch starting at %d: %s", start, exc)

    return elevations


def build_elevation_lookup(points_utm: List[Tuple[float, float]],
                            dem_path: Optional[str],
                            crs_utm: str = "EPSG:25833") -> Dict[Tuple[float, float], float]:
    """Build a ``{(x, y): z_m}`` dictionary for a list of UTM points.

    Uses the local GeoTIFF if *dem_path* is provided and ``rasterio`` is
    available; otherwise falls back to the OpenTopoData API.  If neither
    source is reachable, returns a dictionary with ``0.0`` for every point
    and emits a warning.

    :param points_utm: Unique (x, y) coordinate pairs in the projected CRS
    :type points_utm: List[Tuple[float, float]]
    :param dem_path: Path to a local GeoTIFF DEM, or ``None`` to force API
    :type dem_path: Optional[str]
    :param crs_utm: EPSG string of the input CRS
    :type crs_utm: str
    :return: Mapping from (x, y) to elevation [m]
    :rtype: Dict[Tuple[float, float], float]
    """
    if not points_utm:
        return {}

    elevations: Optional[List[float]] = None

    if dem_path:
        try:
            elevations = query_elevation_from_geotiff(points_utm, dem_path, crs_utm)
            logger.info("Elevation lookup from GeoTIFF (%d points)", len(points_utm))
        except Exception as exc:
            logger.warning("GeoTIFF elevation lookup failed (%s) — trying API fallback", exc)

    if elevations is None:
        try:
            elevations = query_elevation_from_api(points_utm, crs_utm)
            logger.info("Elevation lookup from OpenTopoData API (%d points)", len(points_utm))
        except Exception as exc:
            logger.warning("API elevation lookup failed (%s) — all heights set to 0.0 m", exc)
            elevations = [0.0] * len(points_utm)

    return dict(zip(points_utm, elevations))


def assign_elevation_to_geodataframe(gdf: gpd.GeoDataFrame,
                                      elevation_lookup: Dict[Tuple[float, float], float],
                                      default_z: float = 0.0) -> gpd.GeoDataFrame:
    """Write Z-coordinates from *elevation_lookup* into a GeoDataFrame's geometries.

    Supports ``Point`` and ``LineString`` geometry types.  For each vertex
    ``(x, y)`` the corresponding elevation is looked up; if not found,
    *default_z* is used.  The returned GeoDataFrame has the same CRS and
    attributes as the input but with 3-D geometries.

    :param gdf: Input GeoDataFrame with 2-D or 3-D geometries
    :type gdf: gpd.GeoDataFrame
    :param elevation_lookup: Mapping ``{(x, y): z_m}``
    :type elevation_lookup: Dict[Tuple[float, float], float]
    :param default_z: Fallback elevation when a vertex is not in the lookup
    :type default_z: float
    :return: GeoDataFrame with 3-D geometries
    :rtype: gpd.GeoDataFrame
    """

    def _z(x: float, y: float) -> float:
        return elevation_lookup.get((x, y), default_z)

    def _elevate_geometry(geom):
        if geom is None:
            return geom
        if geom.geom_type == "Point":
            return Point(geom.x, geom.y, _z(geom.x, geom.y))
        if geom.geom_type == "LineString":
            return LineString([(x, y, _z(x, y)) for x, y in geom.coords])
        # Unsupported geometry type — return unchanged with a warning
        logger.warning("assign_elevation_to_geodataframe: unsupported geometry type '%s'",
                       geom.geom_type)
        return geom

    gdf_3d = gdf.copy()
    gdf_3d["geometry"] = gdf["geometry"].apply(_elevate_geometry)
    return gdf_3d


def collect_unique_points_from_gdfs(*gdfs: gpd.GeoDataFrame) -> List[Tuple[float, float]]:
    """Collect all unique 2-D (x, y) vertex coordinates from one or more GeoDataFrames.

    This is a convenience function to assemble the list of points that need
    elevation lookup before building the network.

    :param gdfs: One or more GeoDataFrames with Point or LineString geometries
    :return: Deduplicated list of (x, y) tuples
    :rtype: List[Tuple[float, float]]
    """
    points: set = set()
    for gdf in gdfs:
        for geom in gdf.geometry:
            if geom is None:
                continue
            if geom.geom_type == "Point":
                points.add((geom.x, geom.y))
            elif geom.geom_type == "LineString":
                for x, y, *_ in geom.coords:
                    points.add((x, y))
    return list(points)
