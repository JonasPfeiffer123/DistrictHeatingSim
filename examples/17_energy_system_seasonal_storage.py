import numpy as np
from districtheatingsim.heat_generators.energy_system import EnergySystem
from districtheatingsim.heat_generators.chp import CHP, CHPStrategy
from districtheatingsim.heat_generators.gas_boiler import GasBoiler, GasBoilerStrategy
from districtheatingsim.heat_generators.power_to_heat import PowerToHeat, PowerToHeatStrategy
from districtheatingsim.heat_generators.biomass_boiler import BiomassBoiler, BiomassBoilerStrategy
from districtheatingsim.heat_generators.base_heat_pumps import HeatPumpStrategy
from districtheatingsim.heat_generators.river_heat_pump import RiverHeatPump
from districtheatingsim.heat_generators.waste_heat_pump import WasteHeatPump
from districtheatingsim.heat_generators.geothermal_heat_pump import Geothermal
from districtheatingsim.heat_generators.solar_thermal import SolarThermal, SolarThermalStrategy
from districtheatingsim.heat_generators.STES import STES
from districtheatingsim.heat_generators.simple_thermal_storage import SimpleThermalStorage

from districtheatingsim.utilities.test_reference_year import import_TRY

from matplotlib import pyplot as plt

import pandas as pd
import os

# Testparameter
time_steps = pd.date_range(start="2023-01-01", end="2023-12-31 23:00:00", freq="h").to_numpy()

file_path = os.path.abspath('examples/data/Lastgang/Lastgang.csv')

df = pd.read_csv(file_path, delimiter=';', encoding='utf-8')
load_profile = df['Gesamtwärmebedarf_Gebäude_kW'].values
VLT_L = np.random.uniform(85, 85, 8760)
RLT_L = np.random.uniform(50, 50, 8760)

TRY_filename = os.path.abspath('examples/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat')
TRY_data = import_TRY(TRY_filename)

COP_filename = os.path.abspath('examples/data/COP/Kennlinien WP.csv')
COP_data = np.genfromtxt(COP_filename, delimiter=';')

economic_parameters = {"gas_price": 50, "wood_price": 40, "electricity_price": 120, "capital_interest_rate": 0.05, 
                       "inflation_rate": 0.03, "time_period": 20, "subsidy_eligibility": "Nein", "hourly_rate": 45}  # Wirtschaftsparameter

# Speicherparameter
storage_params = {
    "storage_type": "truncated_trapezoid",  # Speichergeometrie
    "dimensions": (20, 20, 50, 50, 15),  # Geometrieparameter
    "rho": 1000,  # Dichte des Mediums (kg/m³)
    "cp": 4180,  # Spezifische Wärmekapazität (J/kg*K)
    "T_ref": 10,  # Referenztemperatur (°C)
    "lambda_top": 0.04,  # Wärmeleitfähigkeit der oberen Isolierung (W/m*K)
    "lambda_side": 0.03,  # Wärmeleitfähigkeit der seitlichen Isolierung (W/m*K)
    "lambda_bottom": 0.05,  # Wärmeleitfähigkeit der unteren Isolierung (W/m*K)
    "lambda_soil": 1.5,  # Wärmeleitfähigkeit des Bodens (W/m*K)
    "dt_top": 0.3,  # Dicke der oberen Isolierung (m)
    "ds_side": 0.4,  # Dicke der seitlichen Isolierung (m)
    "db_bottom": 0.5,  # Dicke der unteren Isolierung (m)
    "T_amb": 10,  # Umgebungstemperatur (°C)
    "T_soil": 10,  # Bodentemperatur (°C)
    "T_max": 95,  # Maximale Speichertemperatur (°C)
    "T_min": 40,  # Minimale Speichertemperatur (°C)
    "initial_temp": 60,  # Anfangstemperatur des Speichers (°C)
    "hours": 8760,  # Anzahl der Stunden in einem Jahr
    "num_layers": 5,  # Anzahl der Schichten für die Schichtung
    "thermal_conductivity": 0.6  # Wärmeleitfähigkeit des Mediums (W/m*K)
}

# Initialisiere das Energiesystem
energy_system = EnergySystem(time_steps, load_profile, VLT_L, RLT_L, TRY_data, COP_data, economic_parameters)

# Initialisiere den Speicher
storage = STES(name="Saisonalspeicher", **storage_params)
energy_system.add_storage(storage)

# Füge Generatoren hinzu
chp = CHP("BHKW_1", th_Leistung_kW=500)
energy_system.add_technology(chp)
chp.strategy = CHPStrategy(charge_on=75, charge_off=70)

#pth = PowerToHeat("PtH_1", thermal_capacity_kW=500)
#energy_system.add_technology(pth)
#pth.strategy = PowerToHeatStrategy(charge_on=75)

# Biomasssboiler hinzufügen
#biomass_boiler = BiomassBoiler("Biomassekessel_1", thermal_capacity_kW=500)
#energy_system.add_technology(biomass_boiler)
#biomass_boiler.strategy = BiomassBoilerStrategy(charge_on=75, charge_off=70)

# Gasboiler hinzufügen
#gas_boiler = GasBoiler("Gasboiler_1", thermal_capacity_kW=1000)
#energy_system.add_technology(gas_boiler)
#gas_boiler.strategy = GasBoilerStrategy(charge_on=70)

# Erneuerbare Energien hinzufügen
#river_heat_pump = RiverHeatPump("Flusswärmepumpe_1", Wärmeleistung_FW_WP=600, Temperatur_FW_WP=20)
#energy_system.add_technology(river_heat_pump)
#river_heat_pump.strategy = HeatPumpStrategy(charge_on=75, charge_off=70)

#waste_heat_pump = WasteHeatPump("Abwärmepumpe_1", Kühlleistung_Abwärme=600, Temperatur_Abwärme=20)
#energy_system.add_technology(waste_heat_pump)
#waste_heat_pump.strategy = HeatPumpStrategy(charge_on=75, charge_off=70)

#waste_water_heat_pump = WasteHeatPump("Abwasserwärmepumpe_1", Kühlleistung_Abwärme=200, Temperatur_Abwärme=20)
#energy_system.add_technology(waste_water_heat_pump)
#waste_water_heat_pump.strategy = HeatPumpStrategy(charge_on=75, charge_off=70)

#geothermal_heat_pump = Geothermal("Geothermie_1", Fläche=10000, Bohrtiefe=100, Temperatur_Geothermie=20)
#energy_system.add_technology(geothermal_heat_pump)
#geothermal_heat_pump.strategy = HeatPumpStrategy(charge_on=75, charge_off=70)

#solar_thermal = SolarThermal("Solarthermie_1", bruttofläche_STA=2500, vs=50, Typ="Vakuumröhrenkollektor")
#energy_system.add_technology(solar_thermal)
#solar_thermal.strategy = SolarThermalStrategy(charge_on=75, charge_off=70)


# Berechne den Energiemix mit Speicher
results = energy_system.calculate_mix()

# Ergebnisse anzeigen
print("Simulationsergebnisse:")
print(f"Speicherwirkungsgrad: {results['storage_class'].efficiency*100:.2f}%")
print(f"Überschüssige Wärme durch Stagnation: {results['storage_class'].excess_heat:.2f} kWh")
print(f"Nicht gedeckter Bedarf aufgrund von Speicherentleerung: {results['storage_class'].unmet_demand:.2f} kWh")
print(f"Stagnationsdauer: {results['storage_class'].stagnation_time} h")

# Ergebnisse plotten
results['storage_class'].plot_results(results["Wärmeleistung_L"][0], load_profile, VLT_L, RLT_L)
energy_system.plot_stack_plot()
energy_system.plot_pie_chart()
plt.show()