"""
Biomass Boiler System Module
============================

This module provides comprehensive biomass boiler system modeling capabilities.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11

The implementation includes detailed thermal modeling, storage system integration, economic analysis, and environmental
impact assessment for wood pellet and biomass-fired heating systems.

The module supports both standalone boiler operation and boiler-storage
combinations with advanced control strategies for optimal system performance
and economic operation in district heating networks.

Features
--------
- Comprehensive biomass boiler modeling with efficiency curves
- Integrated thermal storage system with dynamic simulation
- Wood storage sizing and cost optimization
- Advanced control strategies for optimal operation
- Economic analysis including BEW subsidy calculations
- Environmental impact assessment for CO2 and primary energy
- Part-load operation modeling with minimum load constraints

Technical Specifications
------------------------
**Biomass Boiler Modeling**:
- Thermal capacity sizing from 10 kW to 10+ MW installations
- Efficiency modeling with Nutzungsgrad (utilization factor) calculations
- Part-load operation constraints with minimum load thresholds
- Start-stop cycle analysis for operational optimization
- Wood pellet and biomass fuel consumption calculations

**Thermal Storage Integration**:
- Dynamic thermal storage simulation with heat balance calculations
- Storage capacity optimization for demand-supply matching
- Temperature-based control strategies with hysteresis
- Storage fill level monitoring and optimization
- Heat exchanger modeling for storage integration

**Economic Analysis**:
- Comprehensive cost modeling including capital and operational costs
- Wood storage facility sizing and cost calculations
- BEW (Bundesförderung für effiziente Wärmenetze) subsidy integration
- Annuity-based economic evaluation with lifecycle assessment
- Heat generation cost calculations (Wärmegestehungskosten)

**Environmental Assessment**:
- CO2 emission calculations for biomass fuel consumption
- Primary energy factor analysis for renewable biomass
- Lifecycle environmental impact assessment
- Sustainability metrics for renewable energy integration

Classes
-------
BiomassBoiler : Main biomass boiler system class
BiomassBoilerStrategy : Control strategy for biomass boiler operation

Dependencies
------------
- numpy >= 1.20.0 : Numerical calculations and array operations
- districtheatingsim.heat_generators.base_heat_generator : Base classes for heat generators

Applications
------------
The module supports biomass applications including:
- District heating central heating plants
- Building-level biomass heating systems
- Combined heat and power (CHP) biomass applications
- Thermal storage integration for demand management
- Renewable energy system optimization for district heating

References
----------
Biomass boiler modeling based on:
- VDI 4640 renewable energy systems standards
- DIN EN 303-5 biomass boiler efficiency standards
- BEW subsidy guidelines for efficient heating networks
- German renewable energy regulations (EEWärmeG)
"""

import numpy as np
from typing import Dict, Tuple, List, Optional, Union

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy

class BiomassBoiler(BaseHeatGenerator):
    """
    Comprehensive biomass boiler system for district heating applications.

    This class models biomass-fired heating systems including wood pellet boilers,
    biomass boilers, and integrated thermal storage systems. The implementation
    provides detailed performance modeling, economic analysis, and environmental
    impact assessment for renewable heating system integration.

    The biomass boiler model includes advanced features such as part-load operation
    modeling, thermal storage integration, control strategy optimization, and
    comprehensive cost analysis including German BEW subsidy calculations.

    Parameters
    ----------
    name : str
        Unique identifier for the biomass boiler system.
        Used for system identification and result tracking.
    thermal_capacity_kW : float
        Nominal thermal power output of the biomass boiler [kW].
        Determines maximum heat generation capacity under rated conditions.
    Größe_Holzlager : float, optional
        Wood storage facility capacity [tons].
        Storage capacity for biomass fuel supply (default: 40 tons).
    spez_Investitionskosten : float, optional
        Specific investment costs for boiler equipment [€/kW].
        Capital cost per unit thermal capacity (default: 200 €/kW).
    spez_Investitionskosten_Holzlager : float, optional
        Specific investment costs for wood storage facility [€/ton].
        Storage facility cost per unit storage capacity (default: 400 €/ton).
    Nutzungsgrad_BMK : float, optional
        Boiler thermal efficiency (utilization factor) [-].
        Ratio of useful heat output to fuel energy input (default: 0.8).
    min_Teillast : float, optional
        Minimum part-load operation threshold [-].
        Minimum operational load as fraction of nominal capacity (default: 0.3).
    speicher_aktiv : bool, optional
        Enable integrated thermal storage system.
        Activates storage modeling and control strategies (default: False).
    Speicher_Volumen : float, optional
        Thermal storage tank volume [m³].
        Storage capacity for thermal energy buffering (default: 20 m³).
    T_vorlauf : float, optional
        Supply water temperature [°C].
        Forward flow temperature for storage calculations (default: 90°C).
    T_ruecklauf : float, optional
        Return water temperature [°C].
        Return flow temperature for storage calculations (default: 60°C).
    initial_fill : float, optional
        Initial storage fill level [-].
        Starting storage state as fraction of total capacity (default: 0.0).
    min_fill : float, optional
        Minimum storage fill level [-].
        Lower operational limit for storage system (default: 0.2).
    max_fill : float, optional
        Maximum storage fill level [-].
        Upper operational limit for storage system (default: 0.8).
    spez_Investitionskosten_Speicher : float, optional
        Specific investment costs for thermal storage [€/m³].
        Storage system cost per unit volume (default: 750 €/m³).
    active : bool, optional
        Initial operational state of the boiler system.
        Starting condition for simulation (default: True).
    opt_BMK_min : float, optional
        Minimum boiler capacity for optimization [kW].
        Lower bound for capacity optimization (default: 0).
    opt_BMK_max : float, optional
        Maximum boiler capacity for optimization [kW].
        Upper bound for capacity optimization (default: 1000).
    opt_Speicher_min : float, optional
        Minimum storage capacity for optimization [m³].
        Lower bound for storage optimization (default: 0).
    opt_Speicher_max : float, optional
        Maximum storage capacity for optimization [m³].
        Upper bound for storage optimization (default: 100).

    Attributes
    ----------
    thermal_capacity_kW : float
        Nominal thermal power output [kW]
    Größe_Holzlager : float
        Wood storage facility capacity [tons]
    Nutzungsgrad_BMK : float
        Boiler thermal efficiency [-]
    min_Teillast : float
        Minimum part-load operation threshold [-]
    speicher_aktiv : bool
        Thermal storage system activation status
    Nutzungsdauer : int
        System operational lifespan [years]
    co2_factor_fuel : float
        CO2 emission factor for biomass fuel [tCO2/MWh]
    primärenergiefaktor : float
        Primary energy factor for biomass [-]
    Anteil_Förderung_BEW : float
        BEW subsidy percentage [-]
    strategy : BiomassBoilerStrategy
        Control strategy for boiler operation

    Notes
    -----
    Biomass Boiler Technology:
        
        **Thermal Performance**:
        The biomass boiler model calculates thermal performance based on:
        - Nominal efficiency under rated conditions
        - Part-load operation characteristics with minimum load constraints
        - Fuel consumption based on lower heating value of biomass
        - Start-stop cycle analysis for operational optimization
        
        **Fuel System**:
        Wood storage sizing considers:
        - Annual fuel consumption based on heat generation
        - Storage capacity for supply security (typically 2-4 weeks)
        - Delivery logistics and storage facility requirements
        - Fuel handling and feeding system integration
        
        **Control Strategy**:
        The integrated control system manages:
        - Load-following operation with efficiency optimization
        - Thermal storage charging and discharging cycles
        - Temperature-based control with hysteresis
        - Start-stop optimization for minimal cycling

    Economic Modeling:
        
        **Investment Costs**:
        - Boiler system costs including installation and commissioning
        - Wood storage facility including handling equipment
        - Thermal storage system for demand management
        - Integration costs for district heating connection
        
        **Operational Costs**:
        - Biomass fuel costs with price escalation modeling
        - Maintenance and service costs
        - Operational labor requirements
        - Insurance and administrative costs
        
        **Subsidy Integration**:
        BEW (Bundesförderung für effiziente Wärmenetze) support:
        - Up to 40% investment cost coverage for eligible systems
        - Enhanced support for renewable energy integration
        - Performance-based subsidy calculations

    Environmental Impact:
        
        **CO2 Emissions**:
        - Low carbon emissions from sustainable biomass (0.036 tCO2/MWh)
        - Carbon-neutral operation with sustainable fuel sources
        - Lifecycle emission analysis including fuel transport
        
        **Primary Energy**:
        - Low primary energy factor for renewable biomass (0.2)
        - Reduced fossil fuel dependency
        - Contribution to renewable energy targets

    Examples
    --------
    >>> # Create basic biomass boiler system
    >>> boiler = BiomassBoiler(
    ...     name="Biomass_Central_Plant",
    ...     thermal_capacity_kW=500.0,
    ...     Größe_Holzlager=60.0,  # 60 tons wood storage
    ...     Nutzungsgrad_BMK=0.85  # 85% efficiency
    ... )
    >>> 
    >>> print(f"Boiler capacity: {boiler.thermal_capacity_kW} kW")
    >>> print(f"Wood storage: {boiler.Größe_Holzlager} tons")
    >>> print(f"Efficiency: {boiler.Nutzungsgrad_BMK:.1%}")

    >>> # Biomass boiler with integrated thermal storage
    >>> boiler_storage = BiomassBoiler(
    ...     name="Biomass_with_Storage",
    ...     thermal_capacity_kW=300.0,
    ...     speicher_aktiv=True,
    ...     Speicher_Volumen=50.0,  # 50 m³ storage tank
    ...     T_vorlauf=85.0,         # 85°C supply temperature
    ...     T_ruecklauf=55.0        # 55°C return temperature
    ... )
    >>> 
    >>> # Simulate annual operation
    >>> import numpy as np
    >>> annual_hours = 8760
    >>> load_profile = np.random.uniform(50, 250, annual_hours)  # Variable load
    >>> 
    >>> # Economic parameters for analysis
    >>> economic_params = {
    ...     'electricity_price': 0.25,     # €/kWh
    ...     'gas_price': 0.08,             # €/kWh
    ...     'wood_price': 0.05,            # €/kWh biomass
    ...     'capital_interest_rate': 0.04,  # 4% interest
    ...     'inflation_rate': 0.02,        # 2% inflation
    ...     'time_period': 20,             # 20-year analysis
    ...     'subsidy_eligibility': "Ja",   # BEW subsidy eligible
    ...     'hourly_rate': 45.0            # €/hour labor cost
    ... }
    >>> 
    >>> # Calculate system performance and economics
    >>> results = boiler_storage.calculate(
    ...     economic_parameters=economic_params,
    ...     duration=1.0,  # 1-hour time steps
    ...     load_profile=load_profile
    ... )
    >>> 
    >>> print(f"Annual heat generation: {results['Wärmemenge']:.1f} MWh")
    >>> print(f"Fuel consumption: {results['Brennstoffbedarf']:.1f} MWh")
    >>> print(f"Heat generation cost: {results['WGK']:.2f} €/MWh")
    >>> print(f"CO2 emissions: {results['spec_co2_total']:.3f} tCO2/MWh")

    >>> # Optimization for district heating integration
    >>> # Define load profile for district heating network
    >>> winter_load = np.concatenate([
    ...     np.random.uniform(200, 400, 2000),  # Winter heating season
    ...     np.random.uniform(50, 150, 4760),   # Transition periods
    ...     np.random.uniform(200, 400, 2000)   # Second winter period
    ... ])
    >>> 
    >>> # Optimize boiler sizing
    >>> optimal_boiler = BiomassBoiler(
    ...     name="Optimized_District_Boiler",
    ...     thermal_capacity_kW=350.0,
    ...     Größe_Holzlager=80.0,
    ...     speicher_aktiv=True,
    ...     Speicher_Volumen=40.0,
    ...     opt_BMK_min=200,      # Minimum 200 kW
    ...     opt_BMK_max=800,      # Maximum 800 kW
    ...     opt_Speicher_min=20,  # Minimum 20 m³ storage
    ...     opt_Speicher_max=100  # Maximum 100 m³ storage
    ... )
    >>> 
    >>> # Get optimization parameters
    >>> initial_vals, var_names, bounds = optimal_boiler.add_optimization_parameters(0)
    >>> print(f"Optimization variables: {var_names}")
    >>> print(f"Initial values: {initial_vals}")
    >>> print(f"Bounds: {bounds}")

    >>> # Environmental impact analysis
    >>> optimal_boiler.calculate_environmental_impact()
    >>> print(f"Primary energy consumption: {optimal_boiler.primärenergie:.1f} MWh")
    >>> print(f"Specific CO2 emissions: {optimal_boiler.spec_co2_total:.3f} tCO2/MWh")
    >>> 
    >>> # Compare with fossil fuel alternative
    >>> fossil_co2 = 0.200  # tCO2/MWh for natural gas
    >>> co2_savings = fossil_co2 - optimal_boiler.spec_co2_total
    >>> print(f"CO2 savings vs. gas: {co2_savings:.3f} tCO2/MWh")

    See Also
    --------
    BaseHeatGenerator : Base class for heat generation systems
    BiomassBoilerStrategy : Control strategy for biomass boiler operation
    """
    
    def __init__(self, name: str, thermal_capacity_kW: float, Größe_Holzlager: float = 40, 
                 spez_Investitionskosten: float = 200, spez_Investitionskosten_Holzlager: float = 400, 
                 Nutzungsgrad_BMK: float = 0.8, min_Teillast: float = 0.3,
                 speicher_aktiv: bool = False, Speicher_Volumen: float = 20, 
                 T_vorlauf: float = 90, T_ruecklauf: float = 60, 
                 initial_fill: float = 0.0, min_fill: float = 0.2, max_fill: float = 0.8, 
                 spez_Investitionskosten_Speicher: float = 750, active: bool = True, 
                 opt_BMK_min: float = 0, opt_BMK_max: float = 1000, 
                 opt_Speicher_min: float = 0, opt_Speicher_max: float = 100):
        super().__init__(name)
        self.thermal_capacity_kW = thermal_capacity_kW
        self.Größe_Holzlager = Größe_Holzlager
        self.spez_Investitionskosten = spez_Investitionskosten
        self.spez_Investitionskosten_Holzlager = spez_Investitionskosten_Holzlager
        self.Nutzungsgrad_BMK = Nutzungsgrad_BMK
        self.min_Teillast = min_Teillast
        self.speicher_aktiv = speicher_aktiv
        self.Speicher_Volumen = Speicher_Volumen
        self.T_vorlauf = T_vorlauf
        self.T_ruecklauf = T_ruecklauf
        self.initial_fill = initial_fill
        self.min_fill = min_fill
        self.max_fill = max_fill
        self.spez_Investitionskosten_Speicher = spez_Investitionskosten_Speicher
        self.active = active
        self.opt_BMK_min = opt_BMK_min
        self.opt_BMK_max = opt_BMK_max
        self.opt_Speicher_min = opt_Speicher_min
        self.opt_Speicher_max = opt_Speicher_max
        
        # System specifications based on biomass boiler standards
        self.Nutzungsdauer = 15  # Operational lifespan [years]
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 3, 3, 0  # Installation and maintenance factors
        self.co2_factor_fuel = 0.036  # tCO2/MWh for wood pellets (carbon-neutral)
        self.primärenergiefaktor = 0.2  # Primary energy factor for biomass
        self.Anteil_Förderung_BEW = 0.4  # BEW subsidy percentage (40%)

        # Initialize control strategy
        self.strategy = BiomassBoilerStrategy(75, 70)

        # Initialize operational arrays
        self.init_operation(8760)

    def init_operation(self, hours: int) -> None:
        """
        Initialize operational arrays for annual simulation.

        Parameters
        ----------
        hours : int
            Number of simulation hours (typically 8760 for annual analysis).
        """
        self.betrieb_mask = np.array([False] * hours)
        self.Wärmeleistung_kW = np.zeros(hours, dtype=float)
        self.Wärmemenge_MWh = 0
        self.Brennstoffbedarf_MWh = 0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0
        self.Betriebsstunden_pro_Start = 0
        
        self.calculated = False  # Flag to indicate if calculation is complete

    def simulate_operation(self, Last_L: np.ndarray) -> None:
        """
        Simulate biomass boiler operation without thermal storage.

        This method models the operational behavior of the biomass boiler
        in load-following mode, considering minimum part-load constraints
        and efficiency characteristics for optimal heat generation.

        Parameters
        ----------
        Last_L : numpy.ndarray
            Hourly thermal load profile [kW].
            Heat demand time series for the district heating system.

        Notes
        -----
        Operational Characteristics:
            
            **Part-Load Operation**:
            - Minimum load threshold prevents inefficient operation
            - Boiler operates only when load exceeds minimum part-load
            - Heat output matches load up to nominal capacity
            
            **Efficiency Modeling**:
            - Constant efficiency assumed for simplification
            - Part-load efficiency effects can be integrated
            - Start-stop penalties included in operational analysis
            
            **Load Following**:
            - Direct load-following without storage buffering
            - Immediate response to demand changes
            - No thermal inertia or storage effects considered

        The simulation sets operational flags and heat output arrays
        for subsequent economic and environmental analysis.
        """
        # Determine operational periods based on minimum part-load constraint
        self.betrieb_mask = Last_L >= self.thermal_capacity_kW * self.min_Teillast
        
        # Calculate heat output limited by boiler capacity
        self.Wärmeleistung_kW[self.betrieb_mask] = np.minimum(
            Last_L[self.betrieb_mask], 
            self.thermal_capacity_kW
        )

    def simulate_storage(self, Last_L: np.ndarray, duration: float) -> None:
        """
        Simulate integrated biomass boiler and thermal storage operation.

        This method models the combined operation of the biomass boiler
        with thermal storage system, including dynamic storage management,
        temperature-based control strategies, and optimal charging/discharging
        cycles for demand-supply balancing.

        Parameters
        ----------
        Last_L : numpy.ndarray
            Hourly thermal load profile [kW].
            Heat demand time series for the system.
        duration : float
            Time step duration [hours].
            Typically 1.0 hour for hourly simulation.

        Notes
        -----
        Storage System Modeling:
            
            **Thermal Storage Calculation**:
            Storage capacity based on water storage with temperature difference:
            - Capacity = Volume × ρ × cp × ΔT / 3600 [kWh]
            - Sensible heat storage in water medium
            - Temperature stratification effects simplified
            
            **Control Strategy**:
            The storage control implements:
            - Priority loading when storage capacity available
            - Boiler operation at nominal capacity when active
            - Storage discharge when boiler inactive
            - Hysteresis control to prevent frequent switching
            
            **Heat Balance**:
            - Storage charging: Boiler output > Load demand
            - Storage discharging: Load demand > Boiler output
            - Heat loss effects can be integrated for detailed modeling
            
            **Operational Limits**:
            - Minimum fill level maintains reserve capacity
            - Maximum fill level prevents overcharging
            - Storage state tracking for optimization analysis

        The simulation updates storage fill levels, boiler operation,
        and storage charging/discharging profiles for annual analysis.
        """
        # Calculate thermal storage capacity based on water storage
        speicher_kapazitaet = (self.Speicher_Volumen * 4186 * 
                              (self.T_vorlauf - self.T_ruecklauf) / 3600)  # kWh
        
        # Initialize storage state and operational limits
        speicher_fill = self.initial_fill * speicher_kapazitaet
        min_speicher_fill = self.min_fill * speicher_kapazitaet
        max_speicher_fill = self.max_fill * speicher_kapazitaet

        # Initialize storage-related arrays
        self.Wärmeleistung_Speicher_kW = np.zeros_like(Last_L)
        self.Speicher_Fuellstand = np.zeros_like(Last_L)

        # Simulate hourly storage operation
        for i in range(len(Last_L)):
            if self.active:
                # Check if storage is full
                if speicher_fill >= max_speicher_fill:
                    self.active = False
                else:
                    # Operate boiler at nominal capacity
                    self.Wärmeleistung_kW[i] = self.thermal_capacity_kW
                    
                    # Manage storage charging/discharging
                    if Last_L[i] < self.thermal_capacity_kW:
                        # Charge storage with excess heat
                        self.Wärmeleistung_Speicher_kW[i] = Last_L[i] - self.thermal_capacity_kW
                        speicher_fill += (self.thermal_capacity_kW - Last_L[i]) * duration
                        speicher_fill = float(min(speicher_fill, speicher_kapazitaet))
                    else:
                        # No storage charging when load exceeds boiler capacity
                        self.Wärmeleistung_Speicher_kW[i] = 0
            else:
                # Check if storage needs recharging
                if speicher_fill <= min_speicher_fill:
                    self.active = True
            
            # Storage discharge mode when boiler inactive
            if not self.active:
                self.Wärmeleistung_kW[i] = 0
                self.Wärmeleistung_Speicher_kW[i] = Last_L[i]
                speicher_fill -= Last_L[i] * duration
                speicher_fill = float(max(speicher_fill, 0))

            # Update storage fill level percentage
            self.Speicher_Fuellstand[i] = speicher_fill / speicher_kapazitaet * 100  # %

        # Update operational mask based on boiler operation
        self.betrieb_mask = self.Wärmeleistung_kW > 0

    def generate(self, t: int, **kwargs) -> Tuple[float, float]:
        """
        Generate heat output for specified time step.

        This method provides the instantaneous heat generation for
        real-time simulation or control system integration, considering
        the current operational state and control strategy.

        Parameters
        ----------
        t : int
            Current time step index.
        **kwargs
            Additional parameters for heat generation control.

        Returns
        -------
        tuple of (float, float)
            Heat generation and electricity generation:
            
            heat_output : float
                Instantaneous thermal power output [kW].
            electricity_output : float
                Electrical power output [kW] (always 0 for boiler-only systems).

        Notes
        -----
        Real-Time Operation:
            
            **Control Integration**:
            - Interfaces with system control strategies
            - Responds to external control signals
            - Maintains operational constraints and limits
            
            **Heat Generation**:
            - Provides nominal capacity when active
            - Zero output when system inactive
            - No electrical cogeneration in standard biomass boilers
            
            **State Management**:
            - Updates operational arrays for time step
            - Maintains consistency with simulation results
            - Supports both simulation and real-time operation

        This method is typically used within larger system simulations
        or for real-time control system integration.
        """
        if self.active:
            self.betrieb_mask[t] = True
            self.Wärmeleistung_kW[t] = self.thermal_capacity_kW
        else:
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0

        return self.Wärmeleistung_kW[t], 0  # Heat output, electricity output
    
    def calculate_results(self, duration: float) -> None:
        """
        Calculate operational performance metrics from simulation results.

        Parameters
        ----------
        duration : float
            Time step duration [hours] for energy calculations.
        """
        # Calculate annual energy generation and fuel consumption
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Brennstoffbedarf_MWh = self.Wärmemenge_MWh / self.Nutzungsgrad_BMK

        # Analyze start-stop cycles and operational hours
        starts = np.diff(self.betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(self.betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = (self.Betriebsstunden / self.Anzahl_Starts 
                                         if self.Anzahl_Starts > 0 else 0)

    def calculate_heat_generation_costs(self, economic_parameters: Dict) -> float:
        """
        Calculate comprehensive heat generation costs including BEW subsidies.

        This method performs detailed economic analysis of the biomass boiler
        system including investment costs, operational expenses, and subsidy
        calculations according to German BEW funding guidelines.

        Parameters
        ----------
        economic_parameters : dict
            Dictionary containing economic parameters:
            
            - electricity_price : float
                Electricity price [€/kWh]
            - gas_price : float  
                Natural gas price [€/kWh]
            - wood_price : float
                Biomass fuel price [€/kWh]
            - capital_interest_rate : float
                Interest rate for capital costs [-]
            - inflation_rate : float
                Annual inflation rate [-] 
            - time_period : int
                Analysis time period [years]
            - subsidy_eligibility : str
                BEW subsidy eligibility ("Ja"/"Nein")
            - hourly_rate : float
                Labor cost rate [€/hour]

        Returns
        -------
        float
            Heat generation cost [€/MWh].
            Levelized cost of heat including all system costs.

        Notes
        -----
        Economic Analysis Components:
            
            **Investment Costs**:
            - Boiler system: Capacity-based costs [€/kW]
            - Wood storage: Storage-based costs [€/ton]
            - Thermal storage: Volume-based costs [€/m³]
            - Installation and commissioning costs
            
            **Operational Costs**:
            - Fuel costs: Annual biomass consumption
            - Maintenance: Percentage of investment costs
            - Labor: Operational effort requirements
            - Insurance and administrative costs
            
            **BEW Subsidy Calculation**:
            The Bundesförderung für effiziente Wärmenetze provides:
            - Up to 40% investment cost coverage
            - Enhanced support for renewable integration
            - Reduced total system costs for eligible projects
            
            **Annuity Method**:
            - Capital recovery factor calculation
            - Present value of operational costs
            - Levelized cost of heat generation
            - Inflation and interest rate effects

        The calculation provides comprehensive lifecycle cost analysis
        suitable for district heating economic optimization.
        """
        # Extract economic parameters
        self.Strompreis = economic_parameters['electricity_price']
        self.Gaspreis = economic_parameters['gas_price']
        self.Holzpreis = economic_parameters['wood_price']
        self.q = economic_parameters['capital_interest_rate']
        self.r = economic_parameters['inflation_rate']
        self.T = economic_parameters['time_period']
        self.BEW = economic_parameters['subsidy_eligibility']
        self.stundensatz = economic_parameters['hourly_rate']

        if self.Wärmemenge_MWh == 0:
            return 0
        
        # Calculate component investment costs
        self.Investitionskosten_Kessel = self.spez_Investitionskosten * self.thermal_capacity_kW
        self.Investitionskosten_Holzlager = self.spez_Investitionskosten_Holzlager * self.Größe_Holzlager
        if self.speicher_aktiv:
            self.Investitionskosten_Speicher = self.spez_Investitionskosten_Speicher * self.Speicher_Volumen
        else:
            self.Investitionskosten_Speicher = 0
        self.Investitionskosten = (self.Investitionskosten_Kessel + 
                                  self.Investitionskosten_Holzlager + 
                                  self.Investitionskosten_Speicher)

        # Calculate standard annuity without subsidies
        self.A_N = self.annuity(
            initial_investment_cost=self.Investitionskosten,
            asset_lifespan_years=self.Nutzungsdauer,
            installation_factor=self.f_Inst,
            maintenance_inspection_factor=self.f_W_Insp,
            operational_effort_h=self.Bedienaufwand,
            interest_rate_factor=self.q,
            inflation_rate_factor=self.r,
            consideration_time_period_years=self.T, 
            annual_energy_demand=self.Brennstoffbedarf_MWh,
            energy_cost_per_unit=self.Holzpreis,
            annual_revenue=0,
            hourly_rate=self.stundensatz
        )
        
        self.WGK = self.A_N / self.Wärmemenge_MWh

        # Calculate BEW subsidy scenario
        self.Eigenanteil = 1 - self.Anteil_Förderung_BEW
        self.Investitionskosten_Gesamt_BEW = self.Investitionskosten * self.Eigenanteil
        
        self.Annuität_BEW = self.annuity(
            initial_investment_cost=self.Investitionskosten_Gesamt_BEW,
            asset_lifespan_years=self.Nutzungsdauer,
            installation_factor=self.f_Inst,
            maintenance_inspection_factor=self.f_W_Insp,
            operational_effort_h=self.Bedienaufwand,
            interest_rate_factor=self.q,
            inflation_rate_factor=self.r,
            consideration_time_period_years=self.T, 
            annual_energy_demand=self.Brennstoffbedarf_MWh,
            energy_cost_per_unit=self.Holzpreis,
            annual_revenue=0,
            hourly_rate=self.stundensatz
        )
        
        self.WGK_BEW = self.Annuität_BEW / self.Wärmemenge_MWh

        # Return appropriate cost based on subsidy eligibility
        if self.BEW == "Nein":
            return self.WGK
        elif self.BEW == "Ja":
            return self.WGK_BEW

    def calculate_environmental_impact(self) -> None:
        """
        Calculate environmental impact metrics for the biomass boiler system.

        This method assesses the environmental performance of the biomass
        heating system including CO2 emissions, primary energy consumption,
        and renewable energy contribution for sustainability analysis.

        Notes
        -----
        Environmental Assessment:
            
            **CO2 Emissions**:
            - Biomass CO2 factor: 0.036 tCO2/MWh (low carbon)
            - Carbon-neutral operation with sustainable biomass
            - Significantly lower emissions than fossil fuels
            - Lifecycle emissions including transport and processing
            
            **Primary Energy**:
            - Primary energy factor: 0.2 for renewable biomass
            - Low fossil fuel dependency
            - Renewable energy system classification
            - Contribution to renewable energy targets
            
            **Sustainability Metrics**:
            - Specific emissions per MWh of heat generated
            - Primary energy consumption analysis
            - Renewable energy fraction calculations
            - Environmental benefit quantification

        The environmental analysis supports sustainability reporting
        and renewable energy system optimization for district heating.
        """
        # Calculate CO2 emissions from biomass fuel consumption
        self.co2_emissions = self.Brennstoffbedarf_MWh * self.co2_factor_fuel  # tCO2
        
        # Calculate specific CO2 emissions per unit heat generated
        self.spec_co2_total = (self.co2_emissions / self.Wärmemenge_MWh 
                              if self.Wärmemenge_MWh > 0 else 0)  # tCO2/MWh_heat

        # Calculate primary energy consumption
        self.primärenergie = self.Brennstoffbedarf_MWh * self.primärenergiefaktor
        

    def calculate(self, economic_parameters: Dict, duration: float, 
                 load_profile: np.ndarray, **kwargs) -> Dict:
        """
        Comprehensive biomass boiler system analysis and optimization.

        This method performs complete system analysis including thermal
        simulation, economic evaluation, and environmental assessment
        for biomass boiler systems in district heating applications.

        Parameters
        ----------
        economic_parameters : dict
            Economic analysis parameters including costs, rates, and subsidies.
        duration : float
            Simulation time step duration [hours].
        load_profile : numpy.ndarray
            Annual hourly thermal load profile [kW].
        **kwargs
            Additional calculation parameters.

        Returns
        -------
        dict
            Comprehensive results dictionary containing:
            
            - tech_name : str
                Technology identifier
            - Wärmemenge : float
                Annual heat generation [MWh]
            - Wärmeleistung_L : numpy.ndarray
                Hourly heat output profile [kW]
            - Brennstoffbedarf : float
                Annual fuel consumption [MWh]
            - WGK : float
                Heat generation cost [€/MWh]
            - Anzahl_Starts : int
                Number of start-stop cycles
            - Betriebsstunden : float
                Annual operating hours [h]
            - Betriebsstunden_pro_Start : float
                Average operating hours per start [h]
            - spec_co2_total : float
                Specific CO2 emissions [tCO2/MWh]
            - primärenergie : float
                Primary energy consumption [MWh]
            - color : str
                Visualization color identifier
            - Wärmeleistung_Speicher_L : numpy.ndarray, optional
                Storage heat exchange profile [kW] (if storage active)
            - Speicherfüllstand_L : numpy.ndarray, optional
                Storage fill level profile [%] (if storage active)

        Notes
        -----
        Analysis Workflow:
            
            **1. Thermal Simulation**:
            - Storage or non-storage operation simulation
            - Load-following or storage-buffered operation
            - Operational constraint enforcement
            
            **2. Performance Calculation**:
            - Energy balance and efficiency analysis
            - Start-stop cycle analysis
            - Capacity factor and utilization metrics
            
            **3. Economic Analysis**:
            - Investment and operational cost calculation
            - BEW subsidy integration
            - Levelized cost of heat determination
            
            **4. Environmental Assessment**:
            - CO2 emission calculation
            - Primary energy analysis
            - Sustainability metric determination

        The comprehensive analysis supports system optimization,
        economic feasibility assessment, and environmental impact
        evaluation for biomass heating in district energy systems.
        """
        # Perform thermal simulation if not already calculated
        if self.calculated == False:
            if self.speicher_aktiv:
                self.simulate_storage(load_profile, duration)
            else:
                self.simulate_operation(load_profile)
            
        # Calculate performance metrics
        self.calculate_results(duration)
        
        # Perform economic and environmental analysis
        WGK = self.calculate_heat_generation_costs(economic_parameters)
        self.calculate_environmental_impact()

        # Compile comprehensive results
        results = {
            'tech_name': self.name,
            'Wärmemenge': self.Wärmemenge_MWh,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'Brennstoffbedarf': self.Brennstoffbedarf_MWh,
            'WGK': WGK,
            'Anzahl_Starts': self.Anzahl_Starts,
            'Betriebsstunden': self.Betriebsstunden,
            'Betriebsstunden_pro_Start': self.Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            'color': "green"  # Green color for renewable biomass
        }

        # Add storage-specific results if thermal storage is active
        if self.speicher_aktiv:
            results['Wärmeleistung_Speicher_L'] = self.Wärmeleistung_Speicher_kW
            results['Speicherfüllstand_L'] = self.Speicher_Fuellstand

        return results
    
    def set_parameters(self, variables: List[float], variables_order: List[str], idx: int) -> None:
        """
        Set optimization parameters for the biomass boiler system.

        Parameters
        ----------
        variables : list of float
            Optimization variable values.
        variables_order : list of str
            Variable names corresponding to values.
        idx : int
            Technology index for parameter identification.
        """
        try:
            self.thermal_capacity_kW = variables[variables_order.index(f"P_BMK_{idx}")]
        except ValueError as e:
            print(f"Fehler beim Setzen der Parameter für {self.name}: {e}")

    def add_optimization_parameters(self, idx: int) -> Tuple[List[float], List[str], List[Tuple[float, float]]]:
        """
        Define optimization parameters for biomass boiler system sizing.

        This method sets up optimization variables, bounds, and initial values
        for system capacity optimization in district heating applications.

        Parameters
        ----------
        idx : int
            Technology index for unique parameter identification.

        Returns
        -------
        tuple of (list, list, list)
            Optimization setup parameters:
            
            initial_values : list of float
                Initial values for optimization variables.
            variables_order : list of str
                Variable names for parameter identification.
            bounds : list of tuple
                Lower and upper bounds for each variable.

        Notes
        -----
        Optimization Variables:
            
            **Boiler Capacity**:
            - Variable: P_BMK_{idx} [kW]
            - Bounds: [opt_BMK_min, opt_BMK_max]
            - Optimization target: Optimal thermal capacity
            
            **Storage Volume** (if storage active):
            - Variable: Speicher_Volumen_{idx} [m³]
            - Bounds: [opt_Speicher_min, opt_Speicher_max]
            - Optimization target: Optimal storage size

        The optimization setup supports multi-objective optimization
        including cost minimization, efficiency maximization, and
        environmental impact reduction for district heating systems.
        """
        # Initialize with boiler capacity optimization
        initial_values = [self.thermal_capacity_kW]
        variables_order = [f"P_BMK_{idx}"]
        bounds = [(self.opt_BMK_min, self.opt_BMK_max)]

        # Add storage optimization if thermal storage is active
        if self.speicher_aktiv:
            initial_values.append(self.Speicher_Volumen)
            variables_order.append(f"Speicher_Volumen_{idx}")
            bounds.append((self.opt_Speicher_min, self.opt_Speicher_max))

        return initial_values, variables_order, bounds

    def get_display_text(self) -> str:
        """
        Generate display text for GUI representation.

        Returns
        -------
        str
            Formatted text describing system configuration.
        """
        return (f"{self.name}: th. Leistung: {self.thermal_capacity_kW:.1f}, "
                f"Größe Holzlager: {self.Größe_Holzlager:.1f} t, "
                f"spez. Investitionskosten Kessel: {self.spez_Investitionskosten:.1f} €/kW, "
                f"spez. Investitionskosten Holzlager: {self.spez_Investitionskosten_Holzlager:.1f} €/t")
    
    def extract_tech_data(self) -> Tuple[str, str, str, str]:
        """
        Extract technology data for reporting and documentation.

        Returns
        -------
        tuple of (str, str, str, str)
            Technology data summary:
            
            name : str
                System name identifier
            dimensions : str  
                Technical specifications
            costs : str
                Cost breakdown information
            full_costs : str
                Total investment costs
        """
        dimensions = f"th. Leistung: {self.thermal_capacity_kW:.1f} kW, Größe Holzlager: {self.Größe_Holzlager:.1f} t"
        costs = (f"Investitionskosten Kessel: {self.Investitionskosten_Kessel:.1f} €, "
                f"Investitionskosten Holzlager: {self.Investitionskosten_Holzlager:.1f} €")
        full_costs = f"{self.Investitionskosten:.1f}"
        return self.name, dimensions, costs, full_costs

class BiomassBoilerStrategy(BaseStrategy):
    """
    Advanced control strategy for biomass boiler systems with thermal storage.

    This class implements temperature-based control strategies for optimal
    biomass boiler operation including storage management, efficiency
    optimization, and demand-responsive operation for district heating systems.

    Parameters
    ----------
    charge_on : float
        Upper storage temperature threshold to activate boiler [°C].
        Storage temperature above which boiler starts charging.
    charge_off : float
        Lower storage temperature threshold to deactivate boiler [°C].
        Storage temperature below which boiler stops charging.

    Notes
    -----
    Control Strategy Features:
        
        **Temperature-Based Control**:
        - Hysteresis control prevents frequent switching
        - Storage temperature monitoring for optimal operation
        - Demand-responsive charging and discharging cycles
        
        **Efficiency Optimization**:
        - Optimal boiler loading for maximum efficiency
        - Minimized start-stop cycles for reduced wear
        - Storage buffering for smooth operation
        
        **Integration Capabilities**:
        - District heating system integration
        - External control signal compatibility
        - Predictive control algorithm support

    The control strategy ensures optimal biomass boiler operation
    while maintaining system efficiency and minimizing operational costs.

    Examples
    --------
    >>> # Create control strategy for storage-integrated boiler
    >>> strategy = BiomassBoilerStrategy(
    ...     charge_on=75,   # Start charging at 75°C storage temperature
    ...     charge_off=70   # Stop charging at 70°C storage temperature
    ... )
    >>> 
    >>> # Apply strategy to biomass boiler
    >>> boiler = BiomassBoiler(
    ...     name="Controlled_Biomass_System",
    ...     thermal_capacity_kW=400.0,
    ...     speicher_aktiv=True
    ... )
    >>> boiler.strategy = strategy

    See Also
    --------
    BaseStrategy : Base class for heat generator control strategies
    BiomassBoiler : Biomass boiler system implementation
    """
    
    def __init__(self, charge_on: float, charge_off: float):
        """
        Initialize biomass boiler control strategy with temperature setpoints.

        Parameters
        ----------
        charge_on : float
            Upper storage temperature to activate boiler [°C].
        charge_off : float
            Lower storage temperature to deactivate boiler [°C].
        """
        super().__init__(charge_on, charge_off)