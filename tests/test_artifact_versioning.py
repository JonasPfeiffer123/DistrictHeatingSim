"""Round-trip tests for the D4 step-2 artifacts (building JSON, dialog_config.json).

Both now route save/load through utilities/schema.py: writes stamp a `_meta` block,
loads tolerate it (and legacy / pre-versioning files). These tests pin the format
change and that the extra `_meta` key does not leak into the consumers.
"""

import json

import pytest

from districtheatingsim.utilities.schema import SCHEMA_VERSIONS

pytestmark = pytest.mark.usefixtures("qapp")


class TestBuildingDataVersioning:
    @staticmethod
    def _model(json_path):
        from districtheatingsim.gui.BuildingTab.building_tab import BuildingModel
        m = BuildingModel()
        m.json_path = str(json_path)
        return m

    def _building_data(self):
        return {
            "0": {"wärme": [1.0, 2.0], "Adresse": "A-Str 1"},
            "1": {"wärme": [3.0, 4.0], "Adresse": "B-Str 2"},
        }

    def test_save_stamps_meta_and_load_skips_it(self, tmp_path):
        path = tmp_path / "buildings.json"
        m = self._model(path)
        m.save_json(self._building_data())

        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["_meta"]["schema_version"] == SCHEMA_VERSIONS["building_data"]
        assert "app_version" in raw["_meta"]

        m2 = self._model(path)
        m2.load_json()
        # The _meta block must not leak in as a building entry; the two buildings load.
        assert set(m2.results.keys()) == {"0", "1"}
        assert m2.results["0"]["wärme"] == [1.0, 2.0]

    def test_legacy_building_file_without_meta_loads(self, tmp_path):
        path = tmp_path / "buildings.json"
        path.write_text(json.dumps(self._building_data()), encoding="utf-8")  # no _meta
        m = self._model(path)
        m.load_json()  # must not raise
        assert set(m.results.keys()) == {"0", "1"}


class TestDialogConfigVersioning:
    def test_save_stamps_meta_and_load_roundtrips(self, tmp_path):
        from districtheatingsim.gui.NetSimulationTab.net_generation_dialog import (
            load_dialog_config,
            save_dialog_config,
        )
        path = str(tmp_path / "dialog_config.json")  # absolute → skips get_resource_path
        config = {"some_setting": 42, "nested": {"a": 1}}
        save_dialog_config(config, path)

        raw = json.loads((tmp_path / "dialog_config.json").read_text(encoding="utf-8"))
        assert raw["_meta"]["schema_version"] == SCHEMA_VERSIONS["dialog_config"]

        loaded = load_dialog_config(path)
        assert loaded["some_setting"] == 42
        assert loaded["nested"] == {"a": 1}

    def test_legacy_dialog_config_without_meta_loads(self, tmp_path):
        from districtheatingsim.gui.NetSimulationTab.net_generation_dialog import load_dialog_config
        path = tmp_path / "dialog_config.json"
        path.write_text(json.dumps({"some_setting": 7}), encoding="utf-8")  # no _meta
        loaded = load_dialog_config(str(path))  # must not raise
        assert loaded["some_setting"] == 7
