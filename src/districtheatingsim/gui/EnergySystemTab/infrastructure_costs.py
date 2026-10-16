"""
Infrastructure costs from the generated network (user test 2026-10-08, UT-M11).

The cost table started with flat placeholders (network 2 Mio. €, planning 0.5 Mio. €) that went
into every generator calculation unless "Kosten aus geoJSON berechnen" was clicked, and the columns
"T_N, F_inst, F_w_insp" were not explained. The network and house-station costs are now estimated
from the network as soon as one exists (only where the table still holds the placeholder), the
remaining flat values are named as such.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

#: Specific costs of the estimates (the defaults of the "aus geoJSON berechnen" dialogs)
NETWORK_COST_PER_M = 1000.0  # € per metre of route incl. civil works
STATION_COST_PER_KW = 250.0  # € per kW of maximum heat demand

#: The flat values the table starts with
PLACEHOLDER_COSTS = {
    "Wärmenetz": 2_000_000,
    "Hausanschlussstationen": 100_000,
    "Druckhaltung": 20_000,
    "Hydraulik": 40_000,
    "Elektroinstallation": 15_000,
    "Planungskosten": 500_000,
}

#: Explanations of the table columns (tooltips)
COLUMN_HINTS = {
    "Kosten": "Investition in €",
    "T_N": "Nutzungsdauer in Jahren",
    "F_inst": "Aufwand für Instandsetzung in % der Investition pro Jahr (VDI 2067)",
    "F_w_insp": "Aufwand für Wartung und Inspektion in % der Investition pro Jahr (VDI 2067)",
    "Bedienaufwand": "Bedienaufwand in Stunden pro Jahr",
    "Annuität": "Jährliche Kosten in €/a aus Kapital, Instandsetzung, Wartung und Bedienung (VDI 2067)",
}


def _line_length_m(feature: dict) -> float:
    calculated = (feature.get("properties") or {}).get("calculated") or {}
    if calculated.get("length_m"):
        return float(calculated["length_m"])
    coordinates = (feature.get("geometry") or {}).get("coordinates") or []
    return sum(
        ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        for (x1, y1, *_), (x2, y2, *_) in zip(coordinates, coordinates[1:], strict=False)
    )


def network_quantities(geojson_path: str) -> tuple[float, float | None] | None:
    """
    Route length and connected load of a unified network GeoJSON.

    :return: ``(route length in m, sum of the house stations' maximum heat demand in kW or None if
        the network has not been calculated yet)``, or None without a readable network.
    """
    if not geojson_path or not os.path.exists(geojson_path):
        return None
    try:
        with open(geojson_path, encoding="utf-8") as file:
            features = json.load(file).get("features", [])
    except (OSError, ValueError) as e:
        logger.warning("Netz für die Kostenschätzung nicht lesbar: %s", e)
        return None
    route = sum(
        _line_length_m(f) for f in features if (f.get("properties") or {}).get("feature_type") == "network_line_flow"
    )
    loads = [
        (f["properties"].get("building_data") or {}).get("heat_demand_W")
        for f in features
        if (f.get("properties") or {}).get("feature_type") == "building_connection"
    ]
    connected_kw = sum(float(w) for w in loads if w) / 1000 if loads and all(loads) else None
    return route, connected_kw


def estimate_infrastructure_costs(geojson_path: str) -> dict[str, tuple[float, str]]:
    """
    Network and house-station costs estimated from the network.

    :return: ``{component: (cost in €, German note)}``; empty without a network.
    """
    quantities = network_quantities(geojson_path)
    if not quantities:
        return {}
    route, connected_kw = quantities
    estimates = {}
    if route > 0:
        estimates["Wärmenetz"] = (
            round(route * NETWORK_COST_PER_M, -3),
            f"Wärmenetz: {route:,.0f} m Trasse × {NETWORK_COST_PER_M:,.0f} €/m (inkl. Tiefbau)".replace(",", "."),
        )
    if connected_kw:
        estimates["Hausanschlussstationen"] = (
            round(connected_kw * STATION_COST_PER_KW, -2),
            f"Hausanschlussstationen: {connected_kw:,.0f} kW × {STATION_COST_PER_KW:,.0f} €/kW".replace(",", "."),
        )
    return estimates
