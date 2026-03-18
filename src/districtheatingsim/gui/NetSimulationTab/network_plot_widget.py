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
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineSettings
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False
    logging.warning("PyQt6.QtWebEngineWidgets not available. Interactive plot will use fallback label.")

from PyQt6.QtCore import pyqtSignal, QTimer, QUrl
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel
from PyQt6.QtCore import Qt

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
        if self._net_data is None or not hasattr(self._net_data, 'net'):
            return

        try:
            if not force and self._plot_html_path and os.path.exists(self._plot_html_path):
                if WEBENGINE_AVAILABLE:
                    self._canvas.setUrl(QUrl.fromLocalFile(self._plot_html_path))
                return

            selected = self._param_dropdown.currentData()
            component_type = selected['component'] if selected else None
            parameter = selected['parameter'] if selected else None

            plotter = InteractiveNetworkPlot(self._net_data.net, crs=self.project_crs)
            fig = plotter.create_plot(
                parameter=parameter,
                component_type=component_type,
                basemap_style='carto-positron',
                colorscale='RdYlBu_r',
            )

            if WEBENGINE_AVAILABLE:
                with tempfile.NamedTemporaryFile(
                    mode='w', suffix='.html', delete=False, encoding='utf-8'
                ) as f:
                    fig.write_html(
                        f.name,
                        include_plotlyjs='inline',
                        config={'displayModeBar': True, 'displaylogo': False},
                    )
                    self._plot_html_path = f.name

                self._inject_click_handler(self._plot_html_path)
                self._canvas.setUrl(QUrl.fromLocalFile(self._plot_html_path))

                if not self._click_timer.isActive():
                    self._click_timer.start()
            else:
                self._canvas.setText(
                    "Interactive visualization requires PyQt6-WebEngine.\n"
                    "Please install: pip install PyQt6-WebEngine"
                )

        except Exception as e:
            logging.error(f"Error creating interactive plot: {e}\n{traceback.format_exc()}")
            if WEBENGINE_AVAILABLE:
                self._canvas.setHtml(
                    f"<html><body><h3>Error creating plot:</h3><p>{str(e)}</p></body></html>"
                )

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
            settings = self._canvas.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        else:
            self._canvas = QLabel("Interactive plot requires PyQt6-WebEngine")
            self._canvas.setMinimumSize(500, 500)
            self._canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._canvas)

    def _populate_param_dropdown(self):
        if self._net_data is None or not hasattr(self._net_data, 'net'):
            return

        self._param_dropdown.blockSignals(True)
        self._param_dropdown.clear()
        self._param_dropdown.addItem("Standard (ohne Parameter)", userData=None)

        try:
            plotter = InteractiveNetworkPlot(self._net_data.net, crs=self.project_crs)
            available = plotter._get_available_parameters()

            component_labels = {
                'junction': 'Junction',
                'pipe': 'Pipe',
                'heat_consumer': 'Heat Consumer',
                'pump': 'Pump',
                'flow_control': 'Flow Control',
            }
            for comp, label in component_labels.items():
                if comp in available and available[comp]:
                    for param in available[comp]:
                        item_label = f"{label}: {plotter._get_parameter_label(param)}"
                        self._param_dropdown.addItem(
                            item_label,
                            userData={'component': comp, 'parameter': param},
                        )
        except Exception as e:
            logging.error(f"Error populating network param dropdown: {e}")
        finally:
            self._param_dropdown.blockSignals(False)

    def _on_param_changed(self, _index: int):
        self._invalidate_cache()
        self.refresh(force=True)

    def _invalidate_cache(self):
        if self._plot_html_path and os.path.exists(self._plot_html_path):
            try:
                os.remove(self._plot_html_path)
            except Exception as e:
                logging.warning(f"Could not remove old plot file: {e}")
        self._plot_html_path = None

    def _inject_click_handler(self, html_path: str):
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html = f.read()
            html = html.replace('</body>', self._CLICK_JS + '</body>')
            with open(html_path, 'w', encoding='utf-8') as f:
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
