"""
Nearest-geometry lookup for network generation.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

The street snapping steps (building connections, MST road alignment) looked up the nearest
street for every point by computing the distance to *every* street — per point and, in the
road alignment, per iteration. The GeoDataFrame's spatial index (built once and cached by
geopandas) answers the same question without the full scan (BACKLOG G5).
"""

import geopandas as gpd
from shapely.geometry.base import BaseGeometry


def nearest_position(layer: gpd.GeoDataFrame, geometry: BaseGeometry) -> int | None:
    """
    Positional index of the geometry in ``layer`` closest to ``geometry``.

    On ties (equidistant geometries) the first one in ``layer`` order wins — the same result
    as a full scan with ``distance(...).idxmin()`` on a default index or a strict ``<`` loop.

    :param layer: Geometries to search (typically streets)
    :type layer: gpd.GeoDataFrame
    :param geometry: Query geometry
    :type geometry: BaseGeometry
    :return: Position (``iloc``) of the nearest geometry, or ``None`` for an empty layer
    :rtype: Optional[int]
    """
    if len(layer) == 0:
        return None
    _, positions = layer.sindex.nearest(geometry, return_all=True)
    return int(positions.min())
