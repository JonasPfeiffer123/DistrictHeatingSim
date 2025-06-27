"""
Gas Boiler System Module
========================

This module provides comprehensive gas-fired boiler system modeling capabilities
for district heating applications.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11

The implementation includes detailed thermal
modeling, economic analysis, and environmental impact assessment for natural
gas-fired heating systems with focus on efficiency optimization and cost-effective
heat generation.

The module supports both standalone boiler operation and integration with other
heat generation technologies in multi-technology district heating systems.

Features
--------
- Comprehensive gas boiler modeling with efficiency calculations
- Economic analysis including fuel cost optimization
- Environmental impact assessment for natural gas combustion
- Simple and reliable operation for baseload heat generation
- Integration capabilities with district heating control systems

Technical Specifications
------------------------
**Gas Boiler Modeling**:
- Thermal capacity sizing from residential to industrial scale
- Efficiency modeling with Nutzungsgrad (utilization factor) calculations
- Simple load-following operation without minimum load constraints
- Fuel consumption calculations based on natural gas combustion
- Reliable heat generation for district heating baseload

**Economic Analysis**:
- Comprehensive cost modeling including capital and operational costs
- Natural gas fuel cost calculations with price escalation
- Simple investment cost structure with low capital requirements
- Annuity-based economic evaluation for lifecycle assessment
- Heat generation cost calculations (Wärmegestehungskosten)

**Environmental Assessment**:
- CO2 emission calculations for natural gas combustion
- Primary energy factor analysis for fossil fuel consumption
- Environmental impact metrics for sustainability reporting

Classes
-------
GasBoiler : Main gas boiler system class
GasBoilerStrategy : Control strategy for gas boiler operation

Dependencies
------------
- numpy >= 1.20.0 : Numerical calculations and array operations
- districtheatingsim.heat_generators.base_heat_generator : Base classes for heat generators

Applications
------------
The module supports gas boiler applications including:
- District heating backup and peak load systems
- Baseload heat generation for smaller networks
- Backup systems for renewable energy integration
- Cost-effective heat generation for transition periods

References
----------
Gas boiler modeling based on:
- DIN EN 15459 energy performance of heating systems
- VDI 2067 economic efficiency calculations
- German energy regulations and efficiency standards
"""

import numpy as np
from typing import Dict, Tuple, List, Optional, Union

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy

class GasBoiler(BaseHeatGenerator):
    """
    Comprehensive gas-fired boiler system for district heating applications.

    This class models natural gas-fired heating systems for district heating
    applications with focus on economic efficiency, reliability, and simple
    operation. The implementation provides detailed performance modeling,
    economic analysis, and environmental impact assessment for conventional
    gas boiler technology.

    The gas boiler model includes simple load-following operation, economic
    optimization, and integration capabilities for multi-technology heating
    systems in district heating networks.

    Parameters
    ----------
    name : str
        Unique identifier for the gas boiler system.
        Used for system identification and result tracking.
    thermal_capacity_kW : float
        Nominal thermal power output of the gas boiler [kW].
        Determines maximum heat generation capacity under rated conditions.
    spez_Investitionskosten : float, optional
        Specific investment costs for boiler equipment [€/kW].
        Capital cost per unit thermal capacity (default: 30 €/kW).
    Nutzungsgrad : float, optional
        Boiler thermal efficiency (utilization factor) [-].
        Ratio of useful heat output to fuel energy input (default: 0.9).
    active : bool, optional
        Initial operational state of the boiler system.
        Starting condition for simulation (default: True).

    Attributes
    ----------
    thermal_capacity_kW : float
        Nominal thermal power output [kW]
    spez_Investitionskosten : float
        Specific investment costs [€/kW]
    Nutzungsgrad : float
        Boiler thermal efficiency [-]
    active : bool
        Current operational state
    Nutzungsdauer : int
        System operational lifespan [years]
    f_Inst : float
        Installation factor [-]
    f_W_Insp : float
        Maintenance and inspection factor [-]
    Bedienaufwand : float
        Operational effort [hours/year]
    co2_factor_fuel : float
        CO2 emission factor for natural gas [tCO2/MWh]
    primärenergiefaktor : float
        Primary energy factor for natural gas [-]
    strategy : GasBoilerStrategy
        Control strategy for boiler operation

    Notes
    -----
    Gas Boiler Technology:
        
        **Thermal Performance**:
        The gas boiler model provides:
        - High efficiency natural gas combustion (typically 90%+)
        - Simple load-following operation without complex controls
        - Reliable heat generation for district heating applications
        - Fast response time for demand changes
        - Proven technology with low maintenance requirements
        
        **Operational Characteristics**:
        - Direct load-following without minimum load constraints
        - High reliability and availability (>95% typical)
        - Simple control systems and operation
        - Low operational complexity compared to renewable systems
        - Suitable for baseload and backup applications
        
        **Economic Advantages**:
        - Low capital investment costs (~30 €/kW)
        - Simple installation and commissioning
        - Low maintenance requirements
        - Established supply chains and service networks

    Economic Modeling:
        
        **Investment Costs**:
        - Boiler equipment: Low specific costs due to mature technology
        - Installation: Simple installation with standard connections
        - Commissioning: Straightforward startup procedures
        - Integration: Easy integration with existing heating systems
        
        **Operational Costs**:
        - Fuel costs: Natural gas price dependency
        - Maintenance: Low maintenance due to simple technology
        - Service: Established service networks
        - Operational labor: Minimal due to automated operation
        
        **Economic Characteristics**:
        - Low capital costs enable economic competitiveness
        - Fuel cost sensitivity to natural gas market prices
        - Suitable for backup and peak load applications
        - Economic hedge against renewable energy intermittency

    Environmental Impact:
        
        **CO2 Emissions**:
        - Natural gas CO2 factor: 0.201 tCO2/MWh fuel
        - Moderate emissions compared to renewable alternatives
        - Lower emissions than oil or coal heating systems
        - Transition technology for decarbonization pathways
        
        **Primary Energy**:
        - Primary energy factor: 1.1 for natural gas
        - Fossil fuel dependency consideration
        - Energy security through established gas infrastructure
        - Bridge technology for renewable energy transition

    Examples
    --------
    >>> # Create basic gas boiler system
    >>> gas_boiler = GasBoiler(
    ...     name="Gas_Boiler_Backup",
    ...     thermal_capacity_kW=200.0,
    ...     spez_Investitionskosten=35.0,  # €/kW
    ...     Nutzungsgrad=0.92              # 92% efficiency
    ... )
    >>> 
    >>> print(f"Boiler capacity: {gas_boiler.thermal_capacity_kW} kW")
    >>> print(f"Efficiency: {gas_boiler.Nutzungsgrad:.1%}")
    >>> print(f"Investment costs: {gas_boiler.spez_Investitionskosten} €/kW")

    >>> # Simulate annual operation for backup system
    >>> import numpy as np
    >>> annual_hours = 8760
    >>> 
    >>> # Peak load profile (backup operation)
    >>> peak_hours = 500  # 500 hours peak operation per year
    >>> load_profile = np.zeros(annual_hours)
    >>> peak_indices = np.random.choice(annual_hours, peak_hours, replace=False)
    >>> load_profile[peak_indices] = np.random.uniform(150, 200, peak_hours)
    >>> 
    >>> # Economic parameters for gas boiler analysis
    >>> economic_params = {
    ...     'electricity_price': 0.25,     # €/kWh
    ...     'gas_price': 0.08,             # €/kWh natural gas
    ...     'wood_price': 0.05,            # €/kWh (not used for gas boiler)
    ...     'capital_interest_rate': 0.04,  # 4% interest
    ...     'inflation_rate': 0.02,        # 2% inflation
    ...     'time_period': 20,             # 20-year analysis
    ...     'subsidy_eligibility': "Nein", # No subsidies for gas
    ...     'hourly_rate': 40.0            # €/hour labor cost
    ... }
    >>> 
    >>> # Calculate gas boiler performance and economics
    >>> results = gas_boiler.calculate(
    ...     economic_parameters=economic_params,
    ...     duration=1.0,  # 1-hour time steps
    ...     load_profile=load_profile
    ... )
    >>> 
    >>> print(f"Annual heat generation: {results['Wärmemenge']:.1f} MWh")
    >>> print(f"Fuel consumption: {results['Brennstoffbedarf']:.1f} MWh")
    >>> print(f"Heat generation cost: {results['WGK']:.2f} €/MWh")
    >>> print(f"Operating hours: {results['Betriebsstunden']:.0f} h/year")
    >>> print(f"CO2 emissions: {results['spec_co2_total']:.3f} tCO2/MWh")

    >>> # Compare with renewable alternative
    >>> renewable_co2 = 0.036  # tCO2/MWh for biomass
    >>> co2_difference = results['spec_co2_total'] - renewable_co2
    >>> print(f"Additional CO2 vs. biomass: {co2_difference:.3f} tCO2/MWh")

    >>> # Economic analysis for backup system
    >>> capacity_factor = results['Betriebsstunden'] / 8760
    >>> print(f"Capacity factor: {capacity_factor:.1%}")
    >>> 
    >>> # Backup system economics
    >>> annual_fixed_costs = gas_boiler.Investitionskosten * 0.1  # 10% of investment
    >>> annual_variable_costs = results['Brennstoffbedarf'] * economic_params['gas_price'] * 1000
    >>> total_annual_costs = annual_fixed_costs + annual_variable_costs
    >>> print(f"Annual fixed costs: {annual_fixed_costs:.0f} €")
    >>> print(f"Annual variable costs: {annual_variable_costs:.0f} €")
    >>> print(f"Total annual costs: {total_annual_costs:.0f} €")

    >>> # Integration with renewable energy system
    >>> # Gas boiler as backup for renewable energy intermittency
    >>> renewable_capacity_kW = 300.0  # Primary renewable system
    >>> backup_sizing_factor = 0.7     # 70% backup capacity
    >>> 
    >>> backup_boiler = GasBoiler(
    ...     name="Renewable_Backup",
    ...     thermal_capacity_kW=renewable_capacity_kW * backup_sizing_factor,
    ...     spez_Investitionskosten=30.0,
    ...     Nutzungsgrad=0.90
    ... )
    >>> 
    >>> print(f"Primary renewable capacity: {renewable_capacity_kW} kW")
    >>> print(f"Backup gas capacity: {backup_boiler.thermal_capacity_kW} kW")
    >>> print(f"Backup ratio: {backup_sizing_factor:.1%}")

    >>> # Environmental impact assessment
    >>> backup_boiler.calculate_environmental_impact()
    >>> 
    >>> # Carbon footprint analysis
    >>> if results['Wärmemenge'] > 0:
    ...     annual_co2_emissions = results['Wärmemenge'] * results['spec_co2_total']
    ...     print(f"Annual CO2 emissions: {annual_co2_emissions:.1f} tCO2")
    ...     
    ...     # Cost of carbon consideration
    ...     carbon_price = 50  # €/tCO2
    ...     carbon_cost = annual_co2_emissions * carbon_price
    ...     print(f"Carbon cost (50 €/tCO2): {carbon_cost:.0f} €/year")

    See Also
    --------
    BaseHeatGenerator : Base class for heat generation systems
    GasBoilerStrategy : Control strategy for gas boiler operation
    """

    def __init__(self, name: str, thermal_capacity_kW: float, spez_Investitionskosten: float = 30, 
                 Nutzungsgrad: float = 0.9, active: bool = True):
        """
        Initialize the gas boiler system with thermal and economic parameters.

        Parameters
        ----------
        name : str
            Unique identifier for the gas boiler system.
        thermal_capacity_kW : float
            Nominal thermal power output [kW].
        spez_Investitionskosten : float, optional
            Specific investment costs [€/kW] (default: 30).
        Nutzungsgrad : float, optional
            Boiler thermal efficiency [-] (default: 0.9).
        active : bool, optional
            Initial operational state (default: True).
        """
        super().__init__(name)
        self.thermal_capacity_kW = thermal_capacity_kW
        self.spez_Investitionskosten = spez_Investitionskosten
        self.Nutzungsgrad = Nutzungsgrad
        self.active = active
        
        # System specifications based on gas boiler standards
        self.Nutzungsdauer = 20  # Operational lifespan [years]
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 1, 2, 0  # Installation and maintenance factors
        self.co2_factor_fuel = 0.201  # tCO2/MWh for natural gas
        self.primärenergiefaktor = 1.1  # Primary energy factor for natural gas

        # Initialize control strategy
        self.strategy = GasBoilerStrategy(70)

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

    def calculate_operation(self, Last_L: np.ndarray) -> None:
        """
        Simulate gas boiler operation with simple load-following strategy.

        This method models the operational behavior of the gas boiler
        in direct load-following mode, providing reliable heat generation
        whenever heat demand is present without complex operational constraints.

        Parameters
        ----------
        Last_L : numpy.ndarray
            Hourly thermal load profile [kW].
            Heat demand time series for the district heating system.

        Notes
        -----
        Operational Characteristics:
            
            **Load Following**:
            - Direct response to heat demand without minimum load
            - Simple on/off operation based on load presence
            - Heat output matches demand up to nominal capacity
            - High reliability and availability for district heating
            
            **Control Strategy**:
            - Boiler operates whenever heat demand exists
            - No complex control algorithms or constraints
            - Immediate response to demand changes
            - Suitable for backup and peak load applications
            
            **Performance**:
            - Constant efficiency across operational range
            - No part-load efficiency penalties modeled
            - Fast startup and response characteristics
            - High system availability and reliability

        The simulation sets operational flags and heat output arrays
        for subsequent economic and environmental analysis.
        """
        # Operate whenever there is heat demand
        self.betrieb_mask = Last_L > 0
        
        # Calculate heat output limited by boiler capacity
        self.Wärmeleistung_kW[self.betrieb_mask] = np.minimum(
            Last_L[self.betrieb_mask], 
            self.thermal_capacity_kW
        )

    def generate(self, t: int, **kwargs) -> Tuple[float, float]:
        """
        Generate heat output for specified time step.

        This method provides instantaneous heat generation for real-time
        simulation or control system integration, considering the current
        operational state and remaining heat demand in the system.

        Parameters
        ----------
        t : int
            Current time step index.
        **kwargs
            Additional keyword arguments:
            
            remaining_load : float
                Remaining heat demand to be covered [kW].

        Returns
        -------
        tuple of (float, float)
            Heat generation outputs:
            
            heat_output : float
                Instantaneous thermal power output [kW].
            electricity_output : float
                Electrical power output [kW] (always 0 for gas boiler).

        Notes
        -----
        Real-Time Operation:
            
            **Heat Generation**:
            - Provides heat output up to nominal capacity
            - Covers remaining load demand when active
            - Zero output when system inactive
            - No electrical generation for boiler-only systems
            
            **Control Integration**:
            - Interfaces with system control strategies
            - Responds to remaining load requirements
            - Maintains operational state consistency
            - Supports multi-technology system integration
            
            **State Management**:
            - Updates operational arrays for time step
            - Maintains consistency with simulation results
            - Supports both simulation and real-time operation

        This method is typically used within larger district heating
        simulations or for real-time control system integration.
        """
        remaining_load = kwargs.get('remaining_load', 0)

        if self.active:
            self.betrieb_mask[t] = True
            self.Wärmeleistung_kW[t] = min(remaining_load, self.thermal_capacity_kW)
        else:
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0
        
        return self.Wärmeleistung_kW[t], 0  # Heat output, no electricity generation
        
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
        self.Brennstoffbedarf_MWh = self.Wärmemenge_MWh / self.Nutzungsgrad
        
        # Analyze start-stop cycles and operational hours
        starts = np.diff(self.betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(self.betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = (self.Betriebsstunden / self.Anzahl_Starts 
                                         if self.Anzahl_Starts > 0 else 0)

    def calculate_heat_generation_cost(self, economic_parameters: Dict) -> None:
        """
        Calculate comprehensive heat generation costs for the gas boiler system.

        This method performs detailed economic analysis of the gas boiler
        including investment costs, operational expenses, and fuel cost
        calculations for lifecycle cost assessment.

        Parameters
        ----------
        economic_parameters : dict
            Dictionary containing economic parameters:
            
            - electricity_price : float
                Electricity price [€/kWh] (not used for gas boiler)
            - gas_price : float  
                Natural gas price [€/kWh]
            - wood_price : float
                Wood price [€/kWh] (not used for gas boiler)
            - capital_interest_rate : float
                Interest rate for capital costs [-]
            - inflation_rate : float
                Annual inflation rate [-] 
            - time_period : int
                Analysis time period [years]
            - subsidy_eligibility : str
                Subsidy eligibility (typically "Nein" for gas)
            - hourly_rate : float
                Labor cost rate [€/hour]

        Notes
        -----
        Economic Analysis Components:
            
            **Investment Costs**:
            - Boiler equipment: Low specific costs due to mature technology
            - Installation: Simple installation procedures
            - Low complexity compared to renewable technologies
            - Established supply chains reduce costs
            
            **Operational Costs**:
            - Fuel costs: Natural gas consumption based on efficiency
            - Maintenance: Low maintenance due to simple technology  
            - Service: Established service networks
            - Operational effort: Minimal due to automated operation
            
            **Cost Structure**:
            - Low capital costs enable competitive economics
            - High sensitivity to natural gas price fluctuations
            - Suitable for backup and peak load cost optimization
            - Economic hedge for renewable energy intermittency
            
            **Annuity Method**:
            - Capital recovery factor calculation
            - Present value of operational costs
            - Levelized cost of heat generation
            - Inflation and interest rate effects

        The calculation provides comprehensive lifecycle cost analysis
        for gas boiler economic evaluation in district heating systems.
        """
        # Extract economic parameters
        self.Strompreis = economic_parameters['electricity_price']
        self.Gaspreis = economic_parameters['gas_price']
        self.Holzpreis = economic_parameters['wood_price']
        self.q = economic_parameters['capital_interest_rate']
        self.r = economic_parameters['inflation_rate']
        self.T = economic_parameters['time_period']
        self.BEW = economic_parameters['subsidy_eligibility']
        self.hourly_rate = economic_parameters['hourly_rate']

        if self.Wärmemenge_MWh > 0:
            # Calculate investment costs
            self.Investitionskosten = self.spez_Investitionskosten * self.thermal_capacity_kW

            # Calculate annuity including all cost components
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
                energy_cost_per_unit=self.Gaspreis,
                annual_revenue=0,
                hourly_rate=self.hourly_rate
            )
            
            # Calculate heat generation cost
            self.WGK = self.A_N / self.Wärmemenge_MWh
        else:
            # Handle case with no heat generation
            self.Investitionskosten = 0
            self.A_N = 0
            self.WGK = float('inf')

    def calculate_environmental_impact(self) -> None:
        """
        Calculate environmental impact metrics for the gas boiler system.

        This method assesses the environmental performance of the gas-fired
        heating system including CO2 emissions from natural gas combustion
        and primary energy consumption for sustainability analysis.

        Notes
        -----
        Environmental Assessment:
            
            **CO2 Emissions**:
            - Natural gas CO2 factor: 0.201 tCO2/MWh fuel
            - Direct combustion emissions from gas boiler
            - Moderate emissions compared to renewable alternatives
            - Lower emissions than oil or coal heating systems
            
            **Primary Energy**:
            - Primary energy factor: 1.1 for natural gas
            - Fossil fuel dependency consideration
            - Energy security through established infrastructure
            - Bridge technology for renewable energy transition
            
            **Environmental Considerations**:
            - Transition technology for decarbonization
            - Lower impact than other fossil alternatives
            - Backup role supports renewable energy integration
            - Established infrastructure reduces additional impact

        The environmental analysis supports sustainability reporting
        and transition planning for district heating decarbonization.
        """
        # Calculate CO2 emissions from natural gas consumption
        self.co2_emissions = self.Brennstoffbedarf_MWh * self.co2_factor_fuel  # tCO2
        
        # Calculate specific CO2 emissions per unit heat generated
        self.spec_co2_total = (self.co2_emissions / self.Wärmemenge_MWh 
                              if self.Wärmemenge_MWh > 0 else 0)  # tCO2/MWh_heat
        
        # Calculate primary energy consumption
        self.primärenergie = self.Brennstoffbedarf_MWh * self.primärenergiefaktor

    def calculate(self, economic_parameters: Dict, duration: float, 
                 load_profile: np.ndarray, **kwargs) -> Dict:
        """
        Comprehensive gas boiler system analysis.

        This method performs complete system analysis including thermal
        simulation, economic evaluation, and environmental assessment
        for gas boiler systems in district heating applications.

        Parameters
        ----------
        economic_parameters : dict
            Economic analysis parameters including costs and rates.
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

        Notes
        -----
        Analysis Workflow:
            
            **1. Thermal Simulation**:
            - Load-following operation simulation
            - Heat output calculation based on demand
            - Operational constraint evaluation
            
            **2. Performance Calculation**:
            - Energy balance and efficiency analysis
            - Start-stop cycle analysis
            - Capacity factor and utilization metrics
            
            **3. Economic Analysis**:
            - Investment and operational cost calculation
            - Natural gas fuel cost evaluation
            - Levelized cost of heat determination
            
            **4. Environmental Assessment**:
            - CO2 emission calculation
            - Primary energy analysis
            - Environmental impact quantification

        The comprehensive analysis supports gas boiler evaluation,
        economic feasibility assessment, and environmental impact
        analysis for district heating system integration.
        """
        # Perform thermal simulation if not already calculated
        if self.calculated == False:
            self.calculate_operation(load_profile)

        # Calculate performance metrics
        self.calculate_results(duration)
        
        # Perform economic and environmental analysis
        self.calculate_heat_generation_cost(economic_parameters)
        self.calculate_environmental_impact()

        # Compile comprehensive results
        results = {
            'tech_name': self.name,
            'Wärmemenge': self.Wärmemenge_MWh,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'Brennstoffbedarf': self.Brennstoffbedarf_MWh,
            'WGK': self.WGK,
            'Anzahl_Starts': self.Anzahl_Starts,
            'Betriebsstunden': self.Betriebsstunden,
            'Betriebsstunden_pro_Start': self.Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            "color": "saddlebrown"  # Brown color for gas technology
        }

        return results
    
    def set_parameters(self, variables: List[float], variables_order: List[str], idx: int) -> None:
        """
        Set optimization parameters for the gas boiler system.

        Parameters
        ----------
        variables : list of float
            Optimization variable values.
        variables_order : list of str
            Variable names corresponding to values.
        idx : int
            Technology index for parameter identification.
            
        Notes
        -----
        The gas boiler typically has no optimization parameters
        as it serves as a reference technology or backup system
        with fixed capacity determined by other system requirements.
        """
        pass

    def add_optimization_parameters(self, idx: int) -> Tuple[List[float], List[str], List[Tuple[float, float]]]:
        """
        Define optimization parameters for gas boiler system.

        Parameters
        ----------
        idx : int
            Technology index for unique parameter identification.

        Returns
        -------
        tuple of (list, list, list)
            Empty optimization setup:
            
            initial_values : list of float
                Empty list (no optimization variables).
            variables_order : list of str
                Empty list (no variable names).
            bounds : list of tuple
                Empty list (no optimization bounds).

        Notes
        -----
        Gas boilers typically serve as reference technologies or backup
        systems with fixed capacities determined by system requirements
        rather than optimization. They provide:
        
        - Fixed backup capacity for renewable systems
        - Reference technology for economic comparison
        - Peak load coverage with predetermined sizing
        - Simple technology without complex optimization needs
        """
        return [], [], []

    def get_display_text(self) -> str:
        """
        Generate display text for GUI representation.

        Returns
        -------
        str
            Formatted text describing gas boiler configuration.
        """
        return (f"{self.name}: Nennleistung: {self.thermal_capacity_kW:.1f} kW, "
                f"Nutzungsgrad: {self.Nutzungsgrad:.2f}, "
                f"spez. Investitionskosten: {self.spez_Investitionskosten:.1f} €/kW")
    
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
                Cost information
            full_costs : str
                Total investment costs
        """
        dimensions = f"th. Leistung: {self.thermal_capacity_kW:.1f} kW"
        costs = f"Investitionskosten: {self.Investitionskosten:.1f} €"
        full_costs = f"{self.Investitionskosten:.1f}"
        return self.name, dimensions, costs, full_costs

class GasBoilerStrategy(BaseStrategy):
    """
    Control strategy for gas boiler systems in district heating applications.

    This class implements simple temperature-based control strategies for
    gas boiler operation, typically used as backup or peak load systems
    in district heating networks with focus on reliability and simple operation.

    Parameters
    ----------
    charge_on : float
        Storage temperature threshold to activate gas boiler [°C].
        Temperature below which gas boiler starts operation.
    charge_off : float, optional
        Storage temperature threshold to deactivate gas boiler [°C].
        Temperature above which gas boiler stops operation (default: None).

    Notes
    -----
    Control Strategy Features:
        
        **Simple Operation**:
        - Temperature-based activation for backup operation
        - Demand-responsive operation for peak load coverage
        - High reliability through simple control algorithms
        
        **Backup Function**:
        - Activation when other systems cannot meet demand
        - Storage temperature monitoring for system state
        - Immediate response to low storage conditions
        
        **Integration Capabilities**:
        - Coordination with renewable energy systems
        - Multi-technology system integration
        - Priority-based operation in technology mix

    The control strategy ensures reliable backup operation while
    minimizing unnecessary gas consumption through optimal activation.

    Examples
    --------
    >>> # Create control strategy for backup gas boiler
    >>> strategy = GasBoilerStrategy(
    ...     charge_on=70,   # Activate at 70°C storage temperature
    ...     charge_off=80   # Deactivate at 80°C storage temperature
    ... )
    >>> 
    >>> # Apply strategy to gas boiler
    >>> boiler = GasBoiler(
    ...     name="Backup_Gas_Boiler",
    ...     thermal_capacity_kW=150.0
    ... )
    >>> boiler.strategy = strategy

    See Also
    --------
    BaseStrategy : Base class for heat generator control strategies
    GasBoiler : Gas boiler system implementation
    """
    
    def __init__(self, charge_on: float, charge_off: Optional[float] = None):
        """
        Initialize gas boiler control strategy with temperature setpoints.

        Parameters
        ----------
        charge_on : float
            Storage temperature to activate gas boiler [°C].
        charge_off : float, optional
            Storage temperature to deactivate gas boiler [°C].
        """
        super().__init__(charge_on, charge_off)

    def decide_operation(self, current_state: float, upper_storage_temp: float, 
                        lower_storage_temp: float, remaining_demand: float) -> bool:
        """
        Decide gas boiler operation based on storage temperature and demand.

        This method implements the decision logic for gas boiler activation
        based on storage conditions and remaining heat demand, typically
        for backup or peak load operation in district heating systems.

        Parameters
        ----------
        current_state : float
            Current system state (not used in this implementation).
        upper_storage_temp : float
            Current upper storage temperature [°C].
        lower_storage_temp : float
            Current lower storage temperature [°C] (not used).
        remaining_demand : float
            Remaining heat demand to be covered [kW].

        Returns
        -------
        bool
            Operation decision:
            
            True : Gas boiler should be turned on
            False : Gas boiler should remain off

        Notes
        -----
        Decision Logic:
            
            **Activation Conditions**:
            - Storage temperature below activation threshold
            - Remaining heat demand exists in the system
            - Both conditions must be met for operation
            
            **Backup Operation**:
            - Ensures system reliability when other sources insufficient
            - Prevents storage depletion during high demand periods
            - Provides immediate heat generation capacity
            
            **Economic Operation**:
            - Minimizes unnecessary gas consumption
            - Operates only when required by system conditions
            - Supports cost-effective multi-technology operation

        The decision logic ensures reliable backup operation while
        optimizing fuel consumption and operational efficiency.
        """
        # Activate gas boiler if storage temperature is low AND demand exists
        if upper_storage_temp < self.charge_on and remaining_demand > 0:
            return True  # Turn gas boiler on
        else:
            return False  # Keep gas boiler off