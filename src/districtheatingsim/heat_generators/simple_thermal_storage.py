"""
Simple Thermal Storage Module
=============================

This module provides comprehensive modeling capabilities for Seasonal Thermal Energy Storage (STES)
systems in district heating applications.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-10-09

It implements sophisticated heat transfer calculations,
geometric modeling for various storage configurations, and performance analysis tools for
large-scale thermal storage design and optimization.

The module is based on validated simulation methods from scientific literature and supports
multiple storage geometries including cylindrical tanks, pit thermal energy storage (PTES)
with truncated cone and trapezoid configurations, both above-ground and underground installations.

External References
-------------------
Simulation method for assessing hourly energy flows in district heating system with seasonal thermal energy storage
Authors: Kapil Narula, Fleury de Oliveira Filho, Willy Villasmil, Martin K. Patel
Journal: Renewable Energy, Volume 151, May 2020, Pages 1250-1268
DOI: https://doi.org/10.1016/j.renene.2019.11.121
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, Dict, Any, List, Optional, Union

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator

class ThermalStorage(BaseHeatGenerator):
    """
    Base class for thermal energy storage systems in district heating applications.

    This class provides the fundamental framework for modeling various types of thermal
    energy storage systems, including geometry calculations, heat transfer modeling,
    and performance analysis. It serves as the foundation for specialized storage
    implementations and supports multiple storage configurations commonly used in
    district heating systems.

    Parameters
    ----------
    name : str
        Unique identifier for the storage system.
    storage_type : str
        Type of storage geometry. Valid options:
        
        - **"cylindrical"** : Cylindrical tank storage
        - **"truncated_cone"** : Pit storage with conical shape
        - **"truncated_trapezoid"** : Pit storage with trapezoidal shape
        
    dimensions : tuple
        Geometric dimensions specific to storage type:
        
        - **Cylindrical**: (radius[m], height[m])
        - **Truncated cone**: (top_radius[m], bottom_radius[m], height[m])
        - **Truncated trapezoid**: (top_length[m], top_width[m], bottom_length[m], bottom_width[m], height[m])
        
    rho : float
        Density of storage medium [kg/m³]. Typical values:
        - Water: 1000 kg/m³
        - Water-glycol mixture: 1030-1100 kg/m³
        
    cp : float
        Specific heat capacity of storage medium [J/(kg·K)]. Typical values:
        - Water: 4186 J/(kg·K)
        - Water-glycol mixture: 3500-4000 J/(kg·K)
        
    T_ref : float
        Reference temperature for energy calculations [°C].
        Typically set to 0°C or minimum operating temperature.
        
    lambda_top : float
        Thermal conductivity of top insulation [W/(m·K)].
        Typical values: 0.02-0.05 W/(m·K) for high-performance insulation.
        
    lambda_side : float
        Thermal conductivity of side insulation [W/(m·K)].
        
    lambda_bottom : float
        Thermal conductivity of bottom insulation [W/(m·K)].
        
    lambda_soil : float
        Thermal conductivity of surrounding soil [W/(m·K)].
        Typical values: 1.0-2.5 W/(m·K) depending on soil type and moisture.
        
    T_amb : float
        Ambient air temperature [°C]. Can be constant or time-varying.
        
    T_soil : float
        Undisturbed soil temperature [°C]. Typically 8-12°C in temperate climates.
        
    T_max : float
        Maximum allowable storage temperature [°C].
        Limited by material properties and safety considerations.
        
    T_min : float
        Minimum allowable storage temperature [°C].
        Prevents freezing or operation below design limits.
        
    initial_temp : float
        Initial storage temperature at simulation start [°C].
        
    dt_top : float
        Thickness of top insulation layer [m].
        
    ds_side : float
        Thickness of side insulation layer [m].
        
    db_bottom : float
        Thickness of bottom insulation layer [m].
        
    hours : int, optional
        Number of simulation hours. Default is 8760 (one year).
        
    num_layers : int, optional
        Number of thermal stratification layers. Default is 5.
        Used for advanced stratified storage modeling.
        
    thermal_conductivity : float, optional
        Thermal conductivity of storage medium [W/(m·K)]. Default is 0.6.
        Water: ~0.6 W/(m·K), used for internal heat transfer calculations.

    Attributes
    ----------
    volume : float
        Total storage volume [m³] calculated from geometry.
    S_top : float
        Top surface area [m²] for heat loss calculations.
    S_side : float
        Side surface area [m²] for heat loss calculations.
    S_bottom : float
        Bottom surface area [m²] for heat loss calculations.
    Q_sto : numpy.ndarray
        Time series of stored thermal energy [J].
    Q_loss : numpy.ndarray
        Time series of heat losses [kW].
    T_sto : numpy.ndarray
        Time series of storage temperature [°C].
    efficiency : float
        Overall storage efficiency calculated after simulation.
    operational_costs : float
        Calculated operational costs based on energy losses.

    Notes
    -----
    Storage Design Considerations:
        
        **Geometry Selection**:
        - **Cylindrical**: Simple construction, uniform heat distribution
        - **Truncated cone**: Optimal for large-scale PTES, natural stratification
        - **Truncated trapezoid**: Flexible shape adaptation to site constraints

    See Also
    --------
    SimpleThermalStorage : Simplified storage model for basic applications
    StratifiedThermalStorage : Advanced stratified storage modeling
    calculate_operational_costs : Economic analysis of storage operation
    calculate_efficiency : Performance evaluation methods
    """

    def __init__(self, name: str, storage_type: str, dimensions: Tuple[float, ...], 
                 rho: float, cp: float, T_ref: float, lambda_top: float, 
                 lambda_side: float, lambda_bottom: float, lambda_soil: float, 
                 T_amb: float, T_soil: float, T_max: float, T_min: float, 
                 initial_temp: float, dt_top: float, ds_side: float, 
                 db_bottom: float, hours: int = 8760, num_layers: int = 5, 
                 thermal_conductivity: float = 0.6):
        super().__init__(name)
        self.storage_type = storage_type
        self.dimensions = dimensions
        self.rho = rho
        self.cp = cp
        self.T_ref = T_ref
        self.lambda_top = lambda_top
        self.lambda_side = lambda_side
        self.lambda_bottom = lambda_bottom
        self.lambda_soil = lambda_soil
        self.T_amb = T_amb
        self.T_soil = T_soil
        self.T_max = T_max
        self.T_min = T_min
        self.initial_temp = initial_temp
        self.dt_top = dt_top
        self.ds_side = ds_side
        self.db_bottom = db_bottom
        self.hours = hours
        self.num_layers = num_layers
        self.thermal_conductivity = thermal_conductivity
        self.Q_sto = np.zeros(hours)
        self.Q_loss = np.zeros(hours)
        self.T_sto = np.zeros(hours)
        self.T_sto[0] = initial_temp
        
        # Calculate geometry-dependent properties
        if storage_type == "cylindrical_overground" or storage_type == "cylindrical_underground":
            self.volume, self.S_top, self.S_side, self.S_bottom = self.calculate_cylindrical_geometry(dimensions)
        elif storage_type == "truncated_cone":
            self.volume, self.S_top, self.S_side, self.S_bottom = self.calculate_truncated_cone_geometry(dimensions)
        elif storage_type == "truncated_trapezoid":
            self.volume, self.S_top, self.S_side, self.S_bottom = self.calculate_truncated_trapezoid_geometry(dimensions)
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")

        self.colorbar_exists = False
        self.labels_exist = False

    def calculate_cylindrical_geometry(self, dimensions: Tuple[float, float]) -> Tuple[float, float, float, float]:
        """
        Calculate geometric properties for cylindrical thermal storage.

        This method computes the volume and surface areas for cylindrical storage tanks,
        which are commonly used for short-term and medium-term thermal storage in
        district heating systems. Cylindrical geometry provides uniform heat distribution
        and simplified construction compared to more complex pit storage designs.

        Parameters
        ----------
        dimensions : Tuple[float, float]
            Cylindrical tank dimensions (radius[m], height[m]).
            
            - **radius** : Tank radius [m], typically 2-50m for district heating
            - **height** : Tank height [m], typically 5-30m depending on application

        Returns
        -------
        Tuple[float, float, float, float]
            Geometric properties for heat transfer calculations:
            
            - **volume** (float) : Storage volume [m³]
            - **S_top** (float) : Top surface area [m²]
            - **S_side** (float) : Cylindrical side surface area [m²]
            - **S_bottom** (float) : Bottom surface area [m²]

        See Also
        --------
        calculate_truncated_cone_geometry : Conical pit storage geometry
        calculate_truncated_trapezoid_geometry : Trapezoidal pit storage geometry
        SimpleThermalStorage.calculate_heat_loss : Heat loss calculations using surface areas
        """

        radius, height = dimensions
        volume = np.pi * radius**2 * height
        S_top = np.pi * radius**2
        S_side = 2 * np.pi * radius * height
        S_bottom = S_top  # Same as top for cylinder
        return volume, S_top, S_side, S_bottom

    def calculate_truncated_cone_geometry(self, dimensions: Tuple[float, float, float]) -> Tuple[float, float, float, float]:
        """
        Calculate geometric properties for truncated cone Pit Thermal Energy Storage (PTES).

        This method computes volume and surface areas for conical pit storage systems,
        which are widely used for large-scale seasonal thermal energy storage in
        district heating systems. The truncated cone geometry provides excellent
        structural stability and optimal thermal stratification for long-term storage.

        Parameters
        ----------
        dimensions : Tuple[float, float, float]
            Truncated cone dimensions (top_radius[m], bottom_radius[m], height[m]).
            
            - **top_radius** : Radius at top surface [m], typically 15-50m
            - **bottom_radius** : Radius at bottom [m], typically 20-60m  
            - **height** : Depth of pit storage [m], typically 10-30m

        Returns
        -------
        Tuple[float, float, float, float]
            Geometric properties for thermal analysis:
            
            - **volume** (float) : Storage volume [m³]
            - **S_top** (float) : Top surface area [m²]
            - **S_side** (float) : Conical side surface area [m²]
            - **S_bottom** (float) : Bottom surface area [m²]

        See Also
        --------
        calculate_cylindrical_geometry : Cylindrical tank geometry
        calculate_truncated_trapezoid_geometry : Alternative pit storage geometry
        SimpleThermalStorage.calculate_heat_loss : PTES-specific heat loss calculations
        """

        top_radius, bottom_radius, height = dimensions
        
        # Volume using truncated cone formula
        volume = (1/3) * np.pi * height * (top_radius**2 + bottom_radius**2 + top_radius * bottom_radius)
        
        # Surface areas
        S_top = np.pi * top_radius**2
        S_bottom = np.pi * bottom_radius**2
        
        # Slant height for lateral surface area
        slant_height = np.sqrt((bottom_radius - top_radius)**2 + height**2)
        S_side = np.pi * (top_radius + bottom_radius) * slant_height
        
        return volume, S_top, S_side, S_bottom

    def calculate_truncated_trapezoid_geometry(self, dimensions: Tuple[float, float, float, float, float]) -> Tuple[float, float, float, float]:
        """
        Calculate geometric properties for truncated trapezoidal Pit Thermal Energy Storage (PTES).

        This method computes volume and surface areas for trapezoidal pit storage systems,
        which offer maximum flexibility for adaptation to site constraints and irregular
        plot geometries. Trapezoidal PTES provides excellent storage capacity while
        accommodating rectangular site boundaries and existing infrastructure.

        Parameters
        ----------
        dimensions : Tuple[float, float, float, float, float]
            Trapezoidal pit dimensions (top_length[m], top_width[m], bottom_length[m], bottom_width[m], height[m]).
            
            - **top_length** : Length at top surface [m]
            - **top_width** : Width at top surface [m]  
            - **bottom_length** : Length at bottom [m], typically larger than top
            - **bottom_width** : Width at bottom [m], typically larger than top
            - **height** : Depth of pit storage [m]

        Returns
        -------
        Tuple[float, float, float, float]
            Geometric properties for thermal calculations:
            
            - **volume** (float) : Storage volume [m³]
            - **S_top** (float) : Top rectangular surface area [m²]
            - **S_side** (float) : Total trapezoidal side surface area [m²]
            - **S_bottom** (float) : Bottom rectangular surface area [m²]

        See Also
        --------
        calculate_cylindrical_geometry : Cylindrical storage geometry
        calculate_truncated_cone_geometry : Conical pit storage geometry
        SimpleThermalStorage.calculate_heat_loss : Heat loss calculations for pit storage
        """

        top_length, top_width, bottom_length, bottom_width, height = dimensions
        
        # Calculate areas of top and bottom rectangles
        A_top = top_length * top_width
        A_bottom = bottom_length * bottom_width
        
        # Volume using truncated pyramid formula
        volume = (height / 3) * (A_top + A_bottom + np.sqrt(A_top * A_bottom))
        
        # Surface areas
        S_top = A_top
        S_bottom = A_bottom
        
        # Side surface areas (four trapezoidal faces)
        # Length faces (2 faces)
        side_length_slant = np.sqrt(((bottom_length - top_length) / 2)**2 + height**2)
        S_side_length = 2 * ((top_length + bottom_length) / 2) * side_length_slant
        
        # Width faces (2 faces)  
        side_width_slant = np.sqrt(((bottom_width - top_width) / 2)**2 + height**2)
        S_side_width = 2 * ((top_width + bottom_width) / 2) * side_width_slant
        
        # Total side surface area
        S_side = S_side_length + S_side_width
        
        return volume, S_top, S_side, S_bottom
    
    def calculate_efficiency(self, Q_in: np.ndarray) -> None:
        """
        Calculate overall thermal storage efficiency.

        This method computes the storage system efficiency as the ratio of useful
        energy output to total energy input, accounting for thermal losses during
        storage periods. The efficiency metric is essential for performance
        evaluation and system optimization in district heating applications.

        Parameters
        ----------
        Q_in : numpy.ndarray
            Time series of energy input to storage [kWh/h].
            Must cover same time period as simulation.

        Notes
        -----
        Efficiency Definition:
            
            **Round-trip Efficiency**:
            η = (E_input - E_losses) / E_input = 1 - (E_losses / E_input)
            
            Where:
            - E_input: Total energy charged to storage
            - E_losses: Total thermal losses during storage period
            - η: Storage efficiency (0-1)

        See Also
        --------
        calculate_operational_costs : Economic analysis of storage losses
        simulate : Main simulation method that generates loss data
        """
        total_input = np.sum(Q_in)
        self.total_energy_loss_kWh = np.sum(self.Q_loss)
        
        if total_input > 0:
            self.efficiency = 1 - (self.total_energy_loss_kWh / total_input)
        else:
            self.efficiency = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert storage object to dictionary for serialization.

        This method creates a serializable dictionary representation of the thermal
        storage object, excluding non-serializable attributes like scene items.
        Essential for saving storage configurations and simulation results.

        Returns
        -------
        Dict[str, Any]
            Dictionary containing all serializable attributes of the storage object.

        Notes
        -----
        Serialization Use Cases:
            - Configuration file export/import
            - Simulation result archiving
            - Parameter optimization workflows
            - Model sharing and reproduction
        """

        data = self.__dict__.copy()
        data.pop('scene_item', None)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThermalStorage':
        """
        Create storage object from dictionary.

        Parameters
        ----------
        data : Dict[str, Any]
            Dictionary containing storage object attributes.

        Returns
        -------
        ThermalStorage
            Reconstructed storage object with attributes from dictionary.

        """

        obj = cls.__new__(cls)
        obj.__dict__.update(data)
        return obj
    
    def __deepcopy__(self, memo: Dict[int, Any]) -> 'ThermalStorage':
        """
        Create deep copy of storage object.

        Parameters
        ----------
        memo : Dict[int, Any]
            Memoization dictionary for deepcopy operation.

        Returns
        -------
        ThermalStorage
            Deep copy of the thermal storage object.
        """

        return self.from_dict(self.to_dict())

class SimpleThermalStorage(ThermalStorage):
    """
    Simplified thermal storage model for basic district heating applications.

    This class implements a simplified thermal storage model based on lumped capacitance
    analysis, suitable for preliminary design studies and basic performance assessment.
    It provides temperature-dependent heat loss calculations for various storage
    configurations commonly used in district heating systems.

    The model uses established heat transfer correlations for different storage types
    including above-ground and underground cylindrical tanks, and pit thermal energy
    storage (PTES) systems with cone and trapezoid geometries.

    Parameters
    ----------
    *args, **kwargs
        Arguments passed to parent ThermalStorage class.
        See ThermalStorage documentation for complete parameter descriptions.

    Attributes
    ----------
    Q_in : numpy.ndarray
        Time series of heat input to storage [kWh/h].
    Q_out : numpy.ndarray
        Time series of heat output from storage [kWh/h].

    Notes
    -----
    Model Assumptions:
        
        **Lumped Capacitance**:
        - Uniform temperature distribution within storage
        - No thermal stratification effects
        - Instantaneous heat transfer within storage volume
        - Single temperature node representation

        **Heat Transfer Mechanisms**:
        - Conductive heat transfer through insulation layers
        - Heat transfer to soil for underground installations
        - Temperature-dependent thermal resistance calculations
        - Steady-state heat transfer analysis per time step

    Storage Type Configurations:
        
        **"cylindrical_overground"**:
        - Above-ground cylindrical tanks
        - Heat loss through top, sides, and bottom
        - Ambient air temperature boundary condition for top and sides
        - Soil temperature boundary condition for bottom with ground resistance

        **"cylindrical_underground"**:
        - Underground cylindrical tanks
        - Combined side and bottom heat loss to soil
        - Minimum insulation thickness requirements
        - Soil thermal resistance network

        **"truncated_cone"** and **"truncated_trapezoid"**:
        - Pit thermal energy storage (PTES) systems
        - Heat loss through sides and bottom to soil
        - Logarithmic resistance correlations for pit geometry
        - No top surface losses (covered storage)

    See Also
    --------
    ThermalStorage : Base class with complete parameter documentation
    StratifiedThermalStorage : Advanced stratified storage model
    calculate_heat_loss : Detailed heat loss calculation methods
    simulate : Main simulation workflow
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Check Biot number validity for lumped capacitance assumption
        self._check_biot_number()

    def _check_biot_number(self) -> None:
        """
        Check Biot number to validate lumped capacitance assumption.
        
        The Biot number (Bi) indicates whether internal temperature gradients
        are negligible. For lumped capacitance to be valid, Bi should be < 0.1.
        
        Biot Number:
            Bi = (h × L_c) / k
            
        Where:
            - h: Heat transfer coefficient [W/(m²·K)]
            - L_c: Characteristic length [m] = V / A_surface
            - k: Thermal conductivity of storage medium [W/(m·K)]
            
        This method calculates Bi and issues a warning if it exceeds 0.1,
        suggesting that StratifiedThermalStorage may be more appropriate.
        """
        import warnings
        
        # Calculate characteristic length: L_c = Volume / Surface Area
        total_surface_area = self.S_top + self.S_side + self.S_bottom
        L_c = self.volume / total_surface_area
        
        # Estimate effective heat transfer coefficient at storage boundary
        # The Biot number compares internal vs external thermal resistance
        # For well-insulated storage, the dominant resistance is the insulation
        # 
        # Bi = h_eff × L_c / k_medium
        # 
        # Where h_eff is the overall heat transfer coefficient through insulation:
        # h_eff ≈ λ_ins / δ_ins (for well-insulated storage)
        
        # Use average insulation properties
        avg_insulation_thickness = (self.dt_top + self.ds_side + self.db_bottom) / 3
        avg_insulation_conductivity = (self.lambda_top + self.lambda_side + self.lambda_bottom) / 3
        
        # Effective heat transfer coefficient (dominated by insulation resistance)
        # This represents heat flow from storage interior through insulation
        h_eff = avg_insulation_conductivity / avg_insulation_thickness
        
        # Calculate Biot number
        k_medium = self.thermal_conductivity  # Water: ~0.6 W/(m·K)
        Bi = (h_eff * L_c) / k_medium
        
        # Store for reference
        self.biot_number = Bi
        self.characteristic_length = L_c
        
        # Issue warning if Bi > 0.1 (lumped capacitance assumption questionable)
        if Bi > 0.1:
            warnings.warn(
                f"\n{'='*70}\n"
                f"LUMPED CAPACITANCE VALIDITY WARNING\n"
                f"{'='*70}\n"
                f"Biot number (Bi = {Bi:.3f}) exceeds 0.1 for this storage configuration.\n\n"
                f"Storage properties:\n"
                f"  - Volume: {self.volume:.1f} m³\n"
                f"  - Characteristic length: {L_c:.2f} m\n"
                f"  - Effective heat transfer coefficient: {h_eff:.2f} W/(m²·K)\n"
                f"  - Medium thermal conductivity: {k_medium:.2f} W/(m·K)\n\n"
                f"Interpretation:\n"
                f"  Bi < 0.1  : Lumped capacitance valid (uniform temperature)\n"
                f"  Bi > 0.1  : Internal temperature gradients significant\n"
                f"  Bi > 1.0  : Temperature highly non-uniform\n\n"
                f"Recommendation:\n"
                f"  For Bi > 0.1, consider using 'StratifiedThermalStorage'\n"
                f"  for improved accuracy with temperature stratification modeling.\n"
                f"{'='*70}",
                UserWarning,
                stacklevel=3
            )
        else:
            # Confirmation message for valid lumped capacitance
            print(f"✓ Biot number check: Bi = {Bi:.4f} < 0.1 - Lumped capacitance valid")
    
    def calculate_heat_loss(self, T_sto_last: float) -> float:
        """
        Calculate temperature-dependent heat losses for various storage configurations.

        This method implements heat transfer calculations for different storage types
        using established thermal resistance networks and correlations from technical
        literature. The calculations account for insulation properties, soil thermal
        characteristics, and geometric factors specific to each storage configuration.

        Parameters
        ----------
        T_sto_last : float
            Storage temperature from previous time step [°C].
            Used as driving temperature difference for heat loss calculations.

        Returns
        -------
        float
            Total heat loss rate [kW] for current time step.

        Notes
        -----
        Heat Loss Calculation Methods:
            
            **Cylindrical Overground Storage**:
            - Top loss: Q_top = (T_sto - T_amb) × (λ_top/δ_top) × A_top
            - Side loss: Q_side = (T_sto - T_amb) × (λ_side/δ_side) × A_side
            - Bottom loss: Q_bottom = (T_sto - T_amb) × R_total^(-1) × A_bottom
            
            Where R_total includes insulation and soil thermal resistances.

            **Cylindrical Underground Storage**:
            - Combined side/bottom loss using cylindrical resistance correlation
            - Minimum insulation thickness requirement: δ_min = 0.37 × R × (λ_side/λ_soil)
            - Thermal resistance: R = δ_side/λ_side + 0.52×R/λ_soil

            **Pit Storage (Cone/Trapezoid)**:
            - Logarithmic resistance correlations for pit geometry
            - Side resistance: K_s = [ln((a+bH)/a)] / (bH) where a,b depend on geometry
            - Bottom resistance: K_b = [ln((c+bH_bottom)/c)] / (2bH_bottom)

        Thermal Resistance Networks:
            
            **Series Resistances**:
            - Insulation thermal resistance: R_ins = δ/λ
            - Soil thermal resistance: R_soil = f(geometry, λ_soil)
            - Interface resistances: Typically negligible for large storage

            **Parallel Heat Paths**:
            - Multiple surface orientations
            - Thermal bridges through structural elements
            - Edge effects at geometry transitions

        See Also
        --------
        simulate : Main simulation using heat loss calculations
        ThermalStorage.calculate_cylindrical_geometry : Geometry calculations
        plot_results : Visualization of heat loss results
        """

        if self.storage_type == "cylindrical_overground":
            # Heat loss from top to ambient air
            Q_t = (T_sto_last - self.T_amb) * (self.lambda_top / self.dt_top) * self.S_top
            
            # Heat loss from sides to ambient air
            Q_s = (T_sto_last - self.T_amb) * (self.lambda_side / self.ds_side) * self.S_side
            
            # Heat loss from bottom through insulation and soil
            R_bottom_insulation = self.db_bottom / self.lambda_bottom
            R_soil = 4 * self.dimensions[0] / (3 * np.pi * self.lambda_soil)
            R_total_bottom = R_bottom_insulation + R_soil
            Q_b = (T_sto_last - self.T_amb) / R_total_bottom * self.S_bottom
            
            return (Q_t + Q_s + Q_b) / 1000  # Convert W to kW

        elif self.storage_type == "cylindrical_underground":
            # Underground cylindrical storage - combined side and bottom losses
            R = self.dimensions[0]  # Radius
            H = self.dimensions[1]  # Height
            
            # Minimum insulation thickness requirement
            d_min = (self.lambda_side / self.lambda_soil) * R * 0.37
            
            if self.ds_side > 2 * d_min:
                # Thermal conductance for combined side and bottom
                K_sb = 1 / (self.ds_side / self.lambda_side + 0.52 * R / self.lambda_soil)
                
                # Combined surface area (cylindrical surface + bottom)
                S_c = np.pi * R**2 + 2 * np.pi * R * H
                
                Q_sb = (T_sto_last - self.T_soil) * K_sb * S_c
                return Q_sb / 1000  # Convert W to kW
            else:
                raise ValueError(f"Insulation thickness {self.ds_side:.3f}m too small. "
                               f"Minimum required: {2*d_min:.3f}m")

        elif self.storage_type in ["truncated_cone", "truncated_trapezoid"]:
            # Pit thermal energy storage heat loss calculations
            H = self.dimensions[2]  # Height/depth
            
            # Side heat loss calculation
            a = self.ds_side / self.lambda_side + np.pi * H / (2 * self.lambda_soil)
            b = np.pi / self.lambda_soil
            
            if (a + b * H) > a and a > 0:
                K_s = (1 / (b * H)) * np.log((a + b * H) / a)
                Q_s = (T_sto_last - self.T_soil) * K_s * self.S_side
            else:
                Q_s = 0

            # Bottom heat loss calculation  
            if self.storage_type == "truncated_cone":
                bottom_characteristic_length = self.dimensions[1]  # Bottom radius
            else:  # truncated_trapezoid
                bottom_characteristic_length = min(self.dimensions[2], self.dimensions[3])  # Min of bottom dimensions
            
            c = self.db_bottom / self.lambda_bottom + np.pi * H / (2 * self.lambda_soil)
            
            if (c + b * bottom_characteristic_length) > c and c > 0:
                K_b = (1 / (2 * b * bottom_characteristic_length)) * np.log((c + b * bottom_characteristic_length) / c)
                Q_b = (T_sto_last - self.T_soil) * K_b * self.S_bottom
            else:
                Q_b = 0

            return (Q_s + Q_b) / 1000  # Convert W to kW
        
        else:
            raise ValueError(f"Unsupported storage type for heat loss calculation: {self.storage_type}")

    def simulate(self, Q_in: np.ndarray, Q_out: np.ndarray) -> None:
        """
        Execute thermal storage simulation with energy balance calculations.

        This method performs hour-by-hour thermal simulation of the storage system,
        solving energy balance equations and tracking temperature evolution over time.
        The simulation accounts for heat inputs, outputs, thermal losses, and
        temperature-dependent storage behavior.

        Parameters
        ----------
        Q_in : numpy.ndarray
            Time series of heat input power to storage [kW].
            Positive values represent charging (heat addition).
            Array length must match the number of simulation hours.
        Q_out : numpy.ndarray
            Time series of heat output power from storage [kW].  
            Positive values represent discharging (heat extraction).
            Array length must match the number of simulation hours.

        Notes
        -----
        Timestep Assumption:
            **This simulation assumes hourly timesteps (Δt = 1 hour).**
            
            The energy balance integrates power over 1-hour intervals:
            E[t] = E[t-1] + (Q_in[t] - Q_out[t] - Q_loss[t]) × Δt
            
            Since Δt = 1 h, energy in kWh equals power in kW numerically:
            Energy [kWh] = Power [kW] × 1 [h]

        Simulation Methodology:
            
            **Energy Balance Equation**:
            dE/dt = Q̇_in - Q̇_out - Q̇_loss
            
            **Discrete Form (hourly timesteps)**:
            E[t] = E[t-1] + (Q̇_in[t] - Q̇_out[t] - Q̇_loss[t]) × Δt
            
            Where:
            - E: Stored thermal energy [kWh]
            - Q̇_in: Heat input power [kW]
            - Q̇_out: Heat output power [kW] 
            - Q̇_loss: Heat loss power [kW]
            - Δt: Time step = 1 hour

            **Temperature Calculation**:
            T_storage = (E_stored / (m × cp)) + T_ref
            
            Where:
            - E_stored: Total stored energy [J]
            - m: Storage mass [kg] = ρ × V
            - cp: Specific heat capacity [J/(kg·K)]
            - T_ref: Reference temperature [°C]

        Lumped Capacitance Method:
            
            **Assumptions**:
            - Uniform temperature throughout storage volume
            - Negligible internal temperature gradients (Bi << 0.1)
            - Instantaneous thermal equilibrium within storage
            - Valid for small storage or slow thermal processes
            
            **Validity Criterion (Biot Number)**:
            Bi = (h × L_c) / k < 0.1
            
            Where:
            - h: Heat transfer coefficient [W/(m²·K)]
            - L_c: Characteristic length [m] = V/A
            - k: Thermal conductivity of medium [W/(m·K)]
            
            For large seasonal storage (>1000 m³), consider using
            StratifiedThermalStorage for improved accuracy.

        Simulation Features:
            
            **Temperature Limits**:
            - Maximum temperature constraint (T_max)
            - Minimum temperature constraint (T_min)
            - Physical boundary enforcement
            - Automatic energy recalculation at limits

            **Heat Loss Calculation**:
            - Temperature-dependent losses at each time step
            - Uses previous time step temperature (explicit scheme)
            - Multiple storage configuration support
            - Accounts for insulation and soil thermal resistances

            **Energy Balance Verification**:
            - Total energy input tracking
            - Cumulative loss calculation
            - Storage efficiency determination

        See Also
        --------
        calculate_heat_loss : Heat loss calculation method
        plot_results : Visualization of simulation results
        calculate_efficiency : Overall efficiency calculation
        StratifiedThermalStorage : Advanced model for large storage with stratification
        """
        self.Q_in = Q_in
        self.Q_out = Q_out
        
        # Timestep for energy integration (hours)
        dt = 1.0  # [h] - hourly timesteps assumed
        
        # Pre-calculate constants for computational efficiency
        # (Avoid repeated calculations inside loop)
        V_rho_cp = self.volume * self.rho * self.cp  # Thermal capacity [J/K]
        conversion_factor = 3.6e6  # Conversion factor J ↔ kWh
        E_max = V_rho_cp * (self.T_max - self.T_ref) / conversion_factor  # Max energy [kWh]
        E_min = V_rho_cp * (self.T_min - self.T_ref) / conversion_factor  # Min energy [kWh]

        # Explicit time-stepping loop (Forward Euler method)
        # 
        # Why a for-loop?
        # - Each timestep depends on previous temperature T[t-1]
        # - Heat losses are nonlinear (temperature-dependent)
        # - Full vectorization not possible due to temperature feedback
        # - For-loop is standard approach for such coupled ODEs
        #
        # Alternative methods (if needed for performance):
        # - Numba JIT compilation: 50-100x speedup
        # - scipy.integrate.odeint: Higher accuracy, adaptive timesteps
        # - Implicit methods: Better stability for stiff systems
        for t in range(self.hours):
            if t == 0:
                # Initialize first timestep
                # No heat losses applied at t=0 (initial condition, not a time interval)
                self.Q_loss[0] = 0.0
                self.Q_sto[0] = V_rho_cp * (self.T_sto[0] - self.T_ref) / conversion_factor
            else:
                # Calculate heat loss based on previous timestep temperature (explicit scheme)
                # Q_loss[t] = f(T[t-1]) ensures numerical stability for dt=1h
                self.Q_loss[t] = self.calculate_heat_loss(self.T_sto[t-1])
                
                # Energy balance equation (discrete form):
                # E[t] = E[t-1] + (Q̇_in - Q̇_out - Q̇_loss) × Δt
                # 
                # Units: kWh = kWh + (kW - kW - kW) × 1h
                # For Δt=1h: numerically, kW equals kWh (integral over 1 hour)
                self.Q_sto[t] = self.Q_sto[t-1] + (Q_in[t] - Q_out[t] - self.Q_loss[t]) * dt

                # Convert stored energy to temperature
                # From: E = m × cp × (T - T_ref) → T = E/(m×cp) + T_ref
                self.T_sto[t] = (self.Q_sto[t] * conversion_factor / V_rho_cp) + self.T_ref

                # Apply physical temperature constraints
                # (Prevent unphysical temperatures, e.g., boiling or freezing)
                if self.T_sto[t] > self.T_max:
                    self.T_sto[t] = self.T_max
                    self.Q_sto[t] = E_max  # Recalculate energy consistently
                    
                elif self.T_sto[t] < self.T_min:
                    self.T_sto[t] = self.T_min
                    self.Q_sto[t] = E_min  # Recalculate energy consistently
        
        # Calculate overall storage efficiency
        self.calculate_efficiency(Q_in)

    def plot_results(self) -> None:
        """
        Generate comprehensive visualization of thermal storage simulation results.

        This method creates a multi-panel plot showing the key performance indicators
        and operational characteristics of the thermal storage system. The visualization
        includes energy flows, storage state, temperature evolution, and heat losses
        over the simulation period.

        Notes
        -----
        Plot Components:
            
            **Energy Flow Analysis** (Top Left):
            - Heat input profile [kW] over time
            - Heat output profile [kW] over time
            - Visual comparison of charging and discharging patterns

            **Storage Energy Content** (Top Right):
            - Stored thermal energy [kWh] evolution
            - Energy capacity utilization
            - Storage cycling behavior

            **Temperature Evolution** (Bottom Left):
            - Storage temperature [°C] over time
            - Temperature limits visualization
            - Thermal cycling patterns

            **Heat Loss Analysis** (Bottom Right):
            - Heat loss rate [kW] over time
            - Temperature-dependent loss variations
            - Total energy loss quantification

        Visualization Features:
            - Professional matplotlib styling
            - Clear axis labels and units
            - Legends for data interpretation
            - Tight layout for optimal presentation

        See Also
        --------
        simulate : Run simulation to generate data for plotting
        calculate_efficiency : Performance metrics displayed in results
        """
        fig = plt.figure(figsize=(16, 10))
        
        # Create subplot grid
        axs1 = fig.add_subplot(2, 2, 1)
        axs2 = fig.add_subplot(2, 2, 2)
        axs3 = fig.add_subplot(2, 2, 3)
        axs4 = fig.add_subplot(2, 2, 4)
        
        # Time axis (assuming hourly data)
        time_hours = np.arange(len(self.Q_in))
        
        # Plot 1: Heat Input and Output
        axs1.plot(time_hours, self.Q_in, label='Heat Input (kW)', color='red', linewidth=1.5)
        axs1.plot(time_hours, self.Q_out, label='Heat Output (kW)', color='blue', linewidth=1.5)
        axs1.set_title('Heat Input and Output', fontsize=14, fontweight='bold')
        axs1.set_xlabel('Time [hours]')
        axs1.set_ylabel('Power [kW]')
        axs1.legend()
        axs1.grid(True, alpha=0.3)

        # Plot 2: Stored Heat
        axs2.plot(time_hours, self.Q_sto, label='Stored Heat (kWh)', color='green', linewidth=2)
        axs2.set_title('Stored Thermal Energy', fontsize=14, fontweight='bold')
        axs2.set_xlabel('Time [hours]')
        axs2.set_ylabel('Stored Energy [kWh]')
        axs2.legend()
        axs2.grid(True, alpha=0.3)

        # Plot 3: Storage Temperature
        axs3.plot(time_hours, self.T_sto, label='Storage Temperature (°C)', color='orange', linewidth=2)
        # Add temperature limits as horizontal lines
        axs3.axhline(y=self.T_max, color='red', linestyle='--', alpha=0.7, label=f'T_max ({self.T_max}°C)')
        axs3.axhline(y=self.T_min, color='blue', linestyle='--', alpha=0.7, label=f'T_min ({self.T_min}°C)')
        axs3.set_title('Storage Temperature Profile', fontsize=14, fontweight='bold')
        axs3.set_xlabel('Time [hours]')
        axs3.set_ylabel('Temperature [°C]')
        axs3.legend()
        axs3.grid(True, alpha=0.3)

        # Plot 4: Heat Loss
        axs4.plot(time_hours, self.Q_loss, label='Heat Loss (kW)', color='purple', linewidth=2)
        axs4.set_title('Heat Loss Rate', fontsize=14, fontweight='bold')
        axs4.set_xlabel('Time [hours]')
        axs4.set_ylabel('Heat Loss [kW]')
        axs4.legend()
        axs4.grid(True, alpha=0.3)

        # Plot 3D geometry
        #self.plot_3d_temperature_distribution(axs6, 3000)

        # Adjust layout for better spacing
        plt.tight_layout()
    