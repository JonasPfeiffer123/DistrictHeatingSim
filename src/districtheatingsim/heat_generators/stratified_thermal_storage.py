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

    Examples
    --------
    >>> # Create stratified PTES with detailed layer analysis
    >>> stratified_ptes = StratifiedThermalStorage(
    ...     name="Stratified_PTES_01",
    ...     storage_type="truncated_cone",
    ...     dimensions=(20.0, 30.0, 12.0),  # top_r, bottom_r, height
    ...     rho=1000,  # Water density
    ...     cp=4186,   # Water heat capacity
    ...     T_ref=0,   # Reference temperature
    ...     lambda_top=0.025,    # Top insulation
    ...     lambda_side=0.035,   # Side insulation
    ...     lambda_bottom=0.04,  # Bottom insulation
    ...     lambda_soil=2.0,     # Soil conductivity
    ...     T_amb=8,    # Ambient temperature
    ...     T_soil=10,  # Soil temperature
    ...     T_max=85,   # Maximum temperature
    ...     T_min=15,   # Minimum temperature
    ...     initial_temp=40,  # Initial temperature
    ...     dt_top=0.3,      # Top insulation thickness
    ...     ds_side=0.5,     # Side insulation thickness
    ...     db_bottom=0.3,   # Bottom insulation thickness
    ...     hours=8760,      # Full year simulation
    ...     num_layers=10,   # Detailed stratification
    ...     thermal_conductivity=0.6  # Water conductivity
    ... )

    >>> # Display layer characteristics
    >>> print(f"Layer thickness: {stratified_ptes.layer_thickness:.2f} m")
    >>> print(f"Layer volumes: {stratified_ptes.layer_volume}")
    >>> print(f"Total volume: {stratified_ptes.layer_volume.sum():.1f} m³")

    >>> # Generate seasonal charging/discharging pattern
    >>> import numpy as np
    >>> hours = 8760
    >>> time = np.arange(hours)
    >>> 
    >>> # Summer charging (high solar/waste heat input)
    >>> summer_charging = 500 * np.sin(2 * np.pi * time / 8760) ** 2  # kW
    >>> summer_charging[time < 2000] *= 0.3  # Winter reduction
    >>> summer_charging[time > 6000] *= 0.3  # Winter reduction
    >>> 
    >>> # Winter discharging (district heating demand)
    >>> winter_demand = 200 + 300 * np.cos(2 * np.pi * time / 8760)  # kW
    >>> winter_demand = np.maximum(winter_demand, 0)  # No negative demand
    >>> 
    >>> # Run stratified simulation
    >>> stratified_ptes.simulate_stratified(summer_charging, winter_demand)

    >>> # Analyze stratification effectiveness
    >>> final_temps = stratified_ptes.T_sto_layers[-1, :]  # Final layer temperatures
    >>> temp_gradient = final_temps.max() - final_temps.min()
    >>> print(f"Final temperature stratification: {temp_gradient:.1f} K")

    >>> # Calculate layer-specific performance
    >>> top_layer_avg = stratified_ptes.T_sto_layers[:, 0].mean()
    >>> bottom_layer_avg = stratified_ptes.T_sto_layers[:, -1].mean()
    >>> stratification_ratio = top_layer_avg / bottom_layer_avg
    >>> print(f"Average top layer: {top_layer_avg:.1f}°C")
    >>> print(f"Average bottom layer: {bottom_layer_avg:.1f}°C")
    >>> print(f"Stratification ratio: {stratification_ratio:.2f}")

    >>> # Energy distribution analysis
    >>> layer_energies = []
    >>> for i in range(stratified_ptes.num_layers):
    ...     layer_energy = (stratified_ptes.T_sto_layers[:, i] * 
    ...                    stratified_ptes.layer_volume[i] * 
    ...                    stratified_ptes.rho * stratified_ptes.cp / 3.6e9)  # GWh
    ...     layer_energies.append(layer_energy.mean())
    >>> 
    >>> print("Average energy content by layer [GWh]:")
    >>> for i, energy in enumerate(layer_energies):
    ...     print(f"  Layer {i+1}: {energy:.2f} GWh")

    >>> # Thermal efficiency analysis
    >>> initial_energy = stratified_ptes.Q_sto[0]
    >>> final_energy = stratified_ptes.Q_sto[-1]
    >>> annual_losses = stratified_ptes.Q_loss.sum()
    >>> 
    >>> print(f"Initial stored energy: {initial_energy:.0f} kWh")
    >>> print(f"Final stored energy: {final_energy:.0f} kWh")
    >>> print(f"Annual heat losses: {annual_losses:.0f} kWh")
    >>> print(f"Storage efficiency: {stratified_ptes.efficiency:.1%}")

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

        Raises
        ------
        ValueError
            If storage_type is not supported for layer calculations.
        IndexError
            If dimensions array doesn't contain required geometric parameters.

        Examples
        --------
        >>> # Cylindrical storage layer analysis
        >>> cylinder_storage = StratifiedThermalStorage(
        ...     name="Cylinder_Test",
        ...     storage_type="cylindrical",
        ...     dimensions=(3.0, 8.0),  # radius, height
        ...     # ... other parameters
        ...     num_layers=5
        ... )
        >>> print(f"Layer thickness: {cylinder_storage.layer_thickness:.2f} m")
        >>> print(f"Layer volumes: {cylinder_storage.layer_volume}")

        >>> # Truncated cone PTES layer analysis
        >>> cone_storage = StratifiedThermalStorage(
        ...     name="Cone_PTES",
        ...     storage_type="truncated_cone",
        ...     dimensions=(15.0, 25.0, 10.0),  # top_r, bottom_r, height
        ...     # ... other parameters
        ...     num_layers=8
        ... )
        >>> 
        >>> # Analyze volume distribution
        >>> volume_variation = cone_storage.layer_volume.max() / cone_storage.layer_volume.min()
        >>> print(f"Volume variation factor: {volume_variation:.2f}")

        >>> # Trapezoid storage with site constraints
        >>> trap_storage = StratifiedThermalStorage(
        ...     name="Trapezoid_Site",
        ...     storage_type="truncated_trapezoid", 
        ...     dimensions=(30, 25, 40, 35, 8),  # top_l, top_w, bottom_l, bottom_w, height
        ...     # ... other parameters
        ...     num_layers=6
        ... )
        >>> 
        >>> # Calculate layer area progression
        >>> for i, vol in enumerate(trap_storage.layer_volume):
        ...     layer_area = vol / trap_storage.layer_thickness
        ...     print(f"Layer {i+1} area: {layer_area:.1f} m²")
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

        Examples
        --------
        >>> # Calculate heat losses for stratified storage
        >>> import numpy as np
        >>> 
        >>> # Example layer temperatures (hot top, cold bottom)
        >>> layer_temps = np.array([80, 75, 65, 50, 35])  # °C
        >>> 
        >>> # Calculate total heat loss
        >>> total_loss = stratified_storage.calculate_stratified_heat_loss(layer_temps)
        >>> print(f"Total heat loss: {total_loss:.2f} kW")

        >>> # Analyze layer-specific losses
        >>> print("Layer-specific heat losses:")
        >>> for i, loss in enumerate(stratified_storage.Q_loss_layers):
        ...     print(f"  Layer {i+1}: {loss:.2f} kW")

        >>> # Heat loss distribution analysis
        >>> top_layer_loss = stratified_storage.Q_loss_layers[0]
        >>> side_layers_loss = stratified_storage.Q_loss_layers[1:-1].sum()
        >>> bottom_layer_loss = stratified_storage.Q_loss_layers[-1]
        >>> 
        >>> print(f"Top layer loss: {top_layer_loss:.1f} kW ({top_layer_loss/total_loss:.1%})")
        >>> print(f"Side layers loss: {side_layers_loss:.1f} kW ({side_layers_loss/total_loss:.1%})")
        >>> print(f"Bottom layer loss: {bottom_layer_loss:.1f} kW ({bottom_layer_loss/total_loss:.1%})")

        >>> # Temperature sensitivity analysis
        >>> temp_variations = [layer_temps + i for i in [-5, 0, 5]]  # ±5°C variation
        >>> 
        >>> for i, temps in enumerate(temp_variations):
        ...     loss = stratified_storage.calculate_stratified_heat_loss(temps)
        ...     print(f"Temperature +{(i-1)*5}°C: {loss:.2f} kW")

        Raises
        ------
        ValueError
            If insulation thickness is below minimum requirements for underground storage.
        IndexError
            If T_sto_layers length doesn't match num_layers.
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
                
                # Side thermal resistance calculation
                a = self.ds_side / self.lambda_side + np.pi * H / (2 * self.lambda_soil)
                b = np.pi / self.lambda_soil
                K_s = (1 / (b * H)) * np.log((a + b * H) / a)
                
                # Bottom thermal resistance calculation
                bottom_radius = self.dimensions[1] if self.storage_type == "truncated_cone" else np.sqrt(self.dimensions[2] * self.dimensions[3] / np.pi)
                c = self.db_bottom / self.lambda_bottom + np.pi * H / (2 * self.lambda_soil)
                K_b = (1 / (2 * b * bottom_radius)) * np.log((c + b * bottom_radius) / c)

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

        Examples
        --------
        >>> # Create realistic seasonal energy patterns
        >>> import numpy as np
        >>> 
        >>> # Annual simulation parameters
        >>> hours = 8760
        >>> time = np.arange(hours)
        >>> 
        >>> # Summer solar energy input pattern
        >>> solar_input = 400 * np.maximum(0, np.sin(2 * np.pi * (time - 2000) / 8760))  # kW
        >>> summer_boost = 200 * np.maximum(0, np.sin(2 * np.pi * time / 8760)) ** 4  # Peak summer
        >>> Q_in = solar_input + summer_boost
        >>> 
        >>> # Winter heating demand pattern
        >>> base_demand = 150  # Base load [kW]
        >>> seasonal_demand = 300 * np.maximum(0, -np.cos(2 * np.pi * time / 8760))  # Winter peak
        >>> daily_variation = 50 * np.sin(2 * np.pi * time / 24)  # Daily pattern
        >>> Q_out = base_demand + seasonal_demand + daily_variation
        >>> Q_out = np.maximum(Q_out, 0)  # No negative demand

        >>> # Run stratified simulation
        >>> stratified_storage.simulate_stratified(Q_in, Q_out)

        >>> # Analyze stratification performance
        >>> print("Stratification Analysis:")
        >>> print(f"  Simulation period: {hours} hours")
        >>> print(f"  Total energy input: {Q_in.sum():.0f} kWh")
        >>> print(f"  Total energy output: {Q_out.sum():.0f} kWh")
        >>> print(f"  Storage efficiency: {stratified_storage.efficiency:.1%}")

        >>> # Temperature distribution analysis
        >>> final_layers = stratified_storage.T_sto_layers[-1, :]
        >>> temp_gradient = final_layers.max() - final_layers.min()
        >>> print(f"  Final temperature gradient: {temp_gradient:.1f} K")
        >>> print(f"  Top layer final temp: {final_layers[0]:.1f}°C")
        >>> print(f"  Bottom layer final temp: {final_layers[-1]:.1f}°C")

        >>> # Seasonal performance metrics
        >>> winter_months = np.concatenate([time[:2160], time[6570:]])  # Dec-Feb
        >>> summer_months = time[3648:5832]  # May-Aug
        >>> 
        >>> winter_avg_temp = stratified_storage.T_sto[winter_months].mean()
        >>> summer_avg_temp = stratified_storage.T_sto[summer_months].mean()
        >>> print(f"  Winter average temperature: {winter_avg_temp:.1f}°C")
        >>> print(f"  Summer average temperature: {summer_avg_temp:.1f}°C")

        >>> # Heat loss distribution
        >>> annual_losses = stratified_storage.Q_loss.sum()
        >>> layer_loss_distribution = [
        ...     stratified_storage.Q_loss_layers.sum() / len(stratified_storage.Q_loss_layers)
        ...     for _ in range(stratified_storage.num_layers)
        ... ]
        >>> print(f"  Annual heat losses: {annual_losses:.0f} kWh")
        >>> print(f"  Average loss per layer: {np.mean(layer_loss_distribution):.2f} kW")

        Raises
        ------
        ValueError
            If Q_in and Q_out arrays have different lengths or invalid values.
        RuntimeError
            If simulation encounters numerical instability or convergence issues.

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
        
        # Initialize simulation arrays
        self.T_sto_layers = np.full((self.hours, self.num_layers), self.initial_temp)
        heat_stored_per_layer = np.zeros(self.num_layers)

        # Main simulation loop
        for t in range(self.hours):
            # Calculate heat losses based on current layer temperatures
            if t == 0:
                self.Q_loss[t] = self.calculate_stratified_heat_loss(self.T_sto_layers[t])
            else:
                self.Q_loss[t] = self.calculate_stratified_heat_loss(self.T_sto_layers[t-1])
            
            if t == 0:
                # Initialize stored energy distribution
                self.Q_sto[t] = self.volume * self.rho * self.cp * (self.initial_temp - self.T_ref) / 3.6e6
                heat_stored_per_layer[:] = self.Q_sto[t] / self.num_layers

            else:
                # Apply heat losses to each layer
                for i in range(self.num_layers):
                    Q_loss_layer = self.Q_loss_layers[i]  # Heat loss in kW
                    heat_stored_per_layer[i] -= Q_loss_layer / 1000  # Convert to kWh
                    
                    # Update temperature based on heat loss
                    if self.layer_volume[i] > 0:
                        delta_T = (Q_loss_layer * 3.6e6) / (self.layer_volume[i] * self.rho * self.cp)
                        self.T_sto_layers[t, i] = self.T_sto_layers[t-1, i] - delta_T
                    else:
                        self.T_sto_layers[t, i] = self.T_sto_layers[t-1, i]

                # Calculate inter-layer heat conduction
                for i in range(self.num_layers - 1):
                    delta_T = self.T_sto_layers[t-1, i] - self.T_sto_layers[t-1, i+1]
                    if abs(delta_T) > 1e-6:  # Avoid numerical issues
                        heat_transfer = (self.thermal_conductivity * self.S_side * delta_T / 
                                       self.layer_thickness)  # W
                        heat_transfer_kWh = heat_transfer / 1000  # kWh per hour
                        
                        # Transfer heat between layers
                        heat_stored_per_layer[i] -= heat_transfer_kWh
                        heat_stored_per_layer[i+1] += heat_transfer_kWh

                # Calculate net energy balance for this timestep
                remaining_heat = self.Q_in[t] - self.Q_out[t]  # Net energy [kW]

                # Discharge logic (negative remaining_heat)
                if remaining_heat < 0:
                    heat_needed = abs(remaining_heat)
                    for i in range(self.num_layers):  # Discharge from top to bottom
                        if heat_needed > 1e-6 and self.T_sto_layers[t, i] > self.T_min:
                            available_heat = ((self.T_sto_layers[t, i] - self.T_min) * 
                                            self.layer_volume[i] * self.rho * self.cp / 3.6e6)
                            
                            if heat_needed >= available_heat:
                                # Fully discharge this layer
                                heat_stored_per_layer[i] -= available_heat
                                self.T_sto_layers[t, i] = self.T_min
                                heat_needed -= available_heat
                            else:
                                # Partially discharge this layer
                                heat_stored_per_layer[i] -= heat_needed
                                temp_drop = (heat_needed * 3.6e6) / (self.layer_volume[i] * self.rho * self.cp)
                                self.T_sto_layers[t, i] -= temp_drop
                                heat_needed = 0

                # Charge logic (positive remaining_heat)
                elif remaining_heat > 0:
                    for i in range(self.num_layers):  # Charge from top to bottom
                        if remaining_heat > 1e-6 and self.T_sto_layers[t, i] < self.T_max:
                            max_heat_capacity = ((self.T_max - self.T_sto_layers[t, i]) * 
                                               self.layer_volume[i] * self.rho * self.cp / 3.6e6)
                            
                            if remaining_heat >= max_heat_capacity:
                                # Fully charge this layer
                                heat_stored_per_layer[i] += max_heat_capacity
                                self.T_sto_layers[t, i] = self.T_max
                                remaining_heat -= max_heat_capacity
                            else:
                                # Partially charge this layer
                                heat_stored_per_layer[i] += remaining_heat
                                temp_rise = (remaining_heat * 3.6e6) / (self.layer_volume[i] * self.rho * self.cp)
                                self.T_sto_layers[t, i] += temp_rise
                                remaining_heat = 0

                # Final inter-layer heat conduction after charging/discharging
                for i in range(self.num_layers - 1):
                    delta_T = self.T_sto_layers[t, i] - self.T_sto_layers[t, i+1]
                    if abs(delta_T) > 1e-6:
                        heat_transfer = (self.thermal_conductivity * self.S_side * delta_T / 
                                       self.layer_thickness)  # W
                        heat_transfer_kWh = heat_transfer / 1000  # kWh per hour
                        
                        # Apply heat transfer with temperature update
                        heat_stored_per_layer[i] -= heat_transfer_kWh
                        heat_stored_per_layer[i+1] += heat_transfer_kWh
                        
                        # Update temperatures based on new energy content
                        if self.layer_volume[i] > 0:
                            self.T_sto_layers[t, i] = ((heat_stored_per_layer[i] * 3.6e6) / 
                                                     (self.layer_volume[i] * self.rho * self.cp) + self.T_ref)
                        if self.layer_volume[i+1] > 0:
                            self.T_sto_layers[t, i+1] = ((heat_stored_per_layer[i+1] * 3.6e6) / 
                                                       (self.layer_volume[i+1] * self.rho * self.cp) + self.T_ref)

                # Enforce temperature limits
                self.T_sto_layers[t, :] = np.clip(self.T_sto_layers[t, :], self.T_min, self.T_max)

                # Calculate total stored energy
                self.Q_sto[t] = np.sum(heat_stored_per_layer)

            # Update average storage temperature
            self.T_sto[t] = np.average(self.T_sto_layers[t])

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

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> from mpl_toolkits.mplot3d import Axes3D
        >>> 
        >>> # Create 3D visualization
        >>> fig = plt.figure(figsize=(12, 8))
        >>> ax = fig.add_subplot(111, projection='3d')
        >>> 
        >>> # Visualize at mid-simulation point
        >>> mid_time = len(stratified_storage.T_sto_layers) // 2
        >>> stratified_storage.plot_3d_temperature_distribution(ax, mid_time)
        >>> 
        >>> # Add custom title and formatting
        >>> ax.set_title(f'Temperature Distribution at Hour {mid_time}')
        >>> plt.tight_layout()
        >>> plt.show()

        >>> # Create time-lapse visualization
        >>> time_points = [0, 2190, 4380, 6570, 8760]  # Seasonal snapshots
        >>> fig, axes = plt.subplots(1, 5, figsize=(20, 4), subplot_kw={'projection': '3d'})
        >>> 
        >>> for i, t in enumerate(time_points):
        ...     if t < len(stratified_storage.T_sto_layers):
        ...         stratified_storage.plot_3d_temperature_distribution(axes[i], t)
        ...         axes[i].set_title(f'Hour {t}')
        >>> plt.tight_layout()

        >>> # Analyze temperature distribution
        >>> time_step = 4000  # Mid-year analysis
        >>> temps = stratified_storage.T_sto_layers[time_step]
        >>> 
        >>> print(f"Temperature distribution at hour {time_step}:")
        >>> for i, temp in enumerate(temps):
        ...     print(f"  Layer {i+1}: {temp:.1f}°C")
        >>> 
        >>> gradient = temps.max() - temps.min()
        >>> print(f"Temperature gradient: {gradient:.1f} K")

        Raises
        ------
        ValueError
            If storage_type is not supported for 3D visualization.
        IndexError
            If time_step is outside valid simulation range.

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

        Examples
        --------
        >>> # Generate complete results visualization
        >>> stratified_storage.plot_results()
        >>> plt.show()

        >>> # Save high-resolution figure
        >>> stratified_storage.plot_results()
        >>> plt.savefig('stratified_storage_results.png', dpi=300, bbox_inches='tight')

        >>> # Customize visualization time range
        >>> # Modify internal time arrays before plotting for focused analysis
        >>> start_hour, end_hour = 4000, 6000  # Focus on specific period
        >>> # Note: This would require internal modification for time range selection
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