"""
Unit tests for the GUI-free project-progress evaluation (BACKLOG B1).

``project_progress.py`` holds the filesystem/CSV logic extracted from
``ProjectPresenter.update_progress_tracker`` so the step-completion tracker can be
tested without a QApplication.
"""

import json

from districtheatingsim.gui.ProjectTab.project_progress import (
    check_csv_status,
    check_network_dimensioned,
    evaluate_process_steps,
)

# ----------------------------------------------------------------------------
# check_csv_status
# ----------------------------------------------------------------------------


class TestCheckCsvStatus:
    def test_missing_file(self, tmp_path):
        assert check_csv_status(str(tmp_path / "nope.csv")) == "fehlt"

    def test_present_without_coordinate_columns(self, tmp_path):
        f = tmp_path / "q.csv"
        f.write_text("Name;Adresse\nHaus 1;Weg 1\n", encoding="utf-8")
        assert check_csv_status(str(f)) == "ist vorhanden"

    def test_coordinate_columns_but_no_data(self, tmp_path):
        f = tmp_path / "q.csv"
        f.write_text("Name;UTM_X;UTM_Y\nHaus 1;;\n", encoding="utf-8")
        assert check_csv_status(str(f)) == "ist vorhanden"

    def test_with_valid_coordinates(self, tmp_path):
        f = tmp_path / "q.csv"
        f.write_text("Name;UTM_X;UTM_Y\nHaus 1;33312345.6;5678901.2\n", encoding="utf-8")
        assert check_csv_status(str(f)) == "mit Koordinaten"

    def test_non_numeric_coordinates_counts_as_present(self, tmp_path):
        f = tmp_path / "q.csv"
        f.write_text("Name;UTM_X;UTM_Y\nHaus 1;abc;def\n", encoding="utf-8")
        assert check_csv_status(str(f)) == "ist vorhanden"

    def test_empty_file(self, tmp_path):
        f = tmp_path / "q.csv"
        f.write_text("", encoding="utf-8")
        assert check_csv_status(str(f)) == "ist vorhanden"


# ----------------------------------------------------------------------------
# check_network_dimensioned
# ----------------------------------------------------------------------------


class TestCheckNetworkDimensioned:
    def _write_network(self, tmp_path, metadata):
        f = tmp_path / "Wärmenetz.geojson"
        f.write_text(
            json.dumps({"type": "FeatureCollection", "features": [], "metadata": metadata}),
            encoding="utf-8",
        )
        return f

    def test_missing_file_is_false(self, tmp_path):
        assert check_network_dimensioned(str(tmp_path / "nope.geojson")) is False

    def test_dimensioned_state_is_true(self, tmp_path):
        f = self._write_network(tmp_path, {"state": "dimensioned"})
        assert check_network_dimensioned(str(f)) is True

    def test_other_state_is_false(self, tmp_path):
        f = self._write_network(tmp_path, {"state": "generated"})
        assert check_network_dimensioned(str(f)) is False

    def test_corrupt_file_is_false(self, tmp_path):
        f = tmp_path / "Wärmenetz.geojson"
        f.write_text("{not json", encoding="utf-8")
        assert check_network_dimensioned(str(f)) is False


# ----------------------------------------------------------------------------
# evaluate_process_steps
# ----------------------------------------------------------------------------


def _steps():
    """A minimal two-step tracker mirroring the presenter's schema."""
    return [
        {
            "name": "Schritt 1",
            "required_files": ["Quartier/Quartier IST.csv"],
            "csv_creation_status": "not_checked",
            "geocoding_status": "not_checked",
        },
        {
            "name": "Schritt 2",
            "required_files": ["Lastgang/Gebäude Lastgang.json"],
        },
    ]


class TestEvaluateProcessSteps:
    def test_no_base_path_marks_everything_incomplete(self):
        steps = _steps()
        csv_status, progress = evaluate_process_steps(None, steps)
        assert csv_status == "unbekannt"
        assert progress == 0.0
        assert all(not s["completed"] for s in steps)
        assert steps[0]["missing_files"] == steps[0]["required_files"]

    def test_first_step_csv_with_coordinates_completes_geocoding(self, tmp_path):
        (tmp_path / "Quartier").mkdir()
        (tmp_path / "Quartier" / "Quartier IST.csv").write_text(
            "Name;UTM_X;UTM_Y\nHaus 1;33312345.6;5678901.2\n", encoding="utf-8"
        )
        steps = _steps()
        csv_status, progress = evaluate_process_steps(str(tmp_path), steps)

        assert csv_status == "mit Koordinaten"
        assert steps[0]["csv_creation_status"] == "completed"
        assert steps[0]["geocoding_status"] == "completed"
        assert steps[0]["completed"] is True
        assert steps[1]["completed"] is False  # load profile missing
        assert progress == 50.0

    def test_csv_present_without_coordinates_marks_geocoding_pending(self, tmp_path):
        (tmp_path / "Quartier").mkdir()
        (tmp_path / "Quartier" / "Quartier IST.csv").write_text("Name;Adresse\nHaus 1;Weg 1\n", encoding="utf-8")
        steps = _steps()
        evaluate_process_steps(str(tmp_path), steps)
        assert steps[0]["geocoding_status"] == "pending"

    def test_missing_first_csv_marks_creation_pending(self, tmp_path):
        steps = _steps()
        csv_status, progress = evaluate_process_steps(str(tmp_path), steps)
        assert csv_status == "fehlt"
        assert steps[0]["csv_creation_status"] == "pending"
        assert steps[0]["geocoding_status"] == "not_applicable"
        assert progress == 0.0

    def test_all_files_present_reports_full_progress(self, tmp_path):
        (tmp_path / "Quartier").mkdir()
        (tmp_path / "Quartier" / "Quartier IST.csv").write_text(
            "Name;UTM_X;UTM_Y\nHaus 1;33312345.6;5678901.2\n", encoding="utf-8"
        )
        (tmp_path / "Lastgang").mkdir()
        (tmp_path / "Lastgang" / "Gebäude Lastgang.json").write_text("{}", encoding="utf-8")
        steps = _steps()
        _, progress = evaluate_process_steps(str(tmp_path), steps)
        assert progress == 100.0
        assert all(s["completed"] for s in steps)

    def test_dimensioned_network_step(self, tmp_path):
        # A step that additionally requires the network to be flagged "dimensioned".
        (tmp_path / "Wärmenetz").mkdir()
        net = tmp_path / "Wärmenetz" / "Wärmenetz.geojson"
        req = tmp_path / "Wärmenetz" / "Ergebnisse.p"
        req.write_text("x", encoding="utf-8")
        steps = [{"name": "Sim", "required_files": ["Wärmenetz/Ergebnisse.p"], "check_dimensioned_network": True}]

        # Network not dimensioned -> step incomplete + virtual missing entry appended.
        net.write_text(json.dumps({"metadata": {"state": "generated"}}), encoding="utf-8")
        evaluate_process_steps(str(tmp_path), steps)
        assert steps[0]["completed"] is False
        assert any("nicht dimensioniert" in m for m in steps[0]["missing_files"])

        # Network dimensioned + required file present -> step complete.
        net.write_text(json.dumps({"metadata": {"state": "dimensioned"}}), encoding="utf-8")
        evaluate_process_steps(str(tmp_path), steps)
        assert steps[0]["completed"] is True
        assert steps[0]["missing_files"] == []


def test_empty_step_list_does_not_divide_by_zero():
    csv_status, progress = evaluate_process_steps("/some/path", [])
    assert progress == 0.0
