"""
Heat Generators Module
======================

This file is used to import all heat generators and to provide a registry for the heat generators.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""
from .aqvaheat_heat_pump import AqvaHeat
from .base_heat_generator import BaseHeatGenerator, BaseStrategy
from .base_heat_pumps import HeatPump
from .biomass_boiler import BiomassBoiler
from .chp import CHP
from .gas_boiler import GasBoiler
from .geothermal_heat_pump import Geothermal
from .power_to_heat import PowerToHeat
from .river_heat_pump import RiverHeatPump
from .solar_thermal import SolarThermal
from .thermal_storage import BufferStorage, ThermalStorageAdapter
from .waste_heat_pump import WasteHeatPump

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
    'Thermischer Netzspeicher': ThermalStorageAdapter,
}

# Lookup by Python class name (stored as tech_type in to_dict).
# Used for reliable deserialization without fragile prefix-matching.
TECH_CLASS_BY_TYPE = {cls.__name__: cls for cls in TECH_CLASS_REGISTRY.values()}
