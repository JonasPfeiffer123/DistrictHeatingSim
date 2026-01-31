"""
Base Heat Generator Module
==========================

Abstract base classes for heat generation technologies.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import numpy as np
from typing import Dict, Any, List, Union, Optional
import copy

from districtheatingsim.heat_generators.annuity import annuity

class BaseHeatGenerator:
    """
    Abstract base class for heat generators.

    :param name: Unique identifier
    :type name: str

    .. note::
       Derived classes must implement: calculate(), set_parameters(), add_optimization_parameters()
    """

    def __init__(self, name: str) -> None:
        """
        Initialize the base heat generator.

        :param name: Unique identifier for the heat generator instance
        :type name: str
        """
        self.name = name

    def annuity(self, *args, **kwargs) -> float:
        """
        VDI 2067 compliant economic evaluation wrapper.

        :param args: Positional arguments for annuity function
        :param kwargs: Keyword arguments for annuity function
        :return: Annual equivalent cost [€/year]
        :rtype: float

        .. note::
           See annuity.py for complete parameter documentation.
        """
        return annuity(*args, **kwargs)
    
    def calculate(self, economic_parameters: Dict[str, Any], duration: float, 
                 general_results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Core calculation method for heat generator operation (abstract).

        :param economic_parameters: Economic parameters (electricity_price, gas_price, etc.)
        :type economic_parameters: dict
        :param duration: Time step duration [hours]
        :type duration: float
        :param general_results: System results (heat_demand, temperatures, etc.)
        :type general_results: dict
        :param kwargs: Technology-specific parameters
        :return: Results dict with heat_output, fuel_input, operational_cost, etc.
        :rtype: dict

        :raises NotImplementedError: Must be implemented by derived classes

        .. note::
           Derived classes must implement technology-specific calculations.
        """
        raise NotImplementedError("The method 'calculate' must be implemented in the derived class.")

    def set_parameters(self, variables: List[float], variables_order: List[str], idx: int) -> None:
        """
        Set optimization parameters for the heat generator (abstract).

        :param variables: List of optimization variable values
        :type variables: list of float
        :param variables_order: Order and assignment of optimization variables
        :type variables_order: list of str
        :param idx: Technology index in the system list
        :type idx: int

        :raises NotImplementedError: Must be implemented by derived classes
        """
        raise NotImplementedError("set_parameters must be implemented in the derived class.")
    
    def add_optimization_parameters(self, idx: int) -> Dict[str, Any]:
        """
        Define optimization variables and constraints for the technology (abstract).

        :param idx: Technology index in the system list
        :type idx: int
        :return: Dict with 'variables', 'bounds', 'constraints' keys
        :rtype: dict

        :raises NotImplementedError: Must be implemented by derived classes
        """
        raise NotImplementedError("add_optimization_parameters must be implemented in the derived class.")
    
    def update_parameters(self, optimized_values: List[float], variables_order: List[str]) -> None:
        """
        Update technology parameters from optimization results.

        :param optimized_values: Optimized values for all system variables
        :type optimized_values: list of float
        :param variables_order: Order of variables defining parameter assignment
        :type variables_order: list of str
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
        Extract time-series data for visualization.

        :return: Dict mapping variable names to time-series arrays
        :rtype: dict
        """
        return {
            var_name: getattr(self, var_name) 
            for var_name in self.__dict__ 
            if isinstance(getattr(self, var_name), (list, np.ndarray))
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert heat generator to dictionary for serialization.

        :return: Dictionary representation excluding non-serializable attributes
        :rtype: dict

        .. note::
           Numpy arrays are converted to lists for JSON compatibility.
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
        Create heat generator from dictionary representation.

        :param data: Dictionary containing heat generator attributes
        :type data: dict
        :return: New heat generator object
        :rtype: BaseHeatGenerator
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
        Create deep copy of heat generator.

        :param memo: Memoization dict for deepcopy operation
        :type memo: dict
        :return: Deep copy with independent memory allocation
        :rtype: BaseHeatGenerator
        """
        return self.from_dict(self.to_dict())

class BaseStrategy:
    """
    Base control strategy with hysteresis logic.

    :param charge_on: Temperature threshold for activation [°C]
    :type charge_on: float
    :param charge_off: Temperature threshold for deactivation [°C]
    :type charge_off: float
    """

    def __init__(self, charge_on: float, charge_off: float) -> None:
        """
        Initialize control strategy with temperature thresholds.

        :param charge_on: Storage temperature threshold for activation [°C]
        :type charge_on: float
        :param charge_off: Storage temperature threshold for deactivation [°C]
        :type charge_off: float
        """
        self.charge_on = charge_on
        self.charge_off = charge_off

    def decide_operation(self, current_state: bool, upper_storage_temp: float, 
                        lower_storage_temp: float, remaining_demand: float) -> bool:
        """
        Decide heat generator operation based on storage conditions and demand.

        :param current_state: Current operational state of the heat generator
        :type current_state: bool
        :param upper_storage_temp: Upper storage layer temperature [°C]
        :type upper_storage_temp: float
        :param lower_storage_temp: Lower storage layer temperature [°C]
        :type lower_storage_temp: float
        :param remaining_demand: Remaining heat demand [kW]
        :type remaining_demand: float
        :return: True to operate, False to stop
        :rtype: bool

        .. note::
           ON: Continue if lower_temp < charge_off AND demand > 0.
           OFF: Start if upper_temp ≤ charge_on AND demand > 0.
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
        Convert strategy to dictionary for serialization.

        :return: Dictionary representation of the strategy
        :rtype: dict
        """
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseStrategy':
        """
        Create strategy from dictionary representation.

        :param data: Dictionary containing strategy attributes
        :type data: dict
        :return: New strategy object
        :rtype: BaseStrategy
        """
        obj = cls.__new__(cls)
        obj.__dict__.update(data)
        return obj
    
    def __deepcopy__(self, memo: Dict[int, Any]) -> 'BaseStrategy':
        """
        Create deep copy of strategy.

        :param memo: Memoization dict for deepcopy operation
        :type memo: dict
        :return: Independent copy of strategy
        :rtype: BaseStrategy
        """
        return self.from_dict(self.to_dict())