"""
Project location and climate data (user test 2026-10-08, UT-H9).

Every new project got the bundled TRY (Oberlausitz) and VDI 4655 climate zone 9 / 2 persons per
household without a hint, and the solar thermal dialog was pre-filled with Görlitz in mixed signs
(UT-M4). Pins the location helpers, the new project settings, that the heat demand uses them,
the question before calculating with a far-away TRY and the solar location of a new collector.
"""

import json
import os
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from districtheatingsim.utilities.project_location import (
    CLIMATE_ZONES,
    SOLAR_STD_LONGITUDE,
    building_location,
    climate_data_warning,
    climate_zone_label,
    distance_km,
    format_location,
    solar_location_inputs,
    try_location,
)
from districtheatingsim.utilities.utilities import DEFAULT_TRY_RESOURCE, get_resource_path

BUNDLED_TRY = get_resource_path(DEFAULT_TRY_RESOURCE)
OBERLAUSITZ = (51.1676, 14.4222)
FREIBURG = (47.9787, 7.8296)
FREIBURG_25832 = (412_500.0, 5_314_200.0)


class TestLocationHelpers:
    def test_try_location_from_the_file_name(self):
        assert try_location(BUNDLED_TRY) == pytest.approx(OBERLAUSITZ)

    def test_try_location_from_the_header(self, tmp_path):
        """A renamed TRY still has its Lambert coordinates (EPSG:3034) in the header."""
        renamed = tmp_path / "Klima.dat"
        renamed.write_bytes(open(BUNDLED_TRY, "rb").read())
        lat, lon = try_location(str(renamed))
        assert (lat, lon) == pytest.approx(OBERLAUSITZ, abs=0.01)

    def test_unknown_file_has_no_location(self, tmp_path):
        other = tmp_path / "wetter.dat"
        other.write_text("Stunde;Temperatur\n", encoding="utf-8")
        assert try_location(str(other)) is None
        assert try_location("") is None

    def test_format_and_distance(self):
        assert format_location(*OBERLAUSITZ) == "51,1676° N, 14,4222° O"
        assert distance_km(OBERLAUSITZ, FREIBURG) == pytest.approx(593, abs=2)
        assert distance_km(OBERLAUSITZ, OBERLAUSITZ) == 0

    def test_climate_zones(self):
        assert list(CLIMATE_ZONES) == [str(n) for n in range(1, 16)]
        assert climate_zone_label("12") == "12 – Oberrheingraben und unteres Neckartal"

    def test_building_location(self, tmp_path):
        path = tmp_path / "Quartier IST.csv"
        x, y = FREIBURG_25832
        path.write_text(f"Adresse;UTM_X;UTM_Y\nA;{x};{y}\nB;{x + 200};{y - 200}\nC;;\n", encoding="utf-8-sig")
        lat, lon = building_location(str(path), "EPSG:25832")
        assert (lat, lon) == pytest.approx(FREIBURG, abs=0.01)
        assert building_location(str(tmp_path / "fehlt.csv"), "EPSG:25832") is None

    def test_warning_only_for_a_far_away_try(self):
        assert climate_data_warning(BUNDLED_TRY, None) is None
        assert climate_data_warning(BUNDLED_TRY, (51.15, 14.99)) is None  # Görlitz, 40 km
        message = climate_data_warning(BUNDLED_TRY, FREIBURG)
        assert "593 km" in message
        assert "TRY2015_511676144222_Jahr.dat" in message and "dwd.de" in message

    def test_solar_location_inputs(self):
        """The solar code counts longitudes west-positive: east of Greenwich is negative."""
        inputs = solar_location_inputs(FREIBURG)
        assert inputs == {"Latitude": 47.9787, "Longitude": -7.8296, "STD_Longitude": -15}
        assert SOLAR_STD_LONGITUDE == -15


class _StubConfig:
    def set_last_project(self, *_):
        pass

    def get_relative_path(self, key):
        assert key == "current_building_data_path"
        return os.path.join("..", "Definition Quartier IST", "Quartier IST.csv")


@pytest.fixture
def folder_manager(qapp, tmp_path):
    from districtheatingsim.gui.MainTab.main_data_manager import ProjectFolderManager

    manager = ProjectFolderManager(config_manager=_StubConfig())
    manager.project_folder = str(tmp_path)
    manager.variant_folder = str(tmp_path / "Variante 1")
    return manager


class TestProjectSettings:
    def test_defaults_are_the_former_fixed_values(self, folder_manager):
        folder_manager.load_project_settings()
        assert (folder_manager.climate_zone, folder_manager.persons_per_household) == ("9", 2)
        assert folder_manager.location is None

    def test_roundtrip(self, folder_manager, tmp_path):
        folder_manager.set_location(47.9787, 7.8296, "Freiburg im Breisgau")
        folder_manager.set_climate_zone("12")
        folder_manager.set_persons_per_household(3)

        raw = json.loads((tmp_path / "project_settings.json").read_text(encoding="utf-8"))
        assert raw["climate_zone"] == "12" and raw["persons_per_household"] == 3
        folder_manager.load_project_settings()
        assert folder_manager.location == {"lat": 47.9787, "lon": 7.8296, "name": "Freiburg im Breisgau"}
        assert (folder_manager.climate_zone, folder_manager.persons_per_household) == ("12", 3)
        assert folder_manager.project_location() == pytest.approx(FREIBURG)

    def test_invalid_values_fall_back(self, folder_manager, tmp_path):
        (tmp_path / "project_settings.json").write_text(
            json.dumps({"climate_zone": "99", "persons_per_household": "viele", "location": {"lat": 1}}),
            encoding="utf-8",
        )
        folder_manager.load_project_settings()
        assert (folder_manager.climate_zone, folder_manager.persons_per_household) == ("9", 2)
        assert folder_manager.location is None
        with pytest.raises(ValueError):
            folder_manager.set_climate_zone("16")

    def test_location_falls_back_to_the_buildings(self, folder_manager, tmp_path):
        assert folder_manager.project_location() is None
        csv_dir = tmp_path / "Definition Quartier IST"
        csv_dir.mkdir()
        x, y = FREIBURG_25832
        (csv_dir / "Quartier IST.csv").write_text(f"Adresse;UTM_X;UTM_Y\nA;{x};{y}\n", encoding="utf-8-sig")
        folder_manager.project_crs = "EPSG:25832"
        assert folder_manager.project_location() == pytest.approx(FREIBURG, abs=0.01)


class TestHeatDemand:
    def test_climate_zone_and_persons_reach_the_vdi_profiles(self):
        from districtheatingsim.heat_requirement.heat_requirement_calculation_csv import generate_profiles_from_csv

        buildings = pd.DataFrame(
            {
                "Wärmebedarf": [20000.0],
                "Gebäudetyp": ["EFH"],
                "Subtyp": ["05"],
                "WW_Anteil": [0.2],
                "Normaußentemperatur": [-12],
                "VLT_max": [70],
                "RLT_max": [55],
                "Steigung_Heizkurve": [1.5],
            }
        )
        zone9 = generate_profiles_from_csv(buildings, BUNDLED_TRY, "Datensatz", year=2023)[1]
        zone1 = generate_profiles_from_csv(buildings, BUNDLED_TRY, "Datensatz", year=2023, climate_zone="1")[1]
        persons = generate_profiles_from_csv(buildings, BUNDLED_TRY, "Datensatz", year=2023, number_people_household=4)[
            1
        ]
        for profile in (zone1, persons):
            np.testing.assert_allclose(profile.sum(), zone9.sum(), rtol=1e-3)  # same annual energy
            assert not np.allclose(profile, zone9)  # distributed differently over the days

    def test_thread_passes_the_project_settings(self, monkeypatch, tmp_path):
        from districtheatingsim.gui.BuildingTab import heat_demand_thread

        seen = {}

        def fake_profiles(**kwargs):
            seen.update(kwargs)
            raise RuntimeError("stop here")

        monkeypatch.setattr(heat_demand_thread, "generate_profiles_from_csv", fake_profiles)
        thread = heat_demand_thread.HeatDemandThread(
            pd.DataFrame({"a": [1]}), "try.dat", 2024, str(tmp_path / "x.parquet"), "12", 3
        )
        errors = []
        thread.calculation_error.connect(errors.append)
        thread.run()
        assert errors and (seen["climate_zone"], seen["number_people_household"], seen["year"]) == ("12", 3, 2024)


class TestClimateDataQuestion:
    @pytest.fixture
    def presenter(self, qapp, monkeypatch):
        from PyQt6.QtWidgets import QMessageBox

        questions = []
        answer = {"button": QMessageBox.StandardButton.No}

        def question(*args, **kwargs):
            questions.append(args[2])
            return answer["button"]

        monkeypatch.setattr(QMessageBox, "question", staticmethod(question))
        presenter = SimpleNamespace(
            view=None,
            folder_manager=SimpleNamespace(project_folder="Freiburg", project_location=lambda: FREIBURG),
            _confirmed_climate_data=set(),
        )
        return presenter, questions, answer

    def test_far_away_try_is_asked_once(self, presenter):
        from PyQt6.QtWidgets import QMessageBox

        from districtheatingsim.gui.BuildingTab.building_tab import BuildingPresenter

        p, questions, answer = presenter
        assert BuildingPresenter._climate_data_confirmed(p, BUNDLED_TRY) is False
        assert len(questions) == 1 and "km vom Projektstandort" in questions[0]
        answer["button"] = QMessageBox.StandardButton.Yes
        assert BuildingPresenter._climate_data_confirmed(p, BUNDLED_TRY) is True
        assert BuildingPresenter._climate_data_confirmed(p, BUNDLED_TRY) is True
        assert len(questions) == 2  # not asked again for this project and TRY

    def test_fitting_or_unknown_location_is_not_asked(self, presenter):
        from districtheatingsim.gui.BuildingTab.building_tab import BuildingPresenter

        p, questions, _answer = presenter
        p.folder_manager.project_location = lambda: (51.15, 14.99)
        assert BuildingPresenter._climate_data_confirmed(p, BUNDLED_TRY) is True
        p.folder_manager.project_location = lambda: None
        assert BuildingPresenter._climate_data_confirmed(p, BUNDLED_TRY) is True
        assert questions == []


class TestDialogs:
    def test_try_dialog_shows_the_distance(self, qapp):
        from districtheatingsim.gui.dialogs import TemperatureDataDialog

        dialog = TemperatureDataDialog()
        dialog.temperatureDataFileInput.setText(BUNDLED_TRY)
        assert dialog.locationLabel.text() == "Standort des TRY: 51,1676° N, 14,4222° O"
        dialog.set_project_location(FREIBURG)
        assert "km vom Projektstandort" in dialog.locationLabel.text()
        assert "passt nicht zum Projekt" in dialog.locationLabel.text()

    def test_new_solar_collector_lies_at_the_project(self, qapp, monkeypatch):
        from districtheatingsim.gui.EnergySystemTab import _03_technology_tab as tab_module

        shown = []

        class FakeDialog:
            def __init__(self, tech_type, tech_data):
                shown.append((tech_type, tech_data))

            def exec(self):
                return 0  # rejected

        monkeypatch.setattr(tab_module, "TechInputDialog", FakeDialog)
        tab = SimpleNamespace(data_manager=SimpleNamespace(project_location=lambda: FREIBURG))
        tab_module.TechnologyTab.addTech(tab, "Solarthermie", None)
        tab_module.TechnologyTab.addTech(tab, "Gaskessel", None)
        tab.data_manager.project_location = lambda: None
        tab_module.TechnologyTab.addTech(tab, "Solarthermie", None)
        assert shown == [
            ("Solarthermie", {"Latitude": 47.9787, "Longitude": -7.8296, "STD_Longitude": -15}),
            ("Gaskessel", None),
            ("Solarthermie", None),
        ]

    def test_no_foreign_places_are_pre_filled(self, qapp):
        """UT-M4: a Görlitz coordinate with a digit too many, Bad Muskau and Zittau in every project."""
        from districtheatingsim.gui.LeafletTab.layer_generation_dialog import LayerGenerationDialog

        class Config:
            def get_relative_path(self, key):
                return "x.csv"

        dialog = LayerGenerationDialog("", Config(), project_crs="EPSG:25832")
        assert dialog.coordInput.text() == "" and dialog.addressInput.text() == ""

    def test_map_opens_at_the_project(self):
        from districtheatingsim.gui.LeafletTab.leaflet_tab import VisualizationPresenter

        scripts = []
        page = SimpleNamespace(runJavaScript=scripts.append)
        presenter = SimpleNamespace(
            view=SimpleNamespace(web_view=SimpleNamespace(page=lambda: page)),
            folder_manager=SimpleNamespace(project_location=lambda: FREIBURG),
        )
        VisualizationPresenter._center_map_on_project(presenter)
        presenter.folder_manager.project_location = lambda: None
        VisualizationPresenter._center_map_on_project(presenter)
        assert scripts == ["window.map && window.map.setView([47.9787, 7.8296], 15);"]


def test_find_place(monkeypatch):
    from geopy.location import Location

    from districtheatingsim.geocoding import geocoding

    monkeypatch.setattr(geocoding._geocode, "_sleep", lambda seconds: None)
    monkeypatch.setattr(geocoding._geocode, "min_delay_seconds", 0)
    town = Location("Freiburg im Breisgau, Baden-Württemberg, Deutschland", (47.996, 7.849), {"place_rank": 16})
    monkeypatch.setattr(geocoding._geocode, "func", lambda query: town if "Freiburg" in query else None)
    assert geocoding.find_place("Freiburg") == (47.996, 7.849, "Freiburg im Breisgau, Baden-Württemberg, Deutschland")
    assert geocoding.find_place("Nirgendwo") is None
    assert geocoding.find_place("  ") is None
