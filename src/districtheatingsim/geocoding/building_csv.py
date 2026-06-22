"""
GUI-free building-CSV generation from a building GeoJSON.

For each building feature: compute the centroid, reverse-geocode it (UTM -> WGS84 ->
address), and write a row of the building CSV (address + the caller's default building
parameters). This logic used to be duplicated almost verbatim in
``ProjectModel.create_csv_from_geojson`` (a view) and ``GeoJSONToCSVThread.run`` (a worker);
both now call this single function (BACKLOG B2).
"""

import csv
import json
import logging

logger = logging.getLogger(__name__)

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
    if isinstance(coordinates[0], float):
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
):
    """
    Convert a building GeoJSON into the building CSV, reverse-geocoding each centroid.

    :param geojson_file_path: Input building GeoJSON.
    :param output_file_path: Output CSV path.
    :param default_values: Dict of default building parameters (Wärmebedarf, Gebäudetyp, …)
        and optional fallback address fields (Land/Bundesland/Stadt/Adresse).
    :param project_crs: CRS of the GeoJSON coordinates (transformed to WGS84 for geocoding).
    :param geocoder: Optional geopy-style geocoder with ``.reverse(query, language=, timeout=)``;
        created (Nominatim) on demand if ``None``. Injectable for testing without network.
    :param transformer: Optional pyproj ``Transformer`` (project_crs -> WGS84); created on demand.
    :param progress: Optional ``callable(done, total, message)`` for UI progress reporting.
    :param should_stop: Optional ``callable() -> bool`` to abort cooperatively.
    :return: ``output_file_path``.
    :raises InterruptedError: if ``should_stop()`` returned True.
    :raises RuntimeError: wrapping any other failure.
    """
    try:
        with open(geojson_file_path) as geojson_file:
            data = json.load(geojson_file)

        features = data["features"]
        total = len(features)
        if progress:
            progress(0, total, "Starte Konvertierung...")

        if geocoder is None:
            from geopy.geocoders import Nominatim

            geocoder = Nominatim(user_agent="DistrictHeatingSim")
        if transformer is None:
            from pyproj import Transformer

            transformer = Transformer.from_crs(project_crs, "epsg:4326", always_xy=True)

        with open(output_file_path, "w", encoding="utf-8-sig", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=BUILDING_CSV_FIELDNAMES, delimiter=";")
            writer.writeheader()

            for i, feature in enumerate(features):
                if should_stop is not None and should_stop():
                    raise InterruptedError("Konvertierung abgebrochen")

                centroid = centroid_of(feature["geometry"]["coordinates"])

                land = default_values.get("Land", "Deutschland")
                bundesland = default_values.get("Bundesland", "")
                stadt = default_values.get("Stadt", "")
                adresse = default_values.get("Adresse", "")

                if centroid[0] is not None and centroid[1] is not None:
                    try:
                        lon, lat = transformer.transform(centroid[0], centroid[1])
                        location = geocoder.reverse(f"{lat}, {lon}", language="de", timeout=10)
                        land, bundesland, stadt, adresse = _address_from_location(
                            location, land, bundesland, stadt, adresse
                        )
                        if progress:
                            progress(i + 1, total, f"Gebäude {i + 1}/{total}: {adresse}, {stadt}")
                    except Exception as e:
                        logger.debug("Reverse-Geocoding für Gebäude %d fehlgeschlagen: %s", i + 1, e)
                        if progress:
                            progress(i + 1, total, f"Gebäude {i + 1}/{total}: Geocoding fehlgeschlagen")
                elif progress:
                    progress(i + 1, total, f"Gebäude {i + 1}/{total}: Keine Koordinaten")

                writer.writerow(
                    {
                        "Land": land,
                        "Bundesland": bundesland,
                        "Stadt": stadt,
                        "Adresse": adresse,
                        "Wärmebedarf": default_values["Wärmebedarf"],
                        "Gebäudetyp": default_values["Gebäudetyp"],
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
        return output_file_path
    except InterruptedError:
        raise
    except Exception as e:
        raise RuntimeError(f"Fehler beim Erstellen der CSV-Datei: {e}") from e
