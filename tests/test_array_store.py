"""
Tests for the array-store file format (BACKLOG G7).

``array_store.load(dump(obj))`` must return exactly what the JSON round trip returns — the same
nesting, element types (int vs float vs bool), NaN/inf and key conversion — so every reader of
the former JSON files works unchanged. Checked strictly by comparing ``json.dumps`` output.
"""

import json

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

from districtheatingsim.heat_generators.json_encoder import CustomJSONEncoder
from districtheatingsim.utilities import array_store


def _via_json(obj):
    return json.loads(json.dumps(obj, cls=CustomJSONEncoder))


def _via_store(obj, tmp_path):
    path = str(tmp_path / "data.parquet")
    array_store.dump(obj, path, json_encoder=CustomJSONEncoder)
    return array_store.load(path)


def _same(a, b):
    return json.dumps(a) == json.dumps(b)


N = array_store.MIN_ARRAY_LENGTH + 36


@pytest.mark.parametrize(
    "obj",
    [
        pytest.param({"x": [float(i) / 3 for i in range(N)]}, id="float-list"),
        pytest.param({"x": list(range(N))}, id="int-list"),
        pytest.param({"x": [i % 2 == 0 for i in range(N)]}, id="bool-list"),
        pytest.param({"x": [f"2023-01-01T{i % 24:02d}" for i in range(N)]}, id="str-list"),
        pytest.param({"x": [1, 2.5] * (N // 2)}, id="mixed-int-float-list"),
        pytest.param({"x": [1.0, None] * (N // 2)}, id="list-with-none"),
        pytest.param({"x": [0.5, 1.5, 2.5]}, id="short-list"),
        pytest.param({"x": [float("nan"), float("inf"), -float("inf")] * (N // 3 + 1)}, id="nan-inf"),
        pytest.param({"x": np.linspace(0, 1, N)}, id="np-float64"),
        pytest.param({"x": np.linspace(0, 1, N, dtype=np.float32)}, id="np-float32"),
        pytest.param({"x": np.arange(N, dtype=np.int32)}, id="np-int32"),
        pytest.param({"x": np.arange(N, dtype=np.uint64) + np.uint64(2**63)}, id="np-uint64-overflow"),
        pytest.param({"x": np.arange(N) % 2 == 0}, id="np-bool"),
        pytest.param({"x": np.arange(2 * N, dtype=float).reshape(2, N)}, id="np-2d"),
        pytest.param({"x": [np.float64(0.1)] * N, "y": np.int64(7), "z": np.float64(1.5)}, id="np-scalars"),
        pytest.param({"x": (1.0,) * N}, id="tuple"),
        pytest.param({1: [1.0] * N, "nested": {"a": [{"b": list(range(N))}]}}, id="int-key-nested"),
        pytest.param({"df": pd.DataFrame({"a": np.arange(N, dtype=float), "b": np.arange(N)})}, id="encoder-object"),
        pytest.param([[0.25] * N, "text", 3], id="top-level-list"),
    ],
)
def test_round_trip_matches_json(obj, tmp_path):
    assert _same(_via_store(obj, tmp_path), _via_json(obj))


def test_identical_arrays_are_stored_once(tmp_path):
    series = [float(i) for i in range(N)]
    obj = {str(b): {"außentemperatur": list(series), "wärme": [v * b for v in series]} for b in range(2, 7)}
    path = str(tmp_path / "data.parquet")
    array_store.dump(obj, path)

    assert pq.read_table(path).num_rows == 1 + 5  # one shared temperature row + five demand rows
    loaded = array_store.load(path)
    assert _same(loaded, obj)
    loaded["2"]["außentemperatur"].append(0.0)  # references come back as independent lists
    assert len(loaded["3"]["außentemperatur"]) == N


def test_is_array_store(tmp_path):
    store, other, text = tmp_path / "a.parquet", tmp_path / "b.parquet", tmp_path / "c.json"
    array_store.dump({"x": 1}, str(store))
    pd.DataFrame({"a": [1]}).to_parquet(other)
    text.write_text("{}", encoding="utf-8")

    assert array_store.is_array_store(str(store))
    assert not array_store.is_array_store(str(other))
    assert not array_store.is_array_store(str(text))
    with pytest.raises(ValueError):
        array_store.load(str(other))


def test_unencodable_object_raises_like_json(tmp_path):
    with pytest.raises(TypeError):
        array_store.dump({"x": object()}, str(tmp_path / "a.parquet"), json_encoder=CustomJSONEncoder)
