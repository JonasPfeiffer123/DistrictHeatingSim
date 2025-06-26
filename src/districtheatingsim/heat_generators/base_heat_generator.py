"""
Filename: base_heat_generator.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-06-24
Description: Base classes for heat generators and control strategies in district heating systems.

This module provides the foundational framework for all heat generation technologies and
control strategies in district heating simulations. It implements common interfaces,
economic evaluation methods, and optimization capabilities that are inherited by specific
heat generator implementations such as heat pumps, boilers, and renewable energy systems.

The module follows object-oriented design principles to ensure consistent behavior across
different heat generation technologies while providing flexibility for technology-specific
implementations. It integrates VDI 2067 economic evaluation standards and supports
comprehensive system optimization for district heating applications.

Classes
-------
BaseHeatGenerator : Abstract base class for all heat generation technologies
BaseStrategy : Base class for control strategies and operational logic

Features
--------
- Standardized interface for heat generation technologies
- VDI 2067 compliant economic evaluation integration
- Optimization parameter management and constraint handling
- Serialization and deserialization for simulation persistence
- Control strategy framework with hysteresis logic
- Performance data extraction for analysis and visualization

Design Principles
-----------------
**Technology Abstraction**: Common interface enabling consistent integration of diverse
heat generation technologies (heat pumps, boilers, solar thermal, CHP, etc.)

**Economic Integration**: Built-in VDI 2067 economic evaluation capabilities for
lifecycle cost analysis and technology comparison

**Optimization Support**: Parameter management and constraint definition for
system optimization and capacity sizing

**Extensibility**: Modular design allowing easy addition of new technologies
and control strategies without affecting existing implementations

Dependencies
------------
- numpy >= 1.20.0 : Numerical calculations and array operations
- districtheatingsim.heat_generators.annuity : VDI 2067 economic evaluation

References
----------
Design methodology based on:
- VDI 2067 - Economic efficiency of building installations
- Object-oriented design patterns for energy system modeling
- German district heating technology standards
- Optimization frameworks for energy system design
"""

import numpy as np
from typing import Dict, Any, List, Union, Optional
import copy

from districtheatingsim.heat_generators.annuity import annuity

class BaseHeatGenerator:
    """
    Abstract base class for all heat generation technologies in district heating systems.

    This class provides the fundamental framework and common interface for all heat
    generation technologies including heat pumps, boilers, solar thermal systems,
    combined heat and power (CHP) units, and other renewable energy systems. It
    establishes standardized methods for economic evaluation, optimization integration,
    and simulation management.

    The class implements core functionality shared across all heat generation
    technologies while defining abstract methods that must be implemented by
    specific technology classes. This ensures consistent behavior and interoperability
    within the district heating simulation framework.

    Parameters
    ----------
    name : str
        Unique identifier for the heat generator instance.
        Used for system identification, result tracking, and optimization reference.
        Should follow naming convention: "Technology_Type_ID" (e.g., "Waermepumpe_01").

    Attributes
    ----------
    name : str
        Unique identifier for the heat generator instance.

    Notes
    -----
    Abstract Base Class Design:
        
        **Common Functionality**:
        - Economic evaluation using VDI 2067 methodology
        - Parameter management for optimization algorithms
        - Data serialization for simulation persistence
        - Performance data extraction for analysis
        
        **Technology-Specific Implementation**:
        Derived classes must implement the following abstract methods:
        - `calculate()`: Core simulation calculations
        - `set_parameters()`: Optimization parameter handling
        - `add_optimization_parameters()`: Constraint definition
        
        **Integration Capabilities**:
        - Seamless integration with thermal storage systems
        - Control strategy implementation through BaseStrategy
        - Economic optimization with subsidy considerations
        - Performance monitoring and analysis tools

    Technology Integration Framework:
        
        **Heat Generation Technologies**:
        - **Heat Pumps**: Geothermal, air source, wastewater, waste heat recovery
        - **Conventional Boilers**: Gas, oil, biomass, electric resistance
        - **Renewable Systems**: Solar thermal, geothermal direct use
        - **CHP Systems**: Gas engines, fuel cells, biomass CHP
        - **Hybrid Systems**: Combined renewable and conventional technologies
        
        **Control Integration**:
        - Temperature-based switching logic through BaseStrategy
        - Demand-responsive operation for system optimization
        - Load prioritization and generator sequencing
        - Economic dispatch based on marginal costs

    Economic Evaluation Integration:
        
        **VDI 2067 Compliance**:
        - Standardized lifecycle cost analysis
        - Investment cost evaluation with subsidies
        - Operational cost calculation with energy price escalation
        - Maintenance and replacement cost consideration
        
        **Optimization Support**:
        - Parameter sensitivity analysis
        - Multi-objective optimization capabilities
        - Constraint handling for technical limitations
        - Economic performance indicators

    Examples
    --------
    >>> # Example implementation of a specific heat generator
    >>> class CustomHeatPump(BaseHeatGenerator):
    ...     def __init__(self, name, capacity_kw=500):
    ...         super().__init__(name)
    ...         self.capacity_kw = capacity_kw
    ...         self.efficiency = 4.0  # COP
    ...         
    ...     def calculate(self, economic_parameters, duration, general_results, **kwargs):
    ...         # Implement specific heat pump calculations
    ...         heat_output = min(self.capacity_kw, general_results.get('demand', 0))
    ...         electricity_input = heat_output / self.efficiency
    ...         return {
    ...             'heat_output': heat_output,
    ...             'electricity_input': electricity_input,
    ...             'operational_cost': electricity_input * economic_parameters['electricity_price']
    ...         }
    ...         
    ...     def set_parameters(self, variables, variables_order, idx):
    ...         # Handle optimization parameters
    ...         if f'capacity_{idx}' in variables_order:
    ...             param_idx = variables_order.index(f'capacity_{idx}')
    ...             self.capacity_kw = variables[param_idx]
    ...             
    ...     def add_optimization_parameters(self, idx):
    ...         # Define optimization constraints
    ...         return {
    ...             'variables': [f'capacity_{idx}'],
    ...             'bounds': [(100, 2000)],  # kW capacity range
    ...             'constraints': []
    ...         }

    >>> # Usage in district heating system
    >>> heat_pump = CustomHeatPump("HeatPump_01", capacity_kw=800)
    >>> 
    >>> # Economic evaluation
    >>> economic_params = {
    ...     'electricity_price': 0.28,  # €/kWh
    ...     'capital_interest_rate': 0.04,
    ...     'inflation_rate': 0.025,
    ...     'time_period': 20
    ... }
    >>> 
    >>> # Calculate lifecycle costs
    >>> annual_cost = heat_pump.annuity(
    ...     initial_investment_cost=800000,  # € investment
    ...     asset_lifespan_years=20,
    ...     installation_factor=15,
    ...     maintenance_inspection_factor=2.5,
    ...     interest_rate_factor=1.04,
    ...     inflation_rate_factor=1.025,
    ...     consideration_time_period_years=20
    ... )
    >>> print(f"Annual cost: {annual_cost:,.0f} €/year")

    >>> # Serialization for simulation persistence
    >>> heat_pump_data = heat_pump.to_dict()
    >>> restored_heat_pump = CustomHeatPump.from_dict(heat_pump_data)
    >>> print(f"Restored: {restored_heat_pump.name}, Capacity: {restored_heat_pump.capacity_kw} kW")

    See Also
    --------
    BaseStrategy : Base class for control strategies
    annuity : VDI 2067 economic evaluation function
    numpy.ndarray : Array operations for simulation data
    """

    def __init__(self, name: str) -> None:
        """
        Initialize the base heat generator with identification name.

        Parameters
        ----------
        name : str
            Unique identifier for the heat generator instance.
        """
        self.name = name

    def annuity(self, *args, **kwargs) -> float:
        """
        Wrapper for VDI 2067 compliant economic evaluation.

        This method provides direct access to the standardized economic evaluation
        function following VDI 2067 methodology. It enables lifecycle cost analysis
        for all heat generation technologies with consistent economic assumptions
        and calculation procedures.

        Parameters
        ----------
        *args : tuple
            Positional arguments passed to the annuity function.
            See annuity.py documentation for complete parameter description.
        **kwargs : dict
            Keyword arguments passed to the annuity function.
            Allows flexible parameter specification for economic analysis.

        Returns
        -------
        float
            Annual equivalent cost [€/year].
            Levelized annual cost considering all economic factors.

        Notes
        -----
        This wrapper method ensures all heat generators have consistent access
        to economic evaluation capabilities while maintaining the flexibility
        to customize economic parameters for specific technology requirements.

        The method directly interfaces with the VDI 2067 compliant annuity
        calculation function, providing standardized economic evaluation
        across all heat generation technologies.

        Examples
        --------
        >>> # Economic evaluation for heat generator
        >>> heat_generator = BaseHeatGenerator("TestGenerator")
        >>> 
        >>> annual_cost = heat_generator.annuity(
        ...     initial_investment_cost=500000,  # € investment
        ...     asset_lifespan_years=20,         # years lifetime
        ...     installation_factor=12,          # % installation costs
        ...     maintenance_inspection_factor=2.0, # % annual maintenance
        ...     interest_rate_factor=1.04,       # 4% interest
        ...     inflation_rate_factor=1.025,     # 2.5% inflation
        ...     consideration_time_period_years=25 # years analysis period
        ... )
        >>> print(f"Levelized annual cost: {annual_cost:,.0f} €/year")
        """
        return annuity(*args, **kwargs)
    
    def calculate(self, economic_parameters: Dict[str, Any], duration: float, 
                 general_results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Core calculation method for heat generator operation (abstract).

        This abstract method must be implemented by all derived heat generator
        classes to perform technology-specific calculations including thermal
        performance, energy consumption, operational costs, and environmental
        impact assessment.

        Parameters
        ----------
        economic_parameters : dict
            Economic analysis parameters containing:
            
            - **electricity_price** (float): Electricity cost [€/kWh]
            - **gas_price** (float): Natural gas cost [€/kWh]
            - **biomass_price** (float): Biomass fuel cost [€/kWh]
            - **co2_price** (float): CO2 emission cost [€/tCO2]
            - **maintenance_cost_factor** (float): Maintenance cost factor [-]
            
        duration : float
            Time step duration [hours].
            Simulation time increment for calculations.
        general_results : dict
            System-wide simulation results containing:
            
            - **heat_demand** (float): Current heat demand [kW]
            - **supply_temperature** (float): Required supply temperature [°C]
            - **return_temperature** (float): System return temperature [°C]
            - **storage_temperature** (float): Storage temperature [°C]
            - **ambient_conditions** (dict): Weather and environmental data
            
        **kwargs : dict
            Additional technology-specific parameters:
            
            - **VLT** (float): Flow temperature [°C]
            - **RLT** (float): Return temperature [°C]
            - **COP_data** (np.ndarray): Performance data for heat pumps
            - **efficiency_curve** (callable): Efficiency function for boilers
            - **solar_irradiation** (float): Solar irradiance [W/m²]

        Returns
        -------
        dict
            Calculation results containing technology-specific outputs:
            
            **Common Results** (all technologies):
            - **heat_output** (float): Heat generation [kW]
            - **fuel_input** (float): Primary energy consumption [kW]
            - **operational_cost** (float): Operational cost [€/h]
            - **efficiency** (float): Current efficiency [-]
            - **operational_state** (bool): Operating status
            
            **Technology-Specific Results**:
            - **electricity_consumption** (float): Electric power [kW] (heat pumps, electric boilers)
            - **COP** (float): Coefficient of Performance [-] (heat pumps)
            - **emissions** (float): CO2 emissions [kg/h] (fossil fuel systems)
            - **thermal_energy** (float): Collected thermal energy [kW] (solar thermal)

        Raises
        ------
        NotImplementedError
            This abstract method must be implemented by derived classes.

        Notes
        -----
        Implementation Requirements:
            
            **Performance Calculations**:
            - Heat output based on current demand and system constraints
            - Energy consumption considering efficiency and operating conditions
            - Part-load performance and cycling effects
            - Temperature-dependent performance variations
            
            **Economic Analysis**:
            - Operational costs based on energy consumption and prices
            - Maintenance costs as function of operating hours
            - Start-up costs and cycling penalties
            - Revenue from heat production or grid services
            
            **Environmental Impact**:
            - CO2 emissions from fuel consumption
            - Primary energy consumption including conversion losses
            - Renewable energy integration benefits
            - Lifecycle environmental impact considerations
            
            **Control Integration**:
            - Operating constraints and technical limitations
            - Control strategy interaction and switching logic
            - Load following capabilities and response times
            - Integration with thermal storage systems

        Implementation Example:
            
        >>> def calculate(self, economic_parameters, duration, general_results, **kwargs):
        ...     # Extract system conditions
        ...     demand = general_results.get('heat_demand', 0)
        ...     supply_temp = general_results.get('supply_temperature', 70)
        ...     
        ...     # Calculate heat output (technology-specific logic)
        ...     heat_output = min(demand, self.max_capacity)
        ...     
        ...     # Calculate energy consumption
        ...     efficiency = self.get_efficiency(supply_temp)
        ...     fuel_input = heat_output / efficiency
        ...     
        ...     # Calculate operational costs
        ...     fuel_cost = fuel_input * economic_parameters['gas_price'] * duration
        ...     
        ...     return {
        ...         'heat_output': heat_output,
        ...         'fuel_input': fuel_input,
        ...         'operational_cost': fuel_cost,
        ...         'efficiency': efficiency,
        ...         'operational_state': heat_output > 0
        ...     }
        """
        raise NotImplementedError("The method 'calculate' must be implemented in the derived class.")

    def set_parameters(self, variables: List[float], variables_order: List[str], idx: int) -> None:
        """
        Set optimization parameters for the heat generator (abstract).

        This abstract method handles parameter assignment during optimization
        procedures, allowing optimization algorithms to modify heat generator
        characteristics such as capacity, efficiency, or control parameters
        for system optimization.

        Parameters
        ----------
        variables : list of float
            List of optimization variable values.
            Contains current values for all optimization variables in the system.
        variables_order : list of str
            List defining the order and assignment of optimization variables.
            Maps variable positions to specific parameters and technologies.
        idx : int
            Index of the current technology in the system list.
            Used to identify technology-specific variables.

        Raises
        ------
        NotImplementedError
            This abstract method must be implemented by derived classes.

        Notes
        -----
        Implementation Guidelines:
            
            **Parameter Mapping**:
            - Extract relevant variables for this specific technology
            - Map optimization variables to physical parameters
            - Validate parameter ranges and technical constraints
            - Update object attributes with new parameter values
            
            **Variable Naming Convention**:
            Variables should follow the pattern: "parameter_name_technology_idx"
            Examples: "capacity_kW_1", "efficiency_2", "storage_volume_m3_3"
            
            **Constraint Handling**:
            - Ensure parameters remain within technical feasible ranges
            - Handle interdependencies between related parameters
            - Validate system consistency after parameter updates

        Implementation Example:
            
        >>> def set_parameters(self, variables, variables_order, idx):
        ...     # Find variables belonging to this technology
        ...     tech_vars = [var for var in variables_order if var.endswith(f'_{idx}')]
        ...     
        ...     for var in tech_vars:
        ...         var_idx = variables_order.index(var)
        ...         value = variables[var_idx]
        ...         
        ...         # Map variable to parameter
        ...         if var.startswith('capacity'):
        ...             self.capacity_kW = max(0, min(value, self.max_capacity))
        ...         elif var.startswith('efficiency'):
        ...             self.efficiency = max(0.5, min(value, 1.0))
        """
        raise NotImplementedError("set_parameters must be implemented in the derived class.")
    
    def add_optimization_parameters(self, idx: int) -> Dict[str, Any]:
        """
        Define optimization variables and constraints for the technology (abstract).

        This abstract method specifies the optimization variables, bounds, and
        constraints for the heat generator technology, enabling integration
        with optimization algorithms for system design and operation optimization.

        Parameters
        ----------
        idx : int
            Index of the technology in the system list.
            Used for unique variable identification.

        Returns
        -------
        dict
            Optimization parameter definition containing:
            
            **variables** : list of str
                Names of optimization variables for this technology.
                
            **bounds** : list of tuple
                (min, max) bounds for each optimization variable.
                
            **constraints** : list of dict
                Constraint definitions for optimization algorithm.
                
            **initial_values** : list of float, optional
                Initial guess values for optimization variables.

        Raises
        ------
        NotImplementedError
            This abstract method must be implemented by derived classes.

        Notes
        -----
        Optimization Integration:
            
            **Variable Definition**:
            - Capacity variables (thermal power, storage volume)
            - Performance parameters (efficiency, COP)
            - Control parameters (temperature setpoints, schedules)
            - Economic parameters (investment levels, technology choices)
            
            **Constraint Types**:
            - **Technical Constraints**: Physical limitations and operating ranges
            - **Economic Constraints**: Budget limitations and cost bounds
            - **Regulatory Constraints**: Emission limits and safety requirements
            - **System Constraints**: Integration requirements and compatibility
            
            **Optimization Objectives**:
            - Minimize lifecycle costs (CAPEX + OPEX)
            - Minimize CO2 emissions and environmental impact
            - Maximize renewable energy integration
            - Maximize system efficiency and reliability

        Implementation Example:
            
        >>> def add_optimization_parameters(self, idx):
        ...     return {
        ...         'variables': [
        ...             f'capacity_kW_{idx}',
        ...             f'efficiency_{idx}',
        ...             f'temperature_setpoint_{idx}'
        ...         ],
        ...         'bounds': [
        ...             (100, 2000),    # Capacity range [kW]
        ...             (0.8, 0.95),    # Efficiency range [-]
        ...             (60, 90)        # Temperature range [°C]
        ...         ],
        ...         'constraints': [
        ...             {'type': 'ineq', 'fun': lambda x: x[0] * x[1] - 500},  # Minimum output
        ...         ],
        ...         'initial_values': [800, 0.9, 75]
        ...     }
        """
        raise NotImplementedError("add_optimization_parameters must be implemented in the derived class.")
    
    def update_parameters(self, optimized_values: List[float], variables_order: List[str]) -> None:
        """
        Update technology parameters based on optimization results.

        This method processes optimization results and updates the heat generator
        parameters accordingly. It extracts technology-specific variables from
        the complete optimization solution and applies them to the heat generator
        configuration for subsequent simulation runs.

        Parameters
        ----------
        optimized_values : list of float
            Optimized values for all system variables.
            Results from optimization algorithm execution.
        variables_order : list of str
            Order of variables defining parameter assignment.
            Maps optimization results to specific parameters.

        Notes
        -----
        Parameter Update Process:
            
            **Variable Extraction**:
            - Identify variables belonging to this specific technology
            - Extract corresponding values from optimization results
            - Validate parameter ranges and consistency
            
            **Parameter Assignment**:
            - Update object attributes with optimized values
            - Ensure technical constraints are maintained
            - Log parameter changes for verification
            
            **System Integration**:
            - Coordinate with other system components
            - Update dependent parameters and relationships
            - Prepare for subsequent simulation execution

        The method uses the technology name suffix to identify relevant
        variables and handles parameter assignment with appropriate validation
        and constraint checking.

        Examples
        --------
        >>> # Example optimization result processing
        >>> heat_generator = SomeHeatGenerator("Generator_01")
        >>> 
        >>> # Optimization results
        >>> optimized_values = [800.0, 0.92, 75.0, 1200.0, 0.88]  # Mixed system values
        >>> variables_order = ['capacity_kW_01', 'efficiency_01', 'temp_setpoint_01', 
        ...                   'capacity_kW_02', 'efficiency_02']
        >>> 
        >>> # Update parameters for this technology
        >>> heat_generator.update_parameters(optimized_values, variables_order)
        >>> # Generator_01 parameters are updated: capacity=800kW, efficiency=0.92, temp=75°C
        """
        # Extract technology index from name
        idx = self.name.split("_")[-1]

        # Filter variables belonging to this technology
        relevant_vars = [
            var for var in variables_order if var.endswith(f"_{idx}")
        ]
        relevant_values = [
            value for var, value in zip(variables_order, optimized_values) 
            if var in relevant_vars
        ]

        if not relevant_vars:
            print(f"No relevant variables found for {self.name}.")
            return

        # Update parameters with optimized values
        for var, value in zip(relevant_vars, relevant_values):
            # Extract parameter name without technology index
            param_name = var.rsplit("_", 1)[0]
            if param_name in self.__dict__:
                setattr(self, param_name, value)
                print(f"Set {param_name} for {self.name} to {value}")

    def get_plot_data(self) -> Dict[str, Union[List, np.ndarray]]:
        """
        Extract time-series data for visualization and analysis.

        This method identifies and returns all array-like attributes of the
        heat generator that contain time-series simulation results. It provides
        a convenient interface for accessing performance data for plotting,
        analysis, and reporting purposes.

        Returns
        -------
        dict
            Dictionary mapping variable names to time-series data arrays.
            Contains all list and numpy array attributes for visualization.

        Notes
        -----
        Data Types Included:
            
            **Performance Time Series**:
            - Heat output profiles [kW]
            - Energy consumption patterns [kW]
            - Efficiency variations [-]
            - Operational state sequences [bool]
            
            **Economic Time Series**:
            - Operational cost profiles [€/h]
            - Revenue streams [€/h]
            - Marginal cost variations [€/MWh]
            
            **Environmental Time Series**:
            - CO2 emission profiles [kg/h]
            - Primary energy consumption [kW]
            - Renewable energy fractions [-]

        The method automatically identifies array-like data structures,
        making it easy to extract visualization data without manual
        specification of relevant variables.

        Examples
        --------
        >>> # Extract plot data from heat generator
        >>> plot_data = heat_generator.get_plot_data()
        >>> 
        >>> # Available data for plotting
        >>> for var_name, data in plot_data.items():
        ...     print(f"{var_name}: {len(data)} data points")
        >>> 
        >>> # Create performance visualization
        >>> import matplotlib.pyplot as plt
        >>> 
        >>> if 'heat_output' in plot_data:
        ...     plt.plot(plot_data['heat_output'], label='Heat Output [kW]')
        ...     plt.xlabel('Time [hours]')
        ...     plt.ylabel('Heat Output [kW]')
        ...     plt.legend()
        ...     plt.show()
        """
        return {
            var_name: getattr(self, var_name) 
            for var_name in self.__dict__ 
            if isinstance(getattr(self, var_name), (list, np.ndarray))
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert heat generator object to dictionary for serialization.

        This method creates a dictionary representation of the heat generator
        object, excluding non-serializable attributes such as GUI elements
        or external references. It enables object persistence, data export,
        and simulation state saving for later restoration.

        Returns
        -------
        dict
            Dictionary representation of the heat generator object.
            Contains all serializable attributes and their current values.

        Notes
        -----
        Serialization Features:
            
            **Included Attributes**:
            - All primitive data types (int, float, str, bool)
            - Collections (lists, dictionaries, tuples)
            - Numpy arrays (converted to lists for JSON compatibility)
            - Nested objects with to_dict() methods
            
            **Excluded Attributes**:
            - GUI scene items and visual representations
            - File handles and network connections
            - Lambda functions and non-serializable callables
            - Large temporary calculation arrays

        The method performs automatic filtering to ensure only relevant
        and serializable data is included in the output dictionary,
        making it suitable for JSON export, database storage, or
        configuration file generation.

        Examples
        --------
        >>> # Serialize heat generator configuration
        >>> heat_gen_dict = heat_generator.to_dict()
        >>> 
        >>> # Save to JSON file
        >>> import json
        >>> with open('heat_generator_config.json', 'w') as f:
        ...     json.dump(heat_gen_dict, f, indent=2)
        >>> 
        >>> # Database storage
        >>> database.store_configuration(heat_gen_dict)
        >>> 
        >>> # Configuration comparison
        >>> config_before = heat_generator.to_dict()
        >>> # ... modify parameters ...
        >>> config_after = heat_generator.to_dict()
        >>> changes = {k: v for k, v in config_after.items() 
        ...           if config_before.get(k) != v}
        """
        # Create copy of object dictionary
        data = self.__dict__.copy()
        
        # Remove non-serializable attributes
        data.pop('scene_item', None)  # GUI elements
        
        # Convert numpy arrays to lists for JSON compatibility
        for key, value in data.items():
            if isinstance(value, np.ndarray):
                data[key] = value.tolist()

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseHeatGenerator':
        """
        Create heat generator object from dictionary representation.

        This class method reconstructs a heat generator object from a dictionary
        representation, enabling deserialization from saved configurations,
        database records, or imported simulation setups. It provides the inverse
        operation to the to_dict() method for complete object persistence.

        Parameters
        ----------
        data : dict
            Dictionary containing heat generator attributes.
            Should be created using the to_dict() method or compatible format.

        Returns
        -------
        BaseHeatGenerator
            New heat generator object with attributes from dictionary.
            Fully functional object ready for simulation use.

        Notes
        -----
        Deserialization Process:
            
            **Object Creation**:
            - Creates new object instance without calling __init__
            - Directly updates object dictionary with provided data
            - Preserves all attribute relationships and configurations
            
            **Data Restoration**:
            - Converts lists back to numpy arrays where appropriate
            - Restores nested objects and complex data structures
            - Maintains object state and configuration consistency
            
            **Compatibility**:
            - Compatible with objects saved using to_dict() method
            - Handles version differences through attribute validation
            - Supports partial restoration with missing attributes

        Examples
        --------
        >>> # Load heat generator from dictionary
        >>> saved_config = {
        ...     'name': 'HeatPump_01',
        ...     'capacity_kW': 800,
        ...     'efficiency': 4.2,
        ...     'operational_data': [100, 150, 200, 180]
        ... }
        >>> 
        >>> # Restore object
        >>> restored_generator = SomeHeatGenerator.from_dict(saved_config)
        >>> print(f"Restored: {restored_generator.name}, {restored_generator.capacity_kW} kW")
        >>> 
        >>> # Load from JSON file
        >>> import json
        >>> with open('heat_generator_config.json', 'r') as f:
        ...     config = json.load(f)
        >>> heat_generator = SomeHeatGenerator.from_dict(config)
        >>> 
        >>> # Batch restoration
        >>> configs = database.load_all_heat_generators()
        >>> generators = [SomeHeatGenerator.from_dict(cfg) for cfg in configs]
        """
        # Create new object without calling __init__
        obj = cls.__new__(cls)
        
        # Update object dictionary with provided data
        obj.__dict__.update(data)
        
        # Convert lists back to numpy arrays for array attributes
        for key, value in obj.__dict__.items():
            if isinstance(value, list) and key.endswith(('_array', '_data', '_profile')):
                setattr(obj, key, np.array(value))
        
        return obj
    
    def __deepcopy__(self, memo: Dict[int, Any]) -> 'BaseHeatGenerator':
        """
        Create deep copy of heat generator object.

        This method enables deep copying of heat generator objects using the
        Python copy module. It ensures complete independence between the
        original and copied objects, preventing unintended side effects
        during simulation runs or parameter studies.

        Parameters
        ----------
        memo : dict
            Memoization dictionary for deepcopy operation.
            Used by copy.deepcopy() to track already copied objects.

        Returns
        -------
        BaseHeatGenerator
            Deep copy of the heat generator object.
            Completely independent copy with separate memory allocation.

        Notes
        -----
        Deep Copy Benefits:
            
            **Complete Independence**:
            - Separate memory allocation for all attributes
            - Independent modification without affecting original
            - Safe for parallel simulation runs and parameter studies
            
            **Relationship Preservation**:
            - Maintains all object relationships and configurations
            - Preserves nested objects and complex data structures
            - Ensures consistent object state in the copy
            
            **Use Cases**:
            - Parameter sensitivity analysis with multiple configurations
            - Parallel simulation execution with different scenarios
            - Backup creation before optimization or modification

        Examples
        --------
        >>> import copy
        >>> 
        >>> # Create deep copy for parameter study
        >>> original_generator = SomeHeatGenerator("Original")
        >>> copied_generator = copy.deepcopy(original_generator)
        >>> 
        >>> # Modify copy without affecting original
        >>> copied_generator.capacity_kW = 1000
        >>> print(f"Original: {original_generator.capacity_kW} kW")  # Unchanged
        >>> print(f"Copy: {copied_generator.capacity_kW} kW")        # Modified
        >>> 
        >>> # Batch copying for scenario analysis
        >>> base_config = SomeHeatGenerator("Base")
        >>> scenarios = [copy.deepcopy(base_config) for _ in range(10)]
        >>> 
        >>> # Modify each scenario independently
        >>> for i, scenario in enumerate(scenarios):
        ...     scenario.name = f"Scenario_{i:02d}"
        ...     scenario.capacity_kW = 500 + i * 100  # Vary capacity
        """
        return self.from_dict(self.to_dict())

class BaseStrategy:
    """
    Base class for control strategies in district heating systems.

    This class provides the fundamental framework for implementing control
    strategies that govern the operation of heat generators based on system
    conditions such as storage temperatures, heat demand, and economic factors.
    It implements hysteresis-based control logic to prevent excessive cycling
    while ensuring efficient system operation.

    The class serves as the foundation for technology-specific control strategies
    including temperature-based switching, demand-responsive operation, and
    economic dispatch optimization. It provides standardized interfaces for
    integration with various heat generation technologies and system controllers.

    Parameters
    ----------
    charge_on : float
        Storage temperature threshold for activating heat generation [°C].
        Heat generator starts when storage temperature falls below this value.
    charge_off : float
        Storage temperature threshold for deactivating heat generation [°C].
        Heat generator stops when storage temperature rises above this value.

    Attributes
    ----------
    charge_on : float
        Upper storage temperature threshold for heat generator activation [°C].
    charge_off : float
        Lower storage temperature threshold for heat generator deactivation [°C].

    Notes
    -----
    Control Strategy Framework:
        
        **Hysteresis Control Logic**:
        The class implements temperature-based hysteresis control to prevent
        rapid cycling of heat generators. This approach provides:
        - Stable operation with reduced mechanical wear
        - Energy efficiency through optimized start-stop cycles
        - System protection against temperature oscillations
        
        **Integration Capabilities**:
        - Compatible with all heat generation technologies
        - Supports complex multi-generator control scenarios
        - Enables economic dispatch and load prioritization
        - Provides framework for advanced control algorithms
        
        **Operational Logic**:
        - **Generator ON**: Continue operation while storage temp < charge_off
        - **Generator OFF**: Start operation when storage temp ≤ charge_on
        - **Demand Integration**: Consider remaining system demand
        - **Safety Features**: Prevent operation without demand or overheating

    Control Strategy Applications:
        
        **Temperature-Based Control**:
        - Thermal storage charging and discharging coordination
        - Seasonal energy storage management
        - District heating supply temperature control
        - Building heating system integration
        
        **Economic Optimization**:
        - Electricity price-based heat pump operation
        - Peak demand management and load shifting
        - Multi-energy system coordination
        - Grid service provision and demand response
        
        **System Protection**:
        - Overheating prevention in thermal storage
        - Equipment protection through controlled operation
        - Grid stability support through load management
        - Maintenance scheduling and equipment preservation

    Examples
    --------
    >>> # Basic temperature-based control strategy
    >>> strategy = BaseStrategy(charge_on=65, charge_off=75)
    >>> 
    >>> # Control decision for heat pump operation
    >>> current_state = False    # Heat pump currently off
    >>> upper_temp = 62.0       # °C upper storage layer temperature
    >>> lower_temp = 58.0       # °C lower storage layer temperature
    >>> demand = 300.0          # kW remaining heat demand
    >>> 
    >>> # Should heat pump start?
    >>> decision = strategy.decide_operation(
    ...     current_state, upper_temp, lower_temp, demand
    ... )
    >>> print(f"Start heat pump: {decision}")  # True (temp below charge_on)

    >>> # Advanced control with economic considerations
    >>> class EconomicStrategy(BaseStrategy):
    ...     def __init__(self, charge_on, charge_off, price_threshold=50):
    ...         super().__init__(charge_on, charge_off)
    ...         self.price_threshold = price_threshold  # €/MWh
    ...         
    ...     def decide_operation(self, current_state, upper_temp, lower_temp, 
    ...                         remaining_demand, electricity_price=None):
    ...         # Basic temperature-based decision
    ...         temp_decision = super().decide_operation(
    ...             current_state, upper_temp, lower_temp, remaining_demand
    ...         )
    ...         
    ...         # Economic override
    ...         if electricity_price and electricity_price > self.price_threshold:
    ...             return False  # Don't operate during high price periods
    ...         
    ...         return temp_decision

    >>> # Multi-generator coordination
    >>> strategies = {
    ...     'heat_pump': BaseStrategy(charge_on=60, charge_off=70),
    ...     'gas_boiler': BaseStrategy(charge_on=55, charge_off=65),
    ...     'electric_heater': BaseStrategy(charge_on=50, charge_off=60)
    ... }
    >>> 
    >>> # Prioritized operation based on temperature thresholds
    >>> storage_temp = 58.0
    >>> demand = 500.0
    >>> 
    >>> for name, strategy in strategies.items():
    ...     should_operate = strategy.decide_operation(
    ...         False, storage_temp, storage_temp, demand
    ...     )
    ...     if should_operate:
    ...         print(f"Activate {name} (priority operation)")
    ...         break

    See Also
    --------
    BaseHeatGenerator : Base class for heat generation technologies
    copy.deepcopy : Deep copying for strategy cloning
    """

    def __init__(self, charge_on: float, charge_off: float) -> None:
        """
        Initialize control strategy with temperature thresholds.

        Parameters
        ----------
        charge_on : float
            Storage temperature threshold for heat generation activation [°C].
        charge_off : float
            Storage temperature threshold for heat generation deactivation [°C].
        """
        self.charge_on = charge_on
        self.charge_off = charge_off

    def decide_operation(self, current_state: bool, upper_storage_temp: float, 
                        lower_storage_temp: float, remaining_demand: float) -> bool:
        """
        Decide heat generator operation based on storage conditions and demand.

        This method implements the core control logic for heat generator operation
        using hysteresis control based on storage temperatures and system demand.
        It provides stable operation while preventing excessive cycling and
        ensuring efficient system integration.

        Parameters
        ----------
        current_state : bool
            Current operational state of the heat generator.
            True if generator is currently running, False if stopped.
        upper_storage_temp : float
            Current upper storage layer temperature [°C].
            Used for activation decisions when generator is off.
        lower_storage_temp : float
            Current lower storage layer temperature [°C].
            Used for deactivation decisions when generator is on.
        remaining_demand : float
            Remaining heat demand in the system [kW].
            Unmet demand after other heat generators.

        Returns
        -------
        bool
            Operational decision for heat generator.
            True to operate generator, False to stop operation.

        Notes
        -----
        Control Logic Implementation:
            
            **Generator Currently Operating (current_state = True)**:
            - Continue operation if lower_storage_temp < charge_off AND demand > 0
            - Stop operation if lower_storage_temp ≥ charge_off OR demand ≤ 0
            
            **Generator Currently Stopped (current_state = False)**:
            - Start operation if upper_storage_temp ≤ charge_on AND demand > 0
            - Remain stopped if upper_storage_temp > charge_on OR demand ≤ 0
            
            **Hysteresis Benefits**:
            - Prevents rapid on-off cycling near temperature thresholds
            - Reduces mechanical wear and electrical switching stress
            - Improves energy efficiency through stable operation periods
            - Provides predictable and controllable system behavior

        Decision Matrix:
            
            | Current State | Upper Temp | Lower Temp | Demand | Decision |
            |---------------|------------|------------|--------|----------|
            | OFF           | ≤ charge_on| any        | > 0    | START    |
            | OFF           | > charge_on| any        | any    | STAY OFF |
            | OFF           | any        | any        | ≤ 0    | STAY OFF |
            | ON            | any        | < charge_off| > 0   | CONTINUE |
            | ON            | any        | ≥ charge_off| any   | STOP     |
            | ON            | any        | any        | ≤ 0    | STOP     |

        Examples
        --------
        >>> # Initialize control strategy
        >>> strategy = BaseStrategy(charge_on=65, charge_off=75)
        >>> 
        >>> # Test various operational scenarios
        >>> test_cases = [
        ...     # (current_state, upper_temp, lower_temp, demand, expected)
        ...     (False, 60.0, 55.0, 300.0, True),   # Start: low temp, high demand
        ...     (False, 70.0, 65.0, 300.0, False),  # Stay off: high temp
        ...     (False, 60.0, 55.0, 0.0, False),    # Stay off: no demand
        ...     (True, 70.0, 72.0, 200.0, True),    # Continue: temp below charge_off
        ...     (True, 75.0, 76.0, 200.0, False),   # Stop: temp above charge_off
        ...     (True, 70.0, 72.0, 0.0, False),     # Stop: no demand
        ... ]
        >>> 
        >>> for i, (state, upper, lower, demand, expected) in enumerate(test_cases):
        ...     result = strategy.decide_operation(state, upper, lower, demand)
        ...     status = "✓" if result == expected else "✗"
        ...     print(f"Test {i+1}: {status} Result={result}, Expected={expected}")

        >>> # Real-time control simulation
        >>> storage_temps = [68, 66, 64, 62, 65, 70, 74, 76, 78, 75, 72]
        >>> demands = [400, 350, 300, 250, 200, 300, 400, 500, 450, 350, 200]
        >>> generator_state = False
        >>> 
        >>> print("Time | Upper | Lower | Demand | State | Decision")
        >>> print("-" * 50)
        >>> 
        >>> for hour, (temp, demand) in enumerate(zip(storage_temps, demands)):
        ...     decision = strategy.decide_operation(
        ...         generator_state, temp, temp-2, demand
        ...     )
        ...     state_str = "ON " if generator_state else "OFF"
        ...     decision_str = "START" if decision and not generator_state else \
        ...                   "STOP " if not decision and generator_state else \
        ...                   "CONT " if decision else "OFF "
        ...     print(f"{hour:4d} | {temp:5.1f} | {temp-2:5.1f} | {demand:6.0f} | "
        ...           f"{state_str} | {decision_str}")
        ...     generator_state = decision
        """
        # Check current operational state and apply hysteresis logic
        if current_state:
            # Generator is currently operating
            if lower_storage_temp < self.charge_off and remaining_demand > 0:
                return True  # Continue operation
            else:
                return False  # Stop operation (overheating protection or no demand)
        else:
            # Generator is currently stopped
            if upper_storage_temp <= self.charge_on and remaining_demand > 0:
                return True  # Start operation (low storage temp and demand present)
            else:
                return False  # Remain stopped (sufficient storage temp or no demand)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert strategy object to dictionary for serialization.

        This method creates a dictionary representation of the control strategy
        object for serialization, export, and persistence purposes. It enables
        saving and restoring control configurations as part of system setup
        and simulation management.

        Returns
        -------
        dict
            Dictionary representation of the strategy object.
            Contains all strategy parameters and configuration data.

        Notes
        -----
        The method creates a complete copy of the object's internal dictionary,
        making it suitable for JSON export, database storage, or configuration
        file generation. All strategy parameters and settings are preserved
        in the output dictionary.

        Examples
        --------
        >>> # Serialize strategy configuration
        >>> strategy = BaseStrategy(charge_on=65, charge_off=75)
        >>> strategy_dict = strategy.to_dict()
        >>> print(strategy_dict)  # {'charge_on': 65, 'charge_off': 75}
        >>> 
        >>> # Save multiple strategies
        >>> strategies = {
        ...     'heat_pump': BaseStrategy(60, 70),
        ...     'gas_boiler': BaseStrategy(55, 65)
        ... }
        >>> config = {name: strategy.to_dict() 
        ...          for name, strategy in strategies.items()}
        """
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseStrategy':
        """
        Create strategy object from dictionary representation.

        This class method reconstructs a control strategy object from a dictionary
        representation, enabling deserialization from saved configurations or
        imported system setups. It provides complete restoration of strategy
        objects from serialized data.

        Parameters
        ----------
        data : dict
            Dictionary containing strategy attributes.
            Should contain all necessary parameters for strategy initialization.

        Returns
        -------
        BaseStrategy
            New strategy object with attributes from dictionary.
            Fully functional strategy ready for system integration.

        Examples
        --------
        >>> # Restore strategy from dictionary
        >>> saved_config = {'charge_on': 65, 'charge_off': 75}
        >>> strategy = BaseStrategy.from_dict(saved_config)
        >>> print(f"Restored strategy: {strategy.charge_on}°C / {strategy.charge_off}°C")
        >>> 
        >>> # Load strategy configuration from file
        >>> import json
        >>> with open('strategy_config.json', 'r') as f:
        ...     config = json.load(f)
        >>> strategies = {name: BaseStrategy.from_dict(cfg) 
        ...              for name, cfg in config.items()}
        """
        obj = cls.__new__(cls)
        obj.__dict__.update(data)
        return obj
    
    def __deepcopy__(self, memo: Dict[int, Any]) -> 'BaseStrategy':
        """
        Create deep copy of strategy object.

        This method enables deep copying of control strategy objects for
        independent modification and parallel system configurations. It ensures
        complete separation between original and copied strategy objects.

        Parameters
        ----------
        memo : dict
            Memoization dictionary for deepcopy operation.
            Used by copy.deepcopy() to track already copied objects.

        Returns
        -------
        BaseStrategy
            Deep copy of the strategy object.
            Independent copy with separate memory allocation.

        Examples
        --------
        >>> import copy
        >>> 
        >>> # Create independent strategy copies
        >>> base_strategy = BaseStrategy(charge_on=65, charge_off=75)
        >>> strategy_copy = copy.deepcopy(base_strategy)
        >>> 
        >>> # Modify copy without affecting original
        >>> strategy_copy.charge_on = 60
        >>> print(f"Original: {base_strategy.charge_on}°C")  # 65°C
        >>> print(f"Copy: {strategy_copy.charge_on}°C")      # 60°C
        """
        return self.from_dict(self.to_dict())