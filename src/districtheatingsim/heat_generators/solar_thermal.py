"""
Filename: solar_thermal.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-10
Description: This script calculates the heat generation of a thermal solar heat generator.

Additional Information: Yield calculation program for solar thermal energy in heating networks (calculation basis: ScenoCalc District Heating 2.0) https://www.scfw.de/)
"""

# Import Bibliotheken
from math import pi, exp, log, sqrt
import numpy as np
from datetime import datetime, timezone

from districtheatingsim.heat_generators.solar_radiation import calculate_solar_radiation
from districtheatingsim.heat_generators.annuity import annuität

class SolarThermal:
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
                 DT_WT_Solar_K=5, DT_WT_Netz_K=5, opt_volume_min=0, opt_volume_max=200, opt_area_min=0, opt_area_max=2000):
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
        self.name = name
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

    def calculate_heat_generation_costs(self, q, r, T, BEW, stundensatz):
        """
        Calculates the weighted average cost of heat generation (WGK).

        Args:
            q (float): Factor for capital recovery.
            r (float): Factor for price escalation.
            T (int): Time period in years.
            BEW (str): Subsidy eligibility ("Ja" or "Nein").
            stundensatz (float): Hourly rate for labor.

        Returns:
            float: Weighted average cost of heat generation.
        """
        if self.Wärmemenge == 0:
            return 0

        self.Investitionskosten_Speicher = self.vs * self.kosten_speicher_spez
        self.Investitionskosten_STA = self.bruttofläche_STA * self.Kosten_STA_spez
        self.Investitionskosten = self.Investitionskosten_Speicher + self.Investitionskosten_STA

        self.A_N = annuität(self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, q, r, T, stundensatz=stundensatz)
        self.WGK = self.A_N / self.Wärmemenge

        self.Eigenanteil = 1 - self.Anteil_Förderung_BEW
        self.Investitionskosten_Gesamt_BEW = self.Investitionskosten * self.Eigenanteil
        self.Annuität_BEW = annuität(self.Investitionskosten_Gesamt_BEW, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, q, r, T, stundensatz=stundensatz)
        self.WGK_BEW = self.Annuität_BEW / self.Wärmemenge

        self.WGK_BEW_BKF = self.WGK_BEW - self.Betriebskostenförderung_BEW

        if BEW == "Nein":
            return self.WGK
        elif BEW == "Ja":
            return self.WGK_BEW_BKF
        
    def calculate_environmental_impact(self):
        # Berechnung der Emissionen
        self.co2_emissions = self.Wärmemenge * self.co2_factor_solar  # tCO2
        # specific emissions heat
        self.spec_co2_total = self.co2_emissions / self.Wärmemenge if self.Wärmemenge > 0 else 0  # tCO2/MWh_heat

        self.primärenergie_Solarthermie = self.Wärmemenge * self.primärenergiefaktor
        
    def calculate(self, VLT_L, RLT_L, TRY, time_steps, calc1, calc2, q, r, T, BEW, stundensatz, duration, general_results):
        """
        Calculates the performance and cost of the solar thermal system.

        Args:
            VLT_L (array): Forward temperature profile in degrees Celsius.
            RLT_L (array): Return temperature profile in degrees Celsius.
            TRY (array): Test Reference Year data.
            time_steps (array): Array of time steps.
            calc1 (float): Calculation parameter 1.
            calc2 (float): Calculation parameter 2.
            q (float): Factor for capital recovery.
            r (float): Factor for price escalation.
            T (int): Time period in years.
            BEW (str): Subsidy eligibility ("Ja" or "Nein").
            stundensatz (float): Hourly rate for labor.
            duration (float): Duration of each time step in hours.
            general_results (dict): General results dictionary containing rest load.

        Returns:
            dict: Dictionary containing the results of the calculation.
        """
        # Berechnung der Solarthermieanlage
        self.Wärmemenge, self.Wärmeleistung_kW, self.Speicherladung, self.Speicherfüllstand = Berechnung_STA(self.bruttofläche_STA, 
                                                                                                        self.vs, self.Typ, general_results['Restlast_L'], VLT_L, RLT_L, 
                                                                                                        TRY, time_steps, calc1, calc2, duration, self.Tsmax, self.Longitude, self.STD_Longitude, 
                                                                                                        self.Latitude, self.East_West_collector_azimuth_angle, self.Collector_tilt_angle, self.Tm_rl, 
                                                                                                        self.Qsa, self.Vorwärmung_K, self.DT_WT_Solar_K, self.DT_WT_Netz_K)
        # Berechnung der Wärmegestehungskosten
        self.WGK = self.calculate_heat_generation_costs(q, r, T, BEW, stundensatz)

        self.calculate_environmental_impact()

        results = { 
            'Wärmemenge': self.Wärmemenge,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'WGK': self.WGK,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie_Solarthermie,
            'Speicherladung_L': self.Speicherladung,
            'Speicherfüllstand_L': self.Speicherfüllstand,
            'color': "red"
        }

        return results

    def get_display_text(self):
        return (f"{self.name}: Bruttokollektorfläche: {self.bruttofläche_STA} m², "
                f"Volumen Solarspeicher: {self.vs} m³, Kollektortyp: {self.Typ}, "
                f"spez. Kosten Speicher: {self.kosten_speicher_spez} €/m³, "
                f"spez. Kosten Flachkollektor: {self.kosten_fk_spez} €/m², "
                f"spez. Kosten Röhrenkollektor: {self.kosten_vrk_spez} €/m²")
    
    def to_dict(self):
        """
        Converts the SolarThermal object to a dictionary.

        Returns:
            dict: Dictionary representation of the SolarThermal object.
        """
        # Erstelle eine Kopie des aktuellen Objekt-Dictionaries
        data = self.__dict__.copy()
        
        # Entferne das scene_item und andere nicht notwendige Felder
        data.pop('scene_item', None)
        return data

    @staticmethod
    def from_dict(data):
        """
        Creates a SolarThermal object from a dictionary.

        Args:
            data (dict): Dictionary containing the attributes of a SolarThermal object.

        Returns:
            SolarThermal: A new SolarThermal object with attributes from the dictionary.
        """
        obj = SolarThermal.__new__(SolarThermal)
        obj.__dict__.update(data)
        return obj

def Berechnung_STA(Bruttofläche_STA, VS, Typ, Last_L, VLT_L, RLT_L, TRY, time_steps, calc1, calc2, duration, Tsmax=90, Longitude=-14.4222, STD_Longitude=-15, Latitude=51.1676,
                   East_West_collector_azimuth_angle=0, Collector_tilt_angle=36, Tm_rl=60, Qsa=0, Vorwärmung_K=8, DT_WT_Solar_K=5, DT_WT_Netz_K=5):
    """
    Berechnung der thermischen Solaranlage (STA) zur Wärmegewinnung.

    Args:
        Bruttofläche_STA (float): Bruttofläche der Solaranlage.
        VS (float): Speichervolumen der Solaranlage.
        Typ (str): Typ der Solaranlage ("Flachkollektor" oder "Vakuumröhrenkollektor").
        Last_L (array): Lastprofil.
        VLT_L (array): Vorlauftemperaturprofil.
        RLT_L (array): Rücklauftemperaturprofil.
        TRY (tuple): TRY-Daten (Temperatur, Windgeschwindigkeit, Direktstrahlung, Globalstrahlung).
        time_steps (array): Zeitstempel.
        calc1 (int): Startindex für die Berechnung.
        calc2 (int): Endindex für die Berechnung.
        duration (float): Zeitdauer der Berechnung.
        Tsmax (float, optional): Maximale Speichertemperatur. Defaults to 90.
        Longitude (float, optional): Längengrad des Standorts. Defaults to -14.4222.
        STD_Longitude (float, optional): Standardlängengrad. Defaults to -15.
        Latitude (float, optional): Breitengrad des Standorts. Defaults to 51.1676.
        East_West_collector_azimuth_angle (float, optional): Azimutwinkel des Kollektors. Defaults to 0.
        Collector_tilt_angle (float, optional): Neigungswinkel des Kollektors. Defaults to 36.
        Tm_rl (float, optional): Mittlere Rücklauftemperatur. Defaults to 60.
        Qsa (float, optional): Anfangswärmemenge im Speicher. Defaults to 0.
        Vorwärmung_K (float, optional): Vorwärmung in Kelvin. Defaults to 8.
        DT_WT_Solar_K (float, optional): Temperaturdifferenz Wärmetauscher Solar in Kelvin. Defaults to 5.
        DT_WT_Netz_K (float, optional): Temperaturdifferenz Wärmetauscher Netz in Kelvin. Defaults to 5.

    Returns:
        tuple: Gesamtwärmemenge, Wärmeoutput, Speicherladung und Speicherfüllstand.
    """
    Temperatur_L, Windgeschwindigkeit_L, Direktstrahlung_L, Globalstrahlung_L = TRY[0], TRY[1], TRY[2], TRY[3]

    # Bestimmen Sie das kleinste Zeitintervall in time_steps
    min_interval = np.min(np.diff(time_steps)).astype('timedelta64[m]').astype(int)

    # Anpassen der stündlichen Werte an die time_steps
    # Wiederholen der stündlichen Werte entsprechend des kleinsten Zeitintervalls
    repeat_factor = 60 // min_interval  # Annahme: min_interval teilt 60 ohne Rest
    Temperatur_L = np.repeat(Temperatur_L, repeat_factor)[calc1:calc2]
    Windgeschwindigkeit_L = np.repeat(Windgeschwindigkeit_L, repeat_factor)[calc1:calc2]
    Direktstrahlung_L = np.repeat(Direktstrahlung_L, repeat_factor)[calc1:calc2]
    Globalstrahlung_L = np.repeat(Globalstrahlung_L, repeat_factor)[calc1:calc2]

    if Bruttofläche_STA == 0 or VS == 0:
        return 0, np.zeros_like(Last_L), np.zeros_like(Last_L), np.zeros_like(Last_L)
    
    Tag_des_Jahres_L = np.array([datetime.fromtimestamp(t.astype('datetime64[s]').astype(np.int64), tz=timezone.utc).timetuple().tm_yday for t in time_steps])

    # Definition Albedo-Wert
    Albedo = 0.2
    # Definition Korrekturfaktor Windgeschwindigkeit
    wcorr = 0.5

    if Typ == "Flachkollektor":
        # Vorgabewerte Flachkollektor Vitosol 200-F XL13
        # Bruttofläche ist Bezugsfläche
        Eta0b_neu = 0.763
        Kthetadiff = 0.931
        Koll_c1 = 1.969
        Koll_c2 = 0.015
        Koll_c3 = 0
        KollCeff_A = 9.053
        KollAG = 13.17
        KollAAp = 12.35

        Aperaturfläche = Bruttofläche_STA * (KollAAp / KollAG)
        Bezugsfläche = Bruttofläche_STA

        IAM_W = {0: 1, 10: 1, 20: 0.99, 30: 0.98, 40: 0.96, 50: 0.91, 60: 0.82, 70: 0.53, 80: 0.27, 90: 0.0}
        IAM_N = {0: 1, 10: 1, 20: 0.99, 30: 0.98, 40: 0.96, 50: 0.91, 60: 0.82, 70: 0.53, 80: 0.27, 90: 0.0}

    if Typ == "Vakuumröhrenkollektor":
        # Vorgabewerte Vakuumröhrenkollektor
        # Aperaturfläche ist Bezugsfläche
        Eta0hem = 0.688
        a1 = 0.583
        a2 = 0.003
        KollCeff_A = 8.78
        KollAG = 4.94
        KollAAp = 4.5

        Koll_c1 = a1
        Koll_c2 = a2
        Koll_c3 = 0
        Eta0b_neu = 0.693
        Kthetadiff = 0.951

        Aperaturfläche = Bruttofläche_STA * (KollAAp / KollAG)
        Bezugsfläche = Aperaturfläche

        IAM_W = {0: 1, 10: 1.02, 20: 1.03, 30: 1.03, 40: 1.03, 50: 0.96, 60: 1.07, 70: 1.19, 80: 0.595, 90: 0.0}
        IAM_N = {0: 1, 10: 1, 20: 0.99, 30: 0.96, 40: 0.93, 50: 0.9, 60: 0.87, 70: 0.86, 80: 0.43, 90: 0.0}

    # Vorgabewerte Rohrleitungen
    Y_R = 2  # 1 oberirdisch, 2 erdverlegt, 3...
    Lrbin_E = 80
    Drbin_E = 0.1071
    P_KR_E = 0.26

    AR = Lrbin_E * Drbin_E * 3.14
    KR_E = P_KR_E * Lrbin_E / AR
    VRV_bin = Lrbin_E * (Drbin_E / 2) ** 2 * 3.14

    D46 = 0.035
    D47 = D46 / KR_E / 2
    L_Erdreich = 2
    D49 = 0.8
    D51 = L_Erdreich / D46 * log((Drbin_E / 2 + D47) / (Drbin_E / 2))
    D52 = log(2 * D49 / (Drbin_E / 2 + D47)) + D51 + log(sqrt(1 + (D49 / Drbin_E) ** 2))
    hs_RE = 1 / D52
    D54 = 2 * pi * L_Erdreich * hs_RE
    D55 = 2 * D54
    D56 = pi * (Drbin_E + 2 * D47)
    Keq_RE = D55 / D56
    CRK = VRV_bin * 3790 / 3.6 / AR  # 3790 für Glykol, 4180 für Wasser

    # Interne Verrohrung
    VRV = 0.0006
    KK = 0.06
    CKK = VRV * 3790 / 3.6

    # Vorgabewerte Speicher
    QSmax = 1.16 * VS * (Tsmax - Tm_rl)

    GT_H_Gk, K_beam_L, GbT_L, GdT_H_Dk_L = calculate_solar_radiation(Globalstrahlung_L, Direktstrahlung_L, 
                                                                     Tag_des_Jahres_L, time_steps, Longitude,
                                                                     STD_Longitude, Latitude, Albedo, East_West_collector_azimuth_angle,
                                                                     Collector_tilt_angle, IAM_W, IAM_N)

    Speicher_Wärmeoutput_L = []
    Speicherladung_L = []
    Speicherfüllstand_L = []
    Gesamtwärmemenge = 0

    Zähler = 0

    for Tag_des_Jahres, K_beam, GbT, GdT_H_Dk, Temperatur, Windgeschwindigkeit, Last, VLT, RLT in zip(Tag_des_Jahres_L, K_beam_L, GbT_L, GdT_H_Dk_L, Temperatur_L, Windgeschwindigkeit_L, Last_L, VLT_L, RLT_L):
        Eta0b_neu_K_beam_GbT = Eta0b_neu * K_beam * GbT
        Eta0b_neu_Kthetadiff_GdT_H_Dk = Eta0b_neu * Kthetadiff * GdT_H_Dk

        if Zähler < 1:
            TS_unten = RLT
            Zieltemperatur_Solaranlage = TS_unten + Vorwärmung_K + DT_WT_Solar_K + DT_WT_Netz_K
            TRL_Solar = RLT
            Tm_a = (Zieltemperatur_Solaranlage + TRL_Solar) / 2
            Pkoll_a = 0
            Tgkoll_a = 9.3
            T_koll_a = Temperatur - (Temperatur - Tgkoll_a) * exp(-Koll_c1 / KollCeff_A * 3.6) + (Pkoll_a * 3600) / (
                        KollCeff_A * Bezugsfläche)
            Pkoll_b = 0
            T_koll_b = Temperatur - (Temperatur - 0) * exp(-Koll_c1 / KollCeff_A * 3.6) + (Pkoll_b * 3600) / (
                        KollCeff_A * Bezugsfläche)
            Tgkoll = 9.3  # Kollektortemperatur im Gleichgewicht

            # Verluste Verbindungsleitung
            TRV_bin_vl = Temperatur
            TRV_bin_rl = Temperatur

            # Verluste interne Rohrleitungen
            TRV_int_vl = Temperatur
            TRV_int_rl = Temperatur
            Summe_PRV = 0  # Rohrleitungsverluste aufsummiert
            Kollektorfeldertrag = 0
            PSout = min(Kollektorfeldertrag, Last)
            QS = Qsa * 1000
            PSV = 0
            Tag_des_Jahres_alt = Tag_des_Jahres
            Stagnation = 0
            S_HFG = QS / QSmax  # Speicherfüllungsgrad

        else:
            T_koll_a_alt = T_koll_a
            T_koll_b_alt = T_koll_b
            Tgkoll_a_alt = Tgkoll_a
            Tgkoll_alt = Tgkoll
            Summe_PRV_alt = Summe_PRV
            Zieltemperatur_Solaranlage_alt = Zieltemperatur_Solaranlage
            Kollektorfeldertrag_alt = Kollektorfeldertrag

            # Define constants
            c1 = Koll_c1 * (Tm_a - Temperatur)
            c2 = Koll_c2 * (Tm_a - Temperatur) ** 2
            c3 = Koll_c3 * wcorr * Windgeschwindigkeit * (Tm_a - Temperatur)

            # Calculate lower storage tank temperature
            if QS/QSmax >= 0.8:
                TS_unten = RLT + DT_WT_Netz_K + (2/3 * (VLT - RLT) / 0.2 * QS/QSmax) + (1 / 3 * (VLT - RLT)) - (2/3 * (VLT - RLT) / 0.2 * QS/QSmax)
            else:
                TS_unten = RLT + DT_WT_Netz_K + (1 / 3 * (VLT - RLT) / 0.8) * QS/QSmax

            # Calculate solar target temperature and return line temperature
            Zieltemperatur_Solaranlage = TS_unten + Vorwärmung_K + DT_WT_Solar_K + DT_WT_Netz_K
            TRL_Solar = TS_unten + DT_WT_Solar_K

            # Calculate collector A power output and temperature
            Pkoll_a = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1 - c2 - c3) * Bezugsfläche / 1000)
            T_koll_a = Temperatur - (Temperatur - Tgkoll_a_alt) * exp(-Koll_c1 / KollCeff_A * 3.6) + (Pkoll_a * 3600) / (
                        KollCeff_A * Bezugsfläche)

            # Calculate collector B power output and temperature
            c1 = Koll_c1 * (T_koll_b_alt - Temperatur)
            c2 = Koll_c2 * (T_koll_b_alt - Temperatur) ** 2
            c3 = Koll_c3 * wcorr * Windgeschwindigkeit * (T_koll_b_alt - Temperatur)
            Pkoll_b = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1 - c2 - c3) * Bezugsfläche / 1000)
            T_koll_b = Temperatur - (Temperatur - Tgkoll_a_alt) * exp(-Koll_c1 / KollCeff_A * 3.6) + (Pkoll_b * 3600) / (
                        KollCeff_A * Bezugsfläche)

            # Calculate new collector A glycol temperature and average temperature
            Tgkoll_a = min(Zieltemperatur_Solaranlage, T_koll_a)
            Tm_a = (Zieltemperatur_Solaranlage + TRL_Solar) / 2

            # calculate average collector temperature
            Tm_koll_alt = (T_koll_a_alt + T_koll_b_alt) / 2
            Tm_koll = (T_koll_a + T_koll_b) / 2
            Tm_sys = (Zieltemperatur_Solaranlage + TRL_Solar) / 2
            if Tm_koll < Tm_sys and Tm_koll_alt < Tm_sys:
                Tm = Tm_koll
            else:
                Tm = Tm_sys

            # calculate collector power output
            c1 = Koll_c1 * (Tm - Temperatur)
            c2 = Koll_c2 * (Tm - Temperatur) ** 2
            c3 = Koll_c3 * wcorr * Windgeschwindigkeit * (Tm - Temperatur)
            Pkoll = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1 - c2 - c3) * Bezugsfläche / 1000)

            # calculate collector temperature surplus
            T_koll = Temperatur - (Temperatur - Tgkoll) * exp(-Koll_c1 / KollCeff_A * 3.6) + (Pkoll * 3600) / (
                        KollCeff_A * Bezugsfläche)
            Tgkoll = min(Zieltemperatur_Solaranlage, T_koll)

            # Verluste Verbindungsleitung
            TRV_bin_vl_alt = TRV_bin_vl
            TRV_bin_rl_alt = TRV_bin_rl

            # Variablen für wiederkehrende Bedingungen definieren
            ziel_erreich = Tgkoll >= Zieltemperatur_Solaranlage and Pkoll > 0
            ziel_erhöht = Zieltemperatur_Solaranlage >= Zieltemperatur_Solaranlage_alt

            # Berechnung von TRV_bin_vl und TRV_bin_rl
            if ziel_erreich:
                TRV_bin_vl = Zieltemperatur_Solaranlage
                TRV_bin_rl = TRL_Solar
            else:
                TRV_bin_vl = Temperatur - (Temperatur - TRV_bin_vl_alt) * exp(-Keq_RE / CRK)
                TRV_bin_rl = Temperatur - (Temperatur - TRV_bin_rl_alt) * exp(-Keq_RE / CRK)

            # Berechnung von P_RVT_bin_vl und P_RVT_bin_rl, für Erdverlegte sind diese Identisch
            P_RVT_bin_vl = P_RVT_bin_rl = Lrbin_E / 1000 * ((TRV_bin_vl + TRV_bin_rl) / 2 - Temperatur) * 2 * pi * L_Erdreich * hs_RE

            # Berechnung von P_RVK_bin_vl und P_RVK_bin_rl
            if ziel_erhöht:
                P_RVK_bin_vl = max((TRV_bin_vl_alt - TRV_bin_vl) * VRV_bin * 3790 / 3600, 0)
                P_RVK_bin_rl = max((TRV_bin_rl_alt - TRV_bin_rl) * VRV_bin * 3790 / 3600, 0)
            else:
                P_RVK_bin_vl = 0
                P_RVK_bin_rl = 0

            # Verluste interne Rohrleitungen
            TRV_int_vl_alt = TRV_int_vl
            TRV_int_rl_alt = TRV_int_rl

            trv_int_vl_check = Tgkoll >= Zieltemperatur_Solaranlage and Pkoll > 0
            trv_int_rl_check = Tgkoll >= Zieltemperatur_Solaranlage and Pkoll > 0

            TRV_int_vl = Zieltemperatur_Solaranlage if trv_int_vl_check else Temperatur - (
                        Temperatur - TRV_int_vl_alt) * exp(-KK / CKK)
            TRV_int_rl = TRL_Solar if trv_int_rl_check else Temperatur - (Temperatur - TRV_int_rl_alt) * exp(-KK / CKK)

            P_RVT_int_vl = (TRV_int_vl - Temperatur) * KK * Bezugsfläche / 1000 / 2
            P_RVT_int_rl = (TRV_int_rl - Temperatur) * KK * Bezugsfläche / 1000 / 2

            if Zieltemperatur_Solaranlage < Zieltemperatur_Solaranlage_alt:
                P_RVK_int_vl = P_RVK_int_rl = 0
            else:
                P_RVK_int_vl = max((TRV_int_vl_alt - TRV_int_vl) * VRV * Bezugsfläche / 2 * 3790 / 3600, 0)
                P_RVK_int_rl = max((TRV_int_rl_alt - TRV_int_rl) * VRV * Bezugsfläche / 2 * 3790 / 3600, 0)

            PRV = max(P_RVT_bin_vl, P_RVK_bin_vl, 0) + max(P_RVT_bin_rl,P_RVK_bin_rl, 0) + \
                  max(P_RVT_int_vl, P_RVK_int_vl, 0) + max(P_RVT_int_rl, P_RVK_int_rl, 0)  # Rohrleitungsverluste

            # Berechnung Kollektorfeldertrag
            if T_koll > Tgkoll_alt:
                if Tgkoll >= Zieltemperatur_Solaranlage:
                    value1 = (T_koll-Tgkoll)/(T_koll-Tgkoll_alt) * Pkoll
                else:
                    value1 = 0
                value2 = max(0, min(Pkoll, value1))

                if Stagnation <= 0:
                    value3 = 1
                else:
                    value3 = 0
                Kollektorfeldertrag = value2 * value3
            else:
                Kollektorfeldertrag = 0

            # Rohrleitungsverluste aufsummiert
            if (Kollektorfeldertrag == 0 and Kollektorfeldertrag_alt == 0) or Kollektorfeldertrag <= Summe_PRV_alt:
                Summe_PRV = PRV + Summe_PRV_alt - Kollektorfeldertrag
            else:
                Summe_PRV = PRV

            if Kollektorfeldertrag > Summe_PRV_alt:
                Zwischenwert = Kollektorfeldertrag - Summe_PRV_alt
            else:
                Zwischenwert = 0

            PSout = min(Zwischenwert + QS, Last) if Zwischenwert + QS > 0 else 0

            Zwischenwert_Stag_verl = max(0, QS - PSV + Zwischenwert - PSout - QSmax)

            Speicher_Wärmeinput_ohne_FS = Zwischenwert - Zwischenwert_Stag_verl
            PSin = Speicher_Wärmeinput_ohne_FS

            if QS - PSV + PSin - PSout > QSmax:
                QS = QSmax
            else:
                QS = QS - PSV + PSin - PSout

            # Berechnung Mitteltemperatur im Speicher
            value1 = QS/QSmax
            value2 = Zieltemperatur_Solaranlage - DT_WT_Solar_K
            if QS <= 0:
                ergebnis1 = value2
            else:
                value3 = (value2 - Tm_rl) / (Tsmax - Tm_rl)
                if value1 < value3:
                    ergebnis1 = VLT + DT_WT_Netz_K
                else:
                    ergebnis1 = Tsmax

            value4 = (1 - value1) * TS_unten
            Tms = value1 * ergebnis1 + value4

            PSV = 0.75 * (VS * 1000) ** 0.5 * 0.16 * (Tms - Temperatur) / 1000

            if Tag_des_Jahres == Tag_des_Jahres_alt:
                value1_stagnation = 0
                if Zwischenwert > Last and QS >= QSmax:
                    value1_stagnation = 1
                Stagnation = 1 if value1_stagnation + Stagnation > 0 else 0
            else:
                Stagnation = 0

            S_HFG = QS / QSmax  # Speicherfüllungsgrad

        Speicherfüllstand_L.append(S_HFG)
        Speicherladung_L.append(QS)
        Speicher_Wärmeoutput_L.append(PSout)
        Gesamtwärmemenge += (PSout / 1000) * duration

        Zähler += 1

    return Gesamtwärmemenge, np.array(Speicher_Wärmeoutput_L).astype("float64"), np.array(Speicherladung_L).astype("float64"), np.array(Speicherfüllstand_L).astype("float64")

