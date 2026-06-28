"""
GUI-free project-progress evaluation for the project definition tab (BACKLOG B1).

The project tab shows a step-by-step completion tracker (Quartier-CSV → load
profile → streets → network → simulation → generator mix). Deciding which steps
are done is pure filesystem/CSV logic; it was buried inside
``ProjectPresenter.update_progress_tracker`` next to the Qt view calls. Extracted
here so it is unit-testable without a QApplication. The presenter is now a thin
caller that pushes the result into the view.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import csv
import json
import logging
import os

# Network whose "dimensioned" flag a step may additionally require (relative to base_path).
_DIMENSIONED_NETWORK_FILE = "Wärmenetz/Wärmenetz.geojson"


def check_csv_status(csv_file_path: str) -> str:
    """
    Classify the Quartier CSV: missing, present, or present-with-coordinates.

    :param csv_file_path: Path to the building CSV to check.
    :return: ``"fehlt"``, ``"ist vorhanden"`` or ``"mit Koordinaten"``.
    :rtype: str
    """
    if not os.path.exists(csv_file_path):
        return "fehlt"

    try:
        with open(csv_file_path, encoding="utf-8", errors="ignore") as file:
            # Use semicolon delimiter to match the CSV format
            reader = csv.DictReader(file, delimiter=";")
            headers = reader.fieldnames

            if not headers:
                return "ist vorhanden"

            # Check if UTM coordinate columns exist
            coord_columns = ["UTM_X", "UTM_Y"]
            has_coord_headers = all(col in headers for col in coord_columns)

            if not has_coord_headers:
                return "ist vorhanden"

            # Check if coordinate columns have data
            for row in reader:
                if "UTM_X" in row and "UTM_Y" in row and row["UTM_X"] and row["UTM_Y"]:
                    if row["UTM_X"].strip() and row["UTM_Y"].strip():
                        try:
                            float(row["UTM_X"])
                            float(row["UTM_Y"])
                            return "mit Koordinaten"  # Found at least one valid coordinate pair
                        except ValueError:
                            continue
                # Only check first few rows for performance
                break

            return "ist vorhanden"  # Has headers but no valid coordinate data

    except (OSError, csv.Error, UnicodeDecodeError, ValueError) as e:
        # If we can't read the CSV, assume it exists but is problematic — but log it,
        # so a corrupt/locked CSV is not silently reported as "ist vorhanden".
        logging.warning("Konnte CSV-Status von %s nicht lesen: %s", csv_file_path, e)
        return "ist vorhanden"


def check_network_dimensioned(network_file_path: str) -> bool:
    """
    Whether a network GeoJSON carries ``metadata.state == "dimensioned"``.

    :param network_file_path: Path to the ``Wärmenetz.geojson`` file.
    :return: ``True`` if the network is dimensioned, ``False`` otherwise.
    :rtype: bool
    """
    if not os.path.exists(network_file_path):
        return False

    try:
        from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema

        geojson = NetworkGeoJSONSchema.import_from_file(network_file_path)

        # Check metadata for state == "dimensioned"
        metadata = geojson.get("metadata", {})
        state = metadata.get("state", "")
        return state == "dimensioned"

    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        logging.warning("Konnte Netz-Status von %s nicht lesen: %s", network_file_path, e)
        return False


def evaluate_process_steps(base_path, process_steps: list[dict]) -> tuple[str, float]:
    """
    Update each process step's completion state from the filesystem.

    Mutates every step dict in place (``completed`` / ``missing_files`` and, for the
    first step, ``csv_creation_status`` / ``geocoding_status``) so the same dicts can
    be handed to the view, and returns the headline ``(csv_status, overall_progress)``.

    :param base_path: Project base path; if falsy, every step is marked incomplete.
    :param process_steps: The presenter's process-step dicts (mutated in place).
    :return: ``(csv_status, overall_progress_percent)``.
    :rtype: tuple[str, float]
    """
    csv_status = "unbekannt"
    if base_path and process_steps:
        # CSV status: first process step (Quartier IST.csv) with detailed analysis.
        first_step = process_steps[0]
        csv_file_path = os.path.join(base_path, first_step["required_files"][0])
        csv_status = check_csv_status(csv_file_path)

        if os.path.exists(csv_file_path):
            first_step["csv_creation_status"] = "completed"
            if csv_status == "mit Koordinaten":
                first_step["geocoding_status"] = "completed"
            elif csv_status == "ist vorhanden":
                first_step["geocoding_status"] = "pending"
            else:
                first_step["geocoding_status"] = "not_applicable"
        else:
            first_step["csv_creation_status"] = "pending"
            first_step["geocoding_status"] = "not_applicable"

        for step in process_steps:
            full_paths = [os.path.join(base_path, path) for path in step["required_files"]]
            generated_files = [file for file in full_paths if os.path.exists(file)]

            # Special check for the dimensioned-network flag in Wärmenetz.geojson
            if step.get("check_dimensioned_network", False):
                network_file = os.path.join(base_path, _DIMENSIONED_NETWORK_FILE)
                network_dimensioned = check_network_dimensioned(network_file)

                step["missing_files"] = [path for path in full_paths if not os.path.exists(path)]
                if not network_dimensioned:
                    step["missing_files"].append(f"{_DIMENSIONED_NETWORK_FILE} (nicht dimensioniert)")
                    step["completed"] = False
                else:
                    step["completed"] = len(step["missing_files"]) == 0
            else:
                step["completed"] = len(generated_files) == len(full_paths)
                step["missing_files"] = [path for path in full_paths if not os.path.exists(path)]
    else:
        for step in process_steps:
            step["completed"] = False
            step["missing_files"] = step["required_files"]

    total_steps = len(process_steps)
    completed_steps = sum(1 for step in process_steps if step["completed"])
    overall_progress = (completed_steps / total_steps) * 100 if total_steps else 0.0

    return csv_status, overall_progress
