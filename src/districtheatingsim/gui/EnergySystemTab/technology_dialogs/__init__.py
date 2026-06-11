"""
Technology-input dialogs for the Energy System Tab.

Public entry point: :class:`TechInputDialog` routes a technology-type string to
the matching sub-dialog. The simple and combustion dialogs are schema-driven
(see :mod:`._base` / :mod:`._schemas`); solar, geothermal, river/Aqva heat-pump
and 1D thermal-storage dialogs remain hand-written in their own modules.

The legacy module ``_04_technology_dialogs`` re-exports everything from here so
existing import paths keep working.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from districtheatingsim.gui.EnergySystemTab.technology_dialogs._base import (
    CheckField,
    Field,
    SchemaDialog,
)
from districtheatingsim.gui.EnergySystemTab.technology_dialogs._combustion import (
    BiomassBoilerDialog,
    CHPDialog,
    HolzgasCHPDialog,
)
from districtheatingsim.gui.EnergySystemTab.technology_dialogs._dispatcher import TechInputDialog
from districtheatingsim.gui.EnergySystemTab.technology_dialogs._geothermal import GeothermalDialog
from districtheatingsim.gui.EnergySystemTab.technology_dialogs._heat_pump import (
    AqvaHeatDialog,
    RiverHeatPumpDialog,
)
from districtheatingsim.gui.EnergySystemTab.technology_dialogs._simple import (
    GasBoilerDialog,
    PowerToHeatDialog,
    WasteHeatPumpDialog,
)
from districtheatingsim.gui.EnergySystemTab.technology_dialogs._solar import SolarThermalDialog
from districtheatingsim.gui.EnergySystemTab.technology_dialogs._storage import ThermalStorage1DDialog

__all__ = [
    "TechInputDialog",
    "Field", "CheckField", "SchemaDialog",
    "GasBoilerDialog", "PowerToHeatDialog", "WasteHeatPumpDialog",
    "BiomassBoilerDialog", "CHPDialog", "HolzgasCHPDialog",
    "SolarThermalDialog", "GeothermalDialog",
    "RiverHeatPumpDialog", "AqvaHeatDialog",
    "ThermalStorage1DDialog",
]
