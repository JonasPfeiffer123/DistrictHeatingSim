"""
Filename: biomass_boiler.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: Contains the BiomassBoiler class representing a biomass boiler system.

"""

import numpy as np

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator

class BiomassBoiler(BaseHeatGenerator):
    """
    A class representing a biomass boiler system.

    Attributes:
        name (str): Name of the biomass boiler.
        P_BMK (float): Boiler power in kW.
        Größe_Holzlager (float): Size of the wood storage in cubic meters.
        spez_Investitionskosten (float): Specific investment costs for the boiler in €/kW.
        spez_Investitionskosten_Holzlager (float): Specific investment costs for the wood storage in €/m³.
        Nutzungsgrad_BMK (float): Efficiency of the biomass boiler.
        min_Teillast (float): Minimum part-load operation as a fraction of the nominal load.
        speicher_aktiv (bool): Indicates if a storage system is active.
        Speicher_Volumen (float): Volume of the thermal storage in cubic meters.
        T_vorlauf (float): Supply temperature in °C.
        T_ruecklauf (float): Return temperature in °C.
        initial_fill (float): Initial fill level of the storage as a fraction of the total volume.
        min_fill (float): Minimum fill level of the storage as a fraction of the total volume.
        max_fill (float): Maximum fill level of the storage as a fraction of the total volume.
        spez_Investitionskosten_Speicher (float): Specific investment costs for the thermal storage in €/m³.
        BMK_an (bool): Indicates if the boiler is on.
        opt_BMK_min (float): Minimum boiler capacity for optimization.
        opt_BMK_max (float): Maximum boiler capacity for optimization.
        opt_Speicher_min (float): Minimum storage capacity for optimization.
        opt_Speicher_max (float): Maximum storage capacity for optimization.
        Nutzungsdauer (int): Lifespan of the biomass boiler in years.
        f_Inst (float): Installation factor.
        f_W_Insp (float): Inspection factor.
        Bedienaufwand (float): Operational effort.
        co2_factor_fuel (float): CO2 factor for the fuel in tCO2/MWh.
        primärenergiefaktor (float): Primary energy factor for the fuel.
    """
    
    def __init__(self, name, P_BMK, Größe_Holzlager=40, spez_Investitionskosten=200, spez_Investitionskosten_Holzlager=400, Nutzungsgrad_BMK=0.8, min_Teillast=0.3,
                 speicher_aktiv=False, Speicher_Volumen=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, min_fill=0.2, max_fill=0.8, 
                 spez_Investitionskosten_Speicher=750, BMK_an=True, opt_BMK_min=0, opt_BMK_max=1000, opt_Speicher_min=0, opt_Speicher_max=100):
        super().__init__(name)
        self.P_BMK = P_BMK
        self.Größe_Holzlager = Größe_Holzlager
        self.spez_Investitionskosten = spez_Investitionskosten
        self.spez_Investitionskosten_Holzlager = spez_Investitionskosten_Holzlager
        self.Nutzungsgrad_BMK = Nutzungsgrad_BMK
        self.min_Teillast = min_Teillast
        self.speicher_aktiv = speicher_aktiv
        self.Speicher_Volumen = Speicher_Volumen
        self.T_vorlauf = T_vorlauf
        self.T_ruecklauf = T_ruecklauf
        self.initial_fill = initial_fill
        self.min_fill = min_fill
        self.max_fill = max_fill
        self.spez_Investitionskosten_Speicher = spez_Investitionskosten_Speicher
        self.BMK_an = BMK_an
        self.opt_BMK_min = opt_BMK_min
        self.opt_BMK_max = opt_BMK_max
        self.opt_Speicher_min = opt_Speicher_min
        self.opt_Speicher_max = opt_Speicher_max
        self.Nutzungsdauer = 15
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 3, 3, 0
        self.co2_factor_fuel = 0.036 # tCO2/MWh pellets
        self.primärenergiefaktor = 0.2 # Pellets

    def simulate_operation(self, Last_L, duration):
        """
        Simulates the operation of the biomass boiler.

        Args:
            Last_L (array): Load profile of the system in kW.
            duration (float): Duration of each time step in hours.

        Returns:
            None
        """
        self.Wärmeleistung_kW = np.zeros_like(Last_L)

        # Cases where the biomass boiler can operate
        betrieb_mask = Last_L >= self.P_BMK * self.min_Teillast
        self.Wärmeleistung_kW[betrieb_mask] = np.minimum(Last_L[betrieb_mask], self.P_BMK)

        self.Wärmemenge_BMK = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Brennstoffbedarf_BMK = self.Wärmemenge_BMK / self.Nutzungsgrad_BMK

        # Calculate number of starts and operating hours per start
        starts = np.diff(betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden_gesamt = np.sum(betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = self.Betriebsstunden_gesamt / self.Anzahl_Starts if self.Anzahl_Starts > 0 else 0

    def simulate_storage(self, Last_L, duration):
        """
        Simulates the operation of the storage system.

        Args:
            Last_L (array): Load profile of the system in kW.
            duration (float): Duration of each time step in hours.

        Returns:
            None
        """
        # Storage parameters
        speicher_kapazitaet = self.Speicher_Volumen * 4186 * (self.T_vorlauf - self.T_ruecklauf) / 3600  # kWh
        speicher_fill = self.initial_fill * speicher_kapazitaet
        min_speicher_fill = self.min_fill * speicher_kapazitaet
        max_speicher_fill = self.max_fill * speicher_kapazitaet

        self.Wärmeleistung_kW = np.zeros_like(Last_L)
        self.Wärmeleistung_Speicher_kW = np.zeros_like(Last_L)
        self.speicher_fuellstand = np.zeros_like(Last_L)

        for i in range(len(Last_L)):
            if self.BMK_an:
                if speicher_fill >= max_speicher_fill:
                    self.BMK_an = False
                else:
                    self.Wärmeleistung_kW[i] = self.P_BMK
                    if Last_L[i] < self.P_BMK:
                        self.Wärmeleistung_Speicher_kW[i] = Last_L[i] - self.P_BMK
                        speicher_fill += (self.P_BMK - Last_L[i]) * duration
                        speicher_fill = float(min(speicher_fill, speicher_kapazitaet))
                    else:
                        self.Wärmeleistung_Speicher_kW[i] = 0
            else:
                if speicher_fill <= min_speicher_fill:
                    self.BMK_an = True
            
            if not self.BMK_an:
                self.Wärmeleistung_kW[i] = 0
                self.Wärmeleistung_Speicher_kW[i] = Last_L[i]
                speicher_fill -= Last_L[i] * duration
                speicher_fill = float(max(speicher_fill, 0))

            self.speicher_fuellstand[i] = speicher_fill / speicher_kapazitaet * 100  # %

        self.Wärmemenge_Biomassekessel_Speicher = np.sum(self.Wärmeleistung_kW / 1000) * duration

        # Calculate fuel consumption
        self.Brennstoffbedarf_BMK_Speicher = self.Wärmemenge_Biomassekessel_Speicher / self.Nutzungsgrad_BMK

        # Calculate number of starts and operating hours per start
        betrieb_mask = self.Wärmeleistung_kW > 0
        starts = np.diff(betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts_Speicher = np.sum(starts)
        self.Betriebsstunden_gesamt_Speicher = np.sum(betrieb_mask) * duration
        self.Betriebsstunden_pro_Start_Speicher = self.Betriebsstunden_gesamt_Speicher / self.Anzahl_Starts_Speicher if self.Anzahl_Starts_Speicher > 0 else 0

    def calculate_heat_generation_cost(self, Wärmemenge, Brennstoffbedarf, economic_parameters):
        """
        Calculates the weighted average cost of heat generation.

        Args:
            Wärmemenge (float): Amount of heat generated.
            Brennstoffbedarf (float): Fuel consumption.
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

        if Wärmemenge == 0:
            return 0
        
        self.Investitionskosten_Kessel = self.spez_Investitionskosten * self.P_BMK
        self.Investitionskosten_Holzlager = self.spez_Investitionskosten_Holzlager * self.Größe_Holzlager
        self.Investitionskosten_Speicher = self.spez_Investitionskosten_Speicher * self.Speicher_Volumen
        self.Investitionskosten = self.Investitionskosten_Kessel + self.Investitionskosten_Holzlager + self.Investitionskosten_Speicher

        self.A_N = self.annuity(self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, self.q, self.r, self.T, 
                                Brennstoffbedarf, self.Holzpreis, stundensatz=self.stundensatz)
        
        self.WGK_BMK = self.A_N / Wärmemenge

    def calculate_environmental_impact(self, Brennstoffbedarf, Wärmemenge):
        """
        Calculates the environmental impact of the biomass boiler system.

        Args:
            None

        Returns:
            None
        """

        # CO2 emissions due to fuel usage
        self.co2_emissions = Brennstoffbedarf * self.co2_factor_fuel # tCO2
        # specific emissions heat
        self.spec_co2_total = self.co2_emissions / Wärmemenge if Wärmemenge > 0 else 0 # tCO2/MWh_heat

        self.primärenergie = Brennstoffbedarf * self.primärenergiefaktor
        

    def calculate(self, economic_parameters, duration, general_results, **kwargs):
        """
        Calculates the performance and cost of the biomass boiler system.

        Args:
            economic_parameters (dict): Dictionary containing economic parameters.
            duration (float): Duration of each time step in hours.
            general_results (dict): General results dictionary containing rest load.

        Returns:
            dict: Dictionary containing the results of the calculation.
        """
        if self.speicher_aktiv:
            self.simulate_storage(general_results["Restlast_L"], duration)
            Wärmemenge = self.Wärmemenge_Biomassekessel_Speicher
            Brennstoffbedarf = self.Brennstoffbedarf_BMK_Speicher
            Wärmeleistung_kW = self.Wärmeleistung_kW
            Anzahl_Starts = self.Anzahl_Starts_Speicher
            Betriebsstunden = self.Betriebsstunden_gesamt_Speicher
            Betriebsstunden_pro_Start = self.Betriebsstunden_pro_Start_Speicher
        else:
            self.simulate_operation(general_results["Restlast_L"], duration)
            Wärmemenge = self.Wärmemenge_BMK
            Brennstoffbedarf = self.Brennstoffbedarf_BMK
            Wärmeleistung_kW = self.Wärmeleistung_kW
            Anzahl_Starts = self.Anzahl_Starts
            Betriebsstunden = self.Betriebsstunden_gesamt
            Betriebsstunden_pro_Start = self.Betriebsstunden_pro_Start

        self.calculate_heat_generation_cost(Wärmemenge, Brennstoffbedarf, economic_parameters)
        self.calculate_environmental_impact(Brennstoffbedarf, Wärmemenge)

        results = {
            'Wärmemenge': Wärmemenge,
            'Wärmeleistung_L': Wärmeleistung_kW,
            'Brennstoffbedarf': Brennstoffbedarf,
            'WGK': self.WGK_BMK,
            'Anzahl_Starts': Anzahl_Starts,
            'Betriebsstunden': Betriebsstunden,
            'Betriebsstunden_pro_Start': Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            'color': "green"
        }

        if self.speicher_aktiv:
            results['Wärmeleistung_Speicher_L'] = self.Wärmeleistung_Speicher_kW

        return results
    
    def set_parameters(self, variables, variables_order, idx):
        try:
            self.P_BMK = variables[variables_order.index(f"P_BMK_{idx}")]
        except ValueError as e:
            print(f"Fehler beim Setzen der Parameter für {self.name}: {e}")

    def add_optimization_parameters(self, idx):
        """
        Fügt Optimierungsparameter für Biomassekessel hinzu und gibt sie zurück.

        Args:
            idx (int): Index der Technologie in der Liste.

        Returns:
            tuple: Initiale Werte, Variablennamen und Grenzen der Variablen.
        """
        initial_values = [self.P_BMK]
        variables_order = [f"P_BMK_{idx}"]
        bounds = [(self.opt_BMK_min, self.opt_BMK_max)]

        if self.speicher_aktiv:
            initial_values.append(self.Speicher_Volumen)
            variables_order.append(f"Speicher_Volumen_{idx}")
            bounds.append((self.opt_Speicher_min, self.opt_Speicher_max))

        return initial_values, variables_order, bounds
    
    def update_parameters(self, optimized_values, variables_order, idx):
        """
        Aktualisiert die Parameter für Biomassekessel.

        Args:
            optimized_values (list): Liste der optimierten Werte.
            variables_order (list): Liste der Variablennamen.
            idx (int): Index der Technologie in der Liste.
        """
        self.P_BMK = optimized_values[variables_order.index(f"P_BMK_{idx}")]
        if self.speicher_aktiv:
            self.Speicher_Volumen = optimized_values[variables_order.index(f"Speicher_Volumen_{idx}")]

    def get_display_text(self):
        return (f"{self.name}: th. Leistung: {self.P_BMK}, Größe Holzlager: {self.Größe_Holzlager} t, "
                f"spez. Investitionskosten Kessel: {self.spez_Investitionskosten} €/kW, "
                f"spez. Investitionskosten Holzlager: {self.spez_Investitionskosten_Holzlager} €/t")

