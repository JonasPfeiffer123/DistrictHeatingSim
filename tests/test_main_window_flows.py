"""
Opening, saving and switching in the main window (user test 2026-10-08, UT-M5, UT-M6, UT-M17).

UT-M5: cancelling "Projekt öffnen" still asked to save and then reported "Projektpfad '' nicht
gefunden"; a cancelled variant choice left the project half opened.
UT-M6: every close and switch asked to save (default "Speichern") and warned about missing
versioning, and the save rewrote everything - re-exporting an unchanged net overwrote a network
generated on the map since.
UT-M17: switching to a variant asked every time which generator config to load.
"""

import os
from types import SimpleNamespace

import pytest
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from districtheatingsim.gui.MainTab.main_view import HeatSystemDesignGUI


def _window(**tabs):
    calls = []
    window = SimpleNamespace(
        base_path="C:/Projekte/Zittau/Variante 1",
        calls=calls,
        show_error_message=lambda text: calls.append(("error", text)),
        show_message=lambda title, text: calls.append(("info", title, text)),
        running_calculations=lambda: [],
        **tabs,
    )
    window.unsaved_changes = lambda: HeatSystemDesignGUI.unsaved_changes(window)
    window.show_save_dialog = lambda *a: calls.append(("save question",)) or "continue"
    window.save_all_project_results = lambda: calls.append(("save all",)) or True
    window.on_importResultsAction = lambda: calls.append(("load results",))
    return window


def _tabs(table_modified=False, net=False, energy=False):
    saved = []
    project = SimpleNamespace(
        presenter=SimpleNamespace(table_modified=table_modified, save_csv=lambda show_dialog: saved.append("csv"))
    )
    calc = SimpleNamespace(
        unsaved_changes=net,
        saveNet=lambda show_dialog: saved.append("net"),
        exportNetGeoJSON=lambda show_dialog: saved.append("geojson"),
    )
    energy_tab = SimpleNamespace(
        unsaved_changes=energy,
        _active_config_name="Solar",
        save_results_JSON=lambda show_dialog: saved.append("energy"),
    )
    return {"projectTab": project, "calcTab": calc, "energySystemTab": energy_tab}, saved


class TestUnsavedChanges:
    def test_nothing_unsaved_asks_nothing(self, qapp):
        tabs, _saved = _tabs()
        window = _window(**tabs)
        assert HeatSystemDesignGUI.unsaved_changes(window) == []
        assert HeatSystemDesignGUI.show_save_dialog(window, "Schließen", "Speichern?", "Speichern") == "continue"

    def test_the_question_names_what_is_unsaved(self, qapp, monkeypatch):
        tabs, _saved = _tabs(net=True, energy=True)
        window = _window(**tabs)
        assert HeatSystemDesignGUI.unsaved_changes(window) == [
            "Netzberechnung (Tab „Wärmenetzberechnung“)",
            "Erzeugerberechnung „Solar“",
        ]
        shown = []

        def exec_(box):
            shown.append(box.text())
            box._clicked = next(b for b in box.buttons() if b.text() == "Abbrechen")
            return 0

        monkeypatch.setattr(QMessageBox, "exec", exec_)
        monkeypatch.setattr(QMessageBox, "clickedButton", lambda box: box._clicked)
        from PyQt6.QtWidgets import QWidget

        parent = QWidget()  # the message box needs a widget as parent
        parent.base_path = window.base_path
        parent.unsaved_changes = window.unsaved_changes
        assert HeatSystemDesignGUI.show_save_dialog(parent, "Schließen", "Speichern?", "Speichern") == "cancel"
        assert shown == [
            "Nicht gespeichert:\n  • Netzberechnung (Tab „Wärmenetzberechnung“)\n  • Erzeugerberechnung „Solar“"
        ]

    def test_save_writes_only_what_changed(self, qapp):
        tabs, saved = _tabs(energy=True)
        window = _window(**tabs)
        assert HeatSystemDesignGUI.save_all_project_results(window) is True
        assert saved == ["energy"]  # no net re-export over a network generated on the map since
        assert window.calls == [("info", "Gespeichert", "Gespeichert:\n  • Erzeugerberechnung „Solar“")]

    def test_menu_save_without_changes(self, qapp):
        tabs, saved = _tabs()
        window = _window(**tabs)
        HeatSystemDesignGUI.save_project(window)
        assert saved == [] and window.calls == [
            ("info", "Projekt speichern", "Es gibt keine ungespeicherten Änderungen.")
        ]


class TestOpenProject:
    def test_cancelled_folder_dialog_changes_nothing(self, qapp, monkeypatch):
        monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: ""))
        window = _window()
        window.presenter = SimpleNamespace(open_existing_project=lambda path: window.calls.append(("open", path)))
        HeatSystemDesignGUI.on_open_existing_project(window)
        assert window.calls == []  # no save question, no "Projektpfad '' nicht gefunden"

    def test_folder_without_variants_is_not_opened(self, qapp, tmp_path):
        window = _window()
        window.presenter = SimpleNamespace(open_existing_project=lambda path: window.calls.append(("open", path)))
        HeatSystemDesignGUI.on_open_existing_project(window, str(tmp_path))
        assert window.calls[0][0] == "error" and "kein DistrictHeatingSim-Projekt" in window.calls[0][1]
        assert len(window.calls) == 1

    def test_cancelled_variant_choice_changes_nothing(self, qapp, tmp_path, monkeypatch):
        for name in ("Variante 1", "Variante 2"):
            (tmp_path / name).mkdir()
        monkeypatch.setattr(QInputDialog, "getItem", staticmethod(lambda *a, **k: ("", False)))
        window = _window()
        window.presenter = SimpleNamespace(open_existing_project=lambda path: window.calls.append(("open", path)))
        HeatSystemDesignGUI.on_open_existing_project(window, str(tmp_path))
        assert window.calls == []

    def test_open_with_chosen_variant(self, qapp, tmp_path, monkeypatch):
        for name in ("Variante 1", "Variante 2"):
            (tmp_path / name).mkdir()
        monkeypatch.setattr(QInputDialog, "getItem", staticmethod(lambda *a, **k: ("Variante 2", True)))
        window = _window()
        variants = []
        window.presenter = SimpleNamespace(
            open_existing_project=lambda path: window.calls.append(("open", path)),
            folder_manager=SimpleNamespace(set_variant_folder=variants.append),
        )
        HeatSystemDesignGUI.on_open_existing_project(window, str(tmp_path))
        assert [c[0] for c in window.calls] == ["save question", "open", "load results"]
        assert variants == ["Variante 2"]


def test_new_project_does_not_inherit_the_previous_variant(qapp, tmp_path):
    from districtheatingsim.gui.MainTab.main_data_manager import ProjectFolderManager

    class Config:
        def set_last_project(self, *_):
            pass

    for project in ("Zittau", "Freiburg"):
        (tmp_path / project / "Variante 1").mkdir(parents=True)
    (tmp_path / "Zittau" / "Variante 2").mkdir()
    manager = ProjectFolderManager(config_manager=Config())
    announced = []
    manager.project_folder_changed.connect(announced.append)
    manager.set_project_folder(str(tmp_path / "Zittau"))
    manager.set_variant_folder("Variante 2")
    manager.set_project_folder(str(tmp_path / "Freiburg"))
    assert announced[-1] == os.path.join(str(tmp_path / "Freiburg"), "Variante 1")


def test_variant_switch_takes_the_newest_config_without_asking(tmp_path):
    from districtheatingsim.gui.EnergySystemTab._01_energy_system_main_tab import EnergySystemTab

    results = tmp_path / "Ergebnisse"
    results.mkdir()
    for name, when in (
        ("Ergebnisse.parquet", 100),
        ("Ergebnisse_Solar.parquet", 300),
        ("Ergebnisse_BHKW.parquet", 200),
    ):
        (results / name).write_text("x")
        os.utime(results / name, (when, when))
    tab = SimpleNamespace(_ergebnisse_dir=lambda: str(results))
    configs = [
        ("Standard", "Ergebnisse.parquet"),
        ("BHKW", "Ergebnisse_BHKW.parquet"),
        ("Solar", "Ergebnisse_Solar.parquet"),
    ]
    assert EnergySystemTab._newest_config(tab, configs) == "Solar"
    assert EnergySystemTab._newest_config(SimpleNamespace(_ergebnisse_dir=lambda: str(tmp_path)), configs) == "Standard"
    assert not hasattr(EnergySystemTab, "_ask_which_config")


@pytest.mark.parametrize("handler", ["_on_initialization_done", "_on_recalculation_done"])
def test_net_changes_are_unsaved_and_pipe_edits_get_a_new_stamp(qapp, monkeypatch, handler):
    from PyQt6.QtWidgets import QProgressBar

    from districtheatingsim.gui.NetSimulationTab.net_simulation_tab import NetSimulationTab

    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    tab = SimpleNamespace(
        unsaved_changes=False,
        _net_stamp={"id": "alt", "eingaben": {"Gebäudelastgänge": "p1"}},
        _init_inputs={"Gebäudelastgänge": "p2"},
        _progress_bar=QProgressBar(),
        _net_plot=SimpleNamespace(set_network=lambda nd: None),
        _info_panel=SimpleNamespace(update=lambda nd: None),
        _refresh_all_widgets=lambda: None,
    )
    getattr(NetSimulationTab, handler)(tab, SimpleNamespace())
    assert tab.unsaved_changes is True
    assert tab._net_stamp["id"] != "alt"
    expected = "p2" if handler == "_on_initialization_done" else "p1"
    assert tab._net_stamp["eingaben"] == {"Gebäudelastgänge": expected}
