"""
Quality of the geocoding (user test 2026-10-08, UT-H6).

Nominatim answers an address whose house number it does not know with the street (and an empty or
unknown street with the town). Such points and buildings that end up on the same point used to be
reported as "found"; the network then got house connections in the middle of the street or several
on one spot. The summary now names them, the project table and the map mark them.
"""

import pandas as pd
import pytest
from geopy.location import Location

from districtheatingsim.geocoding import geocoding
from districtheatingsim.geocoding.geocoding import (
    PRECISION_HOUSE,
    PRECISION_STREET,
    PRECISION_TOWN,
    format_geocoding_summary,
    geocoding_row_notes,
    match_precision,
)

HEADER = "Land;Bundesland;Stadt;Adresse;Wärmebedarf"


def _csv(tmp_path, *addresses):
    path = tmp_path / "Quartier IST.csv"
    rows = [f"Deutschland;Baden-Württemberg;Freiburg im Breisgau;{a};1000" if a is not None else "" for a in addresses]
    path.write_text("\n".join([HEADER, *rows]) + "\n", encoding="utf-8-sig")
    return str(path)


# What Nominatim answered on 2026-10-12 (class / place_rank of the result)
ANSWERS = {
    "Vaubanallee": (412800.0, 5314300.0, PRECISION_STREET),  # rank 26, highway
    "Kurt-Tucholsky-Straße 9": (413020.0, 5314230.0, PRECISION_STREET),
    "Vaubanallee 9": (413200.0, 5314110.0, PRECISION_HOUSE),  # rank 30, building
    "Markt 1": (413500.0, 5314500.0, PRECISION_HOUSE),
    "Markt 1 a": (413500.04, 5314500.03, PRECISION_HOUSE),  # same building, 5 cm apart
    "Neuer Weg 3": (414900.0, 5316900.0, PRECISION_TOWN),  # rank 12, the town
}


@pytest.fixture
def fake_nominatim(monkeypatch):
    queried = []

    def locate(address, to_crs=None):
        queried.append(address)
        return ANSWERS.get(address.split(",")[0], (None, None, None))

    monkeypatch.setattr(geocoding, "locate_address", locate)
    return queried


class TestMatchPrecision:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ({"class": "building", "place_rank": 30}, PRECISION_HOUSE),
            ({"class": "place", "type": "house", "place_rank": "28"}, PRECISION_HOUSE),
            ({"class": "highway", "place_rank": 26}, PRECISION_STREET),
            ({"class": "highway", "place_rank": 27}, PRECISION_STREET),
            ({"class": "place", "type": "square", "place_rank": 25}, PRECISION_TOWN),
            ({"class": "boundary", "place_rank": 12}, PRECISION_TOWN),
            ({"class": "highway"}, PRECISION_STREET),  # no rank: the class decides
            ({}, PRECISION_HOUSE),  # nothing known: no false alarm
        ],
    )
    def test_place_rank(self, raw, expected):
        assert match_precision(raw) == expected

    def test_locate_address_reports_the_street_fallback(self, monkeypatch):
        monkeypatch.setattr(geocoding._geocode, "_sleep", lambda seconds: None)
        monkeypatch.setattr(geocoding._geocode, "min_delay_seconds", 0)
        raw = {"class": "highway", "type": "residential", "addresstype": "road", "place_rank": 26}
        street = Location("Kurt-Tucholsky-Straße, Vauban, Freiburg", (47.9754628, 7.8221123), raw)
        monkeypatch.setattr(geocoding._geocode, "func", lambda address: street)
        x, y, precision = geocoding.locate_address("Kurt-Tucholsky-Straße 9, Freiburg", to_crs="EPSG:25832")
        assert precision == PRECISION_STREET
        assert x == pytest.approx(413_000, abs=2000) and y == pytest.approx(5_314_200, abs=2000)
        assert geocoding.get_coordinates("Kurt-Tucholsky-Straße 9, Freiburg", to_crs="EPSG:25832") == (x, y)


class TestProcessData:
    def test_imprecise_and_shared_points_are_listed_with_their_row(self, tmp_path, fake_nominatim):
        path = _csv(
            tmp_path,
            "Vaubanallee",
            "Vaubanallee",
            "Kurt-Tucholsky-Straße 9",
            "Vaubanallee 9",
            "Nirgendwo 1",
            "Neuer Weg 3",
            "Markt 1",
            "Markt 1 a",
        )
        summary = geocoding.process_data(path, crs="EPSG:25832")

        assert (summary["total"], summary["success"], summary["failed"]) == (8, 7, 1)
        numbers = {key: [item["number"] for item in summary[key]] for key in ("not_found", "street_only", "town_only")}
        assert numbers == {"not_found": [5], "street_only": [1, 2, 3], "town_only": [6]}
        groups = [[item["number"] for item in group] for group in summary["same_point"]]
        assert groups == [[1, 2], [7, 8]]
        assert summary["street_only"][0]["address"] == "Vaubanallee, Freiburg im Breisgau"
        assert summary["street_only"][2]["x"] == 413020.0

        frame = pd.read_csv(path, sep=";", encoding="utf-8-sig")
        assert frame["UTM_X"].tolist()[:2] == [412800.0, 412800.0]

    def test_rows_without_address_are_not_sent_to_nominatim(self, tmp_path, fake_nominatim):
        """Nominatim answers ', Freiburg im Breisgau, …' with the town centre - a silent wrong point."""
        path = _csv(tmp_path, "Vaubanallee 9", "", None, "Markt 1")
        summary = geocoding.process_data(path, crs="EPSG:25832")

        assert len(fake_nominatim) == 2
        assert summary["total"] == 3  # the blank line is kept but not counted
        assert summary["not_found"] == [{"number": 2, "address": "(keine Adresse), Freiburg im Breisgau"}]
        lines = open(path, encoding="utf-8-sig").read().splitlines()
        assert len(lines) == 5 and lines[3] == ""  # header + 4 rows, blank line in place
        frame = pd.read_csv(path, sep=";", encoding="utf-8-sig", skip_blank_lines=False)
        assert frame["UTM_X"].tolist()[3] == 413500.0  # row numbers stay aligned with the table


class TestMessages:
    def _summary(self, tmp_path):
        path = _csv(tmp_path, "Vaubanallee", "Vaubanallee", "Kurt-Tucholsky-Straße 9", "Nirgendwo 1", "Markt 1")
        return geocoding.process_data(path, crs="EPSG:25832")

    def test_message_names_every_finding(self, tmp_path, fake_nominatim):
        all_fine, message = format_geocoding_summary(self._summary(tmp_path))
        assert not all_fine
        assert "4 von 5 Adressen gefunden" in message
        assert "Nicht gefunden (1):\n  • Nr. 4: Nirgendwo 1, Freiburg im Breisgau" in message
        assert "Nur die Straße gefunden, nicht das Haus (3)" in message
        assert "Nr. 3: Kurt-Tucholsky-Straße 9, Freiburg im Breisgau" in message
        assert "Mehrere Gebäude auf demselben Punkt (1 Gruppe):\n  • Nr. 1, 2: Vaubanallee, Freiburg im Breisgau" in (
            message
        )
        assert "Nr. = Zeile der Gebäudetabelle" in message

    def test_exact_matches_need_no_check(self, tmp_path, fake_nominatim):
        summary = geocoding.process_data(_csv(tmp_path, "Vaubanallee 9", "Markt 1"), crs="EPSG:25832")
        assert format_geocoding_summary(summary) == (True, "Geocoding abgeschlossen: 2 von 2 Adressen gefunden.")
        assert geocoding_row_notes(summary) == {}

    def test_long_lists_are_cut(self):
        items = [{"number": n, "address": f"Weg {n}"} for n in range(1, 41)]
        _ok, message = format_geocoding_summary({"total": 40, "success": 40, "street_only": items})
        assert "Nr. 15: Weg 15" in message and "Nr. 16: Weg 16" not in message
        assert "… und 25 weitere" in message

    def test_summary_without_rows_still_works(self):
        """Older callers only know failed_addresses."""
        all_fine, message = format_geocoding_summary(
            {"total": 2, "success": 1, "failed_addresses": ["Nirgendwo 1, Zittau, Sachsen, Deutschland"]}
        )
        assert not all_fine and "  • Nirgendwo 1, Zittau, Sachsen, Deutschland" in message
        assert "Nr." not in message

    def test_row_notes(self, tmp_path, fake_nominatim):
        notes = geocoding_row_notes(self._summary(tmp_path))
        assert notes == {
            1: "Nur die Straße gefunden, nicht das Haus; Gleicher Punkt wie Nr. 2",
            2: "Nur die Straße gefunden, nicht das Haus; Gleicher Punkt wie Nr. 1",
            3: "Nur die Straße gefunden, nicht das Haus",
            4: "Adresse nicht gefunden",
        }


class TestMarking:
    def test_project_table_marks_the_rows(self, qapp, tmp_path, fake_nominatim):
        from types import SimpleNamespace

        from PyQt6.QtWidgets import QTableWidget

        from districtheatingsim.gui.ProjectTab.project_tab import ProjectModel, ProjectPresenter

        path = _csv(tmp_path, "Vaubanallee", "Vaubanallee 9", "Nirgendwo 1")
        summary = geocoding.process_data(path, crs="EPSG:25832")
        presenter = SimpleNamespace(
            view=SimpleNamespace(csvTable=QTableWidget()),
            model=ProjectModel(),
            NOT_FOUND_COLOUR=ProjectPresenter.NOT_FOUND_COLOUR,
            IMPRECISE_COLOUR=ProjectPresenter.IMPRECISE_COLOUR,
        )
        ProjectPresenter.load_csv(presenter, path)
        ProjectPresenter._mark_geocoding_findings(presenter, summary)

        table = presenter.view.csvTable
        assert table.item(0, 3).toolTip() == "Nur die Straße gefunden, nicht das Haus"
        assert table.item(0, 0).background().color() == ProjectPresenter.IMPRECISE_COLOUR
        assert table.item(1, 3).toolTip() == ""
        assert table.item(2, 5).background().color() == ProjectPresenter.NOT_FOUND_COLOUR  # UTM column, empty

    def test_map_marks_imprecise_points(self, tmp_path, fake_nominatim):
        import json
        from types import SimpleNamespace

        from districtheatingsim.gui.LeafletTab.leaflet_tab import VisualizationPresenter

        scripts = []
        page = SimpleNamespace(runJavaScript=scripts.append)
        presenter = SimpleNamespace(
            view=SimpleNamespace(web_view=SimpleNamespace(page=lambda: page)),
            folder_manager=SimpleNamespace(project_crs="EPSG:25832"),
            GEOCODING_LAYER=VisualizationPresenter.GEOCODING_LAYER,
        )
        path = _csv(tmp_path, "Vaubanallee", "Vaubanallee", "Vaubanallee 9", "Nirgendwo 1")
        VisualizationPresenter._mark_geocoding_findings(presenter, geocoding.process_data(path, crs="EPSG:25832"))

        (script,) = scripts
        assert script.endswith(", 'Geocoding prüfen');")
        layer = json.loads(script[len("window.importGeoJSON(") : script.rindex(", 'Geocoding")])
        assert layer["crs"]["properties"]["name"] == "EPSG:25832"
        assert [f["properties"]["Nr."] for f in layer["features"]] == [1, 2]  # not found: no point
        assert layer["features"][0]["geometry"]["coordinates"] == [412800.0, 5314300.0]
        assert layer["features"][0]["properties"]["Hinweis"].startswith("Nur die Straße gefunden")
