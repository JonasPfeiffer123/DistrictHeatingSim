"""
STES Simulation Module
================================

Seasonal Thermal Energy Storage with mass flow and temperature-dependent operations.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

.. note:: Based on Narula et al., Renewable Energy 151 (2020), DOI: 10.1016/j.renene.2019.11.121
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from districtheatingsim.heat_generators.simple_thermal_storage import SimpleThermalStorage
from districtheatingsim.heat_generators.stratified_thermal_storage import StratifiedThermalStorage
from districtheatingsim.heat_generators.STES_animation import STESAnimation

class STES(StratifiedThermalStorage):
    """
    Seasonal Thermal Energy Storage with mass flow modeling.

    .. note::
       Extends StratifiedThermalStorage with mass flow calculations and stagnation prevention.
    """
    def __init__(self, **kwargs):
        """
        Initialize STES system with mass flow modeling and temperature tracking.

        .. note::
           Extends StratifiedThermalStorage with mass flow arrays, temperature interfaces, and operational constraints.
        """
        super().__init__(**kwargs)

        # Mass flow time series arrays
        self.mass_flow_in = np.zeros(self.hours)      # kg/s - Heat input mass flow
        self.mass_flow_out = np.zeros(self.hours)     # kg/s - Heat output mass flow
        
        # Temperature time series arrays
        self.T_Q_in_flow = np.zeros(self.hours)       # °C - Heat source supply temperature
        self.T_Q_in_return = np.zeros(self.hours)     # °C - Heat source return temperature
        self.T_Q_out_flow = np.zeros(self.hours)      # °C - Consumer supply temperature
        self.T_Q_out_return = np.zeros(self.hours)    # °C - Consumer return temperature

        # Performance tracking variables
        self.excess_heat = 0          # kWh - Total excess heat due to stagnation
        self.unmet_demand = 0         # kWh - Total unmet heat demand
        self.stagnation_time = 0      # hours - Duration of stagnation conditions

        # Storage state and flow tracking
        self.storage_state = np.zeros(self.hours)           # Storage charge fraction [0-1]
        self.Q_net_storage_flow = np.zeros(self.hours)      # kW - Net storage flow

        # Operational constraints
        self.T_max_rücklauf = 70      # °C - Maximum return temperature to generators
        self.dT_VLT = 15              # K - Supply temperature tolerance

    def simulate_stratified_temperature_mass_flows(self, t: int, Q_in: float, Q_out: float, 
                                                  T_Q_in_flow: float, T_Q_out_return: float) -> None:
        """
        Simulate stratified STES operation with mass flow and temperature dynamics.

        :param t: Current simulation time step (hours, 0 to hours-1)
        :type t: int
        :param Q_in: Heat input power from generators (kW)
        :type Q_in: float
        :param Q_out: Heat demand from consumers (kW)
        :type Q_out: float
        :param T_Q_in_flow: Heat source supply temperature (°C)
        :type T_Q_in_flow: float
        :param T_Q_out_return: Consumer return temperature (°C)
        :type T_Q_out_return: float
        :raises ValueError: If time step outside valid range
        :raises RuntimeError: If mass flow calculations non-physical

        .. note::
           Includes mass flow calculations, temperature-dependent charging/discharging controls, thermal stratification, and operational constraint enforcement.
        """
        # Create local copies to avoid modifying input parameters
        T_Q_in_flow_copy = np.copy(T_Q_in_flow)
        T_Q_out_return_copy = np.copy(T_Q_out_return)

        # Initialize power arrays for this simulation
        self.Q_in = np.zeros(self.hours)      # Heat input power [kW]
        self.Q_out = np.zeros(self.hours)     # Heat output power [kW]
        self.T_Q_in_flow = T_Q_in_flow_copy   # Generator supply temperature
        self.T_Q_out_return = T_Q_out_return_copy  # Consumer return temperature
        
        if t == 0:
            # Initialize stratified storage conditions
            self.T_sto_layers = np.full((self.hours, self.num_layers), self.T_sto[0])
            self.Q_loss[t] = self.calculate_stratified_heat_loss(self.T_sto_layers[t])
            
            # Initialize energy content per layer [kWh]
            self.heat_stored_per_layer = (self.layer_volume * self.rho * self.cp * 
                                        (self.T_sto[0] - T_Q_out_return) / 3.6e6)
            self.Q_sto[t] = np.sum(self.heat_stored_per_layer)

        else:
            # Calculate heat losses and inter-layer conduction
            self.Q_loss[t] = self.calculate_stratified_heat_loss(self.T_sto_layers[t - 1])

            # Apply heat losses to each layer
            for i in range(self.num_layers):
                Q_loss_layer = self.Q_loss_layers[i]  # Layer-specific loss [kW]
                self.heat_stored_per_layer[i] -= Q_loss_layer / 3600  # Convert to kWh
                
                # Temperature drop due to heat loss
                if self.layer_volume[i] > 0:
                    delta_T = (Q_loss_layer * 3.6e6) / (self.layer_volume[i] * self.rho * self.cp)
                    self.T_sto_layers[t, i] = self.T_sto_layers[t - 1, i] - delta_T

            # Inter-layer heat conduction
            for i in range(self.num_layers - 1):
                delta_T = self.T_sto_layers[t - 1, i] - self.T_sto_layers[t - 1, i + 1]
                if abs(delta_T) > 1e-6:  # Avoid numerical issues
                    # Conductive heat transfer [W]
                    heat_transfer = (self.thermal_conductivity * self.S_side * delta_T / 
                                   self.layer_thickness)
                    heat_transfer_kWh = heat_transfer / 3.6e6 * 3600  # Convert to kWh

                    # Transfer heat between adjacent layers
                    self.heat_stored_per_layer[i] -= heat_transfer_kWh
                    self.heat_stored_per_layer[i + 1] += heat_transfer_kWh

                    # Update temperatures based on energy transfer
                    if self.layer_volume[i] > 0:
                        delta_T_transfer = (heat_transfer_kWh * 3.6e6 / 
                                          (self.layer_volume[i] * self.rho * self.cp))
                        self.T_sto_layers[t, i] -= delta_T_transfer
                        self.T_sto_layers[t, i + 1] += delta_T_transfer

            # Update average storage temperature
            self.T_sto[t] = np.average(self.T_sto_layers[t])

            # Charging operation constraints
            if self.T_sto_layers[t, -1] < self.T_max_rücklauf:
                # Charging is possible - bottom layer temperature acceptable
                self.Q_in[t] = Q_in
                if T_Q_in_flow > self.T_sto_layers[t, -1]:
                    self.mass_flow_in[t] = ((self.Q_in[t] * 1000) / 
                                          (self.cp * (T_Q_in_flow - self.T_sto_layers[t, -1])))
                else:
                    self.mass_flow_in[t] = 0
            else:
                # Storage overheating - cannot accept additional heat
                self.mass_flow_in[t] = 0
                self.excess_heat += Q_in
                self.stagnation_time += 1
                self.Q_in[t] = 0

            # Discharging operation constraints
            if self.T_sto_layers[t, 0] > T_Q_in_flow - self.dT_VLT:
                # Discharging is possible - sufficient supply temperature
                self.Q_out[t] = Q_out
                if self.T_sto_layers[t, 0] > T_Q_out_return:
                    self.mass_flow_out[t] = ((self.Q_out[t] * 1000) / 
                                           (self.cp * (self.T_sto_layers[t, 0] - T_Q_out_return)))
                else:
                    self.mass_flow_out[t] = 0
            else:
                # Storage too cold - cannot meet supply requirements
                self.mass_flow_out[t] = 0
                self.unmet_demand += Q_out
                self.Q_out[t] = 0

            # Calculate net storage flow (positive for discharge, negative for charge)
            self.Q_net_storage_flow[t] = self.Q_out[t] - self.Q_in[t]

            # Debug output for verification
            if t == 100:
                print(f"Mass flow in: {self.mass_flow_in[t]:.3f} kg/s, "
                      f"Mass flow out: {self.mass_flow_out[t]:.3f} kg/s, "
                      f"Q_in: {self.Q_in[t]:.1f} kW, Q_out: {self.Q_out[t]:.1f} kW, "
                      f"Q_net: {self.Q_net_storage_flow[t]:.1f} kW")

            # Heat input distribution (top to bottom charging)
            T_flow_current = T_Q_in_flow_copy
            for i in range(self.num_layers):
                if self.mass_flow_in[t] > 0 and self.layer_volume[i] > 0:
                    # Calculate mixing temperature in Kelvin for accuracy
                    layer_mass = self.layer_volume[i] * self.rho
                    flow_mass_per_hour = self.mass_flow_in[t] * 3600
                    
                    mix_temp_K = ((flow_mass_per_hour * self.cp * (T_flow_current + 273.15)) +
                                  (layer_mass * self.cp * (self.T_sto_layers[t, i] + 273.15))) / \
                                 ((flow_mass_per_hour * self.cp) + (layer_mass * self.cp))

                    # Calculate added heat energy
                    added_heat = (self.mass_flow_in[t] * self.cp * 
                                (T_flow_current - self.T_sto_layers[t, i]) * 3600)
                    self.heat_stored_per_layer[i] += added_heat / 3.6e6

                    # Update layer temperature and flow temperature
                    self.T_sto_layers[t, i] = mix_temp_K - 273.15
                    T_flow_current = self.T_sto_layers[t, i]

            # Heat extraction (bottom to top return flow)
            T_return_current = T_Q_out_return_copy
            for i in range(self.num_layers - 1, -1, -1):
                if self.mass_flow_out[t] > 0 and self.layer_volume[i] > 0:
                    # Calculate mixing temperature with return flow
                    layer_mass = self.layer_volume[i] * self.rho
                    flow_mass_per_hour = self.mass_flow_out[t] * 3600
                    
                    mix_temp_K = ((flow_mass_per_hour * self.cp * (T_return_current + 273.15)) +
                                  (layer_mass * self.cp * (self.T_sto_layers[t, i] + 273.15))) / \
                                 ((flow_mass_per_hour * self.cp) + (layer_mass * self.cp))

                    # Calculate removed heat energy
                    removed_heat = (self.mass_flow_out[t] * self.cp * 
                                  (self.T_sto_layers[t, i] - T_return_current) * 3600)
                    self.heat_stored_per_layer[i] -= removed_heat / 3.6e6

                    # Update layer temperature and return temperature
                    self.T_sto_layers[t, i] = mix_temp_K - 273.15
                    T_return_current = self.T_sto_layers[t, i]

            # Update total stored energy and average temperature
            self.Q_sto[t] = np.sum(self.heat_stored_per_layer)
            self.T_sto[t] = np.average(self.T_sto_layers[t])

        # Set system interface temperatures
        self.T_Q_in_return[t] = self.T_sto_layers[t, -1]    # Return to generators
        self.T_Q_out_flow[t] = self.T_sto_layers[t, 0]      # Supply to consumers

    def current_storage_state(self, t: int, T_Q_out_return: float, T_Q_in_flow: float) -> tuple:
        """
        Calculate current storage charge state and energy content.

        :param t: Current time step
        :type t: int
        :param T_Q_out_return: Consumer return temperature (°C)
        :type T_Q_out_return: float
        :param T_Q_in_flow: Generator supply temperature (°C)
        :type T_Q_in_flow: float
        :return: Tuple (storage_fraction [0-1], available_energy [kWh], max_energy [kWh])
        :rtype: tuple

        .. note::
           Storage fraction: 0.0 = empty, 1.0 = full. Based on available energy above return temperature.
        """
        # Determine reference storage temperature
        if t == 0:
            T_sto_current = self.T_sto[t]
        else:
            T_sto_current = self.T_sto[t - 1]

        # Calculate available energy above return temperature
        available_energy_in_storage = np.sum([
            max(0, (T_sto_current - T_Q_out_return)) * self.layer_volume[i] * self.rho * self.cp / 3.6e6 
            for i in range(self.num_layers)
        ])

        # Calculate maximum possible energy content
        max_possible_energy = np.sum([
            max(0, (T_Q_in_flow - T_Q_out_return)) * self.layer_volume[i] * self.rho * self.cp / 3.6e6 
            for i in range(self.num_layers)
        ])

        # Calculate storage fraction with bounds checking
        if max_possible_energy > 0:
            storage_fraction = available_energy_in_storage / max_possible_energy
        else:
            storage_fraction = 0.0

        # Store in time series array
        self.storage_state[t] = max(0, min(1, storage_fraction))
        
        return (self.storage_state[t], available_energy_in_storage, max_possible_energy)

    def current_storage_temperatures(self, t: int) -> tuple:
        """
        Get current storage interface temperatures for system integration.

        :param t: Current time step
        :type t: int
        :return: Tuple (supply_temp, return_temp) in °C
        :rtype: tuple
        """
        if t == 0:
            return self.T_sto[t], self.T_sto[t]
        else:
            return self.T_sto_layers[t-1, 0], self.T_sto_layers[t-1, -1]

    def calculate_costs(self, Wärmemenge_MWh: float, Investitionskosten: float, 
                       Nutzungsdauer: float, f_Inst: float, f_W_Insp: float, 
                       Bedienaufwand: float, q: float, r: float, T: float, 
                       Energiebedarf: float, Energiekosten: float, E1: float, 
                       stundensatz: float) -> None:
        """
        Calculate heat generation costs including investment and operational expenses.

        :param Wärmemenge_MWh: Annual heat delivery (MWh/year)
        :type Wärmemenge_MWh: float
        :param Investitionskosten: Total investment costs (€)
        :type Investitionskosten: float
        :param Nutzungsdauer: System lifetime (years)
        :type Nutzungsdauer: float
        :param f_Inst: Installation cost factor
        :type f_Inst: float
        :param f_W_Insp: Maintenance and inspection cost factor
        :type f_W_Insp: float
        :param Bedienaufwand: Operation effort (hours/year)
        :type Bedienaufwand: float
        :param q: Interest rate factor
        :type q: float
        :param r: Real interest rate
        :type r: float
        :param T: Economic lifetime (years)
        :type T: float
        :param Energiebedarf: Energy consumption (kWh/year)
        :type Energiebedarf: float
        :param Energiekosten: Energy costs (€/kWh)
        :type Energiekosten: float
        :param E1: Reference energy (kWh)
        :type E1: float
        :param stundensatz: Labor cost rate (€/hour)
        :type stundensatz: float

        .. note::
           Follows VDI guidelines for economic assessment. Calculates annualized costs and specific heat generation costs (€/MWh).
        """
        # Store parameters for cost calculation
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

        # Calculate annualized costs
        self.A_N = self.annuität(
            self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, 
            self.f_W_Insp, self.Bedienaufwand, q, r, T, 
            Energiebedarf, Energiekosten, E1, stundensatz
        )

        # Calculate specific heat generation costs
        if self.Wärmemenge_MWh > 0:
            self.WGK = self.A_N / self.Wärmemenge_MWh
        else:
            self.WGK = float('inf')

    def get_display_text(self) -> str:
        """
        Generate display text with key system parameters.

        :return: Formatted text with type, volume, temperatures, layers
        :rtype: str
        """
        return (f"{self.storage_type.capitalize()} STES: Volume: {self.volume:.1f} m³, "
                f"Max Temp: {self.T_max:.1f} °C, Min Temp: {self.T_min:.1f} °C, "
                f"Layers: {self.num_layers}")

    def extract_tech_data(self) -> tuple:
        """
        Extract technical data for system documentation.

        :return: Tuple (type, dimensions, costs, full_costs)
        :rtype: tuple
        """
        storage_type = self.storage_type.capitalize() + " STES"
        dimensions = f"Volume: {self.volume:.1f} m³, Layers: {self.num_layers}"
        costs = 0  # To be implemented based on cost calculation
        full_costs = 0  # To be implemented based on cost calculation
        return storage_type, dimensions, costs, full_costs

    def plot_results(self, Q_in: np.ndarray, Q_out: np.ndarray, 
                    T_Q_in_flow: np.ndarray, T_Q_out_return: np.ndarray) -> None:
        """
        Generate comprehensive multi-panel visualization of STES simulation results.

        :param Q_in: Heat input time series (kW)
        :type Q_in: numpy.ndarray
        :param Q_out: Heat output time series (kW)
        :type Q_out: numpy.ndarray
        :param T_Q_in_flow: Supply temperature time series (°C)
        :type T_Q_in_flow: numpy.ndarray
        :param T_Q_out_return: Return temperature time series (°C)
        :type T_Q_out_return: numpy.ndarray

        .. note::
           Shows energy flows, temperatures, heat losses, stored energy, layer temperatures, and 3D temperature distribution.
        """
        fig = plt.figure(figsize=(16, 10))
        
        # Create subplot layout
        axs1 = fig.add_subplot(2, 3, 1)
        axs2 = fig.add_subplot(2, 3, 2)
        axs3 = fig.add_subplot(2, 3, 3)
        axs4 = fig.add_subplot(2, 3, 4)
        axs5 = fig.add_subplot(2, 3, 5)
        axs6 = fig.add_subplot(2, 3, 6, projection='3d')

        # Separate positive and negative values for storage flow visualization
        Q_net_positive = np.maximum(self.Q_net_storage_flow, 0)  # Discharging
        Q_net_negative = np.minimum(self.Q_net_storage_flow, 0)  # Charging

        # Panel 1: Energy flows and storage operations
        axs1.plot(Q_out, label='Wärmeverbrauch', color='blue', linewidth=0.5)

        # Storage charging (negative net flow)
        axs1.fill_between(
            range(self.hours), 0, Q_net_negative,
            where=Q_net_negative < 0,
            color='orange', alpha=0.7,
            label='Speicherbeladung'
        )
        
        # Heat generation and storage discharging
        axs1.stackplot(
            range(self.hours),
            Q_in, Q_net_positive,
            labels=['Wärmeerzeugung', 'Speicherentladung'],
            colors=['red', 'purple'], alpha=0.8
        )

        axs1.set_ylabel('Wärme (kW)')
        axs1.set_title('Wärmeerzeugung, -verbrauch und Speicher-Nettofluss')
        axs1.legend(loc='upper left', bbox_to_anchor=(0, 1))
        axs1.grid(True, alpha=0.3)

        # Panel 2: System temperatures
        axs2.plot(self.T_sto, label='Speichertemperatur', linewidth=1.5, color='black')
        axs2.plot(T_Q_in_flow, label='Vorlauftemperatur Erzeuger (Eintritt)', 
                 linestyle='--', color='green', alpha=0.8)
        axs2.plot(T_Q_out_return, label='Rücklauftemperatur Verbraucher (Eintritt)', 
                 linestyle='--', color='orange', alpha=0.8)
        axs2.plot(self.T_Q_in_return, label='Rücklauftemperatur Erzeuger (Austritt)', 
                 linestyle='--', color='purple', alpha=0.8)
        axs2.plot(self.T_Q_out_flow, label='Vorlauftemperatur Verbraucher (Austritt)', 
                 linestyle='--', color='brown', alpha=0.8)
        
        axs2.set_ylabel('Temperatur (°C)')
        axs2.set_title('Systemtemperaturen im Zeitverlauf')
        axs2.legend(loc='upper left', bbox_to_anchor=(0, 1))
        axs2.grid(True, alpha=0.3)

        # Panel 3: Heat losses
        axs3.plot(self.Q_loss, label='Wärmeverlust', color='orange', linewidth=1.5)
        axs3.set_ylabel('Wärmeverlust (kW)')
        axs3.set_title('Wärmeverlust im Zeitverlauf')
        axs3.legend()
        axs3.grid(True, alpha=0.3)

        # Panel 4: Stored energy
        axs4.plot(self.Q_sto, label='Gespeicherte Wärme', color='green', linewidth=1.5)
        axs4.set_ylabel('Gespeicherte Wärme (kWh)')
        axs4.set_title('Gespeicherte Wärme im Zeitverlauf')
        axs4.legend()
        axs4.grid(True, alpha=0.3)

        # Panel 5: Stratified layer temperatures
        colors = plt.cm.viridis(np.linspace(0, 1, self.T_sto_layers.shape[1]))
        for i in range(self.T_sto_layers.shape[1]):
            axs5.plot(self.T_sto_layers[:, i], label=f'Schicht {i+1}', 
                     color=colors[i], linewidth=1.2)
        
        axs5.set_xlabel('Zeit (Stunden)')
        axs5.set_ylabel('Temperatur (°C)')
        axs5.set_title('Temperaturen der Schichten im Speicher')
        axs5.legend(loc='upper left', bbox_to_anchor=(0, 1))
        axs5.grid(True, alpha=0.3)

        # Panel 6: 3D temperature distribution
        visualization_time = min(6000, len(self.T_sto_layers) - 1)
        self.plot_3d_temperature_distribution(axs6, visualization_time)

        plt.tight_layout()


if __name__ == '__main__':
    """
    Demonstration of STES system simulation with realistic district heating profiles.
    
    This example shows complete STES system setup, simulation execution, and results
    analysis for a large-scale seasonal thermal energy storage application.
    """
    # STES system parameters for large-scale district heating
    params = {
        "storage_type": "truncated_trapezoid",
        "dimensions": (20, 20, 50, 50, 15),  # Large pit thermal energy storage
        "rho": 1000,                         # Water density [kg/m³]
        "cp": 4180,                          # Water heat capacity [J/(kg·K)]
        "T_ref": 10,                         # Reference temperature [°C]
        "lambda_top": 0.04,                  # Top insulation thermal conductivity [W/(m·K)]
        "lambda_side": 0.03,                 # Side insulation thermal conductivity [W/(m·K)]
        "lambda_bottom": 0.05,               # Bottom insulation thermal conductivity [W/(m·K)]
        "lambda_soil": 1.5,                  # Soil thermal conductivity [W/(m·K)]
        "dt_top": 0.3,                       # Top insulation thickness [m]
        "ds_side": 0.4,                      # Side insulation thickness [m]
        "db_bottom": 0.5,                    # Bottom insulation thickness [m]
        "T_amb": 10,                         # Ambient temperature [°C]
        "T_soil": 10,                        # Soil temperature [°C]
        "T_max": 95,                         # Maximum storage temperature [°C]
        "T_min": 40,                         # Minimum storage temperature [°C]
        "initial_temp": 60,                  # Initial storage temperature [°C]
        "hours": 8760,                       # Annual simulation [hours]
        "num_layers": 5,                     # Number of stratification layers
        "thermal_conductivity": 0.6          # Water thermal conductivity [W/(m·K)]
    }
    
    # Create STES system instances for comparison
    simple_STES = SimpleThermalStorage(
        name="Einfacher Saisonaler Wärmespeicher", **params
    )
    stratified_STES = StratifiedThermalStorage(
        name="Geschichteter Saisonaler Wärmespeicher", **params
    )
    temperature_stratified_STES = STES(
        name="Temperaturaufgelöster Saisonaler Wärmespeicher", **params
    )

    # Load realistic heating demand profile
    file_path = os.path.abspath('examples/data/Lastgang/Lastgang.csv')
    df = pd.read_csv(file_path, delimiter=';', encoding='utf-8')
    Q_out_profile = df['Gesamtwärmebedarf_Gebäude_kW'].values
    
    # Define system operating temperatures
    T_Q_in_flow_profile = np.full(params['hours'], 85.0)    # Generator supply [°C]
    T_Q_out_return_profile = np.full(params['hours'], 50.0) # Consumer return [°C]

    # Define heat input profile (e.g., from solar thermal or waste heat)
    Q_in = np.full(params['hours'], 500.0)  # Constant heat input [kW]

    # Execute STES simulation
    print("Starting STES simulation...")
    for t in range(params['hours']):
        temperature_stratified_STES.simulate_stratified_temperature_mass_flows(
            t, Q_in[t], Q_out_profile[t], 
            T_Q_in_flow_profile[t], T_Q_out_return_profile[t]
        )

    # Generate comprehensive results visualization
    temperature_stratified_STES.plot_results(
        Q_in, Q_out_profile, T_Q_in_flow_profile, T_Q_out_return_profile
    )
    
    # Calculate performance metrics
    temperature_stratified_STES.calculate_efficiency(Q_in)
    
    # Display performance results
    print("\n=== STES Performance Results ===")
    print(f"Speicherwirkungsgrad / -effizienz: {temperature_stratified_STES.efficiency * 100:.2f}%")
    print(f"Überschüssige Wärme durch Stagnation: {temperature_stratified_STES.excess_heat:.2f} kWh")
    print(f"Nicht gedeckter Bedarf aufgrund von Speicherentleerung: {temperature_stratified_STES.unmet_demand:.2f} kWh")
    print(f"Stagnationsdauer: {temperature_stratified_STES.stagnation_time} h")
    
    # Additional performance analysis
    total_energy_in = np.sum(Q_in)
    total_energy_out = np.sum(Q_out_profile)
    storage_utilization = temperature_stratified_STES.Q_sto.max() / temperature_stratified_STES.Q_sto[0]
    
    print(f"\n=== Additional Analysis ===")
    print(f"Total energy input: {total_energy_in:.0f} kWh")
    print(f"Total energy demand: {total_energy_out:.0f} kWh")
    print(f"Peak storage utilization: {storage_utilization:.2f}")
    
    # Interactive 3D visualization
    print("\nGenerating 3D animation...")
    STES_animation = STESAnimation(temperature_stratified_STES)
    STES_animation.show()

    plt.show()