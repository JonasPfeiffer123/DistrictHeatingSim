"""
Geocoding module for address to coordinate transformation.

Provides Nominatim-based geocoding with coordinate system transformation
from WGS84 to UTM Zone 33N (ETRS89).

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import csv
import logging
import os
import shutil
import tempfile
from collections import defaultdict

from geopy.exc import GeocoderParseError, GeocoderQueryError, GeocoderServiceError
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from pyproj import Transformer

from districtheatingsim.utilities.web_services import ServiceUnavailableError, describe_service_error, is_transient

logger = logging.getLogger(__name__)

# Shared geolocator instance (Nominatim usage policy: max 1 req/sec, identify your app). Errors are
# not swallowed: a blocked or unreachable Nominatim looked like "address not found" (UT-H3).
_geolocator = Nominatim(user_agent="DistrictHeatingSim/1.0")
_geocode = RateLimiter(
    _geolocator.geocode, min_delay_seconds=1, max_retries=3, error_wait_seconds=5, swallow_exceptions=False
)


def _is_service_failure(exc: BaseException) -> bool:
    """True if Nominatim itself failed (blocked, overloaded, unreachable) - not the address."""
    if isinstance(exc, (GeocoderQueryError, GeocoderParseError)):
        return False
    return isinstance(exc, GeocoderServiceError) or is_transient(exc)


#: Match precision of :func:`locate_address`: the house (number or building), only the street, or
#: only a square, district or the town.
PRECISION_HOUSE = "house"
PRECISION_STREET = "street"
PRECISION_TOWN = "town"

#: Nominatim ``place_rank`` of a result: 28-30 house numbers and buildings, 26-27 streets, below
#: that squares, districts and towns (https://nominatim.org/release-docs/latest/customize/Ranking/).
#: An address whose house number Nominatim does not know comes back as the street (UT-H6).
_HOUSE_RANK = 28
_STREET_RANK = 26

#: Decimals (m) to which projected coordinates are compared for "same point": Nominatim gives
#: identical answers for a repeated street, so only exact repeats need catching
_SAME_POINT_DECIMALS = 1

#: Entries listed per finding in the user message; the rest is counted
_MAX_LISTED = 15


def match_precision(raw: dict) -> str:
    """
    Precision of a Nominatim result from its ``place_rank`` (one of the ``PRECISION_*`` values).

    :param raw: The raw Nominatim answer (``geopy.Location.raw``).
    """
    try:
        rank = int(raw.get("place_rank"))
    except (TypeError, ValueError):
        return PRECISION_STREET if raw.get("class") == "highway" else PRECISION_HOUSE
    if rank >= _HOUSE_RANK:
        return PRECISION_HOUSE
    if rank >= _STREET_RANK:
        return PRECISION_STREET
    return PRECISION_TOWN


def _lookup(address):
    """
    The Nominatim result for ``address``, or None if it was not found.

    :raises ServiceUnavailableError: If Nominatim is blocked, overloaded or unreachable
    """
    try:
        location = _geocode(address)
    except Exception as e:
        if _is_service_failure(e):
            raise ServiceUnavailableError(describe_service_error("Nominatim", e, attempts=4)) from e
        logger.warning("Geocoding of %s failed: %s", address, e)
        return None
    if not location:
        logger.warning("Could not geocode the address %s", address)
    return location


def find_place(query: str) -> tuple[float, float, str] | None:
    """
    Look up a town or address for the project location (new-project assistant, UT-H9).

    :param query: What the user typed, e.g. "Freiburg im Breisgau" or "Vaubanallee 2, Freiburg".
    :return: ``(lat, lon, display_name)`` in WGS84, or None if nothing was found.
    :raises ServiceUnavailableError: If Nominatim is blocked, overloaded or unreachable
    """
    location = _lookup(query) if query and query.strip() else None
    if not location:
        return None
    return float(location.latitude), float(location.longitude), location.address


def locate_address(address, from_crs="epsg:4326", to_crs="epsg:25833"):
    """
    Geocode an address, transform it to the target CRS and say how precise the match is.

    Uses a shared rate-limited Nominatim instance (max 1 req/sec) to comply
    with the Nominatim usage policy.

    :param address: Address to geocode
    :type address: str
    :param from_crs: Source CRS (default: WGS84)
    :type from_crs: str
    :param to_crs: Target CRS (default: ETRS89/UTM Zone 33N)
    :type to_crs: str
    :return: ``(x, y, precision)`` with a ``PRECISION_*`` value, or ``(None, None, None)`` if the
        address was not found
    :rtype: tuple
    :raises ServiceUnavailableError: If Nominatim is blocked, overloaded or unreachable
    """
    location = _lookup(address)
    if not location:
        return (None, None, None)
    transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)
    utm_x, utm_y = transformer.transform(location.longitude, location.latitude)
    return (utm_x, utm_y, match_precision(location.raw or {}))


def get_coordinates(address, from_crs="epsg:4326", to_crs="epsg:25833"):
    """
    Geocode address and transform coordinates to UTM.

    :return: (UTM_X, UTM_Y) coordinates or (None, None) if the address was not found
    :rtype: tuple of float
    :raises ServiceUnavailableError: If Nominatim is blocked, overloaded or unreachable

    See :func:`locate_address`, which also returns the precision of the match.
    """
    utm_x, utm_y, _precision = locate_address(address, from_crs=from_crs, to_crs=to_crs)
    return (utm_x, utm_y)


def _listed(entries: list[str]) -> str:
    """Bullet list of at most ``_MAX_LISTED`` entries, the rest counted."""
    lines = [f"  • {entry}" for entry in entries[:_MAX_LISTED]]
    if len(entries) > _MAX_LISTED:
        lines.append(f"  … und {len(entries) - _MAX_LISTED} weitere")
    return "\n".join(lines)


def _numbers(entries: list[dict]) -> str:
    return ", ".join(str(entry["number"]) for entry in entries)


def _group_label(group: list[dict]) -> str:
    """'Nr. 1, 2, 3: Vaubanallee, Freiburg' - the addresses once each."""
    addresses = list(dict.fromkeys(entry["address"] for entry in group))
    return f"Nr. {_numbers(group)}: {' / '.join(addresses)}"


def format_geocoding_summary(summary: dict) -> tuple[bool, str]:
    """
    German user message for the summary returned by :func:`process_data`.

    Besides the addresses that were not found it names the ones Nominatim only placed on the
    street or in the town and the buildings that ended up on the same point (UT-H6) - each would
    otherwise give a wrong house connection without any hint.

    :param summary: Dict of :func:`process_data`.
    :return: ``(all_fine, message)``.
    :rtype: tuple[bool, str]
    """
    total = summary.get("total", 0)
    success = summary.get("success", 0)
    message = f"Geocoding abgeschlossen: {success} von {total} Adressen gefunden."
    not_found = summary.get("not_found")
    if not_found is None:  # summary without row numbers
        not_found = [{"number": None, "address": address} for address in summary.get("failed_addresses", [])]
    street_only = summary.get("street_only", [])
    town_only = summary.get("town_only", [])
    same_point = summary.get("same_point", [])

    def entry(item):
        return item["address"] if item["number"] is None else f"Nr. {item['number']}: {item['address']}"

    sections = []
    if not_found:
        sections.append(f"Nicht gefunden ({len(not_found)}):\n{_listed([entry(item) for item in not_found])}")
    if street_only:
        sections.append(
            f"Nur die Straße gefunden, nicht das Haus ({len(street_only)}) – der Punkt liegt irgendwo auf der "
            f"Straße:\n{_listed([entry(item) for item in street_only])}"
        )
    if town_only:
        sections.append(
            f"Nur der Ort gefunden ({len(town_only)}) – der Punkt liegt im Orts- oder Stadtteilzentrum:\n"
            f"{_listed([entry(item) for item in town_only])}"
        )
    if same_point:
        sections.append(
            f"Mehrere Gebäude auf demselben Punkt ({len(same_point)} "
            f"{'Gruppe' if len(same_point) == 1 else 'Gruppen'}):\n"
            f"{_listed([_group_label(group) for group in same_point])}"
        )
    if not sections:
        return True, message
    hint = (
        "Bitte prüfen Sie Schreibweise und Hausnummer und geocodieren Sie erneut, oder tragen Sie die "
        "Koordinaten (UTM_X/UTM_Y) von Hand ein."
    )
    if summary.get("not_found") is not None:
        hint = f"Nr. = Zeile der Gebäudetabelle. {hint}"
    return False, "\n\n".join([message, *sections, hint])


def geocoding_row_notes(summary: dict) -> dict[int, str]:
    """
    Note per building (table row number, 1-based) that needs a look after geocoding (UT-H6).

    :param summary: Dict of :func:`process_data`.
    :return: ``{number: note}`` for the rows to mark; empty if all addresses were found exactly.
    """
    notes: dict[int, list[str]] = defaultdict(list)
    for item in summary.get("not_found", []):
        notes[item["number"]].append("Adresse nicht gefunden")
    for item in summary.get("street_only", []):
        notes[item["number"]].append("Nur die Straße gefunden, nicht das Haus")
    for item in summary.get("town_only", []):
        notes[item["number"]].append("Nur der Ort gefunden")
    for group in summary.get("same_point", []):
        for item in group:
            others = ", ".join(str(other["number"]) for other in group if other is not item)
            notes[item["number"]].append(f"Gleicher Punkt wie Nr. {others}")
    return {number: "; ".join(texts) for number, texts in notes.items()}


def process_data(input_csv, crs: str = "EPSG:25833") -> dict:
    """
    Add projected coordinates to CSV file via geocoding.

    Requests are rate-limited to 1/sec to comply with the Nominatim usage policy.

    :param input_csv: Path to CSV file (delimiter ';', columns: country, state, city, address)
    :type input_csv: str
    :param crs: Target projected CRS for UTM_X/UTM_Y columns (default EPSG:25833)
    :type crs: str
    :return: Summary dict with keys ``total``, ``success``, ``failed``, ``failed_addresses`` and the
        findings to check (UT-H6): ``not_found``, ``street_only``, ``town_only`` (lists of
        ``{"number", "address", "x", "y"}``, number = 1-based data row as in the building table) and
        ``same_point`` (groups of such entries that got identical coordinates)
    :rtype: dict
    :raises ServiceUnavailableError: If Nominatim fails; the CSV is left unchanged
    """
    temp_fd, temp_path = tempfile.mkstemp()
    os.close(temp_fd)

    total = 0
    success = 0
    failed_addresses = []
    findings = {"not_found": [], "street_only": [], "town_only": []}
    by_point = defaultdict(list)

    try:
        # utf-8-sig on both sides: reading the BOM-prefixed file as plain utf-8 kept the BOM in the
        # first header and prepended another one on every run (BACKLOG UT-H7).
        with (
            open(input_csv, encoding="utf-8-sig") as infile,
            open(temp_path, mode="w", newline="", encoding="utf-8-sig") as outfile,
        ):
            reader = csv.reader(infile, delimiter=";")
            writer = csv.writer(outfile, delimiter=";")

            headers = next(reader)
            headers[0] = headers[0].lstrip("\ufeff")

            # Check if UTM_X and UTM_Y columns are already in the headers
            if "UTM_X" in headers and "UTM_Y" in headers:
                utm_x_index = headers.index("UTM_X")
                utm_y_index = headers.index("UTM_Y")
                headers_written = True
                writer.writerow(headers)
            else:
                utm_x_index = len(headers)
                utm_y_index = len(headers) + 1
                headers_written = False
                writer.writerow(headers + ["UTM_X", "UTM_Y"])

            for number, row in enumerate(reader, start=1):
                if not any(cell.strip() for cell in row):
                    writer.writerow(row)  # blank line: kept, not counted
                    continue
                country, state, city, address = (cell.strip() for cell in (row + [""] * 4)[:4])
                full_address = f"{address}, {city}, {state}, {country}"
                if address:
                    utm_x, utm_y, precision = locate_address(full_address, to_crs=crs)  # rate-limited
                else:
                    # Without a street Nominatim answers with the town centre
                    utm_x, utm_y, precision = None, None, None

                total += 1
                item = {"number": number, "address": ", ".join(p for p in (address or "(keine Adresse)", city) if p)}
                if utm_x is not None and utm_y is not None:
                    success += 1
                    item.update(x=utm_x, y=utm_y)
                    if precision == PRECISION_STREET:
                        findings["street_only"].append(item)
                    elif precision == PRECISION_TOWN:
                        findings["town_only"].append(item)
                    by_point[(round(utm_x, _SAME_POINT_DECIMALS), round(utm_y, _SAME_POINT_DECIMALS))].append(item)
                else:
                    failed_addresses.append(full_address)
                    findings["not_found"].append(item)

                if headers_written:
                    # Ensure the row has enough columns before assignment
                    if len(row) > utm_x_index:
                        row[utm_x_index] = utm_x
                    else:
                        row.extend([utm_x])
                    if len(row) > utm_y_index:
                        row[utm_y_index] = utm_y
                    else:
                        row.extend([utm_y])
                else:
                    row.extend([utm_x, utm_y])

                writer.writerow(row)

        # Replace the original file with the updated temporary file using shutil.move
        shutil.move(temp_path, input_csv)
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

    return {
        "total": total,
        "success": success,
        "failed": total - success,
        "failed_addresses": failed_addresses,
        **findings,
        "same_point": [group for group in by_point.values() if len(group) > 1],
    }


if __name__ == "__main__":
    # File name of the data file with addresses
    input_csv = "data/data_geocoded.csv"  # dummy file name, replace with actual file path

    # Call the process_data function to read from input_csv and write to
    # process_data(input_csv)
