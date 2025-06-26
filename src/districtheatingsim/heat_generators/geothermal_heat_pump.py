"""
Filename: geothermal_heat_pump.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: Geothermal heat pump implementation for district heating applications.

This module provides comprehensive modeling capabilities for geothermal heat pump systems
in district heating applications. Geothermal heat pumps utilize the stable thermal energy
stored in the earth through vertical ground source heat exchangers (boreholes), offering
highly efficient and sustainable heating solutions with excellent seasonal performance.

The implementation includes detailed geothermal system design with borehole field modeling,
heat extraction calculations considering ground thermal properties, economic analysis
including drilling costs, and optimization capabilities for system sizing. It supports
variable drilling depths, probe spacing optimization, and thermal load management.

Features
--------
- Geothermal borehole field design and thermal modeling
- Heat extraction capacity calculation based on ground properties
- Seasonal thermal performance analysis with stable COP characteristics
- Economic evaluation including drilling costs and heat pump equipment
- Optimization support for borehole field area and drilling depth
- Integration with district heating storage and control systems

Technical Specifications
------------------------
**Geothermal System Design**:
- Vertical borehole heat exchangers with variable depth
- Probe spacing optimization for thermal interference minimization
- Ground thermal properties and heat extraction rates
- Seasonal thermal energy storage in ground mass

**Performance Modeling**:
- Stable source temperature for consistent COP performance
- Heat extraction limitations based on ground thermal capacity
- Operating hour calculations for sustainable ground thermal management
- Part-load operation with minimum threshold constraints

**Economic Components**:
- Borehole drilling costs with depth-dependent pricing
- Heat pump unit investment and installation costs
- Ground source system infrastructure (headers, pumps, controls)
- Long-term thermal sustainability and system lifecycle costs

Classes
-------
Geothermal : Geothermal heat pump system implementation

Dependencies
------------
- numpy >= 1.20.0 : Numerical calculations and array operations
- districtheatingsim.heat_generators.base_heat_pump : Base heat pump framework

Applications
------------
The module supports geothermal heat pump applications including:
- District heating systems with stable ground source heat extraction
- Large-scale heat pump installations with high seasonal efficiency
- Seasonal thermal energy storage systems with ground coupling
- Industrial heating applications requiring high reliability and efficiency

References
----------
Geothermal heat pump modeling based on:
- VDI 4640 guidelines for geothermal systems design and operation
- German geothermal association (GtV) technical standards
- Ground source heat pump performance calculation methods
- Thermal response test evaluation procedures and ground thermal modeling
"""

import numpy as np
from typing import Dict, Any, Union, Tuple, Optional

from districtheatingsim.heat_generators.base_heat_pumps import HeatPump

class Geothermal(HeatPump):
    """
    Geothermal heat pump system for district heating applications.

    This class implements a comprehensive geothermal heat pump model suitable for
    district heating systems. Geothermal heat pumps extract thermal energy from
    the earth through vertical borehole heat exchangers, providing highly efficient
    heating with stable performance throughout the year. The system includes detailed
    modeling of borehole fields, heat extraction rates, and economic considerations.

    Geothermal heat pumps offer exceptional advantages including very stable source
    temperatures, highest seasonal efficiency among heat pump technologies, minimal
    environmental impact, and long-term sustainability. The system requires careful
    design of borehole fields to ensure optimal thermal performance and economic viability.

    Parameters
    ----------
    name : str
        Unique identifier for the geothermal heat pump system.
        Should follow naming convention for system tracking and identification.
    Fläche : float
        Available area for geothermal borehole field installation [m²].
        Determines the maximum number of boreholes that can be installed.
    Bohrtiefe : float
        Drilling depth for geothermal boreholes [m].
        Typical range: 50-400m depending on ground conditions and capacity requirements.
    Temperatur_Geothermie : float
        Undisturbed ground temperature at installation depth [°C].
        Typically 8-12°C in Central Europe, increases with depth (~3K/100m).
    spez_Bohrkosten : float, optional
        Specific drilling costs per meter [€/m].
        Includes drilling, casing, grouting, and probe installation. Default is 100 €/m.
    spez_Entzugsleistung : float, optional
        Specific thermal extraction power per meter borehole [W/m].
        Depends on ground thermal properties and operating hours. Default is 50 W/m.
    Vollbenutzungsstunden : float, optional
        Full utilization hours per year [hours].
        Operating hours at rated capacity for thermal sustainability. Default is 2400 hours.
    Abstand_Sonden : float, optional
        Distance between adjacent boreholes [m].
        Prevents thermal interference and ensures sustainable operation. Default is 10 m.
    spezifische_Investitionskosten_WP : float, optional
        Specific investment costs for heat pump unit [€/kW].
        Heat pump equipment and installation costs. Default is 1000 €/kW.
    min_Teillast : float, optional
        Minimum part-load ratio [-].
        Minimum operational capacity as fraction of rated power. Default is 0.2.
    min_area_geothermal : float, optional
        Minimum area for optimization [m²]. Default is 0.
    max_area_geothermal : float, optional
        Maximum area for optimization [m²]. Default is 5000.
    min_depth_geothermal : float, optional
        Minimum drilling depth for optimization [m]. Default is 0.
    max_depth_geothermal : float, optional
        Maximum drilling depth for optimization [m]. Default is 400.

    Attributes
    ----------
    Fläche : float
        Borehole field area [m²].
    Bohrtiefe : float
        Borehole drilling depth [m].
    Temperatur_Geothermie : float
        Ground source temperature [°C].
    spez_Bohrkosten : float
        Specific drilling costs [€/m].
    spez_Entzugsleistung : float
        Specific heat extraction rate [W/m].
    Vollbenutzungsstunden : float
        Annual full utilization hours [hours].
    Abstand_Sonden : float
        Borehole spacing [m].
    min_Teillast : float
        Minimum part-load ratio [-].
    Anzahl_Sonden : int
        Number of boreholes in the field.
    Entzugsleistung_VBH : float
        Heat extraction capacity at full utilization hours [kW].
    Entzugswärmemenge : float
        Annual extractable thermal energy [MWh].
    Investitionskosten_Sonden : float
        Total borehole field investment costs [€].
    Wärmeleistung_kW : numpy.ndarray
        Heat output time series [kW].
    el_Leistung_kW : numpy.ndarray
        Electrical power consumption time series [kW].
    VLT_WP : numpy.ndarray
        Heat pump flow temperature time series [°C].
    COP : numpy.ndarray
        Coefficient of Performance time series [-].
    betrieb_mask : numpy.ndarray
        Operational state mask [bool].
    max_Wärmeleistung : float
        Maximum heat output capacity [kW].
    spez_Investitionskosten_Erdsonden : float
        Specific borehole investment costs [€/kW].
    Wärmemenge_MWh : float
        Total heat production [MWh].
    Strommenge_MWh : float
        Total electricity consumption [MWh].
    SCOP : float
        Seasonal Coefficient of Performance [-].
    WGK : float
        Heat generation costs [€/MWh].

    Notes
    -----
    Geothermal Heat Pump Technology:
        
        **Ground Source Heat Extraction**:
        Geothermal systems extract thermal energy from the earth through
        vertical borehole heat exchangers, providing several advantages:
        - Very stable source temperatures throughout the year
        - Highest efficiency among heat pump technologies
        - Minimal visual and environmental impact
        - Long-term thermal sustainability with proper design
        
        **Borehole Field Design**:
        - Vertical borehole heat exchangers (typically 50-400m deep)
        - Optimal spacing to prevent thermal interference (>6m typical)
        - Ground thermal properties determine extraction rates
        - Seasonal thermal energy storage in ground mass
        
        **Thermal Performance**:
        - Stable COP performance due to constant source temperature
        - Higher efficiency compared to air source systems
        - Reduced cycling and more continuous operation
        - Excellent part-load performance characteristics

    Performance Modeling:
        
        **Heat Extraction Calculation**:
        The thermal extraction capacity depends on:
        - Borehole depth and number of boreholes
        - Ground thermal properties and conductivity
        - Operating hours and thermal load patterns
        - Sustainable long-term thermal balance
        
        **COP Performance**:
        - Stable performance due to constant ground temperature
        - Highest COP values among heat pump technologies
        - Minimal seasonal variation in efficiency
        - Excellent performance at higher flow temperatures
        
        **Thermal Sustainability**:
        - Balanced thermal extraction and natural regeneration
        - Operating hour limitations for long-term sustainability
        - Ground thermal capacity and thermal diffusivity considerations

    Economic Analysis:
        
        **Investment Costs**:
        - Borehole drilling: Typically €50-150/m depending on ground conditions
        - Heat pump unit: Standard water-to-water heat pump equipment
        - Ground source infrastructure: Headers, circulation pumps, controls
        - Site preparation: Access for drilling equipment and installation
        
        **Operational Costs**:
        - Electricity: Heat pump and circulation pump operation
        - Maintenance: Minimal due to protected underground installation
        - Monitoring: Optional ground temperature and performance monitoring
        - Lifecycle: Very long system lifetime (>25 years for ground loop)

    Examples
    --------
    >>> # Create geothermal heat pump system
    >>> geothermal_hp = Geothermal(
    ...     name="GeoHP_01",
    ...     Fläche=2000.0,                      # m² borehole field area
    ...     Bohrtiefe=150.0,                    # m drilling depth
    ...     Temperatur_Geothermie=10.0,         # °C ground temperature
    ...     spez_Bohrkosten=120.0,              # €/m drilling costs
    ...     spez_Entzugsleistung=55.0,          # W/m extraction rate
    ...     Vollbenutzungsstunden=2200,         # hours full utilization
    ...     Abstand_Sonden=8.0,                 # m borehole spacing
    ...     spezifische_Investitionskosten_WP=1100.0,  # €/kW heat pump costs
    ...     min_Teillast=0.15                   # 15% minimum load
    ... )

    >>> # System design calculations
    >>> print(f"Number of boreholes: {geothermal_hp.Anzahl_Sonden}")
    >>> print(f"Heat extraction capacity: {geothermal_hp.Entzugsleistung_VBH:.1f} kW")
    >>> print(f"Annual thermal energy: {geothermal_hp.Entzugswärmemenge:.1f} MWh")
    >>> print(f"Borehole field costs: {geothermal_hp.Investitionskosten_Sonden:,.0f} €")

    >>> # Performance calculation with COP data
    >>> flow_temperatures = np.full(100, 50.0)  # °C supply temperature
    >>> cop_data = np.array([
    ...     [0,    35,   45,   55,   65,   75],    # Flow temperatures
    ...     [0,    4.5,  4.0,  3.4,  2.9,  2.4],  # COP at 0°C source
    ...     [10,   5.8,  5.1,  4.3,  3.6,  3.0],  # COP at 10°C source
    ...     [15,   6.2,  5.4,  4.6,  3.8,  3.1],  # COP at 15°C source
    ... ])
    >>> 
    >>> # Calculate operation with load profile
    >>> load_profile = np.random.uniform(100, 400, 100)  # kW varying load
    >>> geothermal_hp.calculate_operation(load_profile, flow_temperatures, cop_data)

    >>> # Economic evaluation
    >>> economic_params = {
    ...     'electricity_price': 0.26,           # €/kWh
    ...     'capital_interest_rate': 0.04,       # 4% interest
    ...     'inflation_rate': 0.025,             # 2.5% inflation
    ...     'time_period': 25,                   # 25-year analysis
    ...     'subsidy_eligibility': "Ja",         # BEW eligible
    ...     'hourly_rate': 60.0                  # €/hour labor cost
    ... }
    >>> 
    >>> # Calculate performance metrics
    >>> duration = 1.0  # hours
    >>> geothermal_hp.calculate_results(duration)
    >>> 
    >>> # Calculate heat generation costs
    >>> wgk = geothermal_hp.calculate_heat_generation_costs(
    ...     geothermal_hp.max_Wärmeleistung,
    ...     geothermal_hp.Wärmemenge_MWh,
    ...     geothermal_hp.Strommenge_MWh,
    ...     geothermal_hp.spez_Investitionskosten_Erdsonden,
    ...     economic_params
    ... )
    >>> 
    >>> print(f"Heat generation costs: {wgk:.2f} €/MWh")
    >>> print(f"SCOP: {geothermal_hp.SCOP:.2f}")
    >>> print(f"Operating hours: {geothermal_hp.Betriebsstunden:.0f} hours")

    >>> # System optimization example
    >>> # Optimize borehole field design for minimum costs
    >>> areas = np.arange(1000, 4000, 200)  # m² area range
    >>> depths = np.arange(100, 300, 25)    # m depth range
    >>> 
    >>> optimal_cost = float('inf')
    >>> optimal_design = None
    >>> 
    >>> for area in areas:
    ...     for depth in depths:
    ...         test_system = Geothermal(
    ...             name="TestGeo", 
    ...             Fläche=area, 
    ...             Bohrtiefe=depth,
    ...             Temperatur_Geothermie=10.0
    ...         )
    ...         # Calculate costs for this design
    ...         total_cost = (test_system.Investitionskosten_Sonden + 
    ...                      test_system.spezifische_Investitionskosten_WP * 
    ...                      test_system.Entzugsleistung_VBH)
    ...         if total_cost < optimal_cost and test_system.Entzugsleistung_VBH >= 500:
    ...             optimal_cost = total_cost
    ...             optimal_design = (area, depth)
    >>> 
    >>> print(f"Optimal design: {optimal_design[0]} m² area, {optimal_design[1]} m depth")
    >>> print(f"Investment cost: {optimal_cost:,.0f} €")

    See Also
    --------
    HeatPump : Base heat pump implementation
    BaseHeatGenerator : Base class for heat generators
    numpy.ndarray : Array operations for time-series data
    """

    def __init__(self, name: str, Fläche: float, Bohrtiefe: float, 
                 Temperatur_Geothermie: float, spez_Bohrkosten: float = 100, 
                 spez_Entzugsleistung: float = 50, Vollbenutzungsstunden: float = 2400, 
                 Abstand_Sonden: float = 10, spezifische_Investitionskosten_WP: float = 1000, 
                 min_Teillast: float = 0.2, min_area_geothermal: float = 0, 
                 max_area_geothermal: float = 5000, min_depth_geothermal: float = 0, 
                 max_depth_geothermal: float = 400) -> None:
        """
        Initialize geothermal heat pump system.

        Parameters
        ----------
        name : str
            Unique identifier for the geothermal heat pump system.
        Fläche : float
            Available area for geothermal borehole field installation [m²].
        Bohrtiefe : float
            Drilling depth for geothermal boreholes [m].
        Temperatur_Geothermie : float
            Undisturbed ground temperature at installation depth [°C].
        spez_Bohrkosten : float, optional
            Specific drilling costs per meter [€/m]. Default is 100.
        spez_Entzugsleistung : float, optional
            Specific thermal extraction power per meter borehole [W/m]. Default is 50.
        Vollbenutzungsstunden : float, optional
            Full utilization hours per year [hours]. Default is 2400.
        Abstand_Sonden : float, optional
            Distance between adjacent boreholes [m]. Default is 10.
        spezifische_Investitionskosten_WP : float, optional
            Specific investment costs for heat pump unit [€/kW]. Default is 1000.
        min_Teillast : float, optional
            Minimum part-load ratio [-]. Default is 0.2.
        min_area_geothermal : float, optional
            Minimum area for optimization [m²]. Default is 0.
        max_area_geothermal : float, optional
            Maximum area for optimization [m²]. Default is 5000.
        min_depth_geothermal : float, optional
            Minimum drilling depth for optimization [m]. Default is 0.
        max_depth_geothermal : float, optional
            Maximum drilling depth for optimization [m]. Default is 400.
        """
        super().__init__(name, spezifische_Investitionskosten_WP=spezifische_Investitionskosten_WP)
        self.Fläche = Fläche
        self.Bohrtiefe = Bohrtiefe
        self.Temperatur_Geothermie = Temperatur_Geothermie
        self.spez_Bohrkosten = spez_Bohrkosten
        self.spez_Entzugsleistung = spez_Entzugsleistung
        self.Vollbenutzungsstunden = Vollbenutzungsstunden
        self.Abstand_Sonden = Abstand_Sonden
        self.min_Teillast = min_Teillast
        self.min_area_geothermal = min_area_geothermal
        self.max_area_geothermal = max_area_geothermal
        self.min_depth_geothermal = min_depth_geothermal
        self.max_depth_geothermal = max_depth_geothermal

        # Calculate borehole field design parameters
        self.Anzahl_Sonden = (round(np.sqrt(self.Fläche) / self.Abstand_Sonden) + 1) ** 2
        self.Entzugsleistung_VBH = self.Bohrtiefe * self.spez_Entzugsleistung * self.Anzahl_Sonden / 1000  # kW
        self.Entzugswärmemenge = self.Entzugsleistung_VBH * self.Vollbenutzungsstunden / 1000  # MWh
        self.Investitionskosten_Sonden = self.Bohrtiefe * self.spez_Bohrkosten * self.Anzahl_Sonden

    def calculate_operation(self, Last_L: np.ndarray, VLT_L: np.ndarray, 
                           COP_data: np.ndarray) -> None:
        """
        Calculate operational performance with thermal sustainability constraints.

        This method performs comprehensive operational analysis of the geothermal
        heat pump considering thermal extraction sustainability, load demand matching,
        and heat pump technical constraints. It uses iterative calculation to balance
        thermal extraction rates with sustainable ground thermal management.

        Parameters
        ----------
        Last_L : numpy.ndarray
            Heat load demand time series [kW].
            Required heat output from the system.
        VLT_L : numpy.ndarray
            Required flow temperature time series [°C].
            Target supply temperatures for heat delivery.
        COP_data : numpy.ndarray
            COP lookup table for performance interpolation.
            Manufacturer performance data for efficiency calculations.

        Notes
        -----
        Operational Calculation Methodology:
            
            **Thermal Sustainability Iteration**:
            The method uses binary search to find the optimal operating hours
            that balance heat extraction with ground thermal sustainability:
            
            1. **Operating Hours Range**: 1-8760 hours per year
            2. **Heat Extraction Rate**: Annual thermal energy ÷ operating hours
            3. **Heat Output Capacity**: Based on COP and thermal extraction
            4. **Load Matching**: Compare capacity with actual demand
            5. **Convergence**: Iterate until thermal balance is achieved
            
            **Constraints Applied**:
            - Ground thermal extraction limits (sustainable rates)
            - Heat pump minimum part-load operation
            - Flow temperature delivery capability
            - Available area and drilling depth
            
            **Performance Calculation**:
            - Real-time COP based on ground and flow temperatures
            - Electrical consumption for actual heat output
            - Thermal extraction from ground
            - Operational state determination

        The iterative approach ensures that the system operates within
        sustainable thermal extraction limits while meeting heat demand
        requirements and maintaining economic viability.

        Examples
        --------
        >>> # Define operational scenario
        >>> hours = 8760
        >>> load_demand = 300 + 100 * np.sin(2 * np.pi * np.arange(hours) / 8760)
        >>> flow_temps = np.full(hours, 55.0)  # °C constant flow temperature
        >>> 
        >>> # COP data for geothermal heat pump
        >>> cop_data = np.array([
        ...     [0,    35,   45,   55,   65,   75],
        ...     [10,   5.8,  5.1,  4.3,  3.6,  3.0],  # 10°C ground temp
        ...     [12,   6.0,  5.3,  4.5,  3.7,  3.1],  # 12°C ground temp
        ... ])
        >>> 
        >>> # Calculate sustainable operation
        >>> geothermal_hp.calculate_operation(load_demand, flow_temps, cop_data)
        >>> 
        >>> # Analyze thermal sustainability
        >>> annual_extraction = np.sum(geothermal_hp.Wärmeleistung_kW - 
        ...                           geothermal_hp.el_Leistung_kW) / 1000
        >>> print(f"Annual thermal extraction: {annual_extraction:.1f} MWh")
        >>> print(f"Sustainable limit: {geothermal_hp.Entzugswärmemenge:.1f} MWh")
        >>> print(f"Utilization ratio: {annual_extraction/geothermal_hp.Entzugswärmemenge:.2f}")
        """
        if self.Fläche > 0 and self.Bohrtiefe > 0:
            # Calculate COP for all time steps
            self.COP, self.VLT_WP = self.calculate_COP(VLT_L, self.Temperatur_Geothermie, COP_data)

            # Iterative calculation for thermal sustainability
            # Find optimal operating hours that balance extraction with sustainability
            B_min = 1
            B_max = 8760
            tolerance = 0.5
            
            while B_max - B_min > tolerance:
                B = (B_min + B_max) / 2
                
                # Calculate heat extraction rate for these operating hours
                Entzugsleistung = self.Entzugswärmemenge * 1000 / B  # kW
                
                # Calculate corresponding heat pump capacity
                self.Wärmeleistung_kW = Entzugsleistung / (1 - (1 / self.COP))
                
                # Determine when heat pump can operate
                self.betrieb_mask = Last_L >= self.Wärmeleistung_kW * self.min_Teillast
                
                # Calculate actual operation within constraints
                self.Wärmeleistung_kW[self.betrieb_mask] = np.minimum(
                    Last_L[self.betrieb_mask], 
                    self.Wärmeleistung_kW[self.betrieb_mask]
                )
                self.el_Leistung_kW[self.betrieb_mask] = (
                    self.Wärmeleistung_kW[self.betrieb_mask] - 
                    (Entzugsleistung * np.ones_like(Last_L))[self.betrieb_mask]
                )
                
                # Calculate actual thermal extraction
                Entzugsleistung_tat_L = np.zeros_like(Last_L)
                Entzugsleistung_tat_L[self.betrieb_mask] = (
                    self.Wärmeleistung_kW[self.betrieb_mask] - 
                    self.el_Leistung_kW[self.betrieb_mask]
                )
                Entzugswärme = np.sum(Entzugsleistung_tat_L) / 1000  # MWh
                
                # Adjust operating hours based on thermal balance
                if Entzugswärme > self.Entzugswärmemenge:
                    B_min = B  # Need more operating hours (less extraction per hour)
                else:
                    B_max = B  # Can use fewer operating hours (more extraction per hour)
        else:
            # No geothermal system available - set all outputs to zero
            self.betrieb_mask = np.zeros_like(Last_L, dtype=bool)
            self.Wärmeleistung_kW = np.zeros_like(Last_L, dtype=float)
            self.el_Leistung_kW = np.zeros_like(Last_L, dtype=float)
            self.VLT_WP = np.zeros_like(Last_L, dtype=float)
            self.COP = np.zeros_like(Last_L, dtype=float)

    def generate(self, t: int, **kwargs) -> Tuple[float, float]:
        """
        Generate heat at specific time step with geothermal constraints.

        This method calculates heat generation and electricity consumption for
        a single time step, considering geothermal thermal extraction limits
        and operational constraints. It provides the interface for time-step-based
        simulation and real-time system operation.

        Parameters
        ----------
        t : int
            Current time step index.
            Index for accessing time-series data arrays.
        **kwargs : dict
            Additional parameters for heat generation:
            
            - **VLT_L** (float): Required flow temperature [°C]
            - **COP_data** (numpy.ndarray): Performance lookup table

        Returns
        -------
        tuple of float
            Heat generation and electricity consumption:
            
            heat_output : float
                Heat generation at time step t [kW].
                
            electricity_consumption : float
                Electricity consumption at time step t [kW].

        Notes
        -----
        Generation Logic:
            
            **Thermal Extraction Calculation**:
            - Assumes uniform thermal extraction distribution
            - Calculates instantaneous extraction rate from annual energy
            - Determines heat pump capacity based on COP and extraction
            
            **Operational Constraints**:
            - System active status verification
            - Flow temperature delivery capability
            - Available geothermal area and drilling depth
            - Thermal sustainability limits
            
            **Performance Calculation**:
            - Real-time COP based on ground and flow temperatures
            - Heat output matching thermal extraction capability
            - Electrical consumption calculation

        Examples
        --------
        >>> # Single time step generation
        >>> t = 1500  # Hour 1500 of simulation
        >>> 
        >>> generation_params = {
        ...     'VLT_L': 55.0,        # °C required flow temperature
        ...     'COP_data': cop_data  # Performance lookup table
        ... }
        >>> 
        >>> heat_out, elec_in = geothermal_hp.generate(t, **generation_params)
        >>> print(f"Hour {t}: {heat_out:.1f} kW heat, {elec_in:.1f} kW electricity")
        >>> 
        >>> # Check operational state and efficiency
        >>> if geothermal_hp.betrieb_mask[t]:
        ...     print(f"COP: {geothermal_hp.COP[t]:.2f}")
        ...     extraction = heat_out - elec_in
        ...     print(f"Ground heat extraction: {extraction:.1f} kW")
        ... else:
        ...     print("Geothermal heat pump not operating")
        """
        VLT = kwargs.get('VLT_L', 0)
        COP_data = kwargs.get('COP_data', None)

        # Calculate COP for current conditions
        self.COP[t], self.VLT_WP[t] = self.calculate_COP(VLT, self.Temperatur_Geothermie, COP_data)

        # Calculate thermal extraction rate (assuming uniform distribution)
        Entzugsleistung = self.Entzugswärmemenge * 1000 / 8760  # kW
        Wärmeleistung = Entzugsleistung / (1 - (1 / self.COP[t]))
        el_Leistung = Wärmeleistung - Entzugsleistung

        # Check operational constraints
        if (self.active and 
            self.VLT_WP[t] >= VLT and 
            self.Fläche > 0 and 
            self.Bohrtiefe > 0):
            # Geothermal system can operate
            self.betrieb_mask[t] = True
            self.Wärmeleistung_kW[t] = Wärmeleistung
            self.el_Leistung_kW[t] = self.Wärmeleistung_kW[t] - (self.Wärmeleistung_kW[t] / Wärmeleistung) * el_Leistung
        else:
            # System cannot operate - set outputs to zero
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0
            self.el_Leistung_kW[t] = 0
            self.VLT_WP[t] = 0
            self.COP[t] = 0

        return self.Wärmeleistung_kW[t], self.el_Leistung_kW[t]

    def calculate_results(self, duration: float) -> None:
        """
        Calculate aggregated performance metrics from simulation results.

        This method processes the time-series simulation results to calculate
        comprehensive performance indicators including energy production,
        efficiency metrics, operational statistics, and economic parameters
        specific to geothermal heat pump systems.

        Parameters
        ----------
        duration : float
            Time step duration [hours].
            Length of each simulation time step for energy calculations.

        Notes
        -----
        Calculated Metrics:
            
            **Capacity and Cost Metrics**:
            - Maximum heat output capacity from simulation
            - Specific geothermal investment costs per kW capacity
            - Total energy production and consumption
            
            **Performance Indicators**:
            - Seasonal Coefficient of Performance (SCOP)
            - Operating hours and system utilization
            - Start-up frequency and cycling behavior
            
            **Economic Parameters**:
            - Borehole field specific costs for economic analysis
            - Integration with heat generation cost calculations
            - Performance data for optimization algorithms

        Examples
        --------
        >>> # Calculate results after simulation
        >>> simulation_duration = 1.0  # hours per time step
        >>> geothermal_hp.calculate_results(simulation_duration)
        >>> 
        >>> # Display performance summary
        >>> print("Geothermal Heat Pump Performance Summary:")
        >>> print(f"Maximum capacity: {geothermal_hp.max_Wärmeleistung:.1f} kW")
        >>> print(f"Heat production: {geothermal_hp.Wärmemenge_MWh:.1f} MWh")
        >>> print(f"Electricity consumption: {geothermal_hp.Strommenge_MWh:.1f} MWh")
        >>> print(f"SCOP: {geothermal_hp.SCOP:.2f}")
        >>> print(f"Operating hours: {geothermal_hp.Betriebsstunden:.0f} hours")
        >>> print(f"Specific borehole costs: {geothermal_hp.spez_Investitionskosten_Erdsonden:.1f} €/kW")
        """
        # Calculate maximum heat output and specific costs
        self.max_Wärmeleistung = max(self.Wärmeleistung_kW)
        self.spez_Investitionskosten_Erdsonden = (
            self.Investitionskosten_Sonden / self.max_Wärmeleistung 
            if self.max_Wärmeleistung > 0 else 0
        )

        # Calculate energy totals
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Strommenge_MWh = np.sum(self.el_Leistung_kW / 1000) * duration
        
        # Calculate Seasonal Coefficient of Performance
        self.SCOP = self.Wärmemenge_MWh / self.Strommenge_MWh if self.Strommenge_MWh > 0 else 0
        
        # Calculate operational statistics
        starts = np.diff(self.betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(self.betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = (
            self.Betriebsstunden / self.Anzahl_Starts 
            if self.Anzahl_Starts > 0 else 0
        )

    def calculate(self, economic_parameters: Dict[str, Any], duration: float, 
                 load_profile: np.ndarray, **kwargs) -> Dict[str, Any]:
        """
        Comprehensive calculation of geothermal heat pump performance and economics.

        This method performs complete analysis of the geothermal heat pump system
        including thermal performance, economic evaluation, and environmental
        impact assessment. It integrates borehole field design, heat extraction
        modeling, and lifecycle cost analysis for comprehensive system evaluation.

        Parameters
        ----------
        economic_parameters : dict
            Economic analysis parameters containing cost data and financial assumptions.
        duration : float
            Simulation time step duration [hours].
        load_profile : numpy.ndarray
            Heat demand time series [kW].
        **kwargs : dict
            Additional calculation parameters:
            
            - **VLT_L** (numpy.ndarray): Flow temperature time series [°C]
            - **COP_data** (numpy.ndarray): Performance lookup table

        Returns
        -------
        dict
            Comprehensive calculation results containing:
            
            **Performance Results**:
            - Heat production and power consumption time series
            - Energy totals and efficiency metrics
            - Operational statistics and reliability data
            
            **Economic Results**:
            - Heat generation costs [€/MWh]
            - Investment cost breakdown (boreholes + heat pump)
            - Economic performance indicators
            
            **Environmental Results**:
            - CO2 emissions and specific emission factors
            - Primary energy consumption
            - Environmental impact assessment

        Notes
        -----
        Calculation Integration:
            
            **1. Thermal Performance Analysis**:
            - Borehole field thermal sustainability modeling
            - Heat extraction calculations with ground thermal limits
            - Heat pump performance with stable ground temperatures
            
            **2. Economic Evaluation**:
            - Geothermal-specific investment costs (drilling + heat pump)
            - Operational cost analysis with excellent efficiency
            - Heat generation cost calculation using VDI 2067 methodology
            
            **3. Environmental Assessment**:
            - CO2 emissions from electricity consumption only
            - High renewable energy contribution
            - Excellent environmental performance indicators

        Examples
        --------
        >>> # Define comprehensive calculation parameters
        >>> economic_params = {
        ...     'electricity_price': 0.25,       # €/kWh
        ...     'capital_interest_rate': 0.04,   # 4% interest
        ...     'inflation_rate': 0.025,         # 2.5% inflation
        ...     'time_period': 25,               # 25-year analysis
        ...     'subsidy_eligibility': "Ja",     # BEW eligible
        ...     'hourly_rate': 60.0              # €/hour labor
        ... }
        >>> 
        >>> # Generate annual load profile
        >>> hours = 8760
        >>> base_load = 300  # kW base heat demand
        >>> seasonal_variation = 200 * np.sin(2 * np.pi * np.arange(hours) / 8760 - np.pi/2)
        >>> load_profile = base_load + seasonal_variation
        >>> flow_temps = np.full(hours, 50.0)  # °C flow temperature
        >>> 
        >>> # Perform comprehensive calculation
        >>> results = geothermal_hp.calculate(
        ...     economic_parameters=economic_params,
        ...     duration=1.0,
        ...     load_profile=load_profile,
        ...     VLT_L=flow_temps,
        ...     COP_data=cop_data
        ... )
        >>> 
        >>> # Display comprehensive results
        >>> print("Geothermal Heat Pump Analysis Results:")
        >>> print(f"Heat generation: {results['Wärmemenge']:.1f} MWh/year")
        >>> print(f"Electricity demand: {results['Strombedarf']:.1f} MWh/year")
        >>> print(f"Heat generation costs: {results['WGK']:.2f} €/MWh")
        >>> print(f"SCOP: {geothermal_hp.SCOP:.2f}")
        >>> print(f"CO2 emissions: {results['spec_co2_total']:.3f} tCO2/MWh")
        >>> print(f"Operating hours: {results['Betriebsstunden']:.0f} hours/year")
        >>> print(f"Starts per year: {results['Anzahl_Starts']}")
        """
        # Extract required parameters
        VLT_L = kwargs.get('VLT_L')
        COP_data = kwargs.get('COP_data')

        # Perform operational calculation if not already done
        if not self.calculated:
            self.calculate_operation(load_profile, VLT_L, COP_data)
            self.calculated = True
        
        # Calculate performance metrics
        self.calculate_results(duration)
        
        # Economic evaluation with geothermal-specific costs
        self.WGK = self.calculate_heat_generation_costs(
            self.max_Wärmeleistung, 
            self.Wärmemenge_MWh, 
            self.Strommenge_MWh, 
            self.spez_Investitionskosten_Erdsonden, 
            economic_parameters
        )
        
        # Environmental impact assessment
        self.calculate_environmental_impact()

        # Compile comprehensive results
        results = {
            'tech_name': self.name,
            'Wärmemenge': self.Wärmemenge_MWh,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'Strombedarf': self.Strommenge_MWh,
            'el_Leistung_L': self.el_Leistung_kW,
            'WGK': self.WGK,
            'Anzahl_Starts': self.Anzahl_Starts,
            'Betriebsstunden': self.Betriebsstunden,
            'Betriebsstunden_pro_Start': self.Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            'color': "darkorange"  # Visualization color coding
        }

        return results
    
    def set_parameters(self, variables: list, variables_order: list, idx: int) -> None:
        """
        Set optimization parameters for the geothermal heat pump system.

        This method updates the borehole field area and drilling depth based on
        optimization algorithm results, enabling simultaneous optimization of
        both geometric parameters for economic and performance objectives.

        Parameters
        ----------
        variables : list
            List of optimization variable values.
        variables_order : list
            List defining variable order and identification.
        idx : int
            Technology index for parameter identification.

        Notes
        -----
        The method extracts area and drilling depth parameters from the
        optimization variables and recalculates all dependent system
        parameters including number of boreholes, thermal extraction
        capacity, and investment costs.

        Error handling ensures robust operation during optimization
        procedures and provides debugging information when parameter
        assignment fails.

        Examples
        --------
        >>> # Set optimized parameters
        >>> variables = [2500.0, 180.0, 1000.0]  # Mixed optimization variables
        >>> variables_order = ['Fläche_01', 'Bohrtiefe_01', 'capacity_02']
        >>> idx = 1  # Geothermal system index
        >>> 
        >>> geothermal_hp.set_parameters(variables, variables_order, idx)
        >>> print(f"Updated area: {geothermal_hp.Fläche} m²")
        >>> print(f"Updated depth: {geothermal_hp.Bohrtiefe} m")
        >>> print(f"New thermal capacity: {geothermal_hp.Entzugsleistung_VBH:.1f} kW")
        """
        try:
            # Extract geothermal parameters from optimization variables
            area_var = f"Fläche_{idx}"
            depth_var = f"Bohrtiefe_{idx}"
            
            if area_var in variables_order:
                area_index = variables_order.index(area_var)
                self.Fläche = variables[area_index]
            
            if depth_var in variables_order:
                depth_index = variables_order.index(depth_var)
                self.Bohrtiefe = variables[depth_index]
            
            # Recalculate dependent parameters
            self.Anzahl_Sonden = (round(np.sqrt(self.Fläche) / self.Abstand_Sonden) + 1) ** 2
            self.Entzugsleistung_VBH = self.Bohrtiefe * self.spez_Entzugsleistung * self.Anzahl_Sonden / 1000
            self.Entzugswärmemenge = self.Entzugsleistung_VBH * self.Vollbenutzungsstunden / 1000
            self.Investitionskosten_Sonden = self.Bohrtiefe * self.spez_Bohrkosten * self.Anzahl_Sonden
            
        except ValueError as e:
            print(f"Error setting parameters for {self.name}: {e}")

    def add_optimization_parameters(self, idx: int) -> Tuple[list, list, list]:
        """
        Define optimization parameters for geothermal heat pump system.

        This method specifies the optimization variables, bounds, and initial
        values for the geothermal heat pump system, enabling integration
        with optimization algorithms for borehole field design and system sizing.

        Parameters
        ----------
        idx : int
            Technology index for unique variable identification.

        Returns
        -------
        tuple
            Optimization parameter definition:
            
            initial_values : list
                Initial values for optimization variables.
                
            variables_order : list
                Variable names for parameter identification.
                
            bounds : list
                (min, max) bounds for each optimization variable.

        Notes
        -----
        Optimization Variables:
            
            **Borehole Field Area [m²]**:
            - Available land area for borehole installation
            - Determines maximum number of boreholes
            - Constraint by site characteristics and regulations
            
            **Drilling Depth [m]**:
            - Borehole depth for thermal extraction
            - Deeper drilling increases capacity but also costs
            - Typical range 50-400m depending on geology
            
            **Optimization Relationships**:
            - Thermal capacity = f(area, depth, spacing, extraction rate)
            - Investment costs = f(number of boreholes, depth, drilling costs)
            - Performance = f(ground temperature, heat pump efficiency)

        Examples
        --------
        >>> # Get optimization parameters
        >>> idx = 1  # System index
        >>> initial, variables, bounds = geothermal_hp.add_optimization_parameters(idx)
        >>> 
        >>> print("Geothermal Heat Pump Optimization Parameters:")
        >>> for i, (var, bound, init) in enumerate(zip(variables, bounds, initial)):
        ...     unit = "m²" if "Fläche" in var else "m"
        ...     print(f"{var}: {init} {unit}, bounds: {bound[0]}-{bound[1]} {unit}")
        >>> 
        >>> # Use in optimization algorithm
        >>> from scipy.optimize import minimize
        >>> 
        >>> def objective(x):
        ...     geothermal_hp.set_parameters(x, variables, idx)
        ...     # Calculate objective (e.g., minimize total costs)
        ...     total_cost = (geothermal_hp.Investitionskosten_Sonden + 
        ...               geothermal_hp.spezifische_Investitionskosten_WP * 
        ...               geothermal_hp.Entzugsleistung_VBH)
        ...     return total_cost
        >>> 
        >>> result = minimize(objective, initial, bounds=bounds)
        >>> print(f"Optimal area: {result.x[0]:.0f} m²")
        >>> print(f"Optimal depth: {result.x[1]:.0f} m")
        """
        initial_values = [self.Fläche, self.Bohrtiefe]
        variables_order = [f"Fläche_{idx}", f"Bohrtiefe_{idx}"]
        bounds = [
            (self.min_area_geothermal, self.max_area_geothermal),
            (self.min_depth_geothermal, self.max_depth_geothermal)
        ]
        
        return initial_values, variables_order, bounds

    def get_display_text(self) -> str:
        """
        Generate human-readable display text for system configuration.

        This method creates a formatted string containing key system
        parameters and configuration data for user interfaces, reports,
        and system documentation.

        Returns
        -------
        str
            Formatted display text with system parameters.

        Notes
        -----
        Display Information:
            
            **Borehole Field Parameters**:
            - Available area for geothermal installation
            - Drilling depth and number of boreholes
            - Ground source temperature
            
            **Economic Parameters**:
            - Specific drilling costs per meter
            - Heat extraction rate specifications
            - System design operating hours
            
            **Technical Specifications**:
            - Borehole spacing and field layout
            - Heat pump investment costs
            - Performance and efficiency characteristics

        Examples
        --------
        >>> # Display system configuration
        >>> print(geothermal_hp.get_display_text())
        >>> # Output: "GeoHP_01: Fläche Sondenfeld: 2000.0 m², Bohrtiefe: 150.0 m, 
        >>> #          Quelltemperatur Erdreich: 10.0 °C, spez. Bohrkosten: 120.0 €/m, 
        >>> #          spez. Entzugsleistung: 55.0 W/m, Vollbenutzungsstunden: 2200.0 h, 
        >>> #          Abstand Sonden: 8.0 m, spez. Investitionskosten Wärmepumpe: 1100.0 €/kW"
        """
        return (f"{self.name}: Fläche Sondenfeld: {self.Fläche} m², Bohrtiefe: {self.Bohrtiefe} m, "
                f"Quelltemperatur Erdreich: {self.Temperatur_Geothermie} °C, spez. Bohrkosten: "
                f"{self.spez_Bohrkosten} €/m, spez. Entzugsleistung: {self.spez_Entzugsleistung} W/m, "
                f"Vollbenutzungsstunden: {self.Vollbenutzungsstunden} h, Abstand Sonden: {self.Abstand_Sonden} m, "
                f"spez. Investitionskosten Wärmepumpe: {self.spezifische_Investitionskosten_WP} €/kW")
    
    def extract_tech_data(self) -> Tuple[str, str, str, str]:
        """
        Extract technology data for reporting and analysis.

        This method compiles key technical and economic data into formatted
        strings suitable for reports, comparisons, and system documentation.
        It provides standardized data extraction for analysis tools.

        Returns
        -------
        tuple of str
            Technology data summary:
            
            name : str
                System name identifier.
                
            dimensions : str
                Technical specifications and capacity information.
                
            costs : str
                Detailed cost breakdown for system components.
                
            full_costs : str
                Total investment cost summary.

        Notes
        -----
        Data Categories:
            
            **Technical Dimensions**:
            - Borehole field area and drilling depth
            - Ground temperature and thermal extraction specifications
            - Calculated thermal capacity from system design
            
            **Cost Breakdown**:
            - Borehole field drilling and installation costs
            - Heat pump equipment and installation costs
            - Component-wise investment breakdown
            
            **Total Investment**:
            - Combined geothermal system investment costs
            - Complete economic evaluation basis

        Examples
        --------
        >>> # Extract technology data
        >>> name, dimensions, costs, total = geothermal_hp.extract_tech_data()
        >>> 
        >>> print(f"Technology: {name}")
        >>> print(f"Specifications: {dimensions}")
        >>> print(f"Cost breakdown: {costs}")
        >>> print(f"Total investment: {total} €")
        >>> 
        >>> # Use for comparative analysis
        >>> technologies = [geo_hp_1, geo_hp_2, geo_hp_3]
        >>> comparison_data = [tech.extract_tech_data() for tech in technologies]
        >>> 
        >>> for name, dim, cost, total in comparison_data:
        ...     print(f"{name}: {total} € total investment")
        """
        # Technical specifications
        dimensions = (f"Fläche: {self.Fläche:.1f} m², Bohrtiefe: {self.Bohrtiefe:.1f} m, "
                     f"Temperatur Geothermie: {self.Temperatur_Geothermie:.1f} °C, "
                     f"Entzugsleistung: {self.spez_Entzugsleistung:.1f} W/m, "
                     f"th. Leistung: {self.max_Wärmeleistung:.1f} kW")
        
        # Detailed cost breakdown
        borehole_cost = self.Investitionskosten_Sonden
        hp_cost = self.spezifische_Investitionskosten_WP * self.max_Wärmeleistung
        costs = (f"Investitionskosten Sondenfeld: {borehole_cost:.1f} €, "
                f"Investitionskosten Wärmepumpe: {hp_cost:.1f} €")
        
        # Total investment costs
        full_costs = f"{borehole_cost + hp_cost:.1f} €"
        
        return self.name, dimensions, costs, full_costs