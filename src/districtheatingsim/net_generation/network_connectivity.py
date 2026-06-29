"""
GUI-free connectivity analysis for the unified district-heating network.

The pandapipes generation merges line endpoints into junctions by **exact**
``(x, y)`` coordinate match (see ``pp_net_initialisation_geojson``: junction dicts
keyed by raw coordinate tuples). So after the Leaflet editor moves a vertex even a
fraction off its neighbour, the two endpoints become *separate* junctions and the
network silently splits — pandapipes then fails with a connectivity error at solve
time, far from the cause.

This module reproduces that exact-match topology *before* generation and reports:

* how many connected components the Vorlauf (flow) and Rücklauf (return) networks
  fall into (a healthy net has exactly one each),
* heat-substation (HAST) / generator connections that do not bridge a flow node to
  a return node (a "floating" consumer/producer that won't close the loop),
* **near-miss** endpoint clusters — points that nearly coincide but are not exactly
  equal, i.e. the usual root cause after editing — which :func:`snap_network_endpoints`
  can repair by collapsing each cluster onto a single shared coordinate.

It is deliberately PyQt- and geopandas-free (plain coordinate sequences) so it can
be unit-tested without a display; the Leaflet tab adapts its features to/from here.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import math
from collections import Counter
from dataclasses import dataclass, field

# Default snap / near-miss tolerance in CRS units (metres for the project's EPSG:25833).
# Endpoints closer than this that are not exactly equal are treated as "meant to be one
# junction" — small enough not to merge genuinely distinct nodes of a DH network.
DEFAULT_TOLERANCE_M = 0.5

Coord = tuple[float, float]


@dataclass
class NearMissCluster:
    """A group of endpoints that nearly coincide but are not exactly equal."""

    representative: Coord
    members: list[Coord]  # the distinct coordinates in the cluster (incl. representative)


@dataclass
class ConnectivityReport:
    """Result of :func:`check_network_connectivity`."""

    ok: bool
    flow_components: int
    return_components: int
    floating_consumers: list[int] = field(default_factory=list)  # indices into building_connections
    floating_generators: list[int] = field(default_factory=list)  # indices into generator_connections
    has_generator: bool = False
    near_miss_clusters: list[NearMissCluster] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Union-find
# ---------------------------------------------------------------------------


class _UnionFind:
    def __init__(self):
        self._parent: dict = {}

    def find(self, x):
        self._parent.setdefault(x, x)
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        # path compression
        while self._parent[x] != root:
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a, b):
        self._parent[self.find(a)] = self.find(b)

    def component_count(self, nodes) -> int:
        return len({self.find(n) for n in nodes})


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _xy(point) -> Coord:
    """Return the 2-D ``(x, y)`` of a coordinate (dropping any z)."""
    return (point[0], point[1])


def line_endpoints(line) -> tuple[Coord, Coord]:
    """Return the first and last 2-D vertex of a coordinate sequence."""
    return _xy(line[0]), _xy(line[-1])


def _component_count(lines) -> int:
    """Number of connected components formed by the endpoints of *lines*."""
    uf = _UnionFind()
    nodes = set()
    for line in lines:
        a, b = line_endpoints(line)
        uf.union(a, b)
        nodes.add(a)
        nodes.add(b)
    return uf.component_count(nodes) if nodes else 0


# ---------------------------------------------------------------------------
# Near-miss clustering
# ---------------------------------------------------------------------------


def _all_endpoints(flow_lines, return_lines, building_connections, generator_connections) -> list[Coord]:
    points: list[Coord] = []
    for group in (flow_lines, return_lines, building_connections, generator_connections):
        for line in group:
            a, b = line_endpoints(line)
            points.append(a)
            points.append(b)
    return points


def _cluster_near_points(points: list[Coord], tolerance: float) -> dict[Coord, Coord]:
    """
    Map every distinct point to a cluster representative.

    Points within *tolerance* of each other are unioned; the representative of a
    cluster is the coordinate that occurs most often (so off-by-epsilon outliers
    snap onto the existing shared junction), tie-broken deterministically.

    :return: ``{point: representative}`` for every distinct input point.
    """
    counts = Counter(points)
    distinct = list(counts)

    # Grid-bucket by tolerance so only nearby points are compared (3x3 neighbourhood).
    buckets: dict[tuple[int, int], list[Coord]] = {}
    cell = tolerance if tolerance > 0 else 1.0
    for p in distinct:
        buckets.setdefault((math.floor(p[0] / cell), math.floor(p[1] / cell)), []).append(p)

    uf = _UnionFind()
    for p in distinct:
        uf.find(p)
    tol_sq = tolerance * tolerance
    for (cx, cy), members in buckets.items():
        # candidate neighbours: this cell + the 8 surrounding cells
        neighbours: list[Coord] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbours.extend(buckets.get((cx + dx, cy + dy), ()))
        for p in members:
            for q in neighbours:
                if p is q:
                    continue
                if (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 <= tol_sq:
                    uf.union(p, q)

    # Pick a representative per cluster: most frequent coord, then smallest.
    clusters: dict[Coord, list[Coord]] = {}
    for p in distinct:
        clusters.setdefault(uf.find(p), []).append(p)

    mapping: dict[Coord, Coord] = {}
    for members in clusters.values():
        representative = max(members, key=lambda c: (counts[c], -c[0], -c[1]))
        for p in members:
            mapping[p] = representative
    return mapping


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_network_connectivity(
    flow_lines,
    return_lines,
    building_connections,
    generator_connections,
    *,
    tolerance: float = DEFAULT_TOLERANCE_M,
) -> ConnectivityReport:
    """
    Analyse the unified network's connectivity the way pandapipes will see it.

    Each argument is a list of coordinate sequences (``[(x, y), …]`` per feature);
    z-coordinates, if any, are ignored. Connectivity is evaluated with **exact**
    endpoint matching (mirroring generation); *tolerance* is used only to surface
    near-miss endpoint clusters that explain a split and that
    :func:`snap_network_endpoints` can repair.

    :return: A :class:`ConnectivityReport`.
    """
    flow_nodes = set()
    for line in flow_lines:
        flow_nodes.update(line_endpoints(line))
    return_nodes = set()
    for line in return_lines:
        return_nodes.update(line_endpoints(line))

    flow_components = _component_count(flow_lines)
    return_components = _component_count(return_lines)

    def _bridges(line) -> bool:
        a, b = line_endpoints(line)
        return (a in flow_nodes and b in return_nodes) or (b in flow_nodes and a in return_nodes)

    floating_consumers = [i for i, line in enumerate(building_connections) if not _bridges(line)]
    floating_generators = [i for i, line in enumerate(generator_connections) if not _bridges(line)]
    has_generator = len(generator_connections) > 0

    # Near-miss clusters: distinct-but-near endpoints that should likely be one junction.
    mapping = _cluster_near_points(
        _all_endpoints(flow_lines, return_lines, building_connections, generator_connections), tolerance
    )
    grouped: dict[Coord, set[Coord]] = {}
    for point, rep in mapping.items():
        grouped.setdefault(rep, set()).add(point)
    near_miss_clusters = [
        NearMissCluster(representative=rep, members=sorted(members))
        for rep, members in grouped.items()
        if len(members) > 1
    ]
    near_miss_clusters.sort(key=lambda c: c.representative)

    messages: list[str] = []
    if flow_components > 1:
        messages.append(f"Vorlaufnetz ist in {flow_components} getrennte Teile zerfallen (erwartet: 1).")
    if return_components > 1:
        messages.append(f"Rücklaufnetz ist in {return_components} getrennte Teile zerfallen (erwartet: 1).")
    if floating_consumers:
        messages.append(f"{len(floating_consumers)} Hausanschluss(e) sind nicht an Vor- und Rücklauf angebunden.")
    if floating_generators:
        messages.append(f"{len(floating_generators)} Erzeugeranschluss(e) sind nicht an Vor- und Rücklauf angebunden.")
    if not has_generator:
        messages.append("Kein Erzeugerstandort im Netz vorhanden.")
    if near_miss_clusters:
        messages.append(
            f"{len(near_miss_clusters)} fast-zusammenfallende Endpunkt-Gruppe(n) gefunden "
            f"(< {tolerance:g} m, aber nicht exakt gleich) — wahrscheinliche Ursache der Trennung."
        )

    ok = (
        flow_components == 1
        and return_components == 1
        and not floating_consumers
        and not floating_generators
        and has_generator
    )
    if ok and not messages:
        messages.append("Netz ist vollständig verbunden (Vorlauf, Rücklauf, HAST und Erzeuger).")

    return ConnectivityReport(
        ok=ok,
        flow_components=flow_components,
        return_components=return_components,
        floating_consumers=floating_consumers,
        floating_generators=floating_generators,
        has_generator=has_generator,
        near_miss_clusters=near_miss_clusters,
        messages=messages,
    )


def _snap_line(line, mapping: dict[Coord, Coord]):
    """Return *line* with its first/last vertex moved to the cluster representative.

    Intermediate vertices are left untouched; any z-coordinate on a snapped endpoint
    is preserved (only x/y are moved). Returns ``(new_line, n_changed)``.
    """
    new_line = [tuple(pt) for pt in line]
    changed = 0
    for idx in (0, -1):
        rep = mapping.get(_xy(new_line[idx]))
        if rep is not None and rep != _xy(new_line[idx]):
            new_line[idx] = (rep[0], rep[1], *tuple(new_line[idx][2:]))
            changed += 1
    return new_line, changed


def snap_network_endpoints(
    flow_lines,
    return_lines,
    building_connections,
    generator_connections,
    *,
    tolerance: float = DEFAULT_TOLERANCE_M,
):
    """
    Collapse near-coincident endpoints onto a shared coordinate to restore connectivity.

    Each near-miss cluster (endpoints within *tolerance*) is snapped onto its
    representative coordinate (the most common one — i.e. outliers move onto the
    existing junction). Only feature endpoints are moved; intermediate vertices and
    z-values are preserved.

    :return: ``(flow, return, building, generator, n_snapped)`` — the four feature
        groups with snapped endpoints and the number of endpoint coordinates changed.
    """
    mapping = _cluster_near_points(
        _all_endpoints(flow_lines, return_lines, building_connections, generator_connections), tolerance
    )

    total = 0
    snapped_groups = []
    for group in (flow_lines, return_lines, building_connections, generator_connections):
        new_group = []
        for line in group:
            new_line, changed = _snap_line(line, mapping)
            total += changed
            new_group.append(new_line)
        snapped_groups.append(new_group)

    return (*snapped_groups, total)


# ---------------------------------------------------------------------------
# Unified-GeoJSON adapters (operate on the plain dict — no geopandas needed)
# ---------------------------------------------------------------------------

# Map the unified-schema feature_type strings to our four groups. Kept as literals so
# this module stays import-light (no dependency on NetworkGeoJSONSchema).
_GEOJSON_FEATURE_GROUP = {
    "network_line_flow": "flow",
    "network_line_return": "return",
    "building_connection": "building",
    "generator_connection": "generator",
}


def feature_groups_from_geojson(geojson: dict):
    """
    Extract the four coordinate-sequence groups from a unified network GeoJSON dict.

    Non-LineString features, unknown ``feature_type`` values and degenerate (<2 vertex)
    lines are ignored. Coordinates are taken as-is (the unified file is stored in the
    project's projected CRS, i.e. metres — so the metre tolerance applies directly).

    :return: ``(flow_lines, return_lines, building_connections, generator_connections)``.
    """
    groups: dict[str, list] = {"flow": [], "return": [], "building": [], "generator": []}
    for feature in geojson.get("features", []):
        group = _GEOJSON_FEATURE_GROUP.get((feature.get("properties") or {}).get("feature_type"))
        geometry = feature.get("geometry") or {}
        if group is None or geometry.get("type") != "LineString":
            continue
        coords = [(c[0], c[1]) for c in geometry.get("coordinates", [])]
        if len(coords) >= 2:
            groups[group].append(coords)
    return groups["flow"], groups["return"], groups["building"], groups["generator"]


def check_geojson_connectivity(geojson: dict, *, tolerance: float = DEFAULT_TOLERANCE_M) -> ConnectivityReport:
    """Run :func:`check_network_connectivity` on a unified network GeoJSON dict."""
    return check_network_connectivity(*feature_groups_from_geojson(geojson), tolerance=tolerance)


def snap_geojson_endpoints(geojson: dict, *, tolerance: float = DEFAULT_TOLERANCE_M) -> tuple[dict, int]:
    """
    Snap near-coincident network endpoints in a unified GeoJSON, in place on a copy.

    Builds one near-miss mapping from all network/connection endpoints and rewrites the
    first/last coordinate of every flow/return/building/generator LineString onto its
    cluster representative — repairing the silent splits without touching feature
    properties or intermediate vertices.

    :return: ``(new_geojson, n_snapped)`` — a deep-copied GeoJSON with snapped endpoints
        and the number of endpoint coordinates changed.
    """
    import copy

    flow, ret, bld, gen = feature_groups_from_geojson(geojson)
    mapping = _cluster_near_points(_all_endpoints(flow, ret, bld, gen), tolerance)

    new_geojson = copy.deepcopy(geojson)
    total = 0
    for feature in new_geojson.get("features", []):
        group = _GEOJSON_FEATURE_GROUP.get((feature.get("properties") or {}).get("feature_type"))
        geometry = feature.get("geometry") or {}
        if group is None or geometry.get("type") != "LineString":
            continue
        coords = geometry.get("coordinates", [])
        if len(coords) < 2:
            continue
        for idx in (0, -1):
            rep = mapping.get((coords[idx][0], coords[idx][1]))
            if rep is not None and (rep[0], rep[1]) != (coords[idx][0], coords[idx][1]):
                coords[idx] = [rep[0], rep[1], *list(coords[idx][2:])]
                total += 1
    return new_geojson, total
