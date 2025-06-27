"""
Combined Heat and Power (CHP) System Module
============================================

This module provides comprehensive Combined Heat and Power (CHP) system modeling
capabilities for district heating applications.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11

The implementation includes detailed
thermal and electrical performance modeling, storage system integration, economic
analysis, and environmental impact assessment for gas-fired and biomass-fired
CHP systems.

The module supports both gas CHP (Erdgas-BHKW) and wood gasification CHP
(Holzgas-BHKW) technologies with advanced control strategies for optimal
cogeneration operation in district heating networks.

Features
--------
- Comprehensive CHP modeling with thermal and electrical efficiency curves
- Gas-fired and biomass-fired CHP system variants
- Integrated thermal storage system with dynamic simulation
- Advanced control strategies for cogeneration optimization
- Economic analysis including electricity revenue calculations
- Environmental impact assessment including CO2 offset benefits
- Part-load operation modeling with minimum load constraints

Technical Specifications
------------------------
**CHP System Modeling**:
- Thermal capacity sizing from 10 kW to 1+ MW installations
- Electrical efficiency modeling with power-to-heat ratios
- Combined efficiency calculations for fuel utilization optimization
- Part-load operation constraints with minimum load thresholds
- Start-stop cycle analysis for operational optimization

**Cogeneration Technologies**:
- Gas CHP: Natural gas-fired internal combustion engines
- Wood Gas CHP: Biomass gasification with gas engine systems
- Electrical efficiency: 33% typical for gas engines
- Combined efficiency: 90% total fuel utilization
- Heat-to-power ratio optimization for district heating

**Thermal Storage Integration**:
- Dynamic thermal storage simulation with heat balance calculations
- Storage capacity optimization for cogeneration scheduling
- Temperature-based control strategies with hysteresis
- Storage fill level monitoring and optimization
- Heat exchanger modeling for storage integration

**Economic Analysis**:
- Comprehensive cost modeling including capital and operational costs
- Electricity revenue calculations based on market prices
- Technology-specific investment costs (Gas vs. Wood Gas CHP)
- BEW (Bundesförderung für effiziente Wärmenetze) subsidy integration
- Annuity-based economic evaluation with electricity offset

**Environmental Assessment**:
- CO2 emission calculations for fuel consumption
- CO2 savings from electricity generation (grid displacement)
- Net CO2 impact assessment for cogeneration systems
- Primary energy factor analysis for different fuel types
- Sustainability metrics for renewable and fossil CHP systems

Classes
-------
CHP : Main combined heat and power system class
CHPStrategy : Control strategy for CHP operation with storage

Dependencies
------------
- numpy >= 1.20.0 : Numerical calculations and array operations
- districtheatingsim.heat_generators.base_heat_generator : Base classes for heat generators

Applications
------------
The module supports CHP applications including:
- District heating central CHP plants
- Building-level cogeneration systems
- Industrial heat and power supply
- Grid-connected electricity generation with heat recovery
- Renewable biomass cogeneration systems

References
----------
CHP system modeling based on:
- VDI 4608 combined heat and power systems standards
- ASUE (Arbeitsgemeinschaft für sparsamen und umweltfreundlichen Energieverbrauch) guidelines
- German Cogeneration Act (Kraft-Wärme-Kopplungsgesetz - KWKG)
- BEW subsidy guidelines for efficient heating networks
"""

import numpy as np
from typing import Dict, Tuple, List, Optional, Union

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy

class CHP(BaseHeatGenerator):
    """
    Comprehensive Combined Heat and Power (CHP) system for district heating applications.

    This class models gas-fired and biomass-fired CHP systems including internal
    combustion engines, gas turbines, and wood gasification systems. The implementation
    provides detailed cogeneration performance modeling, economic analysis including
    electricity revenue, and environmental impact assessment for high-efficiency
    heat and power generation.

    The CHP model includes advanced features such as heat-led operation with storage,
    electrical efficiency optimization, part-load operation modeling, and comprehensive
    cost analysis including German KWKG and BEW subsidy calculations.

    Parameters
    ----------
    name : str
        Unique identifier for the CHP system.
        Technology prefix determines fuel type: "BHKW" for gas, "Holzgas-BHKW" for biomass.
    th_Leistung_kW : float
        Nominal thermal power output of the CHP system [kW].
        Determines maximum heat generation capacity under rated conditions.
    spez_Investitionskosten_GBHKW : float, optional
        Specific investment costs for gas CHP systems [€/kW].
        Capital cost per unit thermal capacity for gas engines (default: 1500 €/kW).
    spez_Investitionskosten_HBHKW : float, optional
        Specific investment costs for wood gas CHP systems [€/kW].
        Capital cost per unit thermal capacity for biomass gasification (default: 1850 €/kW).
    el_Wirkungsgrad : float, optional
        Electrical efficiency of the CHP system [-].
        Ratio of electrical output to fuel energy input (default: 0.33).
    KWK_Wirkungsgrad : float, optional
        Combined heat and power efficiency [-].
        Total fuel utilization efficiency for heat and electricity (default: 0.9).
    min_Teillast : float, optional
        Minimum part-load operation threshold [-].
        Minimum operational load as fraction of nominal capacity (default: 0.7).
    speicher_aktiv : bool, optional
        Enable integrated thermal storage system.
        Activates storage modeling and control strategies (default: False).
    Speicher_Volumen_BHKW : float, optional
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
        Initial operational state of the CHP system.
        Starting condition for simulation (default: True).
    opt_BHKW_min : float, optional
        Minimum CHP capacity for optimization [kW].
        Lower bound for capacity optimization (default: 0).
    opt_BHKW_max : float, optional
        Maximum CHP capacity for optimization [kW].
        Upper bound for capacity optimization (default: 1000).
    opt_BHKW_Speicher_min : float, optional
        Minimum storage capacity for optimization [m³].
        Lower bound for storage optimization (default: 0).
    opt_BHKW_Speicher_max : float, optional
        Maximum storage capacity for optimization [m³].
        Upper bound for storage optimization (default: 100).

    Attributes
    ----------
    th_Leistung_kW : float
        Nominal thermal power output [kW]
    thermischer_Wirkungsgrad : float
        Thermal efficiency of the CHP system [-]
    el_Leistung_Soll : float
        Nominal electrical power output [kW]
    el_Wirkungsgrad : float
        Electrical efficiency [-]
    KWK_Wirkungsgrad : float
        Combined heat and power efficiency [-]
    min_Teillast : float
        Minimum part-load operation threshold [-]
    speicher_aktiv : bool
        Thermal storage system activation status
    Nutzungsdauer : int
        System operational lifespan [years]
    co2_factor_fuel : float
        CO2 emission factor for fuel [tCO2/MWh]
    primärenergiefaktor : float
        Primary energy factor for fuel [-]
    co2_factor_electricity : float
        CO2 emission factor for grid electricity [tCO2/MWh]
    Anteil_Förderung_BEW : float
        BEW subsidy percentage [-]
    strategy : CHPStrategy
        Control strategy for CHP operation

    Notes
    -----
    CHP Technology Overview:
        
        **Gas CHP Systems (BHKW)**:
        - Natural gas-fired internal combustion engines
        - Electrical efficiency: ~33% (modern gas engines)
        - Thermal efficiency: ~57% (heat recovery from engine)
        - Combined efficiency: ~90% total fuel utilization
        - Investment costs: ~1500 €/kW thermal capacity
        
        **Wood Gas CHP Systems (Holzgas-BHKW)**:
        - Biomass gasification with gas engine integration
        - Two-stage process: gasification + gas engine
        - Electrical efficiency: ~33% (after gasification losses)
        - Higher investment costs: ~1850 €/kW thermal capacity
        - Renewable fuel source with low CO2 emissions
        
        **Cogeneration Operation**:
        The CHP system operates in heat-led mode:
        - Primary heat demand satisfaction
        - Simultaneous electricity generation
        - Storage integration for demand-supply balancing
        - Economic optimization through electricity sales

    Economic Modeling:
        
        **Investment Costs**:
        - CHP unit: Technology-specific costs per kW thermal
        - Thermal storage: Volume-based storage costs
        - Installation and commissioning costs
        - Grid connection for electricity export
        
        **Operational Economics**:
        - Fuel costs: Natural gas or biomass pellets
        - Electricity revenue: Market-based pricing
        - Maintenance costs: Technology-specific factors
        - KWKG subsidies for cogeneration promotion
        
        **Revenue Streams**:
        - Heat sales to district heating network
        - Electricity sales to grid or direct consumption
        - KWKG bonus payments for cogeneration
        - BEW subsidies for efficient heating networks

    Environmental Impact:
        
        **CO2 Balance**:
        - Direct emissions from fuel combustion
        - CO2 savings from electricity grid displacement
        - Net CO2 impact considering electricity offset
        - System-specific emission factors by fuel type
        
        **Primary Energy**:
        - Fuel-specific primary energy factors
        - High efficiency through cogeneration
        - Reduced total primary energy consumption
        - Contribution to energy efficiency targets

    Examples
    --------
    >>> # Create gas-fired CHP system
    >>> gas_chp = CHP(
    ...     name="BHKW_Central_Plant",
    ...     th_Leistung_kW=400.0,
    ...     el_Wirkungsgrad=0.35,      # 35% electrical efficiency
    ...     KWK_Wirkungsgrad=0.92      # 92% combined efficiency
    ... )
    >>> 
    >>> print(f"Thermal capacity: {gas_chp.th_Leistung_kW} kW")
    >>> print(f"Electrical capacity: {gas_chp.el_Leistung_Soll:.1f} kW")
    >>> print(f"Heat-to-power ratio: {gas_chp.th_Leistung_kW/gas_chp.el_Leistung_Soll:.1f}")

    >>> # Wood gasification CHP with thermal storage
    >>> biomass_chp = CHP(
    ...     name="Holzgas-BHKW_District",
    ...     th_Leistung_kW=250.0,
    ...     speicher_aktiv=True,
    ...     Speicher_Volumen_BHKW=40.0,  # 40 m³ storage tank
    ...     T_vorlauf=85.0,              # 85°C supply temperature
    ...     T_ruecklauf=55.0             # 55°C return temperature
    ... )
    >>> 
    >>> # Simulate annual operation
    >>> import numpy as np
    >>> annual_hours = 8760
    >>> heat_demand = np.random.uniform(80, 300, annual_hours)  # Variable heat load
    >>> 
    >>> # Economic parameters for cogeneration analysis
    >>> economic_params = {
    ...     'electricity_price': 0.28,     # €/kWh electricity sales
    ...     'gas_price': 0.08,             # €/kWh natural gas
    ...     'wood_price': 0.05,            # €/kWh biomass
    ...     'capital_interest_rate': 0.04,  # 4% interest
    ...     'inflation_rate': 0.02,        # 2% inflation
    ...     'time_period': 20,             # 20-year analysis
    ...     'subsidy_eligibility': "Ja",   # BEW and KWKG eligible
    ...     'hourly_rate': 50.0            # €/hour labor cost
    ... }
    >>> 
    >>> # Calculate cogeneration performance and economics
    >>> results = biomass_chp.calculate(
    ...     economic_parameters=economic_params,
    ...     duration=1.0,  # 1-hour time steps
    ...     load_profile=heat_demand
    ... )
    >>> 
    >>> print(f"Annual heat generation: {results['Wärmemenge']:.1f} MWh")
    >>> print(f"Annual electricity generation: {results['Strommenge']:.1f} MWh")
    >>> print(f"Fuel consumption: {results['Brennstoffbedarf']:.1f} MWh")
    >>> print(f"Heat generation cost: {results['WGK']:.2f} €/MWh")
    >>> print(f"Net CO2 emissions: {results['spec_co2_total']:.3f} tCO2/MWh")

    >>> # Cogeneration system optimization
    >>> # Define district heating load profile
    >>> winter_base = np.concatenate([
    ...     np.random.uniform(150, 350, 2000),  # Winter heating season
    ...     np.random.uniform(50, 120, 4760),   # Transition periods
    ...     np.random.uniform(150, 350, 2000)   # Second winter period
    ... ])
    >>> 
    >>> # Optimize CHP sizing for district heating
    >>> optimal_chp = CHP(
    ...     name="BHKW_Optimized",
    ...     th_Leistung_kW=200.0,
    ...     speicher_aktiv=True,
    ...     Speicher_Volumen_BHKW=30.0,
    ...     opt_BHKW_min=100,        # Minimum 100 kW thermal
    ...     opt_BHKW_max=500,        # Maximum 500 kW thermal
    ...     opt_BHKW_Speicher_min=15, # Minimum 15 m³ storage
    ...     opt_BHKW_Speicher_max=80  # Maximum 80 m³ storage
    ... )
    >>> 
    >>> # Get optimization parameters for system sizing
    >>> initial_vals, var_names, bounds = optimal_chp.add_optimization_parameters(0)
    >>> print(f"Optimization variables: {var_names}")
    >>> print(f"Initial values: {initial_vals}")
    >>> print(f"Optimization bounds: {bounds}")

    >>> # Economic comparison: Gas vs. Wood Gas CHP
    >>> optimal_chp.calculate_environmental_impact()
    >>> 
    >>> # Calculate electricity generation revenue
    >>> electricity_revenue = optimal_chp.Strommenge_MWh * economic_params['electricity_price']
    >>> print(f"Annual electricity revenue: {electricity_revenue:.0f} €")
    >>> 
    >>> # Environmental benefits analysis
    >>> print(f"CO2 emissions from fuel: {optimal_chp.co2_emissions:.1f} tCO2")
    >>> print(f"CO2 savings from electricity: {optimal_chp.co2_savings:.1f} tCO2")
    >>> print(f"Net CO2 impact: {optimal_chp.co2_total:.1f} tCO2")
    >>> 
    >>> # Compare with heat-only solution
    >>> heat_only_emissions = optimal_chp.Wärmemenge_MWh * 0.201  # Gas boiler
    >>> cogeneration_benefit = heat_only_emissions - optimal_chp.co2_total
    >>> print(f"CO2 benefit vs. separate generation: {cogeneration_benefit:.1f} tCO2")

    See Also
    --------
    BaseHeatGenerator : Base class for heat generation systems
    CHPStrategy : Control strategy for CHP operation with storage
    """
    
    def __init__(self, name: str, th_Leistung_kW: float, spez_Investitionskosten_GBHKW: float = 1500, 
                 spez_Investitionskosten_HBHKW: float = 1850, el_Wirkungsgrad: float = 0.33, 
                 KWK_Wirkungsgrad: float = 0.9, min_Teillast: float = 0.7, speicher_aktiv: bool = False, 
                 Speicher_Volumen_BHKW: float = 20, T_vorlauf: float = 90, T_ruecklauf: float = 60, 
                 initial_fill: float = 0.0, min_fill: float = 0.2, max_fill: float = 0.8, 
                 spez_Investitionskosten_Speicher: float = 750, active: bool = True, 
                 opt_BHKW_min: float = 0, opt_BHKW_max: float = 1000, 
                 opt_BHKW_Speicher_min: float = 0, opt_BHKW_Speicher_max: float = 100):
        super().__init__(name)
        self.th_Leistung_kW = th_Leistung_kW
        self.spez_Investitionskosten_GBHKW = spez_Investitionskosten_GBHKW
        self.spez_Investitionskosten_HBHKW = spez_Investitionskosten_HBHKW
        self.el_Wirkungsgrad = el_Wirkungsgrad
        self.KWK_Wirkungsgrad = KWK_Wirkungsgrad
        self.min_Teillast = min_Teillast
        self.speicher_aktiv = speicher_aktiv
        self.Speicher_Volumen_BHKW = Speicher_Volumen_BHKW
        self.T_vorlauf = T_vorlauf
        self.T_ruecklauf = T_ruecklauf
        self.initial_fill = initial_fill
        self.min_fill = min_fill
        self.max_fill = max_fill
        self.spez_Investitionskosten_Speicher = spez_Investitionskosten_Speicher
        self.active = active
        self.opt_BHKW_min = opt_BHKW_min
        self.opt_BHKW_max = opt_BHKW_max
        self.opt_BHKW_Speicher_min = opt_BHKW_Speicher_min
        self.opt_BHKW_Speicher_max = opt_BHKW_Speicher_max
        
        # Calculate derived performance parameters
        self.thermischer_Wirkungsgrad = self.KWK_Wirkungsgrad - self.el_Wirkungsgrad
        self.el_Leistung_Soll = self.th_Leistung_kW / self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad
        
        # System specifications based on CHP technology
        self.Nutzungsdauer = 15  # Operational lifespan [years]
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 6, 2, 0  # Installation and maintenance factors
        
        # Technology-specific emission and energy factors
        if self.name.startswith("BHKW"):
            self.co2_factor_fuel = 0.201  # tCO2/MWh for natural gas
            self.primärenergiefaktor = 1.1  # Primary energy factor for gas
        elif self.name.startswith("Holzgas-BHKW"):
            self.co2_factor_fuel = 0.036  # tCO2/MWh for wood pellets
            self.primärenergiefaktor = 0.2  # Primary energy factor for biomass
            
        self.co2_factor_electricity = 0.4  # tCO2/MWh for grid electricity displacement
        self.Anteil_Förderung_BEW = 0.4  # BEW subsidy percentage (40%)

        # Initialize control strategy
        self.strategy = CHPStrategy(75, 70)

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
        self.el_Leistung_kW = np.zeros(hours, dtype=float)
        self.Wärmemenge_MWh = 0
        self.Strommenge_MWh = 0
        self.Brennstoffbedarf_MWh = 0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0
        self.Betriebsstunden_pro_Start = 0

        self.calculated = False  # Flag to indicate if calculation is complete

    def simulate_operation(self, Last_L: np.ndarray) -> None:
        """
        Simulate CHP operation without thermal storage in heat-led mode.

        This method models the operational behavior of the CHP system
        in direct heat-following mode, considering minimum part-load constraints
        and simultaneous heat and electricity generation for optimal
        cogeneration efficiency.

        Parameters
        ----------
        Last_L : numpy.ndarray
            Hourly thermal load profile [kW].
            Heat demand time series for the district heating system.

        Notes
        -----
        Heat-Led Operation:
            
            **Operational Strategy**:
            - Heat demand drives CHP operation decisions
            - Minimum load threshold prevents inefficient operation
            - Electricity generation follows heat production
            - No storage buffering in direct operation mode
            
            **Part-Load Constraints**:
            - CHP operates only when heat load exceeds minimum threshold
            - Minimum part-load typically 70% of nominal capacity
            - Prevents inefficient low-load operation
            - Maintains optimal electrical efficiency
            
            **Cogeneration Characteristics**:
            - Fixed heat-to-power ratio based on engine efficiency
            - Simultaneous heat and electricity production
            - Electrical output proportional to thermal output
            - Combined efficiency optimization

        The simulation sets operational flags and output arrays for both
        thermal and electrical generation for subsequent analysis.
        """
        # Determine operational periods based on minimum part-load constraint
        self.betrieb_mask = Last_L >= self.th_Leistung_kW * self.min_Teillast
        
        # Calculate thermal output limited by CHP capacity
        self.Wärmeleistung_kW[self.betrieb_mask] = np.minimum(
            Last_L[self.betrieb_mask], 
            self.th_Leistung_kW
        )
        
        # Calculate electrical output based on thermal output and efficiency ratio
        self.el_Leistung_kW[self.betrieb_mask] = (
            self.Wärmeleistung_kW[self.betrieb_mask] / 
            self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad
        )

    def simulate_storage(self, Last_L: np.ndarray, duration: float) -> None:
        """
        Simulate integrated CHP and thermal storage operation for optimal cogeneration.

        This method models the combined operation of the CHP system with thermal
        storage, enabling heat-led operation with storage buffering for improved
        capacity utilization, reduced cycling, and enhanced economic performance
        through optimized electricity generation.

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
        Storage-Integrated Cogeneration:
            
            **Operational Strategy**:
            - CHP operates at nominal capacity when active
            - Storage buffers heat for demand-supply balancing
            - Extended CHP runtime for improved economics
            - Reduced start-stop cycles for better efficiency
            
            **Storage Management**:
            Storage capacity based on water storage:
            - Capacity = Volume × ρ × cp × ΔT / 3600 [kWh]
            - Charging: CHP heat output > Instantaneous load
            - Discharging: Load demand > CHP output
            - State-based control with hysteresis
            
            **Control Strategy**:
            - CHP activation when storage at minimum level
            - CHP deactivation when storage reaches maximum
            - Continuous electricity generation during heat storage
            - Optimal capacity factor for economic operation
            
            **Economic Benefits**:
            - Higher annual electricity generation
            - Improved CHP capacity utilization
            - Reduced maintenance through fewer starts
            - Enhanced revenue through storage optimization

        The simulation tracks storage states, heat flows, and electrical
        generation for comprehensive cogeneration analysis.
        """
        # Calculate thermal storage capacity based on water storage
        speicher_kapazitaet = (self.Speicher_Volumen_BHKW * 4186 * 
                              (self.T_vorlauf - self.T_ruecklauf) / 3600)  # kWh
        
        # Initialize storage state and operational limits
        speicher_fill = self.initial_fill * speicher_kapazitaet
        min_speicher_fill = self.min_fill * speicher_kapazitaet
        max_speicher_fill = self.max_fill * speicher_kapazitaet

        # Initialize storage-related arrays
        self.Wärmeleistung_Speicher_kW = np.zeros_like(Last_L)
        self.Speicher_Fuellstand = np.zeros_like(Last_L)

        # Simulate hourly storage and cogeneration operation
        for i in range(len(Last_L)):
            if self.active:
                # Check if storage is full
                if speicher_fill >= max_speicher_fill:
                    self.active = False
                else:
                    # Operate CHP at nominal capacity for optimal efficiency
                    self.Wärmeleistung_kW[i] = self.th_Leistung_kW
                    
                    # Manage storage charging/discharging
                    if Last_L[i] < self.th_Leistung_kW:
                        # Charge storage with excess heat
                        self.Wärmeleistung_Speicher_kW[i] = Last_L[i] - self.th_Leistung_kW
                        speicher_fill += (self.th_Leistung_kW - Last_L[i]) * duration
                        speicher_fill = float(min(speicher_fill, speicher_kapazitaet))
                    else:
                        # No storage charging when load exceeds CHP capacity
                        self.Wärmeleistung_Speicher_kW[i] = 0
            else:
                # Check if storage needs recharging
                if speicher_fill <= min_speicher_fill:
                    self.active = True
            
            # Storage discharge mode when CHP inactive
            if not self.active:
                self.Wärmeleistung_kW[i] = 0
                self.Wärmeleistung_Speicher_kW[i] = Last_L[i]
                speicher_fill -= Last_L[i] * duration
                speicher_fill = float(max(speicher_fill, 0))

            # Calculate electrical output based on thermal output
            self.el_Leistung_kW[i] = (self.Wärmeleistung_kW[i] / 
                                     self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad)
            
            # Update storage fill level percentage
            self.Speicher_Fuellstand[i] = speicher_fill / speicher_kapazitaet * 100  # %

        # Update operational mask based on CHP operation
        self.betrieb_mask = self.Wärmeleistung_kW > 0

    def generate(self, t: int, **kwargs) -> Tuple[float, float]:
        """
        Generate heat and electricity output for specified time step.

        This method provides instantaneous cogeneration for real-time simulation
        or control system integration, considering the current operational state
        and maintaining the fixed heat-to-power ratio characteristics of the
        CHP technology.

        Parameters
        ----------
        t : int
            Current time step index.
        **kwargs
            Additional parameters for cogeneration control.

        Returns
        -------
        tuple of (float, float)
            Cogeneration outputs:
            
            heat_output : float
                Instantaneous thermal power output [kW].
            electricity_output : float
                Instantaneous electrical power output [kW].

        Notes
        -----
        Real-Time Cogeneration:
            
            **Control Integration**:
            - Interfaces with system control strategies
            - Responds to external heat-led control signals
            - Maintains operational constraints and efficiency
            
            **Simultaneous Generation**:
            - Heat output at nominal capacity when active
            - Electricity output based on efficiency ratio
            - Fixed heat-to-power ratio maintenance
            - Zero output when system inactive
            
            **State Management**:
            - Updates operational arrays for time step
            - Maintains consistency with simulation results
            - Supports both simulation and real-time operation

        This method is typically used within larger district heating
        simulations or for real-time cogeneration control integration.
        """
        if self.active:
            self.betrieb_mask[t] = True
            self.Wärmeleistung_kW[t] = self.th_Leistung_kW
            self.el_Leistung_kW[t] = (self.th_Leistung_kW / 
                                     self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad)
        else:
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0
            self.el_Leistung_kW[t] = 0

        return self.Wärmeleistung_kW[t], self.el_Leistung_kW[t]
    
    def calculate_results(self, duration: float) -> None:
        """
        Calculate operational performance metrics from cogeneration simulation.

        Parameters
        ----------
        duration : float
            Time step duration [hours] for energy calculations.
        """
        # Calculate annual energy generation
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Strommenge_MWh = np.sum(self.el_Leistung_kW / 1000) * duration

        # Calculate fuel consumption based on combined efficiency
        self.Brennstoffbedarf_MWh = (self.Wärmemenge_MWh + self.Strommenge_MWh) / self.KWK_Wirkungsgrad

        # Analyze start-stop cycles and operational hours
        starts = np.diff(self.betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(self.betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = (self.Betriebsstunden / self.Anzahl_Starts 
                                         if self.Anzahl_Starts > 0 else 0)
    
    def calculate_heat_generation_costs(self, economic_parameters: Dict) -> float:
        """
        Calculate comprehensive heat generation costs for CHP systems.

        This method performs detailed economic analysis of the CHP system
        including investment costs, operational expenses, electricity revenue,
        and subsidy calculations according to German KWKG and BEW funding
        guidelines for cogeneration systems.

        Parameters
        ----------
        economic_parameters : dict
            Dictionary containing economic parameters:
            
            - electricity_price : float
                Electricity sales price [€/kWh]
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
            Net heat generation cost [€/MWh].
            Levelized cost of heat after electricity revenue offset.

        Notes
        -----
        Cogeneration Economics:
            
            **Investment Costs**:
            - Gas CHP: ~1500 €/kW thermal capacity
            - Wood Gas CHP: ~1850 €/kW thermal capacity
            - Thermal storage: Volume-based costs [€/m³]
            - Higher installation factors due to complexity
            
            **Revenue Streams**:
            - Heat sales: Primary revenue from district heating
            - Electricity sales: Market price or feed-in tariff
            - KWKG bonus: Cogeneration promotion payments
            - BEW subsidies: Investment cost support
            
            **Economic Optimization**:
            - Electricity revenue reduces net heat costs
            - Higher CHP utilization improves economics
            - Storage integration enhances revenue potential
            - Technology choice affects cost structure
            
            **Subsidy Integration**:
            KWKG (Kraft-Wärme-Kopplungsgesetz) support:
            - Bonus payments for cogenerated electricity
            - Enhanced support for high-efficiency CHP
            BEW (Bundesförderung für effiziente Wärmenetze):
            - Up to 40% investment cost coverage
            - Combined subsidy optimization

        The calculation provides net heat generation costs after
        electricity revenue offset for cogeneration optimization.
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
            self.WGK = 0
            return 0
        
        # Determine technology-specific costs and fuel prices
        if self.name.startswith("BHKW"):
            spez_Investitionskosten_BHKW = self.spez_Investitionskosten_GBHKW  # €/kW
            self.Brennstoffpreis = self.Gaspreis
        elif self.name.startswith("Holzgas-BHKW"):
            spez_Investitionskosten_BHKW = self.spez_Investitionskosten_HBHKW  # €/kW
            self.Brennstoffpreis = self.Holzpreis

        # Calculate component investment costs
        self.Investitionskosten_BHKW = spez_Investitionskosten_BHKW * self.th_Leistung_kW
        self.Investitionskosten_Speicher = (self.spez_Investitionskosten_Speicher * 
                                           self.Speicher_Volumen_BHKW)
        self.Investitionskosten = self.Investitionskosten_BHKW + self.Investitionskosten_Speicher

        # Calculate electricity revenue
        self.Stromeinnahmen = self.Strommenge_MWh * self.Strompreis

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
            energy_cost_per_unit=self.Brennstoffpreis,
            annual_revenue=self.Stromeinnahmen,
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
            energy_cost_per_unit=self.Brennstoffpreis,
            annual_revenue=self.Stromeinnahmen,
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
        Calculate environmental impact metrics for the CHP system.

        This method assesses the environmental performance of the cogeneration
        system including CO2 emissions from fuel consumption, CO2 savings from
        electricity grid displacement, and net environmental impact for
        comprehensive sustainability analysis.

        Notes
        -----
        Environmental Assessment:
            
            **CO2 Balance Analysis**:
            - Direct emissions: Fuel combustion in CHP engine
            - Avoided emissions: Electricity grid displacement
            - Net impact: Direct emissions minus avoided emissions
            - System-specific factors by fuel type
            
            **Fuel-Specific Emissions**:
            - Gas CHP: 0.201 tCO2/MWh fuel (natural gas)
            - Wood Gas CHP: 0.036 tCO2/MWh fuel (biomass)
            - Grid electricity: 0.4 tCO2/MWh displaced
            
            **Primary Energy Analysis**:
            - Gas CHP: 1.1 primary energy factor
            - Wood Gas CHP: 0.2 primary energy factor (renewable)
            - Cogeneration efficiency benefits
            - Total primary energy consumption
            
            **Cogeneration Benefits**:
            - Higher overall efficiency than separate generation
            - Reduced total fuel consumption
            - Grid electricity displacement
            - Renewable energy integration (biomass CHP)

        The analysis supports sustainability reporting and environmental
        optimization for cogeneration in district heating systems.
        """
        # Calculate CO2 emissions from fuel consumption
        self.co2_emissions = self.Brennstoffbedarf_MWh * self.co2_factor_fuel  # tCO2
        
        # Calculate CO2 savings from electricity generation (grid displacement)
        self.co2_savings = self.Strommenge_MWh * self.co2_factor_electricity  # tCO2
        
        # Calculate net CO2 impact (can be negative for high electricity generation)
        self.co2_total = self.co2_emissions - self.co2_savings  # tCO2
        
        # Calculate specific CO2 emissions per unit heat generated
        self.spec_co2_total = (self.co2_total / self.Wärmemenge_MWh 
                              if self.Wärmemenge_MWh > 0 else 0)  # tCO2/MWh_heat

        # Calculate primary energy consumption
        self.primärenergie = self.Brennstoffbedarf_MWh * self.primärenergiefaktor
    
    def calculate(self, economic_parameters: Dict, duration: float, 
                 load_profile: np.ndarray, **kwargs) -> Dict:
        """
        Comprehensive CHP system analysis and optimization.

        This method performs complete cogeneration system analysis including
        thermal and electrical simulation, economic evaluation with electricity
        revenue, and environmental assessment for CHP systems in district
        heating applications.

        Parameters
        ----------
        economic_parameters : dict
            Economic analysis parameters including costs, rates, and electricity pricing.
        duration : float
            Simulation time step duration [hours].
        load_profile : numpy.ndarray
            Annual hourly thermal load profile [kW].
        **kwargs
            Additional calculation parameters.

        Returns
        -------
        dict
            Comprehensive cogeneration results dictionary containing:
            
            - tech_name : str
                Technology identifier
            - Wärmemenge : float
                Annual heat generation [MWh]
            - Wärmeleistung_L : numpy.ndarray
                Hourly heat output profile [kW]
            - Brennstoffbedarf : float
                Annual fuel consumption [MWh]
            - WGK : float
                Net heat generation cost [€/MWh]
            - Strommenge : float
                Annual electricity generation [MWh]
            - el_Leistung_L : numpy.ndarray
                Hourly electricity output profile [kW]
            - Anzahl_Starts : int
                Number of start-stop cycles
            - Betriebsstunden : float
                Annual operating hours [h]
            - Betriebsstunden_pro_Start : float
                Average operating hours per start [h]
            - spec_co2_total : float
                Net specific CO2 emissions [tCO2/MWh]
            - primärenergie : float
                Primary energy consumption [MWh]
            - color : str
                Visualization color identifier ("yellow" for CHP)
            - Wärmeleistung_Speicher_L : numpy.ndarray, optional
                Storage heat exchange profile [kW] (if storage active)
            - Speicherfüllstand_L : numpy.ndarray, optional
                Storage fill level profile [%] (if storage active)

        Notes
        -----
        Analysis Workflow:
            
            **1. Cogeneration Simulation**:
            - Storage or non-storage operation simulation
            - Heat-led operation with electricity co-generation
            - Operational constraint enforcement
            
            **2. Performance Calculation**:
            - Heat and electricity energy balance
            - Fuel consumption based on combined efficiency
            - Start-stop cycle and capacity factor analysis
            
            **3. Economic Analysis**:
            - Investment and operational cost calculation
            - Electricity revenue calculation and offset
            - KWKG and BEW subsidy integration
            - Net heat generation cost determination
            
            **4. Environmental Assessment**:
            - CO2 emission and savings calculation
            - Net environmental impact analysis
            - Primary energy consumption assessment

        The comprehensive analysis supports cogeneration optimization,
        economic feasibility assessment with electricity revenue, and
        environmental impact evaluation for district heating integration.
        """
        # Perform cogeneration simulation if not already calculated
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

        # Compile comprehensive cogeneration results
        results = {
            'tech_name': self.name,
            'Wärmemenge': self.Wärmemenge_MWh,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'Brennstoffbedarf': self.Brennstoffbedarf_MWh,
            'WGK': WGK,
            'Strommenge': self.Strommenge_MWh,
            'el_Leistung_L': self.el_Leistung_kW,
            'Anzahl_Starts': self.Anzahl_Starts,
            'Betriebsstunden': self.Betriebsstunden,
            'Betriebsstunden_pro_Start': self.Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            'color': "yellow"  # Yellow color for cogeneration systems
        }

        # Add storage-specific results if thermal storage is active
        if self.speicher_aktiv:
            results['Wärmeleistung_Speicher_L'] = self.Wärmeleistung_Speicher_kW
            results['Speicherfüllstand_L'] = self.Speicher_Fuellstand

        return results
    
    def set_parameters(self, variables: List[float], variables_order: List[str], idx: int) -> None:
        """
        Set optimization parameters for the CHP system.

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
            self.th_Leistung_kW = variables[variables_order.index(f"th_Leistung_kW_{idx}")]
            if self.speicher_aktiv:
                self.Speicher_Volumen_BHKW = variables[variables_order.index(f"Speicher_Volumen_BHKW_{idx}")]
        except ValueError as e:
            print(f"Fehler beim Setzen der Parameter für {self.name}: {e}")

    def add_optimization_parameters(self, idx: int) -> Tuple[List[float], List[str], List[Tuple[float, float]]]:
        """
        Define optimization parameters for CHP system sizing.

        This method sets up optimization variables, bounds, and initial values
        for cogeneration system capacity optimization in district heating
        applications with consideration of heat-to-power ratios.

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
            
            **CHP Thermal Capacity**:
            - Variable: th_Leistung_kW_{idx} [kW]
            - Bounds: [opt_BHKW_min, opt_BHKW_max]
            - Determines both heat and electricity capacity
            
            **Storage Volume** (if storage active):
            - Variable: Speicher_Volumen_BHKW_{idx} [m³]
            - Bounds: [opt_BHKW_Speicher_min, opt_BHKW_Speicher_max]
            - Optimization target: Optimal storage size for cogeneration

        The optimization setup supports multi-objective optimization
        including cost minimization, efficiency maximization, electricity
        revenue optimization, and environmental impact reduction.
        """
        # Initialize with CHP thermal capacity optimization
        initial_values = [self.th_Leistung_kW]
        variables_order = [f"th_Leistung_kW_{idx}"]
        bounds = [(self.opt_BHKW_min, self.opt_BHKW_max)]

        # Add storage optimization if thermal storage is active
        if self.speicher_aktiv:
            initial_values.append(self.Speicher_Volumen_BHKW)
            variables_order.append(f"Speicher_Volumen_BHKW_{idx}")
            bounds.append((self.opt_BHKW_Speicher_min, self.opt_BHKW_Speicher_max))

        return initial_values, variables_order, bounds
    
    def get_display_text(self) -> str:
        """
        Generate display text for GUI representation.

        Returns
        -------
        str
            Formatted text describing CHP system configuration.
        """
        if self.name.startswith("BHKW"):
            return (f"{self.name}: th. Leistung: {self.th_Leistung_kW:.1f} kW, "
                    f"spez. Investitionskosten Erdgas-BHKW: {self.spez_Investitionskosten_GBHKW:.1f} €/kW")
        elif self.name.startswith("Holzgas-BHKW"):
            return (f"{self.name}: th. Leistung: {self.th_Leistung_kW:.1f} kW, "
                    f"spez. Investitionskosten Holzgas-BHKW: {self.spez_Investitionskosten_HBHKW:.1f} €/kW")
        
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
                Technical specifications including heat and electricity capacity
            costs : str
                Investment cost information
            full_costs : str
                Total investment costs
        """
        dimensions = f"th. Leistung: {self.th_Leistung_kW:.1f} kW, el. Leistung: {self.el_Leistung_Soll:.1f} kW"
        costs = f"Investitionskosten: {self.Investitionskosten:.1f}"
        full_costs = f"{self.Investitionskosten:.1f}"
        return self.name, dimensions, costs, full_costs

class CHPStrategy(BaseStrategy):
    """
    Advanced control strategy for CHP systems with thermal storage.

    This class implements temperature-based control strategies for optimal
    CHP operation including storage management, cogeneration optimization,
    and demand-responsive operation for district heating systems with
    focus on maximizing electricity generation revenue.

    Parameters
    ----------
    charge_on : float
        Upper storage temperature threshold to activate CHP [°C].
        Storage temperature above which CHP starts for charging.
    charge_off : float
        Lower storage temperature threshold to deactivate CHP [°C].
        Storage temperature below which CHP stops charging.

    Notes
    -----
    Control Strategy Features:
        
        **Temperature-Based Control**:
        - Hysteresis control prevents frequent switching
        - Storage temperature monitoring for optimal operation
        - Heat-led operation with electricity co-generation
        
        **Cogeneration Optimization**:
        - Extended CHP runtime for electricity revenue
        - Optimal capacity utilization through storage buffering
        - Minimized start-stop cycles for efficiency
        
        **Economic Operation**:
        - Storage charging during low heat demand
        - Electricity generation maximization
        - Grid interaction optimization
        - Revenue enhancement through optimal scheduling

    The control strategy ensures optimal CHP operation while maximizing
    both heat supply reliability and electricity generation revenue.

    Examples
    --------
    >>> # Create control strategy for storage-integrated CHP
    >>> strategy = CHPStrategy(
    ...     charge_on=75,   # Start CHP at 75°C storage temperature
    ...     charge_off=70   # Stop CHP at 70°C storage temperature
    ... )
    >>> 
    >>> # Apply strategy to CHP system
    >>> chp = CHP(
    ...     name="BHKW_Controlled",
    ...     th_Leistung_kW=300.0,
    ...     speicher_aktiv=True
    ... )
    >>> chp.strategy = strategy

    See Also
    --------
    BaseStrategy : Base class for heat generator control strategies
    CHP : Combined heat and power system implementation
    """
    
    def __init__(self, charge_on: float, charge_off: float):
        """
        Initialize CHP control strategy with temperature setpoints.

        Parameters
        ----------
        charge_on : float
            Upper storage temperature to activate CHP [°C].
        charge_off : float
            Lower storage temperature to deactivate CHP [°C].
        """
        super().__init__(charge_on, charge_off)