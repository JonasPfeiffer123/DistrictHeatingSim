"""
Technology Input Dialogs Module — compatibility façade.
========================================================

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

The dialog classes were extracted into the ``technology_dialogs`` package
(schema-driven base + one module per technology family; BACKLOG B1). This module
re-exports them so existing imports — notably
``from ..._04_technology_dialogs import TechInputDialog`` in
``_03_technology_tab.py`` — keep working unchanged.
"""

from districtheatingsim.gui.EnergySystemTab.technology_dialogs import (  # noqa: F401
    AqvaHeatDialog,
    BiomassBoilerDialog,
    CheckField,
    CHPDialog,
    Field,
    GasBoilerDialog,
    GeothermalDialog,
    HolzgasCHPDialog,
    PowerToHeatDialog,
    RiverHeatPumpDialog,
    SchemaDialog,
    SolarThermalDialog,
    TechInputDialog,
    ThermalStorage1DDialog,
    WasteHeatPumpDialog,
)

__all__ = [
    "TechInputDialog",
    "Field", "CheckField", "SchemaDialog",
    "GasBoilerDialog", "PowerToHeatDialog", "WasteHeatPumpDialog",
    "BiomassBoilerDialog", "CHPDialog", "HolzgasCHPDialog",
    "SolarThermalDialog", "GeothermalDialog",
    "RiverHeatPumpDialog", "AqvaHeatDialog",
    "ThermalStorage1DDialog",
]
