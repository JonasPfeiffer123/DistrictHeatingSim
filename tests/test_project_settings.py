"""
Tests for project-settings persistence + schema versioning (D1/D2).

ProjectFolderManager owns ``project_settings.json`` (CRS, calculation year, active
energy configs, TRY/COP paths). These tests pin the save/load round-trip, the new
``version`` field, and that pre-versioning files (no ``version``) still load.

ProjectFolderManager is a QObject, so the session-scoped ``qapp`` fixture is needed.
``project_folder`` is set directly (not via ``set_project_folder``) to avoid the
real ``recent_projects.json`` write that ``set_project_folder`` triggers.
"""

import json

import pytest

from districtheatingsim.gui.MainTab.main_data_manager import ProjectFolderManager
from districtheatingsim.utilities.schema import SCHEMA_VERSIONS

pytestmark = pytest.mark.usefixtures("qapp")


class _StubConfig:
    """Truthy stand-in so ProjectFolderManager doesn't build the real config
    manager; the settings save/load path never calls it."""

    def set_last_project(self, *_):
        pass


def _manager(project_folder):
    m = ProjectFolderManager(config_manager=_StubConfig())
    m.project_folder = str(project_folder)
    return m


def test_save_writes_version_and_roundtrips(tmp_path):
    m = _manager(tmp_path)
    m.project_crs = "EPSG:25833"
    m.calculation_year = 2030
    m.active_energy_configs = {"Variante 1": "Solar+BHKW"}
    m.save_project_settings()

    raw = json.loads((tmp_path / "project_settings.json").read_text(encoding="utf-8"))
    assert raw["_meta"]["schema_version"] == SCHEMA_VERSIONS["project_settings"]
    assert "app_version" in raw["_meta"]

    fresh = _manager(tmp_path)
    fresh.load_project_settings()
    assert fresh.project_crs == "EPSG:25833"
    assert fresh.calculation_year == 2030
    assert fresh.active_energy_configs == {"Variante 1": "Solar+BHKW"}


def test_legacy_top_level_version_settings_load(tmp_path):
    # Files saved by the D2 app used a top-level "version" field; must still load.
    (tmp_path / "project_settings.json").write_text(
        json.dumps({"version": 1, "crs": "EPSG:3857", "calculation_year": 2024}),
        encoding="utf-8",
    )
    m = _manager(tmp_path)
    m.load_project_settings()  # must not raise
    assert m.project_crs == "EPSG:3857"
    assert m.calculation_year == 2024


def test_legacy_settings_without_version_load(tmp_path):
    # Pre-versioning file: no "version" key -> treated as v0, loads with defaults.
    (tmp_path / "project_settings.json").write_text(
        json.dumps({"crs": "EPSG:4326", "calculation_year": 2025}),
        encoding="utf-8",
    )
    m = _manager(tmp_path)
    m.load_project_settings()  # must not raise
    assert m.project_crs == "EPSG:4326"
    assert m.calculation_year == 2025
    # Absent keys fall back to defaults.
    assert m.active_energy_configs == {}
    assert m.try_filename is None


def test_corrupt_settings_falls_back_to_defaults(tmp_path):
    (tmp_path / "project_settings.json").write_text("{ not valid json", encoding="utf-8")
    m = _manager(tmp_path)
    m.load_project_settings()  # must not raise
    assert m.calculation_year == 2023  # default
