"""
Tests for the flow-centric network rebuild (AP1).

``rebuild_network_from_flow`` regenerates the return network and the consumer/producer
VL↔RL bridges from the (edited) flow layer, so the flow is the single editable source of
truth and the four saved layers stay consistent by construction. Connectivity of the
result is asserted via the C31 checker.
"""

import json
from pathlib import Path

import pytest

from districtheatingsim.net_generation.flow_network_rebuild import rebuild_network_from_flow
from districtheatingsim.net_generation.network_connectivity import check_geojson_connectivity


def _line(ftype, coords, props=None):
    p = {"feature_type": ftype}
    if props:
        p.update(props)
    return {
        "type": "Feature",
        "properties": p,
        "geometry": {"type": "LineString", "coordinates": [list(c) for c in coords]},
    }


def _network(flow_segments, building_vl, generator_vl):
    """A minimal unified network: a flow path plus one HAST and one generator bridge.

    The bridges' RL endpoints are deliberately *wrong* (south) so the test proves the
    rebuild recomputes them onto the (north) return network.
    """
    feats = [_line("network_line_flow", seg) for seg in flow_segments]
    feats.append(
        _line(
            "building_connection", [building_vl, (building_vl[0], building_vl[1] - 9.0)], {"building_data": {"id": 7}}
        )
    )
    feats.append(_line("generator_connection", [generator_vl, (generator_vl[0], generator_vl[1] - 9.0)]))
    return {"type": "FeatureCollection", "metadata": {"version": "2.0"}, "features": feats}


class TestRebuildNetworkFromFlow:
    def test_return_regenerated_and_network_connected(self):
        gj = _network([[(0, 0), (10, 0)], [(10, 0), (20, 0)]], building_vl=(20, 0), generator_vl=(0, 0))
        out = rebuild_network_from_flow(gj)

        types = [f["properties"]["feature_type"] for f in out["features"]]
        assert types.count("network_line_flow") == 2
        assert types.count("network_line_return") == 2  # one return per flow segment

        # The whole loop is connected (flow, return, HAST bridge, generator bridge).
        assert check_geojson_connectivity(out).ok is True

    def test_bridge_rl_lands_on_return_junction(self):
        gj = _network([[(0, 0), (10, 0)], [(10, 0), (20, 0)]], building_vl=(20, 0), generator_vl=(0, 0))
        out = rebuild_network_from_flow(gj)

        hast = next(f for f in out["features"] if f["properties"]["feature_type"] == "building_connection")
        vl, rl = hast["geometry"]["coordinates"]
        assert (vl[0], vl[1]) == (20, 0)  # VL stays on the flow vertex
        # RL is the flow vertex offset north by 0.5 m (same vector as the return net).
        assert rl[0] == pytest.approx(20.0) and rl[1] == pytest.approx(0.5)

    def test_building_data_preserved(self):
        gj = _network([[(0, 0), (10, 0)], [(10, 0), (20, 0)]], building_vl=(20, 0), generator_vl=(0, 0))
        out = rebuild_network_from_flow(gj)
        hast = next(f for f in out["features"] if f["properties"]["feature_type"] == "building_connection")
        assert hast["properties"]["building_data"] == {"id": 7}  # only geometry recomputed

    def test_moved_flow_vertex_reattaches_bridge(self):
        # The building VL (20,0) is no longer a flow vertex after the edit; it must snap
        # to the nearest flow vertex (25,3) and still close the loop.
        gj = _network([[(0, 0), (10, 0)], [(10, 0), (25, 3)]], building_vl=(20, 0), generator_vl=(0, 0))
        out = rebuild_network_from_flow(gj)

        hast = next(f for f in out["features"] if f["properties"]["feature_type"] == "building_connection")
        vl = hast["geometry"]["coordinates"][0]
        assert (vl[0], vl[1]) == (25, 3)  # snapped to the moved flow vertex
        assert check_geojson_connectivity(out).ok is True

    def test_no_flow_returns_input_unchanged(self):
        gj = {"type": "FeatureCollection", "features": []}
        assert rebuild_network_from_flow(gj)["features"] == []

    def test_accepts_point_geometry_for_bridges(self):
        # The Leaflet map renders HAST/producers as circle points; rebuild must accept a
        # Point VL and still emit the canonical VL->RL bridge LineString.
        gj = {
            "type": "FeatureCollection",
            "features": [
                _line("network_line_flow", [(0, 0), (10, 0)]),
                _line("network_line_flow", [(10, 0), (20, 0)]),
                {
                    "type": "Feature",
                    "properties": {"feature_type": "building_connection", "building_data": {"id": 1}},
                    "geometry": {"type": "Point", "coordinates": [20, 0]},
                },
                {
                    "type": "Feature",
                    "properties": {"feature_type": "generator_connection"},
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                },
            ],
        }
        out = rebuild_network_from_flow(gj)
        hast = next(f for f in out["features"] if f["properties"]["feature_type"] == "building_connection")
        assert hast["geometry"]["type"] == "LineString"
        assert hast["properties"]["building_data"] == {"id": 1}
        assert check_geojson_connectivity(out).ok is True


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
def test_real_goerlitz_roundtrip_stays_connected():
    geojson = json.loads(_GOERLITZ.read_text(encoding="utf-8"))
    flow_before = sum(1 for f in geojson["features"] if f["properties"].get("feature_type") == "network_line_flow")

    out = rebuild_network_from_flow(geojson)

    rep = check_geojson_connectivity(out)
    assert rep.ok is True, rep.messages
    # One return per flow segment; flow untouched.
    n_flow = sum(1 for f in out["features"] if f["properties"]["feature_type"] == "network_line_flow")
    n_return = sum(1 for f in out["features"] if f["properties"]["feature_type"] == "network_line_return")
    assert n_flow == flow_before
    assert n_return == n_flow
