"""
Network generation from layers: failures must reach the caller (BACKLOG C44).

``generate_and_export_layers`` used to catch loading/export errors, log them and return, so the
GUI's ``NetGenerationThread`` emitted ``calculation_done`` and announced a network that was never
written (an older ``Wärmenetz.geojson`` stayed in place). The errors now propagate to the thread's
``calculation_error`` path. These failures happen before any elevation lookup, so no network access.
"""

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString

from districtheatingsim.net_generation.import_and_create_layers import generate_and_export_layers


def _street_layer(tmp_path) -> str:
    path = tmp_path / "streets.geojson"
    gpd.GeoDataFrame(geometry=[LineString([(0, 0), (100, 0)])], crs="EPSG:25833").to_file(path, driver="GeoJSON")
    return str(path)


def test_missing_building_csv_raises_and_writes_nothing(tmp_path):
    with pytest.raises(FileNotFoundError):
        generate_and_export_layers(_street_layer(tmp_path), str(tmp_path / "missing.csv"), [(50, 10)], str(tmp_path))
    assert not (tmp_path / "Wärmenetz").exists()


def test_missing_coordinate_columns_raise_with_the_column_names(tmp_path):
    csv = tmp_path / "buildings.csv"
    pd.DataFrame({"Adresse": ["A"], "Wärmebedarf": [1000.0]}).to_csv(csv, sep=";", index=False)

    with pytest.raises(KeyError, match="UTM_X"):
        generate_and_export_layers(_street_layer(tmp_path), str(csv), [(50, 10)], str(tmp_path))
    assert not (tmp_path / "Wärmenetz").exists()


def test_missing_street_layer_raises(tmp_path):
    csv = tmp_path / "buildings.csv"
    pd.DataFrame({"UTM_X": [10.0], "UTM_Y": [5.0]}).to_csv(csv, sep=";", index=False)

    with pytest.raises(Exception, match="streets_missing"):
        generate_and_export_layers(str(tmp_path / "streets_missing.geojson"), str(csv), [(50, 10)], str(tmp_path))
