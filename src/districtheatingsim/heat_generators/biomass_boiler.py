"""
Filename: biomass_boiler.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: Contains the BiomassBoiler class representing a biomass boiler system.

"""

import numpy as np

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy

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
    
    def __init__(self, name, thermal_capacity_kW, Größe_Holzlager=40, spez_Investitionskosten=200, spez_Investitionskosten_Holzlager=400, Nutzungsgrad_BMK=0.8, min_Teillast=0.3,
                 speicher_aktiv=False, Speicher_Volumen=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, min_fill=0.2, max_fill=0.8, 
                 spez_Investitionskosten_Speicher=750, active=True, opt_BMK_min=0, opt_BMK_max=1000, opt_Speicher_min=0, opt_Speicher_max=100):
        super().__init__(name)
        self.thermal_capacity_kW = thermal_capacity_kW
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
        self.active = active
        self.opt_BMK_min = opt_BMK_min
        self.opt_BMK_max = opt_BMK_max
        self.opt_Speicher_min = opt_Speicher_min
        self.opt_Speicher_max = opt_Speicher_max
        self.Nutzungsdauer = 15
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 3, 3, 0
        self.co2_factor_fuel = 0.036 # tCO2/MWh pellets
        self.primärenergiefaktor = 0.2 # Pellets

        self.strategy = BiomassBoilerStrategy(75, 70)

        self.init_operation(8760)

    def init_operation(self, hours):
        self.betrieb_mask = np.array([False] * hours)
        self.Wärmeleistung_kW = np.array([0] * hours)
        self.Wärmemenge_MWh = 0
        self.Brennstoffbedarf_MWh = 0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0
        self.Betriebsstunden_pro_Start = 0
        
        self.calculated = False  # Flag to indicate if the calculation is done

    def simulate_operation(self, Last_L):
        """
        Simulates the operation of the biomass boiler.

        Args:
            Last_L (array): Load profile of the system in kW.
            duration (float): Duration of each time step in hours.

        Returns:
            None
        """

        # Cases where the biomass boiler can operate
        self.betrieb_mask = Last_L >= self.thermal_capacity_kW * self.min_Teillast
        self.Wärmeleistung_kW[self.betrieb_mask] = np.minimum(Last_L[self.betrieb_mask], self.thermal_capacity_kW)

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

        self.Wärmeleistung_Speicher_kW = np.zeros_like(Last_L)
        self.Speicher_Fuellstand = np.zeros_like(Last_L)

        for i in range(len(Last_L)):
            if self.active:
                if speicher_fill >= max_speicher_fill:
                    self.active = False
                else:
                    self.Wärmeleistung_kW[i] = self.thermal_capacity_kW
                    if Last_L[i] < self.thermal_capacity_kW:
                        self.Wärmeleistung_Speicher_kW[i] = Last_L[i] - self.thermal_capacity_kW
                        speicher_fill += (self.thermal_capacity_kW - Last_L[i]) * duration
                        speicher_fill = float(min(speicher_fill, speicher_kapazitaet))
                    else:
                        self.Wärmeleistung_Speicher_kW[i] = 0
            else:
                if speicher_fill <= min_speicher_fill:
                    self.active = True
            
            if not self.active:
                self.Wärmeleistung_kW[i] = 0
                self.Wärmeleistung_Speicher_kW[i] = Last_L[i]
                speicher_fill -= Last_L[i] * duration
                speicher_fill = float(max(speicher_fill, 0))

            self.Speicher_Fuellstand[i] = speicher_fill / speicher_kapazitaet * 100  # %

        self.betrieb_mask = self.Wärmeleistung_kW > 0

    def generate(self, t, **kwargs):
        """
        Generates heat for the biomass boiler system.

        Args:
            t (int): Current time step.
            **kwargs: Additional arguments.

        Returns:
            tuple: Heat generation and electricity generation.
        """
        
        if self.active:
            self.betrieb_mask[t] = True
            self.Wärmeleistung_kW[t] = self.thermal_capacity_kW

        else:
            self.betrieb_mask[t] = False
            self.Wärmeleistung_kW[t] = 0

        return self.Wärmeleistung_kW[t], 0 # Wärmeleistung in kW, Stromerzeugung in kW
    
    def calculate_results(self, duration):
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Brennstoffbedarf_MWh = self.Wärmemenge_MWh / self.Nutzungsgrad_BMK

        # Anzahl Starts und Betriebsstunden pro Start berechnen
        starts = np.diff(self.betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(self.betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = self.Betriebsstunden / self.Anzahl_Starts if self.Anzahl_Starts > 0 else 0

    def calculate_heat_generation_costs(self, economic_parameters):
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
        
        self.Investitionskosten_Kessel = self.spez_Investitionskosten * self.thermal_capacity_kW
        self.Investitionskosten_Holzlager = self.spez_Investitionskosten_Holzlager * self.Größe_Holzlager
        self.Investitionskosten_Speicher = self.spez_Investitionskosten_Speicher * self.Speicher_Volumen
        self.Investitionskosten = self.Investitionskosten_Kessel + self.Investitionskosten_Holzlager + self.Investitionskosten_Speicher

        self.A_N = self.annuity(self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, self.q, self.r, self.T, 
                                self.Brennstoffbedarf_MWh, self.Holzpreis, hourly_rate=self.stundensatz)
        
        self.WGK = self.A_N / self.Wärmemenge_MWh

    def calculate_environmental_impact(self):
        """
        Calculates the environmental impact of the biomass boiler system.

        """

        # CO2 emissions due to fuel usage
        self.co2_emissions = self.Brennstoffbedarf_MWh * self.co2_factor_fuel # tCO2
        # specific emissions heat
        self.spec_co2_total = self.co2_emissions / self.Wärmemenge_MWh if self.Wärmemenge_MWh > 0 else 0 # tCO2/MWh_heat

        self.primärenergie = self.Brennstoffbedarf_MWh * self.primärenergiefaktor
        

    def calculate(self, economic_parameters, duration, load_profile, **kwargs):
        """
        Calculates the performance and cost of the biomass boiler system.

        Args:
            economic_parameters (dict): Dictionary containing economic parameters.
            duration (float): Duration of each time step in hours.
            load_profile (array): Load profile of the system in kW.

        Returns:
            dict: Dictionary containing the results of the calculation.
        """
        # Check if the calculation has already been done
        if self.calculated == False:
            if self.speicher_aktiv:
                self.simulate_storage(load_profile, duration)
            else:
                self.simulate_operation(load_profile)
            
        self.calculate_results(duration)
        self.calculate_heat_generation_costs(economic_parameters)
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
            'color': "green"
        }

        if self.speicher_aktiv:
            results['Wärmeleistung_Speicher_L'] = self.Wärmeleistung_Speicher_kW
            results['Speicherfüllstand_L'] = self.Speicher_Fuellstand

        return results
    
    def set_parameters(self, variables, variables_order, idx):
        try:
            self.thermal_capacity_kW = variables[variables_order.index(f"P_BMK_{idx}")]
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
        initial_values = [self.thermal_capacity_kW]
        variables_order = [f"P_BMK_{idx}"]
        bounds = [(self.opt_BMK_min, self.opt_BMK_max)]

        if self.speicher_aktiv:
            initial_values.append(self.Speicher_Volumen)
            variables_order.append(f"Speicher_Volumen_{idx}")
            bounds.append((self.opt_Speicher_min, self.opt_Speicher_max))

        return initial_values, variables_order, bounds

    def get_display_text(self):
        return (f"{self.name}: th. Leistung: {self.thermal_capacity_kW:.1f}, Größe Holzlager: {self.Größe_Holzlager:.1f} t, "
                f"spez. Investitionskosten Kessel: {self.spez_Investitionskosten:.1f} €/kW, "
                f"spez. Investitionskosten Holzlager: {self.spez_Investitionskosten_Holzlager:.1f} €/t")
    
    def extract_tech_data(self):
        dimensions = f"th. Leistung: {self.thermal_capacity_kW:.1f} kW, Größe Holzlager: {self.Größe_Holzlager:.1f} t"
        costs = f"Investitionskosten Kessel: {self.Investitionskosten_Kessel:.1f} €, Investitionskosten Holzlager: {self.Investitionskosten_Holzlager:.1f} €"
        full_costs = f"{self.Investitionskosten:.1f}"
        return self.name, dimensions, costs, full_costs

# Control strategy for Biomass Boiler
class BiomassBoilerStrategy(BaseStrategy):
    def __init__(self, charge_on, charge_off):
        """
        Initializes the Biomass Boiler strategy with switch points based on storage levels.

        Args:
            charge_on (int): (upper) Storage temperature to activate the boiler.
            charge_off (int): (lower) Storage temperature to deactivate the boiler.
        """
        super().__init__(charge_on, charge_off)
