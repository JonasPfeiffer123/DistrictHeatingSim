"""
calculation_tab – backward-compatibility shim
=============================================

The God-Class ``CalculationTab`` has been split into focused sub-widgets
(:mod:`network_plot_widget`, :mod:`pipe_config_table`,
:mod:`network_info_panel`, :mod:`time_series_widget`) orchestrated by
:class:`~districtheatingsim.gui.NetSimulationTab.net_simulation_tab.NetSimulationTab`.

This module re-exports ``NetSimulationTab`` under the old name so that
existing code (e.g. ``main_view.py``) keeps working without modification.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from districtheatingsim.gui.NetSimulationTab.net_simulation_tab import NetSimulationTab as CalculationTab  # noqa: F401

__all__ = ["CalculationTab"]
