"""Tests for the shared energy-system config name <-> filename mapping (B2)."""

from districtheatingsim.gui.EnergySystemTab.config_naming import (
    config_name_to_filename,
    filename_to_config_name,
)


class TestConfigNaming:
    def test_default_maps_both_ways(self):
        assert config_name_to_filename("Standard") == "Ergebnisse.json"
        assert filename_to_config_name("Ergebnisse.json") == "Standard"

    def test_normal_name_round_trips(self):
        assert config_name_to_filename("Variante A") == "Ergebnisse_Variante A.json"
        assert filename_to_config_name("Ergebnisse_Variante A.json") == "Variante A"
        # full round-trip for a filename-safe name
        for name in ("CHP only", "PV + WP", "Szenario 2030"):
            assert filename_to_config_name(config_name_to_filename(name)) == name

    def test_illegal_chars_sanitised_consistently(self):
        # '/', '\\', ':' are illegal in filenames; they become '-' (lossy but identical in
        # both tabs, which is the point of sharing this — the comparison tab used to lack the
        # sanitiser). The round-trip yields the sanitised form, not the original slash.
        assert config_name_to_filename("A/B") == "Ergebnisse_A-B.json"
        assert config_name_to_filename("A\\B") == "Ergebnisse_A-B.json"
        assert config_name_to_filename("A:B") == "Ergebnisse_A-B.json"
        assert filename_to_config_name(config_name_to_filename("A/B")) == "A-B"
