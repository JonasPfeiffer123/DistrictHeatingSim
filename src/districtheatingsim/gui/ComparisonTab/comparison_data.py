"""
GUI-free data layer for the variant comparison tab.

Pure discovery / loading / transform logic extracted from ``comparison_tab.py``
so it is unit-testable without Qt (BACKLOG B1/B2). The Qt widgets in
``comparison_tab.py`` are thin glue over these functions:

* :func:`discover_variant_configs` / :func:`variant_has_results` — filesystem
  scan of a variant's ``Ergebnisse/`` folder.
* :func:`load_network_kpis` — read the network KPI block from a variant.
* :func:`process_variant_results` — normalise a raw result dict for the dashboard.
* :func:`format_kpi_range` — summarise one KPI across the compared variants.
* :func:`clean_variant_name` — shorten a variant's display name for chart labels.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import json
import logging
import os

from districtheatingsim.gui.EnergySystemTab.config_naming import filename_to_config_name


def format_kpi_range(variant_data: list[dict], key: str, fmt: str, *, empty: str = "--") -> str:
    """
    Summarize one KPI across the compared variants for the dashboard.

    Filters out missing / zero values, then returns a single formatted number, a
    ``"min - max"`` range when several variants differ, or ``empty`` when no
    variant provides the value.

    :param variant_data: One result dict per variant.
    :param key: The metric key to read from each variant dict.
    :param fmt: A ``format()`` spec applied to each number (e.g. ``".1f"``).
    :param empty: Text to show when no variant provides the metric.
    :return: The formatted value / range / ``empty`` string.
    :rtype: str
    """
    values = [v.get(key, 0) for v in variant_data if v.get(key, 0) not in (None, 0)]
    if not values:
        return empty
    if len(values) == 1:
        return format(values[0], fmt)
    return f"{format(min(values), fmt)} - {format(max(values), fmt)}"


def clean_variant_name(full_name: str) -> str:
    """
    Extract a short variant name from a full project-path name for chart labels.

    :param full_name: The variant's display name (possibly ``"Project - Variant"``).
    :return: The part after the last ``" - "``, or the name unchanged.
    :rtype: str
    """
    if " - " in full_name:
        return full_name.split(" - ")[-1]
    return full_name


def discover_variant_configs(variant_path: str) -> list[tuple[str, str]]:
    """
    Return all energy-system configs in a variant as ``(config_name, filename)``.

    :param variant_path: Absolute path to the variant folder.
    :return: List of ``(config_name, filename)`` tuples, ``Standard`` first.
    :rtype: list[tuple[str, str]]
    """
    ergebnisse_dir = os.path.join(variant_path, "Ergebnisse")
    configs: list[tuple[str, str]] = []
    if not os.path.isdir(ergebnisse_dir):
        return configs
    files = sorted(os.listdir(ergebnisse_dir))
    if "Ergebnisse.json" in files:
        configs.append(("Standard", "Ergebnisse.json"))
    for f in files:
        if f.startswith("Ergebnisse_") and f.endswith(".json"):
            configs.append((filename_to_config_name(f), f))
    return configs


def variant_has_results(variant_path: str) -> bool:
    """
    Whether a variant has at least one energy-system result file.

    :param variant_path: Path to the variant folder.
    :return: ``True`` if the variant is usable for comparison.
    :rtype: bool
    """
    ergebnisse_dir = os.path.join(variant_path, "Ergebnisse")
    return os.path.isdir(ergebnisse_dir) and any(
        f.startswith("Ergebnisse") and f.endswith(".json") for f in os.listdir(ergebnisse_dir)
    )


def load_network_kpis(variant_path: str) -> dict:
    """
    Load the network KPI block (length, losses, pump energy, building count).

    Network KPIs live in the variant's ``Wärmenetz`` config and are shared across
    that variant's energy-system configs. Missing/unreadable data yields zeros.

    :param variant_path: Path to the variant folder.
    :return: Network KPI dict with keys ``Trassenlänge``, ``Verteilverluste``,
        ``Pumpenenergie``, ``Anzahl_Gebäude``.
    :rtype: dict
    """
    network_data = {"Trassenlänge": 0, "Verteilverluste": 0, "Pumpenenergie": 0, "Anzahl_Gebäude": 0}
    try:
        config_path = os.path.join(variant_path, "Wärmenetz", "Konfiguration Netzinitialisierung.json")
        if not os.path.exists(config_path):
            return network_data
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        kpi_results = config.get("kpi_results", {})
        network_data["Trassenlänge"] = kpi_results.get("Trassenlänge Wärmenetz [m]", 0)
        network_data["Verteilverluste"] = kpi_results.get("rel. Verteilverluste [%]", 0)
        network_data["Pumpenenergie"] = kpi_results.get("Pumpenstrom [MWh]", 0)
        network_data["Anzahl_Gebäude"] = kpi_results.get("Anzahl angeschlossene Gebäude", 0)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        logging.warning("Konnte Netz-KPIs der Variante nicht lesen: %s", e)
    return network_data


def process_variant_results(results: dict) -> dict:
    """
    Normalise a raw energy-system result dict for dashboard display.

    Rounds the per-tech and aggregate metrics, converts shares to percent and
    reconciles ``primärenergiefaktor_Gesamt`` (which may be a scalar or a per-tech
    list) against the number of heat quantities.

    :param results: Raw results from a variant's ``Ergebnisse*.json``.
    :return: Processed results ready for the dashboard.
    :rtype: dict
    :raises ValueError: If processing fails.
    """
    try:
        # Handle primärenergiefaktor_Gesamt which can be float or list
        pe_gesamt = results.get("primärenergiefaktor_Gesamt", 0)
        waermemengen = results.get("Wärmemengen", [])

        if isinstance(pe_gesamt, (float, int)):
            pe_gesamt = [pe_gesamt] * len(waermemengen) if waermemengen else [pe_gesamt]
        elif isinstance(pe_gesamt, list):
            if len(pe_gesamt) != len(waermemengen) and waermemengen:
                pe_gesamt = pe_gesamt * len(waermemengen) if pe_gesamt else [0] * len(waermemengen)

        processed_results = {
            "techs": results.get("techs", []),
            "Wärmemengen": [round(w, 2) for w in waermemengen],
            "WGK": [round(w, 2) for w in results.get("WGK", [])],
            "Anteile": [round(a * 100, 2) for a in results.get("Anteile", [])],
            "colors": results.get("colors", []),
            "specific_emissions_L": [round(e, 4) for e in results.get("specific_emissions_L", [])],
            "primärenergie_L": [round(pe / w, 4) if w else 0 for pe, w in zip(pe_gesamt, waermemengen, strict=False)],
            "Jahreswärmebedarf": round(results.get("Jahreswärmebedarf", 0), 1),
            "Strommenge": round(results.get("Strommenge", 0), 2),
            "Strombedarf": round(results.get("Strombedarf", 0), 2),
            "WGK_Gesamt": round(results.get("WGK_Gesamt", 0), 2),
            "specific_emissions_Gesamt": round(results.get("specific_emissions_Gesamt", 0), 4),
            "primärenergiefaktor_Gesamt": round(results.get("primärenergiefaktor_Gesamt", 0), 4),
        }

        return processed_results

    except Exception as e:
        raise ValueError(f"Error processing results: {e}") from e
