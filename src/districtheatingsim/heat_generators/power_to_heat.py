"""
Filename: power_to_heat.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: Contains the PowerToHeat class representing a power-to-heat system.

"""

import numpy as np

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator

class PowerToHeat(BaseHeatGenerator):
    """
    A class representing a power-to-heat system.

    Attributes:
        name (str): Name of the power-to-heat system.
        spez_Investitionskosten (float): Specific investment costs for the power-to-heat system in €/kW.
        Nutzungsgrad (float): Efficiency of the power-to-heat system.
        Faktor_Dimensionierung (float): Dimensioning factor.
        Nutzungsdauer (int): Lifespan of the power-to-heat system in years.
        f_Inst (float): Installation factor.
        f_W_Insp (float): Inspection factor.
        Bedienaufwand (float): Operational effort.
        co2_factor_fuel (float): CO2 factor for the primary energy source in tCO2/MWh.
        primärenergiefaktor (float): Primary energy factor for the primary energy source.
    """

    def __init__(self, name, spez_Investitionskosten=30, Nutzungsgrad=0.9, Faktor_Dimensionierung=1, active=True):
        """
        Initializes the PowerToHeat class.

        Args:
            name (str): Name of the power-to-heat system.
            spez_Investitionskosten (float, optional): Specific investment costs for the power-to-heat system in €/kW. Defaults to 30.
            Nutzungsgrad (float, optional): Efficiency of the power-to-heat system. Defaults to 0.9.
            Faktor_Dimensionierung (float, optional): Dimensioning factor. Defaults to 1.
        """
        super().__init__(name)
        self.spez_Investitionskosten = spez_Investitionskosten
        self.Nutzungsgrad = Nutzungsgrad
        self.Faktor_Dimensionierung = Faktor_Dimensionierung
        self.Nutzungsdauer = 20
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 1, 2, 0
        self.co2_factor_fuel = 0.4 # tCO2/MWh electricity
        self.primärenergiefaktor = 2.4
        self.active = active

        self.init_operation(8760)

    def init_operation(self, hours):
        self.Wärmeleistung_kW = np.array([0] * hours)
        self.el_Leistung_kW = np.array([0] * hours)
        self.Wärmemenge_MWh = 0
        self.Strommenge_MWh = 0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0
        self.Betriebsstunden_pro_Start = 0

    def simulate_operation(self, Last_L, duration):
        """
        Simulates the operation of the power-to-heat system.

        Args:
            Last_L (array): Load profile of the system in kW.
            duration (float): Duration of each time step in hours.

        Returns:
            None
        """
        self.Wärmeleistung_kW = np.maximum(Last_L, 0)
        self.el_Leistung_kW = self.Wärmeleistung_kW / self.Nutzungsgrad
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Strommenge_MWh = self.Wärmemenge_MWh / self.Nutzungsgrad
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
            economic_parameters (dict): Dictionary containing economic parameters.

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
        self.stundensatz = economic_parameters['hourly_rate']

        if self.Wärmemenge_MWh == 0:
            return 0
        
        self.Investitionskosten = self.spez_Investitionskosten * self.P_max

        self.A_N = self.annuity(self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, self.q, self.r, self.T,
                            self.Strommenge_MWh, self.Strompreis, hourly_rate=self.stundensatz)
        self.WGK_PTH = self.A_N / self.Wärmemenge_MWh

    def calculate_environmental_impact(self):
        """
        Calculates the environmental impact of the power-to-heat system.
        This method calculates the CO2 emissions due to fuel usage and the specific emissions heat.
        It also calculates the primary energy consumption.
        Returns:
            None
        """
        # CO2 emissions due to fuel usage
        self.co2_emissions = self.Strommenge_MWh * self.co2_factor_fuel  # tCO2
        # specific emissions heat
        self.spec_co2_total = self.co2_emissions / self.Wärmemenge_MWh if self.Wärmemenge_MWh > 0 else 0  # tCO2/MWh_heat
        # primary energy factor
        self.primärenergie = self.Strommenge_MWh * self.primärenergiefaktor

    def calculate(self, economic_parameters, duration, load_profile, **kwargs):
        """
        Calculates the performance and cost of the power-to-heat system.

        Args:
            economic_parameters (dict): Dictionary containing economic parameters.
            duration (float): Duration of each time step in hours.
            load_profile (array): Load profile of the system in kW.

        Returns:
            dict: Dictionary containing the results of the calculation.
        """

        self.simulate_operation(load_profile, duration)
        self.calculate_heat_generation_cost(economic_parameters)
        self.calculate_environmental_impact()

        results = {
            'tech_name': self.name,
            'Wärmemenge': self.Wärmemenge_MWh,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'Brennstoffbedarf': self.Strommenge_MWh,
            'WGK': self.WGK_PTH,
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
        PowerToHeat hat keine Optimierungsparameter. Diese Methode gibt leere Listen zurück.

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

# Control strategy for Power-to-Heat
class PowerToHeatStrategy:
    def __init__(self, storage, charge_on):
        """
        Initializes the Power-to-Heat strategy with a switch point based on storage levels.

        Args:
            storage (TemperatureStratifiedThermalStorage): Instance of the storage.
            charge_on (int): Storage temperature to activate Power-to-Heat unit.

        """
        self.storage = storage
        self.charge_on = charge_on

    def decide_operation(self, current_state, upper_storage_temp, lower_storage_temp, remaining_demand):
        """
        Decide whether to turn the Power-to-Heat unit on based on storage temperature and remaining demand.

        upper_storage_temp (float): Current upper storage temperature.
        remaining_demand (float): Remaining heat demand to be covered.

        If the upper storage temperature is too low and there is still demand, the Power-to-Heat unit is turned on.

        """

        if upper_storage_temp < self.charge_on and remaining_demand > 0:
            return True  # Turn P2H on