"""
Network Plot Widget
===================

Interactive Plotly/WebEngine network visualization with pipe click detection
and parameter overlay dropdown.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import logging
import os
import tempfile
import traceback

try:
    from PyQt6.QtWebEngineCore import QWebEngineSettings
    from PyQt6.QtWebEngineWidgets import QWebEngineView

    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False
    logging.warning("PyQt6.QtWebEngineWidgets not available. Interactive plot will use fallback label.")

from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QLabel, QVBoxLayout, QWidget

from districtheatingsim.net_simulation_pandapipes.interactive_network_plot import InteractiveNetworkPlot


class NetworkPlotWidget(QWidget):
    """
    Interactive Plotly network visualization embedded in a QWebEngineView.

    Emits :attr:`pipe_selected` whenever the user clicks a pipe in the plot.
    Call :meth:`set_network` with a ``NetworkGenerationData`` instance to
    render the network; call :meth:`highlight_pipe` to programmatically
    highlight a pipe from an external selection.
    """

    pipe_selected = pyqtSignal(int)  # pipe index

    # JavaScript injected into every generated HTML file
    _CLICK_JS = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        var plotDiv = document.getElementsByClassName('plotly-graph-div')[0];
        if (!plotDiv) return;

        window.lastHighlighted = -1;

        plotDiv.on('plotly_click', function(data) {
            try {
                for (var i = 0; i < data.points.length; i++) {
                    var point = data.points[i];
                    if (point.customdata && point.customdata.length > 0) {
                        var pipeIdx = point.customdata[0];
                        var traceIdx = point.curveNumber;
                        window.highlightPipe(pipeIdx, traceIdx);
                        window.selectedPipeIndex = pipeIdx;
                    }
                }
            } catch (e) {
                console.error('Error in click handler:', e);
            }
        });

        window.highlightPipe = function(pipeIdx, traceIdx) {
            try {
                var plotDiv = document.getElementsByClassName('plotly-graph-div')[0];
                if (!plotDiv || !plotDiv.data) return;

                if (window.lastHighlighted >= 0) {
                    Plotly.restyle(plotDiv, {
                        'line.width': 4,
                        'line.color': '#2c3e50'
                    }, [window.lastHighlighted]);
                }

                var targetTrace = -1;
                if (traceIdx !== undefined && traceIdx >= 0) {
                    targetTrace = traceIdx;
                } else {
                    for (var i = 0; i < plotDiv.data.length; i++) {
                        var trace = plotDiv.data[i];
                        if (trace.customdata && trace.customdata[0] && trace.customdata[0][0] === pipeIdx) {
                            targetTrace = i;
                            break;
                        }
                    }
                }

                if (targetTrace >= 0) {
                    Plotly.restyle(plotDiv, {
                        'line.width': 8,
                        'line.color': '#FF4500'
                    }, [targetTrace]);
                    window.lastHighlighted = targetTrace;
                }
            } catch (e) {
                console.error('Error highlighting pipe:', e);
            }
        };
    });
    </script>
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._net_data = None
        self._plot_html_path = None
        self._last_selected_pipe = None
        self._page_ready = False  # True once the WebEngine page has finished loading
        self.project_crs: str = "EPSG:25833"

        self._click_timer = QTimer()
        self._click_timer.setInterval(200)
        self._click_timer.timeout.connect(self._poll_click)

        self._init_ui()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def set_network(self, net_data):
        """
        Set network data and refresh the plot.

        :param net_data: Simulation result data with ``net`` attribute.
        :type net_data: NetworkGenerationData
        """
        self._net_data = net_data
        self._invalidate_cache()
        self._populate_param_dropdown()
        self.refresh(force=True)

    def refresh(self, force: bool = False):
        """
        Render or reload the network plot.

        :param force: If ``True``, regenerate the HTML even when cached.
        :type force: bool
        """
        if self._net_data is None or not hasattr(self._net_data, "net"):
            return

        try:
            if not force and self._plot_html_path and os.path.exists(self._plot_html_path):
                if WEBENGINE_AVAILABLE:
                    self._page_ready = False
                    self._canvas.setUrl(QUrl.fromLocalFile(self._plot_html_path))
                return

            selected = self._param_dropdown.currentData()
            component_type = selected["component"] if selected else None
            parameter = selected["parameter"] if selected else None

            plotter = InteractiveNetworkPlot(self._net_data.net, crs=self.project_crs)
            fig = plotter.create_plot(
                parameter=parameter,
                component_type=component_type,
                basemap_style="carto-positron",
                colorscale="RdYlBu_r",
            )

            if WEBENGINE_AVAILABLE:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
                    fig.write_html(
                        f.name,
                        include_plotlyjs="inline",
                        config={"displayModeBar": True, "displaylogo": False},
                    )
                    self._plot_html_path = f.name

                self._inject_click_handler(self._plot_html_path)
                self._page_ready = False
                self._canvas.setUrl(QUrl.fromLocalFile(self._plot_html_path))

                if not self._click_timer.isActive():
                    self._click_timer.start()
            else:
                self._canvas.setText(
                    "Interactive visualization requires PyQt6-WebEngine.\nPlease install: pip install PyQt6-WebEngine"
                )

        except Exception as e:
            logging.error(f"Error creating interactive plot: {e}\n{traceback.format_exc()}")
            if WEBENGINE_AVAILABLE:
                self._canvas.setHtml(f"<html><body><h3>Error creating plot:</h3><p>{str(e)}</p></body></html>")

    def highlight_pipe(self, pipe_idx: int):
        """
        Highlight *pipe_idx* in the plot via JavaScript.

        :param pipe_idx: Index of the pipe to highlight.
        :type pipe_idx: int
        """
        if not WEBENGINE_AVAILABLE:
            return
        js = f"if (window.highlightPipe) {{ window.highlightPipe({pipe_idx}); }}"
        self._canvas.page().runJavaScript(js)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)

        self._param_dropdown = QComboBox()
        self._param_dropdown.setFixedHeight(35)
        self._param_dropdown.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 2px solid #3498db;
                border-radius: 5px;
                background-color: white;
                font-size: 12px;
            }
            QComboBox:hover { border-color: #2980b9; }
            QComboBox::drop-down { border: none; width: 30px; }
        """)
        self._param_dropdown.addItem("Standard (ohne Parameter)", userData=None)
        self._param_dropdown.currentIndexChanged.connect(self._on_param_changed)
        layout.addWidget(self._param_dropdown)

        if WEBENGINE_AVAILABLE:
            self._canvas = QWebEngineView()
            self._canvas.setMinimumSize(500, 500)
            self._canvas.loadFinished.connect(self._on_load_finished)
            settings = self._canvas.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        else:
            self._canvas = QLabel("Interactive plot requires PyQt6-WebEngine")
            self._canvas.setMinimumSize(500, 500)
            self._canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._canvas)

    def _populate_param_dropdown(self):
        if self._net_data is None or not hasattr(self._net_data, "net"):
            return

        self._param_dropdown.blockSignals(True)
        self._param_dropdown.clear()
        self._param_dropdown.addItem("Standard (ohne Parameter)", userData=None)

        try:
            plotter = InteractiveNetworkPlot(self._net_data.net, crs=self.project_crs)
            available = plotter._get_available_parameters()

            component_labels = {
                "junction": "Junction",
                "pipe": "Pipe",
                "heat_consumer": "Heat Consumer",
                "pump": "Pump",
                "flow_control": "Flow Control",
            }
            for comp, label in component_labels.items():
                if comp in available and available[comp]:
                    for param in available[comp]:
                        item_label = f"{label}: {plotter._get_parameter_label(param)}"
                        self._param_dropdown.addItem(
                            item_label,
                            userData={"component": comp, "parameter": param},
                        )
        except Exception as e:
            logging.error(f"Error populating network param dropdown: {e}")
        finally:
            self._param_dropdown.blockSignals(False)

    def _on_param_changed(self, _index: int):
        # Fast path: the network is unchanged, only the colouring parameter changed.
        # Push the new traces into the already-loaded Plotly div via Plotly.react()
        # instead of regenerating the (3.5 MB inline-plotly.js) HTML and reloading the
        # whole page — that reload is what re-fetches the map tiles and costs ~1-2 s.
        if WEBENGINE_AVAILABLE and self._page_ready and self._net_data is not None and hasattr(self._net_data, "net"):
            if self._update_plot_in_place():
                return
        # Fallback (page not ready yet, or the JS update could not be built): full reload.
        self._invalidate_cache()
        self.refresh(force=True)

    def _update_plot_in_place(self) -> bool:
        """
        Recolour the plot without reloading the page.

        Rebuilds the figure in Python (cheap) and hands its data/layout to
        ``Plotly.react`` in the live page, preserving the current map pan/zoom and the
        existing click handlers. Returns ``False`` if the figure could not be built, so
        the caller can fall back to a full reload.
        """
        try:
            selected = self._param_dropdown.currentData()
            component_type = selected["component"] if selected else None
            parameter = selected["parameter"] if selected else None

            plotter = InteractiveNetworkPlot(self._net_data.net, crs=self.project_crs)
            fig = plotter.create_plot(
                parameter=parameter,
                component_type=component_type,
                basemap_style="carto-positron",
                colorscale="RdYlBu_r",
            )
            fig_json = fig.to_json()
        except Exception as e:
            logging.error(f"Error rebuilding plot for in-place update: {e}")
            return False

        # fig_json is a JSON document → also a valid JS object literal; embed directly.
        js = (
            """
        (function() {
            try {
                var plotDiv = document.getElementsByClassName('plotly-graph-div')[0];
                if (!plotDiv || !window.Plotly) return;
                var fig = """
            + fig_json
            + """;
                // Keep the user's current map view instead of snapping back.
                if (plotDiv.layout && plotDiv.layout.mapbox && fig.layout.mapbox) {
                    fig.layout.mapbox.center = plotDiv.layout.mapbox.center;
                    fig.layout.mapbox.zoom = plotDiv.layout.mapbox.zoom;
                }
                Plotly.react(plotDiv, fig.data, fig.layout);
                window.lastHighlighted = -1;
            } catch (e) {
                console.error('In-place plot update failed:', e);
            }
        })();
        """
        )
        self._canvas.page().runJavaScript(js)
        return True

    def _on_load_finished(self, ok: bool):
        self._page_ready = bool(ok)

    def _invalidate_cache(self):
        if self._plot_html_path and os.path.exists(self._plot_html_path):
            try:
                os.remove(self._plot_html_path)
            except Exception as e:
                logging.warning(f"Could not remove old plot file: {e}")
        self._plot_html_path = None

    def _inject_click_handler(self, html_path: str):
        try:
            with open(html_path, encoding="utf-8") as f:
                html = f.read()
            html = html.replace("</body>", self._CLICK_JS + "</body>")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
        except Exception as e:
            logging.error(f"Failed to inject click handler: {e}")

    def _poll_click(self):
        if not WEBENGINE_AVAILABLE:
            return
        try:
            self._canvas.page().runJavaScript(
                "window.selectedPipeIndex",
                self._on_click_result,
            )
        except Exception as e:
            logging.debug(f"Error polling plot click: {e}")

    def _on_click_result(self, pipe_idx):
        if pipe_idx is None or pipe_idx == self._last_selected_pipe:
            return
        self._last_selected_pipe = pipe_idx
        try:
            self._canvas.page().runJavaScript("window.selectedPipeIndex = null;")
        except Exception:
            pass
        self.pipe_selected.emit(int(pipe_idx))
