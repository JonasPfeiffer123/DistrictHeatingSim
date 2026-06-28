"""
Unit tests for the GUI-free variant-comparison data layer (BACKLOG B1).

``comparison_data.py`` holds the discovery / loading / transform logic extracted
from the Qt ``ComparisonTab`` widgets so it can be tested without a QApplication.
``format_kpi_range`` has its own suite in ``test_comparison_kpis.py``.
"""

import json

import pytest

from districtheatingsim.gui.ComparisonTab.comparison_data import (
    clean_variant_name,
    discover_variant_configs,
    load_network_kpis,
    process_variant_results,
    variant_has_results,
)

# ----------------------------------------------------------------------------
# clean_variant_name
# ----------------------------------------------------------------------------


class TestCleanVariantName:
    def test_takes_part_after_last_separator(self):
        assert clean_variant_name("Projekt X - Görlitz - Variante 1") == "Variante 1"

    def test_name_without_separator_is_unchanged(self):
        assert clean_variant_name("Variante 1") == "Variante 1"


# ----------------------------------------------------------------------------
# Filesystem discovery (discover_variant_configs / variant_has_results)
# ----------------------------------------------------------------------------


def _make_variant(tmp_path, name, result_files):
    """Create ``<tmp>/<name>/Ergebnisse/`` with the given JSON files."""
    erg = tmp_path / name / "Ergebnisse"
    erg.mkdir(parents=True)
    for fn in result_files:
        (erg / fn).write_text("{}", encoding="utf-8")
    return tmp_path / name


class TestDiscoverVariantConfigs:
    def test_standard_first_then_named_configs(self, tmp_path):
        variant = _make_variant(
            tmp_path, "Variante 1", ["Ergebnisse.json", "Ergebnisse_Konfiguration B.json", "Ergebnisse_A.json"]
        )
        configs = discover_variant_configs(str(variant))

        # Standard always first; the remaining named configs follow in sorted order.
        assert configs[0] == ("Standard", "Ergebnisse.json")
        names = [c[0] for c in configs]
        assert "Standard" in names and len(configs) == 3
        # every entry maps a config name to an Ergebnisse*.json file
        assert all(fn.startswith("Ergebnisse") and fn.endswith(".json") for _, fn in configs)

    def test_no_standard_file(self, tmp_path):
        variant = _make_variant(tmp_path, "Variante 2", ["Ergebnisse_A.json"])
        configs = discover_variant_configs(str(variant))
        assert len(configs) == 1
        assert configs[0][1] == "Ergebnisse_A.json"
        assert configs[0][0] != "Standard"

    def test_missing_ergebnisse_dir_returns_empty(self, tmp_path):
        assert discover_variant_configs(str(tmp_path / "does_not_exist")) == []

    def test_ignores_non_result_files(self, tmp_path):
        variant = _make_variant(tmp_path, "Variante 3", ["Ergebnisse.json", "notes.txt", "other.json"])
        configs = discover_variant_configs(str(variant))
        assert configs == [("Standard", "Ergebnisse.json")]


class TestVariantHasResults:
    def test_true_when_result_file_present(self, tmp_path):
        variant = _make_variant(tmp_path, "Variante 1", ["Ergebnisse.json"])
        assert variant_has_results(str(variant)) is True

    def test_false_when_dir_missing(self, tmp_path):
        assert variant_has_results(str(tmp_path / "nope")) is False

    def test_false_when_no_result_files(self, tmp_path):
        variant = _make_variant(tmp_path, "Variante 1", ["notes.txt"])
        assert variant_has_results(str(variant)) is False


# ----------------------------------------------------------------------------
# load_network_kpis
# ----------------------------------------------------------------------------


class TestLoadNetworkKpis:
    def _write_net_config(self, tmp_path, kpi_results):
        net_dir = tmp_path / "Wärmenetz"
        net_dir.mkdir(parents=True)
        (net_dir / "Konfiguration Netzinitialisierung.json").write_text(
            json.dumps({"kpi_results": kpi_results}), encoding="utf-8"
        )

    def test_reads_all_kpis(self, tmp_path):
        self._write_net_config(
            tmp_path,
            {
                "Trassenlänge Wärmenetz [m]": 1234.5,
                "rel. Verteilverluste [%]": 12.3,
                "Pumpenstrom [MWh]": 4.2,
                "Anzahl angeschlossene Gebäude": 17,
            },
        )
        kpis = load_network_kpis(str(tmp_path))
        assert kpis["Trassenlänge"] == 1234.5
        assert kpis["Verteilverluste"] == 12.3
        assert kpis["Pumpenenergie"] == 4.2
        assert kpis["Anzahl_Gebäude"] == 17

    def test_missing_config_returns_zeros(self, tmp_path):
        kpis = load_network_kpis(str(tmp_path))
        assert kpis == {"Trassenlänge": 0, "Verteilverluste": 0, "Pumpenenergie": 0, "Anzahl_Gebäude": 0}

    def test_corrupt_json_returns_zeros(self, tmp_path):
        net_dir = tmp_path / "Wärmenetz"
        net_dir.mkdir(parents=True)
        (net_dir / "Konfiguration Netzinitialisierung.json").write_text("{not json", encoding="utf-8")
        kpis = load_network_kpis(str(tmp_path))
        assert kpis["Trassenlänge"] == 0


# ----------------------------------------------------------------------------
# process_variant_results
# ----------------------------------------------------------------------------


class TestProcessVariantResults:
    def test_rounds_and_scales_shares_to_percent(self):
        out = process_variant_results(
            {
                "techs": ["CHP", "GasBoiler"],
                "Wärmemengen": [1234.5678, 500.1234],
                "WGK": [95.456, 110.123],
                "Anteile": [0.7123, 0.2877],
                "Jahreswärmebedarf": 1734.691,
                "WGK_Gesamt": 99.987,
            }
        )
        assert out["Wärmemengen"] == [1234.57, 500.12]
        assert out["WGK"] == [95.46, 110.12]
        assert out["Anteile"] == [71.23, 28.77]  # fractions -> percent
        assert out["Jahreswärmebedarf"] == 1734.7
        assert out["WGK_Gesamt"] == 99.99

    def test_scalar_pe_is_broadcast_over_heat_quantities(self):
        # primärenergiefaktor_Gesamt scalar -> primärenergie_L = pe/w per tech.
        out = process_variant_results({"Wärmemengen": [100.0, 50.0], "primärenergiefaktor_Gesamt": 200.0})
        assert out["primärenergie_L"] == [round(200.0 / 100.0, 4), round(200.0 / 50.0, 4)]

    def test_zero_heat_quantity_does_not_divide_by_zero(self):
        out = process_variant_results({"Wärmemengen": [0.0, 80.0], "primärenergiefaktor_Gesamt": 160.0})
        assert out["primärenergie_L"][0] == 0  # guarded
        assert out["primärenergie_L"][1] == round(160.0 / 80.0, 4)

    def test_empty_results_yields_safe_defaults(self):
        out = process_variant_results({})
        assert out["techs"] == []
        assert out["Wärmemengen"] == []
        assert out["WGK_Gesamt"] == 0
        assert out["primärenergie_L"] == []

    def test_invalid_input_raises_value_error(self):
        # A non-numeric Wärmemenge breaks the round() -> wrapped as ValueError.
        with pytest.raises(ValueError):
            process_variant_results({"Wärmemengen": ["not a number"]})
