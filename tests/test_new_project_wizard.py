"""
The assistant "Neues Projekt" (user test 2026-10-08, report section 6, stage 2).

Creating a project asked for a folder and a name only; location, coordinate system, climate data
and the source of the buildings had to be found elsewhere (UT-H9, UT-K2), and an existing name
ended in "[WinError 183]" (UT-M17). Pins the name check, the location page (CRS suggestion, TRY
check), the answers, and that the presenter stores them in the new project.
"""

import os
from types import SimpleNamespace

import pytest

from districtheatingsim.gui.MainTab.new_project_wizard import (
    BUILDINGS_IMPORT,
    BUILDINGS_MANUAL,
    BUILDINGS_OSM,
    NewProjectChoice,
    new_project_summary,
    project_name_problem,
)

FREIBURG = (47.9961, 7.8494)
GOERLITZ = (51.1528, 14.9873)


class TestNameCheck:
    def test_valid(self, tmp_path):
        assert project_name_problem(str(tmp_path), "Quartier Nord") is None

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("", "Projektnamen"),
            ("   ", "Projektnamen"),
            ("Nord/Süd", "Zeichen"),
            ('Quartier "A"', "Zeichen"),
            ("Quartier.", "Punkt"),
        ],
    )
    def test_invalid_names(self, tmp_path, name, expected):
        assert expected in project_name_problem(str(tmp_path), name)

    def test_existing_project(self, tmp_path):
        (tmp_path / "Zittau").mkdir()
        assert project_name_problem(str(tmp_path), "Zittau") == (
            "Im Ordner gibt es bereits „Zittau“. Bitte wählen Sie einen anderen Namen."
        )

    def test_missing_folder(self, tmp_path):
        assert "vorhandenen Ordner" in project_name_problem(str(tmp_path / "fehlt"), "Zittau")
        assert "vorhandenen Ordner" in project_name_problem("", "Zittau")


@pytest.fixture
def wizard(qapp, tmp_path):
    from districtheatingsim.gui.MainTab.new_project_wizard import NewProjectWizard

    wizard = NewProjectWizard(str(tmp_path))
    yield wizard
    wizard.deleteLater()


class TestWizard:
    def test_defaults(self, wizard, tmp_path):
        choice = wizard.choice()
        assert choice == NewProjectChoice(parent_folder=str(tmp_path), name="Neues Projekt")
        assert (choice.crs, choice.climate_zone, choice.persons_per_household) == ("EPSG:25833", "9", 2)
        assert choice.building_source == BUILDINGS_IMPORT
        assert wizard.project_page.isComplete()

    def test_existing_name_blocks_the_next_page(self, wizard, tmp_path):
        (tmp_path / "Zittau").mkdir()
        wizard.project_page.name_edit.setText("Zittau")
        assert not wizard.project_page.isComplete()
        assert "gibt es bereits" in wizard.project_page.path_label.text()

    def test_place_suggests_crs_and_checks_the_climate_data(self, wizard):
        page = wizard.location_page
        assert "Geben Sie einen Ort an" in page.try_label.text()
        page.set_place(*FREIBURG, "Freiburg im Breisgau", "Freiburg im Breisgau, Baden-Württemberg, Deutschland")
        assert page.crs_combo.currentData() == "EPSG:25832"
        assert "590 km" in page.try_label.text() and "passt nicht" in page.try_label.text()
        assert "dwd.de" in page.try_label.text()

        page.set_place(*GOERLITZ, "Görlitz")
        assert page.crs_combo.currentData() == "EPSG:25833"
        assert "passt." in page.try_label.text()

    def test_own_try_file(self, wizard, tmp_path, monkeypatch):
        from PyQt6.QtWidgets import QFileDialog

        own = tmp_path / "TRY2015_479961078494_Jahr.dat"  # Freiburg, from the DWD
        own.write_text("", encoding="utf-8")
        monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(own), "")))
        page = wizard.location_page
        page.set_place(*FREIBURG, "Freiburg im Breisgau")
        page._choose_try()
        assert page.try_filename == str(own)
        assert page.try_label.text() == "TRY2015_479961078494_Jahr.dat – 0 km vom Ort entfernt, passt."

    def test_choice(self, wizard, tmp_path):
        wizard.project_page.name_edit.setText("  Vauban  ")
        page = wizard.location_page
        page.set_place(*FREIBURG, "Freiburg im Breisgau")
        page.climate_zone_combo.setCurrentIndex(page.climate_zone_combo.findData("12"))
        page.persons_spinbox.setValue(3)
        wizard.buildings_page.buttons[BUILDINGS_OSM].setChecked(True)

        choice = wizard.choice()
        assert choice.name == "Vauban" and choice.project_path == os.path.join(str(tmp_path), "Vauban")
        assert (choice.crs, choice.location, choice.location_name) == ("EPSG:25832", FREIBURG, "Freiburg im Breisgau")
        assert (choice.climate_zone, choice.persons_per_household, choice.try_filename) == ("12", 3, None)
        assert choice.building_source == BUILDINGS_OSM

    def test_place_search_thread(self, qapp, monkeypatch):
        from districtheatingsim.geocoding import geocoding
        from districtheatingsim.gui.MainTab.new_project_wizard import PlaceSearchThread
        from districtheatingsim.utilities.web_services import ServiceUnavailableError

        found, failed = [], []
        monkeypatch.setattr(geocoding, "find_place", lambda query: (*FREIBURG, "Freiburg"))
        thread = PlaceSearchThread("Freiburg")
        thread.found.connect(found.append)
        thread.failed.connect(failed.append)
        thread.run()

        def blocked(query):
            raise ServiceUnavailableError("Der Adressdienst antwortet nicht.")

        monkeypatch.setattr(geocoding, "find_place", blocked)
        thread.run()
        assert found == [(*FREIBURG, "Freiburg")] and failed == ["Der Adressdienst antwortet nicht."]


class TestSummary:
    def test_far_try_and_next_step(self, tmp_path):
        choice = NewProjectChoice(
            str(tmp_path), "Vauban", crs="EPSG:25832", location=FREIBURG, location_name="Freiburg", climate_zone="12"
        )
        text = new_project_summary(choice)
        assert "Standort: Freiburg (47,9961° N, 7,8494° O)" in text
        assert "Koordinatensystem: EPSG:25832" in text
        assert "mitgeliefertes TRY (Oberlausitz) – passt nicht zum Standort" in text
        assert "Klimazone (VDI 4655): 12 – Oberrheingraben und unteres Neckartal" in text
        assert "Gebäudetabelle" in text

    def test_without_location(self, tmp_path):
        text = new_project_summary(NewProjectChoice(str(tmp_path), "Zittau", building_source=BUILDINGS_MANUAL))
        assert "Standort" not in text and "passt nicht" not in text
        assert "Gebäude hinzufügen" in text


class _StubConfig:
    def set_last_project(self, *_):
        pass


class TestPresenter:
    def test_choice_is_stored_in_the_project(self, qapp, tmp_path):
        from districtheatingsim.gui.MainTab.main_data_manager import ProjectFolderManager
        from districtheatingsim.gui.MainTab.main_presenter import HeatSystemPresenter

        folder_manager = ProjectFolderManager(config_manager=_StubConfig())
        folder_manager.project_folder = str(tmp_path)
        own_try = tmp_path / "eigenes TRY.dat"
        own_try.write_text("", encoding="utf-8")
        choice = NewProjectChoice(
            str(tmp_path.parent),
            tmp_path.name,
            crs="EPSG:25832",
            location=FREIBURG,
            location_name="Freiburg",
            try_filename=str(own_try),
            climate_zone="12",
            persons_per_household=3,
        )
        HeatSystemPresenter._apply_new_project_choice(SimpleNamespace(folder_manager=folder_manager), choice)

        folder_manager.load_project_settings()
        assert folder_manager.project_crs == "EPSG:25832"
        assert folder_manager.location == {"lat": FREIBURG[0], "lon": FREIBURG[1], "name": "Freiburg"}
        assert os.path.basename(folder_manager.try_filename) == "eigenes TRY.dat"
        assert (folder_manager.climate_zone, folder_manager.persons_per_household) == ("12", 3)

    def test_existing_folder_is_refused_without_a_technical_error(self, qapp, tmp_path):
        from districtheatingsim.gui.MainTab.main_presenter import HeatSystemPresenter

        (tmp_path / "Zittau").mkdir()
        errors = []
        presenter = SimpleNamespace(view=SimpleNamespace(show_error_message=errors.append))
        assert HeatSystemPresenter.create_new_project(presenter, str(tmp_path), "Zittau") is False
        assert errors == [f"Im Ordner {tmp_path} gibt es bereits „Zittau“. Bitte wählen Sie einen anderen Namen."]
