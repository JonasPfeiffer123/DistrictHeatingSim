"""
User settings outside the installation folder (BACKLOG UT-K6, user test 2026-10-08).

The recent-projects list was written next to the package. In a read-only installation
(C:/Program Files, a system site-packages) ``set_last_project`` raised, the welcome screen
swallowed the error, and opening any project silently did nothing. The bundled example project
was opened (and saved) inside the installation as well.
"""

import json
import os
from types import MethodType, SimpleNamespace

import pytest


class TestSettingsFolder:
    def test_override_wins(self, monkeypatch, tmp_path):
        from districtheatingsim.utilities.path_utils import user_settings_dir

        monkeypatch.setenv("DHS_SETTINGS_DIR", str(tmp_path))
        assert user_settings_dir() == str(tmp_path)

    def test_appdata_on_windows(self, monkeypatch, tmp_path):
        from districtheatingsim.utilities.path_utils import user_settings_dir

        monkeypatch.delenv("DHS_SETTINGS_DIR", raising=False)
        monkeypatch.setenv("APPDATA", str(tmp_path))
        assert user_settings_dir() == os.path.join(str(tmp_path), "DistrictHeatingSim")


class TestRecentProjects:
    def test_default_list_lives_in_the_settings_folder(self, monkeypatch, tmp_path):
        from districtheatingsim.gui.MainTab import main_data_manager

        monkeypatch.setenv("DHS_SETTINGS_DIR", str(tmp_path / "settings"))
        monkeypatch.setattr(main_data_manager, "LEGACY_CONFIG_PATH", str(tmp_path / "gibt_es_nicht.json"))
        manager = main_data_manager.ProjectConfigManager()
        assert manager.config_path == os.path.join(str(tmp_path / "settings"), "recent_projects.json")
        manager.set_last_project(str(tmp_path / "Projekt"))
        assert json.load(open(manager.config_path, encoding="utf-8"))["last_project"] == str(tmp_path / "Projekt")

    def test_list_from_the_installation_folder_is_taken_over_once(self, monkeypatch, tmp_path):
        from districtheatingsim.gui.MainTab import main_data_manager

        legacy = tmp_path / "legacy.json"
        legacy.write_text(json.dumps({"last_project": "C:/alt", "recent_projects": ["C:/alt"]}), encoding="utf-8")
        monkeypatch.setenv("DHS_SETTINGS_DIR", str(tmp_path / "settings"))
        monkeypatch.setattr(main_data_manager, "LEGACY_CONFIG_PATH", str(legacy))
        assert main_data_manager.ProjectConfigManager().get_recent_projects() == ["C:/alt"]
        legacy.write_text(json.dumps({"recent_projects": ["C:/neuer"]}), encoding="utf-8")
        assert main_data_manager.ProjectConfigManager().get_recent_projects() == ["C:/alt"]  # not copied again

    def test_unwritable_list_does_not_stop_opening_a_project(self, qapp, tmp_path):
        from districtheatingsim.gui.MainTab.main_data_manager import ProjectConfigManager, ProjectFolderManager

        unwritable = tmp_path / "ist_ein_ordner"
        unwritable.mkdir()  # writing a file to this path fails like a read-only installation
        project = tmp_path / "Projekt"
        (project / "Variante 1").mkdir(parents=True)
        folder_manager = ProjectFolderManager(ProjectConfigManager(config_path=str(unwritable)))
        emitted = []
        folder_manager.project_folder_changed.connect(emitted.append)
        folder_manager.set_project_folder(str(project))
        assert folder_manager.project_folder == str(project)
        assert emitted == [os.path.join(str(project), "Variante 1")]


class TestExampleProject:
    @staticmethod
    def _example(tmp_path):
        example = tmp_path / "install" / "project_data" / "Görlitz"
        (example / "Variante 1").mkdir(parents=True)
        (example / "project_settings.json").write_text("{}", encoding="utf-8")
        return example

    def test_working_copy_is_created_once_and_then_reused(self, tmp_path):
        from districtheatingsim.gui.MainTab.project_structure import working_copy_of_example

        example = self._example(tmp_path)
        copy_path, created = working_copy_of_example(str(example), str(tmp_path / "Dokumente"))
        assert created and os.path.isdir(os.path.join(copy_path, "Variante 1"))
        assert os.path.basename(copy_path) == "Görlitz (Beispiel)"
        (tmp_path / "Dokumente" / "Görlitz (Beispiel)" / "eigene_datei.txt").write_text("x")
        again, created_again = working_copy_of_example(str(example), str(tmp_path / "Dokumente"))
        assert again == copy_path and not created_again
        assert os.path.exists(os.path.join(again, "eigene_datei.txt"))  # the user's changes are kept

    def test_main_window_opens_the_copy_not_the_bundled_folder(self, qapp, monkeypatch, tmp_path):
        from PyQt6.QtWidgets import QMessageBox

        from districtheatingsim.gui.MainTab import main_view

        example = self._example(tmp_path)
        monkeypatch.setattr(main_view, "user_projects_dir", lambda: str(tmp_path / "Dokumente"))
        shown = []
        monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: shown.append(a[2])))
        window = SimpleNamespace(
            welcome_screen=SimpleNamespace(get_bundled_example_project=lambda: (str(example), {})),
        )
        window._working_project_path = MethodType(main_view.HeatSystemDesignGUI._working_project_path, window)
        opened = window._working_project_path(str(example))
        assert opened == str(tmp_path / "Dokumente" / "Görlitz (Beispiel)")
        assert shown and "unverändert" in shown[0]
        other = str(tmp_path / "anderes Projekt")
        assert window._working_project_path(other) == other


def test_failed_open_is_reported_instead_of_swallowed(qapp, monkeypatch):
    from districtheatingsim.gui.MainTab import main_view

    errors = []

    def fail(path):
        raise OSError("Zugriff verweigert")

    window = SimpleNamespace(
        show_main_interface=lambda: None,
        sync_theme_toggle_state=lambda: None,
        _working_project_path=lambda path: path,
        on_open_existing_project=fail,
        show_error_message=errors.append,
    )
    main_view.HeatSystemDesignGUI.on_project_selected(window, "C:/Projekt")
    assert len(errors) == 1 and "Zugriff verweigert" in errors[0]


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("DHS_SETTINGS_DIR", str(tmp_path / "default-settings"))
