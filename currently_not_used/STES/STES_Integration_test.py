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

from STES import StratifiedThermalStorage
from generators import CHP, PowerToHeat

class TemperatureStratifiedThermalStorage(StratifiedThermalStorage):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.mass_flow_in = np.zeros(self.hours)  # kg/s Massenstrom (input)
        self.mass_flow_out = np.zeros(self.hours)  # kg/s Massenstrom (output)
        self.T_Q_in_flow = np.zeros(self.hours)  # Eingangstemperatur (input) Vorlauf Erzeuger
        self.T_Q_in_return = np.zeros(self.hours)  # Eingangstemperatur (input) Rücklauf Erzeuger
        self.T_Q_out_flow = np.zeros(self.hours)  # Ausgangstemperatur (output) Vorlauf Verbraucher
        self.T_Q_out_return = np.zeros(self.hours)  # Ausgangstemperatur (output) Rücklauf Verbraucher

        self.excess_heat = 0  # Überschüssige Wärme durch Stagnation
        self.unmet_demand = 0  # Nicht gedeckter Wärmebedarf
        self.stagnation_time = 0  # Zeit in Stunden, in der Überhitzung (Stagnation) auftritt

        self.storage_state = np.zeros(self.hours)  # Speicherzustand in Prozent des maximalen Ladezustands

    def simulate_stratified_temperature_mass_flows(self, t, Q_in, Q_out, T_Q_in_flow, T_Q_out_return):
        """
        Simulates stratified heat storage at a specific time step, considering mass flows and internal heat conduction between layers.
        t: Time step in hours.
        Q_in: Input heat in kW (e.g., from a solar thermal source)
        Q_out: Output heat in kW (e.g., to a district heating network)
        T_Q_in_flow: Input flow temperature (e.g., inlet temperature from the heat source)
        T_Q_out_return: Output return temperature (e.g., return temperature from the consumer)
        """

        T_Q_in_flow_copy = np.copy(T_Q_in_flow)
        T_Q_out_return_copy = np.copy(T_Q_out_return)
        Q_in_copy = np.copy(Q_in)
        Q_out_copy = np.copy(Q_out)

        self.Q_in = Q_in_copy  # Input heat in kW
        self.Q_out = Q_out_copy  # Output heat in kW
        self.T_Q_in_flow = T_Q_in_flow_copy  # Vorlauf-Erzeuger
        self.T_Q_out_return = T_Q_out_return_copy  # Rücklauf-Verbraucher
        
        if t == 0:
            self.T_sto_layers = np.full((self.hours, self.num_layers), self.T_sto[0])  # Initialisiere Schichttemperaturen
            self.Q_loss[t] = self.calculate_stratified_heat_loss(self.T_sto_layers[t])
            self.heat_stored_per_layer = self.layer_volume * self.rho * self.cp * (self.T_sto[0] - T_Q_out_return) / 3.6e6  # Wärme in jeder Schicht
            self.Q_sto[t] = sum(self.heat_stored_per_layer)  # Initial total stored heat in kWh

        else:
            # Berechnung der Wärmeverluste und Wärmeleitung zwischen den Schichten
            self.Q_loss[t] = self.calculate_stratified_heat_loss(self.T_sto_layers[t - 1])

            for i in range(self.num_layers):
                Q_loss_layer = self.Q_loss_layers[i]
                self.heat_stored_per_layer[i] -= Q_loss_layer / 3600
                delta_T = (Q_loss_layer * 3.6e6) / (self.layer_volume[i] * self.rho * self.cp)
                self.T_sto_layers[t, i] = self.T_sto_layers[t - 1, i] - delta_T

            for i in range(self.num_layers - 1):
                delta_T = self.T_sto_layers[t - 1, i] - self.T_sto_layers[t - 1, i + 1]
                heat_transfer = self.thermal_conductivity * self.S_side * delta_T / self.layer_thickness
                heat_transfer_kWh = heat_transfer / 3.6e6 * 3600

                self.heat_stored_per_layer[i] -= heat_transfer_kWh
                self.heat_stored_per_layer[i + 1] += heat_transfer_kWh

                delta_T_transfer = heat_transfer_kWh * 3.6e6 / (self.layer_volume[i] * self.rho * self.cp)
                self.T_sto_layers[t, i] -= delta_T_transfer
                self.T_sto_layers[t, i + 1] += delta_T_transfer

            # Update for energy storage state
            self.T_sto[t] = np.average(self.T_sto_layers[t])

            if T_Q_in_flow - self.T_sto_layers[t, 0] != 0:
                self.mass_flow_in[t] = (Q_in * 1000) / (self.cp * (T_Q_in_flow - self.T_sto_layers[t, -1]))
            else:
                self.mass_flow_in[t] = 0

            if self.T_sto_layers[t, -1] - T_Q_out_return != 0:
                self.mass_flow_out[t] = (Q_out * 1000) / (self.cp * (self.T_sto_layers[t, 0] - T_Q_out_return))
            else:
                self.mass_flow_out[t] = 0

            # Inflow from top to bottom
            for i in range(self.num_layers):
                mix_temp_K = ((self.mass_flow_in[t] * self.cp * (T_Q_in_flow + 273.15) * 3600) +
                              (self.layer_volume[i] * self.rho * self.cp * (self.T_sto_layers[t, i] + 273.15))) / \
                             ((self.mass_flow_in[t] * self.cp * 3600) + (self.layer_volume[i] * self.rho * self.cp))

                added_heat = self.mass_flow_in[t] * self.cp * (T_Q_in_flow - self.T_sto_layers[t, i]) * 3600
                self.heat_stored_per_layer[i] += added_heat / 3.6e6
                self.T_sto_layers[t, i] = mix_temp_K - 273.15
                T_Q_in_flow = self.T_sto_layers[t, i]

            # Outflow from bottom to top
            for i in range(self.num_layers - 1, -1, -1):
                mix_temp_K = ((self.mass_flow_out[t] * self.cp * (T_Q_out_return + 273.15) * 3600) +
                              (self.layer_volume[i] * self.rho * self.cp * (self.T_sto_layers[t, i] + 273.15))) / \
                             ((self.mass_flow_out[t] * self.cp * 3600) + (self.layer_volume[i] * self.rho * self.cp))

                removed_heat = self.mass_flow_out[t] * self.cp * (self.T_sto_layers[t, i] - T_Q_out_return) * 3600
                self.heat_stored_per_layer[i] -= removed_heat / 3.6e6
                self.T_sto_layers[t, i] = mix_temp_K - 273.15
                T_Q_out_return = self.T_sto_layers[t, i]

            self.Q_sto[t] = np.sum(self.heat_stored_per_layer)
            self.T_sto[t] = np.average(self.T_sto_layers[t])

        self.T_Q_in_return[t] = self.T_sto_layers[t, -1]
        self.T_Q_out_flow[t] = self.T_sto_layers[t, 0]

    def current_storage_state(self, t, T_Q_out_return, T_Q_in_flow):
        """
        Berechnet und gibt den aktuellen Ladezustand des Speichers als Anteil des maximalen Ladezustands zurück.
        
        Args:
            t (int): Aktueller Zeitschritt.
            T_Q_out_return (float): Rücklauftemperatur des Verbrauchers in °C.
            T_Q_in_flow (float): Vorlauftemperatur des Erzeugers in °C.

        Returns:
            float: Ladezustand in Prozent des maximalen Ladezustands (0–100).
        """
        if t == 0:
            T_sto = self.T_sto[t]
        else:
            T_sto = self.T_sto[t - 1]

        available_energy_in_storage = np.sum([(T_sto - T_Q_out_return) * self.layer_volume[i] * self.rho * self.cp / 3.6e6 
                                            for i in range(self.num_layers)])
        max_possible_energy = np.sum([(T_Q_in_flow - T_Q_out_return) * self.layer_volume[i] * self.rho * self.cp / 3.6e6 
                                    for i in range(self.num_layers)])
        
        self.storage_state[t] = (available_energy_in_storage / max_possible_energy) * 100
        
        # Ladezustand als Prozentwert zurückgeben (zwischen 0 und 100)
        return max(0, min(100, self.storage_state[t]))

    def plot_results(self, Q_in, Q_out, T_Q_in_flow, T_Q_out_return):
        fig = plt.figure(figsize=(16, 10))
        axs1 = fig.add_subplot(2, 3, 1)
        axs2 = fig.add_subplot(2, 3, 2)
        axs3 = fig.add_subplot(2, 3, 3)
        axs4 = fig.add_subplot(2, 3, 4)
        axs5 = fig.add_subplot(2, 3, 5)
        axs6 = fig.add_subplot(2, 3, 6, projection='3d')

        # Q_in and Q_out
        axs1.plot(Q_in, label='Wärmeerzeugung', color='red')
        axs1.plot(Q_out, label='Wärmeverbrauch', color='blue')
        axs1.set_ylabel('Wärme (kW)')
        axs1.set_title('Wärmeerzeugung und Wärmeverbrauch im Zeitverlauf')
        axs1.legend()

        # Plot storage temperature
        axs2.plot(self.T_sto, label='Speichertemperatur')
        axs2.plot(T_Q_in_flow, label='Vorlauftemperatur Erzeuger (Eintritt)', linestyle='--', color='green')
        axs2.plot(T_Q_out_return, label='Rücklauftemperatur Verbraucher (Eintritt)', linestyle='--', color='orange')
        axs2.plot(self.T_Q_in_return, label='Rücklauftemperatur Erzeuger (Austritt)', linestyle='--', color='purple')
        axs2.plot(self.T_Q_out_flow, label='Vorlauftemperatur Verbraucher (Austritt)', linestyle='--', color='brown')
        axs2.plot(self.storage_state, label='Speicherzustand', linestyle='--', color='black')
        axs2.set_ylabel('Temperatur (°C)')
        axs2.set_title(f'Systemtemperaturen im Zeitverlauf')
        axs2.legend()

        # Plot heat loss
        axs3.plot(self.Q_loss, label='Wärmeverlust', color='orange')
        axs3.set_ylabel('Wärmeverlust (kW)')
        axs3.set_title('Wärmeverlust im Zeitverlauf')
        axs3.legend()

        # Plot stored heat
        axs4.plot(self.Q_sto, label='Gespeicherte Wärme', color='green')
        axs4.set_ylabel('Gespeicherte Wärme (kWh)')
        axs4.set_title('Gespeicherte Wärme im Zeitverlauf')
        axs4.legend()

        # Plot stratified storage temperatures
        for i in range(self.T_sto_layers.shape[1]):
            axs5.plot(self.T_sto_layers[:, i], label=f'Layer {i+1}')
        axs5.set_xlabel('Zeit (Stunden)')
        axs5.set_ylabel('Temperatur (°C)')
        axs5.set_title('Temperaturen der Schichten im Speicher')
        axs5.legend()

        # Plot 3D geometry
        self.plot_3d_temperature_distribution(axs6, 6000)

        plt.tight_layout()

# Control strategy for CHP
class CHPStrategy:
    def __init__(self, storage, charge_on, charge_off):
        """
        Initializes the CHP strategy with switch points based on storage levels.

        Args:
            storage (TemperatureStratifiedThermalStorage): Instance of the storage.
            charge_on (int): Storage percentage to activate CHP.
            charge_off (int): Storage percentage to deactivate CHP.
        """
        self.storage = storage
        self.charge_on = charge_on
        self.charge_off = charge_off

    def decide_operation(self, storage_percentage):
        """
        Decide whether to turn the CHP on or off based on storage levels.
        """
        if storage_percentage <= self.charge_on:
            return True  # Turn CHP on
        elif storage_percentage >= self.charge_off:
            return False  # Turn CHP off
        return None  # No change

# Control strategy for Power-to-Heat
class PowerToHeatStrategy:
    def __init__(self, storage, charge_on):
        """
        Initializes the Power-to-Heat strategy, which operates based on remaining demand.
        
        Args:
            storage (TemperatureStratifiedThermalStorage): Instance of the storage.
        """
        self.storage = storage
        self.charge_on = charge_on

    def decide_operation(self, storage_percentage):
        """
        Decide operation based on remaining demand after other generators have operated.
        
        Args:
            remaining_demand (float): Heat demand left after the CHP unit's operation.
        
        Returns:
            bool: True if there is remaining demand to meet, False otherwise.
        """
        if storage_percentage <= self.charge_on:
            return True  # Turn CHP on
        
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

            # Calculate current storage capacity
            storage_percentage = self.storage.current_storage_state(t, T_Q_out_return, T_Q_in_flow)

            # Iterate over prioritized generators
            for generator in self.generators:
                if remaining_demand <= 0:
                    break

                # Apply the generator's specific control strategy
                if generator.name.startswith("BHKW"):
                    new_state = generator.strategy.decide_operation(storage_percentage)
                    if new_state is not None:
                        generator.BHKW_an = new_state
                        generator_state = new_state
                    else:
                        generator_state = generator.BHKW_an
                elif generator.name.startswith("P2H"):
                    generator_state = generator.strategy.decide_operation(storage_percentage)
                else:
                    generator_state = False  # Default to off if strategy is undefined

                #print(f"Generator {generator.name} operating: {generator_state}")

                # Operate the generator if the control strategy allows
                if generator_state:
                    Q_in, _ = generator.generate(t, remaining_demand)
                    remaining_demand -= Q_in  # Adjust remaining demand
                    Q_in_total += Q_in  # Accumulate total input for storage update

            # After evaluating all generators, update the storage with total Q_in
            if Q_in_total > 0:
                self.storage.simulate_stratified_temperature_mass_flows(
                    t, Q_in_total, Q_out, T_Q_in_flow, T_Q_out_return
                )

            # Record the total Q_in for this timestep
            self.Q_in_profile[t] = Q_in_total

            # If there's unmet demand after all generators have been evaluated, record it
            if remaining_demand > 0:
                self.results["unmet_demand"] += remaining_demand

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
    file_path = os.path.abspath('currently_not_used/STES/Lastgang.csv')
    df = pd.read_csv(file_path, delimiter=';', encoding='utf-8')
    Q_out_profile = df['Gesamtwärmebedarf_Gebäude_kW'].values
    T_Q_in_flow_profile = np.random.uniform(85, 85, params['hours'])
    T_Q_out_return_profile = np.random.uniform(50, 50, params['hours'])

    # Initializing generators with individual strategies
    chp = CHP("BHKW_1", th_Leistung_kW=1000, priority=1)
    p2h = PowerToHeat("P2H_1", th_Leistung_kW=1000, priority=2)
    storage = TemperatureStratifiedThermalStorage(**params)

    # Assign individual strategies to generators
    chp.strategy = CHPStrategy(storage, charge_on=20, charge_off=90)
    p2h.strategy = PowerToHeatStrategy(storage, charge_on=20)

    # Controller für die Strategien erstellen
    controller = SystemController([chp, p2h], storage, hours=params['hours'], energy_price_per_kWh=0.10)

    # Simulationen ausführen und Ergebnisse anzeigen
    controller.run_simulation(Q_out_profile, T_Q_in_flow_profile, T_Q_out_return_profile)
    controller.display_results()

    # Ergebnisse plotten
    controller.plot_results(Q_out_profile, T_Q_in_flow_profile, T_Q_out_return_profile)

    plt.show()