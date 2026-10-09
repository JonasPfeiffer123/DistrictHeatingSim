"""
GUI-free building-CSV generation from a building GeoJSON.

For each building feature: skip unheated outbuildings, take the address from the OSM tags
(``addr:*``) or reverse-geocode the centroid (throttled for Nominatim), estimate the heat demand
from footprint × storeys × a specific value, and write a row of the building CSV. This logic
used to be duplicated almost verbatim in ``ProjectModel.create_csv_from_geojson`` (a view) and
``GeoJSONToCSVThread.run`` (a worker); both now call this single function (BACKLOG B2).

Before BACKLOG UT-K5 every building got the dialog's demand and type (a church and the garages
too), OSM addresses were ignored, and the unthrottled reverse geocoding was blocked by
Nominatim - every failure fell back to the first building's address (212 of 239 buildings at
"Spanntigstraße 5").
"""

import csv
import json
import logging

from districtheatingsim.utilities.web_services import describe_service_error, is_transient

logger = logging.getLogger(__name__)

#: OSM ``building=*`` values of unheated outbuildings; they are not written (UT-K5).
OUTBUILDING_TAGS = frozenset(
    {
        "allotment_house",
        "barn",
        "bicycle_parking",
        "boathouse",
        "bridge",
        "bunker",
        "carport",
        "construction",
        "container",
        "cowshed",
        "farm_auxiliary",
        "garage",
        "garages",
        "greenhouse",
        "hut",
        "kiosk",
        "parking",
        "roof",
        "ruins",
        "service",
        "shed",
        "silo",
        "stable",
        "storage_tank",
        "sty",
        "tent",
        "toilets",
        "transformer_tower",
    }
)
#: OSM ``building=*`` values of single- and multi-family houses (type suggestion).
SINGLE_FAMILY_TAGS = frozenset({"bungalow", "detached", "farm", "house", "semidetached_house", "terrace"})
MULTI_FAMILY_TAGS = frozenset({"apartments", "dormitory", "residential"})

# Nominatim stops answering after a few consecutive failures (HTTP 429 / ban); then the remaining
# buildings keep an empty address instead of hammering the service.
_MAX_CONSECUTIVE_SERVICE_FAILURES = 3

# Column contract of the building CSV.
BUILDING_CSV_FIELDNAMES = [
    "Land",
    "Bundesland",
    "Stadt",
    "Adresse",
    "Wärmebedarf",
    "Gebäudetyp",
    "Subtyp",
    "WW_Anteil",
    "Typ_Heizflächen",
    "VLT_max",
    "Steigung_Heizkurve",
    "RLT_max",
    "Normaußentemperatur",
    "UTM_X",
    "UTM_Y",
]


def centroid_of(coordinates):
    """
    Recursively average a (possibly nested) GeoJSON coordinate array.

    Handles a bare ``[x, y]`` point as well as the nested arrays of LineString /
    Polygon / MultiPolygon geometries by averaging the centroids of the parts.

    :param coordinates: A ``[x, y]`` point or a nested list of such arrays.
    :return: ``(x, y)`` centroid, or ``(None, None)`` if no point is found.
    :rtype: tuple
    """
    # Base case: a single [x, y] point.
    if isinstance(coordinates[0], (int, float)):  # GeoJSON may write whole numbers without a point
        return coordinates[0], coordinates[1]

    x_sum = y_sum = 0.0
    total_points = 0
    for item in coordinates:
        x, y = centroid_of(item)
        if x is not None and y is not None:
            x_sum += x
            y_sum += y
            total_points += 1
    if total_points > 0:
        return x_sum / total_points, y_sum / total_points
    return None, None


def osm_address(properties: dict) -> str | None:
    """Street and house number from the OSM ``addr:*`` tags, or None if the number is missing."""
    street = properties.get("addr:street") or properties.get("addr:place")
    number = properties.get("addr:housenumber")
    if street and number:
        return f"{street} {number}"
    return None


def footprint_m2(geometry: dict) -> float:
    """
    Footprint area of a building geometry in a projected CRS [m²] (0 if it has none).

    The building download writes an OSM relation as one polygon of all its outer and inner rings;
    when an "inner" ring is the larger one, the plain area is negative. ``make_valid`` sorts the
    rings out first.
    """
    from shapely import make_valid
    from shapely.geometry import shape

    try:
        return max(float(make_valid(shape(geometry)).area), 0.0)
    except Exception:  # broken or empty geometry
        return 0.0


def storeys(properties: dict, default: float) -> float:
    """Number of storeys from ``building:levels`` (e.g. "3" or "2.5"), else ``default``."""
    try:
        value = float(str(properties.get("building:levels", "")).replace(",", ".").split(";")[0])
    except ValueError:
        return default
    return value if value > 0 else default


def suggest_building_type(osm_building: str | None, default_type: str) -> str:
    """
    Building type for an OSM ``building=*`` value: houses and apartment blocks get the residential
    type of the default's method (VDI 4655 EFH/MFH, BDEW HEF/HMF), everything else the default.
    """
    vdi = default_type in ("EFH", "MFH")
    if osm_building in SINGLE_FAMILY_TAGS:
        return "EFH" if vdi else "HEF"
    if osm_building in MULTI_FAMILY_TAGS:
        return "MFH" if vdi else "HMF"
    return default_type


def _is_service_failure(exc: BaseException) -> bool:
    """True if Nominatim itself failed (blocked, overloaded, unreachable) - not the lookup."""
    from geopy.exc import GeocoderParseError, GeocoderQueryError, GeocoderServiceError

    if isinstance(exc, (GeocoderQueryError, GeocoderParseError)):
        return False
    return isinstance(exc, GeocoderServiceError) or is_transient(exc)


def format_building_csv_summary(summary: dict) -> str:
    """German report of :func:`geojson_to_building_csv` for the user."""
    lines = [f"{summary['written']} von {summary['total']} OSM-Gebäuden übernommen."]
    skipped = summary["skipped_outbuildings"]
    if skipped:
        kinds = ", ".join(f"{count}× {tag}" for tag, count in sorted(skipped.items(), key=lambda kv: -kv[1]))
        lines.append(f"Nebengebäude übersprungen: {sum(skipped.values())} ({kinds}).")
    if summary["skipped_small"]:
        lines.append(
            f"Kleinstgebäude ohne Adresse übersprungen: {summary['skipped_small']} "
            f"(Grundfläche unter {summary['min_footprint_m2']:g} m²)."
        )
    lines.append(
        f"Adressen: {summary['address_from_osm']} aus OpenStreetMap, "
        f"{summary['address_reverse']} über Nominatim ermittelt."
    )
    missing = summary["without_address"]
    if missing:
        listed = ", ".join(str(line) for line in missing[:20]) + (" …" if len(missing) > 20 else "")
        lines.append(f"Ohne Adresse: {len(missing)} Gebäude (CSV-Zeilen {listed}) – bitte ergänzen.")
    if summary.get("shared_addresses"):
        lines.append(
            f"{summary['shared_addresses']} Gebäude teilen sich ihre Adresse mit anderen (z. B. Vorder- und "
            "Hinterhaus) – bitte prüfen, ob sie zusammengefasst werden sollen."
        )
    if summary["specific_demand_kwh_m2"] is not None:
        lines.append(
            f"Wärmebedarf geschätzt aus Grundfläche × Geschosse × {summary['specific_demand_kwh_m2']:g} kWh/(m²·a) "
            f"– bitte prüfen, besonders bei Nichtwohngebäuden."
        )
    if summary["service_error"]:
        lines.append("")
        lines.append(summary["service_error"])
    return "\n".join(lines)


def _address_from_location(location, land, bundesland, stadt, adresse):
    """Merge a geopy reverse-geocode result into (land, bundesland, stadt, adresse)."""
    if not (location and location.raw.get("address")):
        return land, bundesland, stadt, adresse
    address_data = location.raw["address"]
    land = address_data.get("country", land)
    bundesland = address_data.get("state", bundesland)
    stadt = (
        address_data.get("city")
        or address_data.get("town")
        or address_data.get("village")
        or address_data.get("municipality")
        or stadt
    )
    street_parts = []
    if "road" in address_data:
        street_parts.append(address_data["road"])
    if "house_number" in address_data:
        street_parts.append(address_data["house_number"])
    if street_parts:
        adresse = " ".join(street_parts)
    return land, bundesland, stadt, adresse


def geojson_to_building_csv(
    geojson_file_path,
    output_file_path,
    default_values,
    project_crs="EPSG:25833",
    *,
    geocoder=None,
    transformer=None,
    progress=None,
    should_stop=None,
    specific_demand_kwh_m2: float | None = None,
    default_storeys: float = 2.0,
    min_footprint_m2: float = 0.0,
    min_delay_s: float = 1.0,
):
    """
    Convert a building GeoJSON into the building CSV.

    Outbuildings (:data:`OUTBUILDING_TAGS`) are skipped. The address comes from the OSM tags,
    otherwise from reverse geocoding the centroid (at most one request per ``min_delay_s``, the
    Nominatim usage policy); a failed lookup leaves the address empty and is reported.

    :param geojson_file_path: Input building GeoJSON (UTF-8, coordinates in ``project_crs``).
    :param output_file_path: Output CSV path.
    :param default_values: Dict of default building parameters (Wärmebedarf, Gebäudetyp, …)
        and optional fallback fields Land/Bundesland/Stadt. An "Adresse" default is ignored: one
        address for every building is never right.
    :param project_crs: CRS of the GeoJSON coordinates (transformed to WGS84 for geocoding).
    :param geocoder: Optional geopy-style geocoder with ``.reverse(query, language=, timeout=)``;
        created (Nominatim) on demand if ``None``. Injectable for testing without network.
    :param transformer: Optional pyproj ``Transformer`` (project_crs -> WGS84); created on demand.
    :param progress: Optional ``callable(done, total, message)`` for UI progress reporting.
    :param should_stop: Optional ``callable() -> bool`` to abort cooperatively.
    :param specific_demand_kwh_m2: Estimate the heat demand as footprint × storeys × this value
        [kWh/(m²·a)]; ``None`` writes ``default_values["Wärmebedarf"]`` for every building.
    :param default_storeys: Storeys of a building without ``building:levels``.
    :param min_footprint_m2: Skip buildings without an OSM address below this footprint [m²].
    :param min_delay_s: Minimum pause between two reverse-geocoding requests [s].
    :return: Summary dict (``path``, ``total``, ``written``, ``skipped_outbuildings``,
        ``skipped_small``, ``address_from_osm``, ``address_reverse``, ``without_address`` (CSV line
        numbers), ``service_error``, …), see :func:`format_building_csv_summary`.
    :raises InterruptedError: if ``should_stop()`` returned True.
    :raises RuntimeError: wrapping any other failure.
    """
    summary = {
        "path": output_file_path,
        "total": 0,
        "written": 0,
        "skipped_outbuildings": {},
        "skipped_small": 0,
        "min_footprint_m2": min_footprint_m2,
        "address_from_osm": 0,
        "address_reverse": 0,
        "without_address": [],
        "specific_demand_kwh_m2": specific_demand_kwh_m2,
        "service_error": None,
        "shared_addresses": 0,
    }
    try:
        with open(geojson_file_path, encoding="utf-8") as geojson_file:
            data = json.load(geojson_file)

        features = data["features"]
        total = summary["total"] = len(features)
        if progress:
            progress(0, total, "Starte Konvertierung...")

        if geocoder is None:
            from geopy.geocoders import Nominatim

            geocoder = Nominatim(user_agent="DistrictHeatingSim/1.0")
        if transformer is None:
            from pyproj import Transformer

            transformer = Transformer.from_crs(project_crs, "epsg:4326", always_xy=True)
        from geopy.extra.rate_limiter import RateLimiter

        reverse = RateLimiter(
            geocoder.reverse,
            min_delay_seconds=min_delay_s,
            max_retries=2,
            error_wait_seconds=5 if min_delay_s else 0,
            swallow_exceptions=False,
        )
        service_failures = 0
        addresses: dict[str, int] = {}

        with open(output_file_path, "w", encoding="utf-8-sig", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=BUILDING_CSV_FIELDNAMES, delimiter=";")
            writer.writeheader()

            for i, feature in enumerate(features):
                if should_stop is not None and should_stop():
                    raise InterruptedError("Konvertierung abgebrochen")

                properties = feature.get("properties") or {}
                osm_building = properties.get("building")
                if osm_building in OUTBUILDING_TAGS:
                    summary["skipped_outbuildings"][osm_building] = (
                        summary["skipped_outbuildings"].get(osm_building, 0) + 1
                    )
                    if progress:
                        progress(i + 1, total, f"Gebäude {i + 1}/{total}: Nebengebäude ({osm_building}) übersprungen")
                    continue
                address = osm_address(properties)
                area = footprint_m2(feature["geometry"])
                if address is None and area < min_footprint_m2:
                    summary["skipped_small"] += 1
                    if progress:
                        progress(i + 1, total, f"Gebäude {i + 1}/{total}: Kleinstgebäude übersprungen")
                    continue

                centroid = centroid_of(feature["geometry"]["coordinates"])

                land = default_values.get("Land", "Deutschland")
                bundesland = default_values.get("Bundesland", "")
                stadt = properties.get("addr:city") or default_values.get("Stadt", "")
                adresse = ""

                if address is not None:
                    adresse = address
                    summary["address_from_osm"] += 1
                    message = f"Gebäude {i + 1}/{total}: {adresse} (OSM)"
                elif centroid[0] is None or centroid[1] is None:
                    message = f"Gebäude {i + 1}/{total}: Keine Koordinaten"
                elif service_failures >= _MAX_CONSECUTIVE_SERVICE_FAILURES:
                    message = f"Gebäude {i + 1}/{total}: Adressdienst nicht erreichbar"
                else:
                    try:
                        lon, lat = transformer.transform(centroid[0], centroid[1])
                        location = reverse(f"{lat}, {lon}", language="de", timeout=10)
                        service_failures = 0
                        land, bundesland, stadt, adresse = _address_from_location(
                            location, land, bundesland, stadt, adresse
                        )
                        if adresse:
                            summary["address_reverse"] += 1
                        message = f"Gebäude {i + 1}/{total}: {adresse or 'keine Adresse gefunden'}, {stadt}"
                    except Exception as e:
                        logger.debug("Reverse-Geocoding für Gebäude %d fehlgeschlagen: %s", i + 1, e)
                        if _is_service_failure(e):
                            service_failures += 1
                            if service_failures >= _MAX_CONSECUTIVE_SERVICE_FAILURES:
                                summary["service_error"] = describe_service_error("Nominatim", e)
                        message = f"Gebäude {i + 1}/{total}: Geocoding fehlgeschlagen"
                if progress:
                    progress(i + 1, total, message)

                if not adresse:
                    summary["without_address"].append(summary["written"] + 2)  # CSV line (header = 1)
                if specific_demand_kwh_m2 is not None:
                    demand = round(area * storeys(properties, default_storeys) * specific_demand_kwh_m2)
                else:
                    demand = default_values["Wärmebedarf"]

                summary["written"] += 1
                if adresse:
                    addresses[adresse] = addresses.get(adresse, 0) + 1
                writer.writerow(
                    {
                        "Land": land,
                        "Bundesland": bundesland,
                        "Stadt": stadt,
                        "Adresse": adresse,
                        "Wärmebedarf": demand,
                        "Gebäudetyp": suggest_building_type(osm_building, default_values["Gebäudetyp"]),
                        "Subtyp": default_values["Subtyp"],
                        "WW_Anteil": default_values["WW_Anteil"],
                        "Typ_Heizflächen": default_values["Typ_Heizflächen"],
                        "VLT_max": default_values["VLT_max"],
                        "Steigung_Heizkurve": default_values["Steigung_Heizkurve"],
                        "RLT_max": default_values["RLT_max"],
                        "Normaußentemperatur": default_values["Normaußentemperatur"],
                        "UTM_X": centroid[0],
                        "UTM_Y": centroid[1],
                    }
                )
        summary["shared_addresses"] = sum(count for count in addresses.values() if count > 1)
        return summary
    except InterruptedError:
        raise
    except Exception as e:
        raise RuntimeError(f"Fehler beim Erstellen der CSV-Datei: {e}") from e
