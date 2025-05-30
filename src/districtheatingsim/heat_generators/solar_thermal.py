"""
Filename: solar_thermal.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-11
Description: This script calculates the heat generation of a thermal solar heat generator.

Additional Information: Yield calculation program for solar thermal energy in heating networks (calculation basis: ScenoCalc District Heating 2.0) https://www.scfw.de/)
"""

# Import Bibliotheken
from math import pi, exp, log, sqrt
import numpy as np

from districtheatingsim.heat_generators.solar_radiation import calculate_solar_radiation
from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy

class SolarThermal(BaseHeatGenerator):
    """
    A class representing a solar thermal system.

    Attributes:
        name (str): Name of the solar thermal system.
        bruttofläche_STA (float): Gross area of the solar thermal system in square meters.
        vs (float): Volume of the storage system in cubic meters.
        Typ (str): Type of solar collector, e.g., "Flachkollektor" or "Vakuumröhrenkollektor".
        kosten_speicher_spez (float): Specific costs for the storage system in €/m^3.
        kosten_fk_spez (float): Specific costs for flat plate collectors in €/m^2.
        kosten_vrk_spez (float): Specific costs for vacuum tube collectors in €/m^2.
        Tsmax (float): Maximum storage temperature in degrees Celsius.
        Longitude (float): Longitude of the installation site.
        STD_Longitude (float): Standard longitude for the time zone.
        Latitude (float): Latitude of the installation site.
        East_West_collector_azimuth_angle (float): Azimuth angle of the collector in degrees.
        Collector_tilt_angle (float): Tilt angle of the collector in degrees.
        Tm_rl (float): Mean return temperature in degrees Celsius.
        Qsa (float): Initial heat output.
        Vorwärmung_K (float): Preheating in Kelvin.
        DT_WT_Solar_K (float): Temperature difference for the solar heat exchanger in Kelvin.
        DT_WT_Netz_K (float): Temperature difference for the network heat exchanger in Kelvin.
        opt_volume_min (float): Minimum optimization volume in cubic meters.
        opt_volume_max (float): Maximum optimization volume in cubic meters.
        opt_area_min (float): Minimum optimization area in square meters.
        opt_area_max (float): Maximum optimization area in square meters.
        kosten_pro_typ (dict): Dictionary containing the specific costs for different types of collectors.
        Kosten_STA_spez (float): Specific costs for the solar thermal system.
        Nutzungsdauer (int): Service life of the solar thermal system in years.
        f_Inst (float): Installation factor.
        f_W_Insp (float): Inspection factor.
        Bedienaufwand (float): Operational effort.
        Anteil_Förderung_BEW (float): Subsidy rate for the renewable energy law.
        Betriebskostenförderung_BEW (float): Operational cost subsidy for the renewable energy law in €/MWh.
        co2_factor_solar (float): CO2 factor for solar energy in tCO2/MWh.
        primärenergiefaktor (float): Primary energy factor for solar energy.
    """

    def __init__(self, name, bruttofläche_STA, vs, Typ, kosten_speicher_spez=750, kosten_fk_spez=430, kosten_vrk_spez=590, Tsmax=90, Longitude=-14.4222, 
                 STD_Longitude=-15, Latitude=51.1676, East_West_collector_azimuth_angle=0, Collector_tilt_angle=36, Tm_rl=60, Qsa=0, Vorwärmung_K=8, 
                 DT_WT_Solar_K=5, DT_WT_Netz_K=5, opt_volume_min=0, opt_volume_max=200, opt_area_min=0, opt_area_max=2000, active=True):
        """
        Initializes the SolarThermal class.

        Args:
            name (str): Name of the solar thermal system.
            bruttofläche_STA (float): Gross area of the solar thermal system in square meters.
            vs (float): Volume of the storage system in cubic meters.
            Typ (str): Type of solar collector, e.g., "Flachkollektor" or "Vakuumröhrenkollektor".
            kosten_speicher_spez (float, optional): Specific costs for the storage system in €/m^3. Defaults to 750.
            kosten_fk_spez (float, optional): Specific costs for flat plate collectors in €/m^2. Defaults to 430.
            kosten_vrk_spez (float, optional): Specific costs for vacuum tube collectors in €/m^2. Defaults to 590.
            Tsmax (float, optional): Maximum storage temperature in degrees Celsius. Defaults to 90.
            Longitude (float, optional): Longitude of the installation site. Defaults to -14.4222.
            STD_Longitude (float, optional): Standard longitude for the time zone. Defaults to -15.
            Latitude (float, optional): Latitude of the installation site. Defaults to 51.1676.
            East_West_collector_azimuth_angle (float, optional): Azimuth angle of the collector in degrees. Defaults to 0.
            Collector_tilt_angle (float, optional): Tilt angle of the collector in degrees. Defaults to 36.
            Tm_rl (float, optional): Mean return temperature in degrees Celsius. Defaults to 60.
            Qsa (float, optional): Initial heat output. Defaults to 0.
            Vorwärmung_K (float, optional): Preheating in Kelvin. Defaults to 8.
            DT_WT_Solar_K (float, optional): Temperature difference for the solar heat exchanger in Kelvin. Defaults to 5.
            DT_WT_Netz_K (float, optional): Temperature difference for the network heat exchanger in Kelvin. Defaults to 5.
            opt_volume_min (float, optional): Minimum optimization volume in cubic meters. Defaults to 0.
            opt_volume_max (float, optional): Maximum optimization volume in cubic meters. Defaults to 200.
            opt_area_min (float, optional): Minimum optimization area in square meters. Defaults to 0.
            opt_area_max (float, optional): Maximum optimization area in square meters. Defaults to 2000.
        """
        super().__init__(name)
        self.bruttofläche_STA = bruttofläche_STA
        self.vs = vs
        self.Typ = Typ
        self.kosten_speicher_spez = kosten_speicher_spez
        self.kosten_fk_spez = kosten_fk_spez
        self.kosten_vrk_spez = kosten_vrk_spez
        self.Tsmax = Tsmax
        self.Longitude = Longitude
        self.STD_Longitude = STD_Longitude
        self.Latitude = Latitude
        self.East_West_collector_azimuth_angle = East_West_collector_azimuth_angle
        self.Collector_tilt_angle = Collector_tilt_angle
        self.Tm_rl = Tm_rl
        self.Qsa = Qsa
        self.Vorwärmung_K = Vorwärmung_K
        self.DT_WT_Solar_K = DT_WT_Solar_K
        self.DT_WT_Netz_K = DT_WT_Netz_K
        self.opt_volume_min = opt_volume_min
        self.opt_volume_max = opt_volume_max
        self.opt_area_min = opt_area_min
        self.opt_area_max = opt_area_max
        self.active = active

        self.kosten_pro_typ = {
            # Viessmann Flachkollektor Vitosol 200-FM, 2,56 m²: 697,9 € (brutto); 586,5 € (netto) -> 229 €/m²
            # + 200 €/m² Installation/Zubehör
            "Flachkollektor": self.kosten_fk_spez,
            # Ritter Vakuumröhrenkollektor CPC XL1921 (4,99m²): 2299 € (brutto); 1932 € (Netto) -> 387 €/m²
            # + 200 €/m² Installation/Zubehör
            "Vakuumröhrenkollektor": self.kosten_vrk_spez
        }

        self.Kosten_STA_spez = self.kosten_pro_typ[self.Typ]  # €/m^2
        self.Nutzungsdauer = 20  # Jahre
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 0.5, 1, 0
        self.Anteil_Förderung_BEW = 0.4
        self.Betriebskostenförderung_BEW = 10  # €/MWh 10 Jahre
        self.co2_factor_solar = 0.0  # tCO2/MWh heat is 0 ?
        self.primärenergiefaktor = 0.0

        self.strategy = SolarThermalStrategy(charge_on=0, charge_off=0)

        self.init_calculation_constants()
        self.init_operation(8760)

    def init_calculation_constants(self):
        """
        Initializes calculation constants for the solar thermal system.
        """
        
        # Definition Albedo-Wert
        self.Albedo = 0.2
        # Definition Korrekturfaktor Windgeschwindigkeit
        self.wcorr = 0.5

        if self.Typ == "Flachkollektor":
            # Vorgabewerte Flachkollektor Vitosol 200-F XL13
            # Bruttofläche ist Bezugsfläche
            self.Eta0b_neu = 0.763
            self.Kthetadiff = 0.931
            self.Koll_c1 = 1.969
            self.Koll_c2 = 0.015
            self.Koll_c3 = 0
            self.KollCeff_A = 9.053
            self.KollAG = 13.17
            self.KollAAp = 12.35

            self.Aperaturfläche = self.bruttofläche_STA * (self.KollAAp / self.KollAG)
            self.Bezugsfläche = self.bruttofläche_STA

            self.IAM_W = {0: 1, 10: 1, 20: 0.99, 30: 0.98, 40: 0.96, 50: 0.91, 60: 0.82, 70: 0.53, 80: 0.27, 90: 0.0}
            self.IAM_N = {0: 1, 10: 1, 20: 0.99, 30: 0.98, 40: 0.96, 50: 0.91, 60: 0.82, 70: 0.53, 80: 0.27, 90: 0.0}

        if self.Typ == "Vakuumröhrenkollektor":
            # Vorgabewerte Vakuumröhrenkollektor
            # Aperaturfläche ist Bezugsfläche
            self.Eta0hem = 0.688
            self.a1 = 0.583
            self.a2 = 0.003
            self.KollCeff_A = 8.78
            self.KollAG = 4.94
            self.KollAAp = 4.5

            self.Koll_c1 = self.a1
            self.Koll_c2 = self.a2
            self.Koll_c3 = 0
            self.Eta0b_neu = 0.693
            self.Kthetadiff = 0.951

            self.Aperaturfläche = self.bruttofläche_STA * (self.KollAAp / self.KollAG)
            self.Bezugsfläche = self.Aperaturfläche

            self.IAM_W = {0: 1, 10: 1.02, 20: 1.03, 30: 1.03, 40: 1.03, 50: 0.96, 60: 1.07, 70: 1.19, 80: 0.595, 90: 0.0}
            self.IAM_N = {0: 1, 10: 1, 20: 0.99, 30: 0.96, 40: 0.93, 50: 0.9, 60: 0.87, 70: 0.86, 80: 0.43, 90: 0.0}

        # Vorgabewerte Speicher
        self.QSmax = 1.16 * self.vs * (self.Tsmax - self.Tm_rl)

    def init_operation(self, hours):
        self.betrieb_mask = np.array([False] * hours)
        self.Wärmeleistung_kW = np.zeros(hours)
        self.Speicherinhalt = np.zeros(hours)
        self.Speicherfüllstand = np.zeros(hours)
        self.Wärmemenge_MWh = 0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0
        self.Betriebsstunden_pro_Start = 0

        self.calculated = False  # Flag to indicate if the calculation is done

        # Initialisierung der Arrays für die Ergebnisse
        self.Tm_a_L = np.zeros(hours)
        self.Pkoll_a_L = np.zeros(hours)
        self.Pkoll_b_L = np.zeros(hours)
        self.T_koll_a_L = np.zeros(hours)
        self.T_koll_b_L = np.zeros(hours)
        self.Tgkoll_a_L = np.zeros(hours)
        self.Tgkoll_L = np.zeros(hours)
        self.Tm_koll_L = np.zeros(hours)
        self.Tm_L = np.zeros(hours)
        self.Kollektorfeldertrag_L = np.zeros(hours)
        self.Zieltemperatur_Solaranlage_L = np.zeros(hours)
        self.TRL_Solar_L = np.zeros(hours)
        self.TS_unten_L = np.zeros(hours)
        self.Verlustwärmestrom_Speicher_L = np.zeros(hours)
        self.Stagnation_L = np.zeros(hours)

    def calculate_heat_generation_costs(self, economic_parameters):
        """
        Calculates the weighted average cost of heat generation (WGK).

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
        self.stundensatz = economic_parameters['hourly_rate']

        if self.Wärmemenge_MWh == 0:
            return 0

        self.Investitionskosten_Speicher = self.vs * self.kosten_speicher_spez
        self.Investitionskosten_STA = self.bruttofläche_STA * self.Kosten_STA_spez
        self.Investitionskosten = self.Investitionskosten_Speicher + self.Investitionskosten_STA

        self.A_N = self.annuity(self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, self.q, self.r, self.T, hourly_rate=self.stundensatz)
        self.WGK = self.A_N / self.Wärmemenge_MWh

        self.Eigenanteil = 1 - self.Anteil_Förderung_BEW
        self.Investitionskosten_Gesamt_BEW = self.Investitionskosten * self.Eigenanteil
        self.Annuität_BEW = self.annuity(self.Investitionskosten_Gesamt_BEW, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, self.q, self.r, self.T, hourly_rate=self.stundensatz)
        self.WGK_BEW = self.Annuität_BEW / self.Wärmemenge_MWh

        self.WGK_BEW_BKF = self.WGK_BEW - self.Betriebskostenförderung_BEW

        if self.BEW == "Nein":
            return self.WGK
        elif self.BEW == "Ja":
            return self.WGK_BEW_BKF
        
    def calculate_environmental_impact(self):
        # Berechnung der Emissionen
        self.co2_emissions = self.Wärmemenge_MWh * self.co2_factor_solar  # tCO2
        # specific emissions heat
        self.spec_co2_total = self.co2_emissions / self.Wärmemenge_MWh if self.Wärmemenge_MWh > 0 else 0  # tCO2/MWh_heat

        self.primärenergie_Solarthermie = self.Wärmemenge_MWh * self.primärenergiefaktor

    def calculate_solar_thermal_with_storage(self, Last_L, VLT_L, RLT_L, TRY_data, time_steps, duration):
        """
        Berechnung der thermischen Solaranlage (STA) zur Wärmegewinnung.

        Args:
            Last_L (array): Lastprofil.
            VLT_L (array): Vorlauftemperaturprofil.
            RLT_L (array): Rücklauftemperaturprofil.
            TRY_data (tuple): TRY-Daten (Temperatur, Windgeschwindigkeit, Direktstrahlung, Globalstrahlung).
            time_steps (array): Zeitstempel.
            duration (float): Zeitdauer der Berechnung.

        Returns:
            tuple: Gesamtwärmemenge, Wärmeoutput, Speicherladung und Speicherfüllstand.
        """
        self.Lufttemperatur_L, self.Windgeschwindigkeit_L, self.Direktstrahlung_L, self.Globalstrahlung_L = TRY_data[0], TRY_data[1], TRY_data[2], TRY_data[3]
        
        self.GT_H_Gk, self.K_beam_L, self.GbT_L, self.GdT_H_Dk_L = calculate_solar_radiation(time_steps, self.Globalstrahlung_L, self.Direktstrahlung_L, self.Longitude,
                                                                        self.STD_Longitude, self.Latitude, self.Albedo, 
                                                                        self.East_West_collector_azimuth_angle,
                                                                        self.Collector_tilt_angle, self.IAM_W, self.IAM_N)

        # Initialisierung der Arrays für die Ergebnisse
        n_steps = len(time_steps)

        for i in range(n_steps):
            Eta0b_neu_K_beam_GbT = self.Eta0b_neu * self.K_beam_L[i] * self.GbT_L[i]
            Eta0b_neu_Kthetadiff_GdT_H_Dk = self.Eta0b_neu * self.Kthetadiff * self.GdT_H_Dk_L[i]

            if i == 0:
                self.TS_unten_L[i] = RLT_L[i]
                self.TRL_Solar_L[i] = RLT_L[i]
                self.Zieltemperatur_Solaranlage_L[i] = self.TS_unten_L[i] + self.Vorwärmung_K + self.DT_WT_Solar_K + self.DT_WT_Netz_K
                self.Tm_a_L[i] = (self.Zieltemperatur_Solaranlage_L[i] + self.TRL_Solar_L[i]) / 2
                self.Pkoll_a_L[i] = 0
                self.Tgkoll_a_L[i] = 9.3
                self.T_koll_a_L[i] = self.Lufttemperatur_L[i] - (self.Lufttemperatur_L[i] - self.Tgkoll_a_L[i]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_a_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                self.Pkoll_b_L[i] = 0
                self.T_koll_b_L[i] = self.Lufttemperatur_L[i] - (self.Lufttemperatur_L[i] - 0) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_b_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                self.Tgkoll_L[i] = 9.3
                self.Tm_koll_L[i] = (self.T_koll_a_L[i] + self.T_koll_b_L[i]) / 2

                self.Kollektorfeldertrag_L[i] = 0
                self.Wärmeleistung_kW[i] = min(self.Kollektorfeldertrag_L[i], Last_L[i])
                self.Verlustwärmestrom_Speicher_L[i] = 0
                self.Speicherinhalt[i] = self.Qsa * 1000
                self.Speicherfüllstand[i] = self.Speicherinhalt[i] / self.QSmax  # Speicherfüllungsgrad
                self.Stagnation_L[i] = 0

            else:
                # Calculate lower storage tank temperature
                if self.Speicherfüllstand[i - 1] >= 0.8:
                    self.TS_unten_L[i] = RLT_L[i] + self.DT_WT_Netz_K + (2/3 * (VLT_L[i] - RLT_L[i]) / 0.2 * self.Speicherfüllstand[i - 1]) + (1 / 3 * (VLT_L[i] - RLT_L[i])) - (2/3 * (VLT_L[i] - RLT_L[i]) / 0.2 * self.Speicherfüllstand[i - 1])
                else:
                    self.TS_unten_L[i] = RLT_L[i] + self.DT_WT_Netz_K + (1 / 3 * (VLT_L[i] - RLT_L[i]) / 0.8) * self.Speicherfüllstand[i - 1]

                # Calculate solar target temperature and return line temperature
                self.Zieltemperatur_Solaranlage_L[i] = self.TS_unten_L[i] + self.Vorwärmung_K + self.DT_WT_Solar_K + self.DT_WT_Netz_K
                self.TRL_Solar_L[i] = self.TS_unten_L[i] + self.DT_WT_Solar_K

                # Calculate new collector A average temperature
                self.Tm_a_L[i] = (self.Zieltemperatur_Solaranlage_L[i] + self.TRL_Solar_L[i]) / 2

                # Calculate collector A power output and temperature
                c1a = self.Koll_c1 * (self.Tm_a_L[i] - self.Lufttemperatur_L[i])
                c2a = self.Koll_c2 * (self.Tm_a_L[i] - self.Lufttemperatur_L[i]) ** 2
                c3a = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[i] * (self.Tm_a_L[i] - self.Lufttemperatur_L[i])

                self.Pkoll_a_L[i] = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1a - c2a - c3a) * self.Bezugsfläche / 1000)
                self.T_koll_a_L[i] = self.Lufttemperatur_L[i] - (self.Lufttemperatur_L[i] - self.Tgkoll_a_L[i - 1]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_a_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)

                # Calculate collector B power output and temperature
                c1b = self.Koll_c1 * (self.T_koll_b_L[i - 1] - self.Lufttemperatur_L[i])
                c2b = self.Koll_c2 * (self.T_koll_b_L[i - 1] - self.Lufttemperatur_L[i]) ** 2
                c3b = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[i] * (self.T_koll_b_L[i - 1] - self.Lufttemperatur_L[i])
                
                self.Pkoll_b_L[i] = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1b - c2b - c3b) * self.Bezugsfläche / 1000)
                self.T_koll_b_L[i] = self.Lufttemperatur_L[i] - (self.Lufttemperatur_L[i] - self.Tgkoll_a_L[i - 1]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_b_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                
                # Calculate new collector A glycol temperature
                self.Tgkoll_a_L[i] = min(self.Zieltemperatur_Solaranlage_L[i], self.T_koll_a_L[i])

                # calculate average collector temperature
                self.Tm_koll_L[i] = (self.T_koll_a_L[i] + self.T_koll_b_L[i]) / 2
                Tm_sys = (self.Zieltemperatur_Solaranlage_L[i] + self.TRL_Solar_L[i]) / 2
                if self.Tm_koll_L[i] < Tm_sys and self.Tm_koll_L[i - 1] < Tm_sys:
                    self.Tm_L[i] = self.Tm_koll_L[i]
                else:
                    self.Tm_L[i] = Tm_sys

                # calculate collector power output
                c1 = self.Koll_c1 * (self.Tm_L[i] - self.Lufttemperatur_L[i])
                c2 = self.Koll_c2 * (self.Tm_L[i] - self.Lufttemperatur_L[i]) ** 2
                c3 = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[i] * (self.Tm_L[i] - self.Lufttemperatur_L[i])
                Pkoll = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1 - c2 - c3) * self.Bezugsfläche / 1000)

                # calculate collector temperature surplus
                T_koll = self.Lufttemperatur_L[i] - (self.Lufttemperatur_L[i] - self.Tgkoll_L[i - 1]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (Pkoll * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                self.Tgkoll_L[i] = min(self.Zieltemperatur_Solaranlage_L[i], T_koll)

                # Berechnung Kollektorfeldertrag
                if T_koll > self.Tgkoll_L[i - 1]:
                    Pkoll_temp_corr = (T_koll-self.Tgkoll_L[i])/(T_koll-self.Tgkoll_L[i - 1]) * Pkoll if self.Tgkoll_L[i] >= self.Zieltemperatur_Solaranlage_L[i] else 0

                    self.Kollektorfeldertrag_L[i] = max(0, min(Pkoll, Pkoll_temp_corr)) if self.Stagnation_L[i - 1] <= 0 else 0
                else:
                    self.Kollektorfeldertrag_L[i] = 0

                self.Wärmeleistung_kW[i] = min(self.Kollektorfeldertrag_L[i] + self.Speicherinhalt[i - 1], Last_L[i]) if self.Kollektorfeldertrag_L[i] + self.Speicherinhalt[i - 1] > 0 else 0

                Stagnationsverluste = max(0, self.Speicherinhalt[i - 1] - self.Verlustwärmestrom_Speicher_L[i - 1] + self.Kollektorfeldertrag_L[i] - self.Wärmeleistung_kW[i] - self.QSmax)

                PSin = self.Kollektorfeldertrag_L[i] - Stagnationsverluste

                if self.Speicherinhalt[i - 1] - self.Verlustwärmestrom_Speicher_L[i - 1] + PSin - self.Wärmeleistung_kW[i] > self.QSmax:
                    self.Speicherinhalt[i] = self.QSmax
                else:
                    self.Speicherinhalt[i] = self.Speicherinhalt[i - 1] - self.Verlustwärmestrom_Speicher_L[i - 1] + PSin - self.Wärmeleistung_kW[i]

                # Berechnung Mitteltemperatur im Speicher
                self.Speicherfüllstand[i] = self.Speicherinhalt[i] / self.QSmax  # Speicherfüllungsgrad

                TS_oben = self.Zieltemperatur_Solaranlage_L[i] - self.DT_WT_Solar_K
                if self.Speicherinhalt[i] <= 0:
                    berechnete_temperatur = TS_oben
                else:
                    temperaturverhältnis = (TS_oben - self.Tm_rl) / (self.Tsmax - self.Tm_rl)
                    if self.Speicherfüllstand[i] < temperaturverhältnis:
                        berechnete_temperatur = VLT_L[i] + self.DT_WT_Netz_K
                    else:
                        berechnete_temperatur = self.Tsmax

                gewichtete_untere_temperatur = (1 - self.Speicherfüllstand[i]) * self.TS_unten_L[i]
                Tms = self.Speicherfüllstand[i] * berechnete_temperatur + gewichtete_untere_temperatur

                self.Verlustwärmestrom_Speicher_L[i] = 0.75 * (self.vs * 1000) ** 0.5 * 0.16 * (Tms - self.Lufttemperatur_L[i]) / 1000

                self.Stagnation_L[i] = 1 if np.datetime_as_string(time_steps[i], unit='D') == np.datetime_as_string(time_steps[i - 1], unit='D') and self.Kollektorfeldertrag_L[i] > Last_L[i] and self.Speicherinhalt[i] >= self.QSmax else 0

        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW) * duration / 1000  # kWh -> MWh

    def generate(self, t, **kwargs):
        """
        Generates heat for the solar thermal system at a given time step.

        Args:
            t (int): Current time step.
            kwargs (dict): Additional arguments including load profile, TRY data, and time steps.

        Returns:
            float: Heat generation (kW) for the current time step.
        """
        remaining_load = kwargs.get('remaining_load')
        upper_storage_temperature = kwargs.get('upper_storage_temperature')
        lower_storage_temperature = kwargs.get('lower_storage_temperature')
        current_storage_state = kwargs.get('current_storage_state')
        available_energy = kwargs.get('available_energy')
        max_energy = kwargs.get('max_energy')
        Q_loss = kwargs.get('Q_loss')
        TRY_data = kwargs.get('TRY_data')
        time_steps = kwargs.get('time_steps')
        duration = kwargs.get('duration')

        if t == 0:
            self.Lufttemperatur_L, self.Windgeschwindigkeit_L, self.Direktstrahlung_L, self.Globalstrahlung_L = TRY_data[0], TRY_data[1], TRY_data[2], TRY_data[3]
        
            self.GT_H_Gk, self.K_beam_L, self.GbT_L, self.GdT_H_Dk_L = calculate_solar_radiation(time_steps, self.Globalstrahlung_L, self.Direktstrahlung_L, self.Longitude,
                                                                        self.STD_Longitude, self.Latitude, self.Albedo, 
                                                                        self.East_West_collector_azimuth_angle,
                                                                        self.Collector_tilt_angle, self.IAM_W, self.IAM_N)
        
        if self.active:
            Eta0b_neu_K_beam_GbT = self.Eta0b_neu * self.K_beam_L[t] * self.GbT_L[t]
            Eta0b_neu_Kthetadiff_GdT_H_Dk = self.Eta0b_neu * self.Kthetadiff * self.GdT_H_Dk_L[t]

            ### Das muss noch aus dem Speicher kommen ###
            self.QSmax = max_energy # kWh
            self.Speicherinhalt[t] = available_energy # kWh
            self.Speicherfüllstand[t] = current_storage_state

            self.Verlustwärmestrom_Speicher_L[t] = Q_loss # kW
            self.Stagnation_L[t] = 0

            if t == 0:
                self.TS_unten_L[t] = lower_storage_temperature
                self.TRL_Solar_L[t] = lower_storage_temperature
                self.Zieltemperatur_Solaranlage_L[t] = self.TS_unten_L[t] + self.Vorwärmung_K + self.DT_WT_Solar_K + self.DT_WT_Netz_K
                self.Tm_a_L[t] = (self.Zieltemperatur_Solaranlage_L[t] + self.TRL_Solar_L[t]) / 2
                self.Pkoll_a_L[t] = 0
                self.Tgkoll_a_L[t] = 9.3
                self.T_koll_a_L[t] = self.Lufttemperatur_L[t] - (self.Lufttemperatur_L[t] - self.Tgkoll_a_L[t]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_a_L[t] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                self.Pkoll_b_L[t] = 0
                self.T_koll_b_L[t] = self.Lufttemperatur_L[t] - (self.Lufttemperatur_L[t] - 0) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_b_L[t] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                self.Tgkoll_L[t] = 9.3

                self.Kollektorfeldertrag_L[t] = 0
                self.Wärmeleistung_kW[t] = min(self.Kollektorfeldertrag_L[t], remaining_load)

            else:
                # Calculate lower storage tank temperature
                if self.Speicherfüllstand[t - 1] >= 0.8:
                    self.TS_unten_L[t] = lower_storage_temperature + self.DT_WT_Netz_K + (2/3 * (upper_storage_temperature - lower_storage_temperature) / 0.2 * self.Speicherfüllstand[t - 1]) + (1 / 3 * (upper_storage_temperature - lower_storage_temperature)) - (2/3 * (upper_storage_temperature - lower_storage_temperature) / 0.2 * self.Speicherfüllstand[t - 1])
                else:
                    self.TS_unten_L[t] = lower_storage_temperature + self.DT_WT_Netz_K + (1 / 3 * (upper_storage_temperature - lower_storage_temperature) / 0.8) * self.Speicherfüllstand[t - 1]

                # Calculate solar target temperature and return line temperature
                self.Zieltemperatur_Solaranlage_L[t] = self.TS_unten_L[t] + self.Vorwärmung_K + self.DT_WT_Solar_K + self.DT_WT_Netz_K
                self.TRL_Solar_L[t] = self.TS_unten_L[t] + self.DT_WT_Solar_K

                # Calculate new collector A average temperature
                self.Tm_a_L[t] = (self.Zieltemperatur_Solaranlage_L[t] + self.TRL_Solar_L[t]) / 2

                # Calculate collector A power output and temperature
                c1a = self.Koll_c1 * (self.Tm_a_L[t] - self.Lufttemperatur_L[t])
                c2a = self.Koll_c2 * (self.Tm_a_L[t] - self.Lufttemperatur_L[t]) ** 2
                c3a = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[t] * (self.Tm_a_L[t] - self.Lufttemperatur_L[t])

                self.Pkoll_a_L[t] = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1a - c2a - c3a) * self.Bezugsfläche / 1000)
                self.T_koll_a_L[t] = self.Lufttemperatur_L[t] - (self.Lufttemperatur_L[t] - self.Tgkoll_a_L[t - 1]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_a_L[t] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)

                # Calculate collector B power output and temperature
                c1b = self.Koll_c1 * (self.T_koll_b_L[t - 1] - self.Lufttemperatur_L[t])
                c2b = self.Koll_c2 * (self.T_koll_b_L[t - 1] - self.Lufttemperatur_L[t]) ** 2
                c3b = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[t] * (self.T_koll_b_L[t - 1] - self.Lufttemperatur_L[t])
                
                self.Pkoll_b_L[t] = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1b - c2b - c3b) * self.Bezugsfläche / 1000)
                self.T_koll_b_L[t] = self.Lufttemperatur_L[t] - (self.Lufttemperatur_L[t] - self.Tgkoll_a_L[t - 1]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_b_L[t] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                
                # Calculate new collector A glycol temperature
                self.Tgkoll_a_L[t] = min(self.Zieltemperatur_Solaranlage_L[t], self.T_koll_a_L[t])

                # calculate average collector temperature
                self.Tm_koll_L[t] = (self.T_koll_a_L[t] + self.T_koll_b_L[t]) / 2
                Tm_sys = (self.Zieltemperatur_Solaranlage_L[t] + self.TRL_Solar_L[t]) / 2
                if self.Tm_koll_L[t] < Tm_sys and self.Tm_koll_L[t - 1] < Tm_sys:
                    self.Tm_L[t] = self.Tm_koll_L[t]
                else:
                    self.Tm_L[t] = Tm_sys

                # calculate collector power output
                c1 = self.Koll_c1 * (self.Tm_L[t] - self.Lufttemperatur_L[t])
                c2 = self.Koll_c2 * (self.Tm_L[t] - self.Lufttemperatur_L[t]) ** 2
                c3 = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[t] * (self.Tm_L[t] - self.Lufttemperatur_L[t])
                Pkoll = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1 - c2 - c3) * self.Bezugsfläche / 1000)

                # calculate collector temperature surplus
                T_koll = self.Lufttemperatur_L[t] - (self.Lufttemperatur_L[t] - self.Tgkoll_L[t - 1]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (Pkoll * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                self.Tgkoll_L[t] = min(self.Zieltemperatur_Solaranlage_L[t], T_koll)

                # Berechnung Kollektorfeldertrag
                if T_koll > self.Tgkoll_L[t - 1]:
                    Pkoll_temp_corr = (T_koll-self.Tgkoll_L[t])/(T_koll-self.Tgkoll_L[t - 1]) * Pkoll if self.Tgkoll_L[t] >= self.Zieltemperatur_Solaranlage_L[t] else 0

                    self.Kollektorfeldertrag_L[t] = max(0, min(Pkoll, Pkoll_temp_corr)) if self.Stagnation_L[t - 1] <= 0 else 0
                else:
                    self.Kollektorfeldertrag_L[t] = 0

                self.Wärmeleistung_kW[t] = self.Kollektorfeldertrag_L[t]

                self.Stagnation_L[t] = 1 if np.datetime_as_string(time_steps[t], unit='D') == np.datetime_as_string(time_steps[t - 1], unit='D') and self.Kollektorfeldertrag_L[t] > remaining_load and self.Speicherinhalt[t] >= self.QSmax else 0

        # Kumulative Werte aktualisieren
        self.Wärmemenge_MWh += self.Wärmeleistung_kW[t] * duration / 1000 # kW -> MWh

        return self.Wärmeleistung_kW[t], 0  # Rückgabe der erzeugten Wärmeleistung für den aktuellen Zeitschritt

    def calculate(self, economic_parameters, duration, load_profile, **kwargs):
        VLT_L = kwargs.get('VLT_L')
        RLT_L = kwargs.get('RLT_L')
        TRY_data = kwargs.get('TRY_data')
        time_steps = kwargs.get('time_steps')

        """
        Calculates the performance and cost of the solar thermal system.

        Args:
            VLT_L (array): Forward temperature profile in degrees Celsius.
            RLT_L (array): Return temperature profile in degrees Celsius.
            TRY_data (array): Test Reference Year data.
            time_steps (array): Array of time steps.
            duration (float): Duration of each time step in hours.
            load_profile (array): Load profile of the system in kW.

        Returns:
            dict: Dictionary containing the results of the calculation.
        """

        # Check if the calculation has already been done
        if self.calculated == False:
            # Berechnung der Solarthermieanlage
            self.calculate_solar_thermal_with_storage(
                load_profile,
                VLT_L,
                RLT_L,
                TRY_data,
                time_steps,
                duration
            )

        print(f"Berechnung der Solarthermieanlage {self.name} abgeschlossen.")
        print(f"Gesamtwärmemenge: {self.Wärmemenge_MWh:.2f} MWh")
        print(f"Gesamtwärmeleistung: {self.Wärmeleistung_kW} kW")

        # Calculate number of starts and operating hours per start
        betrieb_mask = self.Wärmeleistung_kW > 0
        starts = np.diff(betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = self.Betriebsstunden / self.Anzahl_Starts if self.Anzahl_Starts > 0 else 0

        print(f"Anzahl der Starts: {self.Anzahl_Starts}")
        print(f"Betriebsstunden: {self.Betriebsstunden:.2f} Stunden")
        print(f"Betriebsstunden pro Start: {self.Betriebsstunden_pro_Start:.2f} Stunden")

        # Berechnung der Wärmegestehungskosten
        self.WGK = self.calculate_heat_generation_costs(economic_parameters)

        self.calculate_environmental_impact()

        results = {
            'tech_name': self.name,
            'Wärmemenge': self.Wärmemenge_MWh,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'WGK': self.WGK,
            'Anzahl_Starts': self.Anzahl_Starts,
            'Betriebsstunden': self.Betriebsstunden,
            'Betriebsstunden_pro_Start': self.Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie_Solarthermie,
            'Speicherladung_L': self.Speicherinhalt,
            'Speicherfüllstand_L': self.Speicherfüllstand,
            'color': "red"
        }

        return results
    
    def set_parameters(self, variables, variables_order, idx):
        """
        Setzt spezifische Parameter für Solarthermie basierend auf den Optimierungsvariablen.

        Args:
            variables (list): Liste der Optimierungsvariablen.
            variables_order (list): Reihenfolge der Variablen, die ihre Zuordnung beschreibt.
            idx (int): Index der aktuellen Technologie in der Liste.
        """
        try:
            self.bruttofläche_STA = variables[variables_order.index(f"bruttofläche_STA_{idx}")]
            self.vs = variables[variables_order.index(f"vs_{idx}")]
        except ValueError as e:
            print(f"Fehler beim Setzen der Parameter für {self.name}: {e}")

    def add_optimization_parameters(self, idx):
        """
        Fügt Optimierungsparameter für Solarthermie hinzu und gibt sie zurück.

        Args:
            idx (int): Index der Technologie in der Liste.

        Returns:
            tuple: Initiale Werte, Variablennamen und Grenzen der Variablen.
        """

        initial_values = [self.bruttofläche_STA, self.vs]
        variables_order = [f"bruttofläche_STA_{idx}", f"vs_{idx}"]
        bounds = [(self.opt_area_min, self.opt_area_max), (self.opt_volume_min, self.opt_volume_max)]
        
        return initial_values, variables_order, bounds

    def get_display_text(self):
        return (f"{self.name}: Bruttokollektorfläche: {self.bruttofläche_STA:.1f} m², "
                f"Volumen Solarspeicher: {self.vs:.1} m³, Kollektortyp: {self.Typ}, "
                f"spez. Kosten Speicher: {self.kosten_speicher_spez:.1f} €/m³, "
                f"spez. Kosten Flachkollektor: {self.kosten_fk_spez:.1f} €/m², "
                f"spez. Kosten Röhrenkollektor: {self.kosten_vrk_spez:.1f} €/m²")
    
    def extract_tech_data(self):
        dimensions = f"Bruttokollektorfläche: {self.bruttofläche_STA:.1f} m², Speichervolumen: {self.vs:.1f} m³, Kollektortyp: {self.Typ}"
        costs = f"Investitionskosten Speicher: {self.Investitionskosten_Speicher:.1f} €, Investitionskosten STA: {self.Investitionskosten_STA:.1f} €"
        full_costs = f"{self.Investitionskosten:.1f}"
        return self.name, dimensions, costs, full_costs

class SolarThermalStrategy(BaseStrategy):
    def __init__(self, charge_on, charge_off=None):
        """
        Initializes the Solar Thermal strategy with a switch point based on storage levels.

        Args:
            charge_on (int): Storage temperature to activate the Solar Thermal.
            charge_off (int, optional): Storage temperature to deactivate the Solar Thermal. Defaults to None.
        """
        super().__init__(charge_on, charge_off)  # Initialize BaseStrategy with charge_on and charge_off

    def decide_operation(self, current_state, upper_storage_temp, lower_storage_temp, remaining_demand):
        """
        Decide whether to turn the Solar Thermal on based on storage temperature and remaining demand.

        Args:
            current_state (float): Current state of the system (not used in this implementation).
            upper_storage_temp (float): Current upper storage temperature.
            lower_storage_temp (float): Current lower storage temperature (not used in this implementation).
            remaining_demand (float): Remaining heat demand to be covered.

        Returns:
            bool: True if the Solar Thermal should be turned on, False otherwise.
        """
        
        # Solar Thermal will always produce
        return True