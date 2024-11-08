"""
Filename: generators.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-08
Description: This module contains classes for the combined heat and power (CHP) unit and the power-to-heat unit.

"""

import numpy as np

from annuity import annuität

class CHP:
    def __init__(self, name, th_Leistung_kW, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850, el_Wirkungsgrad=0.33, KWK_Wirkungsgrad=0.9, 
                 min_Teillast=0.7, BHKW_an=True, opt_BHKW_min=0, opt_BHKW_max=2000, priority=1):
        self.name = name
        self.th_Leistung_kW = th_Leistung_kW
        self.spez_Investitionskosten_GBHKW = spez_Investitionskosten_GBHKW
        self.spez_Investitionskosten_HBHKW = spez_Investitionskosten_HBHKW
        self.el_Wirkungsgrad = el_Wirkungsgrad
        self.KWK_Wirkungsgrad = KWK_Wirkungsgrad
        self.min_Teillast = min_Teillast
        self.BHKW_an = BHKW_an
        self.opt_BHKW_min = opt_BHKW_min
        self.opt_BHKW_max = opt_BHKW_max

        self.priority = priority

        self.thermischer_Wirkungsgrad = self.KWK_Wirkungsgrad - self.el_Wirkungsgrad
        self.el_Leistung_Soll = self.th_Leistung_kW / self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad

        self.Nutzungsdauer = 15
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 6, 2, 0
        if self.name.startswith("BHKW"):
            self.co2_factor_fuel = 0.201 # tCO2/MWh gas
            self.primärenergiefaktor = 1.1 # Gas
        elif self.name.startswith("Holzgas-BHKW"):
            self.co2_factor_fuel = 0.036 # tCO2/MWh pellets
            self.primärenergiefaktor = 0.2 # Pellets
        self.co2_factor_electricity = 0.4 # tCO2/MWh electricity

    def init_operation(self, hours):
        self.Wärmeleistung_kW = np.array([0] * hours)
        self.el_Leistung_kW = np.array([0] * hours)
        self.Wärmemenge_MWh = 0
        self.Strommenge_MWh = 0
        self.Brennstoffbedarf_MWh = 0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0
        self.Betriebsstunden_pro_Start = 0

    def generate(self, t, remaining_heat_demand):
        """
        Generates thermal and electrical power for the given time step `t`.
        This method calculates the thermal power, electrical power, fuel consumption, 
        and updates the operational statistics of the combined heat and power (CHP) unit 
        if it is turned on. It also counts the number of starts and updates the 
        operational hours and operational hours per start.
        Args:
            t (int): The current time step.
        Returns:
            tuple: A tuple containing the thermal power (in kW) and electrical power (in kW) 
                   generated at the current time step. If the CHP unit is turned off, 
                   it returns (0, 0).
        """
        
        if self.BHKW_an:
            self.Wärmeleistung_kW[t] = self.th_Leistung_kW # eventuell noch Teillastverhalten nachbilden
            self.el_Leistung_kW[t] = self.th_Leistung_kW / self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad
            # Berechnen des Brennstoffbedarfs
            self.Wärmemenge_MWh += self.Wärmeleistung_kW[t] / 1000
            self.Strommenge_MWh += self.el_Leistung_kW[t] / 1000
            self.Brennstoffbedarf_MWh += (self.Wärmeleistung_kW[t] + self.el_Leistung_kW[t]) / self.KWK_Wirkungsgrad / 1000

            # Anzahl Starts zählen wenn änderung von 0 auf 1
            if self.Wärmeleistung_kW[t] > 0 and self.Wärmeleistung_kW[t - 1] == 0:
                self.Anzahl_Starts += 1
            self.Betriebsstunden += 1
            self.Betriebsstunden_pro_Start = self.Betriebsstunden / self.Anzahl_Starts if self.Anzahl_Starts > 0 else 0

            return self.Wärmeleistung_kW[t], self.el_Leistung_kW[t]
        return 0, 0  # Wenn das BHKW ausgeschaltet ist, liefert es keine Wärme

    def calculate(self, Gaspreis, Holzpreis, Strompreis, q, r, T, BEW, stundensatz):
        """
        Calculates the economic and environmental metrics for the CHP system.

        Args:
            Gaspreis (float): Gas price.
            Holzpreis (float): Wood price.
            Strompreis (float): Electricity price.
            q (float): Factor for capital recovery.
            r (float): Factor for price escalation.
            T (int): Time period in years.
            BEW (float): BEW factor.
            stundensatz (float): Hourly rate.

        Returns:
            dict: Dictionary containing calculated results.
        """

        if self.Wärmemenge_MWh == 0:
            self.WGK_BHKW = 0
            self.spec_co2_total = 0
            self.primärenergie = 0
        else:
            # Holzvergaser-BHKW: 130 kW: 240.000 -> 1850 €/kW
            # (Erd-)Gas-BHKW: 100 kW: 150.000 € -> 1500 €/kW
            if self.name.startswith("BHKW"):
                self.Brennstoffpreis = Gaspreis
                spez_Investitionskosten_BHKW = self.spez_Investitionskosten_GBHKW  # €/kW
            elif self.name.startswith("Holzgas-BHKW"):
                self.Brennstoffpreis = Holzpreis
                spez_Investitionskosten_BHKW = self.spez_Investitionskosten_HBHKW  # €/kW

            self.Investitionskosten_BHKW = spez_Investitionskosten_BHKW * self.th_Leistung_kW

            self.Stromeinnahmen = self.Strommenge_MWh * Strompreis

            self.A_N = annuität(self.Investitionskosten_BHKW, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, q, r, T, self.Brennstoffbedarf_MWh, self.Brennstoffpreis, self.Stromeinnahmen, stundensatz)

            self.WGK_BHKW = self.A_N / self.Wärmemenge_MWh

            # CO2 emissions due to fuel usage
            self.co2_emissions = self.Brennstoffbedarf_MWh * self.co2_factor_fuel # tCO2
            # CO2 savings due to electricity generation
            self.co2_savings = self.Strommenge_MWh * self.co2_factor_electricity # tCO2
            # total co2
            self.co2_total = self.co2_emissions - self.co2_savings # tCO2
            # specific emissions heat
            self.spec_co2_total = self.co2_total / self.Wärmemenge_MWh # tCO2/MWh_heat

            self.primärenergie = self.Brennstoffbedarf_MWh * self.primärenergiefaktor
     
        results = {
            'Wärmemenge': self.Wärmemenge_MWh,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'Brennstoffbedarf': self.Brennstoffbedarf_MWh,
            'WGK': self.WGK_BHKW,
            'Strommenge': self.Strommenge_MWh,
            'el_Leistung_L': self.el_Leistung_kW,
            'Anzahl_Starts': self.Anzahl_Starts,
            'Betriebsstunden': self.Betriebsstunden,
            'Betriebsstunden_pro_Start': self.Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            'color': "yellow"
        }

        return results
    
    def get_display_text(self):
        if self.name.startswith("BHKW"):
            return (f"{self.name}: th. Leistung: {self.th_Leistung_kW} kW, "
                    f"spez. Investitionskosten Erdgas-BHKW: {self.spez_Investitionskosten_GBHKW} €/kW")
        elif self.name.startswith("Holzgas-BHKW"):
            return (f"{self.name}: th. Leistung: {self.th_Leistung_kW} kW, "
                    f"spez. Investitionskosten Holzgas-BHKW: {self.spez_Investitionskosten_HBHKW} €/kW")

    def to_dict(self):
        """
        Converts the object attributes to a dictionary.

        Returns:
            dict: Dictionary containing object attributes.
        """
        # Erstelle eine Kopie des aktuellen Objekt-Dictionaries
        data = self.__dict__.copy()
        
        # Entferne das scene_item und andere nicht notwendige Felder
        data.pop('scene_item', None)
        return data

    @staticmethod
    def from_dict(data):
        """
        Creates an object from a dictionary of attributes.

        Args:
            data (dict): Dictionary containing object attributes.

        Returns:
            CHP: A new CHP object with attributes from the dictionary.
        """
        obj = CHP.__new__(CHP)
        obj.__dict__.update(data)
        return obj

class PowerToHeat:
    def __init__(self, name, th_Leistung_kW, spez_Investitionskosten=100, priority=2):
        self.name = name
        self.th_Leistung_kW = th_Leistung_kW
        self.spez_Investitionskosten = spez_Investitionskosten
        self.priority = priority

        self.Nutzungsdauer = 20
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 2, 2, 0
        self.co2_factor = 0.4 # tCO2/MWh Strom
        self.primärenergiefaktor = 2.4 # Strom

    def init_operation(self, hours):
        self.Wärmeleistung_kW = np.array([0] * hours)
        self.Wärmemenge_MWh = 0
        self.Betriebsstunden = 0

    def generate(self, t, remaining_heat_demand):
        """
        Generates thermal power for the given time step `t`.
        This method calculates the thermal power and updates the operational statistics of the power-to-heat unit.

        Args:
            t (int): The current time step.

        Returns:
            float: The thermal power (in kW) generated at the current time step.
        """
        self.Wärmeleistung_kW[t] = min(self.th_Leistung_kW, remaining_heat_demand)
        self.Wärmemenge_MWh += self.Wärmeleistung_kW[t] / 1000
        self.Betriebsstunden += 1
        return self.Wärmeleistung_kW[t], 0

    def calculate(self, Strompreis, q, r, T, BEW, stundensatz):
        """
        Calculates the economic and environmental metrics for the power-to-heat system.

        Args:
            Strompreis (float): Electricity price.
            q (float): Factor for capital recovery.
            r (float): Factor for price escalation.
            T (int): Time period in years.
            BEW (float): BEW factor.
            stundensatz (float): Hourly rate.
        
        Returns:
            dict: Dictionary containing calculated results.
        """
        if self.Wärmemenge_MWh == 0:
            self.WGK = 0
            self.spec_co2_total = 0
            self.primärenergie = 0

        else:   
            self.Brennstoffpreis = Strompreis
            self.Investitionskosten = self.spez_Investitionskosten * self.th_Leistung_kW

            self.A_N = annuität(self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, q, r, T, self.th_Leistung_kW, self.Brennstoffpreis, 0, stundensatz)

            self.WGK = self.A_N / self.Wärmemenge_MWh

            # CO2 emissions due to fuel usage
            self.co2_emissions = self.Wärmemenge_MWh * self.co2_factor # tCO2

            self.spec_co2_total = self.co2_emissions / self.Wärmemenge_MWh # tCO2/MWh_heat

            self.primärenergie = self.Wärmemenge_MWh * self.primärenergiefaktor

        results = {
            'Wärmemenge': self.Wärmemenge_MWh,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'WGK': self.WGK,
            'Betriebsstunden': self.Betriebsstunden,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            'color': "green"
        }

        return results
    
    def get_display_text(self):
        return (f"{self.name}: th. Leistung: {self.th_Leistung_kW} kW, "
                f"spez. Investitionskosten: {self.spez_Investitionskosten} €/kW")
    
    def to_dict(self):
        """
        Converts the object attributes to a dictionary.

        Returns:
            dict: Dictionary containing object attributes.
        """
        # Erstelle eine Kopie des aktuellen Objekt-Dictionaries
        data = self.__dict__.copy()
        
        # Entferne das scene_item und andere nicht notwendige Felder
        data.pop('scene_item', None)
        return data
    
    @staticmethod
    def from_dict(data):
        """
        Creates an object from a dictionary of attributes.

        Args:
            data (dict): Dictionary containing object attributes.

        Returns:
            PowerToHeat: A new PowerToHeat object with attributes from the dictionary.
        """
        obj = PowerToHeat.__new__(PowerToHeat)
        obj.__dict__.update(data)
        return obj
    
