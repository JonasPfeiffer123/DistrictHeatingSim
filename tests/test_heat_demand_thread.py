"""
Tests for the building heat demand worker (BACKLOG G6).

The calculation (profiles → formatted results → combined data → JSON) moved from the UI
thread to ``HeatDemandThread``. Pins the worker job itself, the thread's signals, and the
presenter behaviour around it: results applied on completion, discarded if the project
changed meanwhile, and no second run while one is in flight. Uses the Görlitz building CSV
and the examples' TRY file.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

_REPO = Path(__file__).resolve().parents[1]
_CSV = (
    _REPO / "src" / "districtheatingsim" / "project_data" / "Görlitz" / "Definition Quartier IST" / "Quartier IST.csv"
)
_TRY = _REPO / "examples" / "data" / "TRY" / "TRY_511676144222" / "TRY2015_511676144222_Jahr.dat"

pytestmark = [
    pytest.mark.skipif(not (_CSV.exists() and _TRY.exists()), reason="Görlitz CSV / TRY data not present"),
    pytest.mark.usefixtures("qapp"),
]


@pytest.fixture(scope="module")
def buildings():
    return pd.read_csv(_CSV, delimiter=";", dtype={"Subtyp": str})


class TestComputeAndSaveHeatDemand:
    def test_results_json_and_input_untouched(self, buildings, tmp_path):
        from districtheatingsim.gui.BuildingTab.heat_demand_thread import compute_and_save_heat_demand

        data = buildings.copy()
        data.index = data.index + 100  # a non-default index must neither break nor be reset in place
        json_path = tmp_path / "Gebäude Lastgang.json"

        outcome = compute_and_save_heat_demand(data, str(_TRY), 2023, str(json_path))

        assert outcome.save_error is None
        assert list(data.index) == list(buildings.index + 100)
        assert set(outcome.results) == {str(i) for i in range(len(buildings))}
        for i, row in buildings.iterrows():
            r = outcome.results[str(i)]
            assert len(r["wärme"]) == 8760
            # hourly kW summed over the year ≈ the building's annual demand in kWh
            assert sum(r["wärme"]) == pytest.approx(float(row["Wärmebedarf"]), rel=0.02)
            assert outcome.combined_data[str(i)]["Adresse"] == row["Adresse"]

        saved = json.loads(json_path.read_text(encoding="utf-8"))
        assert "_meta" in saved
        assert saved["0"]["wärme"] == outcome.results["0"]["wärme"]

    def test_failed_write_keeps_results(self, buildings, tmp_path):
        from districtheatingsim.gui.BuildingTab.heat_demand_thread import compute_and_save_heat_demand

        outcome = compute_and_save_heat_demand(buildings, str(_TRY), 2023, str(tmp_path / "missing" / "x.json"))

        assert outcome.save_error is not None and "Speichern" in outcome.save_error
        assert len(outcome.results) == len(buildings)


class TestHeatDemandThread:
    def test_emits_done_with_outcome(self, qtbot, buildings, tmp_path):
        from districtheatingsim.gui.BuildingTab.heat_demand_thread import HeatDemandThread

        thread = HeatDemandThread(buildings, str(_TRY), 2023, str(tmp_path / "out.json"))
        with qtbot.waitSignal(thread.calculation_done, timeout=60000) as blocker:
            thread.start()
        thread.wait()
        assert len(blocker.args[0].results) == len(buildings)

    def test_emits_error_on_invalid_data(self, qtbot, tmp_path):
        from districtheatingsim.gui.BuildingTab.heat_demand_thread import HeatDemandThread

        thread = HeatDemandThread(pd.DataFrame({"Adresse": ["A"]}), str(_TRY), 2023, str(tmp_path / "out.json"))
        with qtbot.waitSignal(thread.calculation_error, timeout=60000) as blocker:
            thread.start()
        thread.wait()
        assert "Fehler" in blocker.args[0]


class _FakeSignal:
    def connect(self, _slot):
        pass


@pytest.fixture
def presenter(qtbot, buildings, tmp_path):
    """A BuildingPresenter on a real view, fake managers, message boxes recorded instead of shown."""
    from districtheatingsim.gui.BuildingTab.building_tab import BuildingModel, BuildingPresenter, BuildingTabView

    view = BuildingTabView()
    qtbot.addWidget(view)
    messages = []
    view.show_message = lambda title, text: messages.append(("info", title, text))
    view.show_error_message = lambda title, text: messages.append(("error", title, text))

    folder_manager = SimpleNamespace(
        project_folder_changed=_FakeSignal(), variant_folder=None, try_filename=str(_TRY), calculation_year=2023
    )
    p = BuildingPresenter(BuildingModel(), view, folder_manager, None, None)
    p.model.base_path = str(tmp_path)
    p.model.json_path = str(tmp_path / "Gebäude Lastgang.json")
    view.populate_table(buildings)
    p.messages = messages
    yield p
    p.stop_threads()


def _wait_for_worker(qtbot, presenter):
    qtbot.waitUntil(lambda: not presenter._calc_thread.isRunning(), timeout=60000)
    qtbot.wait(50)  # let the queued done/error slot run on the UI thread


class TestBuildingPresenterWorker:
    def test_results_applied_and_saved(self, qtbot, presenter, buildings):
        presenter.calculate_heat_demand()
        assert not presenter.view.calculate_action.isEnabled()  # menu reflects the running job

        _wait_for_worker(qtbot, presenter)

        assert presenter.view.calculate_action.isEnabled()
        assert set(presenter.model.results) == {str(i) for i in range(len(buildings))}
        assert presenter.combined_data is not None
        assert presenter.view.building_combobox.count() > 0
        assert Path(presenter.model.json_path).exists()
        assert len(presenter.messages) == 1
        kind, title, text = presenter.messages[0]
        assert (kind, title) == ("info", "Erfolg") and "abgeschlossen" in text

    def test_project_change_during_run_discards_results(self, qtbot, presenter):
        json_path = Path(presenter.model.json_path)
        presenter.calculate_heat_demand()
        presenter.model.base_path = "anderes Projekt"  # what standard_path does on a project change

        _wait_for_worker(qtbot, presenter)

        assert presenter.model.results is None
        assert presenter.messages == []
        assert json_path.exists()  # still saved for the project it was computed for
        assert presenter.view.calculate_action.isEnabled()

    def test_second_start_refused_while_running(self, qtbot, presenter):
        presenter.calculate_heat_demand()
        first_thread = presenter._calc_thread
        presenter.calculate_heat_demand()

        assert presenter._calc_thread is first_thread
        assert ("error", "Berechnung läuft", "Die Gebäudelastgänge werden bereits berechnet.") in presenter.messages
        _wait_for_worker(qtbot, presenter)
