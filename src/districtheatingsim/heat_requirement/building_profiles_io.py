"""
Read and write the building load profiles file ("Gebäude Lastgang").
=====================================================================

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

The file used to be indented JSON (~1.75 MB per building). It is now written in the
array-store Parquet format (``utilities/array_store``, ~8× smaller, faster to load) with the
same content. Reading accepts both — the format is detected from the file, not its name — so
projects saved earlier keep working (BACKLOG G7).
"""

import json
import os

from districtheatingsim.utilities import array_store
from districtheatingsim.utilities.schema import add_meta


def read_building_profiles(path: str) -> dict:
    """
    Load a building load profiles file (array store or legacy JSON).

    :param path: File to read
    :type path: str
    :return: The stored dict, exactly as ``json.load`` returned it for the JSON format
    :rtype: dict
    """
    return array_store.load_json_compatible(path)


def write_building_profiles(path: str, combined_data: dict) -> None:
    """
    Write building load profiles, stamped with the ``_meta`` schema block.

    A path ending in ``.json`` still writes the legacy JSON (explicit export); any other path
    writes the array-store Parquet format.

    :param path: Target file
    :type path: str
    :param combined_data: Building data + profiles, keyed by building index as string
    :type combined_data: dict
    """
    data = add_meta(combined_data, "building_data")
    if path.lower().endswith(".json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    else:
        array_store.dump(data, path)


def current_format_path(path: str) -> str:
    """The array-store counterpart (same folder and name, ``.parquet``) of a profiles file."""
    return os.path.splitext(path)[0] + ".parquet"


def preferred_profiles_path(current_path: str, legacy_path: str) -> str:
    """
    The profiles file to read by default: the newer of the current-format and the legacy file.

    An older app version may have written the legacy JSON after this one wrote the Parquet
    file. If neither exists, the current-format path is returned.

    :param current_path: Array-store file (current format)
    :type current_path: str
    :param legacy_path: Legacy JSON file
    :type legacy_path: str
    :return: Path to read from
    :rtype: str
    """
    if os.path.exists(legacy_path) and (
        not os.path.exists(current_path) or os.path.getmtime(legacy_path) > os.path.getmtime(current_path)
    ):
        return legacy_path
    return current_path
