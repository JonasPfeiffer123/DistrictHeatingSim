"""
DATE: 07.11.2024
AUTHOR: Dipl-Ing. (FH) Jonas Pfeiffer
FILENAME: STES_Integration_test.py

This script demonstrates the integration of a stratified thermal energy storage (STES) into a district heating system.

"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from STES import StratifiedThermalStorage

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
            available_energy_in_storage = np.sum([(self.T_sto[t] - T_Q_out_return) * self.layer_volume[i] * self.rho * self.cp / 3.6e6 for i in range(self.num_layers)])
            max_possible_energy = np.sum([(T_Q_in_flow - T_Q_out_return) * self.layer_volume[i] * self.rho * self.cp / 3.6e6 for i in range(self.num_layers)])

            if available_energy_in_storage >= max_possible_energy * 0.95:
                self.excess_heat += Q_in
                self.stagnation_time += 1
                Q_in = 0

            if available_energy_in_storage <= max_possible_energy * 0.05:
                self.unmet_demand += Q_out
                Q_out = 0

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

        self.T_Q_in_return[t] = self.T_sto_layers[t, 0]
        self.T_Q_out_flow[t] = self.T_sto_layers[t, -1]

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
        axs2.plot(self.T_Q_in_flow, label='Vorlauftemperatur Erzeuger (Eintritt)', linestyle='--', color='green')
        axs2.plot(self.T_Q_out_return, label='Rücklauftemperatur Verbraucher (Eintritt)', linestyle='--', color='orange')
        axs2.plot(self.T_Q_in_return, label='Rücklauftemperatur Erzeuger (Austritt)', linestyle='--', color='purple')
        axs2.plot(self.T_Q_out_flow, label='Vorlauftemperatur Verbraucher (Austritt)', linestyle='--', color='brown')
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

if __name__ == '__main__':
    # Parameters for storage setup
    params = {
        "storage_type": "truncated_trapezoid",  # Storage geometry
        "dimensions": (20, 20, 50, 50, 15),  # Top length, Top width, Bottom length, Bottom width, Height
        "rho": 1000,  # kg/m³ (density of water)
        "cp": 4180,  # J/kg*K (specific heat capacity of water)
        "T_ref": 10,  # °C reference temperature

        "lambda_top": 0.04,  # W/m*K for top insulation
        "lambda_side": 0.03,  # W/m*K for side insulation
        "lambda_bottom": 0.05,  # W/m*K for bottom insulation
        "lambda_soil": 1.5,  # W/m*K for soil thermal conductivity
        "dt_top": 0.3,  # m thickness of top insulation
        "ds_side": 0.4,  # m thickness of side insulation
        "db_bottom": 0.5,  # m thickness of bottom insulation

        "T_amb": 10,  # °C ambient temperature
        "T_soil": 10,  # °C soil temperature
        "T_max": 95,  # °C maximum storage temperature
        "T_min": 40,  # °C minimum storage temperature
        "initial_temp": 60,  # Initial storage temperature
        "hours": 8760,  # Number of hours in a year
        "num_layers": 5,  # Number of layers for stratified storage
        "thermal_conductivity": 0.6  # W/m*K thermal conductivity of the medium, here water
    }

    # Create instance of the storage class
    temperature_stratified_STES = TemperatureStratifiedThermalStorage(**params)

    # Load demand profile (Q_out) from a CSV file
    file_path = os.path.abspath('currently_not_used/STES/Lastgang.csv')
    df = pd.read_csv(file_path, delimiter=';', encoding='utf-8')
    Q_out_profile = df['Gesamtwärmebedarf_Gebäude_kW'].values  # Demand profile in kW

    # Simulated inputs for Q_in, T_Q_in_flow, T_Q_out_return (as hourly values)
    Q_in_profile = np.random.uniform(450, 455, params['hours'])  # Example heat input in kW
    T_Q_in_flow_profile = np.random.uniform(85, 85, params['hours'])  # Example input flow temperature in °C
    T_Q_out_return_profile = np.random.uniform(50, 50, params['hours'])  # Example output return temperature in °C

    # Energy cost parameters
    energy_price_per_kWh = 0.10  # €/kWh

    # Run simulation step-by-step
    for t in range(params['hours']):
        Q_in = Q_in_profile[t]
        Q_out = Q_out_profile[t]
        T_Q_in_flow = T_Q_in_flow_profile[t]
        T_Q_out_return = T_Q_out_return_profile[t]

        # Update storage for the current time step
        temperature_stratified_STES.simulate_stratified_temperature_mass_flows(t, Q_in, Q_out, T_Q_in_flow, T_Q_out_return)

    # Plot results
    temperature_stratified_STES.plot_results(Q_in_profile, Q_out_profile, T_Q_in_flow_profile, T_Q_out_return_profile)

    # Calculate and display operational costs and efficiency
    temperature_stratified_STES.calculate_operational_costs(energy_price_per_kWh)
    temperature_stratified_STES.calculate_efficiency(Q_in_profile)
    print(f"Speicherwirkungsgrad / -effizienz: {temperature_stratified_STES.efficiency * 100:.2f}%")
    print(f"Betriebskosten: {temperature_stratified_STES.operational_costs:.2f} €")
    print(f"Überschüssige Wärme durch Stagnation: {temperature_stratified_STES.excess_heat:.2f} kWh")
    print(f"Nicht gedeckter Bedarf aufgrund von Speicherentleerung: {temperature_stratified_STES.unmet_demand:.2f} kWh")
    print(f"Stagnationsdauer: {temperature_stratified_STES.stagnation_time} h")

    # Display plots
    plt.show()
