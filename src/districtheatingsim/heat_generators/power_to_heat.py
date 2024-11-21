"""
Filename: power_to_heat.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-18
Description: Contains the PowerToHeat class representing a power-to-heat system.

"""

import numpy as np

from districtheatingsim.heat_generators.annuity import annuität

class PowerToHeat:
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

    def __init__(self, name, spez_Investitionskosten=30, Nutzungsgrad=0.9, Faktor_Dimensionierung=1):
        """
        Initializes the PowerToHeat class.

        Args:
            name (str): Name of the power-to-heat system.
            spez_Investitionskosten (float, optional): Specific investment costs for the power-to-heat system in €/kW. Defaults to 30.
            Nutzungsgrad (float, optional): Efficiency of the power-to-heat system. Defaults to 0.9.
            Faktor_Dimensionierung (float, optional): Dimensioning factor. Defaults to 1.
        """
        self.name = name
        self.spez_Investitionskosten = spez_Investitionskosten
        self.Nutzungsgrad = Nutzungsgrad
        self.Faktor_Dimensionierung = Faktor_Dimensionierung
        self.Nutzungsdauer = 20
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 1, 2, 0
        self.co2_factor_fuel = 0.4 # tCO2/MWh electricity
        self.primärenergiefaktor = 2.4

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
        self.Wärmemenge_PowerToHeat = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Strombedarf = self.Wärmemenge_PowerToHeat / self.Nutzungsgrad
        self.P_max = max(Last_L) * self.Faktor_Dimensionierung

    def calculate_heat_generation_cost(self, Brennstoffkosten, q, r, T, BEW, stundensatz):
        """
        Calculates the weighted average cost of heat generation.

        Args:
            Brennstoffkosten (float): Electricity costs.
            q (float): Factor for capital recovery.
            r (float): Factor for price escalation.
            T (int): Time period in years.
            BEW (float): Factor for operational costs.
            stundensatz (float): Hourly rate for labor.

        Returns:
            float: Weighted average cost of heat generation.
        """
        if self.Wärmemenge_PowerToHeat == 0:
            return 0
        
        self.Investitionskosten = self.spez_Investitionskosten * self.P_max

        self.A_N = annuität(self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, q, r, T,
                            self.Strombedarf, Brennstoffkosten, stundensatz=stundensatz)
        self.WGK_PTH = self.A_N / self.Wärmemenge_PowerToHeat

    def calculate_environmental_impact(self):
        """
        Calculates the environmental impact of the power-to-heat system.
        This method calculates the CO2 emissions due to fuel usage and the specific emissions heat.
        It also calculates the primary energy consumption.
        Returns:
            None
        """
        # CO2 emissions due to fuel usage
        self.co2_emissions = self.Strombedarf * self.co2_factor_fuel  # tCO2
        # specific emissions heat
        self.spec_co2_total = self.co2_emissions / self.Wärmemenge_PowerToHeat if self.Wärmemenge_PowerToHeat > 0 else 0  # tCO2/MWh_heat
        # primary energy factor
        self.primärenergie = self.Strombedarf * self.primärenergiefaktor

    def calculate(self, Strompreis, q, r, T, BEW, stundensatz, duration, general_results):
        """
        Calculates the performance and cost of the power-to-heat system.

        Args:
            Strompreis (float): Cost of electricity in €/kWh.
            q (float): Factor for capital recovery.
            r (float): Factor for price escalation.
            T (int): Time period in years.
            BEW (float): Factor for operational costs.
            stundensatz (float): Hourly rate for labor.
            duration (float): Duration of each time step in hours.
            Last_L (array): Load profile of the system in kW.
            general_results (dict): General results dictionary containing rest load.

        Returns:
            dict: Dictionary containing the results of the calculation.
        """
        self.simulate_operation(general_results['Restlast_L'], duration)
        self.calculate_heat_generation_cost(Strompreis, q, r, T, BEW, stundensatz)
        self.calculate_environmental_impact()

        results = {
            'Wärmemenge': self.Wärmemenge_PowerToHeat,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'Brennstoffbedarf': self.Strombedarf,
            'WGK': self.WGK_PTH,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            "color": "saddlebrown"
        }

        return results

    def get_display_text(self):
        return f"{self.name}: spez. Investitionskosten: {self.spez_Investitionskosten} €/kW"
    
    def to_dict(self):
        """
        Converts the PowerToHeat object to a dictionary.

        Returns:
            dict: Dictionary representation of the PowerToHeat object.
        """
        # Erstelle eine Kopie des aktuellen Objekt-Dictionaries
        data = self.__dict__.copy()
        
        # Entferne das scene_item und andere nicht notwendige Felder
        data.pop('scene_item', None)
        return data

    @staticmethod
    def from_dict(data):
        """
        Creates a new PowerToHeat object from a dictionary.

        Args:
            data (dict): Dictionary containing the attributes of a PowerToHeat object.

        Returns:
            PowerToHeat: A new PowerToHeat object.
        """
        obj = PowerToHeat.__new__(PowerToHeat)
        obj.__dict__.update(data)
        return obj