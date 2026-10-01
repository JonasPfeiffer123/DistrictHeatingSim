"""Tests for the shared energy-system config name <-> filename mapping (B2) and discovery (G7)."""

import os

from districtheatingsim.gui.EnergySystemTab.config_naming import (
    config_file,
    config_files,
    config_name_to_filename,
    discover_configs,
    filename_to_config_name,
)


class TestConfigNaming:
    def test_default_maps_both_ways(self):
        assert config_name_to_filename("Standard") == "Ergebnisse.parquet"
        assert filename_to_config_name("Ergebnisse.parquet") == "Standard"
        assert filename_to_config_name("Ergebnisse.json") == "Standard"  # legacy format

    def test_normal_name_round_trips(self):
        assert config_name_to_filename("Variante A") == "Ergebnisse_Variante A.parquet"
        assert filename_to_config_name("Ergebnisse_Variante A.parquet") == "Variante A"
        assert filename_to_config_name("Ergebnisse_Variante A.json") == "Variante A"
        # full round-trip for a filename-safe name
        for name in ("CHP only", "PV + WP", "Szenario 2030"):
            assert filename_to_config_name(config_name_to_filename(name)) == name

    def test_illegal_chars_sanitised_consistently(self):
        # '/', '\\', ':' are illegal in filenames; they become '-' (lossy but identical in
        # both tabs, which is the point of sharing this — the comparison tab used to lack the
        # sanitiser). The round-trip yields the sanitised form, not the original slash.
        assert config_name_to_filename("A/B") == "Ergebnisse_A-B.parquet"
        assert config_name_to_filename("A\\B") == "Ergebnisse_A-B.parquet"
        assert config_name_to_filename("A:B") == "Ergebnisse_A-B.parquet"
        assert filename_to_config_name(config_name_to_filename("A/B")) == "A-B"

    def test_other_files_are_not_configs(self):
        for filename in ("Ergebnisse.pdf", "calculated_heat_generation.csv", "Ergebnisse_.json", "Notizen.json"):
            assert filename_to_config_name(filename) is None


class TestDiscoverConfigs:
    @staticmethod
    def _touch(folder, name, mtime):
        path = os.path.join(folder, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write("{}")
        os.utime(path, (mtime, mtime))
        return path

    def test_standard_first_both_formats_and_other_files_ignored(self, tmp_path):
        d = str(tmp_path)
        for name in ("Ergebnisse_Z.parquet", "Ergebnisse_A.json", "Ergebnisse.parquet", "Ergebnisse.pdf"):
            self._touch(d, name, 1_000_000_000)
        assert discover_configs(d) == [
            ("Standard", "Ergebnisse.parquet"),
            ("A", "Ergebnisse_A.json"),
            ("Z", "Ergebnisse_Z.parquet"),
        ]

    def test_config_in_both_formats_listed_once_with_the_newer_file(self, tmp_path):
        d = str(tmp_path)
        self._touch(d, "Ergebnisse_A.json", 1_000_000_000)
        newer = self._touch(d, "Ergebnisse_A.parquet", 1_100_000_000)
        assert discover_configs(d) == [("A", "Ergebnisse_A.parquet")]
        assert config_file(d, "A") == newer

        # An older app version re-saved the JSON afterwards: that one wins now.
        legacy = self._touch(d, "Ergebnisse_A.json", 1_200_000_000)
        assert config_file(d, "A") == legacy
        assert sorted(config_files(d, "A")) == sorted([legacy, newer])  # delete removes both

    def test_missing_folder_and_unknown_config(self, tmp_path):
        assert discover_configs(str(tmp_path / "nope")) == []
        assert config_file(str(tmp_path), "Standard") is None
        assert config_files(str(tmp_path), "Standard") == []
