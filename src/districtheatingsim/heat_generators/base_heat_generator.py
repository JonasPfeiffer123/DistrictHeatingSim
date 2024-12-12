"""
Filename: base_heat_generator.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: Contains the base class for heat generators.

"""

class BaseHeatGenerator:
    def __init__(self, name):
        self.name = name

    # Economic efficiency calculation for technical systems according to VDI 2067
    def annuity(self, A0, TN, f_Inst, f_W_Insp, operating_effort=0, q=1.05, r=1.03, T=20, energy_demand=0, energy_costs=0, E1=0, hourly_rate=45):
        """
        Calculate the annuity for a given set of parameters over a specified period.

        Args:
            A0 (float): Initial investment cost.
            TN (int): Useful life of the investment.
            f_Inst (float): Installation factor.
            f_W_Insp (float): Maintenance and inspection factor.
            operating_effort (float, optional): Operating effort in hours. Defaults to 0.
            q (float, optional): Interest rate factor. Defaults to 1.05.
            r (float, optional): Inflation rate factor. Defaults to 1.03.
            T (int, optional): Consideration period in years. Defaults to 20.
            energy_demand (float, optional): Energy demand in kWh. Defaults to 0.
            energy_costs (float, optional): Energy costs in €/kWh. Defaults to 0.
            E1 (float, optional): Annual revenue. Defaults to 0.
            hourly_rate (float, optional): Hourly rate for labor in €/h. Defaults to 45.

        Returns:
            float: Calculated annuity value.
        """
        self.A0 = A0
        self.TN = TN
        self.f_Inst = f_Inst
        self.f_W_Insp = f_W_Insp
        self.operating_effort = operating_effort
        self.q = q
        self.r = r
        self.T = T
        self.energy_demand = energy_demand
        self.energy_costs = energy_costs
        self.E1 = E1
        self.hourly_rate = hourly_rate
        
        self.n = max(self.T // self.TN, 0)

        self.a = (self.q - 1) / (1 - (self.q ** (-self.T)))  # Annuity factor
        self.b = (1 - (self.r / self.q) ** self.T) / (self.q - self.r)  # Price dynamic present value factor
        self.b_v = self.b_B = self.b_IN = self.b_s = self.b_E = self.b

        # Capital-bound costs
        self.AN = self.A0 + sum(self.A0 * (self.r ** (i * self.TN)) / (self.q ** (i * self.TN)) for i in range(1, self.n + 1))  # Present value of investment costs

        self.R_W = self.A0 * (self.r**(self.n*self.TN)) * (((self.n+1)*self.TN-self.T)/self.TN) * 1/(self.q**self.T)  # Residual value
        self.A_N_K = (self.AN - self.R_W) * self.a  # Annuity of capital-bound costs

        # Demand-bound costs
        self.A_V1 = self.energy_demand * self.energy_costs  # Energy costs first period
        self.A_N_V = self.A_V1 * self.a * self.b_v  # Annuity of demand-bound costs

        # Operation-bound costs
        self.A_B1 = self.operating_effort * self.hourly_rate  # Operating costs first period
        self.A_IN = self.A0 * (self.f_Inst + self.f_W_Insp)/100  # Maintenance costs
        self.A_N_B = self.A_B1 * self.a * self.b_B + self.A_IN * self.a * self.b_IN  # Annuity of operation-bound costs

        # Other costs
        self.A_S1 = 0  # Other costs first period
        self.A_N_S = self.A_S1 * self.a * self.b_s  # Annuity of other costs

        self.A_N = - (self.A_N_K + self.A_N_V + self.A_N_B + self.A_N_S)  # Annuity

        # Revenues
        self.A_NE = self.E1 * self.a * self.b_E  # Annuity of revenues

        self.A_N += self.A_NE  # Annuity with revenues

        return -self.A_N
    
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