"""
CRS (Coordinate Reference System) utilities for DistrictHeatingSim.

Provides automatic CRS suggestion based on geographic location and a curated
list of common projected coordinate systems.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from typing import List, Tuple


# Curated list of common projected CRS options (epsg_code, display_label)
COMMON_CRS_OPTIONS: List[Tuple[str, str]] = [
    ("EPSG:25832", "EPSG:25832 – ETRS89 / UTM Zone 32N (Westdeutschland, 6°–12°E)"),
    ("EPSG:25833", "EPSG:25833 – ETRS89 / UTM Zone 33N (Ostdeutschland, 12°–18°E)"),
    ("EPSG:25834", "EPSG:25834 – ETRS89 / UTM Zone 34N (Osteuropa, 18°–24°E)"),
    ("EPSG:25835", "EPSG:25835 – ETRS89 / UTM Zone 35N (24°–30°E)"),
    ("EPSG:32632", "EPSG:32632 – WGS84 / UTM Zone 32N"),
    ("EPSG:32633", "EPSG:32633 – WGS84 / UTM Zone 33N"),
    ("EPSG:32634", "EPSG:32634 – WGS84 / UTM Zone 34N"),
    ("EPSG:31467", "EPSG:31467 – DHDN / Gauß-Krüger Zone 3 (Deutschland)"),
    ("EPSG:31468", "EPSG:31468 – DHDN / Gauß-Krüger Zone 4 (Deutschland)"),
    ("EPSG:2056",  "EPSG:2056  – CH1903+ / LV95 (Schweiz)"),
    ("EPSG:31287", "EPSG:31287 – MGI / Austria Lambert (Österreich)"),
    ("EPSG:3035",  "EPSG:3035  – ETRS89 / LAEA Europe (ganz Europa)"),
    ("EPSG:3857",  "EPSG:3857  – Web Mercator (globale Webkarten)"),
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
