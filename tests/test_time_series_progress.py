"""
Time series: default method, progress and cancel (BACKLOG UT-H1, user test 2026-10-08).

The detailed time series was the default and took 1.5-3 h for a year with 15 buildings,
showing only an endless busy bar; it could not be cancelled, and closing the app during a run
froze it (``stop()`` requested an interruption that ``run()`` never checked).
"""

import copy
import time
from types import SimpleNamespace

import pytest


def _small_net(n):
    """The two-consumer net of the G2 tests (tests/ is on sys.path; imported here so pytest does
    not collect that test class a second time)."""
    import test_net_simulation

    return test_net_simulation.TestParallelTimeSeries._nd(n)


class TestProgressText:
    @pytest.mark.parametrize(
        ("done", "total", "elapsed", "expected"),
        [
            (0, 8760, 0.0, "Zeitschritt 0 von 8760 – Restzeit wird ermittelt …"),
            (2, 8760, 1.0, "Zeitschritt 2 von 8760 – Restzeit wird ermittelt …"),
            (100, 160, 10.0, "Zeitschritt 100 von 160 – noch unter 1 min"),
            (100, 8760, 50.0, "Zeitschritt 100 von 8760 – noch ca. 72 min"),
            (100, 8760, 99.0, "Zeitschritt 100 von 8760 – noch ca. 2 h 23 min"),
        ],
    )
    def test_format(self, done, total, elapsed, expected):
        from districtheatingsim.gui.NetSimulationTab.net_calculation_threads import format_time_series_progress

        assert format_time_series_progress(done, total, elapsed) == expected


@pytest.mark.slow
class TestDetailedTimeSeriesProgress:
    def test_progress_before_every_step(self):
        from districtheatingsim.net_simulation_pandapipes import pp_net_time_series_simulation as ts

        calls = []
        ts.thermohydraulic_time_series_net(_small_net(6), progress=lambda done, total: calls.append((done, total)))
        assert calls == [(i, 6) for i in range(6)]

    def test_cancel_between_two_steps(self):
        from districtheatingsim.net_simulation_pandapipes import pp_net_time_series_simulation as ts

        calls = []

        def progress(done, total):
            calls.append(done)
            if done == 3:
                raise ts.TimeSeriesCancelled()

        with pytest.raises(ts.TimeSeriesCancelled):
            ts.thermohydraulic_time_series_net(_small_net(8), progress=progress)
        assert calls == [0, 1, 2, 3]

    def test_parallel_progress_reaches_the_total(self, monkeypatch):
        from districtheatingsim.net_simulation_pandapipes import pp_net_time_series_simulation as ts

        monkeypatch.setattr(ts, "PARALLEL_MIN_BLOCK_STEPS", 3)
        calls = []
        ts.thermohydraulic_time_series_net(
            _small_net(8), workers=2, progress=lambda done, total: calls.append((done, total))
        )
        assert calls[-1] == (8, 8)
        assert [done for done, _ in calls] == sorted(done for done, _ in calls)

    def test_parallel_cancel_stops_the_workers(self, monkeypatch):
        from districtheatingsim.net_simulation_pandapipes import pp_net_time_series_simulation as ts

        monkeypatch.setattr(ts, "PARALLEL_MIN_BLOCK_STEPS", 3)

        def cancel(done, total):
            raise ts.TimeSeriesCancelled()

        started = time.monotonic()
        with pytest.raises(ts.TimeSeriesCancelled):
            ts.thermohydraulic_time_series_net(_small_net(400), workers=2, progress=cancel)
        assert time.monotonic() - started < 60  # 400 steps in two blocks would take far longer


class TestCalculationThread:
    """The thread works on a copy, reports progress, and stops when cancelled."""

    @staticmethod
    def _thread(monkeypatch, steps=5, on_step=None, simplified=False):
        from districtheatingsim.gui.NetSimulationTab import net_calculation_threads as threads

        def detailed(data, workers=1, progress=None):
            data.net.append("controllers")  # a run mutates the net in place
            for i in range(steps):
                progress(i, steps)
                if on_step:
                    on_step(i)
            data.net.append("results")
            return data

        monkeypatch.setattr(threads, "time_series_preprocessing", lambda data: data)
        monkeypatch.setattr(threads, "thermohydraulic_time_series_net", detailed)
        monkeypatch.setattr(threads, "simplified_time_series_net", lambda data: data)
        original = SimpleNamespace(net=[], calculate_results=lambda: None)
        thread = threads.NetCalculationThread(original, simplified=simplified)
        events = {"done": [], "cancelled": 0, "error": [], "progress": []}
        thread.calculation_done.connect(events["done"].append)
        thread.calculation_error.connect(events["error"].append)
        thread.progress.connect(lambda done, total: events["progress"].append((done, total)))
        thread.calculation_cancelled.connect(lambda: events.__setitem__("cancelled", events["cancelled"] + 1))
        return thread, original, events

    def test_success_returns_the_copy_and_leaves_the_callers_net(self, qapp, monkeypatch):
        thread, original, events = self._thread(monkeypatch)
        thread.run()
        assert events["progress"] == [(i, 5) for i in range(5)] and events["error"] == []
        (result,) = events["done"]
        assert result is not original and result.net == ["controllers", "results"]
        assert original.net == []

    def test_cancel_emits_cancelled_and_keeps_the_callers_net(self, qapp, monkeypatch):
        holder = {}
        thread, original, events = self._thread(
            monkeypatch, on_step=lambda i: holder["thread"].cancel() if i == 1 else None
        )
        holder["thread"] = thread
        thread.run()
        assert events["cancelled"] == 1 and events["done"] == [] and events["error"] == []
        assert events["progress"] == [(0, 5), (1, 5)]
        assert original.net == []

    def test_stop_ends_a_running_calculation_at_once(self, qapp, monkeypatch):
        thread, _original, events = self._thread(monkeypatch, steps=100000, on_step=lambda i: time.sleep(0.01))
        thread.start()
        deadline = time.monotonic() + 10
        while not events["progress"] and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)
        started = time.monotonic()
        thread.stop()  # what closing the main window calls
        assert not thread.isRunning()
        assert time.monotonic() - started < 2  # the whole run would take > 15 min


class TestDialogDefault:
    def test_simplified_is_the_default(self, qapp, tmp_path):
        from PyQt6.QtWidgets import QWidget

        from districtheatingsim.gui.MainTab.main_data_manager import ProjectConfigManager
        from districtheatingsim.gui.NetSimulationTab.timeseries_dialog import TimeSeriesCalculationDialog

        parent = QWidget()
        parent.config_manager = ProjectConfigManager(config_path=str(tmp_path / "recent.json"))
        dialog = TimeSeriesCalculationDialog(str(tmp_path), parent)
        values = dialog.getValues()
        assert values["simplified"] is True
        assert not dialog.WorkersInput.isEnabled()
        dialog.detailedCalcRadio.setChecked(True)
        assert dialog.WorkersInput.isEnabled() and dialog.getValues()["simplified"] is False


def test_copy_of_a_real_network_data_object_works():
    """The thread deep-copies NetworkGenerationData; a pandapipes net with controllers must survive it."""
    data = _small_net(4)
    clone = copy.deepcopy(data)
    assert clone.net is not data.net and len(clone.net.controller) == len(data.net.controller)
