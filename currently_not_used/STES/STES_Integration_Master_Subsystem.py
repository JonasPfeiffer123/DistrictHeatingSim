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
from annuity import annuität

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

        # Variable for net flow, positive for charge, negative for discharge
        self.Q_net_storage_flow = np.zeros(self.hours)

        self.T_max_rücklauf = 70  # Maximale Rücklauftemperatur für Erzeuger
        self.T_min_vorlauf = 70  # Minimale Vorlauftemperatur für Verbraucher

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

            """
            # when the storage is full, the inflow is zero
            if self.T_sto_layers[t, -1] < self.T_max_rücklauf:
                # Ladeoperation möglich
                self.mass_flow_in[t] = (Q_in * 1000) / (self.cp * (T_Q_in_flow - self.T_sto_layers[t, -1]))
            else:
                # Speicherüberhitzung oder keine ausreichende Temperaturdifferenz
                self.mass_flow_in[t] = 0
                self.excess_heat += Q_in
                self.stagnation_time += 1
                self.Q_in = 0

            # when the storage is empty, the outflow is zero
            if self.T_sto_layers[t, 0] > self.T_min_vorlauf:
                # Entladeoperation möglich
                self.mass_flow_out[t] = (Q_out * 1000) / (self.cp * (self.T_sto_layers[t, 0] - T_Q_out_return))
            else:
                # Speicher zu kalt oder keine ausreichende Temperaturdifferenz
                self.mass_flow_out[t] = 0
                self.unmet_demand += Q_out
                self.Q_out = 0
            """

            self.mass_flow_in[t] = (Q_in * 1000) / (self.cp * (T_Q_in_flow - self.T_sto_layers[t, -1]))
            self.mass_flow_out[t] = (Q_out * 1000) / (self.cp * (self.T_sto_layers[t, 0] - T_Q_out_return))

            # Berechne den Netto-Wärmefluss als Differenz zwischen ein- und ausströmender Wärme
            self.Q_net_storage_flow[t] = Q_out - Q_in

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
        return max(0, min(100, self.storage_state[t])), available_energy_in_storage, max_possible_energy
    
    def current_storage_temperatures(self, t):
        """
        Gibt die aktuelle Temperatur des Speichers an den Enden zurück.

        Args:
            t (int): Aktueller Zeitschritt.

        Returns:
            tuple: Vorlauf- und Rücklauftemperatur des Speichers.

        """

        if t == 0:
            return self.T_sto[t], self.T_sto[t]
        else:
            return self.T_sto_layers[t-1, 0], self.T_sto_layers[t-1, -1]

    def plot_results(self, Q_in, Q_out, T_Q_in_flow, T_Q_out_return):
        fig = plt.figure(figsize=(16, 10))
        axs1 = fig.add_subplot(2, 3, 1)
        axs2 = fig.add_subplot(2, 3, 2)
        axs3 = fig.add_subplot(2, 3, 3)
        axs4 = fig.add_subplot(2, 3, 4)
        axs5 = fig.add_subplot(2, 3, 5)
        axs6 = fig.add_subplot(2, 3, 6, projection='3d')

        # plot Wärmeerzeugung as line plot
        axs1.plot(Q_out, label='Wärmeverbrauch', color='blue', linewidth=0.5)
        # plot Wärmeverbrauch and storage net flow as stackplot
        axs1.stackplot(range(self.hours), Q_in, self.Q_net_storage_flow, labels=['Wärmeerzeugung', 'Netto-Speicherfluss'], colors=['red', 'purple'])
        axs1.set_ylabel('Wärme (kW)')
        axs1.set_title('Wärmeerzeugung, -verbrauch und Speicher-Nettofluss')
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

    def calculate_costs(self, Wärmemenge_MWh, Investitionskosten, Nutzungsdauer, f_Inst, f_W_Insp, Bedienaufwand, q, r, T, Energiebedarf, Energiekosten, E1, stundensatz):
        """
        Berechnet den Anteil der Wärmegestehungskosten für den Speicher.
        """
        self.Wärmemenge_MWh = Wärmemenge_MWh
        self.Investitionskosten = Investitionskosten
        self.Nutzungsdauer = Nutzungsdauer
        self.f_Inst = f_Inst
        self.f_W_Insp = f_W_Insp
        self.Bedienaufwand = Bedienaufwand
        self.q = q
        self.r = r
        self.T = T
        self.Energiebedarf = Energiebedarf
        self.Energiekosten = Energiekosten
        self.E1 = E1
        self.stundensatz = stundensatz

        self.A_N = annuität(self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, q, r, T, Energiebedarf, Energiekosten, E1, stundensatz)

        self.WGK = self.A_N / self.Wärmemenge_MWh

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
        if upper_storage_temp != None:
            if upper_storage_temp < self.charge_on and remaining_demand > 0:
                return True  # Turn P2H on
        else:
            if remaining_demand > 0:
                return True  # Turn P2H on
            
class SubsystemController:
    def __init__(self, generators, hours, storage=None):
        self.generators = sorted(generators, key=lambda gen: gen.priority)
        self.storage = storage
        self.Q_in_profile = np.zeros(hours)  # Heat input profile for each time step

        for generator in self.generators:
            generator.init_operation(hours if storage else 8760)

    def run_subsystem_simulation(self, t, Q_out, T_Q_in_flow, T_Q_out_return, remaining_demand):
        Q_in_total = 0

        if self.storage:
            upper_storage_temp, lower_storage_temp = self.storage.current_storage_temperatures(t)

            # Iterate over prioritized generators in this subsystem
            for generator in self.generators:
                if generator.name.startswith("BHKW"):
                    new_state = generator.strategy.decide_operation(
                        generator.BHKW_an, upper_storage_temp, lower_storage_temp
                    )
                    generator_state = new_state
                    generator.BHKW_an = new_state
                elif generator.name.startswith("P2H"):
                    generator_state = generator.strategy.decide_operation(upper_storage_temp, remaining_demand)
                else:
                    generator_state = False

                if generator_state:
                    Q_in, _ = generator.generate(t, remaining_demand)
                    remaining_demand -= Q_in
                    Q_in_total += Q_in

            self.storage.simulate_stratified_temperature_mass_flows(t, Q_in_total, Q_out, T_Q_in_flow, T_Q_out_return)
            remaining_demand -= self.storage.Q_net_storage_flow[t]
            self.Q_in_profile[t] = Q_in_total  # Record the Q_in total

        else:
            # Run the simulation for non-storage systems (direct demand coverage)
            for generator in self.generators:
                if generator_state := generator.strategy.decide_operation(None, remaining_demand):
                    Q_in, _ = generator.generate(t, remaining_demand)
                    remaining_demand -= Q_in
                    self.Q_in_profile[t] = Q_in_total  # Record the Q_in total

        return remaining_demand


class MasterSystemController:
    def __init__(self, subsystems, hours, energy_price_per_kWh):
        self.subsystems = subsystems
        self.hours = hours
        self.energy_price_per_kWh = energy_price_per_kWh
        self.results = {"storage_efficiency": 0, "storage_operational_costs": 0}

    def run_system_simulation(self, Q_out_profile, T_Q_in_flow_profile, T_Q_out_return_profile):
        for t in range(self.hours):
            Q_out = Q_out_profile[t]
            T_Q_in_flow = T_Q_in_flow_profile[t]
            T_Q_out_return = T_Q_out_return_profile[t]
            remaining_demand = Q_out

            for subsystem in self.subsystems:
                remaining_demand = subsystem.run_subsystem_simulation(
                    t, Q_out, T_Q_in_flow, T_Q_out_return, remaining_demand
                )

    def calculate_final_results(self):
        for subsystem in self.subsystems:
            if subsystem.storage:
                subsystem.storage.calculate_efficiency(subsystem.Q_in_profile)
                subsystem.storage.calculate_operational_costs(self.energy_price_per_kWh)
                self.results["storage_efficiency"] += subsystem.storage.efficiency * 100
                self.results["storage_operational_costs"] += subsystem.storage.operational_costs

    def display_results(self):
        print(f"Speicherwirkungsgrad / -effizienz: {self.results['storage_efficiency']:.2f}%")
        print(f"Betriebskosten: {self.results['storage_operational_costs']:.2f} €")

    def plot_results(self):
        for subsystem in self.subsystems:
            if subsystem.storage:
                subsystem.storage.plot_results(subsystem.Q_in_profile, subsystem.storage.Q_out, subsystem.storage.T_Q_in_flow, subsystem.storage.T_Q_out_return)


# Beispiel-Aufruf

if __name__ == "__main__":
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

    file_path = os.path.abspath('currently_not_used/STES/Lastgang.csv')
    df = pd.read_csv(file_path, delimiter=';', encoding='utf-8')
    Q_out_profile = df['Gesamtwärmebedarf_Gebäude_kW'].values
    T_Q_in_flow_profile = np.random.uniform(85, 85, params['hours'])
    T_Q_out_return_profile = np.random.uniform(50, 50, params['hours'])

    # Initialisierung von Erzeugern und Speichern
    chp = CHP("BHKW_1", th_Leistung_kW=500, priority=1)
    p2h = PowerToHeat("P2H_1", th_Leistung_kW=1000, priority=2)
    storage = TemperatureStratifiedThermalStorage(**params)

    p2h_stand_alone = PowerToHeat("P2H_2", th_Leistung_kW=500, priority=3)

    # Strategie-Zuweisung
    chp.strategy = CHPStrategy(storage, charge_on=70, charge_off=70)
    p2h.strategy = PowerToHeatStrategy(storage, charge_on=70)
    p2h_stand_alone.strategy = PowerToHeatStrategy(None, charge_on=70)

    # Subsysteme erstellen
    subsystem1 = SubsystemController([chp, p2h], params["hours"], storage)
    subsystem2 = SubsystemController([p2h_stand_alone], params["hours"])  # Kein Speicher

    # Master-Systemcontroller erstellen und Simulation ausführen
    master_controller = MasterSystemController([subsystem1, subsystem2], hours=params['hours'], energy_price_per_kWh=0.10)
    master_controller.run_system_simulation(Q_out_profile, T_Q_in_flow_profile, T_Q_out_return_profile)
    master_controller.calculate_final_results()
    master_controller.display_results()
    master_controller.plot_results()
    plt.show()