"""
Filename: base_heat_generator.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: Contains the base class for heat generators.

"""

class BaseHeatGenerator:
    def __init__(self, name):
        self.name = name

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
    
    def update_parameters(self, optimized_values, variables_order, idx):
        """
        Aktualisiert die Parameter der Technologie basierend auf den optimierten Werten.

        Args:
            optimized_values (list): Liste der optimierten Werte.
            variables_order (list): Liste der Variablennamen.
            idx (int): Index der Technologie in der Liste.
        """
        raise NotImplementedError("Die Methode 'update_parameters' muss in der abgeleiteten Klasse implementiert werden.")
    
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