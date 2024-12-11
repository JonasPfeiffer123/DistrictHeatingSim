"""
Filename: chp.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: Contains the Combined Heat and Power (CHP) class for simulating CHP systems and calculating performance and economic metrics.

"""

import numpy as np

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator

class CHP(BaseHeatGenerator):
    """
    This class represents a Combined Heat and Power (CHP) system and provides methods to calculate various performance and economic metrics.

    Args:
        name (str): Name of the CHP system.
        th_Leistung_BHKW (float): Thermal power of the CHP system in kW.
        spez_Investitionskosten_GBHKW (float): Specific investment costs for gas CHP in €/kW. Default is 1500.
        spez_Investitionskosten_HBHKW (float): Specific investment costs for wood gas CHP in €/kW. Default is 1850.
        el_Wirkungsgrad (float): Electrical efficiency of the CHP system. Default is 0.33.
        KWK_Wirkungsgrad (float): Combined heat and power efficiency. Default is 0.9.
        min_Teillast (float): Minimum partial load. Default is 0.7.
        speicher_aktiv (bool): Flag indicating if the storage is active. Default is False.
        Speicher_Volumen_BHKW (float): Storage volume in m³. Default is 20.
        T_vorlauf (float): Flow temperature in °C. Default is 90.
        T_ruecklauf (float): Return temperature in °C. Default is 60.
        initial_fill (float): Initial fill level of the storage. Default is 0.0.
        min_fill (float): Minimum fill level of the storage. Default is 0.2.
        max_fill (float): Maximum fill level of the storage. Default is 0.8.
        spez_Investitionskosten_Speicher (float): Specific investment costs for storage in €/m³. Default is 750.
        BHKW_an (bool): Flag indicating if the CHP is on. Default is True.
        opt_BHKW_min (float): Minimum optimization value for CHP. Default is 0.
        opt_BHKW_max (float): Maximum optimization value for CHP. Default is 1000.
        opt_BHKW_Speicher_min (float): Minimum optimization value for CHP storage. Default is 0.
        opt_BHKW_Speicher_max (float): Maximum optimization value for CHP storage. Default is 100.

    Attributes:
        thermischer_Wirkungsgrad (float): Thermal efficiency of the CHP system.
        el_Leistung_Soll (float): Desired electrical power of the CHP system in kW.
        Nutzungsdauer (int): Usage duration in years.
        f_Inst (float): Installation factor.
        f_W_Insp (float): Inspection factor.
        Bedienaufwand (float): Operating effort.
        co2_factor_fuel (float): CO2 emission factor for fuel in tCO2/MWh.
        primärenergiefaktor (float): Primary energy factor.
        co2_factor_electricity (float): CO2 emission factor for electricity in tCO2/MWh.

    Methods:
        BHKW(Last_L, duration): Calculates the power and heat output of the CHP system without storage.
        storage(Last_L, duration): Calculates the power and heat output of the CHP system with storage.
        WGK(Wärmemenge, Strommenge, Brennstoffbedarf, Brennstoffkosten, Strompreis, q, r, T, BEW, stundensatz): Calculates the economic metrics for the CHP system.
        calculate(Gaspreis, Holzpreis, Strompreis, q, r, T, BEW, stundensatz, duration, general_results): Calculates the economic and environmental metrics for the CHP system.
        to_dict(): Converts the object attributes to a dictionary.
        from_dict(data): Creates an object from a dictionary of attributes.
    """
    def __init__(self, name, th_Leistung_BHKW, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850, el_Wirkungsgrad=0.33, KWK_Wirkungsgrad=0.9, 
                 min_Teillast=0.7, speicher_aktiv=False, Speicher_Volumen_BHKW=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, min_fill=0.2, max_fill=0.8, 
                 spez_Investitionskosten_Speicher=750, BHKW_an=True, opt_BHKW_min=0, opt_BHKW_max=1000, opt_BHKW_Speicher_min=0, opt_BHKW_Speicher_max=100):
        super().__init__(name)
        self.th_Leistung_BHKW = th_Leistung_BHKW
        self.spez_Investitionskosten_GBHKW = spez_Investitionskosten_GBHKW
        self.spez_Investitionskosten_HBHKW = spez_Investitionskosten_HBHKW
        self.el_Wirkungsgrad = el_Wirkungsgrad
        self.KWK_Wirkungsgrad = KWK_Wirkungsgrad
        self.min_Teillast = min_Teillast
        self.speicher_aktiv = speicher_aktiv
        self.Speicher_Volumen_BHKW = Speicher_Volumen_BHKW
        self.T_vorlauf = T_vorlauf
        self.T_ruecklauf = T_ruecklauf
        self.initial_fill = initial_fill
        self.min_fill = min_fill
        self.max_fill = max_fill
        self.spez_Investitionskosten_Speicher = spez_Investitionskosten_Speicher
        self.BHKW_an = BHKW_an
        self.opt_BHKW_min = opt_BHKW_min
        self.opt_BHKW_max = opt_BHKW_max
        self.opt_BHKW_Speicher_min = opt_BHKW_Speicher_min
        self.opt_BHKW_Speicher_max = opt_BHKW_Speicher_max
        self.thermischer_Wirkungsgrad = self.KWK_Wirkungsgrad - self.el_Wirkungsgrad
        self.el_Leistung_Soll = self.th_Leistung_BHKW / self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad
        self.Nutzungsdauer = 15
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 6, 2, 0
        if self.name.startswith("BHKW"):
            self.co2_factor_fuel = 0.201 # tCO2/MWh gas
            self.primärenergiefaktor = 1.1 # Gas
        elif self.name.startswith("Holzgas-BHKW"):
            self.co2_factor_fuel = 0.036 # tCO2/MWh pellets
            self.primärenergiefaktor = 0.2 # Pellets
        self.co2_factor_electricity = 0.4 # tCO2/MWh electricity

    def simulate_operation(self, Last_L, duration):
        """
        Calculates the power and heat output of the CHP system without storage.

        Args:
            Last_L (array-like): Load demand.
            duration (float): Time duration.

        Returns:
            None
        """
        self.Wärmeleistung_kW = np.zeros_like(Last_L)
        self.el_Leistung_kW = np.zeros_like(Last_L)

        # Fälle, in denen das BHKW betrieben werden kann
        betrieb_mask = Last_L >= self.th_Leistung_BHKW * self.min_Teillast
        self.Wärmeleistung_kW[betrieb_mask] = np.minimum(Last_L[betrieb_mask], self.th_Leistung_BHKW)
        self.el_Leistung_kW[betrieb_mask] = self.Wärmeleistung_kW[betrieb_mask] / self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad

        self.Wärmemenge_BHKW = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Strommenge_BHKW = np.sum(self.el_Leistung_kW / 1000) * duration

        # Berechnen des Brennstoffbedarfs
        self.Brennstoffbedarf_BHKW = (self.Wärmemenge_BHKW + self.Strommenge_BHKW) / self.KWK_Wirkungsgrad

        # Anzahl Starts und Betriebsstunden pro Start berechnen
        starts = np.diff(betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden_gesamt = np.sum(betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = self.Betriebsstunden_gesamt / self.Anzahl_Starts if self.Anzahl_Starts > 0 else 0

    def simulate_storage(self, Last_L, duration):
        """
        Calculates the power and heat output of the CHP system with storage.

        Args:
            Last_L (array-like): Load demand.
            duration (float): Time duration.

        Returns:
            None
        """
        # Speicherparameter
        speicher_kapazitaet = self.Speicher_Volumen_BHKW * 4186 * (self.T_vorlauf - self.T_ruecklauf) / 3600  # kWh
        speicher_fill = self.initial_fill * speicher_kapazitaet
        min_speicher_fill = self.min_fill * speicher_kapazitaet
        max_speicher_fill = self.max_fill * speicher_kapazitaet

        self.Wärmeleistung_kW = np.zeros_like(Last_L)
        self.Wärmeleistung_Speicher_kW = np.zeros_like(Last_L)
        self.el_Leistung_BHKW_kW = np.zeros_like(Last_L)
        self.speicher_fuellstand_BHKW = np.zeros_like(Last_L)

        for i in range(len(Last_L)):
            if self.BHKW_an:
                if speicher_fill >= max_speicher_fill:
                    self.BHKW_an = False
                else:
                    self.Wärmeleistung_kW[i] = self.th_Leistung_BHKW
                    if Last_L[i] < self.th_Leistung_BHKW:
                        self.Wärmeleistung_Speicher_kW[i] = Last_L[i] - self.th_Leistung_BHKW
                        speicher_fill += (self.th_Leistung_BHKW - Last_L[i]) * duration
                        speicher_fill = float(min(speicher_fill, speicher_kapazitaet))
                    else:
                        self.Wärmeleistung_Speicher_kW[i] = 0
            else:
                if speicher_fill <= min_speicher_fill:
                    self.BHKW_an = True
            
            if not self.BHKW_an:
                self.Wärmeleistung_kW[i] = 0
                self.Wärmeleistung_Speicher_kW[i] = Last_L[i]
                speicher_fill -= Last_L[i] * duration
                speicher_fill = float(max(speicher_fill, 0))

            self.el_Leistung_BHKW_kW[i] = self.Wärmeleistung_kW[i] / self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad
            self.speicher_fuellstand_BHKW[i] = speicher_fill / speicher_kapazitaet * 100  # %

        self.Wärmemenge_BHKW_Speicher = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Strommenge_BHKW_Speicher = np.sum(self.el_Leistung_BHKW_kW / 1000) * duration

        # Berechnen des Brennstoffbedarfs
        self.Brennstoffbedarf_BHKW_Speicher = (self.Wärmemenge_BHKW_Speicher + self.Strommenge_BHKW_Speicher) / self.KWK_Wirkungsgrad

        # Anzahl Starts und Betriebsstunden pro Start berechnen
        betrieb_mask = self.Wärmeleistung_kW > 0
        starts = np.diff(betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts_Speicher = np.sum(starts)
        self.Betriebsstunden_gesamt_Speicher = np.sum(betrieb_mask) * duration
        self.Betriebsstunden_pro_Start_Speicher = self.Betriebsstunden_gesamt_Speicher / self.Anzahl_Starts_Speicher if self.Anzahl_Starts_Speicher > 0 else 0
    
    def calculate_heat_generation_costs(self, Wärmemenge, Strommenge, Brennstoffbedarf, economic_parameters):
        """
        Calculates the economic metrics for the CHP system.

        Args:
            Wärmemenge (float): Amount of heat generated.
            Strommenge (float): Amount of electricity generated.
            Brennstoffbedarf (float): Fuel consumption.
            economic_parameters (dict): Dictionary containing economic parameters.

        Returns:
            float: Weighted average cost of energy for the CHP system.
        """

        self.Strompreis = economic_parameters['electricity_price']
        self.Gaspreis = economic_parameters['gas_price']
        self.Holzpreis = economic_parameters['wood_price']
        self.q = economic_parameters['capital_interest_rate']
        self.r = economic_parameters['inflation_rate']
        self.T = economic_parameters['time_period']
        self.BEW = economic_parameters['subsidy_eligibility']
        self.stundensatz = economic_parameters['hourly_rate']

        if Wärmemenge == 0:
            self.WGK_BHKW = 0
            return 0
        # Holzvergaser-BHKW: 130 kW: 240.000 -> 1850 €/kW
        # (Erd-)Gas-BHKW: 100 kW: 150.000 € -> 1500 €/kW
        if self.name.startswith("BHKW"):
            spez_Investitionskosten_BHKW = self.spez_Investitionskosten_GBHKW  # €/kW
            self.Brennstoffpreis = self.Gaspreis
        elif self.name.startswith("Holzgas-BHKW"):
            spez_Investitionskosten_BHKW = self.spez_Investitionskosten_HBHKW  # €/kW
            self.Brennstoffpreis = self.Holzpreis

        self.Investitionskosten_BHKW = spez_Investitionskosten_BHKW * self.th_Leistung_BHKW
        self.Investitionskosten_Speicher = self.spez_Investitionskosten_Speicher * self.Speicher_Volumen_BHKW
        self.Investitionskosten = self.Investitionskosten_BHKW + self.Investitionskosten_Speicher

        self.Stromeinnahmen = Strommenge * self.Strompreis

        self.A_N = self.annuity(self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, self.q, self.r, self.T, Brennstoffbedarf, self.Brennstoffpreis, self.Stromeinnahmen, self.stundensatz)
        self.WGK_BHKW = self.A_N / Wärmemenge

    def calculate_environmental_impact(self, Wärmemenge, Strommenge, Brennstoffbedarf):
        # CO2 emissions due to fuel usage
        self.co2_emissions = Brennstoffbedarf * self.co2_factor_fuel # tCO2
        # CO2 savings due to electricity generation
        self.co2_savings = Strommenge * self.co2_factor_electricity # tCO2
        # total co2
        self.co2_total = self.co2_emissions - self.co2_savings # tCO2
        # specific emissions heat
        self.spec_co2_total = self.co2_total / Wärmemenge if Wärmemenge > 0 else 0 # tCO2/MWh_heat

        self.primärenergie = Brennstoffbedarf * self.primärenergiefaktor

    def calculate(self, economic_parameters, duration, general_results, **kwargs):
        """
        Calculates the economic and environmental metrics for the CHP system.

        Args:
            economic_parameters (dict): Dictionary containing economic parameters.
            duration (float): Time duration.
            general_results (dict): Dictionary containing general results.

        Returns:
            dict: Dictionary containing calculated results.
        """
        if self.speicher_aktiv:
            self.simulate_storage(general_results["Restlast_L"], duration)
            Wärmemenge = self.Wärmemenge_BHKW_Speicher
            Strommenge = self.Strommenge_BHKW_Speicher
            Brennstoffbedarf = self.Brennstoffbedarf_BHKW_Speicher
            Wärmeleistung_kW = self.Wärmeleistung_kW
            el_Leistung_BHKW = self.el_Leistung_BHKW_kW
            Anzahl_Starts = self.Anzahl_Starts_Speicher
            Betriebsstunden = self.Betriebsstunden_gesamt_Speicher
            Betriebsstunden_pro_Start = self.Betriebsstunden_pro_Start_Speicher
        else:
            self.simulate_operation(general_results["Restlast_L"], duration)
            Wärmemenge = self.Wärmemenge_BHKW
            Strommenge = self.Strommenge_BHKW
            Brennstoffbedarf = self.Brennstoffbedarf_BHKW
            Wärmeleistung_kW = self.Wärmeleistung_kW
            el_Leistung_BHKW = self.el_Leistung_kW
            Anzahl_Starts = self.Anzahl_Starts
            Betriebsstunden = self.Betriebsstunden_gesamt
            Betriebsstunden_pro_Start = self.Betriebsstunden_pro_Start

        self.calculate_heat_generation_costs(Wärmemenge, Strommenge, Brennstoffbedarf, economic_parameters)
        self.calculate_environmental_impact(Wärmemenge, Strommenge, Brennstoffbedarf)
     
        results = {
            'Wärmemenge': Wärmemenge,
            'Wärmeleistung_L': Wärmeleistung_kW,
            'Brennstoffbedarf': Brennstoffbedarf,
            'WGK': self.WGK_BHKW,
            'Strommenge': Strommenge,
            'el_Leistung_L': el_Leistung_BHKW,
            'Anzahl_Starts': Anzahl_Starts,
            'Betriebsstunden': Betriebsstunden,
            'Betriebsstunden_pro_Start': Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            'color': "yellow"
        }

        if self.speicher_aktiv:
            results['Wärmeleistung_Speicher_L'] = self.Wärmeleistung_Speicher_kW

        return results
    
    def set_parameters(self, variables, variables_order, idx):
        try:
            self.th_Leistung_BHKW = variables[variables_order.index(f"th_Leistung_BHKW_{idx}")]
            if self.speicher_aktiv:
                self.Speicher_Volumen_BHKW = variables[variables_order.index(f"Speicher_Volumen_BHKW_{idx}")]
        except ValueError as e:
            print(f"Fehler beim Setzen der Parameter für {self.name}: {e}")

    def add_optimization_parameters(self, idx):
        """
        Fügt Optimierungsparameter für BHKW hinzu und gibt sie zurück.

        Args:
            idx (int): Index der Technologie in der Liste.

        Returns:
            tuple: Initiale Werte, Variablennamen und Grenzen der Variablen.
        """
        initial_values = [self.th_Leistung_BHKW]
        variables_order = [f"th_Leistung_BHKW_{idx}"]
        bounds = [(self.opt_BHKW_min, self.opt_BHKW_max)]

        if self.speicher_aktiv:
            initial_values.append(self.Speicher_Volumen_BHKW)
            variables_order.append(f"Speicher_Volumen_BHKW_{idx}")
            bounds.append((self.opt_BHKW_Speicher_min, self.opt_BHKW_Speicher_max))

        return initial_values, variables_order, bounds
    
    def update_parameters(self, optimized_values, variables_order, idx):
        """
        Aktualisiert die Parameter für BHKW.

        Args:
            optimized_values (list): Liste der optimierten Werte.
            variables_order (list): Liste der Variablennamen.
            idx (int): Index der Technologie in der Liste.
        """
        self.th_Leistung_BHKW = optimized_values[variables_order.index(f"th_Leistung_BHKW_{idx}")]
        if self.speicher_aktiv:
            self.Speicher_Volumen_BHKW = optimized_values[variables_order.index(f"Speicher_Volumen_BHKW_{idx}")]
    
    def get_display_text(self):
        if self.name.startswith("BHKW"):
            return (f"{self.name}: th. Leistung: {self.th_Leistung_BHKW} kW, "
                    f"spez. Investitionskosten Erdgas-BHKW: {self.spez_Investitionskosten_GBHKW} €/kW")
        elif self.name.startswith("Holzgas-BHKW"):
            return (f"{self.name}: th. Leistung: {self.th_Leistung_BHKW} kW, "
                    f"spez. Investitionskosten Holzgas-BHKW: {self.spez_Investitionskosten_HBHKW} €/kW")

