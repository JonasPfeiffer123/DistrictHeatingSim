"""
STES Simulation Module
================================

This module implements sophisticated Seasonal Thermal Energy Storage (STES) systems
with detailed mass flow calculations, temperature-dependent storage operations, and
realistic hydraulic behavior modeling.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-06-26

It extends stratified thermal storage to include
mass flow dynamics, charging/discharging controls, and operational constraints for
district heating applications.

The implementation is based on validated research methods and provides comprehensive
analysis of STES performance including stagnation effects, unmet demand calculations,
and system integration aspects critical for seasonal energy storage design.

References
----------
Simulation method for assessing hourly energy flows in district heating system with seasonal thermal energy storage
Authors: Kapil Narula, Fleury de Oliveira Filho, Willy Villasmil, Martin K. Patel
Journal: Renewable Energy, Volume 151, May 2020, Pages 1250-1268
DOI: https://doi.org/10.1016/j.renene.2019.11.121
Link: https://www.sciencedirect.com/science/article/pii/S0960148119318154
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
    Advanced Seasonal Thermal Energy Storage (STES) system with mass flow modeling.

    This class extends the StratifiedThermalStorage to implement sophisticated STES
    systems with detailed mass flow calculations, hydraulic constraints, and realistic
    operational behavior. It provides comprehensive modeling of charging and discharging
    operations including temperature-dependent flow controls, stagnation prevention,
    and system integration aspects for district heating applications.

    The STES model incorporates:
    - Mass flow-based energy transfer calculations
    - Temperature-dependent operational constraints
    - Charging and discharging flow patterns
    - Stagnation and overheating protection
    - Unmet demand tracking and analysis
    - System integration with heat sources and consumers

    Parameters
    ----------
    **kwargs
        All parameters from parent StratifiedThermalStorage class.
        See StratifiedThermalStorage documentation for complete parameter list.

    Attributes
    ----------
    mass_flow_in : numpy.ndarray
        Heat input mass flow rate time series [kg/s].
        Calculated based on heat input and temperature differences.
    mass_flow_out : numpy.ndarray
        Heat output mass flow rate time series [kg/s].
        Calculated based on heat demand and temperature differences.
    T_Q_in_flow : numpy.ndarray
        Heat source supply temperature time series [°C].
        Temperature of heat input from generators (e.g., solar collectors).
    T_Q_in_return : numpy.ndarray
        Heat source return temperature time series [°C].
        Return temperature to heat generators from storage bottom.
    T_Q_out_flow : numpy.ndarray
        Consumer supply temperature time series [°C].
        Supply temperature from storage top to consumers.
    T_Q_out_return : numpy.ndarray
        Consumer return temperature time series [°C].
        Return temperature from consumers to storage.
    excess_heat : float
        Total excess heat due to storage stagnation [kWh].
        Heat that cannot be stored due to temperature limitations.
    unmet_demand : float
        Total unmet heat demand [kWh].
        Demand that cannot be satisfied due to insufficient storage temperature.
    stagnation_time : int
        Total stagnation duration [hours].
        Time periods when storage cannot accept additional heat input.
    storage_state : numpy.ndarray
        Storage charge state time series [0-1].
        Fraction of maximum possible energy content.
    Q_net_storage_flow : numpy.ndarray
        Net storage energy flow time series [kW].
        Positive for discharge, negative for charge operations.
    T_max_rücklauf : float
        Maximum allowable return temperature to generators [°C].
        Thermal protection limit for heat source equipment.
    dT_VLT : float
        Supply temperature tolerance [K].
        Minimum temperature difference for acceptable supply conditions.

    Notes
    -----
    Mass Flow Calculations:
        
        **Heat Input Mass Flow**:
        ṁ_in = Q_in / (cp × (T_supply - T_return_bottom))
        
        **Heat Output Mass Flow**:
        ṁ_out = Q_out / (cp × (T_top - T_return_consumer))
        
        **Energy Transfer**:
        Q = ṁ × cp × ΔT [kW]

    Operational Constraints:
        
        **Charging Limitations**:
        - Storage bottom temperature must remain below T_max_rücklauf
        - Sufficient temperature difference required for heat transfer
        - Mass flow limited by thermal capacity and temperature gradients
        
        **Discharging Limitations**:
        - Storage top temperature must exceed consumer requirements
        - Minimum supply temperature maintained within dT_VLT tolerance
        - Mass flow adjusted for varying temperature conditions

    Storage Control Logic:
        
        **Charging Priority**:
        1. Check bottom layer temperature vs. maximum return limit
        2. Calculate required mass flow for heat input
        3. Distribute heat input through layers (top to bottom)
        4. Track excess heat during stagnation conditions
        
        **Discharging Priority**:
        1. Check top layer temperature vs. minimum supply requirement
        2. Calculate available mass flow for heat output
        3. Extract heat from layers (bottom to top for return flow)
        4. Track unmet demand when insufficient temperature available

    Thermal Stratification:
        Natural temperature stratification maintained through:
        - Density-driven buoyancy effects
        - Controlled inlet/outlet positioning
        - Layer-specific mixing calculations
        - Temperature-dependent flow distribution

    See Also
    --------
    StratifiedThermalStorage : Base stratified storage implementation
    SimpleThermalStorage : Simplified storage model without stratification
    simulate_stratified_temperature_mass_flows : Main simulation method
    current_storage_state : Storage charge state calculation
    plot_results : Comprehensive visualization of STES performance
    """
    def __init__(self, **kwargs):
        """
        Initialize STES system with mass flow modeling capabilities.
        
        Extends parent initialization with STES-specific attributes including
        mass flow arrays, temperature tracking, and operational constraints.
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

        This method performs comprehensive simulation of STES operation including mass flow
        calculations, temperature-dependent charging/discharging controls, thermal stratification
        effects, and operational constraint enforcement. It provides detailed modeling of
        real-world STES behavior for district heating system integration.

        Parameters
        ----------
        t : int
            Current simulation time step [hours].
            Must be within range [0, hours-1] for valid operation.
        Q_in : float
            Heat input power from generators [kW].
            Positive values represent available heat for storage charging.
        Q_out : float
            Heat demand from consumers [kW].
            Positive values represent heat extraction requirements.
        T_Q_in_flow : float
            Heat source supply temperature [°C].
            Temperature of incoming heat from generators (e.g., solar collectors).
        T_Q_out_return : float
            Consumer return temperature [°C].
            Return temperature from district heating consumers.

        Notes
        -----
        Simulation Sequence:
            
            **Initialization Phase (t=0)**:
            1. Initialize layer temperatures to uniform initial condition
            2. Calculate initial heat losses and stored energy
            3. Set up thermal stratification arrays
            
            **Operational Phase (t>0)**:
            1. **Heat Loss Calculation**: Layer-specific thermal losses
            2. **Inter-layer Conduction**: Temperature-driven heat transfer
            3. **Storage State Assessment**: Temperature-based operational limits
            4. **Mass Flow Calculation**: Heat transfer rate determination
            5. **Charging Operation**: Top-down heat input distribution
            6. **Discharging Operation**: Bottom-up heat extraction
            7. **Temperature Update**: Layer-specific temperature evolution

        Mass Flow Calculations:
            
            **Charging Mass Flow**:
            If bottom layer temperature allows charging:
            ṁ_in = Q_in × 1000 / (cp × (T_supply - T_bottom))
            
            **Discharging Mass Flow**:
            If top layer temperature allows discharging:
            ṁ_out = Q_out × 1000 / (cp × (T_top - T_return))

        Operational Logic:
            
            **Charging Constraints**:
            - Bottom layer temperature < T_max_rücklauf (generator protection)
            - Sufficient temperature difference for heat transfer
            - Excess heat tracking during stagnation conditions
            
            **Discharging Constraints**:
            - Top layer temperature > T_supply - dT_VLT (supply quality)
            - Adequate temperature for consumer requirements
            - Unmet demand tracking when storage insufficient

        Heat Distribution:
            
            **Charging (Top to Bottom)**:
            Heat input enters top layers first, maintaining stratification:
            - Calculate mixing temperature with layer content
            - Update layer energy and temperature
            - Pass modified temperature to next layer
            
            **Discharging (Bottom to Top)**:
            Return flow enters bottom, extracts heat upward:
            - Calculate mixing temperature with return flow
            - Extract available heat based on temperature difference
            - Update layer conditions and flow temperature

        Quality Assurance:
            - Temperature bounds enforcement
            - Energy conservation verification
            - Mass flow physical limits
            - Stratification preservation

        See Also
        --------
        current_storage_state : Calculate storage charge level
        current_storage_temperatures : Get storage temperature conditions
        calculate_stratified_heat_loss : Layer-specific heat loss calculation
        """
        # Create local copies to avoid modifying input parameters
        T_Q_in_flow_copy = np.copy(T_Q_in_flow)
        T_Q_out_return_copy = np.copy(T_Q_out_return)

        # Initialize power arrays for this simulation
        self.Q_in = np.zeros(self.hours)      # Heat input power [kW]
        self.Q_out = np.zeros(self.hours)     # Heat output power [kW]
        self.T_Q_in_flow = T_Q_in_flow_copy   # Generator supply temperature
        self.T_Q_out_return = T_Q_out_return_copy  # Consumer return temperature
        
        # Pre-calculate constants for performance optimization (inherited from StratifiedThermalStorage)
        if not hasattr(self, '_constants_initialized'):
            # Calculate interface areas for inter-layer conduction (CRITICAL: horizontal cross-sections!)
            self.A_interface = self._calculate_interface_areas()
            
            # Pre-calculate layer thermal capacities [J/K]
            self.layer_thermal_capacity = self.layer_volume * self.rho * self.cp
            
            # Pre-calculate conduction coefficients [W/K] for inter-layer heat transfer
            self.conduction_coeff = self.thermal_conductivity * self.A_interface / self.layer_thickness
            
            # Conversion factor J/kWh
            self.conversion_factor = 3.6e6
            
            # Mark as initialized
            self._constants_initialized = True
        
        if t == 0:
            # Initialize stratified storage conditions - temperature is PRIMARY state variable
            self.T_sto_layers = np.full((self.hours, self.num_layers), self.T_sto[0])
            
            # Calculate initial heat loss (and store layer-specific losses in Q_loss_layers)
            self.Q_loss[t] = self.calculate_stratified_heat_loss(self.T_sto_layers[t])
            
            # Calculate initial stored energy from temperature distribution [kWh]
            self.Q_sto[t] = np.sum([
                self.layer_volume[i] * self.rho * self.cp * 
                (self.T_sto_layers[t, i] - self.T_ref) / self.conversion_factor
                for i in range(self.num_layers)
            ])

        else:
            # Start with previous timestep temperatures (temperature is primary state variable)
            T_new = self.T_sto_layers[t - 1, :].copy()
            
            # STEP 1: Apply heat losses to each layer
            # Calculate layer-specific heat losses at current temperatures
            self.Q_loss[t] = self.calculate_stratified_heat_loss(T_new)
            
            for i in range(self.num_layers):
                Q_loss_layer = self.Q_loss_layers[i]  # kW
                # Energy loss over dt = 1 hour [kWh]
                energy_loss = Q_loss_layer * 1.0  # dt = 1h
                
                # Update temperature based on heat loss (using pre-calculated capacity)
                if self.layer_volume[i] > 0:
                    delta_T_loss = (energy_loss * self.conversion_factor) / self.layer_thermal_capacity[i]
                    T_new[i] -= delta_T_loss
            
            # STEP 2: Inter-layer heat conduction (using correct horizontal interface areas)
            # Physical correctness: Uses horizontal cross-sectional areas perpendicular to heat flow
            # NOT the vertical side surface area - critical for accurate modeling!
            for i in range(self.num_layers - 1):
                delta_T = T_new[i] - T_new[i + 1]
                if abs(delta_T) > 1e-6:  # Avoid numerical issues with negligible gradients
                    # Heat transfer rate [W] using pre-calculated conduction coefficient
                    # Q_cond = (λ × A_interface / δ_layer) × ΔT
                    Q_cond = self.conduction_coeff[i] * delta_T
                    
                    # Energy transfer over dt = 1 hour [kWh]
                    energy_transfer = (Q_cond / 1000) * 1.0  # dt = 1h
                    
                    # Temperature changes in both layers (using pre-calculated capacities)
                    delta_T_upper = (energy_transfer * self.conversion_factor) / self.layer_thermal_capacity[i]
                    delta_T_lower = (energy_transfer * self.conversion_factor) / self.layer_thermal_capacity[i + 1]
                    
                    T_new[i] -= delta_T_upper
                    T_new[i + 1] += delta_T_lower
            
            # Store updated temperatures (before charging/discharging)
            self.T_sto_layers[t, :] = T_new
            
            # Update average storage temperature
            self.T_sto[t] = np.average(self.T_sto_layers[t])

            # STEP 3: Charging operation constraints (check BEFORE mass flow calculation)
            if self.T_sto_layers[t, -1] < self.T_max_rücklauf:
                # Charging is possible - bottom layer temperature acceptable for generator protection
                self.Q_in[t] = Q_in
                # Calculate required mass flow for heat input
                if T_Q_in_flow > self.T_sto_layers[t, -1] + 1e-3:  # Minimum ΔT for heat transfer
                    self.mass_flow_in[t] = ((self.Q_in[t] * 1000) / 
                                          (self.cp * (T_Q_in_flow - self.T_sto_layers[t, -1])))
                else:
                    self.mass_flow_in[t] = 0  # Insufficient temperature difference
            else:
                # Storage overheating - cannot accept additional heat (stagnation)
                self.mass_flow_in[t] = 0
                self.excess_heat += Q_in  # Track rejected heat
                self.stagnation_time += 1
                self.Q_in[t] = 0

            # STEP 4: Discharging operation constraints (check supply temperature quality)
            if self.T_sto_layers[t, 0] > T_Q_in_flow - self.dT_VLT:
                # Discharging is possible - sufficient supply temperature for consumers
                self.Q_out[t] = Q_out
                # Calculate available mass flow for heat extraction
                if self.T_sto_layers[t, 0] > T_Q_out_return + 1e-3:  # Minimum ΔT for heat transfer
                    self.mass_flow_out[t] = ((self.Q_out[t] * 1000) / 
                                           (self.cp * (self.T_sto_layers[t, 0] - T_Q_out_return)))
                else:
                    self.mass_flow_out[t] = 0  # Insufficient temperature difference
            else:
                # Storage too cold - cannot meet supply requirements
                self.mass_flow_out[t] = 0
                self.unmet_demand += Q_out  # Track unmet demand
                self.Q_out[t] = 0

            # Calculate net storage flow (positive for discharge, negative for charge)
            self.Q_net_storage_flow[t] = self.Q_out[t] - self.Q_in[t]

            # Debug output for verification
            if t == 100:
                print(f"t={t}: Mass flow in: {self.mass_flow_in[t]:.3f} kg/s, "
                      f"Mass flow out: {self.mass_flow_out[t]:.3f} kg/s")
                print(f"       Q_in: {self.Q_in[t]:.1f} kW, Q_out: {self.Q_out[t]:.1f} kW, "
                      f"Q_net: {self.Q_net_storage_flow[t]:.1f} kW")
                print(f"       T_top: {self.T_sto_layers[t, 0]:.2f}°C, "
                      f"T_bottom: {self.T_sto_layers[t, -1]:.2f}°C")

            # STEP 5: Heat input distribution (top to bottom charging with mass flow mixing)
            # Physical model: Incoming flow mixes with layer content
            T_flow_current = T_Q_in_flow_copy
            for i in range(self.num_layers):
                if self.mass_flow_in[t] > 0 and self.layer_volume[i] > 0:
                    # Layer mass [kg]
                    layer_mass = self.layer_volume[i] * self.rho
                    # Flow mass per hour [kg]
                    flow_mass_per_hour = self.mass_flow_in[t] * 3600
                    
                    # Mixing temperature calculation (energy balance)
                    # (m_flow × cp × T_flow + m_layer × cp × T_layer) / (m_total × cp)
                    T_new_layer = ((flow_mass_per_hour * T_flow_current + 
                                   layer_mass * self.T_sto_layers[t, i]) /
                                  (flow_mass_per_hour + layer_mass))
                    
                    # Update layer temperature
                    self.T_sto_layers[t, i] = T_new_layer
                    # Flow continues to next layer at current layer temperature
                    T_flow_current = T_new_layer

            # STEP 6: Heat extraction (bottom to top return flow with mass flow mixing)
            # Physical model: Return flow enters bottom, mixes upward
            T_return_current = T_Q_out_return_copy
            for i in range(self.num_layers - 1, -1, -1):  # Bottom to top
                if self.mass_flow_out[t] > 0 and self.layer_volume[i] > 0:
                    # Layer mass [kg]
                    layer_mass = self.layer_volume[i] * self.rho
                    # Flow mass per hour [kg]
                    flow_mass_per_hour = self.mass_flow_out[t] * 3600
                    
                    # Mixing temperature calculation (energy balance)
                    T_new_layer = ((flow_mass_per_hour * T_return_current + 
                                   layer_mass * self.T_sto_layers[t, i]) /
                                  (flow_mass_per_hour + layer_mass))
                    
                    # Update layer temperature
                    self.T_sto_layers[t, i] = T_new_layer
                    # Return flow continues to next layer at current layer temperature
                    T_return_current = T_new_layer
            
            # STEP 7: Apply temperature limits and calculate total stored energy
            self.T_sto_layers[t, :] = np.clip(self.T_sto_layers[t, :], self.T_min, self.T_max)
            
            # Calculate total stored energy from temperature distribution [kWh]
            self.Q_sto[t] = np.sum([
                self.layer_volume[i] * self.rho * self.cp * 
                (self.T_sto_layers[t, i] - self.T_ref) / self.conversion_factor
                for i in range(self.num_layers)
            ])
            
            # Update average storage temperature
            self.T_sto[t] = np.average(self.T_sto_layers[t])

        # Set system interface temperatures
        self.T_Q_in_return[t] = self.T_sto_layers[t, -1]    # Return to generators
        self.T_Q_out_flow[t] = self.T_sto_layers[t, 0]      # Supply to consumers

    def current_storage_state(self, t: int, T_Q_out_return: float, T_Q_in_flow: float) -> tuple:
        """
        Calculate current storage charge state and energy content.

        This method determines the current charge level of the STES system as a fraction
        of maximum possible energy content. It provides essential information for storage
        management, operational control, and system integration in district heating networks.

        Parameters
        ----------
        t : int
            Current time step for state calculation.
        T_Q_out_return : float
            Consumer return temperature [°C].
            Reference temperature for available energy calculation.
        T_Q_in_flow : float
            Generator supply temperature [°C].
            Reference temperature for maximum energy calculation.

        Returns
        -------
        tuple
            Storage state information containing:
            - storage_fraction (float): Charge state [0-1]
            - available_energy (float): Currently available energy [kWh]
            - max_energy (float): Maximum possible energy content [kWh]

        Notes
        -----
        Energy Calculations:
            
            **Available Energy**:
            E_available = Σ(T_storage - T_return) × V_layer × ρ × cp / 3.6e6
            
            **Maximum Energy**:
            E_max = Σ(T_supply - T_return) × V_layer × ρ × cp / 3.6e6
            
            **Storage Fraction**:
            f_storage = E_available / E_max

        Physical Interpretation:
            - 0.0: Storage at minimum useful temperature (empty)
            - 1.0: Storage at maximum charging temperature (full)
            - >1.0: Storage overcharged (should not occur in normal operation)

        Applications:
            - Storage management and control algorithms
            - System integration with heat sources and loads
            - Performance monitoring and optimization
            - Predictive control strategies
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
        Get current storage interface temperatures.

        Returns the supply and return temperatures at the storage interfaces
        for system integration and control purposes.

        Parameters
        ----------
        t : int
            Current time step.

        Returns
        -------
        tuple
            Storage interface temperatures (supply_temp, return_temp) [°C].
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
        Calculate heat generation costs for the STES system.

        This method computes the economic performance of the STES system including
        investment costs, operational expenses, and heat generation costs per unit
        energy delivered. It provides essential economic data for system optimization
        and investment decision support.

        Parameters
        ----------
        Wärmemenge_MWh : float
            Annual heat delivery [MWh/year].
        Investitionskosten : float
            Total investment costs [€].
        Nutzungsdauer : float
            System lifetime [years].
        f_Inst : float
            Installation cost factor [-].
        f_W_Insp : float
            Maintenance and inspection cost factor [-].
        Bedienaufwand : float
            Operation effort [hours/year].
        q : float
            Interest rate factor [-].
        r : float
            Real interest rate [-].
        T : float
            Economic lifetime [years].
        Energiebedarf : float
            Energy consumption [kWh/year].
        Energiekosten : float
            Energy costs [€/kWh].
        E1 : float
            Reference energy [kWh].
        stundensatz : float
            Labor cost rate [€/hour].

        Notes
        -----
        The method calculates:
        - Annualized costs including capital and operational expenses
        - Specific heat generation costs [€/MWh]
        - Economic performance indicators

        This follows German VDI guidelines for economic assessment
        of thermal energy systems.
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
        Generate display text for system identification.

        Returns
        -------
        str
            Formatted display text with key system parameters.
        """
        return (f"{self.storage_type.capitalize()} STES: Volume: {self.volume:.1f} m³, "
                f"Max Temp: {self.T_max:.1f} °C, Min Temp: {self.T_min:.1f} °C, "
                f"Layers: {self.num_layers}")

    def extract_tech_data(self) -> tuple:
        """
        Extract technical data for system documentation.

        Returns
        -------
        tuple
            Technical data (type, dimensions, costs, full_costs).
        """
        storage_type = self.storage_type.capitalize() + " STES"
        dimensions = f"Volume: {self.volume:.1f} m³, Layers: {self.num_layers}"
        costs = 0  # To be implemented based on cost calculation
        full_costs = 0  # To be implemented based on cost calculation
        return storage_type, dimensions, costs, full_costs

    def plot_results(self, Q_in: np.ndarray, Q_out: np.ndarray, 
                    T_Q_in_flow: np.ndarray, T_Q_out_return: np.ndarray) -> None:
        """
        Generate comprehensive visualization of STES simulation results.

        This method creates a detailed multi-panel visualization showing all aspects
        of STES performance including energy flows, temperatures, storage states,
        and 3D geometry representation for complete system analysis.

        Parameters
        ----------
        Q_in : numpy.ndarray
            Heat input time series [kW].
        Q_out : numpy.ndarray
            Heat output time series [kW].
        T_Q_in_flow : numpy.ndarray
            Supply temperature time series [°C].
        T_Q_out_return : numpy.ndarray
            Return temperature time series [°C].

        Notes
        -----
        Visualization Panels:
            1. Energy flows and storage net flow
            2. System temperatures
            3. Heat losses
            4. Stored energy content
            5. Stratified layer temperatures
            6. 3D temperature distribution

        The visualization provides comprehensive insight into:
        - Seasonal energy patterns
        - Storage charging/discharging cycles
        - Temperature stratification effects
        - System integration performance
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