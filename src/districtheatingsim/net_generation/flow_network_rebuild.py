"""
Flow-centric network rebuild (AP1): derive return + connections from the edited flow.

The district-heating network is *generated* as four layers (Vorlauf/flow,
Rücklauf/return, HAST/building connections, Erzeuger/generator connections), but the
return network and the VL↔RL connection bridges are pure geometric derivations of the
flow line network plus the (fixed) building/producer points:

* the return network is the flow offset perpendicular by a fixed distance
  (``offset_lines_by_angle`` / ``build_offset_map``), and
* each consumer/producer bridge runs from a flow vertex to that same vertex offset by
  the **same** per-vertex vector (so it lands exactly on a return junction).

So the flow is the single editable source of truth. After the Leaflet editor changes
only the flow, :func:`rebuild_network_from_flow` regenerates the return lines and
re-attaches the connection bridges (snapping each to the nearest flow vertex),
preserving the protected building/generator *data* — only geometry is recomputed. This
keeps the four saved layers consistent by construction and avoids the disconnected
networks that manual four-layer editing produced.

GUI-free (geopandas/shapely only); the Leaflet save path calls this before writing.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import geopandas as gpd
from shapely.geometry import LineString, Point

from districtheatingsim.net_generation.net_generation import build_offset_map, offset_lines_by_angle
from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema

# Default return/connection offset — must match generate_and_export_layers (0.5 m, 0°).
DEFAULT_OFFSET_DISTANCE = 0.5
DEFAULT_OFFSET_ANGLE = 0.0
# Tolerance for treating a foreign endpoint as lying *on* a segment (metres, EPSG:25833).
DEFAULT_NODE_TOLERANCE = 0.5


def _feature_type(feature: dict):
    return (feature.get("properties") or {}).get("feature_type")


def node_flow_lines(lines, tolerance: float = DEFAULT_NODE_TOLERANCE):
    """
    Split the flow network into 2-point segments noded at every touch/kink (AP2).

    pandapipes wires each line as ``coords[0] → coords[1]`` and forms junctions only at
    *exact* endpoints, so (a) a multi-vertex line (a kink added by the editor) would wire
    only its first segment, and (b) a line whose endpoint lands mid-way along another line
    would not connect there. This explodes every line into consecutive 2-point segments
    and additionally splits each segment at any *other* segment's endpoint lying on its
    interior (within ``tolerance``), so a junction forms at every kink and touch point.

    Works in 2-D (the Leaflet editor produces 2-D coordinates).

    :param lines: Flow ``LineString`` geometries.
    :param tolerance: Max distance for a foreign endpoint to count as on a segment [m].
    :return: A list of 2-point ``LineString`` segments.
    :rtype: list[LineString]
    """
    # 1) Explode to 2-point segments (this alone fixes multi-vertex "kink" lines).
    segments = []
    for line in lines:
        coords = [(c[0], c[1]) for c in line.coords]
        for a, b in zip(coords[:-1], coords[1:], strict=False):
            if a != b:
                segments.append((a, b))

    # 2) Every segment endpoint is a candidate junction.
    points = set()
    for a, b in segments:
        points.add(a)
        points.add(b)

    # 3) Split each segment at foreign endpoints lying strictly on its interior.
    result = []
    for a, b in segments:
        seg = LineString([a, b])
        hits = []
        for p in points:
            if p == a or p == b:
                continue
            if seg.distance(Point(p)) <= tolerance:
                proj = seg.project(Point(p))
                if 0 < proj < seg.length:
                    hits.append((proj, p))
        if not hits:
            result.append(seg)
        else:
            hits.sort()
            chain = [a, *[p for _, p in hits], b]
            for x, y in zip(chain[:-1], chain[1:], strict=False):
                if x != y:
                    result.append(LineString([x, y]))
    return result


def rebuild_network_from_flow(
    geojson: dict,
    *,
    distance: float = DEFAULT_OFFSET_DISTANCE,
    angle: float = DEFAULT_OFFSET_ANGLE,
    node_tolerance: float = DEFAULT_NODE_TOLERANCE,
) -> dict:
    """
    Regenerate return lines + consumer/producer bridges from the (edited) flow layer.

    The flow is first noded into 2-point segments split at every kink/touch (AP2,
    :func:`node_flow_lines`); return features are regenerated as the noded flow's offset;
    each building/generator connection keeps its properties but its geometry is
    recomputed as ``[vl, vl + offset(vl)]`` where ``vl`` is snapped to the nearest flow
    vertex (so it stays attached and the bridge closes onto a return junction). Any
    non-network features and the top-level ``crs``/``metadata`` are preserved.

    :param geojson: A unified network GeoJSON dict (mutated and returned).
    :param distance: Return/connection offset distance [m].
    :param angle: Preferred-side reference angle [degrees].
    :return: The rebuilt GeoJSON dict.
    :rtype: dict
    """
    NetworkGeoJSONSchema.ensure_feature_types(geojson)  # tolerate older exports (C32)
    features = geojson.get("features", [])

    flow_feats = [f for f in features if _feature_type(f) == NetworkGeoJSONSchema.FEATURE_TYPE_FLOW]
    building_feats = [f for f in features if _feature_type(f) == NetworkGeoJSONSchema.FEATURE_TYPE_BUILDING]
    generator_feats = [f for f in features if _feature_type(f) == NetworkGeoJSONSchema.FEATURE_TYPE_GENERATOR]
    other_feats = [
        f
        for f in features
        if _feature_type(f)
        not in (
            NetworkGeoJSONSchema.FEATURE_TYPE_FLOW,
            NetworkGeoJSONSchema.FEATURE_TYPE_RETURN,
            NetworkGeoJSONSchema.FEATURE_TYPE_BUILDING,
            NetworkGeoJSONSchema.FEATURE_TYPE_GENERATOR,
        )
    ]

    if not flow_feats:
        return geojson  # nothing to derive from

    # Node the flow into 2-point segments split at every kink/touch (AP2), so pandapipes
    # forms a junction there; the return + bridges are then derived from the noded flow.
    flow_lines = [LineString(f["geometry"]["coordinates"]) for f in flow_feats]
    noded_flow = node_flow_lines(flow_lines, tolerance=node_tolerance)
    flow_gdf = gpd.GeoDataFrame(geometry=noded_flow)

    offset_map = build_offset_map(flow_gdf, distance, angle)
    return_gdf = offset_lines_by_angle(flow_gdf, distance, angle)

    vertices = list(offset_map.keys())

    def _snap(vl: tuple) -> tuple:
        """Snap a connection's VL point to the nearest flow vertex so it stays attached."""
        if vl in offset_map:
            return vl
        return min(vertices, key=lambda k: (k[0] - vl[0]) ** 2 + (k[1] - vl[1]) ** 2)

    def _rebuild_bridge(feature: dict) -> None:
        geometry = feature["geometry"]
        coords = geometry["coordinates"]
        # The VL point comes either from a bridge LineString (coords[0]) or, when the
        # Leaflet map renders HAST/producers as circle *points*, from the point itself.
        vl_raw = coords if geometry.get("type") == "Point" else coords[0]
        vl = _snap((vl_raw[0], vl_raw[1]))
        ox, oy = offset_map[vl]
        rl = (vl[0] + ox, vl[1] + oy)
        z = [vl_raw[2]] if len(vl_raw) > 2 else []  # preserve elevation if present
        # Always emit the canonical VL->RL bridge LineString.
        feature["geometry"] = {"type": "LineString", "coordinates": [[vl[0], vl[1], *z], [rl[0], rl[1], *z]]}

    for feature in building_feats:
        _rebuild_bridge(feature)
    for feature in generator_feats:
        _rebuild_bridge(feature)

    # Regenerate flow + return features from the noded flow (no protected data on either;
    # noding may split/merge segments, so the original flow features are not reused).
    new_flow_feats = [
        NetworkGeoJSONSchema.create_network_line_feature(geometry, "flow", f"flow_{i:03d}")
        for i, geometry in enumerate(noded_flow)
    ]
    new_return_feats = [
        NetworkGeoJSONSchema.create_network_line_feature(geometry, "return", f"return_{i:03d}")
        for i, geometry in enumerate(return_gdf.geometry)
    ]

    geojson["features"] = new_flow_feats + new_return_feats + building_feats + generator_feats + other_feats
    return geojson
