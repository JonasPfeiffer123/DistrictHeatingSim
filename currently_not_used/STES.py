# Calculation modell for STES (Seasonal Thermal Energy Storage) systems
"""
DATE: 02.10.2024
AUTHOR: Dipl-Ing. (FH) Jonas Pfeiffer
FILENAME: STES.py

Calculation model for STES (Seasonal Thermal Energy Storage) systems.

Calculation model source:
Simulation method for assessing hourly energy flows in district heating system with seasonal thermal energy storage
Authors: Kapil Narula, Fleury de Oliveira Filho, Willy Villasmil, Martin K. Patel
Link: https://www.sciencedirect.com/science/article/pii/S0960148119318154?via%3Dihub
"""

import numpy as np
import matplotlib.pyplot as plt

class ThermalStorage:
    def __init__(self, storage_type, volume, rho, cp, T_ref, U_top, U_side, U_bottom, 
                 S_top, S_side, S_bottom, T_amb, T_soil, T_max, T_min, initial_temp, hours=8760):
        self.storage_type = storage_type # Choose between "cylindrical" or "pit"
        self.volume = volume # m³
        self.rho = rho # kg/m³ (density of water)
        self.cp = cp # J/kg*K (specific heat capacity of water)
        self.T_ref = T_ref # °C reference temperature
        self.U_top = U_top # W/m²K U-value for top insulation
        self.U_side = U_side # W/m²K U-value for side insulation
        self.U_bottom = U_bottom # W/m²K U-value for bottom insulation
        self.S_top = S_top # Surface area of top in m²
        self.S_side = S_side # Surface area of sides in m²
        self.S_bottom = S_bottom # Surface area of bottom in m²
        self.T_amb = T_amb # °C ambient temperature
        self.T_soil = T_soil # °C soil temperature
        self.T_max = T_max # °C maximum storage temperature
        self.T_min = T_min # °C minimum storage temperature
        self.hours = hours # Number of hours in a year
        self.Q_sto = np.zeros(hours) # Stored heat in J
        self.T_sto = np.zeros(hours) # Storage temperature in °C
        self.T_sto[0] = initial_temp # Initial storage temperature in °C
        
    def calculate_heat_loss(self, T_sto_last):
        # Calculate heat losses based on storage type and geometries
        if self.storage_type == "cylindrical":
            Q_loss_top = self.U_top * self.S_top * (T_sto_last - self.T_amb) # Heat loss from top in W
            Q_loss_side = self.U_side * self.S_side * (T_sto_last - self.T_soil) # Heat loss from sides in W
            Q_loss_bottom = self.U_bottom * self.S_bottom * (T_sto_last - self.T_soil) # Heat loss from bottom in W
        elif self.storage_type == "pit":
            Q_loss_top = self.U_top * self.S_top * (T_sto_last - self.T_amb) # Heat loss from top in W
            Q_loss_side = self.U_side * self.S_side * (T_sto_last - self.T_soil) # Heat loss from sides in W
            Q_loss_bottom = self.U_bottom * self.S_bottom * (T_sto_last - self.T_soil) # Heat loss from bottom in W
        else:
            raise ValueError("Unsupported storage type")
        
        return Q_loss_top + Q_loss_side + Q_loss_bottom # Total heat loss in W

    def simulate(self, Q_in, Q_out):
        for t in range(1, self.hours):
            # Calculate heat loss for the hour
            self.Q_loss = self.calculate_heat_loss(self.T_sto[t-1]) # Heat loss in W

            # Energy balance
            self.Q_sto[t] = self.Q_sto[t-1] + (Q_in[t] - Q_out[t] - self.Q_loss) * 3600 # Stored heat in J others in W --> J = W * s for 1 hour (3600 s)

            # Update storage temperature
            self.T_sto[t] = self.Q_sto[t] / (self.volume * self.rho * self.cp) + self.T_ref

            # Limit temperature within max and min bounds
            if self.T_sto[t] > self.T_max:
                self.T_sto[t] = self.T_max
            elif self.T_sto[t] < self.T_min:
                self.T_sto[t] = self.T_min

        return self.T_sto

    def plot_results(self, Q_in, Q_out):
        fig, axs = plt.subplots(4, 1, figsize=(6, 8), sharex=True)

        # Plot storage temperature
        axs[0].plot(self.T_sto, label='Storage Temperature')
        axs[0].set_ylabel('Temperature (°C)')
        axs[0].set_title(f'Storage Temperature over Time ({self.storage_type} Storage)')
        axs[0].legend()

        # Plot heat loss
        Q_loss = np.array([self.calculate_heat_loss(self.T_sto[t]) for t in range(self.hours)])
        axs[1].plot(Q_loss, label='Heat Loss', color='orange')
        axs[1].set_ylabel('Heat Loss (W)')
        axs[1].set_title('Heat Loss over Time')
        axs[1].legend()

        # Plot stored heat
        axs[2].plot(self.Q_sto, label='Stored Heat', color='green')
        axs[2].set_ylabel('Stored Heat (J)')
        axs[2].set_title('Stored Heat over Time')
        axs[2].legend()

        # Plot heat input and output
        axs[3].plot(Q_in, label='Heat Input', color='blue')
        axs[3].plot(Q_out, label='Heat Output', color='red')
        axs[3].set_xlabel('Hours')
        axs[3].set_ylabel('Heat (W)')
        axs[3].set_title('Heat Input and Output over Time')
        axs[3].legend()

        plt.tight_layout()
        plt.show()

# Example usage with data from Table 1:
params = {
    "storage_type": "cylindrical",  # Choose between "cylindrical" or "pit"
    "volume": 12000,  # m³
    "rho": 1000,  # kg/m³ (density of water)
    "cp": 4180,  # J/kg*K (specific heat capacity of water)
    "T_ref": 10,  # °C reference temperature
    "U_top": 0.3,  # W/m²K U-value for top insulation
    "U_side": 0.06,  # W/m²K U-value for side insulation
    "U_bottom": 0.4,  # W/m²K U-value for bottom insulation
    "S_top": 200,  # Surface area of top in m²
    "S_side": 600,  # Surface area of sides in m²
    "S_bottom": 200,  # Surface area of bottom in m²
    "T_amb": 10,  # °C ambient temperature
    "T_soil": 10,  # °C soil temperature
    "T_max": 95,  # °C maximum storage temperature
    "T_min": 40,  # °C minimum storage temperature
    "initial_temp": 60,  # Initial storage temperature
    "hours": 8760  # Number of hours in a year
}

# Create instance of the class
storage_sim = ThermalStorage(**params)

# Simulated heat input and output (example random values)
Q_in = np.random.uniform(10000, 35000, params['hours'])  # Heat input in W
Q_out = np.random.uniform(10000, 20000, params['hours'])  # Heat output in W

# Run simulation
T_sto = storage_sim.simulate(Q_in, Q_out)

# Plot the results
storage_sim.plot_results(Q_in, Q_out)
