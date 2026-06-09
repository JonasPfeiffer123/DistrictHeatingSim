"""
Schema-driven dialogs for the simple single-block technologies.

GasBoiler, PowerToHeat and WasteHeatPump are plain QLineEdit forms with no
storage section; they reduce to a class attribute pointing at their field schema.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from districtheatingsim.gui.EnergySystemTab.technology_dialogs._base import SchemaDialog
from districtheatingsim.gui.EnergySystemTab.technology_dialogs import _schemas as S


class GasBoilerDialog(SchemaDialog):
    """Configure gas-boiler parameters."""

    title = "Eingabe für Gaskessel"
    main_schema = S.GAS_BOILER


class PowerToHeatDialog(SchemaDialog):
    """Configure Power-to-Heat parameters."""

    title = "Eingabe für Power-to-Heat"
    main_schema = S.POWER_TO_HEAT


class WasteHeatPumpDialog(SchemaDialog):
    """Configure waste-heat-pump parameters."""

    main_schema = S.WASTE_HEAT_PUMP
