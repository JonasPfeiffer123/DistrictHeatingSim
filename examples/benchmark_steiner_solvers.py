"""Compare NetworkX and SteinerPy on the district from example 05b.

From the repository root, after ``pip install -e '.[steiner]'``:
    python examples/benchmark_steiner_solvers.py

Downloads once and reuses cache/steiner_benchmark.graphml. Pass --graphml to
keep a separate snapshot. Both solvers use identical inputs and the existing
edge-splitting/dead-end/connection helpers. Timings exclude download and imports,
but include snapping, graph conversion and solver preprocessing. The time limit
applies to the SteinerPy solver, not the whole pipeline.

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
from pathlib import Path
from time import perf_counter

import geopandas as gpd
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
    parser.add_argument("--graphml", type=Path, default=Path("cache/steiner_benchmark.graphml"))
    parser.add_argument("--time-limit", type=float, default=60.0)
    args = parser.parse_args()
    csv_path = Path(__file__).resolve().parent / "data" / "Quartier IST.csv"
    df = pd.read_csv(csv_path, sep=";")
    buildings = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.UTM_X, df.UTM_Y), crs="EPSG:25833")
    generator_coords = [(480219, 5711597)]
    generators = gpd.GeoDataFrame(geometry=[Point(*generator_coords[0])], crs=buildings.crs)
    terminals = pd.concat([buildings, generators], ignore_index=True)
    if args.graphml.exists():
        graph = ox.load_graphml(args.graphml)
    else:
        graph = download_street_graph(buildings, generator_coords)
        args.graphml.parent.mkdir(parents=True, exist_ok=True)
        ox.save_graphml(graph, args.graphml)
    results = compare_solvers(graph, terminals, time_limit=args.time_limit)
    print(
        json.dumps(
            {
                "graphml": str(args.graphml),
                "graph_sha256": hashlib.sha256(args.graphml.read_bytes()).hexdigest(),
                "buildings": len(buildings),
                "terminal_nodes": len(
                    set(ox.distance.nearest_nodes(graph, terminals.geometry.x, terminals.geometry.y))
                ),
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
