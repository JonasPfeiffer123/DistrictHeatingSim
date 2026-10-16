"""
Infrastructure costs from the network (user test 2026-10-08, UT-M11).

The cost table held flat placeholders (network 2 Mio. €) that went into every generator
calculation unless "Kosten aus geoJSON berechnen" was clicked; the columns were not explained.
"""

import json

import pytest

from districtheatingsim.gui.EnergySystemTab.infrastructure_costs import (
    PLACEHOLDER_COSTS,
    estimate_infrastructure_costs,
    network_quantities,
)


def _network(tmp_path, with_loads=True):
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[0, 0], [300, 400]]},  # 500 m, no stored length
            "properties": {"feature_type": "network_line_flow"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 0]]},
            "properties": {"feature_type": "network_line_flow", "calculated": {"length_m": 700.0}},
        },
        {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 0]]},
            "properties": {"feature_type": "network_line_return", "calculated": {"length_m": 1200.0}},
        },
    ]
    for load in (120_000, 80_000):
        data = {"Adresse": "Markt 1", **({"heat_demand_W": load} if with_loads else {})}
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[0, 0], [5, 0]]},
                "properties": {"feature_type": "building_connection", "building_data": data},
            }
        )
    variant = tmp_path / "Variante 1"
    (variant / "Wärmenetz").mkdir(parents=True)
    path = variant / "Wärmenetz" / "Wärmenetz.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    return str(variant), str(path)


def test_quantities_and_estimates(tmp_path):
    _variant, path = _network(tmp_path)
    assert network_quantities(path) == (1200.0, 200.0)  # flow route only; the return line is not counted
    assert estimate_infrastructure_costs(path) == {
        "Wärmenetz": (1_200_000.0, "Wärmenetz: 1.200 m Trasse × 1.000 €/m (inkl. Tiefbau)"),
        "Hausanschlussstationen": (50_000.0, "Hausanschlussstationen: 200 kW × 250 €/kW"),
    }


def test_network_not_calculated_yet_has_no_station_loads(tmp_path):
    _variant, path = _network(tmp_path, with_loads=False)
    assert network_quantities(path) == (1200.0, None)
    assert list(estimate_infrastructure_costs(path)) == ["Wärmenetz"]
    assert estimate_infrastructure_costs(str(tmp_path / "fehlt.geojson")) == {}


@pytest.fixture
def cost_tab(qapp):
    from PyQt6.QtCore import QObject, pyqtSignal
    from PyQt6.QtWidgets import QWidget

    from districtheatingsim.gui.EnergySystemTab._05_cost_tab import CostTab

    class Folders(QObject):
        project_folder_changed = pyqtSignal(str)
        variant_folder = None

    class Parent(QWidget):
        economic_parameters = {
            "gas_price": 70.0,
            "electricity_price": 150.0,
            "wood_price": 50.0,
            "capital_interest_rate": 1.05,
            "inflation_rate": 1.03,
            "time_period": 20,
            "hourly_rate": 45.0,
            "subsidy_eligibility": "Nein",
        }

    parent = Parent()
    tab = CostTab(Folders(), None, parent)
    yield tab
    tab.deleteLater()
    parent.deleteLater()


def test_placeholders_are_replaced_and_named(cost_tab, tmp_path):
    variant, _path = _network(tmp_path)
    cost_tab.updateDefaultPath(variant)
    data = cost_tab.data
    assert data.at["Wärmenetz", "Kosten"] == 1_200_000.0
    assert data.at["Hausanschlussstationen", "Kosten"] == 50_000.0
    assert data.at["Summe Infrastruktur", "Kosten"] == pytest.approx(
        1_200_000
        + 50_000
        + sum(v for k, v in PLACEHOLDER_COSTS.items() if k not in ("Wärmenetz", "Hausanschlussstationen"))
    )
    hint = cost_tab.costHintLabel.text()
    assert "Aus dem Netz geschätzt: Wärmenetz: 1.200 m Trasse" in hint
    assert (
        "Pauschalwerte, bitte an das Projekt anpassen: Druckhaltung, Hydraulik, Elektroinstallation, Planungskosten."
        in hint
    )
    header = cost_tab.infrastructureCostsTable.horizontalHeaderItem(list(data.columns).index("F_inst"))
    assert "Instandsetzung" in header.toolTip()


def test_values_the_user_entered_stay(cost_tab, tmp_path):
    variant, _path = _network(tmp_path)
    cost_tab.data.at["Wärmenetz", "Kosten"] = 1_750_000
    cost_tab.updateDefaultPath(variant)
    assert cost_tab.data.at["Wärmenetz", "Kosten"] == 1_750_000
    assert cost_tab.data.at["Hausanschlussstationen", "Kosten"] == 50_000.0
