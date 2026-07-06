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
from shapely.geometry import LineString

from districtheatingsim.net_generation.net_generation import build_offset_map, offset_lines_by_angle
from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema

# Default return/connection offset — must match generate_and_export_layers (0.5 m, 0°).
DEFAULT_OFFSET_DISTANCE = 0.5
DEFAULT_OFFSET_ANGLE = 0.0


def _feature_type(feature: dict):
    return (feature.get("properties") or {}).get("feature_type")


def rebuild_network_from_flow(
    geojson: dict,
    *,
    distance: float = DEFAULT_OFFSET_DISTANCE,
    angle: float = DEFAULT_OFFSET_ANGLE,
) -> dict:
    """
    Regenerate return lines + consumer/producer bridges from the (edited) flow layer.

    Flow features are kept exactly as given; return features are regenerated as the flow
    offset; each building/generator connection keeps its properties but its geometry is
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

    flow_lines = [LineString(f["geometry"]["coordinates"]) for f in flow_feats]
    flow_gdf = gpd.GeoDataFrame(geometry=flow_lines)

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

    # Regenerate the return features from the offset flow (no protected data on returns).
    new_return_feats = [
        NetworkGeoJSONSchema.create_network_line_feature(geometry, "return", f"return_{i:03d}")
        for i, geometry in enumerate(return_gdf.geometry)
    ]

    geojson["features"] = flow_feats + new_return_feats + building_feats + generator_feats + other_feats
    return geojson
