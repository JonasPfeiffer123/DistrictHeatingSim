"""
Calculation state of a variant: which result was computed from what (user test 2026-10-08, UT-H10).

Results went stale without notice: a variant copy took over every generator result, and after the
buildings, the load profiles or the network changed, the old numbers still showed in the variant
comparison. File times cannot tell - every project save rewrites the building CSV, the network
files and the generator results.

Each calculation step therefore records a *stamp* when it computes (not when it saves) in
``<variant>/Berechnungsstand.json``: a fresh id and what it was computed from - the fingerprint of
the building data and the climate settings for the building load profiles, the id of the
upstream stamp for every later step::

    Gebäude → Gebäudelastgänge → Netzberechnung → Jahreszeitreihe → Erzeugung: <Konfiguration>

:func:`outdated_results` compares the stamps with the current state. Projects saved before this
file existed have no stamps; nothing is reported for them rather than guessed.

:author: M.Eng. Jonas Pfeiffer
"""

import datetime
import hashlib
import json
import logging
import os
import uuid

logger = logging.getLogger(__name__)

STATE_FILENAME = "Berechnungsstand.json"

BUILDING_PROFILES = "Gebäudelastgänge"
NETWORK_CALCULATION = "Netzberechnung"
TIME_SERIES = "Jahreszeitreihe"
_GENERATION_PREFIX = "Erzeugung: "

#: Columns of the building list the heat demand calculation reads
HEAT_DEMAND_COLUMNS = (
    "Wärmebedarf",
    "Gebäudetyp",
    "Subtyp",
    "WW_Anteil",
    "Normaußentemperatur",
    "VLT_max",
    "RLT_max",
    "Steigung_Heizkurve",
    "Heizgrenztemperatur",
    "Heizexponent",
    "P_max",
)


def generation_key(config_name: str) -> str:
    """State key of an energy-system config ("Erzeugung: Standard")."""
    return f"{_GENERATION_PREFIX}{config_name}"


def new_stamp(inputs: dict, **details) -> dict:
    """A stamp for a result computed just now from ``inputs``."""
    stamp = {
        "id": uuid.uuid4().hex,
        "berechnet": datetime.datetime.now().isoformat(timespec="seconds"),
        "eingaben": inputs,
    }
    stamp.update(details)
    return stamp


def stamp_id(stamp: dict | None) -> str | None:
    return stamp.get("id") if isinstance(stamp, dict) else None


def read_state(variant_folder: str) -> dict:
    """The stamps of a variant (empty if there are none or the file is unreadable)."""
    path = os.path.join(variant_folder or "", STATE_FILENAME)
    if not variant_folder or not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError) as e:
        logger.warning("Berechnungsstand %s nicht lesbar: %s", path, e)
        return {}
    return data if isinstance(data, dict) else {}


def record(variant_folder: str, key: str, stamp: dict | None) -> None:
    """
    Store (or with ``None`` remove) the stamp of one result of a variant.

    Best effort: a failing write is logged, the calculation itself must not fail on it.
    """
    if not variant_folder or not os.path.isdir(variant_folder):
        return
    state = read_state(variant_folder)
    if stamp is None:
        if key not in state:
            return
        state.pop(key)
    else:
        state[key] = stamp
    try:
        with open(os.path.join(variant_folder, STATE_FILENAME), "w", encoding="utf-8") as file:
            json.dump(state, file, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.warning("Berechnungsstand in %s nicht gespeichert: %s", variant_folder, e)


def _normalised(value) -> str:
    text = "" if value is None else str(value).strip()
    if text.lower() in ("nan", "none"):
        return ""
    try:
        return format(float(text.replace(",", ".")), ".10g")
    except ValueError:
        return text


def building_data_fingerprint(table) -> str:
    """
    Fingerprint of what the heat demand calculation reads from a building table.

    Addresses and coordinates do not count (geocoding must not make the load profiles stale);
    numbers count by value ("03" = "3", "0,2" = "0.2"); empty rows and optional columns that are
    empty throughout do not count either (the building tab's table and the CSV differ in both).

    :param table: The building table (``pandas.DataFrame``).
    """
    columns = [column for column in HEAT_DEMAND_COLUMNS if column in table.columns]
    rows = [[_normalised(value) for value in row] for row in table[columns].itertuples(index=False)]
    rows = [row for row in rows if any(row)]
    used = [index for index, _column in enumerate(columns) if any(row[index] for row in rows)]
    payload = json.dumps([[columns[i] for i in used], [[row[i] for i in used] for row in rows]], ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def building_csv_fingerprint(csv_path: str) -> str | None:
    """:func:`building_data_fingerprint` of a building CSV (None if it cannot be read)."""
    import pandas as pd

    if not csv_path or not os.path.exists(csv_path):
        return None
    try:
        table = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        logger.warning("Gebäudedaten %s nicht lesbar: %s", csv_path, e)
        return None
    table.columns = [str(column).lstrip("﻿") for column in table.columns]
    return building_data_fingerprint(table)


def climate_settings(try_filename: str | None, year, climate_zone, persons_per_household) -> dict:
    """The project settings the building load profiles depend on, as stored in a stamp."""
    return {
        "TRY": os.path.basename(try_filename) if try_filename else "",
        "Jahr": int(year) if year is not None else None,
        "Klimazone": str(climate_zone),
        "Personen je Haushalt": int(persons_per_household) if persons_per_household is not None else None,
    }


def network_building_mismatch(network_path: str, building_csv: str) -> str | None:
    """
    Whether the generated network still has one house connection per geocoded building.

    :return: A German reason, or None if the counts agree (or a file is missing/unreadable).
    """
    from districtheatingsim.net_generation.network_connectivity import building_connection_features
    from districtheatingsim.utilities.crs_utils import read_building_coordinates

    if not (os.path.exists(network_path) and os.path.exists(building_csv)):
        return None
    try:
        with open(network_path, encoding="utf-8") as file:
            connections = len(building_connection_features(json.load(file)))
        buildings = len(read_building_coordinates(building_csv)[0])
    except Exception as e:  # noqa: BLE001 - a broken file is reported elsewhere
        logger.warning("Netz/Gebäude-Abgleich nicht möglich: %s", e)
        return None
    if connections == buildings:
        return None
    return (
        f"Die Gebäudeliste hat {buildings} Gebäude mit Koordinaten, das Wärmenetz {connections} Hausanschlüsse "
        "– das Netz neu generieren."
    )


def outdated_results(
    variant_folder: str,
    building_csv: str | None = None,
    climate: dict | None = None,
    configs: list[str] | None = None,
) -> dict[str, str]:
    """
    The results of a variant that no longer match what they were computed from.

    :param variant_folder: The variant.
    :param building_csv: The project's building list (for the load profiles' fingerprint).
    :param climate: Current :func:`climate_settings` of the project.
    :param configs: Energy-system configs to check (default: all with a stamp).
    :return: ``{state key: German reason}``; empty if everything is current or unknown.
    """
    state = read_state(variant_folder)
    reasons: dict[str, str] = {}

    profiles = state.get(BUILDING_PROFILES)
    if profiles:
        inputs = profiles.get("eingaben", {})
        fingerprint = building_csv_fingerprint(building_csv) if building_csv else None
        if fingerprint and inputs.get("Gebäudedaten") and fingerprint != inputs["Gebäudedaten"]:
            reasons[BUILDING_PROFILES] = "Die Gebäudedaten wurden nach der Lastgangberechnung geändert."
        elif climate and inputs.get("Klimadaten") and inputs["Klimadaten"] != climate:
            changed = [name for name, value in climate.items() if inputs["Klimadaten"].get(name) != value]
            reasons[BUILDING_PROFILES] = f"Nach der Lastgangberechnung geändert: {', '.join(changed)}."

    network = state.get(NETWORK_CALCULATION)
    if network and profiles:
        used = network.get("eingaben", {}).get(BUILDING_PROFILES)
        if used and used != stamp_id(profiles):
            reasons[NETWORK_CALCULATION] = "Die Gebäudelastgänge wurden nach der Netzberechnung neu berechnet."
        elif BUILDING_PROFILES in reasons:
            reasons[NETWORK_CALCULATION] = "Sie beruht auf veralteten Gebäudelastgängen."

    series = state.get(TIME_SERIES)
    if series and network:
        used = series.get("eingaben", {}).get(NETWORK_CALCULATION)
        if used and used != stamp_id(network):
            reasons[TIME_SERIES] = "Das Netz wurde nach der Jahreszeitreihe neu berechnet."
        elif NETWORK_CALCULATION in reasons:
            reasons[TIME_SERIES] = "Sie beruht auf einer veralteten Netzberechnung."

    if configs is None:
        configs = [key[len(_GENERATION_PREFIX) :] for key in state if key.startswith(_GENERATION_PREFIX)]
    for config in configs:
        generation = state.get(generation_key(config))
        if not (generation and series):
            continue
        used = generation.get("eingaben", {}).get(TIME_SERIES)
        if used and used != stamp_id(series):
            reasons[generation_key(config)] = "Die Jahreszeitreihe wurde nach der Erzeugerberechnung neu berechnet."
        elif TIME_SERIES in reasons:
            reasons[generation_key(config)] = "Sie beruht auf einer veralteten Jahreszeitreihe."
    return reasons
