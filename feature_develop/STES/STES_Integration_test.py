"""
Filename: STES_Integration_test.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-08
Description: This script demonstrates the integration of a stratified thermal energy storage (STES) into a district heating system.

"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from districtheatingsim.heat_generators.STES import TemperatureStratifiedThermalStorage
from generators import CHP, PowerToHeat

# Control strategy for CHP
class CHPStrategy:
    def __init__(self, storage, charge_on, charge_off):
        """
        Initializes the CHP strategy with switch points based on storage levels.

        Args:
            storage (TemperatureStratifiedThermalStorage): Instance of the storage.
            charge_on (int): (upper) Storage temperature to activate CHP.
            charge_off (int): (lower) Storage temperature to deactivate CHP.
        """
        self.storage = storage
        self.charge_on = charge_on
        self.charge_off = charge_off

    def decide_operation(self, current_state, upper_storage_temp, lower_storage_temp):
        """
        Decide whether to turn the CHP on or off based on storage temperature.

        current_state (bool): Current state of the CHP unit.
        upper_storage_temp (float): Current upper storage temperature.
        lower_storage_temp (float): Current lower storage temperature.

        If the lower storage temperature is too high, the CHP is turned off to prevent overheating.
        If the upper storage temperature is too low, the CHP is turned on to provide additional heat.

        """
        # Check if the CHP is currently on or off
        if current_state:
            # If the CHP is on, check if the lower storage temperature is too high
            if lower_storage_temp < self.charge_off:
                return True  # Keep CHP on
            else:
                return False  # Turn CHP off
        else:
            if upper_storage_temp > self.charge_on:
                return False  # Keep CHP off
            else:    
                return True  # Turn CHP on

# Control strategy for Power-to-Heat
class PowerToHeatStrategy:
    def __init__(self, storage, charge_on):
        """
        Initializes the Power-to-Heat strategy with a switch point based on storage levels.

        Args:
            storage (TemperatureStratifiedThermalStorage): Instance of the storage.
            charge_on (int): Storage temperature to activate Power-to-Heat unit.

        """
        self.storage = storage
        self.charge_on = charge_on

    def decide_operation(self, upper_storage_temp, remaining_demand):
        """
        Decide whether to turn the Power-to-Heat unit on based on storage temperature and remaining demand.

        upper_storage_temp (float): Current upper storage temperature.
        remaining_demand (float): Remaining heat demand to be covered.

        If the upper storage temperature is too low and there is still demand, the Power-to-Heat unit is turned on.

        """

        if upper_storage_temp < self.charge_on and remaining_demand > 0:
            return True  # Turn P2H on
        
class SystemController:
    def __init__(self, generators, storage, hours, energy_price_per_kWh):
        # Sort generators by priority (higher priority first)
        self.generators = sorted(generators, key=lambda gen: gen.priority, reverse=False)
        self.storage = storage
        self.hours = hours
        self.energy_price_per_kWh = energy_price_per_kWh
        self.results = {
            "storage_efficiency": 0,
            "storage_operational_costs": 0,
            "excess_heat": 0,
            "unmet_demand": 0,
            "stagnation_time": 0,
        }

        # Initialize each generator's operation
        for generator in self.generators:
            generator.init_operation(self.hours)

        self.Q_in_profile = np.zeros(self.hours)  # Heat input profile for each time step

    def run_simulation(self, Q_out_profile, T_Q_in_flow_profile, T_Q_out_return_profile):
        for t in range(self.hours):
            Q_out = Q_out_profile[t]
            T_Q_in_flow = T_Q_in_flow_profile[t]
            T_Q_out_return = T_Q_out_return_profile[t]
            remaining_demand = Q_out
            Q_in_total = 0  # Sum of heat input from all generators for this timestep

            # Calculate current storage temperatures
            current_storage_state, _, _ = self.storage.current_storage_state(t, T_Q_out_return, T_Q_in_flow)
            upper_storage_temp, lower_storage_temp = self.storage.current_storage_temperatures(t)

            # Iterate over prioritized generators
            for generator in self.generators:
                # Apply the generator's specific control strategy
                if generator.name.startswith("BHKW"):
                    new_state = generator.strategy.decide_operation(generator.BHKW_an, upper_storage_temp, lower_storage_temp)
                    generator_state = new_state
                    generator.BHKW_an = new_state
                elif generator.name.startswith("P2H"):
                    generator_state = generator.strategy.decide_operation(upper_storage_temp, remaining_demand)
                else:
                    generator_state = False  # Default to off if strategy is undefined

                # Operate the generator if the control strategy allows
                if generator_state:
                    Q_in, _ = generator.generate(t, remaining_demand)
                    remaining_demand -= Q_in  # Adjust remaining demand
                    Q_in_total += Q_in  # Accumulate total input for storage update

            # After evaluating all generators, update the storage with total Q_in
            self.storage.simulate_stratified_temperature_mass_flows(t, Q_in_total, Q_out, T_Q_in_flow, T_Q_out_return)

            remaining_demand -= self.storage.Q_net_storage_flow[t]  # Adjust remaining demand after storage output

            # Record the total Q_in for this timestep
            self.Q_in_profile[t] = Q_in_total

        # Calculate final results after the simulation
        self.calculate_final_results()

    def calculate_final_results(self):
        """
        Berechnet abschließende Effizienz und Betriebskosten des Systems.
        """
        self.storage.calculate_efficiency(self.Q_in_profile)
        self.storage.calculate_operational_costs(self.energy_price_per_kWh)
        self.results["storage_efficiency"] = self.storage.efficiency * 100
        self.results["storage_operational_costs"] = self.storage.operational_costs
        self.results["stagnation_time"] = self.storage.stagnation_time
        self.results["excess_heat"] = self.storage.excess_heat

        Gaspreis = 50 # €/MWh
        Holzpreis = 60 # €/MWh
        Strompreis = 100 # €/MWh
        q = 1.05 # Faktor für Kapitalrückzahlung
        r = 1.03 # Faktor für Preissteigerung
        T = 20 # Zeitraum in Jahren
        BEW = "Nein" # BEW-Betrachtung
        stundensatz = 45 # €/h

        for generator in self.generators:
            if isinstance(generator, CHP):
                self.bhkw_results = generator.calculate(Gaspreis, Holzpreis, Strompreis, q, r, T, BEW, stundensatz)
            if isinstance(generator, PowerToHeat):
                self.p2h_results = generator.calculate(Strompreis, q, r, T, BEW, stundensatz)

    def display_results(self):
        print(f"Speicherwirkungsgrad / -effizienz: {self.results['storage_efficiency']:.2f}%")
        print(f"Betriebskosten: {self.results['storage_operational_costs']:.2f} €")
        print(f"Überschüssige Wärme durch Stagnation: {self.results['excess_heat']:.2f} kWh")
        print(f"Nicht gedeckter Bedarf aufgrund von Speicherentleerung: {self.results['unmet_demand']:.2f} kWh")
        print(f"Stagnationsdauer: {self.results['stagnation_time']} h")
        for generator in self.generators:
            if isinstance(generator, CHP):
                print(f"Anzahl der Starts: {self.bhkw_results['Anzahl_Starts']}")
                print(f"Betriebsstunden: {self.bhkw_results['Betriebsstunden']}")
                print(f"Betriebsstunden pro Start: {self.bhkw_results['Betriebsstunden_pro_Start']:0.2f}")
                print(f"Wärmemenge: {self.bhkw_results['Wärmemenge']:.2f} MWh")
                print(f"Strommenge: {self.bhkw_results['Strommenge']:.2f} MWh")
                print(f"Brennstoffbedarf: {self.bhkw_results['Brennstoffbedarf']:.2f} MWh")
                print(f"Spezifische CO2-Emissionen: {self.bhkw_results['spec_co2_total']:.2f} tCO2/MWh")
                print(f"Primärenergie: {self.bhkw_results['primärenergie']:.2f} MWh")
                print(f"Wärmegestehungskosten: {self.bhkw_results['WGK']:.2f} €/MWh")

            if isinstance(generator, PowerToHeat):
                print(f"Betriebsstunden: {self.p2h_results['Betriebsstunden']:0.2f}")
                print(f"Wärmemenge: {self.p2h_results['Wärmemenge']:.2f} MWh")
                print(f"Spezifische CO2-Emissionen: {self.p2h_results['spec_co2_total']:.2f} tCO2/MWh")
                print(f"Primärenergie: {self.p2h_results['primärenergie']:.2f} MWh")
                print(f"Wärmegestehungskosten: {self.p2h_results['WGK']:.2f} €/MWh")

    def plot_results(self, Q_out_profile, T_Q_in_flow_profile, T_Q_out_return_profile):
        self.storage.plot_results(self.Q_in_profile, Q_out_profile, T_Q_in_flow_profile, T_Q_out_return_profile)

if __name__ == '__main__':
    # Speicher- und BHKW-Parameter
    params = {
        "storage_type": "truncated_trapezoid",
        "dimensions": (20, 20, 50, 50, 15),
        "rho": 1000,
        "cp": 4180,
        "T_ref": 10,
        "lambda_top": 0.04,
        "lambda_side": 0.03,
        "lambda_bottom": 0.05,
        "lambda_soil": 1.5,
        "dt_top": 0.3,
        "ds_side": 0.4,
        "db_bottom": 0.5,
        "T_amb": 10,
        "T_soil": 10,
        "T_max": 95,
        "T_min": 40,
        "initial_temp": 60,
        "hours": 8760,
        "num_layers": 5,
        "thermal_conductivity": 0.6
    }

    # Last- und Temperaturprofile laden
    file_path = os.path.abspath('feature_develop/STES/Lastgang.csv')
    df = pd.read_csv(file_path, delimiter=';', encoding='utf-8')
    Q_out_profile = df['Gesamtwärmebedarf_Gebäude_kW'].values
    T_Q_in_flow_profile = np.random.uniform(85, 85, params['hours'])
    T_Q_out_return_profile = np.random.uniform(50, 50, params['hours'])

    # Initializing generators with individual strategies
    chp = CHP("BHKW_1", th_Leistung_kW=500, priority=1)
    p2h = PowerToHeat("P2H_1", th_Leistung_kW=1000, priority=2)
    storage = TemperatureStratifiedThermalStorage(**params)

    # Assign individual strategies to generators
    chp.strategy = CHPStrategy(storage, charge_on=70, charge_off=70)
    p2h.strategy = PowerToHeatStrategy(storage, charge_on=70)

    # Controller für die Strategien erstellen
    controller = SystemController([chp, p2h], storage, hours=params['hours'], energy_price_per_kWh=0.10)

    # Simulationen ausführen und Ergebnisse anzeigen
    controller.run_simulation(Q_out_profile, T_Q_in_flow_profile, T_Q_out_return_profile)
    controller.display_results()

    # Ergebnisse plotten
    controller.plot_results(Q_out_profile, T_Q_in_flow_profile, T_Q_out_return_profile)

    plt.show()