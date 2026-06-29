"""
Unit tests for the GUI-free network connectivity analysis.

``network_connectivity`` reproduces the exact-endpoint-match topology that
pandapipes generation builds, so a network split by the Leaflet editor (a moved
vertex that no longer coincides with its neighbour) is caught *before* generation
instead of surfacing as an opaque pandapipes connectivity error. See the user
report behind this module.
"""

from pathlib import Path

import pytest

from districtheatingsim.net_generation.network_connectivity import (
    check_geojson_connectivity,
    check_network_connectivity,
    feature_groups_from_geojson,
    snap_geojson_endpoints,
    snap_network_endpoints,
)

# A minimal but complete loop:
#   flow chain  A-B-C at y=0, return chain a-b-c at y=2,
#   generator bridges A<->a (left), HAST bridges C<->c (right).
_A, _B, _C = (0.0, 0.0), (10.0, 0.0), (20.0, 0.0)
_a, _b, _c = (0.0, 2.0), (10.0, 2.0), (20.0, 2.0)


def _healthy():
    return dict(
        flow_lines=[[_A, _B], [_B, _C]],
        return_lines=[[_a, _b], [_b, _c]],
        building_connections=[[_C, _c]],  # HAST bridges flow C <-> return c
        generator_connections=[[_A, _a]],  # generator bridges flow A <-> return a
    )


class TestHealthyNetwork:
    def test_fully_connected_is_ok(self):
        rep = check_network_connectivity(**_healthy())
        assert rep.ok is True
        assert rep.flow_components == 1
        assert rep.return_components == 1
        assert rep.floating_consumers == []
        assert rep.floating_generators == []
        assert rep.has_generator is True
        assert rep.near_miss_clusters == []


class TestDisconnections:
    def test_near_miss_splits_flow_network(self):
        # Second flow line starts 0.3 m off B -> separate junction -> flow splits.
        net = _healthy()
        net["flow_lines"] = [[_A, _B], [(10.0, 0.3), _C]]
        rep = check_network_connectivity(**net)
        assert rep.ok is False
        assert rep.flow_components == 2
        # The near-miss between (10,0) and (10,0.3) is surfaced as the cause.
        assert any({_B, (10.0, 0.3)} == set(cluster.members) for cluster in rep.near_miss_clusters)

    def test_floating_consumer_not_bridging(self):
        net = _healthy()
        # HAST left endpoint floats away from any flow node.
        net["building_connections"] = [[(99.0, 99.0), _c]]
        rep = check_network_connectivity(**net)
        assert rep.ok is False
        assert rep.floating_consumers == [0]

    def test_floating_generator_not_bridging(self):
        net = _healthy()
        net["generator_connections"] = [[(99.0, 99.0), _a]]
        rep = check_network_connectivity(**net)
        assert rep.ok is False
        assert rep.floating_generators == [0]

    def test_missing_generator(self):
        net = _healthy()
        net["generator_connections"] = []
        rep = check_network_connectivity(**net)
        assert rep.ok is False
        assert rep.has_generator is False
        assert any("Erzeugerstandort" in m for m in rep.messages)

    def test_return_network_split(self):
        net = _healthy()
        net["return_lines"] = [[_a, _b], [(10.0, 2.4), _c]]
        rep = check_network_connectivity(**net)
        assert rep.return_components == 2
        assert rep.ok is False


class TestSnap:
    def test_snap_repairs_near_miss_and_recheck_ok(self):
        net = _healthy()
        net["flow_lines"] = [[_A, _B], [(10.0, 0.3), _C]]
        assert check_network_connectivity(**net).ok is False

        flow, ret, bld, gen, n = snap_network_endpoints(**net)
        assert n == 1  # one endpoint moved (10,0.3) -> (10,0)
        rep = check_network_connectivity(
            flow_lines=flow, return_lines=ret, building_connections=bld, generator_connections=gen
        )
        assert rep.ok is True
        assert rep.flow_components == 1

    def test_snap_is_noop_on_healthy_network(self):
        _flow, _ret, _bld, _gen, n = snap_network_endpoints(**_healthy())
        assert n == 0

    def test_snap_preserves_intermediate_vertices_and_z(self):
        # A 3-vertex flow line with a z-coordinate on the endpoint.
        net = _healthy()
        net["flow_lines"] = [[(0.0, 0.0, 5.0), (5.0, 0.0), _B], [(10.0, 0.3), _C]]
        flow, *_ = snap_network_endpoints(**net)
        # Intermediate vertex kept; snapped endpoint keeps its z.
        assert flow[1][0] == (10.0, 0.0)  # (10,0.3) snapped onto (10,0)
        assert flow[0][1] == (5.0, 0.0)  # middle vertex untouched
        assert flow[0][0] == (0.0, 0.0, 5.0)  # z preserved on the unchanged endpoint


def _line_feature(ftype, coords):
    return {
        "type": "Feature",
        "properties": {"feature_type": ftype},
        "geometry": {"type": "LineString", "coordinates": [list(c) for c in coords]},
    }


def _healthy_geojson(flow2_start=_B):
    """Unified-schema GeoJSON dict for the healthy loop; flow2_start lets a test offset it."""
    return {
        "type": "FeatureCollection",
        "features": [
            _line_feature("network_line_flow", [_A, _B]),
            _line_feature("network_line_flow", [flow2_start, _C]),
            _line_feature("network_line_return", [_a, _b]),
            _line_feature("network_line_return", [_b, _c]),
            _line_feature("building_connection", [_C, _c]),
            _line_feature("generator_connection", [_A, _a]),
            # An unrelated point feature must be ignored, not crash the extractor.
            {
                "type": "Feature",
                "properties": {"feature_type": "other"},
                "geometry": {"type": "Point", "coordinates": [1, 2]},
            },
        ],
    }


class TestGeoJSONAdapters:
    def test_feature_groups_extraction_ignores_non_lines(self):
        flow, ret, bld, gen = feature_groups_from_geojson(_healthy_geojson())
        assert len(flow) == 2 and len(ret) == 2 and len(bld) == 1 and len(gen) == 1
        assert flow[0] == [_A, _B]

    def test_check_geojson_healthy_is_ok(self):
        assert check_geojson_connectivity(_healthy_geojson()).ok is True

    def test_check_geojson_detects_split(self):
        rep = check_geojson_connectivity(_healthy_geojson(flow2_start=(10.0, 0.3)))
        assert rep.ok is False
        assert rep.flow_components == 2

    def test_snap_geojson_repairs_and_preserves_structure(self):
        gj = _healthy_geojson(flow2_start=(10.0, 0.3))
        snapped, n = snap_geojson_endpoints(gj)
        assert n == 1
        # Original untouched (deep copy), snapped version reconnects.
        assert check_geojson_connectivity(gj).ok is False
        assert check_geojson_connectivity(snapped).ok is True
        # Properties + feature count preserved.
        assert len(snapped["features"]) == len(gj["features"])
        assert snapped["features"][0]["properties"]["feature_type"] == "network_line_flow"


_GOERLITZ = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "districtheatingsim"
    / "project_data"
    / "Görlitz"
    / "Variante 1"
    / "Wärmenetz"
    / "Wärmenetz.geojson"
)


@pytest.mark.skipif(not _GOERLITZ.exists(), reason="Görlitz network geojson not present")
def test_real_goerlitz_network_is_connected():
    import json

    geojson = json.loads(_GOERLITZ.read_text(encoding="utf-8"))
    rep = check_geojson_connectivity(geojson)
    assert rep.ok is True, rep.messages
    assert rep.flow_components == 1 and rep.return_components == 1
