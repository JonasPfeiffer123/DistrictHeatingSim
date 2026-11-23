"""Compare NetworkX and SteinerPy on the district from example 05b.

From the repository root, after ``pip install -e '.[steiner]'``:
    python examples/benchmark_steiner_solvers.py
    python examples/benchmark_steiner_solvers.py --offline

Downloads once and reuses cache/steiner_benchmark.graphml. Pass --graphml to
keep a separate snapshot. Both solvers use identical inputs and the existing
edge-splitting/dead-end/connection helpers. Single-run timings exclude input
preparation and the initial SteinerPy import, but include snapping, graph
conversion, solver preprocessing and first-call library initialization. Warm
both solvers and repeat for stable timing comparisons. The time limit applies
to the SteinerPy solver, not the whole pipeline.

--offline uses the bundled osm_street_data.geojson (a different street selection
from drive_service). It joins only identical existing vertices, selects ways
within 1 km of the terminals' convex hull, retains the largest component like
OSMnx, and simplifies degree-two nodes. No buildings are dropped. Without OSM
node IDs, coincident vertices are assumed to be junctions; crossings between
segments are not joined. Input hashes and discarded-node counts are reported.

Trench length is the final supply route including building/generator connections
once (before the return-line offset), not the sum of supply and return pipes.
The current post-processing uses straight node-to-node segments, so this metric
differs from the street edges' length weights. The gap certifies only tree cost.
"""

import argparse
import hashlib
import importlib
import json
from importlib.metadata import version
from itertools import pairwise
from pathlib import Path
from time import perf_counter

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd
from shapely.geometry import Point

from districtheatingsim.net_generation.osmnx_steiner_network import (
    build_network_from_split_edges,
    connect_terminals_with_edge_splitting,
    create_connection_lines,
    create_steiner_tree,
    download_street_graph,
    remove_dead_ends,
)


def street_graph_from_geojson(path, terminals):
    streets = gpd.read_file(path).to_crs(terminals.crs)
    streets = streets[streets.intersects(terminals.union_all().convex_hull.buffer(1000))]
    graph = nx.MultiDiGraph(crs=str(terminals.crs))
    # shortcut: the export lacks node IDs; use OSM IDs if coincident non-junction vertices occur.
    node_ids = {}
    for way_id, geometry in streets.geometry.items():
        for start, end in pairwise(geometry.coords):
            if start == end:
                continue
            for xy in (start, end):
                if xy not in node_ids:
                    node_ids[xy] = len(node_ids)
                    graph.add_node(node_ids[xy], x=xy[0], y=xy[1])
            u, v = node_ids[start], node_ids[end]
            attributes = {"osmid": int(way_id), "length": Point(start).distance(Point(end))}
            graph.add_edge(u, v, **attributes)
            graph.add_edge(v, u, **attributes)
    if not graph:
        raise ValueError("No street vertices found near the example district")
    component = max(nx.weakly_connected_components(graph), key=len)
    graph.graph["discarded_street_nodes"] = len(graph) - len(component)
    return ox.simplification.simplify_graph(graph.subgraph(component).copy())


def compare_solvers(street_graph, terminals, time_limit=60.0):
    importlib.import_module("steinerpy")  # Keep the optional import outside the timed section.
    results = []
    for solver in ("networkx", "steinerpy"):
        start = perf_counter()
        tree = create_steiner_tree(street_graph, terminals, solver=solver, time_limit=time_limit)
        tree_seconds = perf_counter() - start
        connections, splits = connect_terminals_with_edge_splitting(tree, street_graph, terminals)
        network = build_network_from_split_edges(tree, street_graph, splits, crs=terminals.crs)
        network = remove_dead_ends(network, {c["network_coords"] for c in connections})
        service_lines = create_connection_lines(connections, crs=terminals.crs)
        results.append(
            {
                "solver": solver,
                "tree_length_m": tree.size(weight="length"),
                "tree_seconds": tree_seconds,
                "gap": tree.graph.get("steiner_gap"),
                "trench_length_m": float(network.length.sum() + service_lines.length.sum()),
                "tree_and_postprocessing_seconds": perf_counter() - start,
            }
        )
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--graphml", type=Path, default=Path("cache/steiner_benchmark.graphml"))
    source.add_argument("--offline", action="store_true", help="Use the bundled OSM streets without a download")
    parser.add_argument("--time-limit", type=float, default=60.0)
    args = parser.parse_args()
    csv_path = Path(__file__).resolve().parent / "data" / "Quartier IST.csv"
    df = pd.read_csv(csv_path, sep=";")
    buildings = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.UTM_X, df.UTM_Y), crs="EPSG:25833")
    generator_coords = [(480219, 5711597)]
    generators = gpd.GeoDataFrame(geometry=[Point(*generator_coords[0])], crs=buildings.crs)
    terminals = pd.concat([buildings, generators], ignore_index=True)
    input_path = args.graphml
    if args.offline:
        input_path = csv_path.parent / "osm_street_data.geojson"
        graph = street_graph_from_geojson(input_path, terminals)
    elif args.graphml.exists():
        graph = ox.load_graphml(args.graphml)
    else:
        graph = download_street_graph(buildings, generator_coords)
        args.graphml.parent.mkdir(parents=True, exist_ok=True)
        ox.save_graphml(graph, args.graphml)
    results = compare_solvers(graph, terminals, time_limit=args.time_limit)
    nearest, distances = ox.distance.nearest_nodes(graph, terminals.geometry.x, terminals.geometry.y, return_dist=True)
    print(
        json.dumps(
            {
                "input_file": str(input_path),
                "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
                "offline": args.offline,
                "buildings": len(buildings),
                "terminal_nodes": len(set(nearest)),
                "max_node_snap_distance_m": float(max(distances)),
                "discarded_street_nodes": graph.graph.get("discarded_street_nodes", 0),
                "street_nodes": graph.number_of_nodes(),
                "street_edges": graph.number_of_edges(),
                "versions": {name: version(name) for name in ("networkx", "osmnx", "steinerpy", "highspy")},
                "time_limit_s": args.time_limit,
                "results": results,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
