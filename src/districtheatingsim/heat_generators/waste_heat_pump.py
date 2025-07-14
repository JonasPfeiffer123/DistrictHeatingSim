"""
Waste Heat Pump Module
================================

This module provides comprehensive modeling capabilities for waste heat pump systems
in district heating applications.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11

Waste heat pumps utilize thermal energy from
industrial processes, data centers, wastewater treatment plants, and other waste
heat sources, providing highly efficient heating solutions with excellent economic
performance and environmental benefits.

The implementation includes detailed waste heat recovery modeling, heat pump
performance calculations considering source temperature variations, economic
analysis including waste heat infrastructure costs, and optimization capabilities
for system sizing. It supports variable waste heat availability and temperature
profiles for accurate seasonal performance modeling.

Features
--------
- Waste heat recovery system modeling with variable source temperatures
- Heat pump performance calculation with waste heat source integration
- Economic evaluation including waste heat recovery infrastructure costs
- Optimization support for cooling capacity and system sizing
- Integration with district heating storage and control systems
- Environmental impact assessment for waste heat utilization

Technical Specifications
------------------------
**Waste Heat Sources**:
- Industrial process waste heat with temperature ranges 20-80°C
- Data center cooling systems and server waste heat
- Wastewater treatment plant thermal energy recovery
- Commercial building HVAC system heat recovery

**Performance Modeling**:
- COP calculation based on waste heat and flow temperatures
- Heat recovery efficiency and thermal transfer rates
- Part-load operation with minimum threshold constraints
- System integration with existing waste heat infrastructure

**Economic Components**:
- Waste heat recovery system investment costs
- Heat pump unit and installation costs
- Infrastructure integration (heat exchangers, pumps, controls)
- Operational savings from waste heat utilization

Classes
-------
WasteHeatPump : Waste heat pump system implementation

Dependencies
------------
- numpy >= 1.20.0 : Numerical calculations and array operations
- districtheatingsim.heat_generators.base_heat_pump : Base heat pump framework

Applications
------------
The module supports waste heat pump applications including:
- Industrial district heating with process waste heat recovery
- Data center waste heat utilization for building heating
- Wastewater treatment plant energy recovery systems
- Commercial and residential district heating with waste heat integration

References
----------
Waste heat pump modeling based on:
- Industrial waste heat recovery guidelines and best practices
- Heat pump integration standards for waste heat sources
- VDI 4640 heat pump performance calculation methods
- Energy efficiency regulations for waste heat utilization
"""

import numpy as np
from typing import Dict, Any, Union, Tuple, Optional

from districtheatingsim.heat_generators.base_heat_pumps import HeatPump

class WasteHeatPump(HeatPump):
    """
    Waste heat pump system for district heating applications.

    This class implements a comprehensive waste heat pump model suitable for
    district heating systems. Waste heat pumps extract thermal energy from
    industrial processes, data centers, wastewater treatment, and other waste
    heat sources, providing highly efficient heating with excellent economic
    performance and environmental sustainability.

    Waste heat pumps offer exceptional advantages including utilization of
    otherwise wasted thermal energy, high coefficient of performance due to
    elevated source temperatures, reduced primary energy consumption, and
    excellent economic viability. The system requires integration with existing
    waste heat sources and careful thermal management.

    Parameters
    ----------
    name : str
        Unique identifier for the waste heat pump system.
        Should follow naming convention for system tracking and identification.
    Kühlleistung_Abwärme : float
        Waste heat cooling capacity available for extraction [kW].
        Thermal power available from waste heat source.
    Temperatur_Abwärme : float
        Waste heat source temperature [°C].
        Temperature level of available waste heat source.
    spez_Investitionskosten_Abwärme : float, optional
        Specific investment costs for waste heat recovery system [€/kW].
        Includes heat exchangers, pumps, controls. Default is 500 €/kW.
    spezifische_Investitionskosten_WP : float, optional
        Specific investment costs for heat pump unit [€/kW].
        Heat pump equipment and installation costs. Default is 1000 €/kW.
    min_Teillast : float, optional
        Minimum part-load ratio [-].
        Minimum operational capacity as fraction of rated power. Default is 0.2.
    opt_cooling_min : float, optional
        Minimum cooling capacity for optimization [kW]. Default is 0.
    opt_cooling_max : float, optional
        Maximum cooling capacity for optimization [kW]. Default is 500.

    Attributes
    ----------
    Kühlleistung_Abwärme : float
        Waste heat cooling capacity [kW].
    Temperatur_Abwärme : float
        Waste heat source temperature [°C].
    spez_Investitionskosten_Abwärme : float
        Specific investment costs for waste heat system [€/kW].
    min_Teillast : float
        Minimum part-load operating ratio [-].
    opt_cooling_min : float
        Minimum optimization capacity bound [kW].
    opt_cooling_max : float
        Maximum optimization capacity bound [kW].
    Wärmeleistung_kW : numpy.ndarray
        Heat output time series [kW].
    Kühlleistung_kW : numpy.ndarray
        Waste heat extraction time series [kW].
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
    Waste Heat Pump Technology:
        
        **Waste Heat Sources**:
        Various industrial and commercial waste heat sources can be utilized:
        - Industrial processes: Manufacturing, chemical production, metalworking
        - Data centers: Server cooling systems and IT equipment heat
        - Wastewater: Municipal and industrial wastewater treatment
        - Buildings: HVAC systems, refrigeration, ventilation air
        - Power generation: Condenser cooling water, flue gas heat recovery
        
        **Heat Recovery Systems**:
        - Heat exchangers for thermal energy transfer
        - Circulation pumps and distribution systems
        - Temperature and flow monitoring systems
        - Integration with existing process equipment
        
        **Performance Characteristics**:
        - High COP due to elevated source temperatures
        - Stable operation with consistent waste heat availability
        - Excellent part-load performance
        - Reduced cycling compared to ambient source systems

    Performance Modeling:
        
        **COP Calculation**:
        The Coefficient of Performance depends on:
        - Waste heat source temperature (typically 20-80°C)
        - District heating supply temperature (heat sink)
        - Temperature lift and heat pump technology
        - Heat exchanger effectiveness and system losses
        
        **Heat Recovery Efficiency**:
        - Available waste heat thermal power
        - Heat exchanger performance and approach temperatures
        - System integration losses and auxiliary power
        - Seasonal variations in waste heat availability

    Economic Analysis:
        
        **Investment Costs**:
        - Heat pump unit: Standard water-to-water heat pump equipment
        - Waste heat recovery: Heat exchangers, pumps, piping, controls
        - System integration: Connection to existing waste heat source
        - Installation: Mechanical and electrical installation costs
        
        **Operational Benefits**:
        - High efficiency reduces electricity consumption
        - Utilization of otherwise wasted thermal energy
        - Reduced primary energy consumption and emissions
        - Potential revenue from waste heat provider

    Examples
    --------
    >>> # Create waste heat pump for data center application
    >>> waste_hp = WasteHeatPump(
    ...     name="WasteHP_DataCenter",
    ...     Kühlleistung_Abwärme=300.0,         # kW waste heat capacity
    ...     Temperatur_Abwärme=35.0,            # °C data center waste heat
    ...     spez_Investitionskosten_Abwärme=600.0,  # €/kW recovery system
    ...     spezifische_Investitionskosten_WP=1200.0,  # €/kW heat pump
    ...     min_Teillast=0.25                   # 25% minimum load
    ... )

    >>> # Calculate heat pump performance
    >>> flow_temperatures = np.full(100, 60.0)  # °C supply temperature
    >>> cop_data = np.array([
    ...     [0,    35,   45,   55,   65,   75],    # Flow temperatures
    ...     [30,   6.5,  5.8,  5.0,  4.2,  3.5],  # COP at 30°C source
    ...     [35,   7.2,  6.4,  5.5,  4.6,  3.8],  # COP at 35°C source
    ...     [40,   7.8,  6.9,  6.0,  5.0,  4.1],  # COP at 40°C source
    ... ])
    >>> 
    >>> heat_output, electric_power, flow_temp, cop = waste_hp.calculate_heat_pump(
    ...     flow_temperatures, cop_data
    ... )

    >>> # Economic evaluation
    >>> economic_params = {
    ...     'electricity_price': 0.28,           # €/kWh
    ...     'capital_interest_rate': 0.04,       # 4% interest
    ...     'inflation_rate': 0.025,             # 2.5% inflation
    ...     'time_period': 20,                   # 20-year analysis
    ...     'subsidy_eligibility': "Ja",         # BEW eligible
    ...     'hourly_rate': 55.0                  # €/hour labor cost
    ... }
    >>> 
    >>> # System operation simulation
    >>> load_profile = np.random.uniform(200, 800, 100)  # kW varying load
    >>> waste_hp.calculate_operation(load_profile, flow_temperatures, cop_data)
    >>> 
    >>> # Calculate performance metrics
    >>> duration = 1.0  # hours
    >>> waste_hp.calculate_results(duration)
    >>> 
    >>> print(f"Total heat production: {waste_hp.Wärmemenge_MWh:.1f} MWh")
    >>> print(f"SCOP: {waste_hp.SCOP:.2f}")
    >>> print(f"Operating hours: {waste_hp.Betriebsstunden:.0f} hours")

    >>> # Industrial waste heat application
    >>> industrial_waste_hp = WasteHeatPump(
    ...     name="WasteHP_Industrial",
    ...     Kühlleistung_Abwärme=800.0,         # kW industrial process heat
    ...     Temperatur_Abwärme=55.0,            # °C process cooling water
    ...     spez_Investitionskosten_Abwärme=400.0,  # €/kW lower integration cost
    ...     spezifische_Investitionskosten_WP=1000.0
    ... )
    >>> 
    >>> # Higher temperature waste heat provides better performance
    >>> industrial_cop_data = np.array([
    ...     [0,    35,   45,   55,   65,   75],
    ...     [50,   9.5,  8.2,  7.0,  5.8,  4.8],  # COP at 50°C source
    ...     [55,   10.2, 8.8,  7.5,  6.2,  5.1],  # COP at 55°C source
    ...     [60,   10.8, 9.3,  8.0,  6.6,  5.4],  # COP at 60°C source
    ... ])

    See Also
    --------
    HeatPump : Base heat pump implementation
    BaseHeatGenerator : Base class for heat generators
    numpy.ndarray : Array operations for time-series data
    """

    def __init__(self, name: str, Kühlleistung_Abwärme: float, 
                 Temperatur_Abwärme: float, spez_Investitionskosten_Abwärme: float = 500, 
                 spezifische_Investitionskosten_WP: float = 1000, min_Teillast: float = 0.2,
                 opt_cooling_min: float = 0, opt_cooling_max: float = 500) -> None:
        """
        Initialize waste heat pump system.

        Parameters
        ----------
        name : str
            Unique identifier for the waste heat pump system.
        Kühlleistung_Abwärme : float
            Waste heat cooling capacity available for extraction [kW].
        Temperatur_Abwärme : float
            Waste heat source temperature [°C].
        spez_Investitionskosten_Abwärme : float, optional
            Specific investment costs for waste heat recovery system [€/kW]. Default is 500.
        spezifische_Investitionskosten_WP : float, optional
            Specific investment costs for heat pump unit [€/kW]. Default is 1000.
        min_Teillast : float, optional
            Minimum part-load ratio [-]. Default is 0.2.
        opt_cooling_min : float, optional
            Minimum cooling capacity for optimization [kW]. Default is 0.
        opt_cooling_max : float, optional
            Maximum cooling capacity for optimization [kW]. Default is 500.
        """
        super().__init__(name, spezifische_Investitionskosten_WP=spezifische_Investitionskosten_WP)
        self.Kühlleistung_Abwärme = Kühlleistung_Abwärme
        self.Temperatur_Abwärme = Temperatur_Abwärme
        self.spez_Investitionskosten_Abwärme = spez_Investitionskosten_Abwärme
        self.min_Teillast = min_Teillast
        self.opt_cooling_min = opt_cooling_min
        self.opt_cooling_max = opt_cooling_max

    def calculate_heat_pump(self, VLT_L: np.ndarray, COP_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate heat pump performance for waste heat operation.

        This method computes the thermal performance of the waste heat pump
        including heat output generation, electrical power consumption, and
        achievable flow temperatures based on the available waste heat source.

        Parameters
        ----------
        VLT_L : numpy.ndarray
            Required flow temperature array [°C].
            Target supply temperatures for district heating system.
        COP_data : numpy.ndarray
            COP lookup table for performance interpolation.
            2D array with source and sink temperature relationships.

        Returns
        -------
        tuple of numpy.ndarray
            Heat pump performance data:
            
            Wärmeleistung_kW : numpy.ndarray
                Heat output from waste heat pump [kW].
                Thermal energy delivered to district heating system.
                
            el_Leistung_kW : numpy.ndarray
                Electrical power consumption [kW].
                Electricity demand for heat pump operation.
                
            VLT_WP_L : numpy.ndarray
                Achievable flow temperatures [°C].
                Heat pump supply temperatures considering technical limits.
                
            COP_L : numpy.ndarray
                Coefficient of Performance [-].
                Instantaneous efficiency for given operating conditions.

        Notes
        -----
        Performance Calculation Process:
            
            **COP Determination**:
            - Uses waste heat temperature as source temperature
            - Interpolates performance from manufacturer data
            - Considers temperature lift limitations
            - Accounts for heat exchanger effectiveness
            
            **Energy Balance**:
            Heat output = Waste heat extraction + Electrical input
            COP = Heat output / Electrical input
            
            **Thermal Constraints**:
            - Available waste heat capacity limitation
            - Heat pump refrigerant operating range
            - Flow temperature delivery capability
            - Heat exchanger approach temperatures

        The calculation ensures energy balance consistency and applies
        technical constraints for realistic waste heat pump modeling.

        Examples
        --------
        >>> # Calculate performance for waste heat pump
        >>> flow_temps = np.array([45, 50, 55, 60, 65])  # °C
        >>> 
        >>> # COP data for waste heat pump with 40°C source
        >>> cop_data = np.array([
        ...     [0,    35,   45,   55,   65,   75],
        ...     [35,   7.0,  6.2,  5.3,  4.4,  3.6],
        ...     [40,   7.8,  6.9,  5.9,  4.9,  4.0],
        ...     [45,   8.5,  7.5,  6.4,  5.3,  4.3]
        ... ])
        >>> 
        >>> # Calculate performance
        >>> heat_out, electric, flow, cop = waste_hp.calculate_heat_pump(
        ...     flow_temps, cop_data
        ... )
        >>> 
        >>> for i, temp in enumerate(flow_temps):
        ...     print(f"Flow {temp}°C: COP={cop[i]:.2f}, "
        ...           f"Heat={heat_out[i]:.1f}kW, "
        ...           f"Electric={electric[i]:.1f}kW")
        """
        # Calculate COP based on waste heat temperature and flow temperature
        COP_L, VLT_WP_L = self.calculate_COP(VLT_L, self.Temperatur_Abwärme, COP_data)
        
        # Calculate heat output based on waste heat extraction and COP
        Wärmeleistung_kW = self.Kühlleistung_Abwärme / (1 - (1 / COP_L))
        
        # Calculate electrical power consumption
        el_Leistung_kW = Wärmeleistung_kW - self.Kühlleistung_Abwärme

        return Wärmeleistung_kW, el_Leistung_kW, VLT_WP_L, COP_L

    def calculate_operation(self, Last_L: np.ndarray, VLT_L: np.ndarray, 
                           COP_data: np.ndarray) -> None:
        """
        Calculate operational performance considering waste heat availability.

        This method performs comprehensive operational analysis of the waste heat
        pump considering waste heat source availability, load demand matching,
        and heat pump technical constraints. It determines optimal operation
        points and calculates corresponding performance metrics.

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
        Operational Logic:
            
            **Waste Heat Availability Check**:
            - Verifies waste heat source is available
            - Calculates maximum heat pump capacity from waste heat
            - Determines operational constraints
            
            **Load Matching**:
            - Heat output limited by waste heat capacity and demand
            - Part-load operation down to minimum threshold
            - Load following capability within waste heat constraints
            
            **Performance Calculation**:
            - Real-time COP based on waste heat and flow temperatures
            - Electrical consumption for actual heat output
            - Waste heat extraction rates
            - Operational state determination

        The method updates all time-series attributes with calculated
        performance data and operational states for the simulation period.

        Examples
        --------
        >>> # Define operational scenario
        >>> hours = 1000
        >>> load_demand = 400 + 200 * np.sin(np.arange(hours) / 100)  # Varying load
        >>> flow_temps = np.full(hours, 55.0)  # °C constant flow temp
        >>> 
        >>> # Calculate operation
        >>> waste_hp.calculate_operation(load_demand, flow_temps, cop_data)
        >>> 
        >>> # Analyze results
        >>> operating_hours = np.sum(waste_hp.betrieb_mask)
        >>> avg_cop = np.mean(waste_hp.COP[waste_hp.betrieb_mask])
        >>> max_output = np.max(waste_hp.Wärmeleistung_kW)
        >>> 
        >>> print(f"Operating hours: {operating_hours}/{hours}")
        >>> print(f"Average COP: {avg_cop:.2f}")
        >>> print(f"Maximum output: {max_output:.1f} kW")
        >>> print(f"Waste heat utilization: {np.sum(waste_hp.Kühlleistung_kW):.1f} kWh")
        """
        if self.Kühlleistung_Abwärme > 0:
            # Calculate heat pump performance for all time steps
            self.Wärmeleistung_kW, self.el_Leistung_kW, self.VLT_WP, self.COP = self.calculate_heat_pump(VLT_L, COP_data)

            # Determine operational constraints
            # Heat pump operates when load demand exceeds minimum part-load threshold
            self.betrieb_mask = Last_L >= self.Wärmeleistung_kW * self.min_Teillast
            
            # Adjust heat output to match actual demand (limited by capacity)
            self.Wärmeleistung_kW[self.betrieb_mask] = np.minimum(
                Last_L[self.betrieb_mask], 
                self.Wärmeleistung_kW[self.betrieb_mask]
            )
            
            # Calculate corresponding electrical consumption
            self.el_Leistung_kW[self.betrieb_mask] = (
                self.Wärmeleistung_kW[self.betrieb_mask] - 
                self.Kühlleistung_Abwärme
            )
            
            # Set outputs to zero when not operating
            self.Wärmeleistung_kW[~self.betrieb_mask] = 0
            self.el_Leistung_kW[~self.betrieb_mask] = 0
            self.VLT_WP[~self.betrieb_mask] = 0
            self.COP[~self.betrieb_mask] = 0
            
            # Initialize waste heat extraction array
            self.Kühlleistung_kW = np.zeros_like(Last_L, dtype=float)
            self.Kühlleistung_kW[self.betrieb_mask] = self.Kühlleistung_Abwärme
        else:
            # No waste heat available - set all outputs to zero
            self.betrieb_mask = np.zeros_like(Last_L, dtype=bool)
            self.Wärmeleistung_kW = np.zeros_like(Last_L, dtype=float)
            self.Kühlleistung_kW = np.zeros_like(Last_L, dtype=float)
            self.el_Leistung_kW = np.zeros_like(Last_L, dtype=float)
            self.VLT_WP = np.zeros_like(Last_L, dtype=float)
            self.COP = np.zeros_like(Last_L, dtype=float)

    def generate(self, t: int, **kwargs) -> Tuple[float, float]:
        """
        Generate heat at specific time step with waste heat constraints.

        This method calculates heat generation and electricity consumption for
        a single time step, considering waste heat availability and operational
        constraints. It provides the interface for time-step-based simulation
        and real-time system operation.

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
            
            **Waste Heat Check**:
            - Verifies waste heat source availability
            - Calculates heat pump capacity from waste heat
            - Determines electrical power requirement
            
            **Operational Constraints**:
            - System active status verification
            - Flow temperature delivery capability
            - Waste heat source availability
            
            **Performance Calculation**:
            - Real-time COP based on current conditions
            - Heat output from waste heat extraction
            - Electrical consumption calculation

        Examples
        --------
        >>> # Single time step generation
        >>> t = 500  # Hour 500 of simulation
        >>> 
        >>> generation_params = {
        ...     'VLT_L': 60.0,        # °C required flow temperature
        ...     'COP_data': cop_data  # Performance lookup table
        ... }
        >>> 
        >>> heat_out, elec_in = waste_hp.generate(t, **generation_params)
        >>> print(f"Hour {t}: {heat_out:.1f} kW heat, {elec_in:.1f} kW electricity")
        >>> 
        >>> # Check operational state and efficiency
        >>> if waste_hp.betrieb_mask[t]:
        ...     print(f"COP: {waste_hp.COP[t]:.2f}")
        ...     print(f"Waste heat extraction: {waste_hp.Kühlleistung_kW[t]:.1f} kW")
        ... else:
        ...     print("Waste heat pump not operating")
        """
        VLT = kwargs.get('VLT_L', 0)
        COP_data = kwargs.get('COP_data', None)

        # Calculate performance for current time step
        self.Wärmeleistung_kW[t], self.el_Leistung_kW[t], self.VLT_WP[t], self.COP[t] = self.calculate_heat_pump(VLT, COP_data)

        # Check operational constraints
        if (self.active and 
            self.VLT_WP[t] >= VLT and 
            self.Kühlleistung_Abwärme > 0):
            # Waste heat pump can operate - generate heat
            self.betrieb_mask[t] = True
            self.Kühlleistung_kW[t] = self.Kühlleistung_Abwärme
        else:
            # Cannot operate - set outputs to zero
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0
            self.el_Leistung_kW[t] = 0
            self.Kühlleistung_kW[t] = 0
            self.VLT_WP[t] = 0
            self.COP[t] = 0

        return self.Wärmeleistung_kW[t], self.el_Leistung_kW[t]
    
    def calculate_results(self, duration: float) -> None:
        """
        Calculate aggregated performance metrics from simulation results.

        This method processes the time-series simulation results to calculate
        comprehensive performance indicators including energy production,
        efficiency metrics, and operational statistics specific to waste
        heat pump systems.

        Parameters
        ----------
        duration : float
            Time step duration [hours].
            Length of each simulation time step for energy calculations.

        Notes
        -----
        Calculated Metrics:
            
            **Energy Metrics**:
            - Total heat production [MWh]
            - Total electricity consumption [MWh]
            - Seasonal Coefficient of Performance (SCOP)
            - Maximum heat output [kW]
            
            **Operational Metrics**:
            - Number of start-up events
            - Total operating hours
            - Average operating hours per start
            - Waste heat utilization efficiency
            
            **Performance Indicators**:
            - System availability and reliability
            - Efficiency variations throughout operation
            - Waste heat recovery effectiveness

        Examples
        --------
        >>> # Calculate results after simulation
        >>> simulation_duration = 1.0  # hours per time step
        >>> waste_hp.calculate_results(simulation_duration)
        >>> 
        >>> # Display performance summary
        >>> print("Waste Heat Pump Performance Summary:")
        >>> print(f"Heat production: {waste_hp.Wärmemenge_MWh:.1f} MWh")
        >>> print(f"Electricity consumption: {waste_hp.Strommenge_MWh:.1f} MWh")
        >>> print(f"SCOP: {waste_hp.SCOP:.2f}")
        >>> print(f"Operating hours: {waste_hp.Betriebsstunden:.0f} hours")
        >>> print(f"Starts per year: {waste_hp.Anzahl_Starts}")
        >>> print(f"Hours per start: {waste_hp.Betriebsstunden_pro_Start:.1f}")
        """
        # Calculate total energy production and consumption
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Strommenge_MWh = np.sum(self.el_Leistung_kW / 1000) * duration
        
        # Calculate Seasonal Coefficient of Performance
        self.SCOP = self.Wärmemenge_MWh / self.Strommenge_MWh if self.Strommenge_MWh > 0 else 0

        # Determine maximum heat output
        self.max_Wärmeleistung = np.max(self.Wärmeleistung_kW)
        
        # Calculate operational statistics
        starts = np.diff(self.betrieb_mask.astype(int)) > 0  # Start-up events
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(self.betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = (self.Betriebsstunden / self.Anzahl_Starts 
                                         if self.Anzahl_Starts > 0 else 0)
    
    def calculate(self, economic_parameters: Dict[str, Any], duration: float, 
                 load_profile: np.ndarray, **kwargs) -> Dict[str, Any]:
        """
        Comprehensive calculation of waste heat pump performance and economics.

        This method performs complete analysis of the waste heat pump system
        including thermal performance, economic evaluation, and environmental
        impact assessment. It integrates waste heat recovery modeling with
        heat pump performance and lifecycle cost analysis.

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
            - Investment cost breakdown (waste heat system + heat pump)
            - Economic performance indicators
            
            **Environmental Results**:
            - CO2 emissions and specific emission factors
            - Primary energy consumption
            - Environmental impact assessment

        Notes
        -----
        Calculation Integration:
            
            **1. Performance Analysis**:
            - Waste heat availability and recovery efficiency
            - Heat pump performance with elevated source temperatures
            - System operation with load following capability
            
            **2. Economic Evaluation**:
            - Waste heat recovery system investment costs
            - Heat pump equipment costs and installation
            - Operational cost analysis with excellent efficiency
            - Heat generation cost calculation using VDI 2067 methodology
            
            **3. Environmental Assessment**:
            - CO2 emissions from electricity consumption only
            - High renewable energy contribution from waste heat
            - Excellent environmental performance indicators

        Examples
        --------
        >>> # Define comprehensive calculation parameters
        >>> economic_params = {
        ...     'electricity_price': 0.28,       # €/kWh
        ...     'capital_interest_rate': 0.04,   # 4% interest
        ...     'inflation_rate': 0.025,         # 2.5% inflation
        ...     'time_period': 20,               # 20-year analysis
        ...     'subsidy_eligibility': "Ja",     # BEW eligible
        ...     'hourly_rate': 55.0              # €/hour labor
        ... }
        >>> 
        >>> # Generate load profile with waste heat availability
        >>> hours = 8760
        >>> base_load = 500  # kW base heat demand
        >>> daily_variation = 200 * np.sin(2 * np.pi * np.arange(hours) / 24)
        >>> load_profile = base_load + daily_variation
        >>> flow_temps = np.full(hours, 55.0)  # °C flow temperature
        >>> 
        >>> # Perform comprehensive calculation
        >>> results = waste_hp.calculate(
        ...     economic_parameters=economic_params,
        ...     duration=1.0,
        ...     load_profile=load_profile,
        ...     VLT_L=flow_temps,
        ...     COP_data=cop_data
        ... )
        >>> 
        >>> # Display comprehensive results
        >>> print("Waste Heat Pump Analysis Results:")
        >>> print(f"Heat generation: {results['Wärmemenge']:.1f} MWh/year")
        >>> print(f"Electricity demand: {results['Strombedarf']:.1f} MWh/year")
        >>> print(f"Heat generation costs: {results['WGK']:.2f} €/MWh")
        >>> print(f"SCOP: {waste_hp.SCOP:.2f}")
        >>> print(f"CO2 emissions: {results['spec_co2_total']:.3f} tCO2/MWh")
        >>> print(f"Operating hours: {results['Betriebsstunden']:.0f} hours/year")
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
        
        # Economic evaluation with waste heat specific costs
        self.WGK = self.calculate_heat_generation_costs(
            self.max_Wärmeleistung, 
            self.Wärmemenge_MWh, 
            self.Strommenge_MWh, 
            self.spez_Investitionskosten_Abwärme, 
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
            'color': "grey"  # Visualization color coding
        }

        return results
    
    def set_parameters(self, variables: list, variables_order: list, idx: int) -> None:
        """
        Set optimization parameters for the waste heat pump system.

        This method updates the waste heat cooling capacity based on optimization
        algorithm results, enabling capacity optimization for economic and
        performance objectives with waste heat source constraints.

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
        The method extracts the waste heat cooling capacity parameter from
        the optimization variables and updates the system configuration
        accordingly. Error handling ensures robust operation during
        optimization procedures.

        Examples
        --------
        >>> # Set optimized capacity
        >>> variables = [450.0, 0.95, 70.0]  # Mixed optimization variables
        >>> variables_order = ['Kühlleistung_Abwärme_01', 'efficiency_02', 'temp_03']
        >>> idx = 1  # Waste heat pump index
        >>> 
        >>> waste_hp.set_parameters(variables, variables_order, idx)
        >>> print(f"Updated waste heat capacity: {waste_hp.Kühlleistung_Abwärme} kW")
        """
        try:
            # Extract waste heat capacity from optimization variables
            capacity_var = f"Kühlleistung_Abwärme_{idx}"
            if capacity_var in variables_order:
                capacity_index = variables_order.index(capacity_var)
                self.Kühlleistung_Abwärme = variables[capacity_index]
        except ValueError as e:
            print(f"Error setting parameters for {self.name}: {e}")

    def add_optimization_parameters(self, idx: int) -> Tuple[list, list, list]:
        """
        Define optimization parameters for waste heat pump system.

        This method specifies the optimization variables, bounds, and initial
        values for the waste heat pump system, enabling integration with
        optimization algorithms for waste heat capacity sizing and system design.

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
            
            **Waste Heat Cooling Capacity [kW]**:
            - Available waste heat for heat pump operation
            - Determines maximum heat pump thermal output
            - Constraint by actual waste heat source availability
            
            **Optimization Relationships**:
            - Heat pump capacity = f(waste heat capacity, COP)
            - Investment costs = f(waste heat system + heat pump costs)
            - Performance = f(waste heat temperature, heat pump efficiency)

        Examples
        --------
        >>> # Get optimization parameters
        >>> idx = 1  # System index
        >>> initial, variables, bounds = waste_hp.add_optimization_parameters(idx)
        >>> 
        >>> print("Waste Heat Pump Optimization Parameters:")
        >>> for i, (var, bound, init) in enumerate(zip(variables, bounds, initial)):
        ...     print(f"{var}: {init} kW, bounds: {bound[0]}-{bound[1]} kW")
        >>> 
        >>> # Use in optimization algorithm
        >>> from scipy.optimize import minimize
        >>> 
        >>> def objective(x):
        ...     waste_hp.set_parameters(x, variables, idx)
        ...     # Calculate objective function (e.g., minimize costs)
        ...     return waste_hp.WGK  # Heat generation costs
        >>> 
        >>> result = minimize(objective, initial, bounds=bounds)
        >>> print(f"Optimal waste heat capacity: {result.x[0]:.1f} kW")
        """
        initial_values = [self.Kühlleistung_Abwärme]
        variables_order = [f"Kühlleistung_Abwärme_{idx}"]
        bounds = [(self.opt_cooling_min, self.opt_cooling_max)]

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
            
            **Waste Heat Parameters**:
            - Available waste heat cooling capacity
            - Waste heat source temperature level
            - System identification and type
            
            **Economic Parameters**:
            - Waste heat recovery system investment costs
            - Heat pump equipment investment costs
            - Cost breakdown for economic analysis
            
            **Technical Specifications**:
            - Performance characteristics
            - System integration requirements

        Examples
        --------
        >>> # Display system configuration
        >>> print(waste_hp.get_display_text())
        >>> # Output: "WasteHP_DataCenter: Kühlleistung Abwärme: 300.0 kW, 
        >>> #          Temperatur Abwärme: 35.0 °C, spez. Investitionskosten Abwärme: 600.0 €/kW, 
        >>> #          spez. Investitionskosten Wärmepumpe: 1200.0 €/kW"
        """
        return (f"{self.name}: Kühlleistung Abwärme: {self.Kühlleistung_Abwärme} kW, "
                f"Temperatur Abwärme: {self.Temperatur_Abwärme} °C, spez. Investitionskosten Abwärme: "
                f"{self.spez_Investitionskosten_Abwärme} €/kW, spez. Investitionskosten Wärmepumpe: "
                f"{self.spezifische_Investitionskosten_WP} €/kW")
    
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
            - Waste heat cooling capacity and source temperature
            - Calculated thermal output capacity
            - System performance specifications
            
            **Cost Breakdown**:
            - Waste heat recovery system investment costs
            - Heat pump equipment and installation costs
            - Component-wise investment breakdown
            
            **Total Investment**:
            - Combined waste heat pump system investment costs
            - Complete economic evaluation basis

        Examples
        --------
        >>> # Extract technology data
        >>> name, dimensions, costs, total = waste_hp.extract_tech_data()
        >>> 
        >>> print(f"Technology: {name}")
        >>> print(f"Specifications: {dimensions}")
        >>> print(f"Cost breakdown: {costs}")
        >>> print(f"Total investment: {total} €")
        >>> 
        >>> # Use for comparative analysis
        >>> technologies = [waste_hp_1, waste_hp_2, waste_hp_3]
        >>> comparison_data = [tech.extract_tech_data() for tech in technologies]
        >>> 
        >>> for name, dim, cost, total in comparison_data:
        ...     print(f"{name}: {total} € total investment")
        """
        # Technical specifications
        dimensions = (f"Kühlleistung Abwärme: {self.Kühlleistung_Abwärme:.1f} kW, "
                     f"Temperatur Abwärme: {self.Temperatur_Abwärme:.1f} °C, "
                     f"th. Leistung: {self.max_Wärmeleistung:.1f} kW")
        
        # Detailed cost breakdown
        waste_heat_cost = self.spez_Investitionskosten_Abwärme * self.max_Wärmeleistung
        hp_cost = self.spezifische_Investitionskosten_WP * self.max_Wärmeleistung
        costs = (f"Investitionskosten Abwärmenutzung: {waste_heat_cost:.1f} €, "
                f"Investitionskosten Wärmepumpe: {hp_cost:.1f} €")
        
        # Total investment costs
        full_costs = f"{waste_heat_cost + hp_cost:.1f}"
        
        return self.name, dimensions, costs, full_costs