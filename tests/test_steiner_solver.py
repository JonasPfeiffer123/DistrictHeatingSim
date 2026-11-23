"""Optional solver routing and compatibility with the existing OSMnx pipeline."""

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import geopandas as gpd
import networkx as nx
import pytest
from shapely.geometry import LineString, Point

from districtheatingsim.net_generation import osmnx_steiner_network as routing


@pytest.fixture
def district():
    graph = nx.MultiDiGraph(crs="EPSG:25833")
    for node, (x, y) in enumerate(((0, 0), (10, 0), (0, 10), (5, 5))):
        graph.add_node(node, x=x, y=y)
    for u, v, length in ((0, 1, 2), (1, 2, 2), (2, 0, 2), (0, 3, 1.1), (1, 3, 1.1), (2, 3, 1.1)):
        graph.add_edge(u, v, length=length, name="short street")
        graph.add_edge(v, u, length=length, name="short street")
    graph.add_edge(0, 3, length=9, name="long parallel street")
    graph.add_edge(0, 0, length=1)
    graph[0][3][0]["geometry"] = graph[3][0][0]["geometry"] = LineString([(0, 0), (1, 3), (5, 5)])
    terminals = gpd.GeoDataFrame(
        geometry=[Point(0, 0), Point(10, 0), Point(0, 10), Point(0, 0)], crs=graph.graph["crs"]
    )
    return graph, terminals


@pytest.fixture
def fake_solver(monkeypatch):
    calls = {}

    def problem(graph, terminals, weight):
        calls.update(graph=graph, terminals=terminals, weight=weight)

        def solve(**kwargs):
            calls.update(kwargs)
            return SimpleNamespace(edges=[(0, 3), (1, 3), (2, 3)], gap=0.05)

        return SimpleNamespace(get_solution=solve)

    monkeypatch.setitem(sys.modules, "steinerpy", SimpleNamespace(Problem=problem))
    return calls


def test_default_matches_networkx_without_optional_dependency(district, monkeypatch):
    graph, terminals = district
    monkeypatch.setitem(sys.modules, "steinerpy", None)
    tree = routing.create_steiner_tree(graph, terminals)
    expected = nx.algorithms.approximation.steiner_tree(graph.to_undirected(), [0, 1, 2, 0], weight="length")
    assert nx.utils.graphs_equal(tree, expected)


def test_optional_solver_preserves_shortest_streets_attributes_and_gap(district, fake_solver):
    graph, terminals = district
    original = graph.copy()
    tree = routing.create_steiner_tree(graph, terminals, solver="steinerpy", time_limit=7)
    assert fake_solver["solver"] == "highs"
    assert fake_solver["time_limit"] == 7
    assert fake_solver["weight"] == "length"
    assert not fake_solver["graph"].is_multigraph()
    assert nx.number_of_selfloops(fake_solver["graph"]) == 0
    assert tree.size(weight="length") == pytest.approx(3.3)
    assert tree[0][3]["name"] == "short street"
    assert tree[0][3]["geometry"].equals(graph[0][3][0]["geometry"])
    assert tree.nodes[3] == graph.nodes[3]
    assert tree.graph["crs"] == graph.graph["crs"]
    assert tree.graph["steiner_gap"] == 0.05
    assert nx.utils.graphs_equal(graph, original)


def test_missing_optional_dependency_is_actionable(district, monkeypatch):
    monkeypatch.setitem(sys.modules, "steinerpy", None)
    with pytest.raises(ImportError, match=r"districtheatingsim\[steiner\]"):
        routing.create_steiner_tree(*district, solver="steinerpy")


@pytest.mark.parametrize(
    "kwargs",
    [{"solver": "typo"}, *({"solver": "steinerpy", "time_limit": t} for t in (0, -1, float("inf"), float("nan")))],
)
def test_invalid_solver_options(district, kwargs):
    with pytest.raises(ValueError):
        routing.create_steiner_tree(*district, **kwargs)


def test_incomplete_solution_is_rejected(district, monkeypatch):
    def problem(*args, **kwargs):
        return SimpleNamespace(get_solution=lambda **kw: SimpleNamespace(edges=[(0, 1)], gap=1))

    monkeypatch.setitem(sys.modules, "steinerpy", SimpleNamespace(Problem=problem))
    with pytest.raises(RuntimeError, match="connecting all terminals"):
        routing.create_steiner_tree(*district, solver="steinerpy")


def test_generation_and_export_forward_solver_options(district, fake_solver, monkeypatch, tmp_path):
    graph, terminals = district
    monkeypatch.setattr(routing, "download_street_graph", lambda **kwargs: graph)
    buildings = terminals.iloc[1:3].copy()
    buildings["UTM_X"] = buildings.geometry.x
    buildings["UTM_Y"] = buildings.geometry.y
    csv = tmp_path / "buildings.csv"
    buildings.drop(columns="geometry").to_csv(csv, sep=";", index=False)
    routing.generate_and_export_osmnx_layers(
        "", str(csv), [(0, 0)], str(tmp_path), steiner_solver="steinerpy", steiner_time_limit=7
    )
    assert fake_solver["time_limit"] == 7
    assert (tmp_path / "Wärmenetz" / "Wärmenetz.geojson").is_file()


def test_real_steinerpy_finds_known_optimum(district):
    pytest.importorskip("steinerpy")
    tree = routing.create_steiner_tree(*district, solver="steinerpy")
    assert nx.is_tree(tree)
    assert {0, 1, 2} <= tree.nodes.keys()
    assert tree.size(weight="length") == pytest.approx(3.3)
    assert tree.graph["steiner_gap"] == pytest.approx(0.0)


def test_benchmark_uses_existing_supply_route(district, fake_solver, monkeypatch, tmp_path):
    example = Path(__file__).resolve().parents[1] / "examples" / "benchmark_steiner_solvers.py"
    compare_solvers = runpy.run_path(str(example))["compare_solvers"]

    graph, terminals = district
    monkeypatch.setattr(routing, "download_street_graph", lambda **kwargs: graph)
    rows = compare_solvers(graph, terminals)
    result = routing.generate_osmnx_network(
        terminals.iloc[1:], [(0, 0)], str(tmp_path), steiner_solver="steinerpy", export_geojson=False
    )
    assert rows[0]["gap"] is None
    assert rows[1]["gap"] == 0.05
    assert rows[1]["trench_length_m"] == pytest.approx(result["supply_network"].length.sum())
