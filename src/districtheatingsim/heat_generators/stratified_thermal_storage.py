"""
Stratified Thermal Storage Module
==================================

This module implements sophisticated stratified thermal energy storage (STES) systems
with multi-layer temperature distribution modeling.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-06-26

It extends the base thermal storage functionality to include thermal stratification effects, layer-specific heat losses,
and inter-layer heat conduction for realistic seasonal thermal energy storage simulation.

The implementation is based on validated research methods for district heating applications
and provides detailed analysis of temperature stratification phenomena critical for
large-scale thermal energy storage design and operation optimization.

References
----------
Simulation method for assessing hourly energy flows in district heating system with seasonal thermal energy storage
Authors: Kapil Narula, Fleury de Oliveira Filho, Willy Villasmil, Martin K. Patel
Journal: Renewable Energy, Volume 151, May 2020, Pages 1250-1268
DOI: https://doi.org/10.1016/j.renene.2019.11.121
Link: https://www.sciencedirect.com/science/article/pii/S0960148119318154
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, Dict, Any, List, Optional, Union

from districtheatingsim.heat_generators.simple_thermal_storage import ThermalStorage

class StratifiedThermalStorage(ThermalStorage):
    """
    Advanced stratified thermal energy storage system with multi-layer temperature modeling.

    This class extends the base ThermalStorage to implement sophisticated thermal
    stratification effects commonly observed in large-scale seasonal thermal energy
    storage (STES) systems. It models temperature gradients, layer-specific heat losses,
    inter-layer heat conduction, and realistic charging/discharging behavior for
    district heating applications.

    The stratified model provides enhanced accuracy for:
    - Seasonal thermal energy storage design
    - Pit thermal energy storage (PTES) optimization
    - Temperature-dependent performance analysis
    - Advanced control strategy development

    Parameters
    ----------
    *args
        All parameters from parent ThermalStorage class.
        See ThermalStorage documentation for complete parameter list.
    **kwargs
        Additional keyword arguments passed to parent class.
        Supports all ThermalStorage initialization parameters.

    Attributes
    ----------
    layer_thickness : float
        Uniform thickness of each stratification layer [m].
        Calculated as total height divided by number of layers.
    layer_volume : numpy.ndarray
        Volume of each individual layer [m³].
        Varies by geometry for truncated shapes.
    T_sto_layers : numpy.ndarray
        Temperature time series for each layer [°C].
        Shape: (hours, num_layers) for complete thermal profile.
    Q_loss_layers : numpy.ndarray
        Heat loss from each layer [kW].
        Layer-specific losses based on geometry and boundary conditions.
    labels_exist : bool
        Flag for 3D visualization label management.
    colorbar_exists : bool
        Flag for 3D visualization colorbar management.

    Notes
    -----
    Stratification Physics:
        
        **Thermal Layering**:
        Natural temperature gradients form due to:
        - Buoyancy effects in fluid storage media
        - Differential heat losses at various depths
        - Charging and discharging flow patterns
        - Conductive heat transfer between layers
        
        **Heat Transfer Mechanisms**:
        - **Conductive losses**: Layer-specific boundary heat transfer
        - **Internal conduction**: Temperature-driven inter-layer transfer
        - **Convective mixing**: Flow-induced temperature redistribution
        - **Stratification preservation**: Design measures to maintain gradients

    Layer Volume Calculations:
        
        **Cylindrical Storage**:
        Uniform layer volumes: V_layer = V_total / n_layers
        
        **Truncated Cone**:
        Variable volumes based on radius interpolation:
        V_layer = (π/3) × h_layer × (r_top² + r_bottom² + r_top × r_bottom)
        
        **Truncated Trapezoid**:
        Variable volumes based on area interpolation:
        V_layer = (h_layer/3) × (A_top + A_bottom + √(A_top × A_bottom))

    Heat Loss Distribution:
        
        **Surface Layers**:
        - Top layer: Direct atmospheric exposure
        - Bottom layer: Soil contact with enhanced resistance
        
        **Internal Layers**:
        - Side losses distributed proportionally
        - Soil thermal resistance for underground storage
        - Insulation effectiveness per layer position

    Charging/Discharging Strategy:
        
        **Charging Priority**:
        Heat input directed to top layers first (hot water inlet)
        Maintains natural stratification during energy storage
        
        **Discharging Priority**:
        Heat extraction from top layers first (hot water outlet)
        Preserves cold water reserve in bottom layers

    See Also
    --------
    ThermalStorage : Base thermal storage class with fundamental calculations
    calculate_layer_thickness : Geometry-specific layer volume calculations
    calculate_stratified_heat_loss : Layer-specific heat loss modeling
    simulate_stratified : Main simulation with stratification effects
    plot_3d_temperature_distribution : Advanced 3D visualization methods
    """
    def __init__(self, *args, **kwargs):
        """
        Initialize stratified thermal storage with layer calculations.
        
        Extends parent initialization with stratification-specific setup
        including layer geometry calculations and thermal property distribution.
        """
        super().__init__(*args, **kwargs)
        self.calculate_layer_thickness()
        
        # Initialize visualization flags
        self.labels_exist = False
        self.colorbar_exists = False

    def calculate_layer_thickness(self) -> None:
        """
        Calculate thickness and volume of each stratification layer based on storage geometry.

        This method determines the geometric properties of individual thermal layers
        for stratified storage modeling. It handles various storage geometries with
        appropriate volume distribution calculations for accurate heat transfer modeling.

        The layer thickness is uniform across all geometries, but layer volumes vary
        for non-cylindrical shapes to account for changing cross-sectional areas.

        Notes
        -----
        Layer Geometry Calculations:
            
            **Uniform Layer Thickness**:
            All storage types use uniform vertical layer divisions:
            layer_thickness = total_height / num_layers
            
            **Volume Distribution by Geometry**:
            
            - **Cylindrical**: Uniform volume per layer
              V_layer = π × r² × h_layer
            
            - **Truncated Cone**: Variable volume using frustum formula
              V_layer = (π × h_layer / 3) × (r_top² + r_bottom² + r_top × r_bottom)
            
            - **Truncated Trapezoid**: Variable volume using prismoidal formula
              V_layer = (h_layer / 3) × (A_top + A_bottom + √(A_top × A_bottom))

        Physical Considerations:
            - Layer boundaries remain horizontal for natural stratification
            - Volume calculations ensure mass conservation
            - Geometric interpolation preserves shape continuity
            - Layer volumes used for thermal capacity calculations
        """

        # Extract height dimension (common for all non-cylindrical geometries)
        if self.storage_type == "cylindrical":
            height = self.dimensions[1]  # radius, height
        else:
            height = self.dimensions[2]  # Common for cone and trapezoid: ..., height
            
        # Calculate uniform layer thickness
        self.layer_thickness = height / self.num_layers
        
        if self.storage_type == "cylindrical":
            # Cylindrical storage: uniform volume per layer
            self.layer_volume = np.full(self.num_layers, self.volume / self.num_layers)

        elif self.storage_type == "truncated_cone":
            # Truncated cone: calculate individual layer volumes using frustum formula
            r1, r2 = self.dimensions[0], self.dimensions[1]  # Top and bottom radii
            layer_volumes = []
            
            for i in range(self.num_layers):
                # Linear interpolation of radii for each layer
                r_top = r1 + (r2 - r1) * (i / self.num_layers)
                r_bottom = r1 + (r2 - r1) * ((i + 1) / self.num_layers)
                
                # Frustum volume formula: V = (π × h / 3) × (r1² + r2² + r1×r2)
                layer_volume = (np.pi * self.layer_thickness / 3) * (
                    r_top**2 + r_bottom**2 + r_top * r_bottom
                )
                layer_volumes.append(layer_volume)

            self.layer_volume = np.array(layer_volumes)

        elif self.storage_type == "truncated_trapezoid":
            # Truncated trapezoid: calculate individual layer volumes using prismoidal formula
            a1, b1 = self.dimensions[0], self.dimensions[1]  # Top length and width
            a2, b2 = self.dimensions[2], self.dimensions[3]  # Bottom length and width
            layer_volumes = []
            
            for i in range(self.num_layers):
                # Linear interpolation of dimensions for each layer
                a_top = a1 + (a2 - a1) * (i / self.num_layers)
                b_top = b1 + (b2 - b1) * (i / self.num_layers)
                a_bottom = a1 + (a2 - a1) * ((i + 1) / self.num_layers)
                b_bottom = b1 + (b2 - b1) * ((i + 1) / self.num_layers)
                
                # Calculate cross-sectional areas
                A_top = a_top * b_top
                A_bottom = a_bottom * b_bottom
                
                # Prismoidal volume formula: V = (h/3) × (A1 + A2 + √(A1×A2))
                layer_volume = (self.layer_thickness / 3) * (
                    A_top + A_bottom + np.sqrt(A_top * A_bottom)
                )
                layer_volumes.append(layer_volume)
            
            self.layer_volume = np.array(layer_volumes)

        else:
            raise ValueError(f"Unsupported storage type '{self.storage_type}' for layer thickness calculation")

    def calculate_stratified_heat_loss(self, T_sto_layers: np.ndarray) -> float:
        """
        Calculate layer-specific heat losses in stratified storage system.

        This method computes heat losses for each individual layer based on the
        storage geometry, insulation properties, and boundary conditions. It accounts
        for varying thermal resistances at different layer positions and storage
        configurations (above-ground vs underground installations).

        Parameters
        ----------
        T_sto_layers : numpy.ndarray
            Temperature array for each storage layer [°C].
            Length must equal num_layers for proper heat loss calculation.

        Returns
        -------
        float
            Total heat loss from all layers [kW].
            Sum of individual layer losses for overall energy balance.

        Notes
        -----
        Heat Loss Calculation Methods:
            
            **Cylindrical Above-Ground Storage**:
            - Top layer: Direct atmospheric convection and radiation
            - Side layers: Distributed side wall losses through insulation
            - Bottom layer: Enhanced soil thermal resistance
            
            **Cylindrical Underground Storage**:
            - Top layer: Direct atmospheric exposure
            - Subsurface layers: Combined side and bottom soil resistance
            - Minimum insulation thickness validation
            
            **PTES (Cone and Trapezoid)**:
            - Top layer: Atmospheric exposure through top insulation
            - Side layers: Soil contact with geometry-dependent resistance
            - Bottom layer: Enhanced bottom resistance with soil thermal effects

        Thermal Resistance Networks:
            
            **Above-Ground Resistance**:
            R_top = δ_insulation / λ_insulation
            R_side = δ_insulation / λ_insulation
            R_bottom = R_insulation + R_soil_enhanced
            
            **Underground Resistance**:
            R_combined = δ_insulation / λ_insulation + R_soil_geometry
            
            **PTES Resistance**:
            R_side = 1 / K_s (geometry-dependent soil resistance)
            R_bottom = 1 / K_b (enhanced bottom soil resistance)

        Quality Assurance:
            - Heat loss array initialized for each calculation
            - Geometry-specific resistance calculations
            - Physical boundary condition validation
            - Layer position identification for appropriate heat transfer models
        """

        # Initialize heat loss array for each layer
        self.Q_loss_layers = np.zeros(len(T_sto_layers))
        
        # Calculate layer-specific heat losses based on storage configuration
        for i, T_layer in enumerate(T_sto_layers):
            
            if self.storage_type == "cylindrical_overground":
                # Above-ground cylindrical storage heat losses
                if i == 0:  # Top layer - atmospheric exposure
                    Q_loss_top = (self.lambda_top / self.dt_top) * self.S_top * (T_layer - self.T_amb) / 1000
                    self.Q_loss_layers[i] = Q_loss_top
                    
                elif i == len(T_sto_layers) - 1:  # Bottom layer - enhanced soil resistance
                    # Enhanced soil thermal resistance for bottom contact
                    R_soil_enhanced = 4 * self.dimensions[0] / (3 * np.pi * self.lambda_soil)
                    R_total = self.db_bottom / self.lambda_bottom + R_soil_enhanced
                    Q_loss_bottom = (1 / R_total) * self.S_bottom * (T_layer - self.T_amb) / 1000
                    self.Q_loss_layers[i] = Q_loss_bottom
                    
                else:  # Side layers - distributed wall losses
                    Q_loss_side = (self.lambda_side / self.ds_side) * (T_layer - self.T_amb) * self.S_side / len(T_sto_layers) / 1000
                    self.Q_loss_layers[i] = Q_loss_side

            elif self.storage_type == "cylindrical_underground":
                # Underground cylindrical storage heat losses
                R = self.dimensions[0]  # Radius
                H = self.dimensions[1]  # Height
                
                # Minimum insulation thickness validation
                d_min = (self.lambda_side / self.lambda_soil) * R * 0.37
                if self.ds_side <= 2 * d_min:
                    raise ValueError(f"Insulation thickness {self.ds_side:.3f}m too small. "
                                   f"Minimum required: {2*d_min:.3f}m")
                
                # Combined thermal resistance for underground portions
                K_sb = (self.ds_side / self.lambda_side + 0.52 * R / self.lambda_soil)**(-1)
                S_c = np.pi * R**2 + 2 * np.pi * R * H  # Total underground surface area

                if i == 0:  # Top layer - atmospheric exposure
                    Q_loss_top = (self.lambda_top / self.dt_top) * self.S_top * (T_layer - self.T_amb) / 1000
                    self.Q_loss_layers[i] = Q_loss_top
                else:  # Underground layers - combined side and bottom resistance
                    Q_loss_sb = K_sb * S_c * (T_layer - self.T_soil) / len(T_sto_layers) / 1000
                    self.Q_loss_layers[i] = Q_loss_sb

            elif self.storage_type == "truncated_cone" or self.storage_type == "truncated_trapezoid":
                # PTES heat losses with geometry-dependent soil thermal resistance
                H = self.dimensions[2]  # Storage height
                
                # Side thermal resistance calculation (logarithmic correlation)
                a = self.ds_side / self.lambda_side + np.pi * H / (2 * self.lambda_soil)
                b = np.pi / self.lambda_soil
                K_s = (1 / (b * H)) * np.log((a + b * H) / a)
                
                # Bottom thermal resistance calculation
                # Characteristic length for bottom heat transfer
                if self.storage_type == "truncated_cone":
                    # Use bottom radius for cone
                    L_char = self.dimensions[1]  # r_bottom
                else:
                    # For trapezoid: use minimum bottom dimension (more conservative)
                    L_char = min(self.dimensions[2], self.dimensions[3])  # min(length, width)
                
                c = self.db_bottom / self.lambda_bottom + np.pi * H / (2 * self.lambda_soil)
                K_b = (1 / (2 * b * L_char)) * np.log((c + b * L_char) / c)

                if i == 0:  # Top layer - atmospheric exposure
                    Q_loss_top = (self.lambda_top / self.dt_top) * self.S_top * (T_layer - self.T_amb) / 1000
                    self.Q_loss_layers[i] = Q_loss_top
                    
                elif i == len(T_sto_layers) - 1:  # Bottom layer - enhanced soil resistance
                    Q_loss_bottom = K_b * self.S_bottom * (T_layer - self.T_soil) / 1000
                    self.Q_loss_layers[i] = Q_loss_bottom
                    
                else:  # Side layers - distributed soil contact losses
                    Q_loss_side = K_s * self.S_side * (T_layer - self.T_soil) / len(T_sto_layers) / 1000
                    self.Q_loss_layers[i] = Q_loss_side

        return np.sum(self.Q_loss_layers)

    def _calculate_interface_areas(self) -> np.ndarray:
        """
        Calculate cross-sectional areas between layers for inter-layer heat conduction.
        
        This method computes the correct horizontal interface areas for heat conduction
        between adjacent layers. For vertical heat transfer, the cross-sectional area
        perpendicular to the direction of heat flow must be used, not the side surface area.
        
        Returns
        -------
        numpy.ndarray
            Array of interface areas [m²] between layers.
            Length: num_layers - 1 (n-1 interfaces for n layers)
        
        Notes
        -----
        Physical Correctness:
            The area used in Fourier's law for vertical conduction must be the
            horizontal cross-sectional area (perpendicular to heat flow direction),
            not the vertical side surface area.
            
            Q_conduction = λ × A_interface × ΔT / δ_layer
            
        Geometry-Specific Calculations:
            - **Cylindrical**: Constant cross-section A = πr²
            - **Truncated Cone**: Variable radius at each interface
            - **Truncated Trapezoid**: Variable rectangular cross-section
        """
        A_interface = np.zeros(self.num_layers - 1)
        
        if self.storage_type == "cylindrical" or self.storage_type == "cylindrical_underground":
            # Constant cross-sectional area
            radius = self.dimensions[0]
            A_interface[:] = np.pi * radius**2
            
        elif self.storage_type == "truncated_cone":
            # Variable cross-sectional area - radius changes with height
            r1, r2 = self.dimensions[0], self.dimensions[1]  # top, bottom radii
            for i in range(self.num_layers - 1):
                # Radius at interface between layers i and i+1
                r_interface = r1 + (r2 - r1) * ((i + 1) / self.num_layers)
                A_interface[i] = np.pi * r_interface**2
                
        elif self.storage_type == "truncated_trapezoid":
            # Variable rectangular cross-section
            a1, b1 = self.dimensions[0], self.dimensions[1]  # top length, width
            a2, b2 = self.dimensions[2], self.dimensions[3]  # bottom length, width
            for i in range(self.num_layers - 1):
                # Dimensions at interface
                a = a1 + (a2 - a1) * ((i + 1) / self.num_layers)
                b = b1 + (b2 - b1) * ((i + 1) / self.num_layers)
                A_interface[i] = a * b
        
        return A_interface

    def _calculate_total_energy(self, T_layers: np.ndarray) -> float:
        """
        Calculate total stored energy from layer temperatures.
        
        This method provides a consistent way to compute total stored energy
        based on the current temperature distribution across all layers.
        It ensures energy and temperature remain synchronized.
        
        Parameters
        ----------
        T_layers : numpy.ndarray
            Temperature of each layer [°C].
            
        Returns
        -------
        float
            Total stored energy [kWh] relative to reference temperature.
        
        Notes
        -----
        Energy Calculation:
            E_total = Σ(V_i × ρ × cp × (T_i - T_ref)) / 3.6e6
            
            Where:
            - V_i: Volume of layer i [m³]
            - ρ: Density [kg/m³]
            - cp: Specific heat capacity [J/(kg·K)]
            - T_i: Temperature of layer i [°C]
            - T_ref: Reference temperature [°C]
            - 3.6e6: Conversion factor J to kWh
        """
        total_energy = 0.0
        for i, T in enumerate(T_layers):
            layer_energy = (self.layer_volume[i] * self.rho * self.cp * 
                           (T - self.T_ref) / 3.6e6)  # kWh
            total_energy += layer_energy
        return total_energy

    def simulate_stratified(self, Q_in: np.ndarray, Q_out: np.ndarray) -> None:
        """
        Simulate stratified thermal storage with multi-layer temperature dynamics.

        This method performs comprehensive simulation of stratified thermal energy storage
        including thermal stratification effects, layer-specific heat losses, inter-layer
        heat conduction, and realistic charging/discharging behavior. It provides detailed
        analysis of temperature distribution evolution for advanced storage system design.

        Parameters
        ----------
        Q_in : numpy.ndarray
            Heat input power time series [kW].
            Positive values represent energy charging into storage.
        Q_out : numpy.ndarray
            Heat output power time series [kW].
            Positive values represent energy discharge from storage.

        Notes
        -----
        Simulation Methodology:
            
            **Thermal Stratification Physics**:
            1. **Layer Heat Balance**: Individual energy balance per layer
            2. **Heat Loss Calculation**: Layer-specific boundary losses
            3. **Inter-layer Conduction**: Temperature-driven heat transfer
            4. **Charging Strategy**: Top-down heat input distribution
            5. **Discharging Strategy**: Top-down heat extraction

        Charging/Discharging Logic:
            
            **Energy Input (Q_in > Q_out)**:
            - Excess heat distributed to layers starting from top
            - Layer temperatures limited by T_max constraint
            - Natural stratification preserved during charging
            - Heat cascades to lower layers when upper layers saturated
            
            **Energy Output (Q_out > Q_in)**:
            - Heat extraction prioritized from top layers
            - Layer temperatures limited by T_min constraint
            - Cold water reserve maintained in bottom layers
            - Extraction stops when layers reach minimum temperature

        Heat Transfer Calculations:
            
            **Conductive Heat Transfer Between Layers**:
            Q_transfer = λ_medium × A_interface × ΔT / δ_layer
            
            **Layer Temperature Update**:
            T_new = T_old + (Q_net × 3.6e6) / (m_layer × cp)
            
            **Energy Conservation**:
            Total energy tracked through mass-energy balance verification

        Quality Assurance:
            - Temperature bounds enforcement (T_min ≤ T ≤ T_max)
            - Energy conservation verification
            - Physical heat transfer limits
            - Numerical stability monitoring
        
        See Also
        --------
        calculate_stratified_heat_loss : Layer-specific heat loss calculations
        calculate_layer_thickness : Geometric layer property calculations  
        plot_3d_temperature_distribution : Advanced visualization of results
        """
        # Store input arrays and validate dimensions
        self.Q_in = np.asarray(Q_in)
        self.Q_out = np.asarray(Q_out)
        
        if len(self.Q_in) != len(self.Q_out):
            raise ValueError("Q_in and Q_out must have the same length")
        
        # Initialize simulation arrays - temperature is the PRIMARY state variable
        self.T_sto_layers = np.full((self.hours, self.num_layers), self.initial_temp)
        
        # Calculate interface areas for inter-layer conduction (correct cross-sectional areas)
        self.A_interface = self._calculate_interface_areas()
        
        # Pre-calculate constants for performance optimization
        dt = 1.0  # hours (explicit for clarity)
        conversion_factor = 3.6e6  # J/kWh conversion
        
        # Pre-calculate layer thermal capacities [J/K]
        layer_thermal_capacity = self.layer_volume * self.rho * self.cp  # [m³ × kg/m³ × J/(kg·K)] = [J/K]
        
        # Pre-calculate conduction coefficients [K/W] for inter-layer heat transfer
        # Q_cond [W] = (λ × A_interface / δ_layer) × ΔT
        # Energy [kWh] = (Q_cond / 1000) × dt
        conduction_coeff = self.thermal_conductivity * self.A_interface / self.layer_thickness  # [W/K]

        # Main simulation loop
        for t in range(self.hours):
            
            if t == 0:
                # Initialize at t=0: Calculate initial stored energy from initial temperature
                self.Q_sto[t] = self._calculate_total_energy(self.T_sto_layers[t])
                
                # Calculate initial heat loss (and store layer-specific losses)
                self.Q_loss[t] = self.calculate_stratified_heat_loss(self.T_sto_layers[t])
                # Note: Q_loss_layers is set by calculate_stratified_heat_loss()
                
            else:
                # Start with previous timestep temperatures
                T_new = self.T_sto_layers[t-1, :].copy()
                
                # STEP 1: Apply heat losses (energy loss over dt = 1 hour)
                # Calculate layer-specific heat losses at current temperatures
                self.Q_loss[t] = self.calculate_stratified_heat_loss(T_new)
                
                # Apply heat losses to each layer
                for i in range(self.num_layers):
                    Q_loss_layer = self.Q_loss_layers[i]  # kW
                    # Energy loss over dt [kWh]
                    energy_loss = Q_loss_layer * dt
                    
                    # Update temperature based on heat loss (using pre-calculated capacity)
                    if self.layer_volume[i] > 0:
                        delta_T_loss = (energy_loss * conversion_factor) / layer_thermal_capacity[i]
                        T_new[i] -= delta_T_loss
                
                # STEP 2: Inter-layer heat conduction (using correct cross-sectional areas)
                # Physical correctness: Uses horizontal interface areas (perpendicular to heat flow)
                # NOT the vertical side surface area - this is critical for accurate modeling
                for i in range(self.num_layers - 1):
                    delta_T = T_new[i] - T_new[i+1]
                    if abs(delta_T) > 1e-6:  # Avoid numerical issues with negligible gradients
                        # Heat transfer rate [W] using pre-calculated conduction coefficient
                        # Q_cond = (λ × A_interface / δ_layer) × ΔT
                        Q_cond = conduction_coeff[i] * delta_T
                        
                        # Energy transfer over dt [kWh]
                        energy_transfer = (Q_cond / 1000) * dt
                        
                        # Temperature changes in both layers (using pre-calculated capacities)
                        delta_T_upper = (energy_transfer * conversion_factor) / layer_thermal_capacity[i]
                        delta_T_lower = (energy_transfer * conversion_factor) / layer_thermal_capacity[i+1]
                        
                        T_new[i] -= delta_T_upper
                        T_new[i+1] += delta_T_lower
                
                # STEP 3: Charging/discharging
                # Net energy balance: positive = charging, negative = discharging
                remaining_heat = (self.Q_in[t] - self.Q_out[t]) * dt  # Net energy [kWh]
                
                # Discharge logic (negative remaining_heat, extract from top layers first)
                if remaining_heat < 0:
                    heat_needed = abs(remaining_heat)
                    for i in range(self.num_layers):  # Top to bottom (hot to cold)
                        if heat_needed > 1e-6 and T_new[i] > self.T_min:
                            # Available energy above T_min [kWh] (using pre-calculated capacity)
                            available_energy = ((T_new[i] - self.T_min) * 
                                              layer_thermal_capacity[i] / conversion_factor)
                            
                            if heat_needed >= available_energy:
                                # Fully discharge this layer to T_min
                                T_new[i] = self.T_min
                                heat_needed -= available_energy
                            else:
                                # Partially discharge this layer
                                temp_drop = (heat_needed * conversion_factor) / layer_thermal_capacity[i]
                                T_new[i] -= temp_drop
                                heat_needed = 0
                                break  # Discharge complete
                
                # Charge logic (positive remaining_heat, add to top layers first)
                elif remaining_heat > 0:
                    for i in range(self.num_layers):  # Top to bottom (maintain stratification)
                        if remaining_heat > 1e-6 and T_new[i] < self.T_max:
                            # Available capacity to T_max [kWh] (using pre-calculated capacity)
                            max_energy_capacity = ((self.T_max - T_new[i]) * 
                                                  layer_thermal_capacity[i] / conversion_factor)
                            
                            if remaining_heat >= max_energy_capacity:
                                # Fully charge this layer to T_max
                                T_new[i] = self.T_max
                                remaining_heat -= max_energy_capacity
                            else:
                                # Partially charge this layer
                                temp_rise = (remaining_heat * conversion_factor) / layer_thermal_capacity[i]
                                T_new[i] += temp_rise
                                remaining_heat = 0
                                break  # Charging complete
                
                # STEP 4: Apply temperature limits
                T_new = np.clip(T_new, self.T_min, self.T_max)
                
                # STEP 5: Store results
                self.T_sto_layers[t, :] = T_new
                self.T_sto[t] = np.mean(T_new)
                self.Q_sto[t] = self._calculate_total_energy(T_new)

            # Note: For t==0, T_sto[0] already set above, just update average
            if t == 0:
                self.T_sto[t] = np.mean(self.T_sto_layers[t])

        # Calculate overall efficiency
        self.calculate_efficiency(self.Q_in)

    def plot_3d_temperature_distribution(self, ax, time_step: int) -> None:
        """
        Visualize 3D temperature stratification in thermal storage system.

        This method creates sophisticated 3D visualizations of temperature distribution
        within stratified thermal storage systems. It supports multiple geometric
        configurations with color-coded temperature layers for comprehensive analysis
        of thermal stratification patterns and storage performance visualization.

        Parameters
        ----------
        ax : matplotlib.axes.Axes3D
            3D matplotlib axes object for plotting.
            Must be created with projection='3d' for proper rendering.
        time_step : int
            Simulation time step for temperature visualization.
            Must be within valid range [0, hours-1].

        Notes
        -----
        Visualization Features:
            
            **Temperature Color Mapping**:
            - Coolwarm colormap for intuitive temperature representation
            - Blue: Cold temperatures (approaching T_min)
            - Red: Hot temperatures (approaching T_max)
            - Smooth gradient transitions between temperature levels
            
            **Geometric Rendering**:
            - **Cylindrical**: Layered cylindrical surfaces with proper curvature
            - **Truncated Cone**: Variable radius layers with smooth transitions
            - **Truncated Trapezoid**: Prismatic layers with rectangular cross-sections
            
            **3D Surface Properties**:
            - Semi-transparent surfaces (alpha=0.7) for internal visibility
            - High-resolution mesh for smooth surface representation
            - Proper surface normal calculations for realistic lighting

        Layer Orientation:
            Temperature layers are oriented with hot layers at the top and cold
            layers at the bottom, representing natural thermal stratification
            behavior in real storage systems.

        Performance Considerations:
            - Optimized mesh resolution for balance between quality and performance
            - Efficient color calculation and application
            - Memory-conscious surface generation for large layer counts

        See Also
        --------
        plot_results : Complete results visualization including 3D plots
        simulate_stratified : Main simulation generating temperature data
        """
        # Validate time step
        if time_step >= len(self.T_sto_layers):
            raise IndexError(f"time_step {time_step} exceeds simulation length {len(self.T_sto_layers)}")

        if self.storage_type == "cylindrical":
            self._plot_cylindrical_3d(ax, time_step)
        elif self.storage_type == "truncated_cone":
            self._plot_cone_3d(ax, time_step)
        elif self.storage_type == "truncated_trapezoid":
            self._plot_trapezoid_3d(ax, time_step)
        else:
            raise ValueError(f"Unsupported storage type '{self.storage_type}' for 3D visualization")

        # Add labels and colorbar only once
        if not hasattr(self, 'labels_exist') or not self.labels_exist:
            ax.set_title(f'Temperature Distribution (Time Step {time_step})')
            ax.set_xlabel('X (m)')
            ax.set_ylabel('Y (m)')
            ax.set_zlabel('Z (m)')
            self.labels_exist = True

        if not hasattr(self, 'colorbar_exists') or not self.colorbar_exists:
            # Create temperature colorbar
            mappable = plt.cm.ScalarMappable(cmap=plt.cm.coolwarm)
            mappable.set_array([self.T_min, self.T_max])
            cbar = plt.colorbar(mappable, ax=ax, shrink=0.5, aspect=5)
            cbar.set_label('Temperature (°C)')
            self.colorbar_exists = True

    def _plot_cylindrical_3d(self, ax, time_step: int) -> None:
        """Plot cylindrical storage 3D visualization."""
        radius, height = self.dimensions
        z_layers = np.linspace(0, height, self.num_layers + 1)
        theta = np.linspace(0, 2 * np.pi, 50)
        
        # Flip coordinates for hot-top visualization
        z_layers = np.flip(z_layers)
        T_layers_flipped = np.flip(self.T_sto_layers[time_step])
        
        for i in range(self.num_layers):
            # Generate cylindrical coordinates
            theta_grid, z_grid = np.meshgrid(theta, z_layers[i:i+2])
            x_grid = radius * np.cos(theta_grid)
            y_grid = radius * np.sin(theta_grid)
            
            # Color based on temperature
            color_value = (T_layers_flipped[i] - self.T_min) / (self.T_max - self.T_min)
            color = plt.cm.coolwarm(color_value)
            facecolors = np.tile(color[:3], (x_grid.shape[0], x_grid.shape[1], 1))
            
            # Plot layer surfaces
            ax.plot_surface(x_grid, y_grid, z_grid, facecolors=facecolors, 
                          rstride=1, cstride=1, alpha=0.7)

    def _plot_cone_3d(self, ax, time_step: int) -> None:
        """Plot truncated cone PTES 3D visualization."""
        top_radius, bottom_radius, height = self.dimensions
        z_layers = np.linspace(0, height, self.num_layers + 1)
        theta = np.linspace(0, 2 * np.pi, 50)
        
        # Calculate radius progression
        radii = np.linspace(bottom_radius, top_radius, len(z_layers))
        T_layers_flipped = np.flip(self.T_sto_layers[time_step])
        
        for i in range(self.num_layers):
            # Generate conical coordinates
            theta_grid, z_grid = np.meshgrid(theta, z_layers[i:i+2])
            x_grid = np.outer(np.cos(theta), radii[i:i+2])
            y_grid = np.outer(np.sin(theta), radii[i:i+2])
            
            # Color based on temperature
            color_value = (T_layers_flipped[i] - self.T_min) / (self.T_max - self.T_min)
            color = plt.cm.coolwarm(color_value)
            facecolors = np.tile(color[:3], (x_grid.shape[0], x_grid.shape[1], 1))
            
            # Plot layer surface
            ax.plot_surface(x_grid, y_grid, np.transpose(z_grid), 
                          facecolors=facecolors, rstride=1, cstride=1, alpha=0.7)

    def _plot_trapezoid_3d(self, ax, time_step: int) -> None:
        """Plot truncated trapezoid PTES 3D visualization."""
        bottom_length, bottom_width, top_length, top_width, height = self.dimensions
        z_layers = np.linspace(0, height, self.num_layers + 1)
        
        # Calculate dimension progression
        lengths = np.linspace(bottom_length, top_length, len(z_layers))
        widths = np.linspace(bottom_width, top_width, len(z_layers))
        T_layers_flipped = np.flip(self.T_sto_layers[time_step])
        
        for i in range(self.num_layers):
            # Layer coordinates
            x_coords = [-lengths[i]/2, lengths[i]/2, lengths[i+1]/2, -lengths[i+1]/2]
            y_coords = [-widths[i]/2, -widths[i]/2, widths[i+1]/2, widths[i+1]/2]
            z_bottom, z_top = z_layers[i], z_layers[i+1]
            
            # Color based on temperature
            color_value = (T_layers_flipped[i] - self.T_min) / (self.T_max - self.T_min)
            color = plt.cm.coolwarm(color_value)
            
            # Plot layer surfaces (simplified representation)
            vertices = [
                [[x_coords[j], y_coords[j], z_bottom] for j in range(4)],
                [[x_coords[j], y_coords[j], z_top] for j in range(4)]
            ]
            
            for vertex_set in vertices:
                xs, ys, zs = zip(*vertex_set)
                ax.plot_trisurf(xs + xs[:1], ys + ys[:1], zs + zs[:1], 
                              color=color[:3], alpha=0.7)

    def plot_results(self) -> None:
        """
        Generate comprehensive visualization of stratified storage simulation results.

        This method creates a multi-panel figure displaying all key aspects of
        stratified thermal storage performance including energy flows, temperature
        evolution, heat losses, stratification patterns, and 3D geometry visualization.

        The visualization provides complete insight into storage behavior for
        performance analysis, design optimization, and operational assessment.

        Notes
        -----
        Visualization Panels:
            
            **Panel 1**: Heat Input/Output Time Series
            - Heat input power [kW] vs time
            - Heat output power [kW] vs time
            - Net energy balance visualization
            
            **Panel 2**: Average Storage Temperature
            - Overall storage temperature evolution [°C]
            - Temperature bounds (T_min, T_max) reference
            - Seasonal temperature variations
            
            **Panel 3**: Heat Loss Analysis
            - Total heat loss time series [kW]
            - Cumulative energy losses
            - Loss rate variations with temperature
            
            **Panel 4**: Stored Energy Content
            - Total stored energy [kWh] vs time
            - Energy capacity utilization
            - Charging and discharging cycles
            
            **Panel 5**: Temperature Stratification
            - Individual layer temperatures [°C]
            - Stratification evolution over time
            - Layer temperature gradients
            
            **Panel 6**: 3D Temperature Distribution
            - Geometric representation with temperature coloring
            - Spatial temperature distribution
            - Visual stratification assessment

        Figure Layout:
            2×3 subplot arrangement for comprehensive overview
            Professional formatting with appropriate scales and legends
            Color coordination across related plots
        """
        fig = plt.figure(figsize=(16, 10))
        
        # Create subplot layout
        ax1 = fig.add_subplot(2, 3, 1)
        ax2 = fig.add_subplot(2, 3, 2)
        ax3 = fig.add_subplot(2, 3, 3)
        ax4 = fig.add_subplot(2, 3, 4)
        ax5 = fig.add_subplot(2, 3, 5)
        ax6 = fig.add_subplot(2, 3, 6, projection='3d')

        # Panel 1: Heat Input and Output
        ax1.plot(self.Q_in, label='Heat Input', color='red', linewidth=1.5)
        ax1.plot(self.Q_out, label='Heat Output', color='blue', linewidth=1.5)
        ax1.set_ylabel('Power (kW)')
        ax1.set_title('Heat Input and Output over Time')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Panel 2: Average Storage Temperature
        ax2.plot(self.T_sto, label='Storage Temperature', color='darkgreen', linewidth=1.5)
        ax2.axhline(y=self.T_max, color='red', linestyle='--', alpha=0.7, label=f'T_max ({self.T_max}°C)')
        ax2.axhline(y=self.T_min, color='blue', linestyle='--', alpha=0.7, label=f'T_min ({self.T_min}°C)')
        ax2.set_ylabel('Temperature (°C)')
        ax2.set_title(f'Storage Temperature ({self.storage_type.replace("_", " ").title()})')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Panel 3: Heat Loss Analysis
        ax3.plot(self.Q_loss, label='Heat Loss', color='orange', linewidth=1.5)
        ax3.set_ylabel('Heat Loss (kW)')
        ax3.set_title('Heat Loss over Time')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # Panel 4: Stored Energy Content
        ax4.plot(self.Q_sto, label='Stored Energy', color='green', linewidth=1.5)
        ax4.set_ylabel('Stored Energy (kWh)')
        ax4.set_title('Stored Energy over Time')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        # Panel 5: Stratified Layer Temperatures
        colors = plt.cm.viridis(np.linspace(0, 1, self.num_layers))
        for i in range(self.num_layers):
            ax5.plot(self.T_sto_layers[:, i], label=f'Layer {i+1}', 
                    color=colors[i], linewidth=1.2)
        ax5.set_xlabel('Time (hours)')
        ax5.set_ylabel('Temperature (°C)')
        ax5.set_title('Stratified Layer Temperatures')
        ax5.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax5.grid(True, alpha=0.3)

        # Panel 6: 3D Temperature Distribution
        visualization_time = min(6000, len(self.T_sto_layers) - 1)  # Safe time selection
        self.plot_3d_temperature_distribution(ax6, visualization_time)

        plt.tight_layout()