"""
Filename: gas_boiler.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: Contains the GasBoiler class representing a gas boiler system.

"""

import numpy as np

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy

class GasBoiler(BaseHeatGenerator):
    """
    A class representing a gas boiler system.

    Attributes:
        name (str): Name of the gas boiler.
        spez_Investitionskosten (float): Specific investment costs for the boiler in €/kW.
        Nutzungsgrad (float): Efficiency of the gas boiler.
        Faktor_Dimensionierung (float): Dimensioning factor.
        Nutzungsdauer (int): Lifespan of the gas boiler in years.
        f_Inst (float): Installation factor.
        f_W_Insp (float): Inspection factor.
        Bedienaufwand (float): Operational effort.
        co2_factor_fuel (float): CO2 factor for the fuel in tCO2/MWh.
        primärenergiefaktor (float): Primary energy factor for the fuel.
    """

    def __init__(self, name, thermal_capacity_kW, spez_Investitionskosten=30, Nutzungsgrad=0.9, active=True):
        """
        Initializes the GasBoiler class.

        Args:
            name (str): Name of the gas boiler.
            thermal_capacity_kW (float): Thermal capacity of the gas boiler in kW.
            spez_Investitionskosten (float, optional): Specific investment costs for the boiler in €/kW. Defaults to 30.
            Nutzungsgrad (float, optional): Efficiency of the gas boiler. Defaults to 0.9.
        """
        super().__init__(name)
        self.thermal_capacity_kW = thermal_capacity_kW
        self.spez_Investitionskosten = spez_Investitionskosten
        self.Nutzungsgrad = Nutzungsgrad
        self.active = active
        self.Nutzungsdauer = 20
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 1, 2, 0
        self.co2_factor_fuel = 0.201  # tCO2/MWh gas
        self.primärenergiefaktor = 1.1

        self.strategy = GasBoilerStrategy(70)

        self.init_operation(8760)

    def init_operation(self, hours):
        self.betrieb_mask = np.array([False] * hours)
        self.Wärmeleistung_kW = np.zeros(hours, dtype=float)
        self.Wärmemenge_MWh = 0
        self.Brennstoffbedarf_MWh = 0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0
        self.Betriebsstunden_pro_Start = 0

        self.calculated = False  # Flag to indicate if the calculation is done

    def calculate_operation(self, Last_L):
        """
        Simulates the operation of the gas boiler.

        Args:
            Last_L (array): Load profile of the system in kW.

        Returns:
            None
        """
        self.betrieb_mask = Last_L > 0
        self.Wärmeleistung_kW[self.betrieb_mask] = np.minimum(Last_L[self.betrieb_mask], self.thermal_capacity_kW)
    
    def generate(self, t, **kwargs):
        """
        Generates thermal power for the given time step `t`.
        This method calculates the thermal power and updates the operational statistics of the power-to-heat unit.

        Args:
            t (int): The current time step.
            **kwargs: Additional keyword arguments.

        Returns:
            float: The thermal power (in kW) generated at the current time step.
        """
        remaining_load = kwargs.get('remaining_load', 0)

        if self.active:
            self.betrieb_mask[t] = True
            self.Wärmeleistung_kW[t] = min(remaining_load, self.thermal_capacity_kW)
        else:
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0
        
        return self.Wärmeleistung_kW[t], 0 # No electricity generation
        
    def calculate_results(self, duration):
        """
        Calculates the operational statistics of the gas boiler.
        This method calculates the total heat generated, fuel demand, number of starts, and operating hours.
        
        Args:
            duration (float): Duration of each time step in hours.
            
        """
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Brennstoffbedarf_MWh = self.Wärmemenge_MWh / self.Nutzungsgrad
        
        # Calculate number of starts and operating hours per start
        starts = np.diff(self.betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(self.betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = self.Betriebsstunden / self.Anzahl_Starts if self.Anzahl_Starts > 0 else 0

    def calculate_heat_generation_cost(self, economic_parameters):
        """
        Calculates the weighted average cost of heat generation.

        Args:
            economic_parameters (dict): Economic parameters dictionary containing fuel costs, capital interest rate, inflation rate, time period, and operational costs.

        Returns:
            float: Weighted average cost of heat generation.
        """

        self.Strompreis = economic_parameters['electricity_price']
        self.Gaspreis = economic_parameters['gas_price']
        self.Holzpreis = economic_parameters['wood_price']
        self.q = economic_parameters['capital_interest_rate']
        self.r = economic_parameters['inflation_rate']
        self.T = economic_parameters['time_period']
        self.BEW = economic_parameters['subsidy_eligibility']
        self.hourly_rate = economic_parameters['hourly_rate']

        if self.Wärmemenge_MWh > 0:
        
            self.Investitionskosten = self.spez_Investitionskosten * self.thermal_capacity_kW

            self.A_N = self.annuity(self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, self.q, self.r, self.T,
                                self.Brennstoffbedarf_MWh, self.Gaspreis, hourly_rate=self.hourly_rate)
            
            # wenn die Wärmemenge 0 ist, dann ist die WGK unendlich
            self.WGK = self.A_N / self.Wärmemenge_MWh
            
        else:
            self.Investitionskosten = 0
            self.A_N = 0
            self.WGK = float('inf')

    def calculate_environmental_impact(self):
        """
        Calculates the environmental impact of the gas boiler.
        This method calculates the CO2 emissions due to fuel usage and the specific emissions heat.
        It also calculates the primary energy consumption.
        Returns:
            None
        """
        # CO2 emissions due to fuel usage
        self.co2_emissions = self.Brennstoffbedarf_MWh * self.co2_factor_fuel  # tCO2
        # specific emissions heat
        self.spec_co2_total = self.co2_emissions / self.Wärmemenge_MWh if self.Wärmemenge_MWh > 0 else 0  # tCO2/MWh_heat
        # primary energy factor
        self.primärenergie = self.Brennstoffbedarf_MWh * self.primärenergiefaktor

    def calculate(self, economic_parameters, duration, load_profile, **kwargs):
        """
        Calculates the performance and cost of the gas boiler system.

        Args:
            economic_parameters (dict): Economic parameters dictionary containing fuel costs, capital interest rate, inflation rate, time period, and operational costs.
            duration (float): Duration of each time step in hours.
            load_profile (array): Load profile of the system in kW.

        Returns:
            dict: Dictionary containing the results of the calculation.
        """

        # Check if the calculation has already been done
        if self.calculated == False:
            self.calculate_operation(load_profile)

        self.calculate_results(duration)
        self.calculate_heat_generation_cost(economic_parameters)
        self.calculate_environmental_impact()

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
            "color": "saddlebrown"
        }

        return results
    
    def set_parameters(self, variables, variables_order, idx):
        pass

    def add_optimization_parameters(self, idx):
        """
        GasBoiler hat keine Optimierungsparameter. Diese Methode gibt leere Listen zurück.

        Args:
            idx (int): Index der Technologie in der Liste.

        Returns:
            tuple: Leere Listen für initial_values, variables_order und bounds.
        """
        return [], [], []

    def get_display_text(self):
        return (f"{self.name}: Nennleistung: {self.thermal_capacity_kW:.1f} kW, "
                f"Nutzungsgrad: {self.Nutzungsgrad:.2f}, "
                f"spez. Investitionskosten: {self.spez_Investitionskosten:.1f} €/kW")
    
    def extract_tech_data(self):
        dimensions = f"th. Leistung: {self.thermal_capacity_kW:.1f} kW"
        costs = f"Investitionskosten: {self.Investitionskosten:.1f} €"
        full_costs = f"{self.Investitionskosten:.1f}"
        return self.name, dimensions, costs, full_costs
    
# Control strategy for GasBoiler
class GasBoilerStrategy(BaseStrategy):
    def __init__(self, charge_on, charge_off=None):
        """
        Initializes the GasBoiler strategy with a switch point based on storage levels.

        Args:
            charge_on (int): Storage temperature to activate the GasBoiler.
            charge_off (int, optional): Storage temperature to deactivate the GasBoiler. Defaults to None.
        """
        super().__init__(charge_on, charge_off)  # Initialize BaseStrategy with charge_on and charge_off

    def decide_operation(self, current_state, upper_storage_temp, lower_storage_temp, remaining_demand):
        """
        Decide whether to turn the GasBoiler on based on storage temperature and remaining demand.

        Args:
            current_state (float): Current state of the system (not used in this implementation).
            upper_storage_temp (float): Current upper storage temperature.
            lower_storage_temp (float): Current lower storage temperature (not used in this implementation).
            remaining_demand (float): Remaining heat demand to be covered.

        Returns:
            bool: True if the GasBoiler should be turned on, False otherwise.
        """
        # Check if the upper storage temperature is below the charge_on threshold and if there is remaining demand
        if upper_storage_temp < self.charge_on and remaining_demand > 0:
            return True  # Turn GasBoiler on
        else:
            return False  # Turn GasBoiler off