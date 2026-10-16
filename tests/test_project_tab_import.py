"""
Building CSV import and round trips in the project tab (user test 2026-10-08).

UT-K3: "CSV importieren" with a file already in the internal schema loaded the *source* file,
so the project's ``Quartier IST.csv`` stayed empty and geocoding / "CSV speichern" wrote into the
user's original outside the project.
UT-H7: the project tab and the geocoding read the BOM-prefixed CSV as plain UTF-8 and wrote it
back with a BOM - one more BOM per save, until pandas no longer found the column ``Land``.
"""

import os

import pandas as pd
import pytest

HEADER = "Land;Bundesland;Stadt;Adresse;Wärmebedarf;Gebäudetyp;Subtyp;WW_Anteil;Typ_Heizflächen;VLT_max;Steigung_Heizkurve;RLT_max;Normaußentemperatur"
ROW = "Deutschland;Sachsen;Zittau;Markt 1;420000;GKO;03;0.1;HK;70;1.5;55;-16"


def _bom_count(path):
    data = open(path, "rb").read()
    count = 0
    while data.startswith(b"\xef\xbb\xbf"):
        count += 1
        data = data[3:]
    return count


class TestBomRoundTrip:
    def test_project_model_load_save_keeps_one_bom(self, tmp_path):
        from districtheatingsim.gui.ProjectTab.project_tab import ProjectModel

        path = str(tmp_path / "Quartier IST.csv")
        open(path, "w", encoding="utf-8-sig").write(HEADER + "\n" + ROW + "\n")
        model = ProjectModel()
        for _ in range(3):
            headers, data = model.load_csv(path)
            model.save_csv(path, headers, data)
        assert _bom_count(path) == 1
        assert model.load_csv(path)[0][0] == "Land"
        assert "Land" in pd.read_csv(path, sep=";", encoding="utf-8-sig").columns

    def test_project_model_repairs_accumulated_boms(self, tmp_path):
        from districtheatingsim.gui.ProjectTab.project_tab import ProjectModel

        path = str(tmp_path / "Quartier IST.csv")
        open(path, "wb").write(b"\xef\xbb\xbf" * 3 + (HEADER + "\n" + ROW + "\n").encode("utf-8"))
        model = ProjectModel()
        headers, data = model.load_csv(path)
        assert headers[0] == "Land"
        model.save_csv(path, headers, data)
        assert _bom_count(path) == 1

    def test_geocoding_twice_keeps_one_bom(self, tmp_path, monkeypatch):
        from districtheatingsim.geocoding import geocoding

        monkeypatch.setattr(geocoding, "locate_address", lambda address, to_crs=None: (486492.0, 5638274.8, "house"))
        path = str(tmp_path / "Quartier IST.csv")
        open(path, "w", encoding="utf-8-sig").write(HEADER + "\n" + ROW + "\n")
        for _ in range(2):
            summary = geocoding.process_data(path, crs="EPSG:25833")
        assert summary["success"] == 1
        assert _bom_count(path) == 1
        frame = pd.read_csv(path, sep=";", encoding="utf-8-sig")
        assert list(frame.columns)[0] == "Land" and frame["UTM_X"].iloc[0] == pytest.approx(486492.0)


@pytest.fixture
def presenter(qapp, tmp_path, monkeypatch):
    """ProjectPresenter on a temporary project; message boxes are recorded."""
    from types import SimpleNamespace

    from PyQt6.QtWidgets import QMessageBox, QTableWidget

    from districtheatingsim.gui.MainTab.main_data_manager import ProjectConfigManager, ProjectFolderManager
    from districtheatingsim.gui.ProjectTab.project_tab import ProjectModel, ProjectPresenter

    config_manager = ProjectConfigManager(config_path=str(tmp_path / "recent.json"))
    folder_manager = ProjectFolderManager(config_manager)
    project = tmp_path / "Zittau"
    (project / "Variante 1").mkdir(parents=True)
    (project / "Definition Quartier IST").mkdir()
    folder_manager.project_folder = str(project)
    folder_manager.variant_folder = str(project / "Variante 1")
    events = {"info": [], "question": []}
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: events["info"].append(a[2])))
    view = SimpleNamespace(
        csvTable=QTableWidget(),
        update_progress=lambda *a, **k: None,
        set_process_steps=lambda *a, **k: None,
        set_outdated=lambda *a, **k: None,
        show_message=lambda *a: None,
    )
    p = ProjectPresenter(ProjectModel(), view, folder_manager, None, config_manager)
    p.timer.stop()
    target = str(project / "Definition Quartier IST" / "Quartier IST.csv")
    return p, target, events


def _choose_file(monkeypatch, path):
    from PyQt6.QtWidgets import QFileDialog

    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (path, "")))


def _answer_question(monkeypatch, events, button):
    from PyQt6.QtWidgets import QMessageBox

    def question(*args, **kwargs):
        events["question"].append(args[2])
        return button

    monkeypatch.setattr(QMessageBox, "question", staticmethod(question))


class TestImportIntoProject:
    def test_file_in_the_internal_schema_is_copied_into_the_project(self, presenter, tmp_path, monkeypatch):
        p, target, events = presenter
        source = str(tmp_path / "meine_gebaeude.csv")
        # Comma-separated and without BOM: the project file must still come out as ';' + BOM.
        open(source, "w", encoding="utf-8").write(HEADER.replace(";", ",") + "\n" + ROW.replace(";", ",") + "\n")
        source_before = open(source, encoding="utf-8").read()
        _choose_file(monkeypatch, source)
        p.import_csv()
        assert p.model.current_file_path == target
        frame = pd.read_csv(target, sep=";", encoding="utf-8-sig", dtype=str)
        assert frame["Adresse"].tolist() == ["Markt 1"] and frame["Subtyp"].tolist() == ["03"]
        assert open(source, encoding="utf-8").read() == source_before  # the user's file is untouched
        assert p.view.csvTable.rowCount() == 1
        assert events["info"] and "1 Gebäude importiert" in events["info"][0]

    def test_existing_buildings_are_only_replaced_after_confirmation(self, presenter, tmp_path, monkeypatch):
        from PyQt6.QtWidgets import QMessageBox

        p, target, events = presenter
        open(target, "w", encoding="utf-8-sig").write(HEADER + "\n" + ROW.replace("Markt 1", "Rathaus") + "\n")
        source = str(tmp_path / "neu.csv")
        open(source, "w", encoding="utf-8").write(HEADER + "\n" + ROW + "\n")
        _choose_file(monkeypatch, source)
        _answer_question(monkeypatch, events, QMessageBox.StandardButton.No)
        p.import_csv()
        assert len(events["question"]) == 1 and "bereits 1 Gebäude" in events["question"][0]
        assert pd.read_csv(target, sep=";", encoding="utf-8-sig")["Adresse"].tolist() == ["Rathaus"]

    def test_an_empty_project_template_is_replaced_without_asking(self, presenter, tmp_path, monkeypatch):
        p, target, events = presenter
        open(target, "w", encoding="utf-8-sig").write(HEADER + "\n" + ";" * 12 + "\n")  # "CSV erstellen" template
        source = str(tmp_path / "neu.csv")
        open(source, "w", encoding="utf-8").write(HEADER + "\n" + ROW + "\n")
        _choose_file(monkeypatch, source)
        p.import_csv()
        assert events["question"] == []
        assert pd.read_csv(target, sep=";", encoding="utf-8-sig")["Adresse"].tolist() == ["Markt 1"]

    def test_choosing_the_project_file_itself_just_loads_it(self, presenter, monkeypatch):
        p, target, events = presenter
        open(target, "w", encoding="utf-8-sig").write(HEADER + "\n" + ROW + "\n")
        _choose_file(monkeypatch, target)
        p.import_csv()
        assert p.model.current_file_path == target and events["info"] == []
        assert os.path.exists(target)


class TestImportExcelTables:
    """UT-H5: Excel exports reach the project normalised, problems are shown before saving."""

    def test_windows_1252_with_decimal_commas(self, presenter, tmp_path, monkeypatch):
        p, target, events = presenter
        source = str(tmp_path / "excel.csv")
        row = ROW.replace("Markt 1", "Bautzner Straße 1").replace(";0.1;", ";0,1;").replace(";1.5;", ";1,5;")
        open(source, "w", encoding="cp1252").write(HEADER + "\n" + row + "\n")
        _choose_file(monkeypatch, source)
        p.import_csv()
        frame = pd.read_csv(target, sep=";", encoding="utf-8-sig", dtype=str)
        assert frame["Adresse"].tolist() == ["Bautzner Straße 1"]
        assert (frame["WW_Anteil"].tolist(), frame["Steigung_Heizkurve"].tolist()) == (["0.1"], ["1.5"])
        assert events["question"] == []

    def test_invalid_values_are_shown_before_anything_is_saved(self, presenter, tmp_path, monkeypatch):
        from PyQt6.QtWidgets import QMessageBox

        p, target, events = presenter
        source = str(tmp_path / "fehler.csv")
        open(source, "w", encoding="utf-8").write(HEADER + "\n" + ROW.replace(";GKO;", ";Büro;") + "\n")
        _choose_file(monkeypatch, source)
        _answer_question(monkeypatch, events, QMessageBox.StandardButton.No)
        p.import_csv()
        assert len(events["question"]) == 1 and "Zeile 2: Gebäudetyp „BÜRO“ ist unbekannt." in events["question"][0]
        assert not os.path.exists(target)

    def test_unreadable_file_is_reported(self, presenter, tmp_path, monkeypatch):
        from PyQt6.QtWidgets import QMessageBox

        p, target, events = presenter
        warnings = []
        monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a[2])))
        _choose_file(monkeypatch, str(tmp_path / "gibt_es_nicht.csv"))
        p.import_csv()
        assert len(warnings) == 1 and "konnte nicht gelesen werden" in warnings[0]
        assert not os.path.exists(target)
