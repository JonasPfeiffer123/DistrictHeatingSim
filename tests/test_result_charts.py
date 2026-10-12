"""
Result and comparison charts (user test 2026-10-08, UT-M7, UT-M10).

UT-M7: the comparison showed "--" until "Projekte aktualisieren"; the energy-mix pies collapsed to
dots next to their legends; Power-to-Heat had the gas boiler's colour.
UT-M10: the year chart started its y axis at the smallest value (a 150 kW CHP running all year was
almost invisible), and the variable list showed internal names such as "BHKW_1_betrieb_mask".
"""

from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from districtheatingsim.gui.ComparisonTab.comparison_data import TECH_COLORS, technology_color  # noqa: E402
from districtheatingsim.heat_generators.energy_system import EnergySystem, _quantity_label  # noqa: E402


class TestTechnologyColours:
    def test_every_type_has_its_own_colour(self):
        from districtheatingsim.heat_generators import TECH_CLASS_REGISTRY

        assert set(TECH_CLASS_REGISTRY) <= set(TECH_COLORS)
        assert len(set(TECH_COLORS.values())) == len(TECH_COLORS)

    def test_type_decides_over_the_saved_colour(self):
        assert technology_color("Power-to-Heat_1", "saddlebrown") == "mediumpurple"
        assert technology_color("Gaskessel_2", "saddlebrown") == "saddlebrown"
        assert technology_color("Holzgas-BHKW_1", "yellow") == "yellowgreen"
        assert technology_color("Ungedeckter Bedarf", "black") == "black"
        assert technology_color("Etwas_1") == "lightgrey"


def test_comparison_pies_share_one_legend(qapp):
    from districtheatingsim.gui.ComparisonTab.comparison_tab import ComparisonDashboard

    dashboard = ComparisonDashboard()
    dashboard.resize(1200, 800)
    variants = [
        {"name": "V1 · A", "techs": ["Gaskessel_1"], "Anteile": [100.0], "colors": ["saddlebrown"]},
        {
            "name": "V1 · B",
            "techs": ["Abwärmepumpe_1", "Power-to-Heat_1"],
            "Anteile": [90.0, 10.0],
            "colors": ["grey", "saddlebrown"],
        },
    ]
    dashboard.variant_data = variants
    dashboard.update_energy_chart()
    figure = dashboard.energy_figure
    assert len(figure.legends) == 1
    assert [t.get_text() for t in figure.legends[0].get_texts()] == ["Gaskessel_1", "Abwärmepumpe_1", "Power-to-Heat_1"]
    assert all(not ax.get_legend() for ax in figure.axes)
    colours = {
        text.get_text(): handle.get_facecolor()
        for text, handle in zip(figure.legends[0].get_texts(), figure.legends[0].legend_handles, strict=True)
    }
    assert colours["Power-to-Heat_1"] != colours["Gaskessel_1"]


def test_comparison_is_not_cleared_after_loading(qapp, tmp_path):
    """The reset slot must run before the explorer's reload on a project change."""
    from PyQt6.QtCore import QObject, pyqtSignal

    from districtheatingsim.gui.ComparisonTab import comparison_tab

    class Folders(QObject):
        project_folder_changed = pyqtSignal(str)

    calls = []
    folders = Folders()
    original_set, original_reset = (
        comparison_tab.ProjectExplorer.set_base_path,
        comparison_tab.ComparisonTab._reset_on_project_change,
    )
    try:
        comparison_tab.ProjectExplorer.set_base_path = lambda self, path: calls.append("load")
        comparison_tab.ComparisonTab._reset_on_project_change = lambda self, path=None: calls.append("reset")
        tab = comparison_tab.ComparisonTab(folders, None, None)
        calls.clear()  # the explorer's first load when it is built
        folders.project_folder_changed.emit(str(tmp_path))
    finally:
        comparison_tab.ProjectExplorer.set_base_path = original_set
        comparison_tab.ComparisonTab._reset_on_project_change = original_reset
    assert calls == ["reset", "load"]
    tab.deleteLater()


@pytest.mark.parametrize(
    ("key", "label"),
    [
        ("Wärmeleistung_kW", "Wärmeleistung (kW)"),
        ("el_Leistung_kW", "elektrische Leistung (kW)"),
        ("Speicher_SOC_%", "Speicher SOC (%)"),
        ("Speicher_T_oben_°C", "Speicher T oben (°C)"),
        ("Wärmeleistung_L", "Wärmeleistung"),
    ],
)
def test_quantity_labels(key, label):
    assert _quantity_label(key) == label


def _energy_system_with_chp(hours=48):
    chp = SimpleNamespace(
        name="BHKW_1",
        get_plot_data=lambda: {
            "Wärmeleistung_kW": np.full(hours, 150.0),
            "el_Leistung_kW": np.full(hours, 100.0),
            "betrieb_mask": np.ones(hours, dtype=bool),
        },
    )
    boiler = SimpleNamespace(
        name="Gaskessel_1",
        get_plot_data=lambda: {"Wärmeleistung_kW": np.linspace(100.0, 300.0, hours)},
    )
    system = EnergySystem.__new__(EnergySystem)
    system.technologies = [chp, boiler]
    system.storage = None
    system.time_steps = np.arange(hours)
    system.results = {"techs": ["BHKW_1", "Gaskessel_1"], "Last_L": np.linspace(250.0, 450.0, hours)}
    return system


def test_plot_variables_without_masks_and_with_readable_names():
    system = _energy_system_with_chp()
    data, initial = system.getInitialPlotData()
    assert "BHKW_1_betrieb_mask" not in data
    assert system.plot_labels["BHKW_1_el_Leistung_kW"] == "BHKW 1: elektrische Leistung (kW)"
    assert system.plot_labels["Last_L"] == "Wärmebedarf (kW)"
    assert initial == ["BHKW_1_Wärmeleistung_kW", "Gaskessel_1_Wärmeleistung_kW", "Last_L"]


def test_year_chart_starts_at_zero_and_shows_the_stack():
    system = _energy_system_with_chp()
    _data, initial = system.getInitialPlotData()
    figure = Figure()
    system.plot_stack_plot(figure=figure, selected_vars=initial)
    main = figure.axes[1]
    bottom, top = main.get_ylim()
    assert bottom == 0.0
    assert top >= 450.0  # the stacked outputs (150 + 300) reach the top
    legend = figure.axes[0].get_legend()
    assert [t.get_text() for t in legend.get_texts()] == ["BHKW 1", "Gaskessel 1", "Wärmebedarf"]


def test_results_tab_maps_labels_back_to_keys(qapp):
    from districtheatingsim.gui.EnergySystemTab._07_results_tab import ResultsTab
    from districtheatingsim.gui.EnergySystemTab._10_utilities import CheckableComboBox

    system = _energy_system_with_chp()
    combo = CheckableComboBox()
    calls = []
    system.plot_stack_plot = lambda figure, selected_vars, second_y_axis: calls.append(selected_vars)
    tab = SimpleNamespace(
        energy_system=system,
        variableComboBox=combo,
        stackPlotFigure=Figure(),
        stackPlotCanvas=SimpleNamespace(draw=lambda: None),
        secondYAxisCheckBox=SimpleNamespace(isChecked=lambda: False),
    )
    tab._checked_keys = lambda: ResultsTab._checked_keys(tab)
    ResultsTab.plotResults(tab)
    items = [combo.model().item(i).text() for i in range(combo.model().rowCount())]
    assert "BHKW 1: Wärmeleistung (kW)" in items and not any("mask" in item for item in items)
    assert calls == [["BHKW_1_Wärmeleistung_kW", "Gaskessel_1_Wärmeleistung_kW", "Last_L"]]


class TestSensitivity:
    def test_ranges_contain_the_base_price(self):
        from districtheatingsim.gui.EnergySystemTab._08_sensitivity_tab import price_range

        assert price_range(70.0) == ("40", "100")  # was 30-60 for a base price of 70 (UT-M16)
        assert price_range(150.0) == ("90", "210")
        assert price_range(2.0) == ("0", "5")

    def test_ranges_follow_the_economic_parameters(self, qapp):
        from PyQt6.QtCore import QObject, pyqtSignal

        from districtheatingsim.gui.EnergySystemTab._08_sensitivity_tab import SensitivityTab

        class Folders(QObject):
            project_folder_changed = pyqtSignal(str)
            variant_folder = None

        tab = SensitivityTab(Folders())
        tab.set_base_prices({"gas_price": 90.0, "electricity_price": 150.0, "wood_price": 50.0})
        assert tab.parse_range(tab.gasPriceRange) == (55.0, 125.0, 5)
        assert tab.gasPriceRange.itemAt(0).widget().text() == "Gaspreis (Basis 90 €/MWh)"
        tab.gasPriceRange.itemAt(1).itemAt(1).widget().setText("60")  # the user's own range
        tab.set_base_prices({"gas_price": 90.0, "electricity_price": 150.0, "wood_price": 50.0})
        assert tab.parse_range(tab.gasPriceRange)[0] == 60.0
        tab.deleteLater()
