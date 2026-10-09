"""
CRS (Coordinate Reference System) utilities for DistrictHeatingSim.

Provides automatic CRS suggestion based on geographic location and a curated
list of common projected coordinate systems.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

# Curated list of common projected CRS options (epsg_code, display_label)
COMMON_CRS_OPTIONS: list[tuple[str, str]] = [
    ("EPSG:25832", "EPSG:25832 – ETRS89 / UTM Zone 32N (Westdeutschland, 6°–12°E)"),
    ("EPSG:25833", "EPSG:25833 – ETRS89 / UTM Zone 33N (Ostdeutschland, 12°–18°E)"),
    ("EPSG:25834", "EPSG:25834 – ETRS89 / UTM Zone 34N (Osteuropa, 18°–24°E)"),
    ("EPSG:25835", "EPSG:25835 – ETRS89 / UTM Zone 35N (24°–30°E)"),
    ("EPSG:32632", "EPSG:32632 – WGS84 / UTM Zone 32N"),
    ("EPSG:32633", "EPSG:32633 – WGS84 / UTM Zone 33N"),
    ("EPSG:32634", "EPSG:32634 – WGS84 / UTM Zone 34N"),
    ("EPSG:31467", "EPSG:31467 – DHDN / Gauß-Krüger Zone 3 (Deutschland)"),
    ("EPSG:31468", "EPSG:31468 – DHDN / Gauß-Krüger Zone 4 (Deutschland)"),
    ("EPSG:2056", "EPSG:2056  – CH1903+ / LV95 (Schweiz)"),
    ("EPSG:31287", "EPSG:31287 – MGI / Austria Lambert (Österreich)"),
    ("EPSG:3035", "EPSG:3035  – ETRS89 / LAEA Europe (ganz Europa)"),
    ("EPSG:3857", "EPSG:3857  – Web Mercator (globale Webkarten)"),
    ("EPSG:32601", "EPSG:32601 – WGS84 / UTM Zone 1N"),
    ("EPSG:32755", "EPSG:32755 – WGS84 / UTM Zone 55S (Australien)"),
]

# Default fallback CRS
DEFAULT_CRS = "EPSG:25833"


def suggest_crs_from_location(lon: float, lat: float) -> str:
    """
    Suggest an appropriate projected CRS based on WGS84 coordinates.

    For European locations (lon −6° to 36°, lat 35° to 72°) the function
    returns an ETRS89 UTM zone (EPSG:25832–25834).  Outside Europe it returns
    the matching WGS84 UTM zone (EPSG:326xx / 327xx).

    :param lon: Longitude in decimal degrees (WGS84)
    :type lon: float
    :param lat: Latitude in decimal degrees (WGS84)
    :type lat: float
    :return: EPSG code string, e.g. ``"EPSG:25833"``
    :rtype: str
    """
    # UTM zone number (1–60)
    zone = int((lon + 180) / 6) + 1

    if lat >= 0:  # Northern hemisphere
        if -6 <= lon <= 36 and 35 <= lat <= 72:
            # ETRS89 UTM for continental Europe (zones 28-37 → EPSG:25828-25837)
            return f"EPSG:{25800 + zone}"
        else:
            # WGS84 UTM North
            return f"EPSG:{32600 + zone}"
    else:  # Southern hemisphere
        return f"EPSG:{32700 + zone}"


def epsg_from_urn(urn: str) -> str:
    """
    Convert an OGC URN CRS identifier to a plain EPSG code string.

    Example: ``"urn:ogc:def:crs:EPSG::25833"`` → ``"EPSG:25833"``
    If the input is already in ``"EPSG:XXXXX"`` form it is returned unchanged.

    :param urn: OGC URN or EPSG string
    :type urn: str
    :return: EPSG code string
    :rtype: str
    """
    if urn.upper().startswith("EPSG:"):
        return urn
    # urn:ogc:def:crs:EPSG::25833  or  urn:ogc:def:crs:EPSG:6.6:25833
    parts = urn.split(":")
    for part in reversed(parts):
        if part.isdigit():
            return f"EPSG:{part}"
    return urn


def crs_to_urn(crs: str) -> str:
    """
    Convert a plain EPSG code to the OGC URN format used in GeoJSON CRS objects.

    Example: ``"EPSG:25833"`` → ``"urn:ogc:def:crs:EPSG::25833"``

    :param crs: EPSG code string (e.g. ``"EPSG:25833"``)
    :type crs: str
    :return: OGC URN string
    :rtype: str
    """
    code = crs.upper().replace("EPSG:", "")
    return f"urn:ogc:def:crs:EPSG::{code}"


#: Tolerance [degrees of longitude/latitude] around a CRS's area of use before a point counts as
#: outside: a UTM zone can be stretched a little past its 6° band without noticeable distortion.
CRS_AREA_TOLERANCE_DEG = 1.0


def to_wgs84(xs, ys, crs: str):
    """
    Transform projected coordinates to WGS84.

    :param xs: Easting values in ``crs``.
    :param ys: Northing values in ``crs``.
    :param crs: Source CRS, e.g. ``"EPSG:25833"``.
    :return: ``(lon, lat)`` arrays in degrees.
    :rtype: tuple[numpy.ndarray, numpy.ndarray]
    """
    import numpy as np
    from pyproj import Transformer

    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(np.asarray(xs, dtype=float), np.asarray(ys, dtype=float))
    return np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)


def outside_crs_area(xs, ys, crs: str, tolerance_deg: float = CRS_AREA_TOLERANCE_DEG):
    """
    Mark coordinates that lie outside the area of use of ``crs``.

    Geocoding computes coordinates in the project CRS even far outside its zone (Freiburg in
    EPSG:25833 gives a negative easting), so wrong projects are only visible this way
    (BACKLOG UT-K2).

    :param xs: Easting values in ``crs``.
    :param ys: Northing values in ``crs``.
    :param crs: The CRS the coordinates are in.
    :param tolerance_deg: Margin around the area of use [degrees].
    :return: Boolean array, ``True`` = outside; all ``False`` if ``crs`` has no area of use.
    :rtype: numpy.ndarray
    """
    import numpy as np
    from pyproj import CRS

    lon, lat = to_wgs84(xs, ys, crs)
    area = CRS.from_user_input(crs).area_of_use
    if area is None:
        return np.zeros(lon.shape, dtype=bool)
    return (
        (lon < area.west - tolerance_deg)
        | (lon > area.east + tolerance_deg)
        | (lat < area.south - tolerance_deg)
        | (lat > area.north + tolerance_deg)
    )


def suggest_crs_for_coordinates(xs, ys, crs: str) -> str:
    """
    Suggest a projected CRS for coordinates given in ``crs`` (from their median WGS84 position).

    :param xs: Easting values in ``crs``.
    :param ys: Northing values in ``crs``.
    :param crs: The CRS the coordinates are in.
    :return: EPSG code, see :func:`suggest_crs_from_location`.
    :rtype: str
    """
    import numpy as np

    lon, lat = to_wgs84(xs, ys, crs)
    return suggest_crs_from_location(float(np.nanmedian(lon)), float(np.nanmedian(lat)))


def read_building_coordinates(csv_path: str):
    """
    Read the ``UTM_X``/``UTM_Y`` columns of a building CSV.

    :param csv_path: Building CSV (``;``-separated, UTF-8 with or without BOM).
    :return: ``(xs, ys)`` arrays of the rows with numeric coordinates; empty arrays if the file
        or the columns do not exist.
    :rtype: tuple[numpy.ndarray, numpy.ndarray]
    """
    import os

    import numpy as np
    import pandas as pd

    if not csv_path or not os.path.exists(csv_path):
        return np.array([]), np.array([])
    frame = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig", dtype=str)
    frame.columns = [str(c).lstrip("\ufeff") for c in frame.columns]
    if "UTM_X" not in frame.columns or "UTM_Y" not in frame.columns:
        return np.array([]), np.array([])
    xs = pd.to_numeric(frame["UTM_X"], errors="coerce")
    ys = pd.to_numeric(frame["UTM_Y"], errors="coerce")
    valid = xs.notna() & ys.notna()
    return xs[valid].to_numpy(dtype=float), ys[valid].to_numpy(dtype=float)


def reproject_building_csv(csv_path: str, from_crs: str, to_crs: str) -> int:
    """
    Convert the ``UTM_X``/``UTM_Y`` columns of a building CSV to another CRS, in place.

    All other columns are written back as they were read (as text, so e.g. a ``Subtyp`` of
    ``03`` keeps its leading zero). Changing the project CRS used to keep the coordinates, which
    then were read in the new CRS and moved the buildings by hundreds of kilometres
    (BACKLOG UT-K2).

    :param csv_path: Building CSV (``;``-separated, UTF-8; written back with BOM).
    :param from_crs: CRS the coordinates are in.
    :param to_crs: Target CRS.
    :return: Number of rows whose coordinates were converted.
    :rtype: int
    """
    import pandas as pd
    from pyproj import Transformer

    frame = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)
    frame.columns = [str(c).lstrip("\ufeff") for c in frame.columns]
    if "UTM_X" not in frame.columns or "UTM_Y" not in frame.columns:
        return 0
    xs = pd.to_numeric(frame["UTM_X"], errors="coerce")
    ys = pd.to_numeric(frame["UTM_Y"], errors="coerce")
    valid = xs.notna() & ys.notna()
    if valid.any():
        transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)
        new_x, new_y = transformer.transform(xs[valid].to_numpy(dtype=float), ys[valid].to_numpy(dtype=float))
        frame.loc[valid, "UTM_X"] = [repr(float(v)) for v in new_x]
        frame.loc[valid, "UTM_Y"] = [repr(float(v)) for v in new_y]
    frame.to_csv(csv_path, sep=";", index=False, encoding="utf-8-sig")
    return int(valid.sum())
