"""
GUI-free project-progress evaluation for the project definition tab (BACKLOG B1).

The project tab shows a step-by-step completion tracker (Quartier-CSV → load
profile → streets → network → simulation → generator mix). Deciding which steps
are done is pure filesystem/CSV logic; it was buried inside
``ProjectPresenter.update_progress_tracker`` next to the Qt view calls. Extracted
here so it is unit-testable without a QApplication. The presenter is now a thin
caller that pushes the result into the view.

:author: M.Eng. Jonas Pfeiffer
"""

import csv
import json
import logging
import os

from districtheatingsim.gui.EnergySystemTab.config_naming import discover_configs
from districtheatingsim.utilities.calculation_state import (
    BUILDING_PROFILES,
    NETWORK_CALCULATION,
    TIME_SERIES,
    generation_key,
    network_building_mismatch,
    outdated_results,
)

logger = logging.getLogger(__name__)

# Network whose "dimensioned" flag a step may additionally require (relative to base_path).
_DIMENSIONED_NETWORK_FILE = "Wärmenetz/Wärmenetz.geojson"

#: Files of a variant the steps look at (relative to the variant folder)
BUILDING_CSV = "../Definition Quartier IST/Quartier IST.csv"
NETWORK_FILE = _DIMENSIONED_NETWORK_FILE
RESULTS_DIR = "Ergebnisse"


def default_process_steps() -> list[dict]:
    """
    The steps of the project tab's progress tracker.

    The street download used to be a required step of its own although the OSMnx network mode loads
    the streets itself, "Schritt 3" came twice, the texts named tabs that no longer exist, and the
    generator step only counted after a CSV export (UT-M14).
    """
    return [
        {
            "key": "buildings",
            "name": "Schritt 1: Gebäude des Quartiers erfassen",
            "description": "Tab „Projektdefinition“: Gebäudeliste importieren, aus OpenStreetMap übernehmen "
            "oder von Hand anlegen, dann „Geokoordinaten berechnen“.",
            "required_files": [BUILDING_CSV],
            "csv_creation_status": "not_checked",
            "geocoding_status": "not_checked",
        },
        {
            "key": "profiles",
            "name": "Schritt 2: Gebäudelastgänge berechnen",
            "description": "Tab „Wärmebedarf Gebäude“: Gebäudedaten laden und die Lastgänge berechnen.",
            # Current Parquet file, or the JSON of projects saved before BACKLOG G7
            "required_files": [["Lastgang/Gebäude Lastgang.parquet", "Lastgang/Gebäude Lastgang.json"]],
        },
        {
            "key": "network",
            "name": "Schritt 3: Wärmenetz generieren",
            "description": "Tab „Kartenansicht Wärmenetzgenerierung“: Datei → „Wärmenetz aus Daten generieren“. "
            "Für die Modi MST und Advanced MST vorher „OSM Straßenabfrage“ ausführen; OSMnx lädt die "
            "Straßen selbst.",
            "required_files": [NETWORK_FILE],
        },
        {
            "key": "simulation",
            "name": "Schritt 4: Thermohydraulische Berechnung",
            "description": "Tab „Wärmenetzberechnung“: Netz initialisieren und dimensionieren, Jahreszeitreihe "
            "berechnen, Ergebnisse speichern.",
            "required_files": [
                # Current JSON, or the pickle of projects saved before BACKLOG G7
                ["Wärmenetz/Ergebnisse Netzinitialisierung.json", "Wärmenetz/Ergebnisse Netzinitialisierung.p"],
                "Wärmenetz/Ergebnisse Netzinitialisierung.csv",
                "Wärmenetz/Konfiguration Netzinitialisierung.json",
                "Lastgang/Lastgang.csv",
            ],
            "check_dimensioned_network": True,
        },
        {
            "key": "generation",
            "name": "Schritt 5: Erzeugermix auslegen und berechnen",
            "description": "Tab „Erzeugerauslegung und Wirtschaftlichkeitsrechnung“: Erzeuger festlegen, "
            "berechnen und die Konfiguration speichern.",
            "required_files": [],
            "check_energy_results": True,
        },
    ]


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
        logger.warning("Konnte CSV-Status von %s nicht lesen: %s", csv_file_path, e)
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
        logger.warning("Konnte Netz-Status von %s nicht lesen: %s", network_file_path, e)
        return False


def _alternatives(entry) -> list[str]:
    """A ``required_files`` entry is one path or a list of alternatives (current format first)."""
    return [entry] if isinstance(entry, str) else list(entry)


def evaluate_process_steps(base_path, process_steps: list[dict], climate: dict | None = None) -> tuple[str, float]:
    """
    Update each process step's completion state from the filesystem.

    Mutates every step dict in place (``completed`` / ``missing_files`` / ``outdated`` and, for
    the first step, ``csv_creation_status`` / ``geocoding_status``) so the same dicts can be
    handed to the view, and returns the headline ``(csv_status, overall_progress)``. An outdated
    step does not count as done (UT-H10).

    :param base_path: Project base path; if falsy, every step is marked incomplete.
    :param process_steps: The presenter's process-step dicts (mutated in place).
    :param climate: Current climate settings of the project (see ``calculation_state.climate_settings``).
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
            missing = [
                os.path.join(base_path, _alternatives(entry)[0])
                for entry in step["required_files"]
                if not any(os.path.exists(os.path.join(base_path, path)) for path in _alternatives(entry))
            ]

            # Special check for the dimensioned-network flag in Wärmenetz.geojson
            if step.get("check_dimensioned_network", False):
                network_file = os.path.join(base_path, _DIMENSIONED_NETWORK_FILE)
                network_dimensioned = check_network_dimensioned(network_file)

                step["missing_files"] = missing
                if not network_dimensioned:
                    step["missing_files"].append(f"{_DIMENSIONED_NETWORK_FILE} (nicht dimensioniert)")
                    step["completed"] = False
                else:
                    step["completed"] = len(step["missing_files"]) == 0
            elif step.get("check_energy_results", False):
                configs = discover_configs(os.path.join(base_path, RESULTS_DIR))
                step["completed"] = not missing and bool(configs)
                step["missing_files"] = missing + ([] if configs else [f"{RESULTS_DIR}/Ergebnisse.parquet"])
            else:
                step["completed"] = not missing
                step["missing_files"] = missing
        _mark_outdated(base_path, process_steps, climate)
    else:
        for step in process_steps:
            step["completed"] = False
            step["missing_files"] = [_alternatives(entry)[0] for entry in step["required_files"]]
            step["outdated"] = None

    total_steps = len(process_steps)
    completed_steps = sum(1 for step in process_steps if step["completed"] and not step.get("outdated"))
    overall_progress = (completed_steps / total_steps) * 100 if total_steps else 0.0

    return csv_status, overall_progress


def variant_outdated(base_path: str, climate: dict | None = None) -> dict:
    """
    Which results of a variant no longer fit what they were computed from (UT-H10).

    :param base_path: The variant folder.
    :param climate: Current climate settings of the project, or None to leave them out.
    :return: ``{"profiles", "network", "simulation": reason or None, "configs": {config: reason}}``.
    """
    building_csv = os.path.normpath(os.path.join(base_path, BUILDING_CSV))
    configs = [name for name, _filename in discover_configs(os.path.join(base_path, RESULTS_DIR))]
    reasons = outdated_results(base_path, building_csv, climate, configs)
    network_reason = network_building_mismatch(os.path.join(base_path, NETWORK_FILE), building_csv)
    simulation_reason = reasons.get(NETWORK_CALCULATION) or reasons.get(TIME_SERIES)
    if not simulation_reason and network_reason:
        simulation_reason = "Sie beruht auf einem Netz, das nicht mehr zur Gebäudeliste passt."
    config_reasons = {}
    for name in configs:
        reason = reasons.get(generation_key(name))
        if not reason and simulation_reason:
            reason = "Sie beruht auf einer veralteten Netzberechnung."
        if reason:
            config_reasons[name] = reason
    return {
        "profiles": reasons.get(BUILDING_PROFILES),
        "network": network_reason,
        "simulation": simulation_reason,
        "configs": config_reasons,
    }


def _mark_outdated(base_path: str, process_steps: list[dict], climate: dict | None) -> None:
    """Set ``outdated`` (German reason or None) on the steps whose results no longer fit (UT-H10)."""
    steps = {step.get("key"): step for step in process_steps}
    for step in process_steps:
        step["outdated"] = None
    if not steps.keys() & {"profiles", "network", "simulation", "generation"}:
        return
    outdated = variant_outdated(base_path, climate)
    by_reason: dict[str, list[str]] = {}
    for name, reason in outdated.pop("configs").items():
        by_reason.setdefault(reason, []).append(name)
    outdated["generation"] = " ".join(f"{', '.join(names)}: {reason}" for reason, names in by_reason.items()) or None
    for key, reason in outdated.items():
        if key in steps and steps[key]["completed"] and reason:
            steps[key]["outdated"] = reason


def outdated_summary(process_steps: list[dict]) -> str:
    """One line naming the outdated steps, or "" if none is."""
    names = [step["name"].split(":", 1)[0] for step in process_steps if step.get("outdated")]
    return f"⚠ Veraltet: {', '.join(names)} – bitte neu berechnen (Details anzeigen)." if names else ""
