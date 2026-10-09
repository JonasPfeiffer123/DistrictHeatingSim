"""
No saving while a worker runs (BACKLOG UT-K4, user test 2026-10-08).

Saving during the yearly time series stored the running worker's net (controllers and
time-series state); after loading, that net never converged again, neither detailed nor
simplified. The same applied to "Speichern und schließen" during a calculation.
"""

from types import MethodType, SimpleNamespace

import pytest


class _Thread:
    def __init__(self, running):
        self._running = running

    def isRunning(self):
        return self._running


def _record_information(monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    shown = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: shown.append(a[2])))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: pytest.fail("save warning shown")))
    return shown


class TestMainWindow:
    @staticmethod
    def _window(busy_tabs):
        from districtheatingsim.gui.MainTab.main_view import HeatSystemDesignGUI

        window = SimpleNamespace(_BUSY_LABELS=HeatSystemDesignGUI._BUSY_LABELS)
        for attribute in HeatSystemDesignGUI._BUSY_LABELS:
            busy = attribute in busy_tabs
            window.__dict__[attribute] = SimpleNamespace(
                is_busy=lambda busy=busy: busy,
                saved=False,
            )
        window.running_calculations = MethodType(HeatSystemDesignGUI.running_calculations, window)
        window.save_all_project_results = MethodType(HeatSystemDesignGUI.save_all_project_results, window)
        return window

    def test_lists_the_tabs_with_a_running_worker(self):
        window = self._window({"calcTab", "energySystemTab"})
        assert window.running_calculations() == ["Wärmenetzberechnung", "Erzeugerauslegung"]

    def test_central_save_is_refused_and_says_why(self, qapp, monkeypatch):
        shown = _record_information(monkeypatch)
        window = self._window({"calcTab"})
        assert window.save_all_project_results() is False
        assert len(shown) == 1 and "Wärmenetzberechnung" in shown[0] and "nichts gespeichert" in shown[0]


class TestNetSimulationTab:
    @staticmethod
    def _tab(running):
        from districtheatingsim.gui.NetSimulationTab.net_simulation_tab import NetSimulationTab

        tab = SimpleNamespace(_net_thread_running=lambda: running)
        tab._refuse_while_busy = MethodType(NetSimulationTab._refuse_while_busy, tab)
        return tab

    def test_menu_save_tells_the_user_and_does_not_save(self, qapp, monkeypatch):
        shown = _record_information(monkeypatch)
        assert self._tab(running=True)._refuse_while_busy(show_dialog=True) is True
        assert shown and "läuft noch" in shown[0]

    def test_central_save_raises_so_the_error_is_collected(self):
        with pytest.raises(RuntimeError, match="läuft noch"):
            self._tab(running=True)._refuse_while_busy(show_dialog=False)

    def test_idle_tab_saves(self):
        assert self._tab(running=False)._refuse_while_busy(show_dialog=False) is False

    def test_is_busy_reflects_every_worker(self):
        from districtheatingsim.gui.NetSimulationTab.net_simulation_tab import NetSimulationTab

        tab = SimpleNamespace(_init_thread=None, _calc_thread=_Thread(True), _recalc_thread=None)
        tab._net_thread_running = MethodType(NetSimulationTab._net_thread_running, tab)
        assert NetSimulationTab.is_busy(tab) is True
        tab._calc_thread = _Thread(False)
        assert NetSimulationTab.is_busy(tab) is False


def test_energy_results_are_not_saved_during_a_calculation(qapp, monkeypatch, tmp_path):
    from districtheatingsim.gui.EnergySystemTab._01_energy_system_main_tab import EnergySystemTab

    tab = SimpleNamespace(
        energy_system=SimpleNamespace(results={"WGK_Gesamt": 100.0}),
        calculationThread=_Thread(True),
        base_path=str(tmp_path),
    )
    tab.is_busy = MethodType(EnergySystemTab.is_busy, tab)
    with pytest.raises(RuntimeError, match="läuft noch"):
        EnergySystemTab.save_results_JSON(tab, show_dialog=False)
    shown = _record_information(monkeypatch)
    assert EnergySystemTab.save_results_JSON(tab, show_dialog=True) is None
    assert shown and "läuft noch" in shown[0]
    assert list(tmp_path.iterdir()) == []  # nothing written
