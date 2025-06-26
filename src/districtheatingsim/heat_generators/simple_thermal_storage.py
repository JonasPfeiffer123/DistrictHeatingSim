"""
Filename: simple_thermal_storage.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-06-26
Description: Advanced thermal energy storage modeling for district heating systems.

This module provides comprehensive modeling capabilities for Seasonal Thermal Energy Storage (STES)
systems in district heating applications. It implements sophisticated heat transfer calculations,
geometric modeling for various storage configurations, and performance analysis tools for
large-scale thermal storage design and optimization.

The module is based on validated simulation methods from scientific literature and supports
multiple storage geometries including cylindrical tanks, pit thermal energy storage (PTES)
with truncated cone and trapezoid configurations, both above-ground and underground installations.

References
----------
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
        
        **Insulation Design**:
        - Top insulation most critical due to convective losses
        - Side insulation thickness depends on storage size and economics
        - Bottom insulation can be reduced for underground installations
        
        **Material Properties**:
        - Water preferred for high heat capacity and low cost
        - Glycol mixtures for freeze protection in cold climates
        - Thermal conductivity affects internal temperature gradients

    Heat Transfer Mechanisms:
        
        **Conductive Losses**:
        - Through insulation materials to ambient environment
        - To surrounding soil for underground installations
        - Internal conduction affects temperature stratification
        
        **Thermal Resistance Networks**:
        - Series resistances through insulation layers
        - Parallel heat paths for complex geometries
        - Soil thermal resistance for underground storage

    Examples
    --------
    >>> # Create cylindrical hot water storage tank
    >>> tank_storage = ThermalStorage(
    ...     name="District_Tank_01",
    ...     storage_type="cylindrical",
    ...     dimensions=(5.0, 10.0),  # 5m radius, 10m height
    ...     rho=1000,  # Water density
    ...     cp=4186,   # Water heat capacity
    ...     T_ref=0,   # Reference temperature
    ...     lambda_top=0.03,    # Insulation conductivity
    ...     lambda_side=0.03,
    ...     lambda_bottom=0.03,
    ...     lambda_soil=1.5,    # Soil conductivity
    ...     T_amb=10,   # Ambient temperature
    ...     T_soil=8,   # Soil temperature
    ...     T_max=95,   # Maximum temperature
    ...     T_min=5,    # Minimum temperature
    ...     initial_temp=60,  # Initial temperature
    ...     dt_top=0.2,   # Insulation thickness
    ...     ds_side=0.15,
    ...     db_bottom=0.1
    ... )

    >>> # Display storage characteristics
    >>> print(f"Storage volume: {tank_storage.volume:.1f} m³")
    >>> print(f"Heat capacity: {tank_storage.volume * tank_storage.rho * tank_storage.cp / 1e9:.1f} GJ/K")

    >>> # Create large-scale PTES with truncated cone geometry
    >>> ptes_storage = ThermalStorage(
    ...     name="PTES_Seasonal_01",
    ...     storage_type="truncated_cone",
    ...     dimensions=(25.0, 35.0, 15.0),  # top_r, bottom_r, height
    ...     rho=1000,
    ...     cp=4186,
    ...     T_ref=0,
    ...     lambda_top=0.025,
    ...     lambda_side=0.035,
    ...     lambda_bottom=0.04,
    ...     lambda_soil=2.0,
    ...     T_amb=8,
    ...     T_soil=10,
    ...     T_max=90,
    ...     T_min=15,
    ...     initial_temp=45,
    ...     dt_top=0.3,
    ...     ds_side=0.5,
    ...     db_bottom=0.3,
    ...     hours=8760  # Full year simulation
    ... )

    >>> # Storage capacity analysis
    >>> max_energy = ptes_storage.volume * ptes_storage.rho * ptes_storage.cp * (ptes_storage.T_max - ptes_storage.T_min) / 3.6e9
    >>> print(f"PTES maximum energy capacity: {max_energy:.0f} GWh")

    >>> # Create flexible trapezoid PTES for constrained site
    >>> site_storage = ThermalStorage(
    ...     name="Site_Adapted_PTES",
    ...     storage_type="truncated_trapezoid",
    ...     dimensions=(40, 30, 50, 40, 12),  # Adapted to site boundaries
    ...     rho=1000,
    ...     cp=4186,
    ...     T_ref=0,
    ...     lambda_top=0.03,
    ...     lambda_side=0.04,
    ...     lambda_bottom=0.04,
    ...     lambda_soil=1.8,
    ...     T_amb=8,
    ...     T_soil=9,
    ...     T_max=85,
    ...     T_min=20,
    ...     initial_temp=50,
    ...     dt_top=0.25,
    ...     ds_side=0.4,
    ...     db_bottom=0.25
    ... )

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
        if storage_type == "cylindrical":
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

        Notes
        -----
        Cylindrical Storage Applications:
            
            **Short-term Storage (Hours to Days)**:
            - Buffer tanks for load balancing
            - Peak shaving applications
            - CHP plant integration
            
            **Medium-term Storage (Days to Weeks)**:
            - Weekly load shifting
            - Industrial process heat storage
            - Solar thermal integration

        Design Considerations:
            
            **Aspect Ratio**:
            - Height/Diameter ratio affects thermal stratification
            - Tall tanks (H/D > 2) promote better stratification
            - Wide tanks (H/D < 1) suitable for large volumes with limited height
            
            **Surface Area Optimization**:
            - Minimize surface-to-volume ratio to reduce heat losses
            - Spherical shape optimal but impractical for large storage
            - Cylindrical provides good compromise between efficiency and constructability

        Heat Loss Considerations:
            - Top surface: Critical for insulation due to buoyancy effects
            - Side surface: Largest area, significant for tall tanks
            - Bottom surface: Can benefit from soil insulation for underground tanks

        Examples
        --------
        >>> # Small buffer tank for residential district heating
        >>> radius, height = 1.5, 3.0  # 1.5m radius, 3m height
        >>> storage = ThermalStorage("Buffer_Tank", "cylindrical", (radius, height), ...)
        >>> volume, S_top, S_side, S_bottom = storage.calculate_cylindrical_geometry((radius, height))
        >>> print(f"Buffer tank volume: {volume:.1f} m³")
        >>> print(f"Surface areas - Top: {S_top:.1f}, Side: {S_side:.1f}, Bottom: {S_bottom:.1f} m²")

        >>> # Large district heating storage tank
        >>> radius, height = 15.0, 20.0  # 15m radius, 20m height
        >>> volume, S_top, S_side, S_bottom = storage.calculate_cylindrical_geometry((radius, height))
        >>> total_surface = S_top + S_side + S_bottom
        >>> surface_to_volume = total_surface / volume
        >>> print(f"Large tank volume: {volume:.0f} m³")
        >>> print(f"Surface-to-volume ratio: {surface_to_volume:.3f} m²/m³")

        >>> # Aspect ratio analysis for stratification
        >>> for h_d_ratio in [0.5, 1.0, 2.0, 3.0]:
        ...     radius = 10.0
        ...     height = h_d_ratio * 2 * radius
        ...     volume, _, S_side, _ = storage.calculate_cylindrical_geometry((radius, height))
        ...     print(f"H/D={h_d_ratio:.1f}: Volume={volume:.0f}m³, Side area={S_side:.0f}m²")

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

        Notes
        -----
        PTES Design Principles:
            
            **Seasonal Storage Applications**:
            - Summer heat collection and winter discharge
            - Solar thermal seasonal storage
            - Industrial waste heat recovery
            - CHP plant seasonal buffering
            
            **Geometric Advantages**:
            - Natural thermal stratification with hot water at top
            - Structural stability against soil pressure
            - Optimal surface-to-volume ratio for large capacities
            - Reduced excavation costs compared to cylindrical pits

        Thermal Stratification:
            
            **Cone Shape Benefits**:
            - Wider bottom provides stable cold water reservoir
            - Narrower top minimizes surface heat losses
            - Sloped sides reduce mixing and maintain stratification
            - Natural convection patterns enhance performance

        Construction Considerations:
            
            **Excavation**:
            - Sloped sides reduce soil stability requirements
            - Natural angle of repose for various soil types
            - Reduced liner material compared to cylindrical design
            
            **Liner Systems**:
            - Flexible liners conform to cone geometry
            - Reduced stress concentrations at corners
            - Improved durability and leak resistance

        Examples
        --------
        >>> # Medium-scale PTES for district heating
        >>> top_r, bottom_r, height = 20.0, 30.0, 15.0
        >>> storage = ThermalStorage("PTES_Medium", "truncated_cone", (top_r, bottom_r, height), ...)
        >>> volume, S_top, S_side, S_bottom = storage.calculate_truncated_cone_geometry((top_r, bottom_r, height))
        >>> 
        >>> # Calculate storage capacity
        >>> capacity_GWh = volume * 1000 * 4186 * (85-15) / 3.6e9  # 85°C to 15°C
        >>> print(f"PTES volume: {volume:.0f} m³")
        >>> print(f"Energy capacity: {capacity_GWh:.1f} GWh")

        >>> # Large-scale seasonal storage
        >>> top_r, bottom_r, height = 35.0, 50.0, 25.0
        >>> volume, S_top, S_side, S_bottom = storage.calculate_truncated_cone_geometry((top_r, bottom_r, height))
        >>> 
        >>> # Surface area analysis for heat loss
        >>> total_surface = S_top + S_side + S_bottom
        >>> side_fraction = S_side / total_surface
        >>> print(f"Large PTES volume: {volume:.0f} m³")
        >>> print(f"Side surface fraction: {side_fraction:.2f}")

        >>> # Geometry optimization for different cone angles
        >>> for bottom_r in [25, 30, 35, 40]:
        ...     volume, _, S_side, _ = storage.calculate_truncated_cone_geometry((20, bottom_r, 15))
        ...     cone_angle = np.arctan(15 / (bottom_r - 20)) * 180 / np.pi
        ...     print(f"Bottom radius {bottom_r}m: Angle={cone_angle:.1f}°, Volume={volume:.0f}m³")

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

        Notes
        -----
        Trapezoidal PTES Applications:
            
            **Site Adaptation Advantages**:
            - Rectangular shapes fit urban plot boundaries
            - Flexible aspect ratios for constrained sites
            - Integration with existing building infrastructure
            - Optimal use of available land area
            
            **Construction Benefits**:
            - Straight side walls simplify construction
            - Standard excavation equipment compatibility
            - Easier access for maintenance and monitoring
            - Modular construction possibilities

        Thermal Performance:
            
            **Stratification Characteristics**:
            - Rectangular geometry provides uniform horizontal temperature layers
            - Aspect ratio affects mixing and stratification quality
            - Corner effects may create local circulation patterns
            - Baffles can enhance stratification performance

        Design Considerations:
            
            **Geometric Optimization**:
            - Bottom area larger than top for structural stability
            - Sloped sides prevent soil collapse during construction
            - Corner radii can reduce stress concentrations
            - Access provisions for inlet/outlet positioning

        Examples
        --------
        >>> # Medium-scale rectangular PTES
        >>> dimensions = (30, 20, 40, 30, 12)  # top_l, top_w, bottom_l, bottom_w, height
        >>> storage = ThermalStorage("Rect_PTES", "truncated_trapezoid", dimensions, ...)
        >>> volume, S_top, S_side, S_bottom = storage.calculate_truncated_trapezoid_geometry(dimensions)
        >>> 
        >>> print(f"Rectangular PTES volume: {volume:.0f} m³")
        >>> print(f"Top area: {S_top:.0f} m², Bottom area: {S_bottom:.0f} m²")
        >>> print(f"Side surface area: {S_side:.0f} m²")

        >>> # Large-scale seasonal storage for district heating
        >>> dimensions = (50, 40, 70, 60, 20)
        >>> volume, S_top, S_side, S_bottom = storage.calculate_truncated_trapezoid_geometry(dimensions)
        >>> 
        >>> # Calculate energy density and surface ratios
        >>> energy_density = volume / (S_top)  # m³/m² - volume per surface area
        >>> surface_to_volume = (S_top + S_side + S_bottom) / volume
        >>> print(f"Large PTES energy density: {energy_density:.1f} m³/m²")
        >>> print(f"Surface-to-volume ratio: {surface_to_volume:.3f} m²/m³")

        >>> # Site constraint analysis - narrow vs wide configurations
        >>> narrow_config = (60, 20, 80, 30, 15)  # Long and narrow
        >>> wide_config = (40, 40, 50, 50, 15)    # Square-like
        >>> 
        >>> for name, config in [("Narrow", narrow_config), ("Wide", wide_config)]:
        ...     vol, _, _, _ = storage.calculate_truncated_trapezoid_geometry(config)
        ...     aspect_ratio = config[0] / config[1]  # length/width at top
        ...     print(f"{name}: Volume={vol:.0f}m³, Aspect ratio={aspect_ratio:.1f}")

        >>> # Construction slope analysis
        >>> dimensions = (30, 25, 40, 35, 12)
        >>> _, _, S_side, _ = storage.calculate_truncated_trapezoid_geometry(dimensions)
        >>> 
        >>> # Calculate side slopes for construction planning
        >>> length_slope = np.arctan(12 / ((40-30)/2)) * 180 / np.pi
        >>> width_slope = np.arctan(12 / ((35-25)/2)) * 180 / np.pi
        >>> print(f"Side slopes - Length: {length_slope:.1f}°, Width: {width_slope:.1f}°")

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

        Efficiency Factors:
            
            **Thermal Losses**:
            - Conductive losses through insulation
            - Heat transfer to soil and ambient environment
            - Temperature-dependent loss rates
            - Seasonal variations in external conditions
            
            **Storage Duration**:
            - Short-term storage: 85-95% efficiency
            - Medium-term storage: 70-85% efficiency  
            - Seasonal storage: 50-70% efficiency

        Performance Benchmarks:
            
            **Storage Type Comparisons**:
            - Hot water tanks: 90-98% (daily cycles)
            - PTES systems: 60-80% (seasonal cycles)
            - Underground storage: 65-85% (reduced ambient losses)
            - Above-ground storage: 55-75% (higher ambient losses)

        Examples
        --------
        >>> # Calculate efficiency after simulation
        >>> Q_in_profile = np.random.uniform(0, 1000, 8760)  # Example input profile
        >>> Q_out_profile = np.random.uniform(0, 800, 8760)   # Example output profile
        >>> 
        >>> storage.simulate(Q_in_profile, Q_out_profile)
        >>> storage.calculate_efficiency(Q_in_profile)
        >>> 
        >>> print(f"Storage efficiency: {storage.efficiency:.1%}")
        >>> print(f"Total input: {np.sum(Q_in_profile):.0f} kWh")
        >>> print(f"Total losses: {storage.total_energy_loss_kWh:.0f} kWh")

        >>> # Seasonal efficiency analysis
        >>> winter_months = range(0, 2160) + range(6552, 8760)  # Nov-Feb
        >>> summer_months = range(2880, 6552)  # Apr-Sep
        >>> 
        >>> winter_losses = np.sum(storage.Q_loss[winter_months])
        >>> summer_losses = np.sum(storage.Q_loss[summer_months])
        >>> 
        >>> winter_input = np.sum(Q_in_profile[winter_months])
        >>> summer_input = np.sum(Q_in_profile[summer_months])
        >>> 
        >>> if winter_input > 0 and summer_input > 0:
        ...     winter_eff = 1 - (winter_losses / winter_input)
        ...     summer_eff = 1 - (summer_losses / summer_input)
        ...     print(f"Winter efficiency: {winter_eff:.1%}")
        ...     print(f"Summer efficiency: {summer_eff:.1%}")

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

        Examples
        --------
        >>> storage_dict = storage.to_dict()
        >>> print("Storage configuration saved")
        """
        data = self.__dict__.copy()
        data.pop('scene_item', None)
        print("Storage saved")
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

        Examples
        --------
        >>> restored_storage = ThermalStorage.from_dict(storage_dict)
        >>> print("Storage loaded")
        """
        obj = cls.__new__(cls)
        obj.__dict__.update(data)
        print("Storage loaded")
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

    Examples
    --------
    >>> # Create simple cylindrical storage tank
    >>> simple_storage = SimpleThermalStorage(
    ...     name="Simple_Tank",
    ...     storage_type="cylindrical_overground",
    ...     dimensions=(3.0, 6.0),  # 3m radius, 6m height
    ...     rho=1000,  # Water
    ...     cp=4186,
    ...     T_ref=0,
    ...     lambda_top=0.03,
    ...     lambda_side=0.03,
    ...     lambda_bottom=0.03,
    ...     lambda_soil=1.5,
    ...     T_amb=10,
    ...     T_soil=8,
    ...     T_max=90,
    ...     T_min=10,
    ...     initial_temp=60,
    ...     dt_top=0.15,
    ...     ds_side=0.10,
    ...     db_bottom=0.10
    ... )

    >>> # Define operation profile
    >>> hours = 8760
    >>> Q_in = np.zeros(hours)
    >>> Q_out = np.zeros(hours)
    >>> 
    >>> # Summer charging profile (May-August)
    >>> Q_in[3000:6000] = 500  # 500 kW charging rate
    >>> 
    >>> # Winter discharging profile (November-February)
    >>> Q_out[7000:8760] = 200  # 200 kW discharge rate
    >>> Q_out[0:1500] = 200

    >>> # Run simulation
    >>> simple_storage.simulate(Q_in, Q_out)
    >>> 
    >>> # Analyze results
    >>> print(f"Storage efficiency: {simple_storage.efficiency:.1%}")
    >>> print(f"Maximum temperature: {np.max(simple_storage.T_sto):.1f}°C")
    >>> print(f"Minimum temperature: {np.min(simple_storage.T_sto):.1f}°C")

    >>> # Plot results
    >>> simple_storage.plot_results()

    See Also
    --------
    ThermalStorage : Base class with complete parameter documentation
    StratifiedThermalStorage : Advanced stratified storage model
    calculate_heat_loss : Detailed heat loss calculation methods
    simulate : Main simulation workflow
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

        Examples
        --------
        >>> # Calculate heat loss for different temperatures
        >>> storage_temps = [20, 40, 60, 80]
        >>> for temp in storage_temps:
        ...     heat_loss = simple_storage.calculate_heat_loss(temp)
        ...     print(f"T={temp}°C: Heat loss = {heat_loss:.1f} kW")

        >>> # Analyze temperature dependence
        >>> temp_range = np.linspace(10, 90, 81)
        >>> losses = [simple_storage.calculate_heat_loss(T) for T in temp_range]
        >>> 
        >>> import matplotlib.pyplot as plt
        >>> plt.plot(temp_range, losses)
        >>> plt.xlabel('Storage Temperature [°C]')
        >>> plt.ylabel('Heat Loss [kW]')
        >>> plt.title('Temperature-Dependent Heat Losses')

        >>> # Compare different storage types
        >>> storage_types = ["cylindrical_overground", "cylindrical_underground"]
        >>> for stype in storage_types:
        ...     storage = SimpleThermalStorage(..., storage_type=stype, ...)
        ...     loss = storage.calculate_heat_loss(60)  # At 60°C
        ...     print(f"{stype}: {loss:.1f} kW at 60°C")

        Raises
        ------
        ValueError
            If insulation thickness is insufficient for underground storage.

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
            Time series of heat input to storage [kWh/h].
            Positive values represent charging (heat addition).
        Q_out : numpy.ndarray
            Time series of heat output from storage [kWh/h].  
            Positive values represent discharging (heat extraction).

        Notes
        -----
        Simulation Methodology:
            
            **Energy Balance Equation**:
            dE/dt = Q_in - Q_out - Q_loss
            
            Where:
            - dE/dt: Rate of change of stored energy
            - Q_in: Heat input rate [kW]
            - Q_out: Heat output rate [kW] 
            - Q_loss: Heat loss rate [kW]

            **Temperature Calculation**:
            T_storage = (E_stored / (m × cp)) + T_ref
            
            Where:
            - E_stored: Total stored energy [J]
            - m: Storage mass [kg] = ρ × V
            - cp: Specific heat capacity [J/(kg·K)]
            - T_ref: Reference temperature [°C]

        Simulation Features:
            
            **Temperature Limits**:
            - Maximum temperature constraint (T_max)
            - Minimum temperature constraint (T_min)
            - Physical boundary enforcement

            **Heat Loss Calculation**:
            - Temperature-dependent losses at each time step
            - Previous time step temperature for loss calculation
            - Multiple storage configuration support

            **Energy Balance Verification**:
            - Total energy input tracking
            - Cumulative loss calculation
            - Storage efficiency determination

        Examples
        --------
        >>> # Define annual operation profile
        >>> hours = 8760
        >>> Q_in = np.zeros(hours)
        >>> Q_out = np.zeros(hours)
        >>> 
        >>> # Summer solar charging (June-August: hours 4000-6000)
        >>> Q_in[4000:6000] = 800  # 800 kW charging rate
        >>> 
        >>> # Winter heating demand (December-February: hours 0-1500, 7500-8760)
        >>> Q_out[0:1500] = 400   # 400 kW discharge rate
        >>> Q_out[7500:8760] = 400

        >>> # Execute simulation
        >>> simple_storage.simulate(Q_in, Q_out)
        >>> 
        >>> # Analyze simulation results
        >>> print(f"Simulation completed for {hours} hours")
        >>> print(f"Initial temperature: {simple_storage.T_sto[0]:.1f}°C")
        >>> print(f"Final temperature: {simple_storage.T_sto[-1]:.1f}°C")
        >>> print(f"Maximum temperature: {np.max(simple_storage.T_sto):.1f}°C")
        >>> print(f"Minimum temperature: {np.min(simple_storage.T_sto):.1f}°C")

        >>> # Energy balance verification
        >>> total_input = np.sum(Q_in)
        >>> total_output = np.sum(Q_out) 
        >>> total_losses = np.sum(simple_storage.Q_loss)
        >>> energy_change = simple_storage.Q_sto[-1] - simple_storage.Q_sto[0]
        >>> 
        >>> balance_check = total_input - total_output - total_losses - energy_change
        >>> print(f"Energy balance check: {balance_check:.1f} kWh (should be ~0)")

        >>> # Seasonal analysis
        >>> charging_period = np.sum(Q_in[4000:6000])
        >>> discharging_period = np.sum(Q_out[0:1500]) + np.sum(Q_out[7500:8760])
        >>> print(f"Total charged: {charging_period:.0f} kWh")
        >>> print(f"Total discharged: {discharging_period:.0f} kWh")
        >>> print(f"Round-trip efficiency: {discharging_period/charging_period:.1%}")

        See Also
        --------
        calculate_heat_loss : Heat loss calculation method
        plot_results : Visualization of simulation results
        calculate_efficiency : Overall efficiency calculation
        """
        self.Q_in = Q_in
        self.Q_out = Q_out

        for t in range(self.hours):
            # Calculate heat loss based on previous time step temperature
            if t == 0:
                # Use initial temperature for first time step loss calculation
                self.Q_loss[t] = self.calculate_heat_loss(self.T_sto[0])
                
                # Calculate initial stored energy relative to reference temperature
                initial_energy_J = self.volume * self.rho * self.cp * (self.T_sto[0] - self.T_ref)
                self.Q_sto[t] = initial_energy_J / 3.6e6  # Convert J to kWh
            else:
                # Use previous time step temperature for heat loss
                self.Q_loss[t] = self.calculate_heat_loss(self.T_sto[t-1])
                
                # Energy balance: Q_stored(t) = Q_stored(t-1) + Q_in - Q_out - Q_loss
                # All terms in kWh (Q_in and Q_out are kWh/h, Q_loss converted to kW and multiplied by 1h)
                self.Q_sto[t] = self.Q_sto[t-1] + (Q_in[t] - Q_out[t] - self.Q_loss[t])

            # Convert stored energy back to temperature
            if t > 0:
                stored_energy_J = self.Q_sto[t] * 3.6e6  # Convert kWh to J
                self.T_sto[t] = (stored_energy_J / (self.volume * self.rho * self.cp)) + self.T_ref

            # Apply temperature limits
            if self.T_sto[t] > self.T_max:
                self.T_sto[t] = self.T_max
                # Recalculate stored energy based on limited temperature
                limited_energy_J = self.volume * self.rho * self.cp * (self.T_max - self.T_ref)
                self.Q_sto[t] = limited_energy_J / 3.6e6
                
            elif self.T_sto[t] < self.T_min:
                self.T_sto[t] = self.T_min
                # Recalculate stored energy based on limited temperature
                limited_energy_J = self.volume * self.rho * self.cp * (self.T_min - self.T_ref)
                self.Q_sto[t] = limited_energy_J / 3.6e6
        
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

        Examples
        --------
        >>> # Run simulation and generate plots
        >>> simple_storage.simulate(Q_in, Q_out)
        >>> simple_storage.plot_results()
        >>> 
        >>> # The plot window will display four subplots showing:
        >>> # - Heat input/output flows
        >>> # - Stored energy evolution  
        >>> # - Storage temperature profile
        >>> # - Heat loss characteristics

        >>> # Save plot to file
        >>> import matplotlib.pyplot as plt
        >>> simple_storage.plot_results()
        >>> plt.savefig('storage_simulation_results.png', dpi=300, bbox_inches='tight')
        >>> plt.show()

        >>> # Customize plot appearance
        >>> simple_storage.plot_results()
        >>> plt.suptitle(f'Thermal Storage Simulation: {simple_storage.name}', fontsize=16)
        >>> plt.tight_layout(rect=[0, 0.03, 1, 0.95])

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