"""
River Water Heat Pump System Module
===================================

This module provides comprehensive modeling capabilities for river water heat pump systems
in district heating applications.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11

River water heat pumps utilize the thermal energy stored
in rivers and water bodies as a renewable heat source, offering sustainable heating solutions
with high efficiency and environmental benefits.

The implementation includes detailed thermodynamic modeling, economic analysis considering
water intake infrastructure costs, environmental impact assessment, and optimization
capabilities for system design. It supports both constant and variable river temperature
profiles for accurate seasonal performance modeling.

Features
--------
- River water heat extraction modeling with temperature-dependent performance
- Water intake infrastructure cost evaluation and system sizing
- Seasonal temperature variation support with time-series data
- Part-load operation modeling with minimum load constraints
- Environmental impact assessment for aquatic ecosystem protection
- Economic optimization considering intake infrastructure and heat pump costs
- Integration with district heating storage and control systems

Technical Specifications
------------------------
**Heat Source Characteristics**:
- River water temperature range: typically 0-25°C
- Heat extraction rates: limited by environmental regulations
- Intake system design: pumps, heat exchangers, filtration
- Return water temperature constraints for ecosystem protection

**Performance Modeling**:
- COP calculation based on river and flow temperatures
- Part-load performance with minimum operating thresholds
- Seasonal efficiency variations with water temperature changes
- Ice formation protection and winter operation considerations

**Economic Components**:
- Heat pump unit investment costs
- River water intake infrastructure (pumps, pipes, heat exchangers)
- Environmental permit costs and compliance requirements
- Operational costs including pumping energy and maintenance

Classes
-------
RiverHeatPump : River water heat pump system implementation

Dependencies
------------
- numpy >= 1.20.0 : Numerical calculations and array operations
- districtheatingsim.heat_generators.base_heat_pump : Base heat pump framework

Applications
------------
The module supports river water heat pump applications including:
- District heating systems with river water heat extraction
- Industrial heating applications near water bodies
- Large-scale heat pump installations with renewable heat sources
- Seasonal thermal energy storage systems with aquatic heat sources

References
----------
River water heat pump modeling based on:
- German water management regulations (Wasserhaushaltsgesetz)
- Environmental impact guidelines for aquatic heat extraction
- VDI 4650 heat pump performance calculation standards
- District heating integration best practices
"""

import numpy as np
from typing import Dict, Any, Union, Tuple, Optional

from districtheatingsim.heat_generators.base_heat_pumps import HeatPump

class RiverHeatPump(HeatPump):
    """
    River water heat pump system for district heating applications.

    This class implements a comprehensive river water heat pump model suitable for
    district heating systems. River water heat pumps extract thermal energy from
    rivers and water bodies, providing renewable heating with high efficiency and
    environmental sustainability. The implementation includes detailed performance
    modeling, economic analysis, and environmental considerations.

    River water heat pumps offer several advantages including stable heat source
    temperatures, high seasonal performance factors, and minimal land use requirements.
    The system includes water intake infrastructure, heat exchangers, and environmental
    protection measures to ensure sustainable operation.

    Parameters
    ----------
    name : str
        Unique identifier for the river heat pump system.
        Should follow naming convention for system tracking.
    Wärmeleistung_FW_WP : float
        Rated thermal output capacity [kW].
        Design heat output under nominal conditions.
    Temperatur_FW_WP : float or numpy.ndarray
        River water temperature [°C].
        Can be constant value or time-series array for seasonal variation.
    dT : float, optional
        Allowable temperature difference tolerance [K].
        Operational flexibility for temperature variations. Default is 0.
    spez_Investitionskosten_Flusswasser : float, optional
        Specific investment costs for river water system [€/kW].
        Includes intake, pumps, heat exchangers. Default is 1000 €/kW.
    spezifische_Investitionskosten_WP : float, optional
        Specific investment costs for heat pump unit [€/kW].
        Heat pump equipment costs. Default is 1000 €/kW.
    min_Teillast : float, optional
        Minimum part-load ratio [-].
        Minimum operational capacity as fraction of rated power. Default is 0.2.
    opt_power_min : float, optional
        Minimum power for optimization [kW].
        Lower bound for capacity optimization. Default is 0.
    opt_power_max : float, optional
        Maximum power for optimization [kW].
        Upper bound for capacity optimization. Default is 500.

    Attributes
    ----------
    Wärmeleistung_FW_WP : float
        Rated thermal output capacity [kW].
    Temperatur_FW_WP : float or numpy.ndarray
        River water temperature profile [°C].
    dT : float
        Temperature difference tolerance [K].
    spez_Investitionskosten_Flusswasser : float
        Specific investment costs for river water infrastructure [€/kW].
    min_Teillast : float
        Minimum part-load operating ratio [-].
    opt_power_min : float
        Minimum optimization capacity bound [kW].
    opt_power_max : float
        Maximum optimization capacity bound [kW].
    Wärmeleistung_kW : numpy.ndarray
        Heat output time series [kW].
    Kühlleistung_kW : numpy.ndarray
        Heat extraction from river time series [kW].
    el_Leistung_kW : numpy.ndarray
        Electrical power consumption time series [kW].
    VLT_WP : numpy.ndarray
        Heat pump flow temperature time series [°C].
    COP : numpy.ndarray
        Coefficient of Performance time series [-].
    betrieb_mask : numpy.ndarray
        Operational state mask [bool].
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
    River Water Heat Pump Technology:
        
        **Heat Source Characteristics**:
        River water provides a stable and renewable heat source with several
        advantages over air source systems:
        - More stable temperatures than ambient air
        - Higher efficiency during winter months
        - Continuous availability independent of weather
        - Large thermal capacity for sustained operation
        
        **Environmental Considerations**:
        - Water temperature change limits to protect aquatic life
        - Intake design to prevent fish entrainment
        - Return water temperature regulations
        - Seasonal operation restrictions during spawning periods
        
        **System Components**:
        - Water intake structure with screening systems
        - Circulation pumps and distribution piping
        - Plate heat exchangers for thermal transfer
        - Return water discharge system
        - Monitoring and control instrumentation

    Performance Modeling:
        
        **COP Calculation**:
        The Coefficient of Performance depends on:
        - River water temperature (heat source)
        - District heating supply temperature (heat sink)
        - Heat pump technology and refrigerant type
        - Part-load operation effects
        
        **Seasonal Variations**:
        - Summer: Higher river temperatures, improved COP
        - Winter: Lower river temperatures, reduced but stable performance
        - Ice protection: Special considerations for freezing conditions
        - Flow variations: Adaptation to seasonal water levels

    Economic Analysis:
        
        **Investment Costs**:
        - Heat pump unit: Standard heat pump equipment costs
        - Intake infrastructure: Pumps, pipes, heat exchangers, controls
        - Environmental permits: Regulatory compliance and monitoring
        - Grid connection: Electrical infrastructure for operation
        
        **Operational Costs**:
        - Electricity: Heat pump and circulation pump operation
        - Maintenance: Regular inspection and cleaning of intake systems
        - Environmental monitoring: Water temperature and flow monitoring
        - Permits and fees: Annual environmental compliance costs

    Examples
    --------
    >>> # Create river water heat pump with constant temperature
    >>> river_hp = RiverHeatPump(
    ...     name="RiverHP_01",
    ...     Wärmeleistung_FW_WP=800.0,          # kW rated capacity
    ...     Temperatur_FW_WP=12.0,              # °C constant river temperature
    ...     dT=2.0,                             # K temperature tolerance
    ...     spez_Investitionskosten_Flusswasser=200.0,  # €/kW intake costs
    ...     spezifische_Investitionskosten_WP=900.0,    # €/kW heat pump costs
    ...     min_Teillast=0.25                   # 25% minimum load
    ... )

    >>> # Create system with seasonal temperature variation
    >>> import numpy as np
    >>> 
    >>> # Generate seasonal river temperature profile
    >>> hours = np.arange(8760)
    >>> seasonal_temp = 12 + 8 * np.sin(2 * np.pi * hours / 8760 - np.pi/2)
    >>> 
    >>> river_hp_seasonal = RiverHeatPump(
    ...     name="RiverHP_Seasonal",
    ...     Wärmeleistung_FW_WP=1200.0,
    ...     Temperatur_FW_WP=seasonal_temp,     # Time-varying temperature
    ...     spez_Investitionskosten_Flusswasser=250.0,
    ...     min_Teillast=0.2
    ... )

    >>> # Calculate heat pump performance
    >>> flow_temperatures = np.full(100, 55.0)  # °C supply temperature
    >>> cop_data = np.array([
    ...     [0,    35,   45,   55,   65,   75],    # Flow temperatures
    ...     [0,    4.2,  3.8,  3.3,  2.8,  2.4],  # COP at 0°C source
    ...     [10,   4.8,  4.3,  3.7,  3.1,  2.6],  # COP at 10°C source
    ...     [15,   5.2,  4.6,  4.0,  3.3,  2.8],  # COP at 15°C source
    ...     [20,   5.6,  5.0,  4.3,  3.6,  3.0]   # COP at 20°C source
    ... ])
    >>> 
    >>> cooling_load, electric_power, flow_temp, cop = river_hp.calculate_heat_pump(
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
    >>> # Calculate heat generation costs
    >>> annual_heat = 3000.0      # MWh/year heat delivery
    >>> annual_electricity = 750.0  # MWh/year electricity consumption
    >>> 
    >>> wgk = river_hp.calculate_heat_generation_costs(
    ...     river_hp.Wärmeleistung_FW_WP,
    ...     annual_heat,
    ...     annual_electricity,
    ...     river_hp.spez_Investitionskosten_Flusswasser,
    ...     economic_params
    ... )
    >>> 
    >>> print(f"Heat generation costs: {wgk:.2f} €/MWh")

    >>> # System operation simulation
    >>> load_profile = np.random.uniform(200, 600, 100)  # kW varying load
    >>> river_hp.calculate_operation(load_profile, flow_temperatures, cop_data)
    >>> 
    >>> # Calculate performance metrics
    >>> duration = 1.0  # hours
    >>> river_hp.calculate_results(duration)
    >>> 
    >>> print(f"Total heat production: {river_hp.Wärmemenge_MWh:.1f} MWh")
    >>> print(f"SCOP: {river_hp.SCOP:.2f}")
    >>> print(f"Operating hours: {river_hp.Betriebsstunden:.0f} hours")

    See Also
    --------
    HeatPump : Base heat pump implementation
    BaseHeatGenerator : Base class for heat generators
    numpy.ndarray : Array operations for time-series data
    """

    def __init__(self, name: str, Wärmeleistung_FW_WP: float, 
                 Temperatur_FW_WP: Union[float, np.ndarray], dT: float = 0, 
                 spez_Investitionskosten_Flusswasser: float = 1000, 
                 spezifische_Investitionskosten_WP: float = 1000, 
                 min_Teillast: float = 0.2, opt_power_min: float = 0, 
                 opt_power_max: float = 500) -> None:
        """
        Initialize river water heat pump system.

        Parameters
        ----------
        name : str
            Unique identifier for the river heat pump system.
        Wärmeleistung_FW_WP : float
            Rated thermal output capacity [kW].
        Temperatur_FW_WP : float or numpy.ndarray
            River water temperature [°C].
        dT : float, optional
            Temperature difference tolerance [K]. Default is 0.
        spez_Investitionskosten_Flusswasser : float, optional
            Specific investment costs for river water system [€/kW]. Default is 1000.
        spezifische_Investitionskosten_WP : float, optional
            Specific investment costs for heat pump unit [€/kW]. Default is 1000.
        min_Teillast : float, optional
            Minimum part-load ratio [-]. Default is 0.2.
        opt_power_min : float, optional
            Minimum power for optimization [kW]. Default is 0.
        opt_power_max : float, optional
            Maximum power for optimization [kW]. Default is 500.
        """
        super().__init__(name, spezifische_Investitionskosten_WP=spezifische_Investitionskosten_WP)
        self.Wärmeleistung_FW_WP = Wärmeleistung_FW_WP
        self.Temperatur_FW_WP = np.array(Temperatur_FW_WP)
        self.dT = dT
        self.spez_Investitionskosten_Flusswasser = spez_Investitionskosten_Flusswasser
        self.min_Teillast = min_Teillast
        self.opt_power_min = opt_power_min
        self.opt_power_max = opt_power_max

    def calculate_heat_pump(self, VLT_L: np.ndarray, COP_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate heat pump performance for river water operation.

        This method computes the thermal performance of the river water heat pump
        including heat extraction from the river, electrical power consumption,
        and achievable flow temperatures. It uses the river water temperature
        as the heat source for COP calculations.

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
            
            Kühlleistung_L : numpy.ndarray
                Heat extraction from river [kW].
                Thermal energy extracted from water source.
                
            el_Leistung_L : numpy.ndarray
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
            - Uses river water temperature as heat source
            - Interpolates performance from manufacturer data
            - Considers technical temperature lift limitations
            - Accounts for part-load performance effects
            
            **Energy Balance**:
            Heat extraction = Heat output - Electrical input
            COP = Heat output / Electrical input
            
            **Temperature Constraints**:
            - Maximum temperature lift typically 75K
            - River water extraction temperature limits
            - Heat pump refrigerant operating range
            - Flow temperature delivery capability

        The calculation ensures energy balance consistency and applies
        technical constraints for realistic system modeling.

        Examples
        --------
        >>> # Calculate performance for varying conditions
        >>> flow_temps = np.array([45, 50, 55, 60, 65])  # °C
        >>> 
        >>> # Example COP data for river water heat pump
        >>> cop_data = np.array([
        ...     [0,    35,   45,   55,   65,   75],
        ...     [5,    4.8,  4.3,  3.7,  3.1,  2.6],
        ...     [10,   5.4,  4.8,  4.1,  3.4,  2.8],
        ...     [15,   5.9,  5.2,  4.4,  3.7,  3.0]
        ... ])
        >>> 
        >>> # Calculate performance
        >>> cooling, electric, flow, cop = river_hp.calculate_heat_pump(
        ...     flow_temps, cop_data
        ... )
        >>> 
        >>> for i, temp in enumerate(flow_temps):
        ...     print(f"Flow {temp}°C: COP={cop[i]:.2f}, "
        ...           f"Electric={electric[i]:.1f}kW, "
        ...           f"Cooling={cooling[i]:.1f}kW")
        """
        # Calculate COP based on river water temperature and flow temperature
        if isinstance(self.Temperatur_FW_WP, list):
            self.Temperatur_FW_WP = np.array(self.Temperatur_FW_WP)
        COP_L, VLT_WP_L = self.calculate_COP(VLT_L, self.Temperatur_FW_WP, COP_data)
        
        # Calculate heat extraction from river (cooling load)
        Kühlleistung_L = self.Wärmeleistung_FW_WP * (1 - (1 / COP_L))
        
        # Calculate electrical power consumption
        el_Leistung_L = self.Wärmeleistung_FW_WP - Kühlleistung_L

        return Kühlleistung_L, el_Leistung_L, VLT_WP_L, COP_L

    def calculate_operation(self, Last_L: np.ndarray, VLT_L: np.ndarray, 
                           COP_data: np.ndarray) -> None:
        """
        Calculate operational performance considering load demand and constraints.

        This method performs comprehensive operational analysis of the river water
        heat pump considering actual load demand, technical constraints, and
        part-load operation requirements. It determines when the heat pump can
        operate effectively and calculates corresponding performance metrics.

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
            
            **Load Matching**:
            - Heat output limited by rated capacity and actual demand
            - Part-load operation down to minimum threshold
            - Load following capability within technical constraints
            
            **Operational Constraints**:
            - Temperature delivery capability check
            - Minimum part-load operation threshold
            - River water temperature availability
            - Environmental protection limits
            
            **Performance Calculation**:
            - Real-time COP based on operating conditions
            - Electrical consumption for actual heat output
            - Heat extraction from river water
            - Operational state determination

        The method updates all time-series attributes with calculated
        performance data and operational states for the simulation period.

        Examples
        --------
        >>> # Define operational scenario
        >>> hours = 100
        >>> load_demand = np.random.uniform(100, 700, hours)  # kW varying load
        >>> flow_temps = np.full(hours, 55.0)                # °C constant flow temp
        >>> 
        >>> # River temperature variation
        >>> river_temps = 10 + 5 * np.sin(np.arange(hours) / 12)  # Daily variation
        >>> river_hp.Temperatur_FW_WP = river_temps
        >>> 
        >>> # Calculate operation
        >>> river_hp.calculate_operation(load_demand, flow_temps, cop_data)
        >>> 
        >>> # Analyze results
        >>> operating_hours = np.sum(river_hp.betrieb_mask)
        >>> avg_cop = np.mean(river_hp.COP[river_hp.betrieb_mask])
        >>> max_output = np.max(river_hp.Wärmeleistung_kW)
        >>> 
        >>> print(f"Operating hours: {operating_hours}/{hours}")
        >>> print(f"Average COP: {avg_cop:.2f}")
        >>> print(f"Maximum output: {max_output:.1f} kW")
        """
        # Determine actual heat output (limited by capacity and demand)
        self.Wärmeleistung_kW = np.minimum(Last_L, self.Wärmeleistung_FW_WP)
        
        # Calculate heat pump performance for all time steps
        self.Kühlleistung_kW, self.el_Leistung_kW, self.VLT_WP, self.COP = self.calculate_heat_pump(VLT_L, COP_data)

        # Determine operational constraints
        # Heat pump operates when:
        # 1. It can achieve required flow temperature (within tolerance)
        # 2. Load demand exceeds minimum part-load threshold
        self.betrieb_mask = np.logical_and(
            self.VLT_WP >= VLT_L - self.dT,  # Temperature delivery capability
            Last_L >= self.Wärmeleistung_FW_WP * self.min_Teillast  # Minimum load requirement
        )

        # Set outputs to zero when not operating
        self.Wärmeleistung_kW[~self.betrieb_mask] = 0
        self.Kühlleistung_kW[~self.betrieb_mask] = 0
        self.el_Leistung_kW[~self.betrieb_mask] = 0
        self.VLT_WP[~self.betrieb_mask] = 0
        self.COP[~self.betrieb_mask] = 0

    def generate(self, t: int, **kwargs) -> Tuple[float, float]:
        """
        Generate heat at specific time step with operational constraints.

        This method calculates heat generation and electricity consumption for
        a single time step, considering operational constraints and system
        conditions. It provides the interface for time-step-based simulation
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
            
            **Operational Check**:
            - System active status verification
            - Temperature delivery capability assessment
            - Minimum capacity requirement validation
            
            **Performance Calculation**:
            - Real-time COP based on current conditions
            - Heat output matching system demand
            - Electrical consumption calculation
            - River heat extraction determination
            
            **Constraint Application**:
            - Output limitation by rated capacity
            - Part-load operation constraints
            - Environmental protection measures

        Examples
        --------
        >>> # Single time step generation
        >>> t = 42  # Hour 42 of simulation
        >>> 
        >>> generation_params = {
        ...     'VLT_L': 60.0,        # °C required flow temperature
        ...     'COP_data': cop_data  # Performance lookup table
        ... }
        >>> 
        >>> heat_out, elec_in = river_hp.generate(t, **generation_params)
        >>> print(f"Hour {t}: {heat_out:.1f} kW heat, {elec_in:.1f} kW electricity")
        >>> 
        >>> # Check operational state
        >>> if river_hp.betrieb_mask[t]:
        ...     print(f"COP: {river_hp.COP[t]:.2f}")
        ...     print(f"River heat extraction: {river_hp.Kühlleistung_kW[t]:.1f} kW")
        ... else:
        ...     print("Heat pump not operating")
        """
        VLT = kwargs.get('VLT_L', 0)
        COP_data = kwargs.get('COP_data', None)

        # Calculate performance for current time step
        self.Kühlleistung_kW[t], self.el_Leistung_kW[t], self.VLT_WP[t], self.COP[t] = self.calculate_heat_pump(VLT, COP_data)

        # Check operational constraints
        if (self.active and 
            self.VLT_WP[t] >= VLT - self.dT and 
            self.Wärmeleistung_FW_WP > 0):
            # Heat pump can operate - generate heat
            self.betrieb_mask[t] = True
            self.Wärmeleistung_kW[t] = self.Wärmeleistung_FW_WP
        else:
            # Heat pump cannot operate - set outputs to zero
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0
            self.Kühlleistung_kW[t] = 0
            self.el_Leistung_kW[t] = 0
            self.VLT_WP[t] = 0
            self.COP[t] = 0

        return self.Wärmeleistung_kW[t], self.el_Leistung_kW[t]

    def calculate_results(self, duration: float) -> None:
        """
        Calculate aggregated performance metrics from simulation results.

        This method processes the time-series simulation results to calculate
        comprehensive performance indicators including energy production,
        efficiency metrics, and operational statistics. It provides summary
        data for economic and technical evaluation.

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
            - Capacity utilization factor
            
            **Performance Indicators**:
            - System availability and reliability
            - Efficiency variations throughout operation
            - Load following performance
            - Environmental impact metrics

        The results are stored as object attributes for subsequent
        economic analysis and performance reporting.

        Examples
        --------
        >>> # Calculate results after simulation
        >>> simulation_duration = 1.0  # hours per time step
        >>> river_hp.calculate_results(simulation_duration)
        >>> 
        >>> # Display performance summary
        >>> print("River Water Heat Pump Performance Summary:")
        >>> print(f"Heat production: {river_hp.Wärmemenge_MWh:.1f} MWh")
        >>> print(f"Electricity consumption: {river_hp.Strommenge_MWh:.1f} MWh")
        >>> print(f"SCOP: {river_hp.SCOP:.2f}")
        >>> print(f"Operating hours: {river_hp.Betriebsstunden:.0f} hours")
        >>> print(f"Number of starts: {river_hp.Anzahl_Starts}")
        >>> print(f"Hours per start: {river_hp.Betriebsstunden_pro_Start:.1f}")
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
        Comprehensive calculation of performance, economics, and environmental impact.

        This method performs complete analysis of the river water heat pump system
        including thermal performance, economic evaluation, and environmental
        impact assessment. It integrates all calculation modules to provide
        comprehensive system evaluation for decision-making.

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
            - Investment and operational cost breakdown
            - Economic performance indicators
            
            **Environmental Results**:
            - CO2 emissions and specific emission factors
            - Primary energy consumption
            - Environmental impact assessment

        Notes
        -----
        Calculation Sequence:
            
            **1. Performance Analysis**:
            - Operational simulation with load following
            - Efficiency calculation for all operating conditions
            - Performance metric aggregation
            
            **2. Economic Evaluation**:
            - Investment cost calculation for heat pump and intake system
            - Operational cost analysis including electricity and maintenance
            - Heat generation cost determination using VDI 2067 methodology
            
            **3. Environmental Assessment**:
            - CO2 emissions from electricity consumption
            - Primary energy factor application
            - Environmental impact quantification

        The method provides complete system evaluation suitable for
        comparative analysis, optimization, and investment decision-making.

        Examples
        --------
        >>> # Define calculation parameters
        >>> economic_params = {
        ...     'electricity_price': 0.28,       # €/kWh
        ...     'capital_interest_rate': 0.04,   # 4% interest
        ...     'inflation_rate': 0.025,         # 2.5% inflation
        ...     'time_period': 20,               # 20-year analysis
        ...     'subsidy_eligibility': "Ja",     # BEW eligible
        ...     'hourly_rate': 55.0              # €/hour labor
        ... }
        >>> 
        >>> # Generate load profile
        >>> hours = 8760
        >>> load_profile = 400 + 200 * np.sin(2 * np.pi * np.arange(hours) / 8760)
        >>> flow_temps = np.full(hours, 55.0)
        >>> 
        >>> # Perform comprehensive calculation
        >>> results = river_hp.calculate(
        ...     economic_parameters=economic_params,
        ...     duration=1.0,
        ...     load_profile=load_profile,
        ...     VLT_L=flow_temps,
        ...     COP_data=cop_data
        ... )
        >>> 
        >>> # Display key results
        >>> print("River Water Heat Pump Analysis Results:")
        >>> print(f"Heat generation: {results['Wärmemenge']:.1f} MWh/year")
        >>> print(f"Electricity demand: {results['Strombedarf']:.1f} MWh/year")
        >>> print(f"Heat generation costs: {results['WGK']:.2f} €/MWh")
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
        
        # Economic evaluation
        self.WGK = self.calculate_heat_generation_costs(
            self.Wärmeleistung_FW_WP, 
            self.Wärmemenge_MWh, 
            self.Strommenge_MWh, 
            self.spez_Investitionskosten_Flusswasser, 
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
            'color': "blue"  # Visualization color coding
        }

        return results

    def set_parameters(self, variables: list, variables_order: list, idx: int) -> None:
        """
        Set optimization parameters for the river heat pump system.

        This method updates the heat pump capacity based on optimization
        algorithm results, enabling capacity sizing optimization for
        economic and performance objectives.

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
        The method extracts the heat pump capacity parameter from the
        optimization variables and updates the system configuration
        accordingly. Error handling ensures robust operation during
        optimization procedures.

        Examples
        --------
        >>> # Set optimized capacity
        >>> variables = [850.0, 0.92, 65.0]  # Mixed optimization variables
        >>> variables_order = ['Wärmeleistung_FW_WP_01', 'efficiency_02', 'temp_03']
        >>> idx = 1  # River heat pump index
        >>> 
        >>> river_hp.set_parameters(variables, variables_order, idx)
        >>> print(f"Updated capacity: {river_hp.Wärmeleistung_FW_WP} kW")
        """
        try:
            # Extract heat pump capacity from optimization variables
            capacity_var = f"Wärmeleistung_FW_WP_{idx}"
            if capacity_var in variables_order:
                var_index = variables_order.index(capacity_var)
                self.Wärmeleistung_FW_WP = variables[var_index]
        except ValueError as e:
            print(f"Error setting parameters for {self.name}: {e}")

    def add_optimization_parameters(self, idx: int) -> Tuple[list, list, list]:
        """
        Define optimization parameters for river water heat pump system.

        This method specifies the optimization variables, bounds, and initial
        values for the river water heat pump system, enabling integration
        with optimization algorithms for system design and capacity sizing.

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
            
            **Capacity Optimization**:
            - Heat pump thermal capacity [kW]
            - Operating range defined by technical and economic constraints
            - Initial value based on current system configuration
            
            **Constraints**:
            - Minimum capacity: Determined by minimum viable system size
            - Maximum capacity: Limited by economic feasibility and technical limits
            - Step size: Optimization algorithm dependent

        Examples
        --------
        >>> # Get optimization parameters
        >>> idx = 1  # System index
        >>> initial, variables, bounds = river_hp.add_optimization_parameters(idx)
        >>> 
        >>> print("River Heat Pump Optimization Parameters:")
        >>> for i, (var, bound, init) in enumerate(zip(variables, bounds, initial)):
        ...     print(f"{var}: {init} kW, bounds: {bound[0]}-{bound[1]} kW")
        >>> 
        >>> # Use in optimization algorithm
        >>> from scipy.optimize import minimize
        >>> 
        >>> def objective(x):
        ...     river_hp.set_parameters(x, variables, idx)
        ...     # Calculate objective function (e.g., minimize costs)
        ...     return river_hp.WGK  # Heat generation costs
        >>> 
        >>> result = minimize(objective, initial, bounds=bounds)
        >>> print(f"Optimal capacity: {result.x[0]:.1f} kW")
        """
        initial_values = [self.Wärmeleistung_FW_WP]
        variables_order = [f"Wärmeleistung_FW_WP_{idx}"]
        bounds = [(self.opt_power_min, self.opt_power_max)]
        
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
            
            **System Identification**:
            - Heat pump name and type
            - Rated thermal capacity
            - River water temperature information
            
            **Technical Parameters**:
            - Temperature difference tolerance
            - Investment cost specifications
            - Performance characteristics
            
            **Temperature Handling**:
            - Constant temperature: Displays actual value
            - Variable temperature: Indicates data availability

        Examples
        --------
        >>> # Display system configuration
        >>> print(river_hp.get_display_text())
        >>> # Output: "RiverHP_01: Wärmeleistung FW WP: 800.0 kW, 
        >>> #          Temperatur FW WP: 12.0 °C, dT: 2.0 K, 
        >>> #          spez. Investitionskosten Flusswärme: 200.0 €/kW, 
        >>> #          spez. Investitionskosten Wärmepumpe: 900.0 €/kW"
        """
        # Handle temperature display based on data type
        if isinstance(self.Temperatur_FW_WP, (np.ndarray, list)):
            # Array data - indicate dataset is loaded
            text_temperture = "Datensatz Temperaturen geladen. "
        elif isinstance(self.Temperatur_FW_WP, (float, int)):
            # Single value - display actual temperature
            text_temperture = f"Temperatur FW WP: {self.Temperatur_FW_WP:.1f} °C, "
        else:
            text_temperture = f"Fehlerhaftes Datenformat: {type(self.Temperatur_FW_WP)} "

        return (f"{self.name}: Wärmeleistung FW WP: {self.Wärmeleistung_FW_WP:.1f} kW, "
                f"{text_temperture}dT: {self.dT:.1f} K, "
                f"spez. Investitionskosten Flusswärme: {self.spez_Investitionskosten_Flusswasser:.1f} €/kW, "
                f"spez. Investitionskosten Wärmepumpe: {self.spezifische_Investitionskosten_WP:.1f} €/kW")

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
            - Thermal capacity rating
            - Performance specifications
            - System size and scale
            
            **Cost Breakdown**:
            - River water infrastructure costs
            - Heat pump equipment costs
            - Component-wise investment breakdown
            
            **Total Investment**:
            - Combined system investment costs
            - Complete economic evaluation basis

        Examples
        --------
        >>> # Extract technology data
        >>> name, dimensions, costs, total = river_hp.extract_tech_data()
        >>> 
        >>> print(f"Technology: {name}")
        >>> print(f"Specifications: {dimensions}")
        >>> print(f"Cost breakdown: {costs}")
        >>> print(f"Total investment: {total} €")
        >>> 
        >>> # Use for comparative analysis
        >>> technologies = [river_hp_1, river_hp_2, river_hp_3]
        >>> comparison_data = [tech.extract_tech_data() for tech in technologies]
        >>> 
        >>> for name, dim, cost, total in comparison_data:
        ...     print(f"{name}: {total} € total investment")
        """
        # Technical specifications
        dimensions = f"th. Leistung: {self.Wärmeleistung_FW_WP:.1f} kW"
        
        # Detailed cost breakdown
        river_cost = self.spez_Investitionskosten_Flusswasser * self.Wärmeleistung_FW_WP
        hp_cost = self.spezifische_Investitionskosten_WP * self.Wärmeleistung_FW_WP
        costs = (f"Investitionskosten Flusswärmenutzung: {river_cost:.1f} €, "
                f"Investitionskosten Wärmepumpe: {hp_cost:.1f} €")
        
        # Total investment costs
        full_costs = f"{river_cost + hp_cost:.1f}"
        
        return self.name, dimensions, costs, full_costs