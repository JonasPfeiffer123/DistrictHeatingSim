"""
Filename: gas_boiler.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: Contains the GasBoiler class representing a gas boiler system.

"""

import numpy as np

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator

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

    def __init__(self, name, spez_Investitionskosten=30, Nutzungsgrad=0.9, Faktor_Dimensionierung=1, active=True):
        """
        Initializes the GasBoiler class.

        Args:
            name (str): Name of the gas boiler.
            spez_Investitionskosten (float, optional): Specific investment costs for the boiler in €/kW. Defaults to 30.
            Nutzungsgrad (float, optional): Efficiency of the gas boiler. Defaults to 0.9.
            Faktor_Dimensionierung (float, optional): Dimensioning factor. Defaults to 1.
        """
        super().__init__(name)
        self.spez_Investitionskosten = spez_Investitionskosten
        self.Nutzungsgrad = Nutzungsgrad
        self.Faktor_Dimensionierung = Faktor_Dimensionierung
        self.active = active
        self.Nutzungsdauer = 20
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 1, 2, 0
        self.co2_factor_fuel = 0.201  # tCO2/MWh gas
        self.primärenergiefaktor = 1.1

        self.init_operation(8760)

    def init_operation(self, hours):
        self.Wärmeleistung_kW = np.array([0] * hours)
        self.Wärmemenge_MWh = 0
        self.Brennstoffbedarf_MWh = 0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0
        self.Betriebsstunden_pro_Start = 0

    def simulate_operation(self, Last_L, duration):
        """
        Simulates the operation of the gas boiler.

        Args:
            Last_L (array): Load profile of the system in kW.
            duration (float): Duration of each time step in hours.

        Returns:
            None
        """
        self.Wärmeleistung_kW = np.maximum(Last_L, 0)
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Brennstoffbedarf_MWh = self.Wärmemenge_MWh / self.Nutzungsgrad
        self.P_max = max(Last_L) * self.Faktor_Dimensionierung

        # Calculate number of starts and operating hours per start
        betrieb_mask = self.Wärmeleistung_kW > 0
        starts = np.diff(betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = self.Betriebsstunden / self.Anzahl_Starts if self.Anzahl_Starts > 0 else 0

    def generate(self, t, remaining_heat_demand):
        """
        Generates thermal power for the given time step `t`.
        This method calculates the thermal power and updates the operational statistics of the power-to-heat unit.

        Args:
            t (int): The current time step.

        Returns:
            float: The thermal power (in kW) generated at the current time step.
        """
        if self.active == False:
            self.th_Leistung_kW = 1000
            self.Wärmeleistung_kW[t] = min(self.th_Leistung_kW, remaining_heat_demand)
            self.Wärmemenge_MWh += self.Wärmeleistung_kW[t] / 1000
            self.Betriebsstunden += 1
            return self.Wärmeleistung_kW[t], 0
        else:
            self.Wärmeleistung_kW[t] = 0
            return 0, 0

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
        
            self.Investitionskosten = self.spez_Investitionskosten * self.P_max

            self.A_N = self.annuity(self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, self.q, self.r, self.T,
                                self.Brennstoffbedarf_MWh, self.Gaspreis, hourly_rate=self.hourly_rate)
            
            # wenn die Wärmemenge 0 ist, dann ist die WGK unendlich
            self.WGK = self.A_N / self.Wärmemenge_MWh
            
        else:
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
        if not hasattr(self, 'Wärmemenge_MWh'):
            self.simulate_operation(load_profile, duration)
            
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
        return f"{self.name}: spez. Investitionskosten: {self.spez_Investitionskosten:.1f} €/kW"
    
    def extract_tech_data(self):
        dimensions = f"th. Leistung: {self.P_max:.1f} kW"
        costs = f"Investitionskosten: {self.Investitionskosten:.1f} €"
        full_costs = f"{self.Investitionskosten:.1f}"
        return self.name, dimensions, costs, full_costs
    
# Control strategy for Gas Boiler
class GasBoilerStrategy:
    def __init__(self, boiler, min_load):
        """
        Initializes the Gas Boiler strategy with a minimum load threshold.

        Args:
            boiler (GasBoiler): Instance of the gas boiler.
            min_load (float): Minimum load to activate the gas boiler in kW.

        """
        self.boiler = boiler
        self.min_load = min_load

    def decide_operation(self, current_load, remaining_demand):
        """
        Decide whether to turn the gas boiler on based on current load and remaining demand.

        Args:
            current_load (float): Current load on the gas boiler in kW.
            remaining_demand (float): Remaining heat demand to be covered in kW.

        If the current load is below the minimum threshold and there is still demand, the gas boiler is turned on.

        Returns:
            bool: True if the gas boiler should be turned on, False otherwise.
        """
        if current_load < self.min_load and remaining_demand > 0:
            return True  # Turn gas boiler on
        return False  # Keep gas boiler off