"""
Tests for the unified-network GeoJSON ``feature_type`` repair (BACKLOG C32).

Older Leaflet map exports wrote ``layer_name`` (Vorlauf/Rücklauf/HAST/Erzeugeranlagen)
onto the saved features but not ``feature_type``. Reloading such a network then crashed
with ``KeyError: 'feature_type'`` (dialog) or silently imported nothing (map).
``ensure_feature_types`` / ``read_network_gdf`` derive the missing ``feature_type`` from
``layer_name`` so those files load again.
"""

import json

from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema


def _feature(props, coords=((0.0, 0.0), (1.0, 1.0))):
    return {
        "type": "Feature",
        "properties": dict(props),
        "geometry": {"type": "LineString", "coordinates": [list(c) for c in coords]},
    }


class TestEnsureFeatureTypes:
    def test_fills_missing_from_layer_name(self):
        gj = {
            "type": "FeatureCollection",
            "features": [
                _feature({"layer_name": "Vorlauf"}),
                _feature({"layer_name": "Rücklauf"}),
                _feature({"layer_name": "HAST"}),
                _feature({"layer_name": "Erzeugeranlagen"}),
            ],
        }
        NetworkGeoJSONSchema.ensure_feature_types(gj)
        types = [f["properties"]["feature_type"] for f in gj["features"]]
        assert types == [
            NetworkGeoJSONSchema.FEATURE_TYPE_FLOW,
            NetworkGeoJSONSchema.FEATURE_TYPE_RETURN,
            NetworkGeoJSONSchema.FEATURE_TYPE_BUILDING,
            NetworkGeoJSONSchema.FEATURE_TYPE_GENERATOR,
        ]

    def test_existing_feature_type_is_preserved(self):
        gj = {
            "type": "FeatureCollection",
            "features": [_feature({"layer_name": "Vorlauf", "feature_type": "network_line_return"})],
        }
        NetworkGeoJSONSchema.ensure_feature_types(gj)
        # An explicit feature_type wins over the layer_name guess.
        assert gj["features"][0]["properties"]["feature_type"] == "network_line_return"

    def test_unknown_layer_name_left_without_feature_type(self):
        gj = {"type": "FeatureCollection", "features": [_feature({"layer_name": "Sonstiges"})]}
        NetworkGeoJSONSchema.ensure_feature_types(gj)
        assert "feature_type" not in gj["features"][0]["properties"]

    def test_no_properties_does_not_crash(self):
        gj = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": None}]}
        NetworkGeoJSONSchema.ensure_feature_types(gj)  # must not raise


class TestReadNetworkGdf:
    def _write(self, tmp_path, features):
        path = tmp_path / "Wärmenetz.geojson"
        path.write_text(
            json.dumps({"type": "FeatureCollection", "features": features}),
            encoding="utf-8",
        )
        return str(path)

    def test_repairs_missing_feature_type_column(self, tmp_path):
        # A file with layer_name but no feature_type (the broken older-export shape).
        path = self._write(
            tmp_path,
            [
                _feature({"layer_name": "Vorlauf"}),
                _feature({"layer_name": "Erzeugeranlagen"}),
            ],
        )
        gdf = NetworkGeoJSONSchema.read_network_gdf(path)
        assert "feature_type" in gdf.columns
        assert set(gdf["feature_type"]) == {
            NetworkGeoJSONSchema.FEATURE_TYPE_FLOW,
            NetworkGeoJSONSchema.FEATURE_TYPE_GENERATOR,
        }
        # The downstream filter pattern now works instead of raising KeyError.
        flow = gdf[gdf["feature_type"] == NetworkGeoJSONSchema.FEATURE_TYPE_FLOW]
        assert len(flow) == 1

    def test_intact_file_is_unchanged(self, tmp_path):
        path = self._write(
            tmp_path,
            [_feature({"layer_name": "Vorlauf", "feature_type": NetworkGeoJSONSchema.FEATURE_TYPE_FLOW})],
        )
        gdf = NetworkGeoJSONSchema.read_network_gdf(path)
        assert list(gdf["feature_type"]) == [NetworkGeoJSONSchema.FEATURE_TYPE_FLOW]
