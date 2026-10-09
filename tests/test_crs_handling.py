"""
CRS handling for projects outside UTM zone 33 (BACKLOG UT-K2, user test 2026-10-08).

Freiburg-Vauban (7.83° E) lies in UTM zone 32. The user test found that a project kept the
default EPSG:25833 without a hint (geocoding gave a negative easting), that switching the CRS
kept the stored coordinates (moving every building by hundreds of kilometres), that the
producer geocoding ignored the project CRS and that the OSMnx export was labelled 25833.
"""

import json
import os

import numpy as np
import pandas as pd
import pytest
from pyproj import Transformer

from districtheatingsim.utilities.crs_utils import (
    outside_crs_area,
    read_building_coordinates,
    reproject_building_csv,
    suggest_crs_for_coordinates,
)

FREIBURG_WGS84 = [(7.8296, 47.9787), (7.8265, 47.9741)]
ZITTAU_WGS84 = [(14.8065, 50.8975), (14.8102, 50.8961)]


def _project(points_wgs84, crs):
    transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    xs, ys = transformer.transform([p[0] for p in points_wgs84], [p[1] for p in points_wgs84])
    return np.asarray(xs), np.asarray(ys)


def _write_building_csv(path, points_wgs84, crs):
    xs, ys = _project(points_wgs84, crs)
    rows = [
        [
            "Deutschland",
            "Baden-Württemberg",
            "Freiburg",
            f"Vaubanallee {i + 1}",
            "50000",
            "HMF",
            "03",
            repr(float(x)),
            repr(float(y)),
        ]
        for i, (x, y) in enumerate(zip(xs, ys, strict=True))
    ]
    rows.append(["Deutschland", "Baden-Württemberg", "Freiburg", "ohne Koordinaten", "1000", "HMF", "03", "", ""])
    header = ["Land", "Bundesland", "Stadt", "Adresse", "Wärmebedarf", "Gebäudetyp", "Subtyp", "UTM_X", "UTM_Y"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(";".join(header) + "\n")
        for row in rows:
            f.write(";".join(row) + "\n")


class TestCrsArea:
    def test_freiburg_in_zone_33_is_outside(self):
        assert outside_crs_area(*_project(FREIBURG_WGS84, "EPSG:25833"), "EPSG:25833").all()

    def test_freiburg_in_zone_32_is_inside(self):
        assert not outside_crs_area(*_project(FREIBURG_WGS84, "EPSG:25832"), "EPSG:25832").any()

    def test_zittau_in_zone_33_is_inside(self):
        assert not outside_crs_area(*_project(ZITTAU_WGS84, "EPSG:25833"), "EPSG:25833").any()

    def test_suggests_zone_32_for_freiburg_given_in_zone_33(self):
        assert suggest_crs_for_coordinates(*_project(FREIBURG_WGS84, "EPSG:25833"), "EPSG:25833") == "EPSG:25832"


class TestReprojectBuildingCsv:
    def test_converts_coordinates_and_keeps_every_other_value(self, tmp_path):
        path = str(tmp_path / "Quartier IST.csv")
        _write_building_csv(path, FREIBURG_WGS84, "EPSG:25833")
        assert reproject_building_csv(path, "EPSG:25833", "EPSG:25832") == 2
        expected_x, expected_y = _project(FREIBURG_WGS84, "EPSG:25832")
        xs, ys = read_building_coordinates(path)
        assert xs == pytest.approx(expected_x, abs=1e-3)
        assert ys == pytest.approx(expected_y, abs=1e-3)
        frame = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)
        assert list(frame.columns)[0] == "Land"
        assert frame["Subtyp"].tolist() == ["03", "03", "03"]  # leading zero kept
        assert frame["Bundesland"].iloc[0] == "Baden-Württemberg"
        assert frame["UTM_X"].iloc[2] == ""  # row without coordinates untouched

    def test_missing_file_has_no_coordinates(self, tmp_path):
        xs, ys = read_building_coordinates(str(tmp_path / "fehlt.csv"))
        assert len(xs) == 0 and len(ys) == 0


@pytest.fixture
def project_presenter(qapp, tmp_path):
    """A ProjectPresenter on a temporary project with a view stub that records set_crs."""
    from types import SimpleNamespace

    from districtheatingsim.gui.MainTab.main_data_manager import ProjectConfigManager, ProjectFolderManager
    from districtheatingsim.gui.ProjectTab.project_tab import ProjectModel, ProjectPresenter

    config_manager = ProjectConfigManager(config_path=str(tmp_path / "recent.json"))
    folder_manager = ProjectFolderManager(config_manager)
    project = tmp_path / "Freiburg"
    (project / "Variante 1").mkdir(parents=True)
    folder_manager.project_folder = str(project)
    folder_manager.variant_folder = str(project / "Variante 1")
    folder_manager.project_crs = "EPSG:25833"
    calls = {"set_crs": [], "messages": []}
    view = SimpleNamespace(
        set_crs=lambda crs: calls["set_crs"].append(crs),
        show_message=lambda title, text: calls["messages"].append(text),
    )
    presenter = ProjectPresenter(ProjectModel(), view, folder_manager, None, config_manager)
    presenter.timer.stop()
    csv_path = str(project / "Definition Quartier IST" / "Quartier IST.csv")
    return presenter, folder_manager, calls, csv_path


def _answer(monkeypatch, button):
    from PyQt6.QtWidgets import QMessageBox

    asked = []

    def question(*args, **kwargs):
        asked.append(args[2] if len(args) > 2 else "")
        return button

    monkeypatch.setattr(QMessageBox, "question", staticmethod(question))
    return asked


class TestChangeProjectCrs:
    def test_switch_converts_the_building_coordinates(self, project_presenter, monkeypatch):
        from PyQt6.QtWidgets import QMessageBox

        presenter, folder_manager, calls, csv_path = project_presenter
        _write_building_csv(csv_path, FREIBURG_WGS84, "EPSG:25833")
        _answer(monkeypatch, QMessageBox.StandardButton.Yes)
        assert presenter.change_project_crs("EPSG:25832")
        assert folder_manager.project_crs == "EPSG:25832"
        assert read_building_coordinates(csv_path)[0] == pytest.approx(
            _project(FREIBURG_WGS84, "EPSG:25832")[0], abs=1e-3
        )
        settings = json.load(
            open(os.path.join(folder_manager.project_folder, "project_settings.json"), encoding="utf-8")
        )
        assert settings["crs"] == "EPSG:25832"

    def test_cancel_keeps_crs_and_coordinates(self, project_presenter, monkeypatch):
        from PyQt6.QtWidgets import QMessageBox

        presenter, folder_manager, calls, csv_path = project_presenter
        _write_building_csv(csv_path, FREIBURG_WGS84, "EPSG:25833")
        before = read_building_coordinates(csv_path)[0]
        _answer(monkeypatch, QMessageBox.StandardButton.Cancel)
        assert not presenter.change_project_crs("EPSG:25832")
        assert folder_manager.project_crs == "EPSG:25833"
        assert calls["set_crs"] == ["EPSG:25833"]  # the combo goes back
        assert read_building_coordinates(csv_path)[0] == pytest.approx(before)

    def test_geocoding_outside_the_zone_offers_the_fitting_crs(self, project_presenter, monkeypatch):
        from PyQt6.QtWidgets import QMessageBox

        presenter, folder_manager, calls, csv_path = project_presenter
        _write_building_csv(csv_path, FREIBURG_WGS84, "EPSG:25833")
        asked = _answer(monkeypatch, QMessageBox.StandardButton.Yes)
        presenter._check_coordinates_fit_crs()
        assert len(asked) == 1 and "EPSG:25832" in asked[0]
        assert folder_manager.project_crs == "EPSG:25832"

    def test_geocoding_inside_the_zone_asks_nothing(self, project_presenter, monkeypatch):
        from PyQt6.QtWidgets import QMessageBox

        presenter, folder_manager, calls, csv_path = project_presenter
        _write_building_csv(csv_path, ZITTAU_WGS84, "EPSG:25833")
        asked = _answer(monkeypatch, QMessageBox.StandardButton.Yes)
        presenter._check_coordinates_fit_crs()
        assert asked == [] and folder_manager.project_crs == "EPSG:25833"


def test_osmnx_export_is_labelled_with_the_project_crs(tmp_path):
    import geopandas as gpd
    from shapely.geometry import LineString

    from districtheatingsim.net_generation.osmnx_steiner_network import export_unified_network

    def lines(*coords):
        return gpd.GeoDataFrame(geometry=[LineString(c) for c in coords], crs="EPSG:25832")

    path = export_unified_network(
        lines([(412000, 5314000), (412100, 5314000)]),
        lines([(412000, 5314001), (412100, 5314001)]),
        lines([(412100, 5314000), (412100, 5314010)]),
        lines([(412000, 5314000), (411990, 5314000)]),
        str(tmp_path),
        crs="EPSG:25832",
    )
    data = json.load(open(path, encoding="utf-8"))
    assert data["crs"]["properties"]["name"].endswith("EPSG::25832")


def test_producer_address_is_geocoded_in_the_project_crs(qapp, monkeypatch):
    from districtheatingsim.gui.LeafletTab import layer_generation_dialog

    targets = []

    def fake_get_coordinates(address, from_crs="epsg:4326", to_crs="epsg:25833"):
        targets.append(to_crs)
        return 412550.8, 5314169.4

    monkeypatch.setattr(layer_generation_dialog, "get_coordinates", fake_get_coordinates)
    dialog = layer_generation_dialog.LayerGenerationDialog("", _FakeConfig(), project_crs="EPSG:25832")
    dialog.addressInput.setText("Deutschland,Baden-Württemberg,Freiburg im Breisgau,Vaubanallee 2")
    dialog.geocodeAndAdd()
    assert targets == ["EPSG:25832"]
    assert dialog.coordTable.item(0, 0).text() == "412550.8"


class _FakeConfig:
    def get_relative_path(self, key):
        return "x.csv"
