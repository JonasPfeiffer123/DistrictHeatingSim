"""
Network plot pipe clicks (BACKLOG G10): pushed over the QWebChannel instead of polled.

The widget used to poll ``window.selectedPipeIndex`` via ``runJavaScript`` every 200 ms for as
long as it existed. The QWebEngineView itself cannot be constructed headless (it crashes under
offscreen Qt — see test_netsim_widgets.py), so these pin the two halves around it: the page
patch (inlined qwebchannel.js + a click handler that calls the bridge) and the bridge that turns
the JavaScript call into the widget's ``pipe_selected`` signal.
"""

from districtheatingsim.gui.NetSimulationTab import network_plot_widget as npw

# Stand-in for plotly's write_html output; the inline script contains the markers the patch
# looks for, as an inlined library could.
_PLOTLY_HTML = (
    "<html><head><meta charset='utf-8'></head><body>"
    "<div class='plotly-graph-div'></div><script>var s = '</head></body>';</script>"
    "</body></html>"
)


def test_patch_inlines_the_channel_client_and_click_handler_once():
    html = npw.NetworkPlotWidget.patch_plot_html(_PLOTLY_HTML)

    assert html.count(npw.NetworkPlotWidget._FILL_CSS) == 1
    assert html.count("var QWebChannel = function") == 1
    assert html.count("pipeBridge.pipeClicked(pipeIdx)") == 1
    # client first, then the handler that uses it, both inside the real body
    assert html.index("var QWebChannel = function") < html.index("new QWebChannel(") < html.rindex("</body>")
    assert html.endswith("</body></html>")
    assert "var s = '</head></body>';" in html  # markers inside scripts are left alone
    assert "selectedPipeIndex" not in html  # the polling contract is gone


def test_patch_leaves_html_without_body_unchanged_apart_from_css():
    assert "pipeBridge" not in npw.NetworkPlotWidget.patch_plot_html("<html><head></head></html>")


def test_bridge_publishes_the_slot_and_emits_every_click(qapp):
    bridge = npw.PipeClickBridge()
    meta = bridge.metaObject()
    methods = {bytes(meta.method(i).methodSignature()).decode() for i in range(meta.methodCount())}
    assert "pipeClicked(int)" in methods  # what QWebChannel exposes to the page

    received = []
    bridge.pipe_clicked.connect(received.append)
    bridge.pipeClicked(7)
    bridge.pipeClicked(7)
    bridge.pipeClicked(2)
    # Re-clicking a pipe selects it again (the poller swallowed repeats of the last pipe).
    assert received == [7, 7, 2]
