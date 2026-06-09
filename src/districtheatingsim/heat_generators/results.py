"""
Energy-system result records.
=============================

One :class:`TechnologyResult` per row of the energy-system result, replacing the
eight hand-maintained parallel lists in ``energy_system.py`` (BACKLOG C4). The
record is the single source of truth; the legacy German ``results`` lists
(``techs``, ``Wärmemengen``, ``Anteile`` …) are projected from it for the GUI and
serialization. Appending one record keeps every projected list in lockstep, so the
divergence bugs that motivated this are structurally impossible.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class TechnologyResult:
    """A single technology's (or storage/unmet-demand row's) contribution.

    Field → legacy ``results`` list it projects to:

    - ``name``                 → ``techs``
    - ``heat_output_kW``       → ``Wärmeleistung_L``
    - ``heat_amount_MWh``      → ``Wärmemengen``
    - ``share``                → ``Anteile``
    - ``heat_generation_cost`` → ``WGK``
    - ``specific_co2``         → ``specific_emissions_L``
    - ``primary_energy``       → ``primärenergie_L``
    - ``color``                → ``colors``
    """

    name: str
    heat_output_kW: np.ndarray   # per-timestep thermal output [kW]
    heat_amount_MWh: float       # annual heat generated [MWh]
    share: float                 # fraction of the annual heat demand [-]
    heat_generation_cost: float  # LCOH / Wärmegestehungskosten [€/MWh]
    specific_co2: float          # specific CO₂ emissions [t/MWh_th]
    primary_energy: float        # primary energy [MWh]
    color: str                   # plot colour
