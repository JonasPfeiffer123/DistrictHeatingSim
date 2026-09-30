"""
Tests for the building load profiles file (BACKLOG G7): written as a Parquet array store,
legacy JSON still read, and the newer of both files preferred when a project has both.
"""

import json
import os
from pathlib import Path

import pytest

from districtheatingsim.heat_requirement.building_profiles_io import (
    current_format_path,
    preferred_profiles_path,
    read_building_profiles,
    write_building_profiles,
)
from districtheatingsim.utilities.schema import SCHEMA_VERSIONS

_GOERLITZ_JSON = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "districtheatingsim"
    / "project_data"
    / "Görlitz"
    / "Variante 1"
    / "Lastgang"
    / "Gebäude Lastgang.json"
)


@pytest.mark.skipif(not _GOERLITZ_JSON.exists(), reason="Görlitz project data not present")
def test_goerlitz_profiles_round_trip_identically_and_smaller(tmp_path):
    original = json.loads(_GOERLITZ_JSON.read_text(encoding="utf-8"))
    buildings = {k: v for k, v in original.items() if k != "_meta"}
    parquet = tmp_path / "Gebäude Lastgang.parquet"

    write_building_profiles(str(parquet), buildings)
    loaded = read_building_profiles(str(parquet))

    assert loaded["_meta"]["schema_version"] == SCHEMA_VERSIONS["building_data"]
    assert json.dumps({k: v for k, v in loaded.items() if k != "_meta"}) == json.dumps(buildings)
    assert parquet.stat().st_size < 0.2 * _GOERLITZ_JSON.stat().st_size  # measured: 1.9 vs 15.8 MB


def test_json_suffix_writes_legacy_json_and_format_is_detected_by_content(tmp_path):
    data = {"0": {"wärme": [float(i) for i in range(100)], "Adresse": "A-Str 1"}}
    as_json, as_other_name = tmp_path / "a.json", tmp_path / "b.dat"

    write_building_profiles(str(as_json), data)
    write_building_profiles(str(as_other_name), data)

    assert json.loads(as_json.read_text(encoding="utf-8"))["0"] == data["0"]
    assert read_building_profiles(str(as_json))["0"] == data["0"]
    assert read_building_profiles(str(as_other_name))["0"] == data["0"]  # Parquet, despite the name


def test_preferred_path_takes_the_newer_file(tmp_path):
    current, legacy = str(tmp_path / "L.parquet"), str(tmp_path / "L.json")
    assert preferred_profiles_path(current, legacy) == current  # neither exists

    Path(legacy).write_text("{}", encoding="utf-8")
    assert preferred_profiles_path(current, legacy) == legacy  # only the legacy file

    Path(current).write_bytes(b"")
    os.utime(legacy, (1_000_000_000, 1_000_000_000))
    os.utime(current, (1_100_000_000, 1_100_000_000))
    assert preferred_profiles_path(current, legacy) == current

    os.utime(legacy, (1_200_000_000, 1_200_000_000))  # re-saved by an older app version
    assert preferred_profiles_path(current, legacy) == legacy


def test_current_format_path():
    assert current_format_path(os.path.join("x", "Gebäude Lastgang.json")) == os.path.join(
        "x", "Gebäude Lastgang.parquet"
    )
