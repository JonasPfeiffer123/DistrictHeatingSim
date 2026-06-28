"""
UI behaviour tests for the BuildingTab and ComparisonTab views' reset path.

Both views gained an explicit "blank everything" method as part of the C29
project-change reset work, so that switching to another project never leaves the
previous project's buildings / variant comparison on screen (BACKLOG C29):

* ``BuildingTabView.clear_display`` — empties the building table, the building
  selection combobox and the profile plot.
* ``ComparisonDashboard.update_dashboard([])`` → ``clear_dashboard`` — resets all
  KPI tiles to "--" and clears the charts.

These are exercised directly through the public populate → clear interface with
lightweight data; neither view embeds a QWebEngineView, so they are stable
headless (unlike NetworkPlotWidget — see test_netsim_widgets.py).
"""

import pandas as pd

from districtheatingsim.gui.BuildingTab.building_tab import BuildingTabView
from districtheatingsim.gui.ComparisonTab.comparison_tab import ComparisonDashboard

# ----------------------------------------------------------------------------
# BuildingTabView.clear_display
# ----------------------------------------------------------------------------


def _building_df():
    return pd.DataFrame(
        {
            "Land": ["DE", "DE"],
            "Gebäudetyp": ["EFH", "MFH"],
            "Wärmebedarf": [15000.0, 42000.0],
        }
    )


class TestBuildingTabViewClear:
    def test_populate_then_clear_display(self, qtbot):
        view = BuildingTabView()
        qtbot.addWidget(view)

        view.populate_table(_building_df())
        view.populate_building_combobox({0: {}, 1: {}})
        assert view.table_widget.rowCount() == 2
        assert view.building_combobox.count() == 2

        view.clear_display()

        assert view.table_widget.rowCount() == 0
        assert view.building_combobox.count() == 0

    def test_clear_display_on_fresh_view_is_safe(self, qtbot):
        view = BuildingTabView()
        qtbot.addWidget(view)
        view.clear_display()  # must not raise on an empty view
        assert view.table_widget.rowCount() == 0

    def test_reusable_after_clear(self, qtbot):
        """A cleared view must accept a new project's buildings — the project-switch case."""
        view = BuildingTabView()
        qtbot.addWidget(view)

        view.populate_table(_building_df())
        view.clear_display()
        view.populate_table(_building_df().head(1))

        assert view.table_widget.rowCount() == 1


# ----------------------------------------------------------------------------
# ComparisonDashboard reset
# ----------------------------------------------------------------------------


def _variant(name, wgk, demand):
    """A variant result dict with the keys the KPI tiles read."""
    return {
        "name": name,
        "WGK_Gesamt": wgk,
        "specific_emissions_Gesamt": 0.12,
        "primärenergiefaktor_Gesamt": 1.1,
        "Jahreswärmebedarf": demand,
    }


class TestComparisonDashboardReset:
    def test_update_then_empty_resets_kpis(self, qtbot):
        dash = ComparisonDashboard()
        qtbot.addWidget(dash)

        dash.update_dashboard([_variant("Variante A", 95.0, 1200.0)])
        # At least the headline KPI should now show a real number, not the placeholder.
        assert dash.kpi_widgets["Wärmegestehungskosten"].value_label.text() != "--"

        dash.update_dashboard([])  # project change / no variants selected

        assert dash.variant_data == []
        for metric, widget in dash.kpi_widgets.items():
            assert widget.value_label.text() == "--", f"KPI {metric!r} not reset"

    def test_clear_dashboard_resets_all_tiles(self, qtbot):
        dash = ComparisonDashboard()
        qtbot.addWidget(dash)

        dash.update_dashboard([_variant("A", 80.0, 900.0), _variant("B", 110.0, 1500.0)])
        dash.clear_dashboard()

        for widget in dash.kpi_widgets.values():
            assert widget.value_label.text() == "--"
