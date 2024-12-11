"""
Filename: heat_pumps.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: Contains classes for different types of heat pumps and methods to calculate performance and economic metrics.

"""

import numpy as np
from scipy.interpolate import RegularGridInterpolator

import CoolProp.CoolProp as CP

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator

class HeatPump(BaseHeatGenerator):
    """
    This class represents a Heat Pump and provides methods to calculate various performance and economic metrics.

    Attributes:
        name (str): The name of the heat pump.
        spezifische_Investitionskosten_WP (float): Specific investment costs of the heat pump per kW. Default is 1000.
        Nutzungsdauer_WP (int): Useful life of the heat pump in years. Default is 20.
        f_Inst_WP (float): Installation factor for the heat pump. Default is 1.
        f_W_Insp_WP (float): Maintenance and inspection factor for the heat pump. Default is 1.5.
        Bedienaufwand_WP (float): Operating effort in hours for the heat pump. Default is 0.
        f_Inst_WQ (float): Installation factor for the heat source. Default is 0.5.
        f_W_Insp_WQ (float): Maintenance and inspection factor for the heat source. Default is 0.5.
        Bedienaufwand_WQ (float): Operating effort in hours for the heat source. Default is 0.
        Nutzungsdauer_WQ_dict (dict): Dictionary containing useful life of different heat sources.
        co2_factor_electricity (float): CO2 emission factor for electricity in tCO2/MWh. Default is 2.4.

    Methods:
        COP_WP(VLT_L, QT, COP_data): Calculates the Coefficient of Performance (COP) of the heat pump.
        WGK(Wärmeleistung, Wärmemenge, Strombedarf, spez_Investitionskosten_WQ, Strompreis, q, r, T, BEW, stundensatz): Calculates the heat generation costs (WGK).
    """

    def __init__(self, name, spezifische_Investitionskosten_WP=1000):
        super().__init__(name)
        self.spezifische_Investitionskosten_WP = spezifische_Investitionskosten_WP
        self.Nutzungsdauer_WP = 20
        self.f_Inst_WP, self.f_W_Insp_WP, self.Bedienaufwand_WP = 1, 1.5, 0
        self.f_Inst_WQ, self.f_W_Insp_WQ, self.Bedienaufwand_WQ = 0.5, 0.5, 0
        self.Nutzungsdauer_WQ_dict = {"Abwärme": 20, "Abwasserwärme": 20, "Flusswasser": 20, "Geothermie": 30}
        self.co2_factor_electricity = 2.4 # tCO2/MWh electricity

    def calculate_COP(self, VLT_L, QT, COP_data):
        """
        Calculates the Coefficient of Performance (COP) of the heat pump using interpolation.

        Args:
            VLT_L (array-like): Flow temperatures.
            QT (float or array-like): Source temperatures.
            COP_data (array-like): COP data for interpolation.

        Returns:
            tuple: Interpolated COP values and adjusted flow temperatures.
        """

        # Interpolationsformel für den COP
        values = COP_data  # np.genfromtxt('Kennlinien WP.csv', delimiter=';')
        row_header = values[0, 1:]  # Vorlauftemperaturen
        col_header = values[1:, 0]  # Quelltemperaturen
        values = values[1:, 1:]

        f = RegularGridInterpolator((col_header, row_header), values, method='linear', bounds_error=False, fill_value=None)

        # Technische Grenze der Wärmepumpe ist Temperaturhub von 75 °C
        VLT_L = np.minimum(VLT_L, 75 + QT)

        # Überprüfen, ob QT eine Zahl oder ein Array ist
        if np.isscalar(QT):
            # Wenn QT eine Zahl ist, erstellen wir ein Array mit dieser Zahl
            QT_array = np.full_like(VLT_L, QT)
        else:
            # Wenn QT bereits ein Array ist, prüfen wir, ob es die gleiche Länge wie VLT_L hat
            if len(QT) != len(VLT_L):
                raise ValueError("QT muss entweder eine einzelne Zahl oder ein Array mit der gleichen Länge wie VLT_L sein.")
            QT_array = QT

        # Vorbereitung für die Interpolation
        input_array = np.column_stack((QT_array, VLT_L))

        # Initialisiere COP_L mit NaNs, um ungültige Werte zu markieren
        COP_L = np.full_like(VLT_L, np.nan)

        try:
            # Berechne die COPs für alle Werte, wobei ungültige Werte nicht extrapoliert werden
            COP_L = f(input_array)
            
            # Für ungültige Werte (wo keine Interpolation möglich ist), setze COP auf 0
            out_of_bounds_mask = np.isnan(COP_L)
            COP_L[out_of_bounds_mask] = 0  # Setzt nur die ungültigen Werte auf 0
            
            if np.any(out_of_bounds_mask):
                print(f"Einige Werte waren außerhalb des gültigen Bereichs und wurden auf 0 gesetzt.")
        except ValueError as e:
            # Dies wird normalerweise nicht mehr auftreten, aber falls doch, behandeln wir es weiterhin
            print(f"Interpolation error: {e}. Setting COP to 0 for values out of bounds.")
            COP_L = np.zeros_like(VLT_L)

        return COP_L, VLT_L

    
    def calculate_heat_generation_costs(self, Wärmeleistung, Wärmemenge, Strombedarf, spez_Investitionskosten_WQ, economic_parameters):
        """
        Calculates the heat generation costs (WGK) of the heat pump.

        Args:
            Wärmeleistung (float): Heat output of the heat pump.
            Wärmemenge (float): Amount of heat produced.
            Strombedarf (float): Electricity demand.
            spez_Investitionskosten_WQ (float): Specific investment costs for the heat source.
            economic_parameters (dict): Economic parameters dictionary containing fuel costs, capital interest rate, inflation rate, time period, and operational costs.

        Returns:
            float: Calculated heat generation costs.
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
        # Kosten Wärmepumpe: Viessmann Vitocal 350 HT-Pro: 140.000 €, 350 kW Nennleistung; 120 kW bei 10/85
        # Annahme Kosten Wärmepumpe: 1000 €/kW; Vereinfachung
        spezifische_Investitionskosten_WP = self.spezifische_Investitionskosten_WP
        Investitionskosten_WP = spezifische_Investitionskosten_WP * round(Wärmeleistung, 0)
        E1_WP = self.annuity(Investitionskosten_WP, self.Nutzungsdauer_WP, self.f_Inst_WP, self.f_W_Insp_WP, self.Bedienaufwand_WP, self.q, self.r, self.T,
                            Strombedarf, self.Strompreis, stundensatz=self.stundensatz)
        WGK_WP_a = E1_WP / Wärmemenge

        # Extrahieren des Basisnamens aus dem Namen des Erzeugers
        base_name = self.name.split('_')[0]
        
        # Überprüfen, ob der Basisname in Nutzungsdauer_WQ_dict vorhanden ist
        if base_name not in self.Nutzungsdauer_WQ_dict:
            raise KeyError(f"{base_name} ist kein gültiger Schlüssel in Nutzungsdauer_WQ_dict")
        
        Investitionskosten_WQ = spez_Investitionskosten_WQ * Wärmeleistung
        E1_WQ = self.annuity(Investitionskosten_WQ, self.Nutzungsdauer_WQ_dict[base_name], self.f_Inst_WQ, self.f_W_Insp_WQ,
                            self.Bedienaufwand_WQ, self.q, self.r, self.T, stundensatz=self.stundensatz)
        WGK_WQ_a = E1_WQ / Wärmemenge

        WGK_Gesamt_a = WGK_WP_a + WGK_WQ_a

        return WGK_Gesamt_a

class RiverHeatPump(HeatPump):
    """
    This class represents a River Heat Pump and provides methods to calculate various performance and economic metrics.

    Args:
        HeatPump (_type_): Base class for the heat pump.

    Attributes:
        Wärmeleistung_FW_WP (float): Heat output of the river water heat pump.
        Temperatur_FW_WP (float): Temperature of the river water.
        dT (float): Temperature difference. Default is 0.
        spez_Investitionskosten_Flusswasser (float): Specific investment costs for river water heat pump per kW. Default is 1000.
        spezifische_Investitionskosten_WP (float): Specific investment costs of the heat pump per kW. Default is 1000.
        min_Teillast (float): Minimum partial load. Default is 0.2.
        co2_factor_electricity (float): CO2 emission factor for electricity in tCO2/MWh. Default is 0.4.
        primärenergiefaktor (float): Primary energy factor. Default is 2.4.

    Methods:
        Berechnung_WP(Wärmeleistung_L, VLT_L, COP_data): Calculates the cooling load, electric power consumption, and adjusted flow temperatures.
        abwärme(Last_L, VLT_L, COP_data, duration): Calculates the waste heat and other performance metrics.
        calculate(VLT_L, COP_data, Strompreis, q, r, T, BEW, stundensatz, duration, general_results): Calculates the economic and environmental metrics for the heat pump.
        to_dict(): Converts the object attributes to a dictionary.
        from_dict(data): Creates an object from a dictionary of attributes.
    """
    def __init__(self, name, Wärmeleistung_FW_WP, Temperatur_FW_WP, dT=0, spez_Investitionskosten_Flusswasser=1000, spezifische_Investitionskosten_WP=1000, min_Teillast=0.2,
                 opt_power_min=0, opt_power_max=500):
        super().__init__(name, spezifische_Investitionskosten_WP=spezifische_Investitionskosten_WP)
        self.Wärmeleistung_FW_WP = Wärmeleistung_FW_WP
        self.Temperatur_FW_WP = Temperatur_FW_WP
        self.dT = dT
        self.spez_Investitionskosten_Flusswasser = spez_Investitionskosten_Flusswasser
        self.min_Teillast = min_Teillast
        self.opt_power_min = opt_power_min
        self.opt_power_max = opt_power_max
        self.co2_factor_electricity = 0.4 # tCO2/MWh electricity
        self.primärenergiefaktor = 2.4

    def calculate_heat_pump(self, Wärmeleistung_L, VLT_L, COP_data):
        """
        Calculates the cooling load, electric power consumption, and adjusted flow temperatures for the heat pump.

        Args:
            Wärmeleistung_L (array-like): Heat output load.
            VLT_L (array-like): Flow temperatures.
            COP_data (array-like): COP data for interpolation.

        Returns:
            tuple: Cooling load, electric power consumption, and adjusted flow temperatures.
        """
        COP_L, VLT_L_WP = self.calculate_COP(VLT_L, self.Temperatur_FW_WP, COP_data)
        Kühlleistung_L = Wärmeleistung_L * (1 - (1 / COP_L))
        el_Leistung_L = Wärmeleistung_L - Kühlleistung_L
        return Kühlleistung_L, el_Leistung_L, VLT_L_WP

    # Änderung Kühlleistung und Temperatur zu Numpy-Array in aw sowie vor- und nachgelagerten Funktionen
    def calculate_operation(self, Last_L, VLT_L, COP_data, duration):
        """
        Calculates the waste heat and other performance metrics for the heat pump.

        Args:
            Last_L (array-like): Load demand.
            VLT_L (array-like): Flow temperatures.
            COP_data (array-like): COP data for interpolation.
            duration (float): Time duration.

        Returns:
            tuple: Heat energy, electricity demand, heat output, electric power, cooling energy, and cooling load.
        """
        if self.Wärmeleistung_FW_WP == 0:
            return 0, 0, np.zeros_like(Last_L), np.zeros_like(VLT_L), 0, np.zeros_like(VLT_L)

        self.Wärmeleistung_kW = np.zeros_like(Last_L)
        self.Kühlleistung_kW = np.zeros_like(Last_L)
        self.el_Leistung_kW = np.zeros_like(Last_L)
        VLT_L_WP = np.zeros_like(VLT_L)

        # Fälle, in denen die Wärmepumpe betrieben werden kann
        betrieb_mask = Last_L >= self.Wärmeleistung_FW_WP * self.min_Teillast
        self.Wärmeleistung_kW[betrieb_mask] = np.minimum(Last_L[betrieb_mask], self.Wärmeleistung_FW_WP)

        self.Kühlleistung_kW[betrieb_mask], self.el_Leistung_kW[betrieb_mask], VLT_L_WP[betrieb_mask] = self.calculate_heat_pump(self.Wärmeleistung_kW[betrieb_mask], VLT_L[betrieb_mask], COP_data)

        # Wärmepumpe soll nur in Betrieb sein, wenn Sie die Vorlauftemperatur erreichen kann
        betrieb_mask_vlt = VLT_L_WP >= VLT_L - self.dT
        self.Wärmeleistung_kW[~betrieb_mask_vlt] = 0
        self.Kühlleistung_kW[~betrieb_mask_vlt] = 0
        self.el_Leistung_kW[~betrieb_mask_vlt] = 0

        self.Wärmemenge = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Kühlmenge = np.sum(self.Kühlleistung_kW / 1000) * duration
        self.Strombedarf = np.sum(self.el_Leistung_kW / 1000) * duration
    
    def calculate_environmental_impact(self):
        # CO2 emissions due to fuel usage
        self.co2_emissions = self.Strombedarf * self.co2_factor_electricity # tCO2
        # specific emissions heat
        self.spec_co2_total = self.co2_emissions / self.Wärmemenge if self.Wärmemenge > 0 else 0 # tCO2/MWh_heat

        self.primärenergie = self.Strombedarf * self.primärenergiefaktor
    
    def calculate(self, economic_parameters, duration, general_results, **kwargs):
        VLT_L = kwargs.get('VLT_L')
        COP_data = kwargs.get('COP_data')

        """
        Calculates the economic and environmental metrics for the river heat pump.

        Args:
            VLT_L (array-like): Flow temperatures.
            COP_data (array-like): COP data for interpolation.
            Strompreis (float): Price of electricity.
            duration (float): Time duration.
            general_results (dict): Dictionary containing general results and metrics.

        Returns:
            dict: Dictionary containing calculated metrics and results.
        """
        
        self.calculate_operation(general_results["Restlast_L"], VLT_L, COP_data, duration)
        WGK_Abwärme = self.calculate_heat_generation_costs(self.Wärmeleistung_FW_WP, self.Wärmemenge, self.Strombedarf, self.spez_Investitionskosten_Flusswasser, economic_parameters)
        self.calculate_environmental_impact()

        results = {
            'Wärmemenge': self.Wärmemenge,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'Strombedarf': self.Strombedarf,
            'el_Leistung_L': self.el_Leistung_kW,
            'WGK': WGK_Abwärme,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            'color': "blue"
        }

        return results
    
    def set_parameters(self, variables, variables_order, idx):
        try:
            self.Wärmeleistung_FW_WP = variables[variables_order.index(f"Wärmeleistung_FW_WP_{idx}")]
        except ValueError as e:
            print(f"Fehler beim Setzen der Parameter für {self.name}: {e}")

    def add_optimization_parameters(self, idx):
        """
        Fügt Optimierungsparameter für Flusswasser-Wärmepumpen hinzu und gibt sie zurück.

        Args:
            idx (int): Index der Technologie in der Liste.

        Returns:
            tuple: Initiale Werte, Variablennamen und Grenzen der Variablen.
        """
        initial_values = [self.Wärmeleistung_FW_WP]
        variables_order = [f"Wärmeleistung_FW_WP_{idx}"]
        bounds = [(self.opt_power_min, self.opt_power_max)]
        
        return initial_values, variables_order, bounds
    
    def update_parameters(self, optimized_values, variables_order, idx):
        """
        Aktualisiert die Parameter für Flusswasser-Wärmepumpen.

        Args:
            optimized_values (list): Liste der optimierten Werte.
            variables_order (list): Liste der Variablennamen.
            idx (int): Index der Technologie in der Liste.
        """
        self.Wärmeleistung_FW_WP = optimized_values[variables_order.index(f"Wärmeleistung_FW_WP_{idx}")]

    def get_display_text(self):
        return (f"{self.name}: Wärmeleistung FW WP: {self.Wärmeleistung_FW_WP} kW, "
                f"Temperatur FW WP: {self.Temperatur_FW_WP} °C, dT: {self.dT} K, "
                f"spez. Investitionskosten Flusswärme: {self.spez_Investitionskosten_Flusswasser} €/kW, "
                f"spez. Investitionskosten Wärmepumpe: {self.spezifische_Investitionskosten_WP} €/kW")

class WasteHeatPump(HeatPump):
    """
    This class represents a Waste Heat Pump and provides methods to calculate various performance and economic metrics.

    Args:
        HeatPump (_type_): Base class for the heat pump.

    Attributes:
        Kühlleistung_Abwärme (float): Cooling capacity of the waste heat pump.
        Temperatur_Abwärme (float): Temperature of the waste heat.
        spez_Investitionskosten_Abwärme (float): Specific investment costs for waste heat pump per kW. Default is 500.
        spezifische_Investitionskosten_WP (float): Specific investment costs of the heat pump per kW. Default is 1000.
        min_Teillast (float): Minimum partial load. Default is 0.2.
        co2_factor_electricity (float): CO2 emission factor for electricity in tCO2/MWh. Default is 0.4.
        primärenergiefaktor (float): Primary energy factor. Default is 2.4.

    Methods:
        Berechnung_WP(VLT_L, COP_data): Calculates the heat load, electric power consumption, and adjusted flow temperatures.
        abwärme(Last_L, VLT_L, COP_data, duration): Calculates the waste heat and other performance metrics.
        calculate(VLT_L, COP_data, Strompreis, q, r, T, BEW, stundensatz, duration, general_results): Calculates the economic and environmental metrics for the heat pump.
        to_dict(): Converts the object attributes to a dictionary.
        from_dict(data): Creates an object from a dictionary of attributes.
    """
    def __init__(self, name, Kühlleistung_Abwärme, Temperatur_Abwärme, spez_Investitionskosten_Abwärme=500, spezifische_Investitionskosten_WP=1000, min_Teillast=0.2,
                 opt_cooling_min=0, opt_cooling_max=500):
        super().__init__(name, spezifische_Investitionskosten_WP=spezifische_Investitionskosten_WP)
        self.Kühlleistung_Abwärme = Kühlleistung_Abwärme
        self.Temperatur_Abwärme = Temperatur_Abwärme
        self.spez_Investitionskosten_Abwärme = spez_Investitionskosten_Abwärme
        self.min_Teillast = min_Teillast
        self.opt_cooling_min = opt_cooling_min
        self.opt_cooling_max = opt_cooling_max
        self.co2_factor_electricity = 0.4 # tCO2/MWh electricity
        self.primärenergiefaktor = 2.4

    def calculate_heat_pump(self, VLT_L, COP_data):
        """
        Calculates the heat load, electric power consumption, and adjusted flow temperatures for the waste heat pump.

        Args:
            VLT_L (array-like): Flow temperatures.
            COP_data (array-like): COP data for interpolation.

        Returns:
            tuple: Heat load, electric power consumption.
        """
        COP_L, VLT_L = self.calculate_COP(VLT_L, self.Temperatur_Abwärme, COP_data)
        Wärmeleistung_L = self.Kühlleistung_Abwärme / (1 - (1 / COP_L))
        el_Leistung_L = Wärmeleistung_L - self.Kühlleistung_Abwärme
        return Wärmeleistung_L, el_Leistung_L

    def calculate_operation(self, Last_L, VLT_L, COP_data, duration):
        """
        Calculates the waste heat and other performance metrics for the waste heat pump.

        Args:
            Last_L (array-like): Load demand.
            VLT_L (array-like): Flow temperatures.
            COP_data (array-like): COP data for interpolation.
            duration (float): Time duration.

        Returns:
            tuple: Heat energy, electricity demand, heat output, electric power.
        """
        if self.Kühlleistung_Abwärme == 0:
            return 0, 0, np.zeros_like(Last_L), np.zeros_like(VLT_L)

        Wärmeleistung_L, el_Leistung_L = self.calculate_heat_pump(VLT_L, COP_data)

        self.Wärmeleistung_kW = np.zeros_like(Last_L)
        self.el_Leistung_kW = np.zeros_like(Last_L)

        # Cases where the heat pump can be operated
        betrieb_mask = Last_L >= Wärmeleistung_L * self.min_Teillast
        self.Wärmeleistung_kW[betrieb_mask] = np.minimum(Last_L[betrieb_mask], Wärmeleistung_L[betrieb_mask])
        self.el_Leistung_kW[betrieb_mask] = self.Wärmeleistung_kW[betrieb_mask] - (self.Wärmeleistung_kW[betrieb_mask] / Wärmeleistung_L[betrieb_mask]) * el_Leistung_L[betrieb_mask]

        self.Wärmemenge = np.sum(self.Wärmeleistung_kW / 1000) * duration
        self.Strombedarf = np.sum(self.el_Leistung_kW / 1000) * duration

        self.max_Wärmeleistung = np.max(self.Wärmeleistung_kW)
    
    def calculate_environmental_impact(self):
        # CO2 emissions due to fuel usage
        self.co2_emissions = self.Strombedarf * self.co2_factor_electricity # tCO2
        # specific emissions heat
        self.spec_co2_total = self.co2_emissions / self.Wärmemenge if self.Wärmemenge > 0 else 0 # tCO2/MWh_heat

        self.primärenergie = self.Strombedarf * self.primärenergiefaktor
    
    def calculate(self, economic_parameters, duration, general_results, **kwargs):
        VLT_L = kwargs.get('VLT_L')
        COP_data = kwargs.get('COP_data')

        """
        Calculates the economic and environmental metrics for the waste heat pump.

        Args:
            VLT_L (array-like): Flow temperatures.
            COP_data (array-like): COP data for interpolation.
            economic_parameters (dict): Economic parameters dictionary containing fuel costs, capital interest rate, inflation rate, time period, and operational costs.
            duration (float): Time duration.
            general_results (dict): Dictionary containing general results and metrics.

        Returns:
            dict: Dictionary containing calculated metrics and results.
        """

        self.calculate_operation(general_results['Restlast_L'], VLT_L, COP_data, duration)
        WGK_Abwärme = self.calculate_heat_generation_costs(self.max_Wärmeleistung, self.Wärmemenge, self.Strombedarf, self.spez_Investitionskosten_Abwärme, economic_parameters)

        self.calculate_environmental_impact()

        results = {
            'Wärmemenge': self.Wärmemenge,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'Strombedarf': self.Strombedarf,
            'el_Leistung_L': self.el_Leistung_kW,
            'WGK': WGK_Abwärme,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            'color': "grey"
        }

        return results
    
    def set_parameters(self, variables, variables_order, idx):
        try:
            self.Kühlleistung_Abwärme = variables[variables_order.index(f"Kühlleistung_Abwärme_{idx}")]
        except ValueError as e:
            print(f"Fehler beim Setzen der Parameter für {self.name}: {e}")

    def add_optimization_parameters(self, idx):
        """
        Fügt Optimierungsparameter für Abwärme hinzu und gibt sie zurück.

        Args:
            idx (int): Index der Technologie in der Liste.

        Returns:
            tuple: Initiale Werte, Variablennamen und Grenzen der Variablen.
        """
        initial_values = [self.Kühlleistung_Abwärme]
        variables_order = [f"Kühlleistung_Abwärme_{idx}"]
        bounds = [(self.opt_cooling_min, self.opt_cooling_max)]

        return initial_values, variables_order, bounds
    
    def update_parameters(self, optimized_values, variables_order, idx):
        """
        Aktualisiert die Parameter für Abwärme.

        Args:
            optimized_values (list): Liste der optimierten Werte.
            variables_order (list): Liste der Variablennamen.
            idx (int): Index der Technologie in der Liste.
        """
        self.Kühlleistung_Abwärme = optimized_values[variables_order.index(f"Kühlleistung_Abwärme_{idx}")]
    
    def get_display_text(self):
        return (f"{self.name}: Kühlleistung Abwärme: {self.Kühlleistung_Abwärme} kW, "
                f"Temperatur Abwärme: {self.Temperatur_Abwärme} °C, spez. Investitionskosten Abwärme: "
                f"{self.spez_Investitionskosten_Abwärme} €/kW, spez. Investitionskosten Wärmepumpe: "
                f"{self.spezifische_Investitionskosten_WP} €/kW")

class Geothermal(HeatPump):
    """
    This class represents a Geothermal Heat Pump and provides methods to calculate various performance and economic metrics.

    Args:
        HeatPump (_type_): Base class for the heat pump.

    Attributes:
        Fläche (float): Area available for geothermal installation.
        Bohrtiefe (float): Drilling depth for geothermal wells.
        Temperatur_Geothermie (float): Temperature of the geothermal source.
        spez_Bohrkosten (float): Specific drilling costs per meter. Default is 100.
        spez_Entzugsleistung (float): Specific extraction performance per meter. Default is 50.
        Vollbenutzungsstunden (float): Full utilization hours per year. Default is 2400.
        Abstand_Sonden (float): Distance between probes. Default is 10.
        min_Teillast (float): Minimum partial load. Default is 0.2.
        co2_factor_electricity (float): CO2 emission factor for electricity in tCO2/MWh. Default is 0.4.
        primärenergiefaktor (float): Primary energy factor. Default is 2.4.

    Methods:
        Geothermie(Last_L, VLT_L, COP_data, duration): Calculates the geothermal heat extraction and other performance metrics.
        calculate(VLT_L, COP_data, Strompreis, q, r, T, BEW, stundensatz, duration, general_results): Calculates the economic and environmental metrics for the geothermal heat pump.
        to_dict(): Converts the object attributes to a dictionary.
        from_dict(data): Creates an object from a dictionary of attributes.
    """
    def __init__(self, name, Fläche, Bohrtiefe, Temperatur_Geothermie, spez_Bohrkosten=100, spez_Entzugsleistung=50,
                 Vollbenutzungsstunden=2400, Abstand_Sonden=10, spezifische_Investitionskosten_WP=1000, min_Teillast=0.2, 
                 min_area_geothermal=0, max_area_geothermal=5000, min_depth_geothermal=0, max_depth_geothermal=400):
        super().__init__(name, spezifische_Investitionskosten_WP=spezifische_Investitionskosten_WP)
        self.Fläche = Fläche
        self.Bohrtiefe = Bohrtiefe
        self.Temperatur_Geothermie = Temperatur_Geothermie
        self.spez_Bohrkosten = spez_Bohrkosten
        self.spez_Entzugsleistung = spez_Entzugsleistung
        self.Vollbenutzungsstunden = Vollbenutzungsstunden
        self.Abstand_Sonden = Abstand_Sonden
        self.min_Teillast = min_Teillast
        self.min_area_geothermal = min_area_geothermal
        self.max_area_geothermal = max_area_geothermal
        self.min_depth_geothermal = min_depth_geothermal
        self.max_depth_geothermal = max_depth_geothermal
        self.co2_factor_electricity = 0.4 # tCO2/MWh electricity
        self.primärenergiefaktor = 2.4

    def calculate_operation(self, Last_L, VLT_L, COP_data, duration):
        """
        Calculates the geothermal heat extraction and other performance metrics.

        Args:
            Last_L (array-like): Load demand.
            VLT_L (array-like): Flow temperatures.
            COP_data (array-like): COP data for interpolation.
            duration (float): Time duration.

        Returns:
            tuple: Heat energy, electricity demand, heat output, electric power.
        """
        if self.Fläche == 0 or self.Bohrtiefe == 0:
            return 0, 0, np.zeros_like(Last_L), np.zeros_like(VLT_L)

        Anzahl_Sonden = (round(np.sqrt(self.Fläche) / self.Abstand_Sonden) + 1) ** 2

        Entzugsleistung_2400 = self.Bohrtiefe * self.spez_Entzugsleistung * Anzahl_Sonden / 1000
        # kW bei 2400 h, 22 Sonden, 50 W/m: 220 kW
        Entzugswärmemenge = Entzugsleistung_2400 * self.Vollbenutzungsstunden / 1000  # MWh
        self.Investitionskosten_Sonden = self.Bohrtiefe * self.spez_Bohrkosten * Anzahl_Sonden

        COP_L, VLT_WP = self.calculate_COP(VLT_L, self.Temperatur_Geothermie, COP_data)

        # tatsächliche Anzahl der Betriebsstunden der Wärmepumpe hängt von der Wärmeleistung ab,
        # diese hängt über Entzugsleistung von der angenommenen Betriebsstundenzahl ab
        B_min = 1
        B_max = 8760
        tolerance = 0.5
        while B_max - B_min > tolerance:
            B = (B_min + B_max) / 2
            # Berechnen der Entzugsleistung
            Entzugsleistung = Entzugswärmemenge * 1000 / B  # kW
            # Berechnen der Wärmeleistung und elektrischen Leistung
            Wärmeleistung_L = Entzugsleistung / (1 - (1 / COP_L))
            el_Leistung_L = Wärmeleistung_L - Entzugsleistung

            # Berechnen der tatsächlichen Werte
            self.Wärmeleistung_kW = np.zeros_like(Last_L)
            self.el_Leistung_kW = np.zeros_like(Last_L)
            Entzugsleistung_tat_L = np.zeros_like(Last_L)

            # Fälle, in denen die Wärmepumpe betrieben werden kann
            betrieb_mask = Last_L >= Wärmeleistung_L * self.min_Teillast
            self.Wärmeleistung_kW[betrieb_mask] = np.minimum(Last_L[betrieb_mask], Wärmeleistung_L[betrieb_mask])
            self.el_Leistung_kW[betrieb_mask] = self.Wärmeleistung_kW[betrieb_mask] - (Entzugsleistung * np.ones_like(Last_L))[betrieb_mask]
            Entzugsleistung_tat_L[betrieb_mask] = self.Wärmeleistung_kW[betrieb_mask] - self.el_Leistung_kW[betrieb_mask]

            Entzugswärme = np.sum(Entzugsleistung_tat_L) / 1000
            self.Wärmemenge = np.sum(self.Wärmeleistung_kW) / 1000
            self.Strombedarf = np.sum(self.el_Leistung_kW) / 1000
            Betriebsstunden = np.count_nonzero(self.Wärmeleistung_kW)

            # Falls es keine Nutzung gibt, wird das Ergebnis 0
            if Betriebsstunden == 0:
                self.Wärmeleistung_kW = np.array([0])
                self.el_Leistung_kW = np.array([0])

            if Entzugswärme > Entzugswärmemenge:
                B_min = B
            else:
                B_max = B

        self.max_Wärmeleistung = max(self.Wärmeleistung_kW)
        JAZ = self.Wärmemenge / self.Strombedarf
        self.Wärmemenge, self.Strombedarf = self.Wärmemenge * duration, self.Strombedarf * duration
    
    def calculate_environmental_impact(self):
        # CO2 emissions due to fuel usage
        self.co2_emissions = self.Strombedarf * self.co2_factor_electricity # tCO2
        # specific emissions heat
        self.spec_co2_total = self.co2_emissions / self.Wärmemenge if self.Wärmemenge > 0 else 0 # tCO2/MWh_heat

        self.primärenergie = self.Strombedarf * self.primärenergiefaktor
    
    def calculate(self, economic_parameters, duration, general_results, **kwargs):
        VLT_L = kwargs.get('VLT_L')
        COP_data = kwargs.get('COP_data')

        """
        Calculates the economic and environmental metrics for the geothermal heat pump.

        Args:
            VLT_L (array-like): Flow temperatures.
            COP_data (array-like): COP data for interpolation.
            economic_parameters (dict): Economic parameters dictionary containing fuel costs, capital interest rate, inflation rate, time period, and operational costs.
            duration (float): Time duration.
            general_results (dict): Dictionary containing general results and metrics.

        Returns:
            dict: Dictionary containing calculated metrics and results.
        """
        self.calculate_operation(general_results['Restlast_L'], VLT_L, COP_data, duration)

        self.spez_Investitionskosten_Erdsonden = self.Investitionskosten_Sonden / self.max_Wärmeleistung
        WGK = self.calculate_heat_generation_costs(self.max_Wärmeleistung, self.Wärmemenge, self.Strombedarf, self.spez_Investitionskosten_Erdsonden, economic_parameters)

        self.calculate_environmental_impact()

        results = {
            'Wärmemenge': self.Wärmemenge,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'Strombedarf': self.Strombedarf,
            'el_Leistung_L': self.el_Leistung_kW,
            'WGK': WGK,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie,
            'color': "darkorange"
        }

        return results
    
    def set_parameters(self, variables, variables_order, idx):
        try:
            self.Fläche = variables[variables_order.index(f"Fläche_{idx}")]
            self.Bohrtiefe = variables[variables_order.index(f"Bohrtiefe_{idx}")]
        except ValueError as e:
            print(f"Fehler beim Setzen der Parameter für {self.name}: {e}")

    def add_optimization_parameters(self, idx):
        """
        Fügt Optimierungsparameter für Geothermie hinzu und gibt sie zurück.

        Args:
            idx (int): Index der Technologie in der Liste.

        Returns:
            tuple: Initiale Werte, Variablennamen und Grenzen der Variablen.
        """
        initial_values = [self.Fläche, self.Bohrtiefe]
        variables_order = [f"Fläche_{idx}", f"Bohrtiefe_{idx}"]
        bounds = [(self.min_area_geothermal, self.max_area_geothermal), (self.min_depth_geothermal, self.max_depth_geothermal)]
        
        return initial_values, variables_order, bounds
    
    def update_parameters(self, optimized_values, variables_order, idx):
        """
        Aktualisiert die Parameter für Geothermie.

        Args:
            optimized_values (list): Liste der optimierten Werte.
            variables_order (list): Liste der Variablennamen.
            idx (int): Index der Technologie in der Liste.
        """
        self.Fläche = optimized_values[variables_order.index(f"Fläche_{idx}")]
        self.Bohrtiefe = optimized_values[variables_order.index(f"Bohrtiefe_{idx}")]

    def get_display_text(self):
        return (f"{self.name}: Fläche Sondenfeld: {self.Fläche} m², Bohrtiefe: {self.Bohrtiefe} m, "
                f"Quelltemperatur Erdreich: {self.Temperatur_Geothermie} °C, spez. Bohrkosten: "
                f"{self.spez_Bohrkosten} €/m, spez. Entzugsleistung: {self.spez_Entzugsleistung} W/m, "
                f"Vollbenutzungsstunden: {self.Vollbenutzungsstunden} h, Abstand Sonden: {self.Abstand_Sonden} m, "
                f"spez. Investitionskosten Wärmepumpe: {self.spezifische_Investitionskosten_WP} €/kW")
    
class AqvaHeat(HeatPump):
    """
    This class represents a AqvaHeat-solution (vacuum ice slurry generator with attached heat pump) and provides methods to calculate various performance and economic metrics.

    Args:
        HeatPump (_type_): Base class for the heat pump.

    Attributes:
        Wärmeleistung_FW_WP (float): Heat output of the river water heat pump.
        Temperatur_FW_WP (float): Temperature of the river water.
        dT (float): Temperature difference. Default is 0.
        spez_Investitionskosten_Flusswasser (float): Specific investment costs for river water heat pump per kW. Default is 1000.
        spezifische_Investitionskosten_WP (float): Specific investment costs of the heat pump per kW. Default is 1000.
        min_Teillast (float): Minimum partial load. Default is 0.2.
        co2_factor_electricity (float): CO2 emission factor for electricity in tCO2/MWh. Default is 0.4.
        primärenergiefaktor (float): Primary energy factor. Default is 2.4.

    Methods:
        Berechnung_WP(Wärmeleistung_L, VLT_L, COP_data): Calculates the cooling load, electric power consumption, and adjusted flow temperatures.
        abwärme(Last_L, VLT_L, COP_data, duration): Calculates the waste heat and other performance metrics.
        calculate(VLT_L, COP_data, Strompreis, q, r, T, BEW, stundensatz, duration, general_results): Calculates the economic and environmental metrics for the heat pump.
        to_dict(): Converts the object attributes to a dictionary.
        from_dict(data): Creates an object from a dictionary of attributes.
    """
    def __init__(self, name, nominal_power=100, temperature_difference=0):

        self.name = name
        self.nominal_power = nominal_power
        self.min_partial_load = 1  # no partial load for now (0..1)
        self.temperature_difference = 2.5  # difference over heat exchanger
        self.primärenergiefaktor = 2.4
        self.Wärmeleistung_FW_WP = nominal_power

    def calculate(self, economic_parameters, duration, general_results, **kwargs):
        """
        Perform specific calculations for waste heat systems.
        """
        VLT_L = kwargs.get('VLT_L')
        COP_data = kwargs.get('COP_data')

        residual_powers = general_results["Restlast_L"]
        effective_powers = np.zeros_like(residual_powers)

        intermediate_temperature = 12  # °C

        # calculate power in time steps where operation of aggregate is possible due to minimal partial load
        operation_mask = residual_powers >= self.nominal_power * self.min_partial_load
        effective_powers[operation_mask] = np.minimum(residual_powers[operation_mask], self.nominal_power)

        # HEAT PUMP
        # calculate first the heat pump (from 12°C to supply temperature)
        COP, effective_output_temperatures = self.calculate_COP(VLT_L, intermediate_temperature, COP_data)
        cooling_powers = effective_powers * (1 - (1 / COP))
        electrical_powers = effective_powers - cooling_powers

        # disable heat pump when not reaching supply temperature
        operation_mask = effective_output_temperatures >= VLT_L - self.temperature_difference  # TODO: verify direction of difference
        effective_powers[~operation_mask] = 0
        cooling_powers[~operation_mask] = 0
        electrical_powers[~operation_mask] = 0

        # sum energy over whole lifetime
        # convert to MWh
        heat_supplied = np.sum(effective_powers / 1000) * duration
        cooling_supplied = np.sum(cooling_powers / 1000) * duration

        # VACUUM ICE GENERATOR
        # now the vacuum ice generator, needs to supply 12°C from river water to the heatpump
        # cooling supplied by heat pump is heat supplied by vacuum ice process 

        isentropic_efficiency = 0.7  # Adjust this value based on the actual compressor efficiency
        fluid = 'Water'
        molar_mass_water = 18.01528  # in g/mol

        # Triple point conditions for water
        # temperature_triple_point = 273.16  # Temperature in Kelvin
        # pressure_triple_point = 611.657  # Pressure in Pascal

        # Define initial conditions
        triple_point_pressure =  CP.PropsSI('ptriple', 'T', 0, 'P', 0, fluid) + 0.01 # in Pascal, delta because of validity range
        triple_point_temperature = CP.PropsSI('T', 'Q', 0, 'P', triple_point_pressure + 1, fluid)  # Triple point temperature

        initial_pressure = triple_point_pressure
        initial_temperature = triple_point_temperature

        # Define final conditions after first compression
        final_temperature = 12 + 273.15  # Convert to Kelvin
        final_pressure = CP.PropsSI('P', 'T', final_temperature, 'Q', 0, fluid)

        # mass flow from condensing vapor at 12°C, 14hPa
        mass_flows = effective_powers / (CP.PropsSI('H','P',14000,'Q',1,'Water') - 
                                        CP.PropsSI('H','P',14000,'Q',0,'Water'))
        # electrical power needed compressing vapor from triple point 
        energy_compression = (CP.PropsSI('H', 'T', final_temperature, 'P', final_pressure, fluid) -
                                      CP.PropsSI('H', 'T', initial_temperature, 'P', initial_pressure, fluid)) / isentropic_efficiency

        electrical_powers += mass_flows * energy_compression / 1000  # W -> kW

        self.Wärmemenge_AqvaHeat = heat_supplied
        self.Wärmeleistung_kW = effective_powers

        electricity_consumed = np.sum(electrical_powers / 1000) * duration
        self.Strombedarf_AqvaHeat = electricity_consumed

        self.el_Leistung_kW = electrical_powers

        WGK_Abwärme = -1
        self.primärenergie = self.Strombedarf_AqvaHeat * self.primärenergiefaktor

        self.spec_co2_total = -1


        results = {
            'Wärmemenge': self.Wärmemenge_AqvaHeat,  # heat energy for whole duration
            'Wärmeleistung_L': self.Wärmeleistung_kW,  # vector length time steps with actual power supplied
            'Strombedarf': self.Strombedarf_AqvaHeat,  # electrical energy consumed during whole duration
            'el_Leistung_L': self.el_Leistung_kW,  # vector length time steps with actual electrical power consumed
            'WGK': WGK_Abwärme,
            'spec_co2_total': self.spec_co2_total,  # tCO2/MWh_heat
            'primärenergie': self.primärenergie,
            'color': "blue"
        }

        return results
    
    def set_parameters(self, variables, variables_order, idx):
        pass

    def add_optimization_parameters(self, idx):
        """
        AqvaHeat hat keine Optimierungsparameter. Diese Methode gibt leere Listen zurück.

        Args:
            idx (int): Index der Technologie in der Liste.

        Returns:
            tuple: Leere Listen für initial_values, variables_order und bounds.
        """
        return [], [], []

    def update_parameters(self, optimized_values, variables_order, idx):
        pass

    def get_display_text(self):
        return f"Name: {self.name}, Nennleistung: {self.nominal_power} kW, Temperaturdifferenz: {self.temperature_difference} K"

