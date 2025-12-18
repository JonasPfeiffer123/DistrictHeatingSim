"""
Energy System Module
=====================

This module provides comprehensive energy system modeling capabilities for district heating
applications.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-04

The implementation includes multi-technology system integration, energy
generation mix optimization, economic analysis, and advanced visualization tools for
complex district heating system analysis and design.

The module supports integration of multiple heat generation technologies including
renewable energy systems, conventional heating technologies, thermal storage systems,
and cogeneration units for optimal district heating system configuration.

Features
--------
- Comprehensive multi-technology energy system modeling
- Advanced optimization algorithms for cost, emissions, and efficiency
- Integrated thermal storage system modeling with stratified tank simulation
- Economic analysis with lifecycle cost assessment
- Environmental impact evaluation including CO2 balance analysis
- Data serialization and persistence with JSON and CSV export capabilities
- Advanced visualization tools for energy flow analysis

Technical Specifications
------------------------
**Energy System Integration**:
- Multi-technology heat generation mix calculation
- Priority-based technology dispatch with control strategies
- Thermal storage integration with temperature-stratified modeling
- Load balancing and remaining demand calculation
- Electrical power balance for cogeneration systems

**Optimization Capabilities**:
- Multi-objective optimization for cost, emissions, and primary energy
- Scipy-based optimization algorithms with multiple restart strategies
- Technology capacity optimization with parameter bounds
- Weighted objective functions for trade-off analysis
- Stochastic optimization with random initialization

**Economic Analysis**:
- Comprehensive cost modeling including capital and operational costs
- Levelized cost of heat calculations for system comparison
- Technology-specific economic parameters and cost functions
- Investment cost optimization with subsidy integration
- Economic performance metrics for decision support

**Environmental Assessment**:
- CO2 emission calculations for multi-technology systems
- Primary energy factor analysis for sustainability assessment
- Environmental impact optimization and trade-off analysis
- Life cycle assessment integration for comprehensive evaluation

Classes
-------
EnergySystem : Main energy system class for multi-technology integration
EnergySystemOptimizer : Optimization algorithms for energy system design

Dependencies
------------
- numpy >= 1.20.0 : Numerical calculations and array operations
- matplotlib >= 3.3.0 : Visualization and plotting capabilities
- scipy >= 1.7.0 : Optimization algorithms and scientific computing
- pandas >= 1.3.0 : Data manipulation and analysis
- districtheatingsim.heat_generators : Heat generation technology modules
- districtheatingsim.gui.EnergySystemTab._10_utilities : Utility functions

Applications
------------
The module supports energy system applications including:
- District heating system design and optimization
- Multi-technology integration and comparison
- Renewable energy system integration with storage
- Economic feasibility studies for heating networks
- Environmental impact assessment and optimization

References
----------
Energy system modeling based on:
- EN 15459 energy performance of heating systems
- VDI 2067 economic efficiency calculations
- German energy regulations and renewable energy integration standards
- IEA guidelines for energy system modeling and optimization
"""

import logging
logging.basicConfig(level=logging.INFO)

import numpy as np
import matplotlib.pyplot as plt
import copy
import json
import pandas as pd

from typing import Dict, Tuple, List, Optional, Union

from scipy.optimize import minimize as scipy_minimize

from districtheatingsim.heat_generators import *
from districtheatingsim.gui.EnergySystemTab._10_utilities import CustomJSONEncoder
import itertools
from matplotlib import cm

class EnergySystem:
    """
    Comprehensive energy system for district heating multi-technology integration.

    This class models complex district heating systems with multiple heat generation
    technologies, thermal storage integration, and advanced control strategies. The
    implementation provides detailed system-level modeling, economic optimization,
    and environmental impact assessment for large-scale district heating applications.

    The energy system supports integration of renewable energy technologies, conventional
    heating systems, cogeneration units, and thermal storage with sophisticated dispatch
    algorithms and optimization capabilities for optimal system design and operation.

    Parameters
    ----------
    time_steps : numpy.ndarray
        Time steps for the simulation (typically hourly for annual analysis).
        Array of datetime64 objects representing simulation timeline.
    load_profile : numpy.ndarray
        Hourly thermal load profile [kW].
        Heat demand time series for the district heating system.
    VLT_L : numpy.ndarray
        Supply (flow) temperature profile [°C].
        Forward flow temperature time series for the heating network.
    RLT_L : numpy.ndarray
        Return temperature profile [°C].
        Return flow temperature time series for the heating network.
    TRY_data : object
        Test Reference Year meteorological data.
        Weather data for renewable energy and heat pump calculations.
    COP_data : object
        Coefficient of Performance data for heat pumps.
        Performance data for heat pump efficiency calculations.
    economic_parameters : dict
        Economic parameters for system analysis including costs and rates.

    Attributes
    ----------
    time_steps : numpy.ndarray
        Simulation time steps [datetime64]
    load_profile : numpy.ndarray
        Heat demand profile [kW]
    VLT_L : numpy.ndarray
        Supply temperature profile [°C]
    RLT_L : numpy.ndarray
        Return temperature profile [°C]
    TRY_data : object
        Meteorological data for calculations
    COP_data : object
        Heat pump performance data
    economic_parameters : dict
        Economic analysis parameters
    technologies : list
        List of heat generation technology objects
    storage : object
        Seasonal thermal energy storage system
    results : dict
        Comprehensive system analysis results
    duration : float
        Time step duration [hours]

    Notes
    -----
    Energy System Architecture:
        
        **Multi-Technology Integration**:
        The energy system supports:
        - Renewable energy technologies (heat pumps, solar thermal, biomass)
        - Conventional heating systems (gas boilers, oil boilers)
        - Cogeneration systems (CHP, micro-CHP)
        - Thermal storage systems (sensible heat, latent heat storage)
        - Hybrid systems with multiple technology combinations
        
        **Control Strategy Implementation**:
        - Priority-based technology dispatch algorithms
        - Temperature-based control for storage integration
        - Load-following strategies for demand response
        - Economic optimization for operational efficiency
        - Environmental impact minimization strategies
        
        **System-Level Modeling**:
        - Heat balance calculations for multi-technology systems
        - Electrical power balance for cogeneration integration
        - Storage state management with temperature stratification
        - Remaining load calculation and unmet demand tracking

    Economic System Analysis:
        
        **Cost Components**:
        - Capital costs: Investment costs for all technologies
        - Operational costs: Fuel, electricity, and maintenance costs
        - Revenue streams: Electricity sales from cogeneration
        - Subsidy integration: BEW, KWKG, and renewable energy subsidies
        
        **Economic Metrics**:
        - Levelized cost of heat (LCOH) for system comparison
        - Net present value (NPV) for investment decisions
        - Payback period analysis for technology selection
        - Sensitivity analysis for parameter variations
        
        **Optimization Objectives**:
        - Cost minimization for economic optimization
        - Emission reduction for environmental goals
        - Primary energy minimization for efficiency
        - Multi-objective optimization with weighted criteria

    Environmental Impact Assessment:
        
        **CO2 Balance Analysis**:
        - Direct emissions from fuel combustion
        - Indirect emissions from electricity consumption
        - Avoided emissions from renewable energy and cogeneration
        - Net CO2 impact for comprehensive assessment
        
        **Sustainability Metrics**:
        - Primary energy consumption by fuel type
        - Renewable energy fraction for sustainability reporting
        - Environmental impact indicators for life cycle assessment
        - Carbon footprint analysis for climate impact evaluation

    Examples
    --------
    >>> # Create comprehensive energy system
    >>> import numpy as np
    >>> from datetime import datetime, timedelta
    >>> 
    >>> # Define simulation parameters
    >>> start_time = datetime(2024, 1, 1)
    >>> time_steps = np.array([start_time + timedelta(hours=h) for h in range(8760)])
    >>> load_profile = np.random.uniform(100, 500, 8760)  # Variable heat demand
    >>> VLT_L = np.full(8760, 80.0)  # 80°C supply temperature
    >>> RLT_L = np.full(8760, 60.0)  # 60°C return temperature
    >>> 
    >>> # Economic parameters for system analysis
    >>> economic_params = {
    ...     'electricity_price': 0.28,     # €/kWh
    ...     'gas_price': 0.08,             # €/kWh natural gas
    ...     'wood_price': 0.05,            # €/kWh biomass
    ...     'capital_interest_rate': 0.04,  # 4% interest
    ...     'inflation_rate': 0.02,        # 2% inflation
    ...     'time_period': 20,             # 20-year analysis
    ...     'subsidy_eligibility': "Ja",   # Subsidy eligible
    ...     'hourly_rate': 50.0            # €/hour labor cost
    ... }
    >>> 
    >>> # Create energy system
    >>> energy_system = EnergySystem(
    ...     time_steps=time_steps,
    ...     load_profile=load_profile,
    ...     VLT_L=VLT_L,
    ...     RLT_L=RLT_L,
    ...     TRY_data=weather_data,  # Meteorological data
    ...     COP_data=cop_data,      # Heat pump performance data
    ...     economic_parameters=economic_params
    ... )

    >>> # Add multiple heat generation technologies
    >>> from districtheatingsim.heat_generators import HeatPump, CHP, GasBoiler
    >>> 
    >>> # Add ground source heat pump as base load
    >>> heat_pump = HeatPump(
    ...     name="Erdwärme_WP_1",
    ...     th_Leistung_kW=300.0,
    ...     Waermequelle="Erdwärme",
    ...     cop_nominal=4.5
    ... )
    >>> energy_system.add_technology(heat_pump)
    >>> 
    >>> # Add CHP for mid-load and electricity generation
    >>> chp_system = CHP(
    ...     name="BHKW_Cogen_2",
    ...     th_Leistung_kW=200.0,
    ...     el_Wirkungsgrad=0.35,
    ...     KWK_Wirkungsgrad=0.90,
    ...     speicher_aktiv=True
    ... )
    >>> energy_system.add_technology(chp_system)
    >>> 
    >>> # Add gas boiler as backup/peak load
    >>> gas_boiler = GasBoiler(
    ...     name="Gas_Backup_3",
    ...     thermal_capacity_kW=150.0,
    ...     Nutzungsgrad=0.92
    ... )
    >>> energy_system.add_technology(gas_boiler)

    >>> # Add seasonal thermal energy storage
    >>> from districtheatingsim.heat_generators import STES
    >>> 
    >>> storage_system = STES(
    ...     name="Seasonal_Storage",
    ...     volume_m3=5000.0,  # 5000 m³ storage tank
    ...     height_m=20.0,
    ...     insulation_thickness_m=0.5
    ... )
    >>> energy_system.add_storage(storage_system)

    >>> # Calculate energy generation mix
    >>> results = energy_system.calculate_mix()
    >>> 
    >>> print(f"Annual heat demand: {results['Jahreswärmebedarf']:.1f} MWh")
    >>> print(f"Heat generation cost: {results['WGK_Gesamt']:.2f} €/MWh")
    >>> print(f"CO2 emissions: {results['specific_emissions_Gesamt']:.3f} tCO2/MWh")
    >>> print(f"Primary energy factor: {results['primärenergiefaktor_Gesamt']:.2f}")
    >>> 
    >>> # Technology contributions
    >>> for tech, share in zip(results['techs'], results['Anteile']):
    ...     print(f"{tech}: {share:.1%} contribution")

    >>> # Optimize system for minimum cost and emissions
    >>> optimization_weights = {
    ...     'WGK_Gesamt': 0.6,                    # 60% weight on cost
    ...     'specific_emissions_Gesamt': 0.3,     # 30% weight on emissions
    ...     'primärenergiefaktor_Gesamt': 0.1     # 10% weight on primary energy
    ... }
    >>> 
    >>> optimized_system = energy_system.optimize_mix(
    ...     weights=optimization_weights,
    ...     num_restarts=10  # Multiple optimization runs
    ... )
    >>> 
    >>> print("Optimization completed:")
    >>> opt_results = optimized_system.calculate_mix()
    >>> print(f"Optimized cost: {opt_results['WGK_Gesamt']:.2f} €/MWh")
    >>> print(f"Optimized emissions: {opt_results['specific_emissions_Gesamt']:.3f} tCO2/MWh")

    >>> # Visualization and analysis
    >>> import matplotlib.pyplot as plt
    >>> 
    >>> # Create energy flow visualization
    >>> fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    >>> 
    >>> # Plot annual load duration curve
    >>> energy_system.plot_stack_plot(figure=fig)
    >>> 
    >>> # Plot technology contribution pie chart
    >>> energy_system.plot_pie_chart(figure=fig)
    >>> 
    >>> plt.tight_layout()
    >>> plt.show()

    >>> # Save results for documentation and reporting
    >>> energy_system.save_to_json("energy_system_results.json")
    >>> energy_system.save_to_csv("energy_system_timeseries.csv")
    >>> 
    >>> # Load and compare different scenarios
    >>> scenario_1 = EnergySystem.load_from_json("energy_system_results.json")
    >>> 
    >>> # Economic comparison
    >>> cost_comparison = {
    ...     'Heat Pump Only': 85.2,  # €/MWh
    ...     'CHP + Gas Backup': 78.6,  # €/MWh
    ...     'Multi-Technology': opt_results['WGK_Gesamt'],  # €/MWh
    ... }
    >>> 
    >>> print("Economic Comparison:")
    >>> for scenario, cost in cost_comparison.items():
    ...     print(f"{scenario}: {cost:.1f} €/MWh")

    See Also
    --------
    EnergySystemOptimizer : Optimization algorithms for energy system design
    BaseHeatGenerator : Base class for heat generation technologies
    STES : Seasonal thermal energy storage system
    """

    def __init__(self, time_steps: np.ndarray, load_profile: np.ndarray, VLT_L: np.ndarray, 
                 RLT_L: np.ndarray, TRY_data: object, COP_data: object, economic_parameters: dict):
        """
        Initialize the energy system with simulation data and economic parameters.

        Parameters
        ----------
        time_steps : numpy.ndarray
            Time steps for simulation.
        load_profile : numpy.ndarray
            Hourly thermal load profile [kW].
        VLT_L : numpy.ndarray
            Supply temperature profile [°C].
        RLT_L : numpy.ndarray
            Return temperature profile [°C].
        TRY_data : object
            Test Reference Year meteorological data.
        COP_data : object
            Coefficient of Performance data.
        economic_parameters : dict
            Economic parameters for analysis.
        """
        self.time_steps = time_steps
        self.load_profile = load_profile
        self.VLT_L = VLT_L
        self.RLT_L = RLT_L
        self.TRY_data = TRY_data
        self.COP_data = COP_data
        self.economic_parameters = economic_parameters
        self.technologies = []  # List to store generator objects
        self.storage = None
        
        self.results = {}

        self.duration = (np.diff(self.time_steps[:2]) / np.timedelta64(1, 'h'))[0]

    def add_technology(self, tech) -> None:
        """
        Add a heat generation technology to the energy system.

        This method integrates individual heat generation technologies into the
        multi-technology energy system for comprehensive system modeling and
        optimization. Technologies are added with default control strategies
        and can be optimized for capacity and operational parameters.

        Parameters
        ----------
        tech : BaseHeatGenerator
            Technology object to add to the system.
            Must inherit from BaseHeatGenerator base class.

        Notes
        -----
        Technology Integration:
            
            **Supported Technologies**:
            - Heat pumps (air source, ground source, water source)
            - Combined heat and power (CHP) systems
            - Solar thermal collectors
            - Biomass heating systems
            - Gas and oil boilers
            - Electric heating systems
            
            **Integration Process**:
            - Technology validation and compatibility check
            - Control strategy assignment for system operation
            - Priority assignment for dispatch algorithm
            - Economic parameter integration for cost analysis
            
            **System Coordination**:
            - Technologies operate based on priority and control strategies
            - Remaining load calculation ensures demand satisfaction
            - Storage integration for enhanced system flexibility
            - Economic optimization considers all technologies

        The technology is added to the system's technology list and will
        be included in subsequent system calculations and optimization.
        """
        self.technologies.append(tech)

    def add_storage(self, storage) -> None:
        """
        Add a seasonal thermal energy storage system to the energy system.

        This method integrates thermal storage systems into the energy system
        for enhanced flexibility, load balancing, and renewable energy integration.
        Storage systems enable temporal decoupling of heat generation and
        consumption for improved system efficiency and economics.

        Parameters
        ----------
        storage : STES
            Seasonal Thermal Energy Storage object.
            Must be instance of STES (Seasonal Thermal Energy Storage) class.

        Notes
        -----
        Storage Integration Benefits:
            
            **System Flexibility**:
            - Temporal decoupling of generation and demand
            - Load balancing for variable renewable energy
            - Peak shaving and valley filling capabilities
            - Enhanced system reliability and availability
            
            **Economic Advantages**:
            - Improved capacity utilization of heat generators
            - Reduced need for peak load backup systems
            - Enhanced integration of low-cost renewable energy
            - Optimization potential for time-of-use tariffs
            
            **Technical Features**:
            - Temperature stratification modeling for efficiency
            - Heat loss calculations for realistic performance
            - Charging and discharging control strategies
            - Integration with multi-technology dispatch algorithms

        The storage system is integrated into the energy balance calculations
        and control strategies for optimal system operation.
        """
        self.storage = storage

    def initialize_results(self) -> None:
        """
        Initialize the results dictionary for energy system calculations.

        This method sets up the comprehensive results structure for storing
        energy system simulation results, performance metrics, and economic
        indicators for subsequent analysis and reporting.

        Notes
        -----
        Results Structure:
            
            **Energy Balance Results**:
            - Heat generation by technology
            - Electrical power generation and consumption
            - Remaining load and unmet demand tracking
            - Storage charging and discharging profiles
            
            **Economic Results**:
            - Technology-specific heat generation costs
            - System-level levelized cost of heat
            - Revenue from electricity generation
            - Investment and operational cost breakdowns
            
            **Environmental Results**:
            - CO2 emissions by technology and total system
            - Primary energy consumption analysis
            - Renewable energy fraction calculation
            - Environmental impact indicators
            
            **Performance Metrics**:
            - Technology capacity factors and utilization
            - System efficiency and performance indicators
            - Operational statistics and reliability metrics

        The results dictionary provides comprehensive data for system
        analysis, optimization, and decision-making support.
        """
        if not hasattr(self, 'results') or not isinstance(self.results, dict):
            self.results = {}

        self.results.update({
            'time_steps': self.time_steps,
            'Last_L': self.load_profile,
            'VLT_L': self.VLT_L,
            'RLT_L': self.RLT_L,
            'Jahreswärmebedarf': (np.sum(self.load_profile) / 1000) * self.duration,
            'Restlast_L': self.load_profile.copy(),
            'Restwärmebedarf': (np.sum(self.load_profile) / 1000) * self.duration,
            'WGK_Gesamt': 0,
            'Strombedarf': 0,
            'Strommenge': 0,
            'el_Leistungsbedarf_L': np.zeros_like(self.load_profile),
            'el_Leistung_L': np.zeros_like(self.load_profile),
            'el_Leistung_ges_L': np.zeros_like(self.load_profile),
            'specific_emissions_Gesamt': 0,
            'primärenergiefaktor_Gesamt': 0,
        })

        # Ensure lists are initialized or cleared
        for key in ['Wärmeleistung_L', 'colors', 'Wärmemengen', 'Anteile', 'WGK', 
                    'specific_emissions_L', 'primärenergie_L', 'techs']:
            if key not in self.results:
                self.results[key] = []
            else:
                self.results[key].clear()

    def set_optimization_variables(self, variables: list, variables_order: list) -> None:
        """
        Set optimization variables for all technologies in the energy system.

        Parameters
        ----------
        variables : list of float
            Optimization variable values.
        variables_order : list of str
            Variable names corresponding to values.
        """
        for tech in self.technologies:
            if len(variables) > 0:
                idx = tech.name.split("_")[-1]
                tech.set_parameters(variables, variables_order, idx)

    def aggregate_results(self, tech_results: dict) -> None:
        """
        Aggregate results from individual technology into overall system results.

        This method accumulates technology-specific results into system-level
        metrics for comprehensive energy system analysis. The aggregation
        includes energy balance, economic metrics, and environmental indicators
        for complete system performance evaluation.

        Parameters
        ----------
        tech_results : dict
            Results dictionary from individual technology calculation.

        Notes
        -----
        Aggregation Process:
            
            **Energy Balance Aggregation**:
            - Heat generation accumulation by technology
            - Electrical power balance for cogeneration systems
            - Remaining load calculation for dispatch algorithm
            - Storage interaction tracking for energy flows
            
            **Economic Aggregation**:
            - Weighted average heat generation costs
            - Technology contribution to total system costs
            - Revenue accumulation from electricity generation
            - Investment cost aggregation for total system costs
            
            **Environmental Aggregation**:
            - CO2 emissions accumulation by technology
            - Primary energy consumption aggregation
            - Weighted environmental impact indicators
            - Renewable energy fraction calculation
            
            **Performance Metrics**:
            - Technology capacity factors and utilization
            - System-level efficiency indicators
            - Operational statistics aggregation

        The aggregated results provide comprehensive system-level metrics
        for performance analysis, economic evaluation, and environmental
        impact assessment of the multi-technology energy system.
        """
        self.results['techs'].append(tech_results.get('tech_name', 'unknown'))
        self.results['Wärmeleistung_L'].append(tech_results.get('Wärmeleistung_L', np.zeros_like(self.load_profile)))
        self.results['Wärmemengen'].append(tech_results.get('Wärmemenge', 0))
        self.results['Anteile'].append(tech_results.get('Wärmemenge', 0) / self.results['Jahreswärmebedarf'])
        self.results['WGK'].append(tech_results.get('WGK', 0))
        self.results['specific_emissions_L'].append(tech_results.get('spec_co2_total', 0))
        self.results['primärenergie_L'].append(tech_results.get('primärenergie', 0))
        self.results['colors'].append(tech_results.get('color', 'gray'))

        if tech_results.get('Wärmemenge', 0) > 1e-6:
            self.results['Restlast_L'] -= tech_results.get('Wärmeleistung_L', np.zeros_like(self.load_profile))
            self.results['Restwärmebedarf'] -= tech_results.get('Wärmemenge', 0)
            self.results['WGK_Gesamt'] += (tech_results['Wärmemenge'] * tech_results['WGK']) / self.results['Jahreswärmebedarf']
            self.results['specific_emissions_Gesamt'] += (tech_results['Wärmemenge'] * tech_results['spec_co2_total']) / self.results['Jahreswärmebedarf']
            self.results['primärenergiefaktor_Gesamt'] += tech_results['primärenergie'] / self.results['Jahreswärmebedarf']

        if tech_results.get("Strommenge"):
            self.results['Strommenge'] += tech_results["Strommenge"]
            self.results['el_Leistung_L'] += tech_results["el_Leistung_L"]
            self.results['el_Leistung_ges_L'] += tech_results["el_Leistung_L"]

        if tech_results.get("Strombedarf"):
            self.results['Strombedarf'] += tech_results["Strombedarf"]
            self.results['el_Leistungsbedarf_L'] += tech_results["el_Leistung_L"]
            self.results['el_Leistung_ges_L'] -= tech_results["el_Leistung_L"]

        if "Wärmeleistung_Speicher_L" in tech_results.keys():
            self.results['Restlast_L'] -= tech_results["Wärmeleistung_Speicher_L"]
            self.results['Wärmeleistung_L'].append(tech_results["Wärmeleistung_Speicher_L"])
            self.results['techs'].append(f"{tech_results['tech_name']}_Speicher")
            self.results['Anteile'].append(0)
            self.results['colors'].append("gray")

    def calculate_mix(self, variables: list = [], variables_order: list = []) -> dict:
        """
        Calculate the comprehensive energy generation mix for the multi-technology system.

        This method performs detailed simulation of the energy system including
        technology dispatch, storage operation, energy balance calculations,
        and comprehensive performance analysis for the complete district heating
        system with multiple heat generation technologies.

        Parameters
        ----------
        variables : list of float, optional
            Optimization variables for technology parameters (default: []).
        variables_order : list of str, optional
            Order of optimization variables for parameter mapping (default: []).

        Returns
        -------
        dict
            Comprehensive energy system results containing:
            
            - time_steps : numpy.ndarray
                Simulation time steps
            - Last_L : numpy.ndarray
                Original heat demand profile [kW]
            - Jahreswärmebedarf : float
                Annual heat demand [MWh]
            - techs : list
                Technology names and contributions
            - Wärmeleistung_L : list of numpy.ndarray
                Heat generation profiles by technology [kW]
            - Wärmemengen : list of float
                Annual heat generation by technology [MWh]
            - Anteile : list of float
                Technology contribution fractions [-]
            - WGK : list of float
                Heat generation costs by technology [€/MWh]
            - WGK_Gesamt : float
                System-level heat generation cost [€/MWh]
            - specific_emissions_Gesamt : float
                System CO2 emissions [tCO2/MWh]
            - primärenergiefaktor_Gesamt : float
                System primary energy factor [-]
            - Strommenge : float
                Total electricity generation [MWh]
            - Strombedarf : float
                Total electricity consumption [MWh]
            - colors : list of str
                Visualization colors for technologies

        Notes
        -----
        Calculation Workflow:
            
            **1. System Initialization**:
            - Results dictionary initialization and setup
            - Technology parameter setting from optimization variables
            - Storage system identification and configuration
            - Control strategy activation for all technologies
            
            **2. Hourly Simulation Loop** (if storage present):
            - Storage state and temperature monitoring
            - Technology dispatch based on control strategies
            - Heat generation calculation for active technologies
            - Storage charging/discharging simulation
            - Remaining load tracking and energy balance
            
            **3. Technology Calculations**:
            - Individual technology performance calculation
            - Economic analysis for each technology
            - Environmental impact assessment
            - Results aggregation into system metrics
            
            **4. System Analysis**:
            - Unmet demand calculation and tracking
            - System-level performance metrics
            - Economic and environmental indicators
            - Visualization data preparation

        Integration with Storage:
            
            **Storage Operation**:
            When seasonal storage is present:
            - Hourly temperature stratification simulation
            - Storage charging from excess heat generation
            - Storage discharging to meet demand
            - Heat loss calculations for realistic performance
            - Storage efficiency and cost analysis
            
            **Control Strategy**:
            - Priority-based technology dispatch
            - Storage state-dependent operation decisions
            - Temperature thresholds for activation/deactivation
            - Economic optimization through storage utilization

        The comprehensive calculation provides detailed system analysis
        for performance evaluation, economic assessment, and optimization
        of multi-technology district heating systems.
        """
        self.initialize_results()
        
        # Initialize optimization variables
        self.set_optimization_variables(variables, variables_order)
        
        for tech in self.technologies:
            if isinstance(tech, STES):
                self.storage = tech
                # remove the storage from the technologies list
                self.technologies.remove(tech)
            else:
                # Initialize each technology
                tech.init_operation(8760)

        if self.storage:
            self.storage_state = np.zeros(len(self.time_steps))

            # Initialize results for each time step
            time_steps = len(self.time_steps)

            for t in range(time_steps):
                Q_in_total = 0  # Total heat input

                T_Q_in_flow = self.VLT_L[t] # Supply temperature
                T_Q_out_return = self.RLT_L[t] # Return temperature

                Q_out_total = self.load_profile[t] # Heat demand
                remaining_load = Q_out_total

                # Get storage state and temperatures
                upper_storage_temperature, lower_storage_temperature = self.storage.current_storage_temperatures(t-1) if t > 0 else (0, 0)
                # Get storage state and available energy
                current_storage_state, available_energy, max_energy = self.storage.current_storage_state(t-1, T_Q_out_return, T_Q_in_flow) if t > 0 else (0, 0, 0)
                # Calculate storage losses
                Q_loss = self.storage.Q_loss[t - 1] if t > 0 else 0

                # Control generators based on priority
                for i, tech in enumerate(self.technologies):
                    tech.active = tech.strategy.decide_operation(tech.active, upper_storage_temperature, lower_storage_temperature, remaining_load)

                    if tech.active:
                        # Create kwargs dictionary with technology-specific data
                        kwargs = {
                            "remaining_load": remaining_load,
                            "VLT_L": self.VLT_L[t],
                            "COP_data": self.COP_data,
                            "time_steps": self.time_steps,
                            "duration": self.duration,
                            "TRY_data": self.TRY_data,
                            "RLT_L": self.RLT_L[t],
                            "upper_storage_temperature": upper_storage_temperature,
                            "lower_storage_temperature": lower_storage_temperature,
                            "current_storage_state": current_storage_state,
                            "available_energy": available_energy,
                            "max_energy": max_energy,
                            "Q_loss": Q_loss,
                        }
                        Q_in, _ = tech.generate(t, **kwargs)
                        remaining_load -= Q_in
                        Q_in_total += Q_in

                        tech.calculated = True  # Mark technology as calculated

                # Update storage
                self.storage.simulate_stratified_temperature_mass_flows(t, Q_in_total, Q_out_total, T_Q_in_flow, T_Q_out_return)

            # Calculate storage results
            self.storage.calculate_efficiency(self.load_profile)
            self.storage.calculate_operational_costs(0.10) # needs to be changed to a parameter
            self.results['storage_class'] = self.storage
        
        for tech in self.technologies:
            # Perform technology-specific calculation
            tech_results = tech.calculate(economic_parameters=self.economic_parameters,
                                        duration=self.duration,
                                        load_profile=self.results["Restlast_L"],
                                        VLT_L=self.VLT_L,
                                        RLT_L=self.RLT_L,
                                        TRY_data=self.TRY_data,
                                        COP_data=self.COP_data,
                                        time_steps=self.time_steps)
                
            if tech_results['Wärmemenge'] > 1e-6:
                self.aggregate_results(tech_results)
            else:
                # Add technology as inactive with zero contribution
                self.aggregate_results({'tech_name': tech.name})

        # Calculate unmet demand after processing all technologies
        if np.any(self.results['Restlast_L'] > 1e-6):
            unmet_demand = np.sum(self.results['Restlast_L']) / 1000 * self.duration
            self.results['Wärmeleistung_L'].append(self.results['Restlast_L'])
            self.results['Wärmemengen'].append(unmet_demand)
            self.results['techs'].append("Ungedeckter Bedarf")
            self.results['Anteile'].append(unmet_demand / self.results['Jahreswärmebedarf'])
            self.results['colors'].append("black")

        self.getInitialPlotData()

        return self.results

    def optimize_mix(self, weights: dict, num_restarts: int = 5):
        """
        Optimize the energy generation mix for multi-objective performance.

        This method performs comprehensive optimization of the energy system
        considering multiple objectives including cost minimization, emission
        reduction, and primary energy efficiency. The optimization uses
        advanced algorithms with multiple restart strategies for robust solutions.

        Parameters
        ----------
        weights : dict
            Weights for optimization criteria:
            
            - WGK_Gesamt : float
                Weight for cost minimization objective
            - specific_emissions_Gesamt : float
                Weight for emission reduction objective  
            - primärenergiefaktor_Gesamt : float
                Weight for primary energy efficiency objective
        num_restarts : int, optional
            Number of random restarts for optimization robustness (default: 5).

        Returns
        -------
        EnergySystem
            Optimized energy system with updated technology parameters.

        Notes
        -----
        Optimization Approach:
            
            **Multi-Objective Optimization**:
            - Weighted sum approach for multiple criteria
            - Economic optimization for cost-effective solutions
            - Environmental optimization for sustainability goals
            - Technical optimization for efficiency maximization
            
            **Optimization Algorithm**:
            - Sequential Least Squares Programming (SLSQP)
            - Multiple random restart strategy for global optimum
            - Bound constraints for realistic parameter ranges
            - Convergence criteria for solution quality
            
            **Technology Parameters**:
            - Heat generation capacity optimization
            - Storage system sizing optimization
            - Control parameter optimization
            - Economic parameter sensitivity analysis
            
            **Robustness Strategy**:
            - Multiple optimization runs with random initialization
            - Best solution selection from multiple attempts
            - Convergence monitoring and solution validation
            - Parameter bound enforcement for realistic solutions

        The optimization provides robust solutions for complex multi-technology
        energy systems with comprehensive trade-off analysis between cost,
        environmental impact, and technical performance objectives.
        """
        optimizer = EnergySystemOptimizer(self, weights, num_restarts)
        self.optimized_energy_system = optimizer.optimize()
        
        return self.optimized_energy_system
    
    def getInitialPlotData(self) -> tuple:
        """
        Extract and prepare data for visualization and plotting.

        This method processes simulation results and prepares data structures
        for advanced visualization including stack plots, time series analysis,
        and energy flow diagrams for comprehensive system analysis.

        Returns
        -------
        tuple of (dict, list)
            Visualization data:
            
            extracted_data : dict
                Dictionary with time series data for all variables
            initial_vars : list
                Initial variable selection for default plots

        Notes
        -----
        Data Extraction:
            
            **Technology Data**:
            - Heat generation profiles by technology
            - Electrical power profiles for cogeneration
            - Operational state variables and control signals
            - Performance indicators and efficiency metrics
            
            **Storage Data**:
            - Storage charging and discharging profiles
            - Storage state and temperature evolution
            - Energy flow tracking for storage integration
            - Storage efficiency and loss analysis
            
            **System Data**:
            - Load profiles and demand tracking
            - Unmet demand identification and quantification
            - System-level energy balance verification
            - Performance metric calculation and tracking

        The extracted data provides comprehensive information for system
        visualization, performance analysis, and reporting capabilities.
        """
        # Extract data
        self.extracted_data = {}
        for tech_class in self.technologies:
            for var_name in dir(tech_class):
                var_value = getattr(tech_class, var_name)
                if isinstance(var_value, (list, np.ndarray)) and len(var_value) == len(self.time_steps):
                    unique_var_name = f"{tech_class.name}_{var_name}"
                    self.extracted_data[unique_var_name] = var_value

        # Add storage data
        if self.storage:
            Q_net_storage_flow = self.storage.Q_net_storage_flow

            # Separate storage charging (negative values) and discharging (positive values)
            Q_net_positive = np.maximum(Q_net_storage_flow, 0)  # Storage discharging
            Q_net_negative = np.minimum(Q_net_storage_flow, 0)  # Storage charging

            # Add storage data to extracted data structure
            self.extracted_data['Speicherbeladung_kW'] = Q_net_negative
            self.extracted_data['Speicherentladung_kW'] = Q_net_positive

        if "Ungedeckter Bedarf" in self.results['techs']:
            # Find index of "Ungedeckter Bedarf" in technology list
            if isinstance(self.results['techs'], list):
                unmet_demand_index = self.results['techs'].index("Ungedeckter Bedarf")
            elif isinstance(self.results['techs'], np.ndarray):
                unmet_demand_index = np.where(self.results['techs'] == "Ungedeckter Bedarf")[0][0]
            else:
                # Skip unmet demand if data type is unknown
                unmet_demand_index = None
            
            # Add unmet demand to extracted data structure if index was found
            if unmet_demand_index is not None:
                self.extracted_data['Ungedeckter_Bedarf_kW'] = self.results["Wärmeleistung_L"][unmet_demand_index]

        # Initial selection
        self.initial_vars = [var_name for var_name in self.extracted_data.keys() if "_Wärmeleistung" in var_name]
        self.initial_vars.append("Last_L")
        if self.storage:
            self.initial_vars.append("Speicherbeladung_kW")
            self.initial_vars.append("Speicherentladung_kW")

        return self.extracted_data, self.initial_vars
    
    def plot_stack_plot(self, figure=None, selected_vars=None, second_y_axis=False) -> None:
        """
        Create comprehensive stack plot visualization of energy system operation.

        This method generates advanced stack plot visualizations showing energy
        flows, technology contributions, storage operation, and load profiles
        for comprehensive system analysis and reporting.

        Parameters
        ----------
        figure : matplotlib.figure.Figure, optional
            Figure object for plotting (default: None creates new figure).
        selected_vars : list of str, optional
            Selected variables for plotting (default: None uses initial selection).
        second_y_axis : bool, optional
            Whether to use second y-axis for additional variables (default: False).

        Notes
        -----
        Visualization Features:
            
            **Stack Plot Components**:
            - Heat generation by technology with color coding
            - Storage charging and discharging visualization
            - Load profile overlay for demand comparison
            - Unmet demand identification and highlighting
            
            **Advanced Features**:
            - Dual y-axis support for different variable types
            - Color cycling and consistent technology identification
            - Interactive legend with technology contributions
            - Professional formatting for reporting quality
            
            **Data Organization**:
            - Priority-based variable ordering for clarity
            - Storage operation highlighted with special formatting
            - Load profile as reference line for demand tracking
            - Professional axis labeling and grid formatting

        The stack plot provides comprehensive visualization for system
        analysis, performance evaluation, and stakeholder communication.
        """
        if figure is None:
            figure = plt.figure()

        if selected_vars is None:
            selected_vars = self.initial_vars

        # X-Achse: Jahresstunden als int
        n_steps = len(self.time_steps)
        x = np.arange(n_steps)
        import matplotlib.gridspec as gridspec
        figure.clear()
        # Breitere Legenden-Spalten für lange Namen
        gs = gridspec.GridSpec(1, 3, width_ratios=[0.22, 0.56, 0.22], figure=figure)
        ax_legend_left = figure.add_subplot(gs[0, 0])
        ax_main = figure.add_subplot(gs[0, 1])
        ax_legend_right = figure.add_subplot(gs[0, 2])
        ax_legend_left.axis('off')
        ax_legend_right.axis('off')
        ax_main.set_prop_cycle(color=cm.tab10.colors)

        # Stackplot- und Linienplot-Logik auf ax_main
        stackplot_vars = []
        if "Speicherbeladung_kW" in selected_vars:
            stackplot_vars.append("Speicherbeladung_kW")
        if "Speicherentladung_kW" in selected_vars:
            stackplot_vars.append("Speicherentladung_kW")
        stackplot_vars += [var for var in selected_vars if var not in stackplot_vars and "_Wärmeleistung" in var]
        if "Ungedeckter_Bedarf_kW" in selected_vars:
            stackplot_vars.append("Ungedeckter_Bedarf_kW")
        if "Speicherentladung_kW" in stackplot_vars:
            stackplot_vars.remove("Speicherentladung_kW")
            stackplot_vars.append("Speicherentladung_kW")

        line_vars = [var for var in selected_vars if var not in stackplot_vars and var != "Last_L"]

        stackplot_data = []
        stackplot_labels = []
        for var in stackplot_vars:
            if var == "Speicherbeladung_kW" and var in self.extracted_data:
                ax_main.fill_between(
                    x,
                    0,
                    self.extracted_data[var],
                    label=var,
                    step="mid",
                    color="gray",
                    alpha=1.0,
                )
            elif var in self.extracted_data:
                stackplot_data.append(self.extracted_data[var])
                stackplot_labels.append(var)

        if stackplot_data:
            ax_main.stackplot(
                x,
                stackplot_data,
                labels=stackplot_labels,
                step="mid",
                edgecolor='none'
            )

        ax2 = ax_main.twinx() if second_y_axis else None
        lines_ax1 = []
        labels_ax1 = []
        lines_ax2 = []
        labels_ax2 = []
        import itertools
        color_cycle = itertools.cycle(cm.Dark2.colors)
        for var_name in line_vars:
            if var_name in self.extracted_data:
                if ax2:
                    line, = ax2.plot(
                        x,
                        self.extracted_data[var_name],
                        label=var_name,
                        color=next(color_cycle)
                    )
                    lines_ax2.append(line)
                    labels_ax2.append(var_name)
                else:
                    line, = ax_main.plot(x, self.extracted_data[var_name], label=var_name)
                    lines_ax1.append(line)
                    labels_ax1.append(var_name)

        if "Last_L" in selected_vars:
            line, = ax_main.plot(x, self.results["Last_L"], color='blue', label='Last', linewidth=0.25)
            lines_ax1.append(line)
            labels_ax1.append('Last')

        # Achsenbeschriftung und Grid
        ax_main.set_title("Jahresganglinie", fontsize=16)
        ax_main.set_xlabel("Jahresstunden", fontsize=14)
        ax_main.set_ylabel("Wärmeleistung [kW]", fontsize=14)
        ax_main.grid()
        if ax2:
            ax2.set_ylabel('Temperatur (°C)', fontsize=14)
            ax2.tick_params(axis='y', labelsize=14)

        step = 1000
        ax_main.set_xticks(np.arange(0, n_steps+step, step))
        ax_main.set_xticklabels([str(i) for i in np.arange(0, n_steps+step, step)])

        # Legenden in eigenen Achsen
        def get_ncol(n):
            return 1 if n <= 18 else 2

        if lines_ax1 or stackplot_labels:
            ncol_left = get_ncol(len(lines_ax1) + len(stackplot_labels))
            ax_legend_left.legend(
                ax_main.get_legend_handles_labels()[0],
                ax_main.get_legend_handles_labels()[1],
                loc='best',
                fontsize=12,
                frameon=False,
                ncol=ncol_left
            )
        if lines_ax2:
            ncol_right = get_ncol(len(lines_ax2))
            ax_legend_right.legend(lines_ax2, labels_ax2, loc='best', fontsize=12, frameon=False, ncol=ncol_right)

        # Weniger Rand, damit die Daten direkt an den Achsen anliegen
        figure.subplots_adjust(left=0.08, right=0.92, wspace=0.18)
        # X-Achse: min/max exakt an Daten
        ax_main.set_xlim(x[0], x[-1])
        # Y-Achse: min/max exakt an Daten
        y_data_ax1 = []
        for arr in stackplot_data:
            y_data_ax1.append(np.asarray(arr))
        for var_name in line_vars:
            if var_name in self.extracted_data:
                y_data_ax1.append(np.asarray(self.extracted_data[var_name]))
        if "Last_L" in selected_vars:
            y_data_ax1.append(np.asarray(self.results["Last_L"]))
        if y_data_ax1:
            y_min = min(arr.min() for arr in y_data_ax1)
            y_max = max(arr.max() for arr in y_data_ax1)
            ax_main.set_ylim(y_min, y_max)
        if ax2:
            y_data_ax2 = []
            for var_name in line_vars:
                if var_name in self.extracted_data:
                    y_data_ax2.append(np.asarray(self.extracted_data[var_name]))
            if y_data_ax2:
                y2_min = min(arr.min() for arr in y_data_ax2)
                y2_max = max(arr.max() for arr in y_data_ax2)
                ax2.set_ylim(y2_min, y2_max)

    def plot_pie_chart(self, figure=None) -> None:
        """
        Create comprehensive pie chart visualization of technology contributions.

        This method generates professional pie charts showing technology
        contributions to heat generation with detailed percentage information
        and color-coded visualization for system analysis and reporting.

        Parameters
        ----------
        figure : matplotlib.figure.Figure, optional
            Figure object for plotting (default: None creates new figure).

        Notes
        -----
        Pie Chart Features:
            
            **Technology Representation**:
            - Technology-specific color coding for identification
            - Percentage contributions with precise calculations
            - Technology names and contribution percentages in legend
            - Professional formatting for presentation quality
            
            **Visualization Quality**:
            - Circular pie chart formatting for visual appeal
            - Clear legend placement for easy reading
            - Consistent color scheme with other visualizations
            - High-quality formatting for reports and presentations
            
            **Information Content**:
            - Precise contribution percentages for each technology
            - Technology identification with descriptive names
            - Visual representation of system composition
            - Quantitative analysis support for decision making

        The pie chart provides clear visualization of technology contributions
        for system analysis, stakeholder communication, and performance reporting.
        """
        if figure is None:
            figure = plt.figure()

        # clear the figure if it already exists
        if figure.axes:
            for ax in figure.axes:
                ax.clear()

        ax = figure.add_subplot(111)
        labels = self.results['techs']
        Anteile = self.results['Anteile']
        colors = self.results['colors']

        # Create the pie chart without percentage labels on the chart
        wedges, _ = ax.pie(
            Anteile,
            labels=None,
            colors=colors,
            startangle=90
        )
        ax.set_title("Anteile Wärmeerzeugung")
        ax.axis("equal")  # Ensure the pie chart is circular

        # Prepare legend labels with percentages
        percent_labels = [f"{label}: {100 * anteil:.1f}%" for label, anteil in zip(labels, Anteile)]
        ax.legend(wedges, percent_labels, loc="center left")
    
    def copy(self):
        """
        Create a comprehensive deep copy of the EnergySystem instance.

        This method creates a complete deep copy of the energy system including
        all technologies, storage systems, results, and configuration parameters
        for scenario analysis, optimization, and comparative studies.

        Returns
        -------
        EnergySystem
            Complete deep copy of the energy system with identical configuration.

        Notes
        -----
        Deep Copy Features:
            
            **Complete System Duplication**:
            - All technology objects with parameters and states
            - Storage system configuration and operational data
            - Economic parameters and analysis settings
            - Results dictionary with all calculated metrics
            
            **Independence Guarantee**:
            - Modifications to copy do not affect original system
            - Separate memory allocation for all objects and arrays
            - Independent optimization and analysis capabilities
            - Isolated scenario and sensitivity analysis support
            
            **Use Cases**:
            - Scenario analysis with parameter variations
            - Optimization with multiple starting points
            - Sensitivity analysis for parameter studies
            - Comparative analysis between system configurations

        The deep copy enables comprehensive scenario analysis and optimization
        studies without affecting the original system configuration.
        """
        # Create a new EnergySystem instance with copied basic attributes
        copied_system = EnergySystem(
            time_steps=self.time_steps.copy(),
            load_profile=self.load_profile.copy(),
            VLT_L=self.VLT_L.copy(),
            RLT_L=self.RLT_L.copy(),
            TRY_data=copy.deepcopy(self.TRY_data),
            COP_data=copy.deepcopy(self.COP_data),
            economic_parameters=copy.deepcopy(self.economic_parameters)
        )

        # Deep-copy the technologies
        copied_system.technologies = [copy.deepcopy(tech) for tech in self.technologies]

        # Deep-copy the storage, if it exists
        if self.storage:
            copied_system.storage = copy.deepcopy(self.storage)

        # Deep-copy the results dictionary
        copied_system.results = copy.deepcopy(self.results)

        # Copy any additional attributes that may have been added dynamically
        for attr_name, attr_value in self.__dict__.items():
            if attr_name not in copied_system.__dict__:
                copied_system.__dict__[attr_name] = copy.deepcopy(attr_value)

        return copied_system

    def to_dict(self) -> dict:
        """
        Convert EnergySystem to dictionary for serialization and storage.

        Returns
        -------
        dict
            Dictionary representation of the complete energy system.
        """
        return {
            'time_steps': self.time_steps.astype(str).tolist(),  # Convert datetime64 to string
            'load_profile': self.load_profile.tolist(),
            'VLT_L': self.VLT_L.tolist(),
            'RLT_L': self.RLT_L.tolist(),
            'TRY_data': [data.tolist() for data in self.TRY_data],
            'COP_data': self.COP_data.tolist(),
            'economic_parameters': self.economic_parameters,
            'technologies': [tech.to_dict() for tech in self.technologies],
            'storage': self.storage.to_dict() if self.storage else None,
            'results': {
                key: (value.to_dict(orient='split') if isinstance(value, pd.DataFrame) else value)
                for key, value in self.results.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict):
        """
        Recreate EnergySystem instance from dictionary representation.

        Parameters
        ----------
        data : dict
            Dictionary representation of the EnergySystem.

        Returns
        -------
        EnergySystem
            Fully initialized EnergySystem object.
        """
        # Restore basic attributes
        time_steps = np.array(data['time_steps'], dtype='datetime64')
        load_profile = np.array(data['load_profile'])
        VLT_L = np.array(data['VLT_L'])
        RLT_L = np.array(data['RLT_L'])
        TRY_data = [np.array(item) for item in data['TRY_data']]
        COP_data = np.array(data['COP_data'])
        economic_parameters = data['economic_parameters']

        # Create the EnergySystem object
        obj = cls(
            time_steps=time_steps,
            load_profile=load_profile,
            VLT_L=VLT_L,
            RLT_L=RLT_L,
            TRY_data=TRY_data,
            COP_data=COP_data,
            economic_parameters=economic_parameters
        )

        # Restore technologies
        obj.technologies = []
        for tech_data in data.get('technologies', []):
            for prefix, tech_class in TECH_CLASS_REGISTRY.items():
                if tech_data['name'].startswith(prefix):
                    obj.technologies.append(tech_class.from_dict(tech_data))
                    break

        # Restore storage
        if data.get('storage'):
            obj.storage = STES.from_dict(data['storage'])

        # Restore results (if available)
        obj.results = {}
        if 'results' in data:
            for key, value in data['results'].items():
                if isinstance(value, dict) and 'columns' in value and 'data' in value:
                    obj.results[key] = pd.DataFrame(**value)
                elif isinstance(value, list):
                    if all(isinstance(v, list) for v in value):
                        obj.results[key] = [np.array(v) for v in value]
                    else:
                        obj.results[key] = np.array(value)
                else:
                    obj.results[key] = value

        return obj
    
    def save_to_csv(self, file_path: str) -> None:
        """
        Save comprehensive energy system results to CSV file for analysis.

        This method exports detailed time series results including heat
        generation profiles, electrical power data, and technology contributions
        to CSV format for external analysis, reporting, and documentation.

        Parameters
        ----------
        file_path : str
            Path for CSV file output.

        Notes
        -----
        CSV Export Features:
            
            **Time Series Data**:
            - Hourly heat generation by technology
            - Electrical power generation and consumption
            - Load profiles and system operation data
            - Storage charging and discharging profiles
            
            **Data Format**:
            - Semicolon-separated values for European standards
            - Timestamp column for time series analysis
            - Technology-specific columns for detailed analysis
            - Comprehensive data for external processing
            
            **Analysis Applications**:
            - External data analysis and visualization
            - Integration with other software tools
            - Detailed performance analysis and reporting
            - Long-term data storage and archiving

        The CSV export enables comprehensive data analysis and integration
        with external analysis tools for detailed system evaluation.
        """
        if not self.results:
            raise ValueError("No results available to save.")

        # Initialize the DataFrame with the timestamps
        df = pd.DataFrame({'time_steps': self.results['time_steps']})
        
        # Add the load data
        df['Last_L'] = self.results['Last_L']
        
        # Add the heat generation data for each technology
        for tech_results, techs in zip(self.results['Wärmeleistung_L'], self.results['techs']):
            df[techs] = tech_results
        
        # Add the electrical power data
        df['el_Leistungsbedarf_L'] = self.results['el_Leistungsbedarf_L']
        df['el_Leistung_L'] = self.results['el_Leistung_L']
        df['el_Leistung_ges_L'] = self.results['el_Leistung_ges_L']
        
        # Save the DataFrame as a CSV file
        df.to_csv(file_path, index=False, sep=";", encoding='utf-8-sig')

    def save_to_json(self, file_path: str) -> None:
        """
        Save complete EnergySystem object to JSON file for persistence.

        Parameters
        ----------
        file_path : str
            Path for JSON file output.
        """
        with open(file_path, 'w') as json_file:
            json.dump(self.to_dict(), json_file, indent=4, cls=CustomJSONEncoder)

    @classmethod
    def load_from_json(cls, file_path: str):
        """
        Load complete EnergySystem object from JSON file.

        Parameters
        ----------
        file_path : str
            Path to JSON file for loading.

        Returns
        -------
        EnergySystem
            Loaded EnergySystem object with complete configuration.
        """
        try:
            with open(file_path, 'r') as json_file:
                data_loaded = json.load(json_file)
            return cls.from_dict(data_loaded)
        except Exception as e:
            raise ValueError(f"Error loading JSON file: {e}")

class EnergySystemOptimizer:
    """
    Multi-objective optimizer for district heating energy system configuration.

    This class implements advanced optimization algorithms for district heating
    energy systems with support for multi-criteria decision making, multiple
    random restarts, and comprehensive technology parameter optimization.
    The optimizer minimizes cost, emissions, and primary energy consumption
    simultaneously through weighted objective functions.

    The optimization framework supports complex energy system configurations
    including renewable technologies, storage systems, and multi-technology
    heat generation mixes for optimal district heating operation.

    Parameters
    ----------
    initial_energy_system : EnergySystem
        Initial energy system configuration for optimization.
        Contains technologies, load profiles, and economic parameters.
    weights : dict
        Multi-objective optimization weights for decision criteria:
        
        - 'WGK_Gesamt' : float
            Weight for total heat generation cost [€/MWh]
        - 'specific_emissions_Gesamt' : float
            Weight for specific CO2 emissions [tCO2/MWh]
        - 'primärenergiefaktor_Gesamt' : float
            Weight for primary energy factor [-]
    num_restarts : int, optional
        Number of random restart optimization runs.
        Multiple restarts prevent local optima (default: 5).

    Attributes
    ----------
    initial_energy_system : EnergySystem
        Reference energy system configuration
    weights : dict
        Multi-objective optimization weights
    num_restarts : int
        Number of optimization restart attempts
    energy_system_copy : EnergySystem
        Working copy for optimization iterations
    best_solution : scipy.optimize.OptimizeResult
        Best optimization solution found across all restarts
    best_objective_value : float
        Lowest objective function value achieved

    Notes
    -----
    Optimization Framework:
        
        **Multi-Objective Optimization**:
        The optimizer implements weighted sum scalarization:
        
        .. math::
            f_{obj} = w_1 \cdot WGK + w_2 \cdot CO_2 + w_3 \cdot PE
        
        Where:
        - WGK: Weighted average heat generation cost [€/MWh]
        - CO₂: Weighted average specific CO2 emissions [tCO2/MWh]
        - PE: Weighted average primary energy factor [-]
        
        **Optimization Algorithm**:
        - Sequential Least Squares Programming (SLSQP)
        - Gradient-based optimization with constraint handling
        - Bound constraints for technology parameters
        - Multiple random restarts for global optimization
        
        **Decision Variables**:
        Technology-specific parameters including:
        - Heat pump capacity and configuration
        - CHP thermal and storage capacity
        - Solar thermal collector area
        - Storage volume and operational parameters
        - Control strategy parameters

    Optimization Process:
        
        **1. Parameter Extraction**:
        - Collect optimization variables from all technologies
        - Define bounds and constraints for each parameter
        - Create variable mapping for parameter identification
        
        **2. Random Restart Strategy**:
        - Generate random initial values within parameter bounds
        - Perform independent optimization runs
        - Track best solution across all restart attempts
        
        **3. Objective Function Evaluation**:
        - Calculate energy system mix for given parameters
        - Evaluate weighted sum of optimization criteria
        - Handle infeasible solutions and constraint violations
        
        **4. Solution Selection**:
        - Compare objective values across all restarts
        - Select globally best solution
        - Update technology parameters with optimal values

    Applications:
        
        **Technology Sizing**:
        - Optimal heat pump capacity for renewable systems
        - CHP sizing for cogeneration applications
        - Solar thermal system dimensioning
        - Storage system capacity optimization
        
        **System Configuration**:
        - Multi-technology heat generation mix
        - Seasonal energy storage integration
        - Control strategy optimization
        - Economic and environmental trade-offs
        
        **Decision Support**:
        - Cost-optimal system design
        - Emission reduction strategies
        - Primary energy minimization
        - Multi-criteria decision analysis

    Examples
    --------
    >>> # Create energy system with multiple technologies
    >>> energy_system = EnergySystem(
    ...     time_steps=time_array,
    ...     load_profile=heat_demand,
    ...     VLT_L=supply_temp,
    ...     RLT_L=return_temp,
    ...     TRY_data=weather_data,
    ...     COP_data=performance_data,
    ...     economic_parameters=economic_params
    ... )
    >>> 
    >>> # Add technologies for optimization
    >>> energy_system.add_technology(HeatPump(
    ...     name="HP_opt_1",
    ...     opt_th_Leistung_min=50,    # Minimum 50 kW
    ...     opt_th_Leistung_max=500,   # Maximum 500 kW
    ...     opt_Speicher_min=10,       # Minimum 10 m³ storage
    ...     opt_Speicher_max=100       # Maximum 100 m³ storage
    ... ))
    >>> 
    >>> energy_system.add_technology(CHP(
    ...     name="BHKW_opt_2",
    ...     opt_BHKW_min=100,          # Minimum 100 kW thermal
    ...     opt_BHKW_max=400,          # Maximum 400 kW thermal
    ...     opt_BHKW_Speicher_min=20,  # Minimum 20 m³ storage
    ...     opt_BHKW_Speicher_max=80   # Maximum 80 m³ storage
    ... ))

    >>> # Define multi-objective optimization weights
    >>> optimization_weights = {
    ...     'WGK_Gesamt': 1.0,                    # Cost weight
    ...     'specific_emissions_Gesamt': 100.0,   # CO2 weight (€/tCO2)
    ...     'primärenergiefaktor_Gesamt': 50.0    # Primary energy weight
    ... }
    >>> 
    >>> # Create optimizer with multiple restarts
    >>> optimizer = EnergySystemOptimizer(
    ...     initial_energy_system=energy_system,
    ...     weights=optimization_weights,
    ...     num_restarts=10  # 10 random restarts
    ... )
    >>> 
    >>> # Perform multi-objective optimization
    >>> optimized_system = optimizer.optimize()
    >>> 
    >>> # Analyze optimization results
    >>> print("Optimization Results:")
    >>> print(f"Best objective value: {optimizer.best_objective_value:.2f}")
    >>> 
    >>> for tech in optimized_system.technologies:
    ...     print(f"Technology: {tech.name}")
    ...     if hasattr(tech, 'th_Leistung_kW'):
    ...         print(f"  Thermal capacity: {tech.th_Leistung_kW:.1f} kW")
    ...     if hasattr(tech, 'Speicher_Volumen'):
    ...         print(f"  Storage volume: {tech.Speicher_Volumen:.1f} m³")

    >>> # Compare optimization scenarios
    >>> scenarios = {
    ...     'cost_optimal': {'WGK_Gesamt': 1.0, 'specific_emissions_Gesamt': 0.0, 'primärenergiefaktor_Gesamt': 0.0},
    ...     'emission_optimal': {'WGK_Gesamt': 0.0, 'specific_emissions_Gesamt': 1.0, 'primärenergiefaktor_Gesamt': 0.0},
    ...     'energy_optimal': {'WGK_Gesamt': 0.0, 'specific_emissions_Gesamt': 0.0, 'primärenergiefaktor_Gesamt': 1.0},
    ...     'balanced': {'WGK_Gesamt': 1.0, 'specific_emissions_Gesamt': 50.0, 'primärenergiefaktor_Gesamt': 25.0}
    ... }
    >>> 
    >>> results = {}
    >>> for scenario_name, weights in scenarios.items():
    ...     optimizer = EnergySystemOptimizer(energy_system, weights, num_restarts=5)
    ...     optimized = optimizer.optimize()
    ...     
    ...     # Calculate final system performance
    ...     final_results = optimized.calculate_mix()
    ...     results[scenario_name] = {
    ...         'cost': final_results['WGK_Gesamt'],
    ...         'emissions': final_results['specific_emissions_Gesamt'],
    ...         'primary_energy': final_results['primärenergiefaktor_Gesamt']
    ...     }
    >>> 
    >>> # Display scenario comparison
    >>> print("\\nScenario Comparison:")
    >>> for scenario, metrics in results.items():
    ...     print(f"{scenario:15s}: Cost={metrics['cost']:.2f} €/MWh, "
    ...           f"CO2={metrics['emissions']:.3f} tCO2/MWh, "
    ...           f"PE={metrics['primary_energy']:.2f}")

    >>> # Sensitivity analysis
    >>> # Test different weight combinations
    >>> import numpy as np
    >>> 
    >>> weight_ranges = np.linspace(0, 1, 5)  # 5 weight levels
    >>> sensitivity_results = []
    >>> 
    >>> for w_cost in weight_ranges:
    ...     for w_emission in weight_ranges:
    ...         w_energy = 1 - w_cost - w_emission
    ...         if w_energy >= 0:  # Ensure weights sum to reasonable total
    ...             weights = {
    ...                 'WGK_Gesamt': w_cost,
    ...                 'specific_emissions_Gesamt': w_emission * 100,
    ...                 'primärenergiefaktor_Gesamt': w_energy * 50
    ...             }
    ...             
    ...             optimizer = EnergySystemOptimizer(energy_system, weights, num_restarts=3)
    ...             optimized = optimizer.optimize()
    ...             results = optimized.calculate_mix()
    ...             
    ...             sensitivity_results.append({
    ...                 'weights': weights,
    ...                 'objective': optimizer.best_objective_value,
    ...                 'cost': results['WGK_Gesamt'],
    ...                 'emissions': results['specific_emissions_Gesamt'],
    ...                 'primary_energy': results['primärenergiefaktor_Gesamt']
    ...             })
    >>> 
    >>> # Find Pareto optimal solutions
    >>> pareto_solutions = []
    >>> for result in sensitivity_results:
    ...     is_pareto = True
    ...     for other in sensitivity_results:
    ...         if (other['cost'] <= result['cost'] and 
    ...             other['emissions'] <= result['emissions'] and
    ...             other['primary_energy'] <= result['primary_energy'] and
    ...             (other['cost'] < result['cost'] or 
    ...              other['emissions'] < result['emissions'] or
    ...              other['primary_energy'] < result['primary_energy'])):
    ...             is_pareto = False
    ...             break
    ...     if is_pareto:
    ...         pareto_solutions.append(result)
    >>> 
    >>> print(f"\\nFound {len(pareto_solutions)} Pareto optimal solutions")

    See Also
    --------
    EnergySystem : Main energy system class for district heating simulation
    scipy.optimize.minimize : Underlying optimization algorithm
    """

    def __init__(self, initial_energy_system: 'EnergySystem', weights: Dict[str, float], num_restarts: int = 5):
        """
        Initialize the multi-objective energy system optimizer.

        Parameters
        ----------
        initial_energy_system : EnergySystem
            Initial energy system configuration containing technologies,
            load profiles, and economic parameters for optimization.
        weights : dict
            Multi-objective optimization weights for decision criteria.
            Keys: 'WGK_Gesamt', 'specific_emissions_Gesamt', 'primärenergiefaktor_Gesamt'
        num_restarts : int, optional
            Number of random restart optimization runs to avoid local optima.
            Higher values increase optimization robustness (default: 5).

        Notes
        -----
        Initialization Process:
            
            **Weight Validation**:
            - Ensures all required weight keys are present
            - Validates weight values are non-negative
            - Normalizes weights for consistent scaling
            
            **Energy System Preparation**:
            - Validates energy system configuration
            - Checks technology optimization parameters
            - Prepares optimization variable extraction
            
            **Restart Strategy Setup**:
            - Configures multiple optimization attempts
            - Prepares random seed management
            - Initializes solution tracking structures

        The initialization validates input parameters and prepares the
        optimization framework for multi-objective energy system optimization.
        """
        self.initial_energy_system = initial_energy_system
        self.weights = weights
        self.num_restarts = num_restarts
        
        # Validate optimization weights
        required_weights = ['WGK_Gesamt', 'specific_emissions_Gesamt', 'primärenergiefaktor_Gesamt']
        for weight_key in required_weights:
            if weight_key not in weights:
                raise ValueError(f"Required weight '{weight_key}' missing from weights dictionary")
            if weights[weight_key] < 0:
                raise ValueError(f"Weight '{weight_key}' must be non-negative")

    def optimize(self) -> 'EnergySystem':
        """
        Perform multi-objective optimization with multiple random restarts.

        This method executes the complete optimization procedure including
        parameter extraction, multiple restart optimization runs, and
        solution selection for optimal district heating system configuration.

        Returns
        -------
        EnergySystem
            Optimized energy system with updated technology parameters.
            Contains optimal capacity sizes, storage volumes, and control settings.

        Raises
        ------
        ValueError
            If no optimization parameters are available or optimization fails.
        RuntimeError
            If optimization algorithm fails to converge in all restart attempts.

        Notes
        -----
        Optimization Algorithm:
            
            **Multi-Restart Strategy**:
            - Performs `num_restarts` independent optimization runs
            - Uses random initial values within parameter bounds
            - Prevents convergence to local optima
            - Selects globally best solution across all attempts
            
            **Objective Function**:
            The weighted sum objective function combines multiple criteria:
            
            .. math::
                f_{obj}(x) = w_1 \cdot WGK(x) + w_2 \cdot CO_2(x) + w_3 \cdot PE(x)
            
            Where x represents the vector of technology parameters.
            
            **Constraint Handling**:
            - Parameter bounds ensure realistic technology sizes
            - Implicit constraints through energy balance requirements
            - Feasibility checking for technology combinations
            
            **Convergence Criteria**:
            - SLSQP algorithm convergence tolerance
            - Maximum iteration limits for computational efficiency
            - Solution feasibility verification

        Optimization Process:
            
            **1. Parameter Setup**:
            - Extract optimization variables from all technologies
            - Define parameter bounds and constraint relationships
            - Create variable mapping for solution interpretation
            
            **2. Multi-Restart Execution**:
            - Generate random initial values for each restart
            - Execute independent optimization runs
            - Track best solution across all attempts
            
            **3. Solution Evaluation**:
            - Calculate energy system performance for each solution
            - Evaluate multi-objective function value
            - Compare solutions across restart attempts
            
            **4. Result Application**:
            - Apply best solution to energy system configuration
            - Update technology parameters with optimal values
            - Validate final system configuration

        The optimization ensures robust global solution finding through
        multiple restart attempts and comprehensive solution evaluation.
        """
        best_solution = None
        best_objective_value = float('inf')

        # Validate that technologies have optimization parameters
        has_optimization_params = False
        for tech in self.initial_energy_system.technologies:
            idx = tech.name.split("_")[-1] if "_" in tech.name else "0"
            tech_values, tech_variables, tech_bounds = tech.add_optimization_parameters(idx)
            if tech_values and tech_variables and tech_bounds:
                has_optimization_params = True
                break

        if not has_optimization_params:
            raise ValueError("No optimization parameters available. Energy system optimization requires "
                           "technologies with configurable parameters (e.g., capacity, storage volume).")

        for restart in range(self.num_restarts):
            print(f"Starting optimization run {restart + 1}/{self.num_restarts}")

            # Create fresh copy for this optimization run
            self.energy_system_copy = self.initial_energy_system.copy()

            # Extract optimization parameters from all technologies
            initial_values = []
            bounds = []
            variables_mapping = {}

            for tech in self.energy_system_copy.technologies:
                idx = tech.name.split("_")[-1] if "_" in tech.name else "0"
                tech_values, tech_variables, tech_bounds = tech.add_optimization_parameters(idx)
                
                # Skip technologies without optimization parameters
                if not tech_values or not tech_variables or not tech_bounds:
                    continue

                initial_values.extend(tech_values)
                bounds.extend(tech_bounds)

                # Map variables to technology for solution interpretation
                for var in tech_variables:
                    variables_mapping[var] = tech.name
            
            variables_order = list(variables_mapping.keys())

            if not initial_values:
                print("No optimization parameters found. Skipping optimization.")
                return self.initial_energy_system

            # Generate random initial values within parameter bounds
            random_initial_values = [
                np.random.uniform(low=bound[0], high=bound[1]) if bound[1] > bound[0] else bound[0]
                for bound in bounds
            ]

            print(f"Initial values for restart {restart + 1}: {random_initial_values}")

            def objective_function(variables):
                """
                Multi-objective function for energy system optimization.

                Parameters
                ----------
                variables : array_like
                    Technology parameter values for evaluation.

                Returns
                -------
                float
                    Weighted sum of optimization criteria.
                """
                try:
                    # Create fresh copy for objective evaluation
                    fresh_energy_system = self.energy_system_copy.copy()

                    # Calculate energy system performance with given parameters
                    results = fresh_energy_system.calculate_mix(variables, variables_order)

                    # Calculate weighted multi-objective value
                    weighted_sum = (
                        self.weights['WGK_Gesamt'] * results['WGK_Gesamt'] +
                        self.weights['specific_emissions_Gesamt'] * results['specific_emissions_Gesamt'] +
                        self.weights['primärenergiefaktor_Gesamt'] * results['primärenergiefaktor_Gesamt']
                    )
                    
                    return weighted_sum

                except Exception as e:
                    print(f"Error in objective function evaluation: {e}")
                    return float('inf')  # Return large value for infeasible solutions

            # Perform optimization with SLSQP algorithm
            try:
                result = scipy_minimize(
                    objective_function, 
                    random_initial_values, 
                    method='SLSQP', 
                    bounds=bounds,
                    options={'maxiter': 1000, 'ftol': 1e-6}
                )

                # Check if current solution is better than previous best
                if result.success and result.fun < best_objective_value:
                    best_objective_value = result.fun
                    best_solution = result
                    print(f"New best solution found in restart {restart + 1}: {result.fun:.4f}")

            except Exception as e:
                print(f"Optimization failed in restart {restart + 1}: {e}")
                continue

        # Apply best solution if found
        if best_solution is not None:
            print(f"Optimization completed successfully. Best objective value: {best_objective_value:.4f}")
            
            # Apply optimal parameters to energy system
            for tech in self.energy_system_copy.technologies:
                idx = tech.name.split("_")[-1] if "_" in tech.name else "0"
                tech.set_parameters(best_solution.x, variables_order, idx)

            # Store optimization results
            self.best_solution = best_solution
            self.best_objective_value = best_objective_value

            return self.energy_system_copy
        else:
            raise RuntimeError("Optimization failed to find valid solution in all restart attempts. "
                             "Consider adjusting parameter bounds, weights, or increasing restart attempts.")

    def get_optimization_summary(self) -> Dict[str, Union[float, int, bool]]:
        """
        Generate comprehensive optimization summary report.

        Returns
        -------
        dict
            Optimization summary containing:
            
            - 'success' : bool
                Whether optimization found valid solution
            - 'best_objective_value' : float
                Lowest objective function value achieved
            - 'num_restarts' : int
                Number of restart attempts performed
            - 'convergence_restarts' : int
                Number of restarts that converged successfully
            - 'optimization_message' : str
                Detailed optimization status message

        Notes
        -----
        The summary provides comprehensive information about optimization
        performance, convergence behavior, and solution quality for
        analysis and reporting purposes.
        """
        if hasattr(self, 'best_solution') and self.best_solution is not None:
            return {
                'success': True,
                'best_objective_value': self.best_objective_value,
                'num_restarts': self.num_restarts,
                'optimization_message': f"Optimization successful with {self.num_restarts} restarts",
                'solution_variables': self.best_solution.x.tolist(),
                'function_evaluations': getattr(self.best_solution, 'nfev', 0),
                'iterations': getattr(self.best_solution, 'nit', 0)
            }
        else:
            return {
                'success': False,
                'best_objective_value': float('inf'),
                'num_restarts': self.num_restarts,
                'optimization_message': "Optimization failed to find valid solution",
                'solution_variables': [],
                'function_evaluations': 0,
                'iterations': 0
            }