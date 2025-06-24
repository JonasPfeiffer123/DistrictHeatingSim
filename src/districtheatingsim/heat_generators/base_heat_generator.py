"""
Filename: base_heat_generator.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-06-24
Description: Contains the base class for heat generators.

"""

import numpy as np

from districtheatingsim.heat_generators.annuity import annuity

class BaseHeatGenerator:
    def __init__(self, name):
        self.name = name

    # Economic calculation for technical systems according to VDI 2067
    def annuity(self, *args, **kwargs):
        """
        Wrapper for the annuität function from annuity.py.
        """
        return annuity(*args, **kwargs)
    
    def calculate(self, economic_parameters, duration, general_results, **kwargs):
        """
        Calculation function for the technology. Must be overridden by specific technologies.
        
        Args:
            economic_parameters (dict): Economic parameters.
            duration (float): Time difference between time steps in hours.
            general_results (dict): General results of the energy system.
            **kwargs: Additional optional parameters (e.g., VLT, RLT, COP_data).
        
        Returns:
            dict: Results of the calculation.
        """
        raise NotImplementedError("The method 'calculate' must be implemented in the derived class.")

    def set_parameters(self, variables, variables_order, idx):
        """
        Sets parameters of the technology based on the optimization variables.

        Args:
            variables (list): List of optimization variables.
            variables_order (list): Order of the variables describing their assignment.
            idx (int): Index of the current technology in the list.
        """
        # This method should be overridden by each technology.
        raise NotImplementedError("set_parameters must be implemented in the derived class.")
    
    def add_optimization_parameters(self, idx):
        """
        Adds optimization variables and constraints for the technology.

        Args:
            idx (int): Index of the technology in the list.
        """
        # This method should be overridden by each technology.
        raise NotImplementedError("add_optimization_parameters must be implemented in the derived class.")
    
    def update_parameters(self, optimized_values, variables_order):
        """
        Aktualisiert die Parameter der Technologie basierend auf den optimierten Werten.

        Args:
            optimized_values (list): Liste der optimierten Werte.
            variables_order (list): Reihenfolge der Variablen.
        """
        idx = self.name.split("_")[-1]

        # Filtere Variablen, die zu dieser Technologie gehören
        relevant_vars = [
            var for var in variables_order if var.endswith(f"_{idx}")
        ]
        relevant_values = [
            value for var, value in zip(variables_order, optimized_values) if var in relevant_vars
        ]

        if not relevant_vars:
            print(f"Keine relevanten Variablen für {self.name} gefunden.")
            return

        for var, value in zip(relevant_vars, relevant_values):
            # Extrahiere den Parametername ohne den Index
            param_name = var.rsplit("_", 1)[0]
            if param_name in self.__dict__:
                setattr(self, param_name, value)
                print(f"Setze {param_name} für {self.name} auf {value}")

    def get_plot_data(self):
        """
        Returns a dictionary of variables relevant for plotting.
        """
        return {var_name: getattr(self, var_name) for var_name in self.__dict__ if isinstance(getattr(self, var_name), (list, np.ndarray))}
    
    def to_dict(self):
        """
        Converts the object to a dictionary, excluding non-serializable attributes.

        Returns:
            dict: Dictionary representation of the object.
        """
        # Erstelle eine Kopie des aktuellen Objekt-Dictionaries
        data = self.__dict__.copy()
        
        # Entferne das scene_item und andere nicht notwendige Felder
        data.pop('scene_item', None)

        return data

    @classmethod
    def from_dict(cls, data):
        """
        Creates an object from a dictionary.

        Args:
            data (dict): Dictionary containing the attributes of the object.

        Returns:
            cls: A new object of the given class with attributes from the dictionary.
        """
        obj = cls.__new__(cls)
        obj.__dict__.update(data)
        return obj
    
    def __deepcopy__(self, memo):
        """
        Creates a deep copy of the GasBoiler object.

        Args:
            memo (dict): Memoization dictionary for deepcopy.

        Returns:
            GasBoiler: A deep copy of the GasBoiler object.
        """
        return self.from_dict(self.to_dict())
    
class BaseStrategy:
    """
    Base class for strategies in the district heating simulation.

    """
    def __init__(self, charge_on, charge_off):
        """
        Initializes the BaseStrategy class.

        Args:
            charge_on (int): Storage temperature threshold for charging.
            charge_off (int): Storage temperature threshold for discharging.

        """
        self.charge_on = charge_on
        self.charge_off = charge_off

    def decide_operation(self, current_state, upper_storage_temp, lower_storage_temp, remaining_demand):
        """
        Decide whether to turn the heat generator unit on based on storage temperature and remaining demand.

        Args:
            current_state (float): Current state of the system.
            upper_storage_temp (float): Current upper storage temperature.
            lower_storage_temp (float): Current lower storage temperature.
            remaining_demand (float): Remaining heat demand to be covered. (not used in this implementation)

        Returns:
            bool: True if the Power-to-Heat unit should be turned on, False otherwise.
        """

        # Check if the generator is active
        if current_state:
            #  Check if the generator is active
            if lower_storage_temp < self.charge_off:
                return True # Keep generator on
            else:
                return False # Turn generator off
        else:
            if upper_storage_temp > self.charge_on:
                return False # Turn generator off
            else:    
                return True  # Turn generator on
    
    def to_dict(self):
        """
        Converts the object to a dictionary, excluding non-serializable attributes.

        Returns:
            dict: Dictionary representation of the object.
        """
        # Erstelle eine Kopie des aktuellen Objekt-Dictionaries
        data = self.__dict__.copy()

        return data

    @classmethod
    def from_dict(cls, data):
        """
        Creates an object from a dictionary.

        Args:
            data (dict): Dictionary containing the attributes of the object.

        Returns:
            cls: A new object of the given class with attributes from the dictionary.
        """
        obj = cls.__new__(cls)
        obj.__dict__.update(data)
        return obj
    
    def __deepcopy__(self, memo):
        """
        Creates a deep copy of the ThermalStorage object.

        Args:
            memo (dict): Memoization dictionary for deepcopy.

        Returns:
            ThermalStorage: A deep copy of the ThermalStorage object.
        """
        return self.from_dict(self.to_dict())
        