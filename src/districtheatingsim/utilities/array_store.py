"""
Compact file format for JSON-like data with large arrays.
=========================================================

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

Project results were written as indented JSON, where every hourly time series (8760 values)
is text and identical series are repeated — ``Gebäude Lastgang.json`` took ~1.75 MB per
building (BACKLOG G7). This module stores the same data as a Parquet file:

- every long, type-homogeneous list or 1-D numpy array (floats, ints, bools or strings) becomes
  one row of a Parquet table (compressed, binary floats); identical arrays are stored once;
- everything else stays in a small JSON "skeleton" in the Parquet schema metadata, with a
  ``{"__dhs_array__": id}`` placeholder where an array was taken out.

:func:`load` returns exactly what ``json.load`` of the equivalent JSON file would return
(same nesting, lists, ``int``/``float``/``bool``/``str`` element types, NaN/inf). Objects JSON
cannot encode natively go through ``json_encoder.default`` first — the same conversion
``json.dump(..., cls=json_encoder)`` applies — so arrays inside them are stored compactly too.
"""

import json

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

FORMAT = "districtheatingsim.array_store/1"
_META_KEY = b"districtheatingsim.array_store"
_REF = "__dhs_array__"
# Shorter lists stay in the skeleton: not worth a table row.
MIN_ARRAY_LENGTH = 64

_INT64_MIN, _INT64_MAX = -(2**63), 2**63 - 1


def _array_kind(values):
    """Return ``(kind, values)`` if ``values`` can become an array row, else ``None``."""
    if isinstance(values, np.ndarray):
        if values.ndim != 1 or len(values) < MIN_ARRAY_LENGTH:
            return None
        if values.dtype.kind == "f":
            return "f", values.astype(np.float64, copy=False)
        if values.dtype.kind == "b":
            return "b", values
        if values.dtype.kind in "iu" and (
            len(values) == 0 or (values.min() >= _INT64_MIN and values.max() <= _INT64_MAX)
        ):
            return "i", values.astype(np.int64)
        return None
    if len(values) < MIN_ARRAY_LENGTH:
        return None
    first = values[0]
    if isinstance(first, (bool, np.bool_)):
        return ("b", values) if all(isinstance(v, (bool, np.bool_)) for v in values) else None
    if isinstance(first, (int, np.integer)):
        ok = all(
            isinstance(v, (int, np.integer)) and not isinstance(v, (bool, np.bool_)) and _INT64_MIN <= v <= _INT64_MAX
            for v in values
        )
        return ("i", values) if ok else None
    if isinstance(first, float):  # includes numpy float64 scalars
        return ("f", values) if all(isinstance(v, float) for v in values) else None
    if isinstance(first, str):
        return ("s", values) if all(isinstance(v, str) for v in values) else None
    return None


class _Extractor:
    def __init__(self, json_encoder):
        self.encoder = json_encoder() if json_encoder else None
        self.rows = []  # (id, kind, values)
        self.seen = {}  # (kind, content key) -> id

    def _store(self, kind, values):
        if kind == "s":
            key = (kind, tuple(values))
        else:
            dtype = {"f": np.float64, "i": np.int64, "b": np.bool_}[kind]
            arr = np.asarray(values, dtype=dtype)
            key = (kind, arr.tobytes())
        if key not in self.seen:
            self.seen[key] = str(len(self.rows))
            self.rows.append((self.seen[key], kind, values))
        return {_REF: self.seen[key]}

    def walk(self, obj):
        if isinstance(obj, dict):
            return {k: self.walk(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, np.ndarray)):
            found = _array_kind(obj)
            if found is not None:
                return self._store(*found)
            if isinstance(obj, np.ndarray):  # what CustomJSONEncoder does with other arrays
                return self.walk(obj.tolist())
            return [self.walk(v) for v in obj]
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        if self.encoder is not None:
            try:
                converted = self.encoder.default(obj)
            except TypeError:
                return obj  # json.dumps below raises exactly as the JSON path would
            return self.walk(converted)
        return obj


def dump(obj, path: str, json_encoder=None) -> None:
    """
    Write ``obj`` (JSON-like) as an array-store Parquet file.

    :param obj: Data to store (dicts, lists, numbers, strings, numpy arrays, …)
    :type obj: Any
    :param path: Target file
    :type path: str
    :param json_encoder: ``json.JSONEncoder`` subclass for objects JSON cannot encode natively
    :type json_encoder: type or None
    """
    extractor = _Extractor(json_encoder)
    skeleton = extractor.walk(obj)
    columns = {"id": [], "kind": [], "f": [], "i": [], "b": [], "s": []}
    for row_id, kind, values in extractor.rows:
        columns["id"].append(row_id)
        columns["kind"].append(kind)
        for k in ("f", "i", "b", "s"):
            columns[k].append(values if k == kind else None)
    table = pa.table(
        {
            "id": pa.array(columns["id"], pa.string()),
            "kind": pa.array(columns["kind"], pa.string()),
            "f": pa.array(columns["f"], pa.list_(pa.float64())),
            "i": pa.array(columns["i"], pa.list_(pa.int64())),
            "b": pa.array(columns["b"], pa.list_(pa.bool_())),
            "s": pa.array(columns["s"], pa.list_(pa.string())),
        }
    )
    meta = json.dumps({"format": FORMAT, "skeleton": skeleton}, cls=json_encoder)
    table = table.replace_schema_metadata({_META_KEY: meta.encode("utf-8")})
    pq.write_table(table, path, compression="zstd")


def is_array_store(path: str) -> bool:
    """Whether ``path`` is a Parquet file written by :func:`dump`."""
    try:
        metadata = pq.read_schema(path).metadata or {}
    except (OSError, pa.ArrowInvalid):
        return False
    return _META_KEY in metadata


def load_json_compatible(path: str):
    """
    Read a file that is either an array store or a (legacy) JSON file — detected from the content.

    :param path: File to read
    :type path: str
    :return: The data, as ``json.load`` would have returned it
    :rtype: Any
    """
    if is_array_store(path):
        return load(path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load(path: str):
    """
    Read an array-store Parquet file.

    :param path: File written by :func:`dump`
    :type path: str
    :return: The data, as ``json.load`` would have returned it
    :rtype: Any
    :raises ValueError: If the file is not an array store
    """
    table = pq.read_table(path)
    metadata = table.schema.metadata or {}
    if _META_KEY not in metadata:
        raise ValueError(f"{path} is not a DistrictHeatingSim array store")
    meta = json.loads(metadata[_META_KEY].decode("utf-8"))
    arrays = {
        row["id"]: row[row["kind"]]
        for row in table.to_pylist()  # lists of Python int/float/bool/str, like json.load
    }

    def restore(node):
        if isinstance(node, dict):
            if len(node) == 1 and _REF in node:
                return list(arrays[node[_REF]])  # fresh list per reference, like json.load
            return {k: restore(v) for k, v in node.items()}
        if isinstance(node, list):
            return [restore(v) for v in node]
        return node

    return restore(meta["skeleton"])
