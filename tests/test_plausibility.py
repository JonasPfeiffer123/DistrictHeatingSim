"""
Plausibility traffic light (user test 2026-10-08, M15, report stage 4).

An implausible result - 773 m² of collector with a 16 m³ storage - was shown like any other.
The checks rate it next to the numbers and say which threshold applies and where it comes from.
"""

from types import SimpleNamespace

import numpy as np
import pytest

from districtheatingsim.utilities.plausibility import format_value, generator_checks, network_checks


def _by_name(checks):
    return {c.name: c for c in checks}


class TestNetworkChecks:
    def test_loss_share_and_heat_density(self):
        checks = _by_name(network_checks({"rel. Verteilverluste [%]": 18.1, "Wärmebedarfsdichte [MWh/(a*m)]": 2.4}))
        assert checks["Wärmeverluste des Netzes"].rating == "warn"  # QM Holzheizwerke: at most 10 %
        assert checks["Wärmebelegungsdichte"].rating == "ok"  # at least 1.8 MWh/(m·a)
        assert "QM Holzheizwerke" in checks["Wärmeverluste des Netzes"].hint

    @pytest.mark.parametrize(
        ("share", "rating"), [(8.0, "ok"), (10.0, "ok"), (15.0, "warn"), (20.0, "warn"), (39.4, "bad")]
    )
    def test_loss_share_ratings(self, share, rating):
        (check,) = network_checks({"rel. Verteilverluste [%]": share})
        assert check.rating == rating

    @pytest.mark.parametrize(("density", "rating"), [(1.8, "ok"), (1.0, "warn"), (0.5, "warn"), (0.3, "bad")])
    def test_heat_density_ratings(self, density, rating):
        (check,) = network_checks({"Wärmebedarfsdichte [MWh/(a*m)]": density})
        assert check.rating == rating

    @pytest.mark.parametrize("share", [-5.0, None, float("nan"), 100.0])
    def test_loss_share_of_a_part_of_the_year_is_left_out(self, share):
        # A short time series compares its generation with the annual demand (negative share)
        assert network_checks({"rel. Verteilverluste [%]": share}) == []

    def test_pressure_loss_against_the_sizing_limit(self):
        (within,) = network_checks({}, max_loss_pa_per_m=290.0, loss_limit_pa_per_m=300.0)
        (above,) = network_checks({}, max_loss_pa_per_m=687.0, loss_limit_pa_per_m=300.0)
        (unlimited,) = network_checks({}, max_loss_pa_per_m=687.0)
        assert (within.rating, above.rating, unlimited.rating) == ("ok", "warn", "info")


def _solar(area, volume, name="Solarthermie_1"):
    return SimpleNamespace(name=name, bruttofläche_STA=area, vs=volume)


class TestGeneratorChecks:
    def test_the_user_tests_solar_plant_is_implausible(self):
        (check,) = generator_checks([_solar(773.0, 16.0)], {})
        assert check.value == pytest.approx(16000 / 773)
        assert check.rating == "bad"
        assert format_value(check) == "21 l/m²"

    @pytest.mark.parametrize(("volume", "rating"), [(50.0, "ok"), (30.0, "warn"), (20.0, "bad")])
    def test_storage_per_collector_ratings(self, volume, rating):
        (check,) = generator_checks([_solar(1000.0, volume)], {})
        assert check.rating == rating

    def test_full_load_hours_are_information(self):
        results = {
            "techs": ["BHKW_1", "Gaskessel_1", "Ungedeckter Bedarf"],
            "Wärmemengen": [800.0, 50.0, 1.0],
            "Wärmeleistung_L": [np.full(8760, 100.0), np.r_[np.zeros(8759), 500.0], np.ones(8760)],
        }
        checks = _by_name(generator_checks([SimpleNamespace(name="BHKW_1")], results))
        assert checks["BHKW_1: Volllaststunden"].value == pytest.approx(8000.0)
        assert checks["Gaskessel_1: Volllaststunden"].value == pytest.approx(100.0)
        assert all(c.rating == "info" for c in checks.values())
        assert "Ungedeckter Bedarf: Volllaststunden" not in checks

    def test_generator_without_heat_is_left_out(self):
        results = {"techs": ["PtH_1"], "Wärmemengen": [0.0], "Wärmeleistung_L": [np.zeros(8760)]}
        assert generator_checks([], results) == []


def test_german_number_format():
    (check,) = network_checks({"Wärmebedarfsdichte [MWh/(a*m)]": 1.2345})
    assert format_value(check) == "1,23 MWh/(m·a)"


def test_results_tab_shows_the_traffic_light(qapp):
    from PyQt6.QtWidgets import QTableWidget

    from districtheatingsim.gui.EnergySystemTab._07_results_tab import ResultsTab
    from districtheatingsim.utilities.plausibility import RATING_COLORS

    table = QTableWidget()
    table.setColumnCount(3)
    system = SimpleNamespace(technologies=[_solar(773.0, 16.0)], results={})
    tab = SimpleNamespace(energy_system=system, plausibilityTable=table, adjustTableSize=lambda t: None)
    ResultsTab.showPlausibility(tab)
    assert table.rowCount() == 1
    assert table.item(0, 1).text() == "21 l/m²"
    assert table.item(0, 2).text() == "● unplausibel"
    assert table.item(0, 2).foreground().color().name() == RATING_COLORS["bad"]
    assert "50-100 l/m²" in table.item(0, 0).toolTip()


def test_network_panel_shows_the_traffic_light(qapp):
    import pandas as pd
    from PyQt6.QtWidgets import QLabel

    from districtheatingsim.gui.NetSimulationTab.network_info_panel import NetworkInfoPanel

    net = SimpleNamespace(
        pipe=pd.DataFrame({"length_km": [0.1], "sections": [5]}),
        res_pipe=pd.DataFrame({"dp_friction_loss_bar": [0.06]}),  # 5 x 0.06 bar over 100 m = 300 Pa/m
    )
    data = SimpleNamespace(
        net=net,
        kpi_results={"Trassenlänge ohne Hausanschlüsse [m]": 900.0, "rel. Verteilverluste [%]": 39.4},
        diameter_optimization_pipe_checked=True,
        max_pressure_loss_pipe=300.0,
    )
    panel = NetworkInfoPanel()
    panel.update(data)
    texts = [label.text() for label in panel.findChildren(QLabel)]
    assert "Plausibilität" in texts
    assert "Wärmeverluste des Netzes" in texts and "● unplausibel" in texts
    assert "300 Pa/m" in texts and "● plausibel" in texts
