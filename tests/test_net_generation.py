"""
Tests for the return-network offset in net_generation (BACKLOG C3).

``offset_lines_by_angle`` builds the return network from the supply lines. The old
implementation translated every vertex by one fixed vector, so segments running
parallel to that direction ended up collinear with (lying on top of) the supply line.
It now offsets each vertex perpendicular to its local direction, which separates
segments of every orientation while keeping the network connected (a shared vertex
maps to a single return coordinate — the junction model keys on exact coordinates).
"""

import logging

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point

from districtheatingsim.net_generation.net_generation import create_perpendicular_line, offset_lines_by_angle
from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema


class TestReturnNetworkOffset:
    def test_isolated_segment_offset_is_perpendicular(self):
        # An east-west segment with the historical angle=0 (east) reference. The old
        # rigid east-translation left it collinear (distance 0); the perpendicular
        # offset separates it by `distance` to the north.
        flow = gpd.GeoDataFrame(geometry=[LineString([(0, 0), (10, 0)])], crs="EPSG:25833")
        ret = offset_lines_by_angle(flow, distance=1.0, angle_degrees=0)

        assert flow.geometry.iloc[0].distance(ret.geometry.iloc[0]) == pytest.approx(1.0, abs=1e-9)
        # Offset is perpendicular (north), not along the line.
        assert [(round(x, 6), round(y, 6)) for x, y in ret.geometry.iloc[0].coords] == [
            (0.0, 1.0),
            (10.0, 1.0),
        ]

    def test_shared_junction_stays_connected(self):
        # Three segments meeting at (10, 0) — incl. an east-west one — form a degree-3
        # junction. The return network must keep them connected at a single junction.
        flow = gpd.GeoDataFrame(
            geometry=[
                LineString([(0, 0), (10, 0)]),  # east-west
                LineString([(10, 0), (10, 10)]),  # north-south
                LineString([(10, 0), (20, 5)]),  # diagonal
            ],
            crs="EPSG:25833",
        )
        ret = offset_lines_by_angle(flow, distance=1.0, angle_degrees=0)

        # No junction split: the return network has exactly as many distinct vertices.
        flow_vertices = {c for line in flow.geometry for c in line.coords}
        ret_vertices = {c for line in ret.geometry for c in line.coords}
        assert len(ret_vertices) == len(flow_vertices)

        # All three return lines meet at one shared return junction (the offset of (10, 0)).
        junction_ends = {
            ret.geometry.iloc[0].coords[-1],  # line 0 ends at (10, 0)
            ret.geometry.iloc[1].coords[0],  # line 1 starts at (10, 0)
            ret.geometry.iloc[2].coords[0],  # line 2 starts at (10, 0)
        }
        assert len(junction_ends) == 1

    def test_no_supply_return_overlap_any_orientation(self):
        # No supply line overlaps/crosses its return line — distance > 0 everywhere.
        # The regression: the old rigid east-offset left east-west segments collinear
        # (distance exactly 0). (At a multi-orientation junction the return naturally
        # converges toward the supply, so only a clean gap — not the full distance — is
        # guaranteed there.)
        flow = gpd.GeoDataFrame(
            geometry=[
                LineString([(0, 0), (10, 0)]),
                LineString([(10, 0), (10, 10)]),
                LineString([(10, 0), (20, 5)]),
            ],
            crs="EPSG:25833",
        )
        ret = offset_lines_by_angle(flow, distance=1.0, angle_degrees=0)
        for fl, rl in zip(flow.geometry, ret.geometry, strict=False):
            assert fl.distance(rl) > 0.0

    def test_z_coordinate_preserved(self):
        flow = gpd.GeoDataFrame(geometry=[LineString([(0, 0, 100.0), (10, 0, 105.0)])], crs="EPSG:25833")
        ret = offset_lines_by_angle(flow, distance=1.0, angle_degrees=0)
        zs = [c[2] for c in ret.geometry.iloc[0].coords]
        assert zs == [100.0, 105.0]


class TestNetworkGeoJSONVersion:
    """D4 step 3: the network GeoJSON carries a schema version in metadata.version
    (a semver string, its own convention); import_from_file validates it softly."""

    def test_current_version_passes_quietly(self, caplog):
        gj = {"type": "FeatureCollection", "features": [], "metadata": {"version": NetworkGeoJSONSchema.VERSION}}
        with caplog.at_level(logging.WARNING):
            found = NetworkGeoJSONSchema.validate_version(gj)
        assert found == NetworkGeoJSONSchema.VERSION
        assert caplog.records == []

    def test_missing_version_warns(self, caplog):
        with caplog.at_level(logging.WARNING):
            found = NetworkGeoJSONSchema.validate_version({"type": "FeatureCollection"})
        assert found is None
        assert any("no schema version" in r.getMessage() for r in caplog.records)

    def test_newer_major_version_warns(self, caplog):
        gj = {"metadata": {"version": "99.0"}}
        with caplog.at_level(logging.WARNING):
            found = NetworkGeoJSONSchema.validate_version(gj)
        assert found == "99.0"
        assert any("newer than this app" in r.getMessage() for r in caplog.records)

    def test_import_from_file_roundtrips_and_validates(self, tmp_path, caplog):
        gj = {"type": "FeatureCollection", "features": [], "metadata": NetworkGeoJSONSchema.create_metadata()}
        path = str(tmp_path / "net.geojson")
        NetworkGeoJSONSchema.export_to_file(gj, path)
        with caplog.at_level(logging.WARNING):
            loaded = NetworkGeoJSONSchema.import_from_file(path)
        assert loaded["metadata"]["version"] == NetworkGeoJSONSchema.VERSION
        assert caplog.records == []


class TestCreatePerpendicularLine:
    """Building→street connection must not crash when the point is 3-D (elevation) but the
    street is 2-D — combining mixed dimensions raised 'inhomogeneous shape' (the MST bug)."""

    _STREET = LineString([(0.0, 49.0), (20.0, 51.0)])

    def test_3d_building_point_on_2d_street(self):
        conn = create_perpendicular_line(Point(10.0, 50.0, 123.0), self._STREET)
        assert conn.geom_type == "LineString"
        assert not conn.has_z  # built in 2-D; elevation assigned to all vertices later
        assert tuple(conn.coords[0]) == (10.0, 50.0)

    def test_2d_building_point_on_2d_street(self):
        conn = create_perpendicular_line(Point(10.0, 50.0), self._STREET)
        assert conn.geom_type == "LineString"
        assert not conn.has_z
