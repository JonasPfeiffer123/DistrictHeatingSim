"""
UI behaviour tests for the NetSimulationTab result widgets.

These pin the ``clear()`` contract added in the C29 project-change reset work:
each widget must be able to drop the previously-loaded network and return to a
blank, empty state so that opening a different project never leaves stale data
on screen (BACKLOG C29).

The widgets are exercised through their public ``populate`` / ``set_network`` /
``update`` + ``clear`` interface with lightweight fakes — no pandapipes solve and
no real Plotly/WebEngine render is needed to assert the reset behaviour.
"""

import pandas as pd

from districtheatingsim.gui.NetSimulationTab.pipe_config_table import PipeConfigTable
from districtheatingsim.gui.NetSimulationTab.time_series_widget import TimeSeriesWidget

# NetworkPlotWidget is intentionally NOT covered here: it embeds a QWebEngineView,
# which crashes the process under offscreen/headless Qt (the platform the test
# suite + CI run on). Its clear() is a trivial passthrough (drop net, blank the
# canvas, clear the dropdown); the risk it could regress unnoticed is low. See
# BACKLOG C29 / the "no WebEngine test seam" note.


# ----------------------------------------------------------------------------
# Lightweight fakes standing in for NetworkGenerationData
# ----------------------------------------------------------------------------


class _FakeNet:
    """Minimal pandapipes-net stand-in: only the ``pipe`` table the widgets read."""

    def __init__(self, pipe_df):
        self.pipe = pipe_df


class _FakeNetData:
    def __init__(self, pipe_df):
        self.net = _FakeNet(pipe_df)


def _pipe_df(n=3):
    """A small pipe DataFrame with the columns PipeConfigTable reads."""
    return pd.DataFrame(
        {
            "name": [f"Pipe {i}" for i in range(n)],
            "from_junction": list(range(n)),
            "to_junction": list(range(1, n + 1)),
            "length_km": [0.05 * (i + 1) for i in range(n)],
            "std_type": ["" for _ in range(n)],
            "inner_diameter_mm": [70.3 for _ in range(n)],
            "k_mm": [0.1 for _ in range(n)],
        }
    )


# ----------------------------------------------------------------------------
# PipeConfigTable
# ----------------------------------------------------------------------------


class TestPipeConfigTableClear:
    def test_populate_then_clear_empties_and_hides(self, qtbot):
        widget = PipeConfigTable()
        qtbot.addWidget(widget)

        widget.populate(_FakeNetData(_pipe_df(3)))
        assert widget._table.rowCount() == 3
        assert widget.isVisible()

        widget.clear()

        assert widget._table.rowCount() == 0
        assert widget._net_data is None
        assert widget._original_pipe_df is None
        assert widget._baseline == {}
        assert not widget.isVisible()

    def test_clear_on_fresh_widget_is_safe(self, qtbot):
        widget = PipeConfigTable()
        qtbot.addWidget(widget)
        widget.clear()  # must not raise even though nothing was ever populated
        assert widget._table.rowCount() == 0

    def test_reusable_after_clear(self, qtbot):
        """A cleared table must accept a new (different) network — the project-switch case."""
        widget = PipeConfigTable()
        qtbot.addWidget(widget)

        widget.populate(_FakeNetData(_pipe_df(5)))
        widget.clear()
        widget.populate(_FakeNetData(_pipe_df(2)))

        assert widget._table.rowCount() == 2
        assert widget.isVisible()


# ----------------------------------------------------------------------------
# TimeSeriesWidget
# ----------------------------------------------------------------------------


class _FakeTimeSeriesData:
    def __init__(self, labels):
        # Only the keys are needed to build the dropdown; clear() never plots.
        self.plot_data = {label: {} for label in labels}


class TestTimeSeriesWidgetClear:
    def test_populate_dropdown_then_clear(self, qtbot):
        widget = TimeSeriesWidget()
        qtbot.addWidget(widget)

        widget._network_data = _FakeTimeSeriesData(["Vorlauftemperatur", "Rücklauftemperatur"])
        widget._rebuild_dropdown()
        assert widget._dropdown is not None
        assert widget._dropdown.model().rowCount() == 2

        widget.clear()

        assert widget._network_data is None
        assert widget._dropdown is None
        assert widget._dropdown_layout.count() == 0

    def test_clear_on_fresh_widget_is_safe(self, qtbot):
        widget = TimeSeriesWidget()
        qtbot.addWidget(widget)
        widget.clear()
        assert widget._network_data is None
        assert widget._dropdown is None
