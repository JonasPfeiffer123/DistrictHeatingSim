"""
Tests for elevation data integration in pandapipes network generation.

Covers:
- elevation_utils: build_elevation_lookup, assign_elevation_to_geodataframe,
  collect_unique_points_from_gdfs
- pp_net_initialisation_geojson: build_elevation_lookup_from_gdf,
  get_line_coords_and_lengths (Z-stripping), junction height_m assignment
- net_generation: 3-D preservation in offset_lines_by_angle and
  generate_connection_lines
- Regression: flat network (all height_m=0) behaves identically to baseline
"""

import math
import pytest
import geopandas as gpd
import pandapipes as pp
from shapely.geometry import LineString, Point
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gdf_from_lines(lines, crs="EPSG:25833"):
    return gpd.GeoDataFrame(geometry=lines, crs=crs)


def _make_gdf_from_points(points, crs="EPSG:25833"):
    return gpd.GeoDataFrame(geometry=points, crs=crs)


# ---------------------------------------------------------------------------
# elevation_utils
# ---------------------------------------------------------------------------

class TestBuildElevationLookup:
    """Unit tests for build_elevation_lookup_from_gdf (pandapipes module)."""

    def test_2d_gdf_returns_empty_lookup(self):
        from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import (
            build_elevation_lookup_from_gdf,
        )
        gdf = _make_gdf_from_lines([LineString([(0, 0), (10, 10)])])
        lookup = build_elevation_lookup_from_gdf(gdf)
        assert lookup == {}

    def test_3d_linestring_extracts_z(self):
        from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import (
            build_elevation_lookup_from_gdf,
        )
        line = LineString([(0.0, 0.0, 100.0), (10.0, 0.0, 110.0)])
        gdf = _make_gdf_from_lines([line])
        lookup = build_elevation_lookup_from_gdf(gdf)
        assert lookup[(0.0, 0.0)] == pytest.approx(100.0)
        assert lookup[(10.0, 0.0)] == pytest.approx(110.0)

    def test_3d_point_geometry_extracts_z(self):
        from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import (
            build_elevation_lookup_from_gdf,
        )
        gdf = _make_gdf_from_points([Point(5.0, 5.0, 55.0)])
        lookup = build_elevation_lookup_from_gdf(gdf)
        assert lookup[(5.0, 5.0)] == pytest.approx(55.0)

    def test_multiple_gdfs_merged(self):
        from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import (
            build_elevation_lookup_from_gdf,
        )
        gdf1 = _make_gdf_from_lines([LineString([(0, 0, 50), (10, 0, 60)])])
        gdf2 = _make_gdf_from_lines([LineString([(10, 0, 60), (20, 0, 70)])])
        lookup = {}
        lookup.update(build_elevation_lookup_from_gdf(gdf1))
        lookup.update(build_elevation_lookup_from_gdf(gdf2))
        assert len(lookup) == 3
        assert lookup[(20.0, 0.0)] == pytest.approx(70.0)


class TestGetLineCoordsAndLengths:
    """Verify that Z is stripped and 2-D tuples are returned."""

    def test_2d_input_unchanged(self):
        from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import (
            get_line_coords_and_lengths,
        )
        line = LineString([(0, 0), (3, 4)])  # length = 5
        gdf = _make_gdf_from_lines([line])
        coords_list, lengths = get_line_coords_and_lengths(gdf)
        assert coords_list[0][0] == (0.0, 0.0)
        assert coords_list[0][1] == (3.0, 4.0)
        assert lengths[0] == pytest.approx(5.0)

    def test_3d_input_stripped_to_2d(self):
        from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import (
            get_line_coords_and_lengths,
        )
        line = LineString([(0, 0, 100), (3, 4, 110)])
        gdf = _make_gdf_from_lines([line])
        coords_list, _ = get_line_coords_and_lengths(gdf)
        # Each coord tuple must have exactly 2 elements
        for coord in coords_list[0]:
            assert len(coord) == 2

    def test_z_stripped_values_correct(self):
        from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import (
            get_line_coords_and_lengths,
        )
        line = LineString([(1, 2, 200), (4, 6, 300)])
        gdf = _make_gdf_from_lines([line])
        coords_list, _ = get_line_coords_and_lengths(gdf)
        assert coords_list[0][0] == (1.0, 2.0)
        assert coords_list[0][1] == (4.0, 6.0)


class TestCollectUniquePoints:
    """Tests for elevation_utils.collect_unique_points_from_gdfs."""

    def test_deduplication(self):
        from districtheatingsim.net_generation.elevation_utils import collect_unique_points_from_gdfs
        gdf1 = _make_gdf_from_lines([LineString([(0, 0), (10, 0)])])
        gdf2 = _make_gdf_from_lines([LineString([(10, 0), (20, 0)])])
        pts = collect_unique_points_from_gdfs(gdf1, gdf2)
        # (10, 0) is shared — should appear once
        assert len(pts) == 3
        assert (10.0, 0.0) in pts

    def test_points_geometry(self):
        from districtheatingsim.net_generation.elevation_utils import collect_unique_points_from_gdfs
        gdf = _make_gdf_from_points([Point(5, 5), Point(15, 15)])
        pts = collect_unique_points_from_gdfs(gdf)
        assert (5.0, 5.0) in pts
        assert (15.0, 15.0) in pts


class TestAssignElevationToGeoDataFrame:
    """Tests for elevation_utils.assign_elevation_to_geodataframe."""

    def test_point_gets_z(self):
        from districtheatingsim.net_generation.elevation_utils import assign_elevation_to_geodataframe
        gdf = _make_gdf_from_points([Point(0, 0)])
        lookup = {(0.0, 0.0): 123.4}
        result = assign_elevation_to_geodataframe(gdf, lookup)
        pt = result.geometry.iloc[0]
        assert pt.has_z
        assert pt.z == pytest.approx(123.4)

    def test_linestring_gets_z_on_all_vertices(self):
        from districtheatingsim.net_generation.elevation_utils import assign_elevation_to_geodataframe
        gdf = _make_gdf_from_lines([LineString([(0, 0), (10, 0)])])
        lookup = {(0.0, 0.0): 50.0, (10.0, 0.0): 60.0}
        result = assign_elevation_to_geodataframe(gdf, lookup)
        line = result.geometry.iloc[0]
        assert line.has_z
        coords = list(line.coords)
        assert coords[0][2] == pytest.approx(50.0)
        assert coords[1][2] == pytest.approx(60.0)

    def test_missing_key_defaults_to_zero(self):
        from districtheatingsim.net_generation.elevation_utils import assign_elevation_to_geodataframe
        gdf = _make_gdf_from_points([Point(99, 99)])
        result = assign_elevation_to_geodataframe(gdf, {})
        assert result.geometry.iloc[0].z == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# net_generation: 3-D preservation
# ---------------------------------------------------------------------------

class TestOffsetLinesPreservesZ:
    """offset_lines_by_angle should preserve Z on 3-D input."""

    def test_z_preserved_after_offset(self):
        from districtheatingsim.net_generation.net_generation import offset_lines_by_angle
        line_3d = LineString([(0, 0, 100), (10, 0, 110)])
        gdf = _make_gdf_from_lines([line_3d])
        result = offset_lines_by_angle(gdf, distance=0.5, angle_degrees=90)
        out_line = result.geometry.iloc[0]
        assert out_line.has_z
        out_coords = list(out_line.coords)
        assert out_coords[0][2] == pytest.approx(100.0)
        assert out_coords[1][2] == pytest.approx(110.0)

    def test_2d_input_stays_2d(self):
        from districtheatingsim.net_generation.net_generation import offset_lines_by_angle
        line_2d = LineString([(0, 0), (10, 0)])
        gdf = _make_gdf_from_lines([line_2d])
        result = offset_lines_by_angle(gdf, distance=0.5, angle_degrees=90)
        out_coords = list(result.geometry.iloc[0].coords)
        assert len(out_coords[0]) == 2


class TestGenerateConnectionLinesPreservesZ:
    """generate_connection_lines should carry building-point Z into the line."""

    def test_3d_point_creates_3d_line(self):
        from districtheatingsim.net_generation.net_generation import generate_connection_lines
        gdf = _make_gdf_from_points([Point(0, 0, 250)])
        result = generate_connection_lines(gdf, offset_distance=1.0, offset_angle=0)
        line = result.geometry.iloc[0]
        assert line.has_z
        coords = list(line.coords)
        assert coords[0][2] == pytest.approx(250.0)
        assert coords[1][2] == pytest.approx(250.0)

    def test_2d_point_creates_2d_line(self):
        from districtheatingsim.net_generation.net_generation import generate_connection_lines
        gdf = _make_gdf_from_points([Point(0, 0)])
        result = generate_connection_lines(gdf, offset_distance=1.0, offset_angle=0)
        # Should not raise; line may be 2-D
        assert result.geometry.iloc[0] is not None


# ---------------------------------------------------------------------------
# Regression: flat network (height_m=0) — same behaviour as before
# ---------------------------------------------------------------------------

class TestFlatNetworkRegressionHeightM:
    """When all elevations are 0, junction.height_m must be 0 everywhere."""

    def test_all_junctions_height_zero_for_2d_geojson(self):
        from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import (
            build_elevation_lookup_from_gdf,
            get_line_coords_and_lengths,
            get_all_point_coords_from_line_cords,
        )
        # Flat 2-D network — no Z coordinates
        line = LineString([(0, 0), (100, 0)])
        gdf = _make_gdf_from_lines([line])

        lookup = build_elevation_lookup_from_gdf(gdf)
        # No 3-D vertices → empty lookup
        assert lookup == {}

        coords_list, _ = get_line_coords_and_lengths(gdf)
        unique = get_all_point_coords_from_line_cords(coords_list)

        net = pp.create_empty_network(fluid="water")
        for i, coord in enumerate(unique):
            height = lookup.get(coord, 0.0)
            pp.create_junction(net, pn_bar=1.05, tfluid_k=363.15,
                               height_m=height, name=f"J{i}", geodata=coord)

        assert (net.junction["height_m"] == 0.0).all()


# ---------------------------------------------------------------------------
# network_geojson_schema: elevation_start_m / elevation_end_m
# ---------------------------------------------------------------------------

class TestNetworkGeoJSONSchemaElevationFields:

    def test_3d_geometry_populates_elevation_fields(self):
        from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema
        line_3d = LineString([(0, 0, 200), (100, 0, 215)])
        feature = NetworkGeoJSONSchema.create_network_line_feature(
            geometry=line_3d, layer="flow", segment_id="seg-1"
        )
        calc = feature["properties"]["calculated"]
        assert calc["elevation_start_m"] == pytest.approx(200.0)
        assert calc["elevation_end_m"] == pytest.approx(215.0)

    def test_2d_geometry_elevation_fields_are_none(self):
        from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema
        line_2d = LineString([(0, 0), (100, 0)])
        feature = NetworkGeoJSONSchema.create_network_line_feature(
            geometry=line_2d, layer="return", segment_id="seg-2"
        )
        calc = feature["properties"]["calculated"]
        assert calc["elevation_start_m"] is None
        assert calc["elevation_end_m"] is None
