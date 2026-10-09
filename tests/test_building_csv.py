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

    assert result["path"] == str(out)
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


# --- UT-K5: OSM buildings as they come (user test 2026-10-08, Ostritz) ---------------------------


def _square(x0, y0, side):
    return [[[x0, y0], [x0 + side, y0], [x0 + side, y0 + side], [x0, y0 + side], [x0, y0]]]


def _write_osm(path, buildings):
    """Buildings as (properties, side length in m) at distinct positions, as the OSM download saves them."""
    features = [
        {
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Polygon", "coordinates": _square(i * 100, 0, side)},
        }
        for i, (props, side) in enumerate(buildings)
    ]
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8"
    )


class _CountingGeocoder:
    """Answers each reverse query with the next result (an address dict or an exception)."""

    def __init__(self, *results):
        self.results = list(results)
        self.queries = []

    def reverse(self, query, language=None, timeout=None):
        self.queries.append(query)
        result = self.results.pop(0) if self.results else {}
        if isinstance(result, Exception):
            raise result
        return _FakeLocation(result)


def _convert(tmp_path, buildings, geocoder, defaults=None, **options):
    geojson, out = tmp_path / "osm.geojson", tmp_path / "osm.csv"
    _write_osm(geojson, buildings)
    summary = geojson_to_building_csv(
        str(geojson),
        str(out),
        {**_DEFAULTS, "Stadt": "Ostritz", **(defaults or {})},
        geocoder=geocoder,
        transformer=_IdentityTransformer(),
        min_delay_s=0,
        **options,
    )
    return summary, _read_csv(out)


class TestOsmBuildings:
    def test_osm_addresses_are_used_and_only_the_rest_is_looked_up(self, tmp_path):
        geocoder = _CountingGeocoder({"road": "Klosterstraße", "house_number": "4", "town": "Ostritz"})
        summary, rows = _convert(
            tmp_path,
            [
                ({"building": "house", "addr:street": "Spanntigstraße", "addr:housenumber": "5"}, 10),
                ({"building": "yes"}, 10),
            ],
            geocoder,
        )
        assert [row["Adresse"] for row in rows] == ["Spanntigstraße 5", "Klosterstraße 4"]
        assert len(geocoder.queries) == 1
        assert (summary["address_from_osm"], summary["address_reverse"]) == (1, 1)

    def test_a_failed_lookup_stays_empty_instead_of_copying_another_address(self, tmp_path):
        geocoder = _CountingGeocoder(RuntimeError("no result"), {"road": "Markt", "house_number": "1"})
        summary, rows = _convert(
            tmp_path, [({"building": "yes"}, 10), ({"building": "yes"}, 10)], geocoder, {"Adresse": "Spanntigstraße 5"}
        )
        assert [row["Adresse"] for row in rows] == ["", "Markt 1"]
        assert summary["without_address"] == [2]  # CSV line of the first building

    def test_outbuildings_and_small_huts_are_skipped(self, tmp_path):
        summary, rows = _convert(
            tmp_path,
            [
                ({"building": "garage"}, 6),
                ({"building": "garages"}, 20),
                ({"building": "shed"}, 3),
                ({"building": "yes"}, 4),  # 16 m², no address: a garden hut
                ({"building": "yes", "addr:street": "Markt", "addr:housenumber": "2"}, 4),  # small, but addressed
                ({"building": "church", "addr:street": "Kirchplatz", "addr:housenumber": "1"}, 30),
            ],
            _CountingGeocoder(),
            min_footprint_m2=30,
        )
        assert [row["Adresse"] for row in rows] == ["Markt 2", "Kirchplatz 1"]
        assert summary["skipped_outbuildings"] == {"garage": 1, "garages": 1, "shed": 1}
        assert summary["skipped_small"] == 1 and summary["written"] == 2 and summary["total"] == 6

    def test_demand_from_footprint_storeys_and_specific_value(self, tmp_path):
        summary, rows = _convert(
            tmp_path,
            [
                ({"building": "apartments", "building:levels": "4", "addr:street": "A", "addr:housenumber": "1"}, 10),
                ({"building": "house", "addr:street": "B", "addr:housenumber": "2"}, 10),
            ],
            _CountingGeocoder(),
            specific_demand_kwh_m2=100,
            default_storeys=2,
        )
        assert [row["Wärmebedarf"] for row in rows] == ["40000", "20000"]  # 100 m² × 4 / × 2 × 100 kWh/m²
        assert [row["Gebäudetyp"] for row in rows] == ["HMF", "HEF"]

    def test_without_estimate_every_building_gets_the_default_demand(self, tmp_path):
        _summary, rows = _convert(
            tmp_path, [({"building": "house", "addr:street": "B", "addr:housenumber": "2"}, 10)], _CountingGeocoder()
        )
        assert rows[0]["Wärmebedarf"] == "30000"

    def test_residential_types_follow_the_method_of_the_default(self, tmp_path):
        _summary, rows = _convert(
            tmp_path,
            [
                ({"building": "detached", "addr:street": "A", "addr:housenumber": "1"}, 10),
                ({"building": "apartments", "addr:street": "B", "addr:housenumber": "2"}, 10),
                ({"building": "school", "addr:street": "C", "addr:housenumber": "3"}, 10),
            ],
            _CountingGeocoder(),
            {"Gebäudetyp": "MFH"},
        )
        assert [row["Gebäudetyp"] for row in rows] == ["EFH", "MFH", "MFH"]

    def test_a_blocked_nominatim_is_not_asked_for_every_building(self, tmp_path):
        from geopy.exc import GeocoderRateLimited

        geocoder = _CountingGeocoder(*[GeocoderRateLimited("429")] * 20)
        summary, rows = _convert(tmp_path, [({"building": "yes"}, 10)] * 8, geocoder)
        assert len(rows) == 8 and all(row["Adresse"] == "" for row in rows)
        # three buildings, each with the rate limiter's two retries, then no more requests
        assert len(geocoder.queries) == 9
        assert "Nominatim" in summary["service_error"]

    def test_lookups_are_throttled(self, tmp_path):
        import time

        geojson, out = tmp_path / "osm.geojson", tmp_path / "osm.csv"
        _write_osm(geojson, [({"building": "yes"}, 10)] * 3)
        started = time.monotonic()
        geojson_to_building_csv(
            str(geojson),
            str(out),
            _DEFAULTS,
            geocoder=_CountingGeocoder(),
            transformer=_IdentityTransformer(),
            min_delay_s=0.2,
        )
        assert time.monotonic() - started >= 0.38  # two pauses between three requests

    def test_utf8_geojson_regardless_of_the_locale(self, tmp_path):
        _summary, rows = _convert(
            tmp_path,
            [({"building": "house", "addr:street": "Görlitzer Straße", "addr:housenumber": "3"}, 10)],
            _CountingGeocoder(),
        )
        assert rows[0]["Adresse"] == "Görlitzer Straße 3"

    def test_report_for_the_user(self, tmp_path):
        from districtheatingsim.geocoding.building_csv import format_building_csv_summary

        summary, _rows = _convert(
            tmp_path,
            [
                ({"building": "garage"}, 6),
                ({"building": "yes"}, 10),
                ({"building": "house", "addr:street": "A", "addr:housenumber": "1"}, 10),
            ],
            _CountingGeocoder(RuntimeError("no result")),
            specific_demand_kwh_m2=100,
        )
        report = format_building_csv_summary(summary)
        assert "2 von 3 OSM-Gebäuden übernommen." in report
        assert "Nebengebäude übersprungen: 1 (1× garage)." in report
        assert "Adressen: 1 aus OpenStreetMap, 0 über Nominatim ermittelt." in report
        assert "Ohne Adresse: 1 Gebäude (CSV-Zeilen 2)" in report
        assert "100 kWh/(m²·a)" in report


def test_relation_with_its_inner_ring_first_has_a_positive_footprint():
    """The building download writes a relation's rings into one polygon; a larger 'hole' made the area negative."""
    from districtheatingsim.geocoding.building_csv import footprint_m2

    small, large = _square(5, 5, 2)[0], _square(0, 0, 20)[0]
    geometry = {"type": "MultiPolygon", "coordinates": [[small, large]]}
    assert footprint_m2(geometry) > 0


def test_shared_addresses_are_reported(tmp_path):
    from districtheatingsim.geocoding.building_csv import format_building_csv_summary

    front_and_back = {"building": "yes", "addr:street": "Markt", "addr:housenumber": "1"}
    summary, rows = _convert(
        tmp_path,
        [
            (front_and_back, 10),
            (front_and_back, 10),
            ({"building": "yes", "addr:street": "Markt", "addr:housenumber": "2"}, 10),
        ],
        _CountingGeocoder(),
    )
    assert len(rows) == 3 and summary["shared_addresses"] == 2
    assert "2 Gebäude teilen sich ihre Adresse" in format_building_csv_summary(summary)
