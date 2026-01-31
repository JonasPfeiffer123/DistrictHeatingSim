"""
Heat Generators Module
======================

This file is used to import all heat generators and to provide a registry for the heat generators.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""
from .base_heat_generator import BaseHeatGenerator, BaseStrategy
from .chp import CHP
from .base_heat_pumps import HeatPump
from .aqvaheat_heat_pump import AqvaHeat
from .river_heat_pump import RiverHeatPump
from .waste_heat_pump import WasteHeatPump
from .geothermal_heat_pump import Geothermal
from .biomass_boiler import BiomassBoiler
from .gas_boiler import GasBoiler
from .power_to_heat import PowerToHeat
from .solar_thermal import SolarThermal
from .STES import STES

TECH_CLASS_REGISTRY = {
    'BHKW': CHP,
    "Holzgas-BHKW": CHP,
    'Flusswärmepumpe': RiverHeatPump,
    'Abwärmepumpe': WasteHeatPump,
    'Geothermie': Geothermal,
    'Biomassekessel': BiomassBoiler,
    'Gaskessel': GasBoiler,
    'Solarthermie': SolarThermal,
    'AqvaHeat': AqvaHeat,
    'Power-to-Heat': PowerToHeat,
    'Saisonaler Wärmespeicher': STES
}
