"""
Map reload after project/variant changes (BACKLOG UT-M3, user test 2026-10-08).

Every folder change connected another one-shot ``loadFinished`` handler; opening a project emits
several folder changes in a row, all handlers fired on the final page, and the network appeared
three times in the layer list.
"""

from types import MethodType, SimpleNamespace


class _Signal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


def _presenter():
    from districtheatingsim.gui.LeafletTab.leaflet_tab import VisualizationPresenter

    web_view = SimpleNamespace(loadFinished=_Signal(), urls=[])
    web_view.setUrl = web_view.urls.append
    presenter = SimpleNamespace(view=SimpleNamespace(web_view=web_view), map_file_path="map.html")
    presenter._reload_map_then = MethodType(VisualizationPresenter._reload_map_then, presenter)
    presenter._on_map_loaded = MethodType(VisualizationPresenter._on_map_loaded, presenter)
    return presenter, web_view


def test_only_the_latest_callback_runs_once():
    presenter, web_view = _presenter()
    runs = []
    for name in ("project", "variant", "results"):  # what opening a project emits
        presenter._reload_map_then(lambda name=name: runs.append(name))
    assert len(web_view.loadFinished.slots) == 1  # one handler, not one per reload
    assert len(web_view.urls) == 3
    web_view.loadFinished.emit(False)  # superseded loads are aborted
    web_view.loadFinished.emit(False)
    assert runs == []
    web_view.loadFinished.emit(True)
    assert runs == ["results"]
    web_view.loadFinished.emit(True)  # a later, unrelated load runs nothing
    assert runs == ["results"]


def test_next_reload_after_a_finished_one_runs_again():
    presenter, web_view = _presenter()
    runs = []
    presenter._reload_map_then(lambda: runs.append(1))
    web_view.loadFinished.emit(True)
    presenter._reload_map_then(lambda: runs.append(2))
    web_view.loadFinished.emit(True)
    assert runs == [1, 2]
