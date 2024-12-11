from .chp import CHP
from .heat_pumps import RiverHeatPump, WasteHeatPump, Geothermal, AqvaHeat
from .biomass_boiler import BiomassBoiler
from .gas_boiler import GasBoiler
from .power_to_heat import PowerToHeat
from .solar_thermal import SolarThermal

TECH_CLASS_REGISTRY = {
    'BHKW': CHP,
    'Flusswasser': RiverHeatPump,
    'Abwärme': WasteHeatPump,
    'Geothermie': Geothermal,
    'Biomassekessel': BiomassBoiler,
    'Gaskessel': GasBoiler,
    'Solarthermie': SolarThermal,
    'AqvaHeat': AqvaHeat,
    'PowerToHeat': PowerToHeat
}
