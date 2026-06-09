"""
Headless smoke tests for the OSM download dialogs and their shared base class.

Unlike the technology dialogs there is no pure-data contract (getInputs) to pin —
these dialogs drive downloads via threads + a JS map bridge. These smoke tests
therefore only assert that both dialogs construct, inherit the shared base
behaviour, and that the safe shared methods behave sanely without a map/thread:
enough to catch a broken extraction (missing attribute, bad super() wiring).

Headless Qt via the session-scoped ``qapp`` fixture + ``QT_QPA_PLATFORM=offscreen``.
"""

import pytest

from districtheatingsim.gui.LeafletTab.osm_dialogs import (
    DownloadOSMDataDialog,
    OSMBuildingQueryDialog,
)
from districtheatingsim.gui.LeafletTab.osm_dialogs_base import OSMDownloadDialogBase

pytestmark = pytest.mark.usefixtures("qapp")


class _StubConfig:
    """Minimal config_manager: echo the key back as a relative path."""

    def get_relative_path(self, key):
        return key


def _street_dialog(tmp_path):
    return DownloadOSMDataDialog(str(tmp_path), _StubConfig(), None, object())


def _building_dialog(tmp_path):
    return OSMBuildingQueryDialog(str(tmp_path), _StubConfig(), None, object())


class TestConstruction:
    def test_street_dialog_builds(self, tmp_path):
        d = _street_dialog(tmp_path)
        assert isinstance(d, OSMDownloadDialogBase)
        assert d._download_button is d.queryButton
        assert d._temp_polygon_filename == "_temp_download_polygon.geojson"

    def test_building_dialog_builds(self, tmp_path):
        d = _building_dialog(tmp_path)
        assert isinstance(d, OSMDownloadDialogBase)
        assert d._download_button is d.downloadButton
        assert d._temp_polygon_filename == "_temp_building_polygon.geojson"

    @pytest.mark.parametrize("factory", [_street_dialog, _building_dialog])
    def test_shared_methods_inherited(self, factory, tmp_path):
        d = factory(tmp_path)
        for name in ("setVisualizationTab", "getCapturedPolygonFromMap",
                     "clearCapturedPolygon", "_begin_polygon_capture",
                     "_onDownloadCanceled", "_onDownloadError"):
            assert hasattr(d, name)


class TestSharedBehaviourWithoutMap:
    """The base methods must be safe when there is no visualization tab / thread."""

    @pytest.mark.parametrize("factory", [_street_dialog, _building_dialog])
    def test_clear_polygon_noop_without_map(self, factory, tmp_path):
        d = factory(tmp_path)
        assert d.visualization_tab is None
        d.clearCapturedPolygon()  # must not raise

    @pytest.mark.parametrize("factory", [_street_dialog, _building_dialog])
    def test_begin_capture_returns_false_without_map(self, factory, tmp_path):
        d = factory(tmp_path)
        assert d._begin_polygon_capture() is False

    @pytest.mark.parametrize("factory", [_street_dialog, _building_dialog])
    def test_cancel_resets_button_without_thread(self, factory, tmp_path):
        d = factory(tmp_path)
        d._download_button.setEnabled(False)
        d._download_button.setText("Download läuft...")
        d._onDownloadCanceled()  # download_thread is None → just resets the button
        assert d._download_button.isEnabled()
        assert d._download_button.text() == "Download starten"


class TestAreaTypeToggle:
    def test_street_city_default_visible(self, tmp_path):
        d = _street_dialog(tmp_path)
        d.areaTypeComboBox.setCurrentIndex(0)  # "Stadt/Ortsname"
        d.toggleAreaType(0)
        assert d.cityWidget.isVisibleTo(d)
        assert not d.csvWidget.isVisibleTo(d)

    def test_building_csv_default_visible(self, tmp_path):
        d = _building_dialog(tmp_path)
        d.areaTypeComboBox.setCurrentIndex(0)  # "Bereich um Gebäude aus CSV"
        d.toggleAreaType()
        assert d.csvWidget.isVisibleTo(d)
        assert not d.polygonWidget.isVisibleTo(d)


class TestHighwayFilter:
    def test_no_types_selected(self, tmp_path):
        d = _street_dialog(tmp_path)
        for cb in d.highwayCheckboxes.values():
            cb.setChecked(False)
        d.updateFilters()
        assert d.custom_filter == '["highway"]'

    def test_single_type_selected(self, tmp_path):
        d = _street_dialog(tmp_path)
        for cb in d.highwayCheckboxes.values():
            cb.setChecked(False)
        d.highwayCheckboxes["primary"].setChecked(True)
        d.updateFilters()
        assert d.custom_filter == '["highway"~"primary"]'
