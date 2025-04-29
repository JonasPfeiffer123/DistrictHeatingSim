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
from datetime import datetime, timezone

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

        # Vorgabewerte Rohrleitungen
        self.Y_R = 2  # 1 oberirdisch, 2 erdverlegt, 3...
        self.Lrbin_E = 80
        self.Drbin_E = 0.1071
        self.P_KR_E = 0.26

        self.AR = self.Lrbin_E * self.Drbin_E * 3.14
        self.KR_E = self.P_KR_E * self.Lrbin_E / self.AR
        self.VRV_bin = self.Lrbin_E * (self.Drbin_E / 2) ** 2 * 3.14

        self.D46 = 0.035
        self.D47 = self.D46 / self.KR_E / 2
        self.L_Erdreich = 2
        self.D49 = 0.8
        self.D51 = self.L_Erdreich / self.D46 * log((self.Drbin_E / 2 + self.D47) / (self.Drbin_E / 2))
        self.D52 = log(2 * self.D49 / (self.Drbin_E / 2 + self.D47)) + self.D51 + log(sqrt(1 + (self.D49 / self.Drbin_E) ** 2))
        self.hs_RE = 1 / self.D52
        self.D54 = 2 * pi * self.L_Erdreich * self.hs_RE
        self.D55 = 2 * self.D54
        self.D56 = pi * (self.Drbin_E + 2 * self.D47)
        self.Keq_RE = self.D55 / self.D56
        self.CRK = self.VRV_bin * 3790 / 3.6 / self.AR  # 3790 für Glykol, 4180 für Wasser

        # Interne Verrohrung
        self.VRV = 0.0006
        self.KK = 0.06
        self.CKK = self.VRV * 3790 / 3.6

        # Vorgabewerte Speicher
        self.QSmax = 1.16 * self.vs * (self.Tsmax - self.Tm_rl)

    def init_operation(self, hours):
        self.betrieb_mask = np.array([False] * hours)
        self.Wärmeleistung_kW = np.zeros(hours)
        self.Speicherladung = np.zeros(hours)
        self.Speicherfüllstand = np.zeros(hours)
        self.Wärmemenge_MWh = 0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0
        self.Betriebsstunden_pro_Start = 0

        self.calculated = False  # Flag to indicate if the calculation is done

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
        # To do: Refining data processing that calc1 and calc2 are not necessary, dont give the whole TRY to this function
        Lufttemperatur_L, Windgeschwindigkeit_L, Direktstrahlung_L, Globalstrahlung_L = TRY_data[0], TRY_data[1], TRY_data[2], TRY_data[3]

        # Bestimmen Sie das kleinste Zeitintervall in time_steps
        min_interval = np.min(np.diff(time_steps)).astype('timedelta64[m]').astype(int)

        # Anpassen der stündlichen Werte an die time_steps
        # Wiederholen der stündlichen Werte entsprechend des kleinsten Zeitintervalls
        repeat_factor = 60 // min_interval  # Annahme: min_interval teilt 60 ohne Rest
        start_time_step, end_time_step = 0, len(time_steps)
        Lufttemperatur_L = np.repeat(Lufttemperatur_L, repeat_factor)[start_time_step:end_time_step]
        Windgeschwindigkeit_L = np.repeat(Windgeschwindigkeit_L, repeat_factor)[start_time_step:end_time_step]
        Direktstrahlung_L = np.repeat(Direktstrahlung_L, repeat_factor)[start_time_step:end_time_step]
        Globalstrahlung_L = np.repeat(Globalstrahlung_L, repeat_factor)[start_time_step:end_time_step]

        if self.bruttofläche_STA == 0 or self.vs == 0:
            return 0, np.zeros_like(Last_L), np.zeros_like(Last_L), np.zeros_like(Last_L)
        
        Tag_des_Jahres_L = np.array([datetime.fromtimestamp(t.astype('datetime64[s]').astype(np.int64), tz=timezone.utc).timetuple().tm_yday for t in time_steps])

        GT_H_Gk, K_beam_L, GbT_L, GdT_H_Dk_L = calculate_solar_radiation(Globalstrahlung_L, Direktstrahlung_L, 
                                                                        Tag_des_Jahres_L, time_steps, self.Longitude,
                                                                        self.STD_Longitude, self.Latitude, self.Albedo, 
                                                                        self.East_West_collector_azimuth_angle,
                                                                        self.Collector_tilt_angle, self.IAM_W, self.IAM_N)

        # Initialisierung der Arrays für die Ergebnisse
        n_steps = len(time_steps)
        self.Wärmeleistung_kW = np.zeros(n_steps)
        self.Speicherladung = np.zeros(n_steps)
        self.Speicherfüllstand = np.zeros(n_steps)
        Tm_a_L = np.zeros(n_steps)
        Pkoll_a_L = np.zeros(n_steps)
        Pkoll_b_L = np.zeros(n_steps)
        T_koll_a_L = np.zeros(n_steps)
        T_koll_b_L = np.zeros(n_steps)
        Tgkoll_a_L = np.zeros(n_steps)
        Tgkoll_L = np.zeros(n_steps)
        Summe_PRV_L = np.zeros(n_steps)
        self.Kollektorfeldertrag_L = np.zeros(n_steps)
        Zieltemperatur_Solaranlage_L = np.zeros(n_steps)
        TRL_Solar_L = np.zeros(n_steps)
        TS_unten_L = np.zeros(n_steps)
        PSV_L = np.zeros(n_steps)
        self.Stagnation_L = np.zeros(n_steps)
        
        # Temperatur Rohrleitungsvorlauf Verbindungsleitungen
        TRV_bin_vl_L = Lufttemperatur_L
        # Temperatur Rohrleitungsrücklauf Verbindungsleitungen
        TRV_bin_rl_L = Lufttemperatur_L

        # Temperatur Rohrleitungsvorlauf interne Rohrleitungen
        TRV_int_vl_L = Lufttemperatur_L
        # Temperatur Rohrleitungsrücklauf interne Rohrleitungen
        TRV_int_rl_L = Lufttemperatur_L

        for i in range(n_steps):
            Eta0b_neu_K_beam_GbT = self.Eta0b_neu * K_beam_L[i] * GbT_L[i]
            Eta0b_neu_Kthetadiff_GdT_H_Dk = self.Eta0b_neu * self.Kthetadiff * GdT_H_Dk_L[i]

            if i == 0:
                TS_unten_L[i] = RLT_L[i]
                TRL_Solar_L[i] = RLT_L[i]
                Zieltemperatur_Solaranlage_L[i] = TS_unten_L[i] + self.Vorwärmung_K + self.DT_WT_Solar_K + self.DT_WT_Netz_K
                Tm_a_L[i] = (Zieltemperatur_Solaranlage_L[i] + TRL_Solar_L[i]) / 2
                Pkoll_a_L[i] = 0
                Tgkoll_a_L[i] = 9.3
                T_koll_a_L[i] = Lufttemperatur_L[i] - (Lufttemperatur_L[i] - Tgkoll_a_L[i]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (Pkoll_a_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                Pkoll_b_L[i] = 0
                T_koll_b_L[i] = Lufttemperatur_L[i] - (Lufttemperatur_L[i] - 0) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (Pkoll_b_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                Tgkoll_L[i] = 9.3

                Summe_PRV_L[i] = 0
                self.Kollektorfeldertrag_L[i] = 0
                self.Wärmeleistung_kW[i] = min(self.Kollektorfeldertrag_L[i], Last_L[i])
                PSV_L[i] = 0
                self.Speicherladung[i] = self.Qsa * 1000
                self.Speicherfüllstand[i] = self.Speicherladung[i] / self.QSmax  # Speicherfüllungsgrad
                self.Stagnation_L[i] = 0

            else:
                # Calculate lower storage tank temperature
                if self.Speicherladung[i]/self.QSmax >= 0.8:
                    TS_unten_L[i] = RLT_L[i] + self.DT_WT_Netz_K + (2/3 * (VLT_L[i] - RLT_L[i]) / 0.2 * self.Speicherladung[i]/self.QSmax) + (1 / 3 * (VLT_L[i] - RLT_L[i])) - (2/3 * (VLT_L[i] - RLT_L[i]) / 0.2 * self.Speicherladung[i]/self.QSmax)
                else:
                    TS_unten_L[i] = RLT_L[i] + self.DT_WT_Netz_K + (1 / 3 * (VLT_L[i] - RLT_L[i]) / 0.8) * self.Speicherladung[i]/self.QSmax

                # Calculate solar target temperature and return line temperature
                Zieltemperatur_Solaranlage_L[i] = TS_unten_L[i] + self.Vorwärmung_K + self.DT_WT_Solar_K + self.DT_WT_Netz_K
                TRL_Solar_L[i] = TS_unten_L[i] + self.DT_WT_Solar_K

                # Calculate new collector A average temperature
                Tm_a_L[i] = (Zieltemperatur_Solaranlage_L[i] + TRL_Solar_L[i]) / 2

                # Calculate collector A power output and temperature
                c1a = self.Koll_c1 * (Tm_a_L[i] - Lufttemperatur_L[i])
                c2a = self.Koll_c2 * (Tm_a_L[i] - Lufttemperatur_L[i]) ** 2
                c3a = self.Koll_c3 * self.wcorr * Windgeschwindigkeit_L[i] * (Tm_a_L[i] - Lufttemperatur_L[i])

                Pkoll_a_L[i] = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1a - c2a - c3a) * self.Bezugsfläche / 1000)
                T_koll_a_L[i] = Lufttemperatur_L[i] - (Lufttemperatur_L[i] - Tgkoll_a_L[i - 1]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (Pkoll_a_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)

                # Calculate collector B power output and temperature
                c1b = self.Koll_c1 * (T_koll_b_L[i - 1] - Lufttemperatur_L[i])
                c2b = self.Koll_c2 * (T_koll_b_L[i - 1] - Lufttemperatur_L[i]) ** 2
                c3b = self.Koll_c3 * self.wcorr * Windgeschwindigkeit_L[i] * (T_koll_b_L[i - 1] - Lufttemperatur_L[i])
                
                Pkoll_b_L[i] = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1b - c2b - c3b) * self.Bezugsfläche / 1000)
                T_koll_b_L[i] = Lufttemperatur_L[i] - (Lufttemperatur_L[i] - Tgkoll_a_L[i - 1]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (Pkoll_b_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                
                # Calculate new collector A glycol temperature
                Tgkoll_a_L[i] = min(Zieltemperatur_Solaranlage_L[i], T_koll_a_L[i])

                # calculate average collector temperature
                Tm_koll_alt = (T_koll_a_L[i - 1] + T_koll_b_L[i - 1]) / 2
                Tm_koll = (T_koll_a_L[i] + T_koll_b_L[i]) / 2
                Tm_sys = (Zieltemperatur_Solaranlage_L[i] + TRL_Solar_L[i]) / 2
                if Tm_koll < Tm_sys and Tm_koll_alt < Tm_sys:
                    Tm = Tm_koll
                else:
                    Tm = Tm_sys

                # calculate collector power output
                c1 = self.Koll_c1 * (Tm - Lufttemperatur_L[i])
                c2 = self.Koll_c2 * (Tm - Lufttemperatur_L[i]) ** 2
                c3 = self.Koll_c3 * self.wcorr * Windgeschwindigkeit_L[i] * (Tm - Lufttemperatur_L[i])
                Pkoll = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1 - c2 - c3) * self.Bezugsfläche / 1000)

                # calculate collector temperature surplus
                T_koll = Lufttemperatur_L[i] - (Lufttemperatur_L[i] - Tgkoll_L[i - 1]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (Pkoll * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                Tgkoll_L[i] = min(Zieltemperatur_Solaranlage_L[i], T_koll)

                # Variablen für wiederkehrende Bedingungen definieren
                ziel_erreich = Tgkoll_L[i] >= Zieltemperatur_Solaranlage_L[i] and Pkoll > 0
                ziel_erhöht = Zieltemperatur_Solaranlage_L[i] >= Zieltemperatur_Solaranlage_L[i - 1]

                # Berechnung Temperatur Vorlauf und Rücklauf der Verbindungsleitungen und internen Rohrleitungen
                if ziel_erreich:
                    TRV_bin_vl_L[i] = Zieltemperatur_Solaranlage_L[i]
                    TRV_bin_rl_L[i] = TRL_Solar_L[i]
                else:
                    TRV_bin_vl_L[i] = Lufttemperatur_L[i] - (Lufttemperatur_L[i] - TRV_bin_vl_L[i - 1]) * exp(-self.Keq_RE / self.CRK)
                    TRV_bin_rl_L[i] = Lufttemperatur_L[i] - (Lufttemperatur_L[i] - TRV_bin_rl_L[i - 1]) * exp(-self.Keq_RE / self.CRK)

                # Berechnung der transitiven Verluste P_RVT_bin_vl und P_RVT_bin_rl Verbindungsleitungen, für Erdverlegte sind diese Identisch
                P_RVT_bin_vl = P_RVT_bin_rl = self.Lrbin_E / 1000 * ((TRV_bin_vl_L[i] + TRV_bin_rl_L[i]) / 2 - Lufttemperatur_L[i]) * 2 * pi * self.L_Erdreich * self.hs_RE

                # Berechnung der kapazitiven Verluste P_RVK_bin_vl und P_RVK_bin_rl Verbindungsleitungen
                if ziel_erhöht:
                    P_RVK_bin_vl = max((TRV_bin_vl_L[i - 1] - TRV_bin_vl_L[i]) * self.VRV_bin * 3790 / 3600, 0)
                    P_RVK_bin_rl = max((TRV_bin_rl_L[i - 1] - TRV_bin_rl_L[i]) * self.VRV_bin * 3790 / 3600, 0)
                else:
                    P_RVK_bin_vl = 0
                    P_RVK_bin_rl = 0

                trv_int_vl_check = Tgkoll_L[i] >= Zieltemperatur_Solaranlage_L[i] and Pkoll > 0
                trv_int_rl_check = Tgkoll_L[i] >= Zieltemperatur_Solaranlage_L[i] and Pkoll > 0

                # Berechnung der Temperatur Vorlauf und Rücklauf der internen Rohrleitungen
                TRV_int_vl_L[i] = Zieltemperatur_Solaranlage_L[i] if trv_int_vl_check else Lufttemperatur_L[i] - (
                            Lufttemperatur_L[i] - TRV_int_vl_L[i - 1]) * exp(-self.KK / self.CKK)
                TRV_int_rl_L[i] = TRL_Solar_L[i] if trv_int_rl_check else Lufttemperatur_L[i] - (Lufttemperatur_L[i] - TRV_int_rl_L[i - 1]) * exp(-self.KK / self.CKK)

                # Berechnung der transitiven Verluste P_RVT_int_vl und P_RVT_int_rl interne Rohrleitungen
                P_RVT_int_vl = (TRV_int_vl_L[i] - Lufttemperatur_L[i]) * self.KK * self.Bezugsfläche / 1000 / 2
                P_RVT_int_rl = (TRV_int_rl_L[i] - Lufttemperatur_L[i]) * self.KK * self.Bezugsfläche / 1000 / 2

                # Berechnung der kapazitiven Verluste P_RVK_int_vl und P_RVK_int_rl interne Rohrleitungen
                if Zieltemperatur_Solaranlage_L[i] < Zieltemperatur_Solaranlage_L[i - 1]:
                    P_RVK_int_vl = P_RVK_int_rl = 0
                else:
                    P_RVK_int_vl = max((TRV_int_vl_L[i - 1] - TRV_int_vl_L[i]) * self.VRV * self.Bezugsfläche / 2 * 3790 / 3600, 0)
                    P_RVK_int_rl = max((TRV_int_rl_L[i - 1] - TRV_int_rl_L[i]) * self.VRV * self.Bezugsfläche / 2 * 3790 / 3600, 0)
                
                # Berechnung der Rohrleitungsverluste
                PRV = max(P_RVT_bin_vl, P_RVK_bin_vl, 0) + max(P_RVT_bin_rl,P_RVK_bin_rl, 0) + \
                    max(P_RVT_int_vl, P_RVK_int_vl, 0) + max(P_RVT_int_rl, P_RVK_int_rl, 0)  # Rohrleitungsverluste

                # Berechnung Kollektorfeldertrag
                if T_koll > Tgkoll_L[i - 1]:
                    Pkoll_temp_corr = (T_koll-Tgkoll_L[i])/(T_koll-Tgkoll_L[i - 1]) * Pkoll if Tgkoll_L[i] >= Zieltemperatur_Solaranlage_L[i] else 0

                    self.Kollektorfeldertrag_L[i] = max(0, min(Pkoll, Pkoll_temp_corr)) if self.Stagnation_L[i - 1] <= 0 else 0
                else:
                    self.Kollektorfeldertrag_L[i] = 0

                # Rohrleitungsverluste aufsummiert
                if (self.Kollektorfeldertrag_L[i] == 0 and self.Kollektorfeldertrag_L[i - 1] == 0) or self.Kollektorfeldertrag_L[i] <= Summe_PRV_L[i - 1]:
                    Summe_PRV_L[i] = PRV + Summe_PRV_L[i - 1] - self.Kollektorfeldertrag_L[i]
                else:
                    Summe_PRV_L[i] = PRV

                if self.Kollektorfeldertrag_L[i] > Summe_PRV_L[i - 1]:
                    Zwischenwert = self.Kollektorfeldertrag_L[i] - Summe_PRV_L[i - 1]
                else:
                    Zwischenwert = 0

                self.Wärmeleistung_kW[i] = min(Zwischenwert + self.Speicherladung[i], Last_L[i]) if Zwischenwert + self.Speicherladung[i] > 0 else 0

                Zwischenwert_Stag_verl = max(0, self.Speicherladung[i] - PSV_L[i] + Zwischenwert - self.Wärmeleistung_kW[i] - self.QSmax)

                Speicher_Wärmeinput_ohne_FS = Zwischenwert - Zwischenwert_Stag_verl
                PSin = Speicher_Wärmeinput_ohne_FS

                if self.Speicherladung[i] - PSV_L[i] + PSin - self.Wärmeleistung_kW[i] > self.QSmax:
                    self.Speicherladung[i] = self.QSmax
                else:
                    self.Speicherladung[i] = self.Speicherladung[i] - PSV_L[i] + PSin - self.Wärmeleistung_kW[i]

                # Berechnung Mitteltemperatur im Speicher
                self.Speicherfüllstand[i] = self.Speicherladung[i] / self.QSmax  # Speicherfüllungsgrad

                TS_oben = Zieltemperatur_Solaranlage_L[i] - self.DT_WT_Solar_K
                if self.Speicherladung[i] <= 0:
                    berechnete_temperatur = TS_oben
                else:
                    temperaturverhältnis = (TS_oben - self.Tm_rl) / (self.Tsmax - self.Tm_rl)
                    if self.Speicherfüllstand[i] < temperaturverhältnis:
                        berechnete_temperatur = VLT_L[i] + self.DT_WT_Netz_K
                    else:
                        berechnete_temperatur = self.Tsmax

                gewichtete_untere_temperatur = (1 - self.Speicherfüllstand[i]) * TS_unten_L[i]
                Tms = self.Speicherfüllstand[i] * berechnete_temperatur + gewichtete_untere_temperatur

                PSV_L[i] = 0.75 * (self.vs * 1000) ** 0.5 * 0.16 * (Tms - Lufttemperatur_L[i]) / 1000

                self.Stagnation_L[i] = 1 if Tag_des_Jahres_L[i] == Tag_des_Jahres_L[i - 1] and Zwischenwert > Last_L[i] and self.Speicherladung[i] >= self.QSmax else 0

        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW) * duration / 1000  # kWh -> MWh

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

        # Calculate number of starts and operating hours per start
        betrieb_mask = self.Wärmeleistung_kW > 0
        starts = np.diff(betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = self.Betriebsstunden / self.Anzahl_Starts if self.Anzahl_Starts > 0 else 0

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
            'Speicherladung_L': self.Speicherladung,
            'Speicherfüllstand_L': self.Speicherfüllstand,
            'color': "red"
        }

        return results
    
    def generate(self, t, **kwargs):
        """
        Generates heat for the solar thermal system at a given time step.

        Args:
            t (int): Current time step.
            kwargs (dict): Additional arguments including load profile, TRY data, and time steps.

        Returns:
            float: Heat generation (kW) for the current time step.
        """
        remaining_demand = kwargs.get('remaining_demand')
        VLT_L = kwargs.get('VLT_L')
        RLT_L = kwargs.get('RLT_L')
        TRY_data = kwargs.get('TRY_data')
        time_steps = kwargs.get('time_steps')
        duration = kwargs.get('duration')

        # Berechnung der Solarthermieanlage für den aktuellen Zeitschritt
        Gesamtwärmemenge, Wärmeleistung, Speicherladung, Speicherfüllstand = self.calculate_solar_thermal_with_storage(
            remaining_demand,  # Nur den aktuellen Zeitschritt übergeben
            VLT_L,
            RLT_L,
            TRY_data,
            time_steps,
            duration
        )

        # Ergebnisse für den aktuellen Zeitschritt speichern
        self.Wärmeleistung_kW[t] = Wärmeleistung[0]
        self.Speicherladung[t] = Speicherladung[0]
        self.Speicherfüllstand[t] = Speicherfüllstand[0]

        # Kumulative Werte aktualisieren
        self.Wärmemenge_MWh += Wärmeleistung[0] / 1000  # kW -> MWh
        if Wärmeleistung[0] > 0:
            self.Betriebsstunden += duration
            if t == 0 or self.Wärmeleistung_kW[t - 1] == 0:
                self.Anzahl_Starts += 1
        self.Betriebsstunden_pro_Start = self.Betriebsstunden / self.Anzahl_Starts if self.Anzahl_Starts > 0 else 0

        return Wärmeleistung[0]  # Rückgabe der erzeugten Wärmeleistung für den aktuellen Zeitschritt
    
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