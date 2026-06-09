"""
Schema-driven dialogs for the combustion technologies with a buffer-storage block.

BiomassBoiler, CHP and HolzgasCHP share an identical 9-field generator-storage
panel (toggled by the "Speicher aktiv" checkbox); only three keys and one default
differ, parametrised via ``_schemas.storage_fields``.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from districtheatingsim.gui.EnergySystemTab.technology_dialogs._base import SchemaDialog
from districtheatingsim.gui.EnergySystemTab.technology_dialogs import _schemas as S


class BiomassBoilerDialog(SchemaDialog):
    """Configure biomass-boiler parameters with optional buffer storage."""

    title = "Eingabe für Biomassekessel"
    main_schema = S.BIOMASS_MAIN
    storage_schema = S.BIOMASS_STORAGE


class CHPDialog(SchemaDialog):
    """Configure gas-CHP parameters with optional buffer storage."""

    main_schema = S.CHP_MAIN
    storage_schema = S.CHP_STORAGE


class HolzgasCHPDialog(SchemaDialog):
    """Configure wood-gas-CHP parameters with optional buffer storage."""

    main_schema = S.HOLZGAS_CHP_MAIN
    storage_schema = S.CHP_STORAGE
