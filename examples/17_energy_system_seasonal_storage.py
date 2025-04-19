import numpy as np
from districtheatingsim.heat_generators.energy_system import EnergySystem
from districtheatingsim.heat_generators.chp import CHP, CHPStrategy
from districtheatingsim.heat_generators.gas_boiler import GasBoiler, GasBoilerStrategy
from districtheatingsim.heat_generators.power_to_heat import PowerToHeat, PowerToHeatStrategy
from districtheatingsim.heat_generators.biomass_boiler import BiomassBoiler, BiomassBoilerStrategy
from districtheatingsim.heat_generators.heat_pumps import RiverHeatPump, WasteHeatPump, Geothermal, HeatPumpStrategy
from districtheatingsim.heat_generators.STES import TemperatureStratifiedThermalStorage

from matplotlib import pyplot as plt

import pandas as pd
import os

# Testparameter
time_steps = pd.date_range(start="2023-01-01", end="2023-12-31 23:00:00", freq="h").to_numpy()

file_path = os.path.abspath('feature_develop/STES/Lastgang.csv')
df = pd.read_csv(file_path, delimiter=';', encoding='utf-8')
load_profile = df['Gesamtwärmebedarf_Gebäude_kW'].values
VLT_L = np.random.uniform(85, 85, 8760)
RLT_L = np.random.uniform(50, 50, 8760)
TRY_data = np.zeros(len(time_steps))  # Dummy-Daten für Test Reference Year
COP_data = np.zeros(len(time_steps))  # Dummy-Daten für COP
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
storage = TemperatureStratifiedThermalStorage(name="Saisonalspeicher", **storage_params)
energy_system.add_storage(storage)

# Füge Generatoren hinzu
chp = CHP("BHKW_1", th_Leistung_BHKW=300)
energy_system.add_technology(chp)
chp.strategy = CHPStrategy(storage, charge_on=75, charge_off=75)

#pth = PowerToHeat("PtH_1")
#energy_system.add_technology(pth)
#pth.strategy = PowerToHeatStrategy(storage, charge_on=60)

# Biomasssboiler hinzufügen
biomass_boiler = BiomassBoiler("Biomassekessel_1", thermal_capacity_kW=500)
energy_system.add_technology(biomass_boiler)
biomass_boiler.strategy = BiomassBoilerStrategy(storage, charge_on=70, charge_off=70)

# Gasboiler hinzufügen
#gas_boiler = GasBoiler("Gasboiler_1")
#energy_system.add_technology(gas_boiler)
#gas_boiler.strategy = GasBoilerStrategy(storage, charge_on=60)

# Erneuerbare Energien hinzufügen
#river_heat_pump = RiverHeatPump("Flusswärmepumpe_1")
#energy_system.add_technology(river_heat_pump)
#river_heat_pump.strategy = HeatPumpStrategy(storage, charge_on=60, charge_off=60)

#waste_heat_pump = WasteHeatPump("Abwärmepumpe_1")
#energy_system.add_technology(waste_heat_pump)
#waste_heat_pump.strategy = HeatPumpStrategy(storage, charge_on=60, charge_off=60)

#geothermal_heat_pump = Geothermal("Geothermie_1")
#energy_system.add_technology(geothermal_heat_pump)
#geothermal_heat_pump.strategy = HeatPumpStrategy(storage, charge_on=60, charge_off=60)

# Berechne den Energiemix mit Speicher
results = energy_system.calculate_mix()

# Ergebnisse anzeigen
print("Simulationsergebnisse:")
print(f"Speicherwirkungsgrad: {results['storage_class'].efficiency*100:.2f}%")
print(f"Betriebskosten: {results['storage_class'].operational_costs:.2f} €")
print(f"Überschüssige Wärme durch Stagnation: {results['storage_class'].excess_heat:.2f} kWh")
print(f"Nicht gedeckter Bedarf aufgrund von Speicherentleerung: {results['storage_class'].unmet_demand:.2f} kWh")
print(f"Stagnationsdauer: {results['storage_class'].stagnation_time} h")


# Ergebnisse plotten
print(results["Wärmeleistung_L"])
results['storage_class'].plot_results(results["Wärmeleistung_L"][0]+results["Wärmeleistung_L"][1], load_profile, VLT_L, RLT_L)
energy_system.plot_stack_plot()
energy_system.plot_pie_chart()
plt.show()