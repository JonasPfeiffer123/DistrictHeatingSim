"""
Double click in the project tree (BACKLOG UT-H8, user test 2026-10-08).

A double click on any folder that was not a variant made it the project folder: TRY/COP were
reset, the CRS fell back to the default and the sub-folder landed in "Zuletzt geöffnet". A double
click on a variant switched without asking to save and without loading the variant's results.
"""

from types import MethodType, SimpleNamespace

import pytest


@pytest.fixture
def tree(tmp_path):
    """ProjectPresenter on a project with two variants; requested variants are recorded."""
    from districtheatingsim.gui.MainTab.main_data_manager import ProjectConfigManager, ProjectFolderManager
    from districtheatingsim.gui.ProjectTab.project_tab import ProjectModel, ProjectPresenter

    config_manager = ProjectConfigManager(config_path=str(tmp_path / "recent.json"))
    folder_manager = ProjectFolderManager(config_manager)
    project = tmp_path / "Zittau"
    for folder in ("Variante 1/Lastgang", "Variante 2", "Definition Quartier IST", "Eingangsdaten allgemein"):
        (project / folder).mkdir(parents=True)
    folder_manager.project_folder = str(project)
    folder_manager.variant_folder = str(project / "Variante 1")
    folder_manager.try_filename = "TRY.dat"
    folder_manager.project_crs = "EPSG:25832"
    requested = []
    view = SimpleNamespace(
        get_selected_file_path=lambda index: str(index),
        variantRequested=SimpleNamespace(emit=requested.append),
    )
    presenter = ProjectPresenter(ProjectModel(), view, folder_manager, None, config_manager)
    presenter.timer.stop()
    return presenter, project, requested


class TestTreeDoubleClick:
    @pytest.mark.parametrize("folder", ["Eingangsdaten allgemein", "Definition Quartier IST", "Variante 1/Lastgang"])
    def test_other_folders_leave_the_project_alone(self, tree, folder):
        presenter, project, requested = tree
        manager = presenter.folder_manager
        presenter.on_tree_view_double_clicked(project / folder)
        assert manager.project_folder == str(project)
        assert manager.variant_folder == str(project / "Variante 1")
        assert manager.try_filename == "TRY.dat" and manager.project_crs == "EPSG:25832"
        assert requested == []
        assert str(project / folder) not in manager.config_manager.get_recent_projects()

    def test_another_variant_is_requested_from_the_main_window(self, tree):
        presenter, project, requested = tree
        presenter.on_tree_view_double_clicked(project / "Variante 2")
        assert requested == ["Variante 2"]
        # Nothing switches before the main window has asked to save.
        assert presenter.folder_manager.variant_folder == str(project / "Variante 1")

    def test_the_open_variant_is_not_requested_again(self, tree):
        presenter, project, requested = tree
        presenter.on_tree_view_double_clicked(project / "Variante 1")
        assert requested == []

    def test_variant_named_folder_outside_the_project_is_ignored(self, tree, tmp_path):
        presenter, _project, requested = tree
        stranger = tmp_path / "Anderes Projekt" / "Variante 1"
        stranger.mkdir(parents=True)
        presenter.on_tree_view_double_clicked(stranger)
        assert requested == []


class TestMainWindowVariantSwitch:
    @staticmethod
    def _window(answer, saved=True):
        from districtheatingsim.gui.MainTab.main_view import HeatSystemDesignGUI

        calls = []
        folder_manager = SimpleNamespace(
            project_folder="C:/Projekt", set_variant_folder=lambda name: calls.append(("variant", name))
        )
        window = SimpleNamespace(
            folder_manager=folder_manager,
            presenter=SimpleNamespace(folder_manager=folder_manager),
            show_save_dialog=lambda *a: calls.append(("ask", a[0])) or answer,
            save_all_project_results=lambda: calls.append(("save", None)) or saved,
            on_importResultsAction=lambda: calls.append(("results", None)),
        )
        window._confirm_leaving_variant = MethodType(HeatSystemDesignGUI._confirm_leaving_variant, window)
        window.on_variant_requested = MethodType(HeatSystemDesignGUI.on_variant_requested, window)
        return window, calls

    def test_asks_to_save_then_switches_and_loads_the_results(self):
        window, calls = self._window("save")
        window.on_variant_requested("Variante 2")
        assert calls == [("ask", "Variante öffnen"), ("save", None), ("variant", "Variante 2"), ("results", None)]

    @pytest.mark.parametrize(("answer", "saved"), [("cancel", True), ("save", False)])
    def test_cancel_or_refused_save_keeps_the_variant(self, answer, saved):
        window, calls = self._window(answer, saved)
        window.on_variant_requested("Variante 2")
        assert ("variant", "Variante 2") not in calls and ("results", None) not in calls
