"""Tests for the GUI-free building-CSV generation (B2: geojson_to_building_csv)."""

import csv
import json

import pytest

from districtheatingsim.geocoding.building_csv import (
    BUILDING_CSV_FIELDNAMES,
    centroid_of,
    geojson_to_building_csv,
)

_DEFAULTS = {
    "Wärmebedarf": 30000,
    "Gebäudetyp": "HMF",
    "Subtyp": "05",
    "WW_Anteil": 0.2,
    "Typ_Heizflächen": "HK",
    "VLT_max": 70,
    "Steigung_Heizkurve": 1.5,
    "RLT_max": 55,
    "Normaußentemperatur": -12,
}


class _FakeLocation:
    def __init__(self, address):
        self.raw = {"address": address}


class _FakeGeocoder:
    """Returns a canned address; records the queries it was asked."""

    def __init__(self, address):
        self._address = address
        self.queries = []

    def reverse(self, query, language=None, timeout=None):
        self.queries.append(query)
        return _FakeLocation(self._address)


class _IdentityTransformer:
    def transform(self, x, y):
        return x, y


def _write_geojson(path, polygons):
    features = [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": coords}} for coords in polygons]
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")


def _read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def test_centroid_of_polygon():
    # A unit square's centroid is its mid-point.
    assert centroid_of([[[10.0, 50.0], [10.0, 51.0], [11.0, 51.0], [11.0, 50.0]]]) == (10.5, 50.5)


def test_writes_geocoded_rows(tmp_path):
    geojson = tmp_path / "buildings.geojson"
    out = tmp_path / "buildings.csv"
    _write_geojson(geojson, [[[[10.0, 50.0], [10.0, 51.0], [11.0, 51.0], [11.0, 50.0]]]])
    geocoder = _FakeGeocoder(
        {"country": "Deutschland", "state": "Sachsen", "city": "Görlitz", "road": "Teststraße", "house_number": "7"}
    )

    progress_calls = []
    result = geojson_to_building_csv(
        str(geojson),
        str(out),
        _DEFAULTS,
        geocoder=geocoder,
        transformer=_IdentityTransformer(),
        progress=lambda *a: progress_calls.append(a),
    )

    assert result == str(out)
    rows = _read_csv(out)
    assert len(rows) == 1
    row = rows[0]
    assert list(row.keys()) == BUILDING_CSV_FIELDNAMES
    # geocoded address fields
    assert (row["Land"], row["Bundesland"], row["Stadt"]) == ("Deutschland", "Sachsen", "Görlitz")
    assert row["Adresse"] == "Teststraße 7"
    # centroid written as UTM_X/Y
    assert float(row["UTM_X"]) == pytest.approx(10.5)
    assert float(row["UTM_Y"]) == pytest.approx(50.5)
    # default building params carried through
    assert row["Gebäudetyp"] == "HMF"
    assert row["Wärmebedarf"] == "30000"
    # progress reported at start + per building
    assert progress_calls[0][0] == 0
    assert any(call[0] == 1 for call in progress_calls)


def test_geocoding_failure_falls_back_to_defaults(tmp_path):
    geojson = tmp_path / "b.geojson"
    out = tmp_path / "b.csv"
    _write_geojson(geojson, [[[[1.0, 2.0], [1.0, 3.0], [2.0, 3.0], [2.0, 2.0]]]])

    class _BoomGeocoder:
        def reverse(self, *a, **k):
            raise RuntimeError("network down")

    geojson_to_building_csv(
        str(geojson),
        str(out),
        {**_DEFAULTS, "Stadt": "FallbackStadt"},
        geocoder=_BoomGeocoder(),
        transformer=_IdentityTransformer(),
    )
    row = _read_csv(out)[0]
    assert row["Stadt"] == "FallbackStadt"  # default kept when geocoding fails
    assert float(row["UTM_X"]) == pytest.approx(1.5)


def test_should_stop_raises_interrupted(tmp_path):
    geojson = tmp_path / "b.geojson"
    out = tmp_path / "b.csv"
    _write_geojson(geojson, [[[[1.0, 2.0], [1.0, 3.0], [2.0, 3.0], [2.0, 2.0]]]])
    with pytest.raises(InterruptedError):
        geojson_to_building_csv(
            str(geojson),
            str(out),
            _DEFAULTS,
            geocoder=_FakeGeocoder({}),
            transformer=_IdentityTransformer(),
            should_stop=lambda: True,
        )


def test_missing_default_key_wrapped_as_runtimeerror(tmp_path):
    geojson = tmp_path / "b.geojson"
    out = tmp_path / "b.csv"
    _write_geojson(geojson, [[[[1.0, 2.0], [1.0, 3.0], [2.0, 3.0], [2.0, 2.0]]]])
    with pytest.raises(RuntimeError, match="Fehler beim Erstellen der CSV-Datei"):
        geojson_to_building_csv(
            str(geojson),
            str(out),
            {"Wärmebedarf": 1},  # missing other required keys
            geocoder=_FakeGeocoder({}),
            transformer=_IdentityTransformer(),
        )
