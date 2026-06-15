"""
Shared base class for the OSM download dialogs.
===============================================

``DownloadOSMDataDialog`` (streets) and ``OSMBuildingQueryDialog`` (buildings)
share the map-polygon capture (JavaScript bridge), the download-thread lifecycle
handlers, and common construction. That duplication lives here; the two concrete
dialogs in ``osm_dialogs.py`` keep only their distinct UI, validation and worker
logic.

Subclasses must provide:
- ``self._download_button``: the start/download QPushButton (set in ``initUI``),
  used by the cancel/error handlers to re-enable the button.
- ``_temp_polygon_filename``: class attribute naming the temp file for a polygon
  captured from the map.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QMessageBox


class OSMDownloadDialogBase(QDialog):
    """Common base for the OSM street/building download dialogs."""

    #: Temp file name for a polygon captured from the map (overridden per subclass).
    _temp_polygon_filename = "_temp_polygon.geojson"

    def __init__(
        self, base_path, config_manager, parent, parent_pres, project_crs: str = "EPSG:25833", visualization_tab=None
    ):
        """
        Initialize shared dialog state.

        :param base_path: Base path for file operations.
        :param config_manager: Configuration manager instance.
        :param parent: Parent widget.
        :param parent_pres: Parent presenter instance.
        :param project_crs: Projected CRS for downloaded data.
        :param visualization_tab: Optional visualization tab for map interaction.
        """
        super().__init__(parent)
        self.base_path = base_path
        self.config_manager = config_manager
        self.parent_pres = parent_pres
        self.project_crs = project_crs
        self.visualization_tab = visualization_tab
        self.waiting_for_polygon = False
        self.download_thread = None
        self.progress_dialog = None
        self._download_button = None  # set by subclass initUI

        # Allow interaction with the map while the dialog is open.
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)

    def setVisualizationTab(self, visualization_tab):
        """
        Set visualization tab reference for map interaction.

        :param visualization_tab: The visualization tab instance.
        """
        self.visualization_tab = visualization_tab

    # ------------------------------------------------------------------
    # Map polygon capture (JavaScript bridge)
    # ------------------------------------------------------------------

    def _begin_polygon_capture(self) -> bool:
        """
        Wire the ``polygon_ready`` signal and enable JS polygon-capture mode.

        Shared core of ``activateMapPolygonDrawing``; the subclasses add their own
        (cosmetically different) button/label updates around this call.

        :return: True if capture started, False if there is no map connection.
        :rtype: bool
        """
        if not self.visualization_tab:
            return False

        self.waiting_for_polygon = True

        if hasattr(self.visualization_tab.view, "geoJsonReceiver"):
            # Disconnect first to avoid duplicate connections.
            try:
                self.visualization_tab.view.geoJsonReceiver.polygon_ready.disconnect(self.onPolygonReady)
            except Exception:
                pass
            self.visualization_tab.view.geoJsonReceiver.polygon_ready.connect(self.onPolygonReady)

        if hasattr(self.visualization_tab.view, "web_view"):
            self.visualization_tab.view.web_view.page().runJavaScript("window.enablePolygonCaptureMode();")

        return True

    def getCapturedPolygonFromMap(self):
        """Get the captured polygon from the map via JavaScript.

        Returns
        -------
        str or None
            Path to temporary GeoJSON file with polygon, or None if no polygon.
        """
        result = {"geojson": None}

        def handle_result(geojson_str):
            if geojson_str:
                try:
                    result["geojson"] = json.loads(geojson_str)
                except Exception:
                    pass

        if hasattr(self.visualization_tab.view, "web_view"):
            js_code = """
                (function() {
                    var polygon = window.getCapturedPolygon();
                    return polygon ? JSON.stringify(polygon) : null;
                })();
            """
            self.visualization_tab.view.web_view.page().runJavaScript(js_code, handle_result)

            # Wait a bit for the callback (simple blocking approach).
            from PyQt6.QtCore import QEventLoop, QTimer

            loop = QEventLoop()
            QTimer.singleShot(100, loop.quit)
            loop.exec()

            if result["geojson"]:
                temp_file = os.path.join(self.base_path, self._temp_polygon_filename)
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(result["geojson"], f)
                return temp_file

        return None

    def clearCapturedPolygon(self):
        """Clear the captured polygon from the map."""
        if self.visualization_tab and hasattr(self.visualization_tab.view, "web_view"):
            self.visualization_tab.view.web_view.page().runJavaScript("window.clearCapturedPolygon();")

    # ------------------------------------------------------------------
    # Download-thread lifecycle
    # ------------------------------------------------------------------

    def _onDownloadCanceled(self):
        """
        Handle download cancellation: terminate the thread and reset the button.
        """
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.terminate()
            self.download_thread.wait()
        if self._download_button is not None:
            self._download_button.setEnabled(True)
            self._download_button.setText("Download starten")

    def _onDownloadError(self, error_message):
        """Handle download error: close progress, reset button, show the message."""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        if self._download_button is not None:
            self._download_button.setEnabled(True)
            self._download_button.setText("Download starten")
        QMessageBox.critical(self, "Fehler", error_message)
