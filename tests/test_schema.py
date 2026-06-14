"""Unit tests for the shared versioned-JSON helper (BACKLOG D4).

`utilities/schema.py` centralizes the version + migrate bookkeeping that D2
duplicated across project_settings.json and the EnergySystem JSON. Pure dict
transforms, GUI-free — no fixtures needed.
"""

import logging

from districtheatingsim.utilities import schema


def test_add_meta_stamps_schema_and_app_version():
    out = schema.add_meta({"a": 1}, "project_settings")
    assert out["a"] == 1
    assert out["_meta"]["schema_version"] == schema.SCHEMA_VERSIONS["project_settings"]
    assert isinstance(out["_meta"]["app_version"], str) and out["_meta"]["app_version"]


def test_add_meta_does_not_mutate_input_and_drops_legacy_version():
    src = {"x": 2, "version": 1}
    out = schema.add_meta(src, "energy_system")
    assert "version" in src              # original untouched
    assert "version" not in out          # legacy top-level field dropped
    assert out["_meta"]["schema_version"] == schema.SCHEMA_VERSIONS["energy_system"]


def test_schema_version_of_reads_meta_block():
    assert schema.schema_version_of({"_meta": {"schema_version": 3}}) == 3


def test_schema_version_of_reads_legacy_top_level_version():
    assert schema.schema_version_of({"version": 2}) == 2


def test_schema_version_of_pre_versioning_is_zero():
    assert schema.schema_version_of({"crs": "EPSG:25833"}) == 0


def test_check_version_warns_when_newer(caplog):
    raw = {"_meta": {"schema_version": schema.SCHEMA_VERSIONS["project_settings"] + 5}}
    with caplog.at_level(logging.WARNING):
        found = schema.check_version(raw, "project_settings")
    assert found == schema.SCHEMA_VERSIONS["project_settings"] + 5
    assert any("newer than this app" in r.getMessage() for r in caplog.records)


def test_check_version_no_warning_when_current(caplog):
    raw = schema.add_meta({"a": 1}, "project_settings")
    with caplog.at_level(logging.WARNING):
        schema.check_version(raw, "project_settings")
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_roundtrip_add_then_read():
    out = schema.add_meta({"payload": True}, "energy_system")
    assert schema.schema_version_of(out) == schema.SCHEMA_VERSIONS["energy_system"]
