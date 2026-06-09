"""
Unit tests for the GUI-free OSM area-selection helpers
(``districtheatingsim.osm.area_selection``).

These pin the area→polygon resolution extracted from the two OSM download dialogs:
the highway-filter string, CSV→buffered-polygon, GeoJSON→polygon, and the
dispatch in ``resolve_area_polygon`` (including the ValueError that replaces the
old QMessageBox-in-a-thread on a malformed CSV).

Deterministic, no network: tiny CSV / GeoJSON fixtures are written to ``tmp_path``.
"""

import json

import pytest

from districtheatingsim.osm import area_selection as area


class TestBuildHighwayFilter:
    def test_selected_types(self):
        out = area.build_highway_filter(["primary", "residential"])
        assert out == '["highway"~"primary|residential"]'

    def test_single_type(self):
        assert area.build_highway_filter(["service"]) == '["highway"~"service"]'

    def test_empty_falls_back_to_unrestricted(self):
        assert area.build_highway_filter([]) == '["highway"]'


def _write_buildings_csv(path, *, with_utm=True):
    # Two points in EPSG:25833 (UTM 33N) near Zittau, Germany.
    if with_utm:
        path.write_text(
            "UTM_X;UTM_Y\n"
            "486000;5640000\n"
            "486100;5640100\n",
            encoding="utf-8",
        )
    else:
        path.write_text("X;Y\n486000;5640000\n", encoding="utf-8")
    return str(path)


def _write_geojson_polygon(path, crs_epsg=4326):
    # A small square. For WGS84 use lon/lat degrees; otherwise use metric coords.
    if crs_epsg == 4326:
        coords = [[14.80, 50.89], [14.81, 50.89], [14.81, 50.90], [14.80, 50.90], [14.80, 50.89]]
    else:
        coords = [[486000, 5640000], [486200, 5640000], [486200, 5640200],
                  [486000, 5640200], [486000, 5640000]]
    fc = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": f"urn:ogc:def:crs:EPSG::{crs_epsg}"}},
        "features": [{
            "type": "Feature",
            "properties": {},
            "geometry": {"type": "Polygon", "coordinates": [coords]},
        }],
    }
    path.write_text(json.dumps(fc), encoding="utf-8")
    return str(path)


class TestPolygonFromCsv:
    def test_returns_wgs84_polygon_with_area(self, tmp_path):
        csv = _write_buildings_csv(tmp_path / "buildings.csv")
        poly = area.polygon_from_csv(csv, "EPSG:25833", buffer_m=50.0)
        assert poly.area > 0
        minx, miny, maxx, maxy = poly.bounds
        # Bounds should be lon/lat degrees (WGS84), roughly around Zittau.
        assert 14 < minx < 15 and 50 < miny < 51

    def test_larger_buffer_grows_polygon(self, tmp_path):
        csv = _write_buildings_csv(tmp_path / "buildings.csv")
        small = area.polygon_from_csv(csv, "EPSG:25833", buffer_m=10.0)
        large = area.polygon_from_csv(csv, "EPSG:25833", buffer_m=200.0)
        assert large.area > small.area

    def test_missing_utm_columns_raises(self, tmp_path):
        csv = _write_buildings_csv(tmp_path / "bad.csv", with_utm=False)
        with pytest.raises(ValueError, match="UTM_X"):
            area.polygon_from_csv(csv, "EPSG:25833", buffer_m=50.0)


class TestPolygonFromGeojson:
    def test_wgs84_input(self, tmp_path):
        gj = _write_geojson_polygon(tmp_path / "poly.geojson", crs_epsg=4326)
        poly = area.polygon_from_geojson(gj)
        assert poly.area > 0
        minx, miny, maxx, maxy = poly.bounds
        assert 14 < minx < 15 and 50 < miny < 51

    def test_non_wgs84_is_reprojected(self, tmp_path):
        gj = _write_geojson_polygon(tmp_path / "poly25833.geojson", crs_epsg=25833)
        poly = area.polygon_from_geojson(gj)
        # After reprojection to WGS84 the bounds must be in degrees, not metres.
        minx, miny, maxx, maxy = poly.bounds
        assert 14 < minx < 15 and 50 < miny < 51


class TestResolveAreaPolygon:
    def test_csv_dispatch(self, tmp_path):
        csv = _write_buildings_csv(tmp_path / "b.csv")
        params = {"area_type": area.AREA_CSV, "csv_file": csv, "project_crs": "EPSG:25833"}
        poly = area.resolve_area_polygon(params, buffer_m=5.0)
        assert poly.area > 0

    def test_geojson_dispatch(self, tmp_path):
        gj = _write_geojson_polygon(tmp_path / "p.geojson")
        params = {"area_type": area.AREA_GEOJSON, "polygon_file": gj}
        assert area.resolve_area_polygon(params, buffer_m=5.0).area > 0

    def test_drawn_dispatch(self, tmp_path):
        gj = _write_geojson_polygon(tmp_path / "drawn.geojson")
        params = {"area_type": area.AREA_DRAWN, "drawn_polygon_file": gj}
        assert area.resolve_area_polygon(params, buffer_m=5.0).area > 0

    def test_city_type_has_no_polygon(self):
        params = {"area_type": area.AREA_CITY}
        with pytest.raises(ValueError):
            area.resolve_area_polygon(params, buffer_m=5.0)

    def test_unknown_type_raises(self):
        params = {"area_type": "Quatsch"}
        with pytest.raises(ValueError):
            area.resolve_area_polygon(params, buffer_m=5.0)
