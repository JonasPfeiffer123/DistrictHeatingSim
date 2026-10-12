"""
Outdated results along the chain buildings → load profiles → network → generators (UT-H10, UT-M14).

A variant copy took over every generator result, and after the buildings or load profiles
changed, the old numbers still showed in the comparison; file times cannot tell because every
project save rewrites the files. Each step now records what it was computed from
(``Berechnungsstand.json``). Pins the fingerprint, the chain of stamps, the progress tracker
(with the corrected steps of UT-M14) and the comparison's view of a variant.
"""

import json
import os
from types import SimpleNamespace

import pandas as pd
import pytest

from districtheatingsim.gui.ProjectTab.project_progress import (
    default_process_steps,
    evaluate_process_steps,
    outdated_summary,
    variant_outdated,
)
from districtheatingsim.utilities.calculation_state import (
    BUILDING_PROFILES,
    NETWORK_CALCULATION,
    STATE_FILENAME,
    TIME_SERIES,
    building_csv_fingerprint,
    building_data_fingerprint,
    climate_settings,
    generation_key,
    network_building_mismatch,
    new_stamp,
    outdated_results,
    read_state,
    record,
)

HEADER = "Land;Bundesland;Stadt;Adresse;Wärmebedarf;Gebäudetyp;Subtyp;WW_Anteil;Typ_Heizflächen;VLT_max;Steigung_Heizkurve;RLT_max;Normaußentemperatur"
ROWS = [
    "Deutschland;Sachsen;Zittau;Markt 1;420000;GKO;03;0.1;HK;70;1.5;55;-16",
    "Deutschland;Sachsen;Zittau;Markt 2;80000;HMF;03;0.2;HK;70;1.5;55;-16",
]
CLIMATE = climate_settings("TRY2015_511676144222_Jahr.dat", 2023, "9", 2)


def _project(tmp_path, rows=ROWS, coordinates=True):
    """A project with one variant; returns (variant folder, building CSV)."""
    variant = tmp_path / "Projekt" / "Variante 1"
    for sub in ("Lastgang", "Wärmenetz", "Ergebnisse"):
        (variant / sub).mkdir(parents=True)
    csv_dir = tmp_path / "Projekt" / "Definition Quartier IST"
    csv_dir.mkdir()
    header = HEADER + (";UTM_X;UTM_Y" if coordinates else "")
    lines = [row + (f";{486000 + i};{5638000 + i}" if coordinates else "") for i, row in enumerate(rows)]
    csv_path = csv_dir / "Quartier IST.csv"
    csv_path.write_text("\n".join([header, *lines]) + "\n", encoding="utf-8-sig")
    return str(variant), str(csv_path)


def _write_csv(csv_path, rows, coordinates=True):
    header = HEADER + (";UTM_X;UTM_Y" if coordinates else "")
    lines = [row + (f";{486000 + i};{5638000 + i}" if coordinates else "") for i, row in enumerate(rows)]
    open(csv_path, "w", encoding="utf-8-sig").write("\n".join([header, *lines]) + "\n")


def _computed_chain(variant, csv_path, configs=("Standard",)):
    """Stamps as if every step had been computed once, in order."""
    profiles = new_stamp({"Gebäudedaten": building_csv_fingerprint(csv_path), "Klimadaten": CLIMATE})
    record(variant, BUILDING_PROFILES, profiles)
    network = new_stamp({BUILDING_PROFILES: profiles["id"]})
    record(variant, NETWORK_CALCULATION, network)
    series = new_stamp({NETWORK_CALCULATION: network["id"]}, datei=os.path.join("Lastgang", "Lastgang.csv"))
    record(variant, TIME_SERIES, series)
    for config in configs:
        record(variant, generation_key(config), new_stamp({TIME_SERIES: series["id"]}))
    return profiles, network, series


class TestFingerprint:
    def test_table_and_csv_agree(self, tmp_path):
        _variant, csv_path = _project(tmp_path)
        table = pd.DataFrame(
            {
                "Adresse": ["anders 1", "anders 2"],
                "Wärmebedarf": [420000.0, "80000"],
                "Gebäudetyp": ["GKO", "HMF"],
                "Subtyp": ["3", "03"],
                "WW_Anteil": ["0,1", 0.2],
                "Typ_Heizflächen": ["HK", "HK"],
                "VLT_max": [70, 70],
                "Steigung_Heizkurve": [1.5, 1.5],
                "RLT_max": [55, 55],
                "Normaußentemperatur": [-16, -16],
                "Heizgrenztemperatur": [None, None],  # optional BDEW column of the building tab, empty
            }
        )
        padded = table.astype(object)
        padded.loc[len(padded)] = [None] * len(padded.columns)  # an empty row added in the table
        assert building_data_fingerprint(padded) == building_csv_fingerprint(csv_path)

    def test_demand_counts_coordinates_do_not(self, tmp_path):
        _variant, csv_path = _project(tmp_path)
        before = building_csv_fingerprint(csv_path)
        _write_csv(csv_path, ROWS, coordinates=False)  # before geocoding
        assert building_csv_fingerprint(csv_path) == before
        _write_csv(csv_path, [ROWS[0].replace("420000", "400000"), ROWS[1]])
        assert building_csv_fingerprint(csv_path) != before
        assert building_csv_fingerprint(str(tmp_path / "fehlt.csv")) is None


class TestState:
    def test_record_and_remove(self, tmp_path):
        stamp = new_stamp({"x": 1}, datei="a.csv")
        record(str(tmp_path), TIME_SERIES, stamp)
        assert read_state(str(tmp_path)) == {TIME_SERIES: stamp}
        assert stamp["datei"] == "a.csv" and len(stamp["id"]) == 32
        record(str(tmp_path), TIME_SERIES, None)
        assert read_state(str(tmp_path)) == {}

    def test_unreadable_or_missing(self, tmp_path):
        assert read_state(str(tmp_path)) == {}
        (tmp_path / STATE_FILENAME).write_text("{kaputt", encoding="utf-8")
        assert read_state(str(tmp_path)) == {}
        record(str(tmp_path / "gibt es nicht"), TIME_SERIES, new_stamp({}))  # no error


class TestChain:
    def test_freshly_computed_is_current(self, tmp_path):
        variant, csv_path = _project(tmp_path)
        _computed_chain(variant, csv_path)
        assert outdated_results(variant, csv_path, CLIMATE) == {}

    def test_changed_buildings_make_everything_downstream_outdated(self, tmp_path):
        variant, csv_path = _project(tmp_path)
        _computed_chain(variant, csv_path, configs=("Standard", "Solar"))
        _write_csv(csv_path, [ROWS[0], ROWS[1].replace("80000", "95000")])

        reasons = outdated_results(variant, csv_path, CLIMATE)
        assert reasons[BUILDING_PROFILES] == "Die Gebäudedaten wurden nach der Lastgangberechnung geändert."
        assert reasons[NETWORK_CALCULATION] == "Sie beruht auf veralteten Gebäudelastgängen."
        assert reasons[TIME_SERIES] == "Sie beruht auf einer veralteten Netzberechnung."
        assert set(reasons) >= {generation_key("Standard"), generation_key("Solar")}

    def test_recomputed_profiles_outdate_the_network(self, tmp_path):
        variant, csv_path = _project(tmp_path)
        _computed_chain(variant, csv_path)
        record(variant, BUILDING_PROFILES, new_stamp({"Gebäudedaten": building_csv_fingerprint(csv_path)}))
        reasons = outdated_results(variant, csv_path, CLIMATE)
        assert BUILDING_PROFILES not in reasons
        assert reasons[NETWORK_CALCULATION] == "Die Gebäudelastgänge wurden nach der Netzberechnung neu berechnet."
        assert generation_key("Standard") in reasons

    def test_new_time_series_outdates_only_the_generators(self, tmp_path):
        variant, csv_path = _project(tmp_path)
        _profiles, network, _series = _computed_chain(variant, csv_path)
        record(variant, TIME_SERIES, new_stamp({NETWORK_CALCULATION: network["id"]}))
        reasons = outdated_results(variant, csv_path, CLIMATE)
        assert reasons == {
            generation_key("Standard"): "Die Jahreszeitreihe wurde nach der Erzeugerberechnung neu berechnet."
        }

    def test_climate_settings_count(self, tmp_path):
        variant, csv_path = _project(tmp_path)
        _computed_chain(variant, csv_path)
        changed = climate_settings("TRY2015_479961078494_Jahr.dat", 2023, "12", 2)
        reasons = outdated_results(variant, csv_path, changed)
        assert reasons[BUILDING_PROFILES] == "Nach der Lastgangberechnung geändert: TRY, Klimazone."

    def test_projects_without_stamps_report_nothing(self, tmp_path):
        variant, csv_path = _project(tmp_path)
        assert outdated_results(variant, csv_path, CLIMATE) == {}


def _network(path, connections):
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[0, i], [10, i]]},
            "properties": {"feature_type": "building_connection"},
        }
        for i in range(connections)
    ]
    open(path, "w", encoding="utf-8").write(
        json.dumps({"type": "FeatureCollection", "features": features, "metadata": {"state": "dimensioned"}})
    )


def test_network_must_have_one_connection_per_building(tmp_path):
    variant, csv_path = _project(tmp_path)
    network = os.path.join(variant, "Wärmenetz", "Wärmenetz.geojson")
    _network(network, 2)
    assert network_building_mismatch(network, csv_path) is None
    _write_csv(csv_path, [*ROWS, ROWS[0].replace("Markt 1", "Markt 3")])
    assert network_building_mismatch(network, csv_path) == (
        "Die Gebäudeliste hat 3 Gebäude mit Koordinaten, das Wärmenetz 2 Hausanschlüsse – das Netz neu generieren."
    )


def _complete_variant(variant, csv_path):
    """Every file the five steps look for."""
    for name in ("Gebäude Lastgang.parquet", "Lastgang.csv"):
        open(os.path.join(variant, "Lastgang", name), "w").write("x")
    for name in (
        "Ergebnisse Netzinitialisierung.json",
        "Ergebnisse Netzinitialisierung.csv",
        "Konfiguration Netzinitialisierung.json",
    ):
        open(os.path.join(variant, "Wärmenetz", name), "w").write("x")
    _network(os.path.join(variant, "Wärmenetz", "Wärmenetz.geojson"), 2)
    open(os.path.join(variant, "Ergebnisse", "Ergebnisse_Solar.parquet"), "w").write("x")


class TestProgressTracker:
    def test_steps(self):
        """UT-M14: five numbered steps, no street download step, the tab names of the app."""
        steps = default_process_steps()
        assert [step["name"].split(":")[0] for step in steps] == [f"Schritt {n}" for n in range(1, 6)]
        assert not any("Straßendaten" in step["name"] for step in steps)
        text = " ".join(step["description"] for step in steps)
        for tab in (
            "Projektdefinition",
            "Wärmebedarf Gebäude",
            "Kartenansicht Wärmenetzgenerierung",
            "Wärmenetzberechnung",
            "Erzeugerauslegung und Wirtschaftlichkeitsrechnung",
        ):
            assert f"„{tab}“" in text

    def test_complete_and_current(self, tmp_path):
        variant, csv_path = _project(tmp_path)
        _complete_variant(variant, csv_path)
        _computed_chain(variant, csv_path, configs=("Solar",))
        steps = default_process_steps()
        _status, progress = evaluate_process_steps(variant, steps, CLIMATE)
        assert progress == 100.0  # the generators count with any saved config, no CSV export needed
        assert outdated_summary(steps) == ""

    def test_outdated_steps_do_not_count(self, tmp_path):
        variant, csv_path = _project(tmp_path)
        _complete_variant(variant, csv_path)
        _computed_chain(variant, csv_path, configs=("Solar",))
        _write_csv(csv_path, [*ROWS, ROWS[0].replace("Markt 1", "Markt 3")])  # a building added
        steps = default_process_steps()
        _status, progress = evaluate_process_steps(variant, steps, CLIMATE)

        outdated = {step["key"]: step["outdated"] for step in steps}
        assert outdated["buildings"] is None
        assert outdated["profiles"] == "Die Gebäudedaten wurden nach der Lastgangberechnung geändert."
        assert "3 Gebäude mit Koordinaten" in outdated["network"]
        assert outdated["simulation"] == "Sie beruht auf veralteten Gebäudelastgängen."
        assert outdated["generation"].startswith("Solar: ")
        assert progress == 20.0
        assert outdated_summary(steps) == (
            "⚠ Veraltet: Schritt 2, Schritt 3, Schritt 4, Schritt 5 – bitte neu berechnen (Details anzeigen)."
        )

    def test_variant_outdated_for_the_comparison(self, tmp_path):
        variant, csv_path = _project(tmp_path)
        _complete_variant(variant, csv_path)
        _computed_chain(variant, csv_path, configs=("Solar",))
        assert variant_outdated(variant)["configs"] == {}
        _write_csv(csv_path, [ROWS[0], ROWS[1].replace("80000", "95000")])
        assert variant_outdated(variant)["configs"] == {"Solar": "Sie beruht auf einer veralteten Jahreszeitreihe."}

    def test_details_dialog_without_required_files(self, qapp):
        from districtheatingsim.gui.ProjectTab.project_tab_dialogs import ProcessDetailsDialog

        steps = default_process_steps()
        evaluate_process_steps(None, steps)
        steps[1].update(completed=True, outdated="Die Gebäudedaten wurden geändert.")
        dialog = ProcessDetailsDialog(steps)  # the generator step has no required files: no ZeroDivisionError
        assert dialog.get_step_progress(steps[4]) == 0.0
        assert dialog.get_step_progress(steps[1]) == 100.0


class TestRecording:
    def test_heat_demand_records_what_it_computed_from(self, tmp_path):
        from districtheatingsim.gui.BuildingTab.building_tab import BuildingPresenter

        variant, csv_path = _project(tmp_path)
        inputs = {"Gebäudedaten": building_csv_fingerprint(csv_path), "Klimadaten": CLIMATE}
        shown = []
        presenter = SimpleNamespace(
            view=SimpleNamespace(
                set_calculation_running=lambda running: None,
                populate_building_combobox=lambda results: None,
                plot=lambda results: None,
                show_message=lambda *a: shown.append(a),
                show_error_message=lambda *a: shown.append(a),
            ),
            model=SimpleNamespace(base_path="ein anderes Projekt", results=None),
            _calc_base_path=variant,
            _calc_inputs=inputs,
        )
        outcome = SimpleNamespace(results={}, combined_data={}, json_path="x.parquet", save_error=None)
        BuildingPresenter._on_heat_demand_done(presenter, outcome)  # project changed meanwhile: still recorded
        assert read_state(variant)[BUILDING_PROFILES]["eingaben"] == inputs
        assert outdated_results(variant, csv_path, CLIMATE) == {}

    def test_energy_system_uses_the_time_series_of_its_load_profile(self, tmp_path):
        from districtheatingsim.gui.EnergySystemTab._01_energy_system_main_tab import EnergySystemTab

        variant, _csv = _project(tmp_path)
        series = new_stamp({}, datei=os.path.join("Lastgang", "Lastgang.csv"))
        record(variant, TIME_SERIES, series)
        tab = SimpleNamespace(base_path=variant)
        assert (
            EnergySystemTab._time_series_id_of(tab, os.path.join(variant, "Lastgang", "Lastgang.csv")) == (series["id"])
        )
        assert EnergySystemTab._time_series_id_of(tab, os.path.join(variant, "Lastgang", "anders.csv")) is None


@pytest.mark.parametrize("missing", [True, False])
def test_generation_step_needs_a_saved_config(tmp_path, missing):
    variant, csv_path = _project(tmp_path)
    if not missing:
        open(os.path.join(variant, "Ergebnisse", "Ergebnisse.parquet"), "w").write("x")
    steps = default_process_steps()
    evaluate_process_steps(variant, steps)
    assert steps[4]["completed"] is not missing


class TestOneBuildingEditor:
    """UT-M13: the heat demand tab had a second editor whose table overwrote the project tab's edits."""

    def test_heat_demand_tab_shows_the_saved_project_list(self, qtbot, tmp_path):
        from districtheatingsim.gui.BuildingTab.building_tab import BuildingModel, BuildingPresenter, BuildingTabView

        _variant, csv_path = _project(tmp_path)
        view = BuildingTabView()
        qtbot.addWidget(view)
        assert view.table_widget.editTriggers() == view.table_widget.EditTrigger.NoEditTriggers
        actions = [action.text() for action in view.menubar.actions()]
        assert "Neue CSV-Vorlage erstellen" not in actions and "Gebäudedaten speichern" not in actions

        folder_manager = SimpleNamespace(project_folder_changed=SimpleNamespace(connect=lambda slot: None))
        folder_manager.variant_folder = None
        presenter = BuildingPresenter(BuildingModel(), view, folder_manager, None, None)
        presenter.model.csv_path = csv_path
        presenter.refresh_buildings()
        assert view.table_widget.rowCount() == 2

        _write_csv(csv_path, [*ROWS, ROWS[0].replace("Markt 1", "Markt 3")])
        os.utime(csv_path, (1, 1))  # a different modification time, whatever the clock resolution
        presenter.refresh_buildings()
        assert view.table_widget.rowCount() == 3

    def test_project_table_is_saved_when_leaving_the_tab(self, qtbot, tmp_path):
        from PyQt6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem

        from districtheatingsim.gui.ProjectTab.project_tab import ProjectModel, ProjectPresenter

        _variant, csv_path = _project(tmp_path)
        table = QTableWidget()
        qtbot.addWidget(table)
        presenter = ProjectPresenter.__new__(ProjectPresenter)
        presenter.model = ProjectModel()
        presenter.view = SimpleNamespace(csvTable=table, statusLabel=QLabel(), show_message=lambda *a: None)
        presenter.update_progress_tracker = lambda: None
        presenter.table_modified = False
        table.itemChanged.connect(presenter._mark_table_modified)
        table.model().rowsInserted.connect(presenter._mark_table_modified)

        ProjectPresenter.load_csv(presenter, csv_path)
        assert presenter.table_modified is False  # loading is no edit
        assert presenter.save_if_modified() is False

        table.setItem(0, 4, QTableWidgetItem("462000"))
        assert presenter.save_if_modified() is True
        assert pd.read_csv(csv_path, sep=";", encoding="utf-8-sig")["Wärmebedarf"].iloc[0] == 462000
        assert "gespeichert" in presenter.view.statusLabel.text()
        assert presenter.table_modified is False

    def test_new_building_list_uses_the_import_template(self, qapp, tmp_path):
        from districtheatingsim.gui.ProjectTab.csv_import_dialog import TARGET_COLUMNS
        from districtheatingsim.gui.ProjectTab.project_tab import ProjectModel, ProjectPresenter

        presenter = ProjectPresenter.__new__(ProjectPresenter)
        presenter.model = ProjectModel()
        presenter.load_csv = lambda path: None
        path = str(tmp_path / "Quartier IST.csv")
        ProjectPresenter.create_csv(presenter, path, show_dialog=False)
        header = open(path, encoding="utf-8-sig").readline().strip().split(";")
        assert header == [name for name, *_ in TARGET_COLUMNS]
        assert {"Heizgrenztemperatur", "Heizexponent", "P_max"} <= set(header)
