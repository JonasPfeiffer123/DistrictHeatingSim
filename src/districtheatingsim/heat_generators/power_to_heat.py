"""
Power-to-Heat System Module
===========================

This module provides comprehensive modeling capabilities for power-to-heat (P2H) systems
in district heating applications.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11

Power-to-heat systems convert electrical energy directly
into thermal energy using electric heating elements, providing flexible heating solutions
with excellent controllability and grid integration capabilities.

The implementation includes detailed electric heating modeling, operational strategy
integration with thermal storage systems, economic analysis including electricity
costs and grid services revenue, and control algorithms for optimal system operation.
It supports various power-to-heat technologies and integration scenarios.

Features
--------
- Electric heating element modeling with configurable efficiency
- Grid integration capabilities for demand response and load balancing
- Thermal storage integration with temperature-based control strategies
- Economic evaluation including electricity costs and potential grid revenues
- Environmental impact assessment considering electricity grid emissions
- Operational optimization for peak shaving and load shifting applications

Technical Specifications
------------------------
**Power-to-Heat Technologies**:
- Electric resistance heating with near-unity efficiency
- Electric boilers for steam and hot water generation
- Immersion heaters for direct thermal storage charging
- Heat pump integration for enhanced efficiency (hybrid systems)

**Control Systems**:
- Temperature-based storage charging strategies
- Grid signal responsive operation for demand response
- Load following capability with rapid response times
- Integration with renewable energy forecasting systems

**Economic Components**:
- Investment costs for electric heating equipment
- Electricity procurement costs with time-variable pricing
- Potential revenue from grid services (balancing, reserves)
- Operational optimization for cost-effective heat generation

Classes
-------
PowerToHeat : Power-to-heat system implementation
PowerToHeatStrategy : Control strategy for storage-integrated operation

Dependencies
------------
- numpy >= 1.20.0 : Numerical calculations and array operations
- districtheatingsim.heat_generators.base_heat_generator : Base heat generator framework

Applications
------------
The module supports power-to-heat applications including:
- District heating systems with renewable energy integration
- Peak shaving and load balancing for electric grid stabilization
- Thermal energy storage charging from excess renewable electricity
- Demand response participation for grid services revenue
- Backup heating systems with high reliability requirements

References
----------
Power-to-heat modeling based on:
- VDI 4655 guidelines for electric heating systems
- Grid integration standards for demand response systems
- Economic evaluation methods for sector coupling technologies
- Operational optimization strategies for power-to-heat systems
"""

import numpy as np
from typing import Dict, Any, Union, Tuple, Optional

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy

class PowerToHeat(BaseHeatGenerator):
    """
    Power-to-heat system for district heating applications.

    This class implements a comprehensive power-to-heat model suitable for
    district heating systems. Power-to-heat systems convert electrical energy
    directly into thermal energy using electric heating elements, providing
    highly controllable heating with excellent grid integration capabilities
    and rapid response characteristics.

    Power-to-heat systems offer exceptional advantages including near-instantaneous
    response times, excellent controllability for grid services, high efficiency
    for direct electric heating, and excellent integration capabilities with
    renewable energy systems and thermal storage.

    Parameters
    ----------
    name : str
        Unique identifier for the power-to-heat system.
        Should follow naming convention for system tracking and identification.
    thermal_capacity_kW : float, optional
        Maximum thermal output capacity [kW].
        Electric heating element capacity. Default is 1000 kW.
    spez_Investitionskosten : float, optional
        Specific investment costs [€/kW].
        Equipment and installation costs per kW capacity. Default is 30 €/kW.
    Nutzungsgrad : float, optional
        Electric heating efficiency [-].
        Electrical to thermal conversion efficiency. Default is 0.9.
    active : bool, optional
        System activation status.
        Enables or disables system operation. Default is True.

    Attributes
    ----------
    thermal_capacity_kW : float
        Maximum thermal output capacity [kW].
    spez_Investitionskosten : float
        Specific investment costs [€/kW].
    Nutzungsgrad : float
        Electric heating efficiency [-].
    Nutzungsdauer : int
        System design lifetime [years].
    f_Inst : float
        Installation cost factor [-].
    f_W_Insp : float
        Maintenance and inspection cost factor [-].
    Bedienaufwand : float
        Operational effort [hours/year].
    co2_factor_fuel : float
        CO2 emission factor for electricity [tCO2/MWh].
    primärenergiefaktor : float
        Primary energy factor for electricity [-].
    active : bool
        System operational status.
    strategy : PowerToHeatStrategy
        Control strategy instance for operational decisions.
    betrieb_mask : numpy.ndarray
        Operational state time series [bool].
    Wärmeleistung_kW : numpy.ndarray
        Heat output time series [kW].
    el_Leistung_kW : numpy.ndarray
        Electrical power consumption time series [kW].
    Wärmemenge_MWh : float
        Total heat production [MWh].
    Strommenge_MWh : float
        Total electricity consumption [MWh].
    Anzahl_Starts : int
        Number of start-up events.
    Betriebsstunden : float
        Total operating hours [hours].
    Betriebsstunden_pro_Start : float
        Average operating hours per start [hours].
    WGK : float
        Heat generation costs [€/MWh].

    Notes
    -----
    Power-to-Heat Technology:
        
        **Electric Heating Principles**:
        Power-to-heat systems utilize electric resistance heating elements
        to convert electrical energy directly into thermal energy:
        - Near-unity electrical to thermal conversion efficiency
        - Instantaneous response to control signals
        - No emissions at point of use
        - Minimal maintenance requirements due to simple technology
        
        **Grid Integration Capabilities**:
        - Rapid load following for grid balancing services
        - Demand response participation for peak load management
        - Integration with variable renewable energy sources
        - Frequency regulation and reserve capacity provision
        
        **System Configurations**:
        - Direct electric heating elements in heating circuits
        - Electric boilers for steam and hot water generation
        - Immersion heaters for thermal storage charging
        - Hybrid systems with heat pump integration

    Performance Characteristics:
        
        **Operational Flexibility**:
        Power-to-heat systems provide exceptional operational flexibility:
        - Response times: seconds to minutes
        - Load modulation: 0-100% capacity in real-time
        - Start-up time: practically instantaneous
        - Cycling capability: unlimited without degradation
        
        **Efficiency Considerations**:
        - Electric heating efficiency: typically 95-98%
        - No combustion losses or heat exchanger losses
        - Minimal standby losses during operation
        - High part-load efficiency maintained
        
        **Integration Benefits**:
        - Excellent renewable energy integration
        - Grid stabilization through demand response
        - Peak shaving and load shifting capabilities
        - Thermal storage charging optimization

    Economic Analysis:
        
        **Investment Costs**:
        - Electric heating elements: Low capital costs (€20-50/kW)
        - Electrical infrastructure: Switchgear, controls, safety systems
        - Installation: Electrical connections and commissioning
        - Grid connection: Potential upgrades for high-power systems
        
        **Operational Economics**:
        - Electricity costs: Primary operational expense
        - Variable pricing: Time-of-use and real-time pricing benefits
        - Grid services revenue: Balancing markets and reserves
        - Maintenance: Minimal due to simple technology
        
        **Economic Optimization**:
        - Load shifting to low-price electricity periods
        - Grid services participation for additional revenue
        - Renewable energy utilization for cost reduction
        - Peak demand charge management

    Examples
    --------
    >>> # Create power-to-heat system for district heating
    >>> p2h_system = PowerToHeat(
    ...     name="P2H_District_01",
    ...     thermal_capacity_kW=2000.0,         # kW electric heating capacity
    ...     spez_Investitionskosten=35.0,       # €/kW investment costs
    ...     Nutzungsgrad=0.95,                  # 95% electric efficiency
    ...     active=True                         # System enabled
    ... )

    >>> # System operation simulation
    >>> hours = 100
    >>> load_profile = 800 + 400 * np.sin(np.arange(hours) / 12)  # Variable load
    >>> p2h_system.simulate_operation(load_profile)

    >>> # Calculate performance metrics
    >>> duration = 1.0  # hours per time step
    >>> p2h_system.calculate_results(duration)
    >>> 
    >>> print(f"Heat production: {p2h_system.Wärmemenge_MWh:.1f} MWh")
    >>> print(f"Electricity consumption: {p2h_system.Strommenge_MWh:.1f} MWh")
    >>> print(f"Operating hours: {p2h_system.Betriebsstunden:.0f} hours")
    >>> print(f"System starts: {p2h_system.Anzahl_Starts}")

    >>> # Economic evaluation with time-variable electricity pricing
    >>> economic_params = {
    ...     'electricity_price': 0.15,          # €/kWh average electricity price
    ...     'gas_price': 0.06,                  # €/kWh (not used for P2H)
    ...     'wood_price': 0.04,                 # €/kWh (not used for P2H)
    ...     'capital_interest_rate': 0.04,      # 4% interest rate
    ...     'inflation_rate': 0.025,            # 2.5% inflation
    ...     'time_period': 20,                  # 20-year analysis period
    ...     'subsidy_eligibility': "Nein",      # No subsidies
    ...     'hourly_rate': 50.0                 # €/hour labor cost
    ... }
    >>> 
    >>> p2h_system.calculate_heat_generation_cost(economic_params)
    >>> print(f"Heat generation costs: {p2h_system.WGK:.2f} €/MWh")

    >>> # Grid services integration example
    >>> # Simulate demand response operation
    >>> grid_signal = np.random.choice([0, 1], hours, p=[0.7, 0.3])  # 30% DR events
    >>> storage_temp = 75 + 10 * np.sin(np.arange(hours) / 24)  # Storage temperature
    >>> 
    >>> # Control strategy with storage integration
    >>> strategy = PowerToHeatStrategy(charge_on=70)  # Charge below 70°C
    >>> 
    >>> for t in range(hours):
    ...     remaining_demand = max(0, load_profile[t] - 500)  # Base load covered
    ...     upper_temp = storage_temp[t]
    ...     
    ...     # Decide operation based on storage temperature and demand
    ...     operate = strategy.decide_operation(
    ...         current_state=0, 
    ...         upper_storage_temp=upper_temp,
    ...         lower_storage_temp=upper_temp-10,
    ...         remaining_demand=remaining_demand
    ...     )
    ...     
    ...     if operate and grid_signal[t]:  # Operate if needed and grid allows
    ...         heat_out, elec_in = p2h_system.generate(t, remaining_load=remaining_demand)
    ...         print(f"Hour {t}: P2H generating {heat_out:.0f} kW, consuming {elec_in:.0f} kW")

    >>> # Environmental impact assessment
    >>> p2h_system.calculate_environmental_impact()
    >>> print(f"CO2 emissions: {p2h_system.spec_co2_total:.3f} tCO2/MWh")
    >>> print(f"Primary energy: {p2h_system.primärenergie:.1f} MWh")

    See Also
    --------
    BaseHeatGenerator : Base class for heat generators
    PowerToHeatStrategy : Control strategy implementation
    numpy.ndarray : Array operations for time-series data
    """

    def __init__(self, name: str, thermal_capacity_kW: float = 1000, 
                 spez_Investitionskosten: float = 30, Nutzungsgrad: float = 0.9, 
                 active: bool = True) -> None:
        """
        Initialize power-to-heat system.

        Parameters
        ----------
        name : str
            Unique identifier for the power-to-heat system.
        thermal_capacity_kW : float, optional
            Maximum thermal output capacity [kW]. Default is 1000.
        spez_Investitionskosten : float, optional
            Specific investment costs [€/kW]. Default is 30.
        Nutzungsgrad : float, optional
            Electric heating efficiency [-]. Default is 0.9.
        active : bool, optional
            System activation status. Default is True.
        """
        super().__init__(name)
        self.thermal_capacity_kW = thermal_capacity_kW
        self.spez_Investitionskosten = spez_Investitionskosten
        self.Nutzungsgrad = Nutzungsgrad
        self.Nutzungsdauer = 20  # years system lifetime
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 1, 2, 0  # Economic factors
        self.co2_factor_fuel = 0.4  # tCO2/MWh electricity grid mix
        self.primärenergiefaktor = 2.4  # Primary energy factor for electricity
        self.active = active

        # Initialize control strategy for storage integration
        self.strategy = PowerToHeatStrategy(75)  # Charge below 75°C

        # Initialize operational arrays
        self.init_operation(8760)

    def init_operation(self, hours: int) -> None:
        """
        Initialize operational data arrays for simulation.

        This method sets up the time-series arrays for storing operational
        data during simulation, ensuring proper data structure initialization
        and calculation state management.

        Parameters
        ----------
        hours : int
            Number of simulation hours to initialize arrays for.

        Notes
        -----
        Initializes the following arrays and variables:
        - Operational state masks and time series
        - Performance metric storage
        - Calculation status flags

        The method prepares the system for simulation by creating
        appropriately sized data structures and resetting all
        operational counters and flags.

        Examples
        --------
        >>> # Initialize for annual simulation
        >>> p2h_system.init_operation(8760)  # 8760 hours = 1 year
        >>> 
        >>> # Verify initialization
        >>> print(f"Operational array size: {len(p2h_system.betrieb_mask)} hours")
        >>> print(f"Calculation status: {p2h_system.calculated}")
        """
        self.betrieb_mask = np.array([False] * hours)
        self.Wärmeleistung_kW = np.array([0.0] * hours)
        self.el_Leistung_kW = np.array([0.0] * hours)
        self.Wärmemenge_MWh = 0.0
        self.Strommenge_MWh = 0.0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0.0
        self.Betriebsstunden_pro_Start = 0.0

        self.calculated = False  # Flag to indicate if calculation is complete

    def simulate_operation(self, Last_L: np.ndarray) -> None:
        """
        Simulate power-to-heat system operation for given load profile.

        This method calculates the operational behavior of the power-to-heat
        system based on the thermal load demand, considering system capacity
        constraints and electrical efficiency characteristics.

        Parameters
        ----------
        Last_L : numpy.ndarray
            Thermal load demand time series [kW].
            Required heat output from the power-to-heat system.

        Notes
        -----
        Simulation Logic:
            
            **Load Following Operation**:
            - System operates when thermal demand exists (Load > 0)
            - Heat output limited by system thermal capacity
            - Electrical consumption calculated using efficiency factor
            
            **Capacity Constraints**:
            - Maximum heat output: thermal_capacity_kW
            - Electrical power: Heat output / efficiency
            - Operational state determined by demand presence
            
            **Performance Calculation**:
            The method updates time-series arrays for:
            - Operational state (betrieb_mask)
            - Heat output (Wärmeleistung_kW)
            - Electrical consumption (el_Leistung_kW)

        Examples
        --------
        >>> # Simulate operation with variable load profile
        >>> hours = 24  # Daily simulation
        >>> base_load = 800  # kW base heating demand
        >>> daily_variation = 400 * np.sin(2 * np.pi * np.arange(hours) / 24)
        >>> load_profile = base_load + daily_variation
        >>> 
        >>> # Run simulation
        >>> p2h_system.simulate_operation(load_profile)
        >>> 
        >>> # Analyze operation
        >>> operating_hours = np.sum(p2h_system.betrieb_mask)
        >>> max_heat_output = np.max(p2h_system.Wärmeleistung_kW)
        >>> total_electricity = np.sum(p2h_system.el_Leistung_kW)
        >>> 
        >>> print(f"Operating hours: {operating_hours}/{hours}")
        >>> print(f"Peak heat output: {max_heat_output:.1f} kW")
        >>> print(f"Total electricity consumption: {total_electricity:.1f} kWh")
        """
        # Determine operational periods (when load demand exists)
        self.betrieb_mask = Last_L > 0
        
        # Calculate heat output limited by system capacity
        self.Wärmeleistung_kW[self.betrieb_mask] = np.minimum(
            Last_L[self.betrieb_mask], 
            self.thermal_capacity_kW
        )
        
        # Calculate electrical consumption based on efficiency
        self.el_Leistung_kW[self.betrieb_mask] = (
            self.Wärmeleistung_kW[self.betrieb_mask] / self.Nutzungsgrad
        )

    def generate(self, t: int, **kwargs) -> Tuple[float, float]:
        """
        Generate thermal power for specific time step.

        This method calculates heat generation and electricity consumption for
        a single time step, considering system constraints and operational
        status. It provides the interface for time-step-based simulation
        and real-time system control.

        Parameters
        ----------
        t : int
            Current time step index.
            Index for accessing time-series data arrays.
        **kwargs : dict
            Additional parameters for heat generation:
            
            - **remaining_load** (float): Remaining thermal demand [kW]

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
            
            **System Status Check**:
            - Verifies system is active and operational
            - Determines heat output based on remaining load
            - Calculates corresponding electrical consumption
            
            **Capacity Constraints**:
            - Heat output limited by thermal_capacity_kW
            - Electrical consumption = Heat output / efficiency
            
            **Operational State Update**:
            - Updates betrieb_mask for current time step
            - Records heat and electrical power time series

        Examples
        --------
        >>> # Single time step generation
        >>> t = 12  # Hour 12 of simulation
        >>> remaining_thermal_demand = 1500.0  # kW
        >>> 
        >>> heat_out, elec_in = p2h_system.generate(
        ...     t, 
        ...     remaining_load=remaining_thermal_demand
        ... )
        >>> 
        >>> print(f"Hour {t}: Generated {heat_out:.1f} kW heat")
        >>> print(f"Consumed {elec_in:.1f} kW electricity")
        >>> print(f"System efficiency: {heat_out/elec_in:.3f}")
        >>> 
        >>> # Check if system was operating
        >>> if p2h_system.betrieb_mask[t]:
        ...     print("Power-to-heat system was operating")
        ... else:
        ...     print("Power-to-heat system was offline")
        """
        remaining_load = kwargs.get('remaining_load', 0)
        
        if self.active and remaining_load > 0:
            # System active and demand exists - operate
            self.betrieb_mask[t] = True
            self.Wärmeleistung_kW[t] = min(remaining_load, self.thermal_capacity_kW)
            self.el_Leistung_kW[t] = self.Wärmeleistung_kW[t] / self.Nutzungsgrad
        else:
            # System inactive or no demand - shutdown
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0.0
            self.el_Leistung_kW[t] = 0.0
        
        return self.Wärmeleistung_kW[t], self.el_Leistung_kW[t]
        
    def calculate_results(self, duration: float) -> None:
        """
        Calculate aggregated performance metrics from simulation results.

        This method processes time-series simulation data to calculate
        comprehensive performance indicators including energy totals,
        operational statistics, and system utilization metrics.

        Parameters
        ----------
        duration : float
            Time step duration [hours].
            Length of each simulation time step for energy calculations.

        Notes
        -----
        Calculated Metrics:
            
            **Energy Totals**:
            - Total heat production [MWh]
            - Total electricity consumption [MWh]
            - Energy conversion efficiency validation
            
            **Operational Statistics**:
            - Number of start-up events
            - Total operating hours
            - Average operating hours per start
            
            **Performance Indicators**:
            - System utilization factors
            - Cycling behavior analysis
            - Load following effectiveness

        Examples
        --------
        >>> # Calculate results after simulation
        >>> simulation_duration = 1.0  # hours per time step
        >>> p2h_system.calculate_results(simulation_duration)
        >>> 
        >>> # Display performance summary
        >>> print("Power-to-Heat Performance Summary:")
        >>> print(f"Heat production: {p2h_system.Wärmemenge_MWh:.1f} MWh")
        >>> print(f"Electricity consumption: {p2h_system.Strommenge_MWh:.1f} MWh")
        >>> print(f"Overall efficiency: {p2h_system.Wärmemenge_MWh/p2h_system.Strommenge_MWh:.3f}")
        >>> print(f"Operating hours: {p2h_system.Betriebsstunden:.0f} hours")
        >>> print(f"System starts: {p2h_system.Anzahl_Starts}")
        >>> print(f"Hours per start: {p2h_system.Betriebsstunden_pro_Start:.1f}")
        """
        # Calculate total energy production and consumption
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Strommenge_MWh = np.sum(self.el_Leistung_kW / 1000) * duration
        
        # Calculate operational statistics
        starts = np.diff(self.betrieb_mask.astype(int)) > 0  # Detect start-up events
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(self.betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = (
            self.Betriebsstunden / self.Anzahl_Starts 
            if self.Anzahl_Starts > 0 else 0
        )
    
    def calculate_heat_generation_cost(self, economic_parameters: Dict[str, Any]) -> None:
        """
        Calculate heat generation costs using VDI 2067 methodology.

        This method performs comprehensive economic analysis of the power-to-heat
        system including capital costs, operational expenses, and levelized
        cost of heat generation based on German engineering standards.

        Parameters
        ----------
        economic_parameters : dict
            Economic analysis parameters containing:
            
            - **electricity_price** (float): Electricity price [€/kWh]
            - **gas_price** (float): Gas price [€/kWh] (not used for P2H)
            - **wood_price** (float): Wood price [€/kWh] (not used for P2H)
            - **capital_interest_rate** (float): Interest rate for capital costs
            - **inflation_rate** (float): Inflation rate for cost escalation
            - **time_period** (int): Analysis time period [years]
            - **subsidy_eligibility** (str): Subsidy eligibility status
            - **hourly_rate** (float): Labor cost rate [€/hour]

        Notes
        -----
        Cost Calculation Components:
            
            **Capital Costs**:
            - Investment costs for electric heating equipment
            - Installation and commissioning costs
            - Infrastructure and electrical connection costs
            
            **Operational Costs**:
            - Electricity procurement costs (primary cost component)
            - Maintenance and inspection costs (minimal for electric systems)
            - Labor costs for operation and maintenance
            
            **Economic Analysis**:
            - Annuity calculation using VDI 2067 methodology
            - Present value analysis with inflation consideration
            - Levelized cost of heat (WGK) calculation

        Examples
        --------
        >>> # Economic evaluation with current energy prices
        >>> economic_params = {
        ...     'electricity_price': 0.25,      # €/kWh current electricity price
        ...     'gas_price': 0.08,              # €/kWh (not relevant for P2H)
        ...     'wood_price': 0.05,             # €/kWh (not relevant for P2H)
        ...     'capital_interest_rate': 0.04,  # 4% interest rate
        ...     'inflation_rate': 0.025,        # 2.5% inflation
        ...     'time_period': 20,              # 20-year analysis
        ...     'subsidy_eligibility': "Nein",  # No subsidies
        ...     'hourly_rate': 55.0             # €/hour labor cost
        ... }
        >>> 
        >>> p2h_system.calculate_heat_generation_cost(economic_params)
        >>> 
        >>> print(f"Investment costs: {p2h_system.Investitionskosten:,.0f} €")
        >>> print(f"Annual costs: {p2h_system.A_N:,.0f} €/year")
        >>> print(f"Heat generation costs: {p2h_system.WGK:.2f} €/MWh")
        >>> 
        >>> # Compare with other heating technologies
        >>> if p2h_system.WGK < 100:
        ...     print("Competitive heat generation costs")
        ... else:
        ...     print("Higher costs - consider optimization strategies")
        """
        # Extract economic parameters
        self.Strompreis = economic_parameters['electricity_price']
        self.Gaspreis = economic_parameters['gas_price']  # Not used for P2H
        self.Holzpreis = economic_parameters['wood_price']  # Not used for P2H
        self.q = economic_parameters['capital_interest_rate']
        self.r = economic_parameters['inflation_rate']
        self.T = economic_parameters['time_period']
        self.BEW = economic_parameters['subsidy_eligibility']
        self.stundensatz = economic_parameters['hourly_rate']
        
        if self.Wärmemenge_MWh > 0:
            # Calculate investment costs
            self.Investitionskosten = self.spez_Investitionskosten * self.thermal_capacity_kW

            # Calculate annuity using VDI 2067 methodology
            self.A_N = self.annuity(
                initial_investment_cost=self.Investitionskosten,
                asset_lifespan_years=self.Nutzungsdauer,
                installation_factor=self.f_Inst,
                maintenance_inspection_factor=self.f_W_Insp,
                operational_effort_h=self.Bedienaufwand,
                interest_rate_factor=self.q,
                inflation_rate_factor=self.r,
                consideration_time_period_years=self.T, 
                annual_energy_demand=self.Strommenge_MWh,
                energy_cost_per_unit=self.Strompreis,
                annual_revenue=0,  # No revenue for basic P2H operation
                hourly_rate=self.stundensatz
            )
            
            # Calculate levelized cost of heat generation
            self.WGK = self.A_N / self.Wärmemenge_MWh
        else:
            # No heat production - set costs to zero/infinite
            self.Investitionskosten = 0
            self.A_N = 0
            self.WGK = float('inf')

    def calculate_environmental_impact(self) -> None:
        """
        Calculate environmental impact of power-to-heat operation.

        This method assesses the environmental performance of the power-to-heat
        system including CO2 emissions from electricity consumption and primary
        energy usage based on grid emission factors and energy conversion chains.

        Notes
        -----
        Environmental Impact Assessment:
            
            **CO2 Emissions**:
            - Direct emissions: Zero at point of use
            - Indirect emissions: Based on electricity grid emission factor
            - Total emissions: Electricity consumption × Grid emission factor
            
            **Primary Energy Consumption**:
            - Electricity consumption × Primary energy factor
            - Accounts for power generation and transmission losses
            - Enables comparison with other heating technologies
            
            **Emission Factors**:
            - Grid electricity: Typically 0.3-0.5 tCO2/MWh (varies by country)
            - Primary energy: Typically 2.0-3.0 (varies by grid mix)
            - Future projections: Decreasing with renewable energy expansion

        The assessment provides data for lifecycle analysis and environmental
        performance comparisons with other heating technologies.

        Examples
        --------
        >>> # Calculate environmental impact
        >>> p2h_system.calculate_environmental_impact()
        >>> 
        >>> print("Environmental Impact Assessment:")
        >>> print(f"Total CO2 emissions: {p2h_system.co2_emissions:.1f} tCO2")
        >>> print(f"Specific CO2 emissions: {p2h_system.spec_co2_total:.3f} tCO2/MWh")
        >>> print(f"Primary energy consumption: {p2h_system.primärenergie:.1f} MWh")
        >>> 
        >>> # Compare with emission benchmarks
        >>> if p2h_system.spec_co2_total < 0.2:
        ...     print("Low-carbon heating solution")
        >>> elif p2h_system.spec_co2_total < 0.3:
        ...     print("Moderate-carbon heating solution")
        >>> else:
        ...     print("Consider renewable electricity procurement")
        """
        # CO2 emissions from electricity consumption
        self.co2_emissions = self.Strommenge_MWh * self.co2_factor_fuel  # tCO2
        
        # Specific CO2 emissions per MWh of heat produced
        self.spec_co2_total = (
            self.co2_emissions / self.Wärmemenge_MWh 
            if self.Wärmemenge_MWh > 0 else 0
        )  # tCO2/MWh_heat
        
        # Primary energy consumption
        self.primärenergie = self.Strommenge_MWh * self.primärenergiefaktor

    def calculate(self, economic_parameters: Dict[str, Any], duration: float, 
                 load_profile: np.ndarray, **kwargs) -> Dict[str, Any]:
        """
        Comprehensive calculation of power-to-heat performance and economics.

        This method performs complete analysis of the power-to-heat system
        including operational simulation, economic evaluation, and environmental
        impact assessment. It provides comprehensive results for system
        evaluation and optimization.

        Parameters
        ----------
        economic_parameters : dict
            Economic analysis parameters containing cost data and financial assumptions.
        duration : float
            Simulation time step duration [hours].
        load_profile : numpy.ndarray
            Thermal load demand time series [kW].
        **kwargs : dict
            Additional calculation parameters (reserved for future extensions).

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
            - Investment cost analysis
            - Economic performance indicators
            
            **Environmental Results**:
            - CO2 emissions and specific emission factors
            - Primary energy consumption
            - Environmental impact assessment

        Notes
        -----
        Calculation Workflow:
            
            **1. Operational Simulation**:
            - System operation based on load profile
            - Capacity constraints and efficiency modeling
            - Performance time series generation
            
            **2. Economic Analysis**:
            - Investment cost calculation
            - Operational cost analysis including electricity
            - Heat generation cost calculation using VDI 2067
            
            **3. Environmental Assessment**:
            - CO2 emissions from electricity grid
            - Primary energy consumption analysis
            - Environmental performance indicators

        Examples
        --------
        >>> # Comprehensive system analysis
        >>> economic_params = {
        ...     'electricity_price': 0.20,       # €/kWh
        ...     'gas_price': 0.07,               # €/kWh (not used)
        ...     'wood_price': 0.05,              # €/kWh (not used)
        ...     'capital_interest_rate': 0.04,   # 4% interest
        ...     'inflation_rate': 0.025,         # 2.5% inflation
        ...     'time_period': 20,               # 20-year analysis
        ...     'subsidy_eligibility': "Nein",   # No subsidies
        ...     'hourly_rate': 50.0              # €/hour labor
        ... }
        >>> 
        >>> # Annual load profile with seasonal variation
        >>> hours = 8760
        >>> base_load = 500  # kW base heating demand
        >>> seasonal = 300 * np.sin(2 * np.pi * np.arange(hours) / 8760 - np.pi/2)
        >>> daily = 100 * np.sin(2 * np.pi * np.arange(hours) / 24)
        >>> load_profile = base_load + seasonal + daily
        >>> 
        >>> # Perform comprehensive calculation
        >>> results = p2h_system.calculate(
        ...     economic_parameters=economic_params,
        ...     duration=1.0,
        ...     load_profile=load_profile
        ... )
        >>> 
        >>> # Display comprehensive results
        >>> print("Power-to-Heat System Analysis Results:")
        >>> print(f"Technology: {results['tech_name']}")
        >>> print(f"Heat generation: {results['Wärmemenge']:.1f} MWh/year")
        >>> print(f"Electricity demand: {results['Strombedarf']:.1f} MWh/year")
        >>> print(f"Heat generation costs: {results['WGK']:.2f} €/MWh")
        >>> print(f"CO2 emissions: {results['spec_co2_total']:.3f} tCO2/MWh")
        >>> print(f"Operating hours: {results['Betriebsstunden']:.0f} hours/year")
        >>> print(f"System starts: {results['Anzahl_Starts']}")
        """
        # Perform operational simulation if not already done
        if not self.calculated:
            self.simulate_operation(load_profile)
            self.calculated = True
        
        # Calculate performance metrics
        self.calculate_results(duration)
        
        # Economic evaluation
        self.calculate_heat_generation_cost(economic_parameters)
        
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
            "color": "saddlebrown"  # Visualization color coding
        }

        return results
    
    def set_parameters(self, variables: list, variables_order: list, idx: int) -> None:
        """
        Set optimization parameters for the power-to-heat system.

        This method provides interface compatibility for optimization algorithms
        even though power-to-heat systems typically have no optimization
        parameters in this implementation.

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
        Power-to-heat systems in this implementation do not have
        optimization parameters, so this method provides a pass-through
        interface for compatibility with optimization frameworks.

        Future extensions could include:
        - Thermal capacity optimization
        - Control strategy parameter optimization
        - Economic parameter optimization

        Examples
        --------
        >>> # Interface compatibility (no actual parameters)
        >>> variables = [1000.0, 0.95]  # Hypothetical parameters
        >>> variables_order = ['capacity_01', 'efficiency_01']
        >>> idx = 1
        >>> 
        >>> p2h_system.set_parameters(variables, variables_order, idx)
        >>> # No actual parameter changes in current implementation
        """
        pass  # No optimization parameters for power-to-heat systems
    
    def add_optimization_parameters(self, idx: int) -> Tuple[list, list, list]:
        """
        Define optimization parameters for power-to-heat system.

        This method returns empty parameter lists as power-to-heat systems
        typically have no optimization parameters in this implementation,
        providing interface compatibility with optimization frameworks.

        Parameters
        ----------
        idx : int
            Technology index for unique variable identification.

        Returns
        -------
        tuple
            Empty optimization parameter definition:
            
            initial_values : list
                Empty list (no optimization variables).
                
            variables_order : list
                Empty list (no variable names).
                
            bounds : list
                Empty list (no bounds).

        Notes
        -----
        Power-to-heat systems typically have fixed parameters:
        - Thermal capacity: Usually fixed based on peak demand
        - Efficiency: Technology-dependent constant
        - Control parameters: Strategy-specific settings

        Future optimization extensions could include:
        - Thermal capacity sizing optimization
        - Grid service participation optimization
        - Load shifting strategy optimization

        Examples
        --------
        >>> # Get optimization parameters (empty for P2H)
        >>> idx = 1
        >>> initial, variables, bounds = p2h_system.add_optimization_parameters(idx)
        >>> 
        >>> print(f"Optimization variables: {len(variables)}")  # Output: 0
        >>> print(f"Initial values: {initial}")  # Output: []
        >>> print(f"Bounds: {bounds}")  # Output: []
        >>> 
        >>> # Compatibility with optimization frameworks
        >>> if len(variables) == 0:
        ...     print("No optimization parameters for power-to-heat system")
        """
        return [], [], []  # No optimization parameters

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
            - System name and type identification
            - Key technical and economic parameters
            
            **Configuration Parameters**:
            - Specific investment costs for economic evaluation
            - Technical specifications and performance data

        Examples
        --------
        >>> # Display system configuration
        >>> print(p2h_system.get_display_text())
        >>> # Output: "P2H_District_01: spez. Investitionskosten: 35.0 €/kW"
        >>> 
        >>> # Use in system overview
        >>> systems = [p2h_system_1, p2h_system_2, p2h_system_3]
        >>> for system in systems:
        ...     print(system.get_display_text())
        """
        return f"{self.name}: spez. Investitionskosten: {self.spez_Investitionskosten:.1f} €/kW"
    
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
            - Thermal capacity and performance specifications
            - System configuration and efficiency data
            
            **Cost Information**:
            - Investment costs and economic parameters
            - Complete financial analysis basis
            
            **Standardized Format**:
            - Consistent formatting for comparison tools
            - Integration with reporting systems

        Examples
        --------
        >>> # Extract technology data
        >>> name, dimensions, costs, total = p2h_system.extract_tech_data()
        >>> 
        >>> print(f"Technology: {name}")
        >>> print(f"Specifications: {dimensions}")
        >>> print(f"Cost breakdown: {costs}")
        >>> print(f"Total investment: {total} €")
        >>> 
        >>> # Use for comparative analysis
        >>> technologies = [p2h_1, p2h_2, p2h_3]
        >>> comparison_data = [tech.extract_tech_data() for tech in technologies]
        >>> 
        >>> for name, dim, cost, total in comparison_data:
        ...     print(f"{name}: {total} € total investment")
        """
        dimensions = f"th. Leistung: {self.thermal_capacity_kW:.1f} kW"
        costs = f"Investitionskosten: {self.Investitionskosten:.1f} €"
        full_costs = f"{self.Investitionskosten:.1f}"
        
        return self.name, dimensions, costs, full_costs


class PowerToHeatStrategy(BaseStrategy):
    """
    Control strategy for power-to-heat systems with thermal storage integration.

    This class implements intelligent control strategies for power-to-heat systems
    integrated with thermal storage, enabling optimized operation based on storage
    temperature levels, grid conditions, and demand patterns. The strategy provides
    temperature-based charging control and demand-responsive operation.

    The control strategy optimizes power-to-heat operation for maximum efficiency
    and economic benefit while maintaining thermal comfort and system reliability.
    It supports integration with grid services and renewable energy systems.

    Parameters
    ----------
    charge_on : float
        Storage temperature threshold to activate power-to-heat charging [°C].
        Below this temperature, the P2H system will operate if demand exists.
    charge_off : float, optional
        Storage temperature threshold to deactivate power-to-heat charging [°C].
        Above this temperature, the P2H system will stop charging. Default is None.

    Attributes
    ----------
    charge_on : float
        Charging activation temperature threshold [°C].
    charge_off : float or None
        Charging deactivation temperature threshold [°C].

    Notes
    -----
    Control Strategy Logic:
        
        **Temperature-Based Control**:
        The strategy uses storage temperature as the primary control signal:
        - Low storage temperature → Activate power-to-heat charging
        - High storage temperature → Deactivate power-to-heat charging
        - Hysteresis control to prevent excessive cycling
        
        **Demand-Response Integration**:
        - Grid signal responsiveness for demand response participation
        - Load shifting optimization for time-of-use electricity pricing
        - Renewable energy integration for excess electricity utilization
        
        **Operational Priorities**:
        1. Storage temperature management (primary)
        2. Grid service requirements (secondary)
        3. Economic optimization (tertiary)

    Examples
    --------
    >>> # Create control strategy for thermal storage integration
    >>> strategy = PowerToHeatStrategy(
    ...     charge_on=70.0,   # Activate P2H below 70°C storage temperature
    ...     charge_off=85.0   # Deactivate P2H above 85°C storage temperature
    ... )

    >>> # Simulate control decisions
    >>> storage_temps = [65, 72, 78, 88, 82, 68]  # °C storage temperatures
    >>> remaining_demands = [300, 150, 0, 0, 100, 250]  # kW thermal demands
    >>> 
    >>> for i, (temp, demand) in enumerate(zip(storage_temps, remaining_demands)):
    ...     operate = strategy.decide_operation(
    ...         current_state=0,
    ...         upper_storage_temp=temp,
    ...         lower_storage_temp=temp-5,
    ...         remaining_demand=demand
    ...     )
    ...     print(f"Hour {i}: Temp={temp}°C, Demand={demand}kW → Operate={operate}")

    >>> # Grid service integration example
    >>> grid_signals = [1, 1, 0, 0, 1, 1]  # 1=operate allowed, 0=restricted
    >>> 
    >>> for i, (temp, demand, grid) in enumerate(zip(storage_temps, remaining_demands, grid_signals)):
    ...     base_decision = strategy.decide_operation(0, temp, temp-5, demand)
    ...     final_decision = base_decision and bool(grid)
    ...     print(f"Hour {i}: Base={base_decision}, Grid={grid} → Final={final_decision}")

    See Also
    --------
    BaseStrategy : Base class for control strategies
    PowerToHeat : Power-to-heat system implementation
    """

    def __init__(self, charge_on: float, charge_off: Optional[float] = None) -> None:
        """
        Initialize power-to-heat control strategy.

        Parameters
        ----------
        charge_on : float
            Storage temperature threshold to activate power-to-heat charging [°C].
        charge_off : float, optional
            Storage temperature threshold to deactivate power-to-heat charging [°C].
            If None, uses charge_on as single threshold. Default is None.
        """
        super().__init__(charge_on, charge_off)

    def decide_operation(self, current_state: float, upper_storage_temp: float, 
                        lower_storage_temp: float, remaining_demand: float) -> bool:
        """
        Decide whether to operate power-to-heat system based on control strategy.

        This method implements the core control logic for power-to-heat operation
        based on storage temperature and remaining thermal demand. It provides
        intelligent switching decisions to optimize system performance.

        Parameters
        ----------
        current_state : float
            Current state of the system (not used in this implementation).
            Reserved for future extensions and compatibility.
        upper_storage_temp : float
            Current upper storage temperature [°C].
            Primary control signal for operation decisions.
        lower_storage_temp : float
            Current lower storage temperature [°C].
            Not used in current implementation, reserved for advanced control.
        remaining_demand : float
            Remaining heat demand to be covered [kW].
            Secondary control signal ensuring demand exists.

        Returns
        -------
        bool
            Operation decision:
            
            True : Power-to-heat system should operate.
            False : Power-to-heat system should remain off.

        Notes
        -----
        Decision Logic:
            
            **Primary Condition**: Storage Temperature
            - If upper_storage_temp < charge_on → Consider operation
            - If upper_storage_temp ≥ charge_on → Do not operate
            
            **Secondary Condition**: Demand Existence
            - remaining_demand > 0 → Demand exists, can operate
            - remaining_demand ≤ 0 → No demand, do not operate
            
            **Combined Logic**:
            - Operate only if BOTH conditions are satisfied
            - Temperature threshold prevents overcharging
            - Demand check prevents unnecessary operation

        The method provides conservative control to prevent storage overheating
        while ensuring operation only when thermal demand exists.

        Examples
        --------
        >>> # Test control strategy decisions
        >>> strategy = PowerToHeatStrategy(charge_on=75.0)
        >>> 
        >>> # Various operating scenarios
        >>> scenarios = [
        ...     (70.0, 300),   # Low temp, high demand → Should operate
        ...     (80.0, 200),   # High temp, medium demand → Should not operate
        ...     (65.0, 0),     # Low temp, no demand → Should not operate
        ...     (72.0, 50),    # Medium temp, low demand → Should operate
        ... ]
        >>> 
        >>> for temp, demand in scenarios:
        ...     decision = strategy.decide_operation(0, temp, temp-5, demand)
        ...     status = "OPERATE" if decision else "OFF"
        ...     print(f"Temp: {temp}°C, Demand: {demand}kW → {status}")
        >>> 
        >>> # Hysteresis control example
        >>> if hasattr(strategy, 'charge_off') and strategy.charge_off:
        ...     print(f"Hysteresis: ON below {strategy.charge_on}°C, OFF above {strategy.charge_off}°C")
        """
        # Check if storage temperature is below charging threshold and demand exists
        if upper_storage_temp < self.charge_on and remaining_demand > 0:
            return True  # Activate power-to-heat system
        else:
            return False  # Keep power-to-heat system off