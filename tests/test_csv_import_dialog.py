"""
Importing real building tables (BACKLOG UT-H5, user test 2026-10-08).

An Excel "CSV (Trennzeichen-getrennt)" export from a German Windows broke the import with a
UnicodeDecodeError (Windows-1252). Read as UTF-8, the mapping dialog did not recognise "Nutzung"
and "Anteil WW", street and house number could not be combined, the decimal comma passed the
import and only broke the heat demand, empty cells became the text "nan", and the WW share had
no default.
"""

import os

import pandas as pd
import pytest

from districtheatingsim.gui.ProjectTab.csv_import_dialog import (
    _suggest_mapping,
    detect_encoding,
    normalise_number,
    prepare_buildings,
    read_source_table,
    validate_buildings,
)

EXCEL_EXPORT = os.path.join(os.path.dirname(__file__), "e2e", "inputs", "freiburg_excel_export.csv")


def _buildings(**overrides):
    row = {
        "Land": "Deutschland",
        "Bundesland": "Sachsen",
        "Stadt": "Zittau",
        "Adresse": "Markt 1",
        "Wärmebedarf": "420000",
        "Gebäudetyp": "GKO",
        "Subtyp": "03",
        "WW_Anteil": "0.1",
        "Typ_Heizflächen": "HK",
        "VLT_max": "70",
        "Steigung_Heizkurve": "1.5",
        "RLT_max": "55",
        "Normaußentemperatur": "-16",
    }
    row.update(overrides)
    return pd.DataFrame([row])


class TestReading:
    def test_excel_export_is_windows_1252(self):
        assert detect_encoding(EXCEL_EXPORT) == "cp1252"

    def test_utf8_with_and_without_bom(self, tmp_path):
        for encoding in ("utf-8", "utf-8-sig"):
            path = tmp_path / f"{encoding}.csv"
            path.write_text("Straße;Wärmebedarf\nMarkt 1;1\n", encoding=encoding)
            assert detect_encoding(str(path)) == "utf-8-sig"
            assert list(read_source_table(str(path))[0].columns) == ["Straße", "Wärmebedarf"]

    def test_excel_export_reads_with_umlauts_and_delimiter(self):
        table, delimiter, encoding = read_source_table(EXCEL_EXPORT)
        assert (delimiter, encoding) == (";", "cp1252")
        assert "Straße" in table.columns and "Jahreswärmebedarf [kWh]" in table.columns
        assert table["Straße"].iloc[5] == "Alfred-Döblin-Platz"

    def test_empty_cells_stay_empty(self, tmp_path):
        path = tmp_path / "leer.csv"
        path.write_text("Adresse;Gebäudetyp\nMarkt 1;\n", encoding="utf-8")
        assert read_source_table(str(path))[0]["Gebäudetyp"].tolist() == [""]


class TestNumbers:
    @pytest.mark.parametrize(
        ("text", "thousands", "expected"),
        [
            ("0,25", False, "0.25"),
            ("1.234,5", False, "1234.5"),
            (" 70 ", False, "70"),
            ("-16", False, "-16"),
            ("1.5", False, "1.5"),
            ("185.000", True, "185000"),
            ("1.234.567", True, "1234567"),
            ("185.000", False, "185.000"),
            ("1.5", True, "1.5"),
            ("185 000", True, "185000"),
            ("k. A.", False, "k.A."),
        ],
    )
    def test_normalise_number(self, text, thousands, expected):
        assert normalise_number(text, thousands) == expected

    def test_prepare_converts_decimal_commas_and_type_case(self):
        table = prepare_buildings(_buildings(WW_Anteil="0,25", Wärmebedarf="185.000", Gebäudetyp=" mfh "))
        row = table.iloc[0]
        assert (row["WW_Anteil"], row["Wärmebedarf"], row["Gebäudetyp"]) == ("0.25", "185000", "MFH")
        assert row["Subtyp"] == "03"  # text columns keep leading zeros


class TestValidation:
    def test_valid_table_has_no_problems(self):
        assert validate_buildings(prepare_buildings(_buildings())) == []

    def test_problems_name_the_line_and_the_field(self):
        table = pd.concat(
            [
                _buildings(),
                _buildings(Wärmebedarf="", Gebäudetyp="Wohnen", WW_Anteil="25", VLT_max="warm"),
            ],
            ignore_index=True,
        )
        problems = validate_buildings(prepare_buildings(table))
        assert "Zeile 3: Wärmebedarf [kWh/a] fehlt." in problems
        assert "Zeile 3: Gebäudetyp „WOHNEN“ ist unbekannt." in problems
        assert "Zeile 3: WW-Anteil [0–1] 25 liegt nicht zwischen 0 und 1." in problems
        assert "Zeile 3: VLT_max [°C] „warm“ ist keine Zahl." in problems
        assert any(p.startswith("Bekannte Gebäudetypen") for p in problems)
        assert not any(p.startswith("Zeile 2") for p in problems)

    def test_mixed_methods_are_reported(self):
        table = pd.concat([_buildings(), _buildings(Gebäudetyp="EFH")], ignore_index=True)
        assert any("gemischt" in p for p in validate_buildings(prepare_buildings(table)))


class TestMappingSuggestions:
    def test_short_names_only_match_exactly_or_by_alias(self):
        assert _suggest_mapping("Gebäudetyp", ["Typ"]) == "Typ"
        assert _suggest_mapping("Subtyp", ["Typ"]) == ""
        assert _suggest_mapping("Typ_Heizflächen", ["Typ"]) == ""


class TestDialog:
    @pytest.fixture
    def dialog(self, qapp):
        from districtheatingsim.gui.ProjectTab.csv_import_dialog import CsvImportDialog

        dialog = CsvImportDialog(EXCEL_EXPORT)
        yield dialog
        dialog.deleteLater()

    @staticmethod
    def _row(dialog, name):
        from districtheatingsim.gui.ProjectTab.csv_import_dialog import TARGET_COLUMNS

        return [column[0] for column in TARGET_COLUMNS].index(name)

    def test_excel_export_is_mapped_automatically(self, dialog):
        def source(name):
            return dialog.table.cellWidget(self._row(dialog, name), dialog._COL_SOURCE).currentText()

        assert source("Adresse") == "Straße"
        assert dialog.table.cellWidget(self._row(dialog, "Adresse"), dialog._COL_ADDITION).currentText() == "Hausnr."
        assert source("Stadt") == "Ort"
        assert source("Gebäudetyp") == "Nutzung"
        assert source("WW_Anteil") == "Anteil WW"
        assert source("Wärmebedarf") == "Jahreswärmebedarf [kWh]"

    def test_result_is_ready_for_the_heat_demand(self, dialog):
        dialog.table.cellWidget(self._row(dialog, "Bundesland"), dialog._COL_DEFAULT).setText("Baden-Württemberg")
        df, errors = dialog._build_result_df()
        assert errors == []
        first = df.iloc[0]
        assert first["Adresse"] == "Vaubanallee 1"
        assert first["Stadt"] == "Freiburg im Breisgau"
        assert (first["WW_Anteil"], first["Wärmebedarf"], first["Gebäudetyp"]) == ("0.25", "185000", "MFH")
        assert validate_buildings(df) == []
        assert not (df == "nan").any().any()

    def test_ww_share_has_a_default(self, qapp, tmp_path):
        from districtheatingsim.gui.ProjectTab.csv_import_dialog import CsvImportDialog

        path = tmp_path / "ohne_ww.csv"
        path.write_text(
            "Adresse;Stadt;Bundesland;Wärmebedarf;Gebäudetyp\nMarkt 1;Zittau;Sachsen;1000;HMF\n", encoding="utf-8"
        )
        dialog = CsvImportDialog(str(path))
        df, errors = dialog._build_result_df()
        assert errors == [] and df["WW_Anteil"].tolist() == ["0.2"]
        dialog.deleteLater()
