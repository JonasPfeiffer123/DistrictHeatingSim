"""
Project location and climate data (user test 2026-10-08, UT-H9).

Every new project got the bundled test reference year (TRY, at 51.17° N / 14.42° E) and VDI 4655
climate zone 9 without a hint, wherever it lay. A project now has a location - set in the
new-project assistant or taken from the geocoded buildings - against which the TRY is checked;
climate zone and persons per household are project settings, and the solar thermal location is
taken from it.

:author: M.Eng. Jonas Pfeiffer
"""

import math
import os
import re

#: Where the DWD provides test reference years (free, registration required)
DWD_TRY_URL = "https://www.dwd.de/DE/leistungen/testreferenzjahre/testreferenzjahre.html"

#: VDI 4655 climate zones: the 15 TRY regions of the Deutscher Wetterdienst
CLIMATE_ZONES: dict[str, str] = {
    "1": "Nordseeküste",
    "2": "Ostseeküste",
    "3": "Nordwestdeutsches Tiefland",
    "4": "Nordostdeutsches Tiefland",
    "5": "Niederrheinisch-westfälische Bucht und Emsland",
    "6": "Nördliche und westliche Mittelgebirge, Randgebiete",
    "7": "Nördliche und westliche Mittelgebirge, zentrale Bereiche",
    "8": "Oberharz und Schwarzwald (mittlere Lagen)",
    "9": "Thüringer Becken und Sächsisches Hügelland",
    "10": "Südöstliche Mittelgebirge bis 1000 m",
    "11": "Erzgebirge, Böhmer- und Schwarzwald oberhalb 1000 m",
    "12": "Oberrheingraben und unteres Neckartal",
    "13": "Schwäbisch-fränkisches Stufenland und Alpenvorland",
    "14": "Schwäbische Alb und Baar",
    "15": "Alpenrand und -täler",
}
DEFAULT_CLIMATE_ZONE = "9"
DEFAULT_PERSONS_PER_HOUSEHOLD = 2

#: Distance between the TRY location and the project beyond which the user is told [km]
TRY_DISTANCE_WARNING_KM = 50.0

#: Standard meridian of the TRY time stamps (MEZ, 15° E) in the solar code's convention, which
#: counts longitudes west-positive: ``4 * (STD_Longitude - Longitude)`` minutes
SOLAR_STD_LONGITUDE = -15


def climate_zone_label(zone: str) -> str:
    """'9 – Thüringer Becken und Sächsisches Hügelland'."""
    return f"{zone} – {CLIMATE_ZONES.get(str(zone), 'unbekannt')}"


def try_location(path: str) -> tuple[float, float] | None:
    """
    Location of a DWD TRY file.

    Read from the file name ``TRY2015_LLLLLLWWWWWW_*.dat`` (lat = LLLLLL/10000, lon = WWWWWW/10000),
    else from the ``Rechtswert``/``Hochwert`` header lines (EPSG:3034, Lambert conformal conic).

    :return: ``(lat, lon)`` in degrees, or None if the file says nothing about its location.
    """
    if not path:
        return None
    match = re.search(r"_(\d{6})(\d{6})_", os.path.basename(path))
    if match:
        return int(match.group(1)) / 10000, int(match.group(2)) / 10000
    try:
        easting = northing = None
        with open(path, encoding="latin-1", errors="replace") as file:
            header = [line for _number, line in zip(range(40), file, strict=False)]
            for line in header:
                if line.startswith("Rechtswert"):
                    easting = float(line.split(":")[1].split()[0])
                elif line.startswith("Hochwert"):
                    northing = float(line.split(":")[1].split()[0])
        if easting is None or northing is None:
            return None
        from pyproj import Transformer

        lon, lat = Transformer.from_crs("EPSG:3034", "EPSG:4326", always_xy=True).transform(easting, northing)
        return lat, lon
    except (OSError, ValueError, IndexError):
        return None


def format_location(lat: float, lon: float) -> str:
    """'51,1676° N, 14,4222° O'."""
    north = f"{abs(lat):.4f}° {'N' if lat >= 0 else 'S'}"
    east = f"{abs(lon):.4f}° {'O' if lon >= 0 else 'W'}"
    return f"{north}, {east}".replace(".", ",")


def distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance between two ``(lat, lon)`` points [km]."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def building_location(csv_path: str, crs: str) -> tuple[float, float] | None:
    """
    Mean location of the geocoded buildings of a building CSV.

    :param csv_path: Building CSV with ``UTM_X``/``UTM_Y`` in ``crs``.
    :param crs: The project CRS.
    :return: ``(lat, lon)``, or None if no building has coordinates.
    """
    from districtheatingsim.utilities.crs_utils import read_building_coordinates, to_wgs84

    try:
        xs, ys = read_building_coordinates(csv_path)
        if not len(xs):
            return None
        lon, lat = to_wgs84(xs, ys, crs)
    except Exception:
        return None
    return float(lat.mean()), float(lon.mean())


def climate_data_warning(try_path: str, location: tuple[float, float] | None) -> str | None:
    """
    German hint if the TRY lies far from the project.

    :param try_path: The project's TRY file.
    :param location: ``(lat, lon)`` of the project, or None if unknown.
    :return: The message, or None if the TRY fits (or nothing can be said).
    """
    if location is None:
        return None
    try_point = try_location(try_path)
    if try_point is None:
        return None
    distance = distance_km(try_point, location)
    if distance <= TRY_DISTANCE_WARNING_KM:
        return None
    return (
        f"Die Klimadaten (Testreferenzjahr) des Projekts gehören zu einem Ort {distance:.0f} km vom "
        f"Projektstandort entfernt:\n\n"
        f"  TRY:      {format_location(*try_point)}  ({os.path.basename(try_path)})\n"
        f"  Projekt: {format_location(*location)}\n\n"
        "Außentemperaturen und Einstrahlung des falschen Orts verändern Lastgänge, Netzverluste und "
        "Solarerträge. Ein Testreferenzjahr für den Standort erhalten Sie kostenlos beim Deutschen "
        f"Wetterdienst ({DWD_TRY_URL}, Registrierung nötig) und legen es unter "
        "„Datenbasis → Klimadaten (TRY) festlegen“ fest."
    )


def solar_location_inputs(location: tuple[float, float]) -> dict:
    """
    Location fields of the solar thermal dialog for a project location.

    The solar code counts longitudes west-positive (see ``SOLAR_STD_LONGITUDE``); the dialog used to
    pre-fill Görlitz with mixed signs (−14.42 / +15), which shifted the hourly profile (UT-M4).
    """
    lat, lon = location
    return {"Latitude": round(lat, 4), "Longitude": round(-lon, 4), "STD_Longitude": SOLAR_STD_LONGITUDE}
