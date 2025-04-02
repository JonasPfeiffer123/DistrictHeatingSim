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
from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator

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

        self.init_operation(8760)

    def init_operation(self, hours):
        self.Wärmeleistung_kW = np.zeros(hours)
        self.Speicherladung = np.zeros(hours)
        self.Speicherfüllstand = np.zeros(hours)
        self.Wärmemenge_MWh = 0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0
        self.Betriebsstunden_pro_Start = 0

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
        # Berechnung der Solarthermieanlage
        self.Wärmemenge_MWh, self.Wärmeleistung_kW, self.Speicherladung, self.Speicherfüllstand = Berechnung_STA(self.bruttofläche_STA, self.vs, self.Typ, load_profile, VLT_L, RLT_L, 
                                                                                                        TRY_data, time_steps, duration, self.Tsmax, self.Longitude, self.STD_Longitude, self.Latitude, 
                                                                                                        self.East_West_collector_azimuth_angle, self.Collector_tilt_angle, self.Tm_rl, self.Qsa, 
        
                                                                                                        self.Vorwärmung_K, self.DT_WT_Solar_K, self.DT_WT_Netz_K)
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
    
    def generate(self, t, remaining_demand, VLT_L, RLT_L, TRY_data, time_steps, duration):
        """
        Generates heat for the solar thermal system at a given time step.

        Args:
            t (int): Current time step.
            remaining_demand (float): Remaining heat demand in kW.
            VLT_L (float): Flow temperature at the current time step.
            RLT_L (float): Return temperature at the current time step.
            TRY_data (array-like): Test Reference Year data.
            time_steps (array-like): Array of time steps.
            duration (float): Duration of each time step in hours.

        Returns:
            float: Heat generation (kW) for the current time step.
        """
        # Berechnung der Solarthermieanlage für den aktuellen Zeitschritt
        Gesamtwärmemenge, Wärmeleistung, Speicherladung, Speicherfüllstand = Berechnung_STA(
            self.bruttofläche_STA,
            self.vs,
            self.Typ,
            [remaining_demand],  # Nur den aktuellen Zeitschritt übergeben
            [VLT_L],
            [RLT_L],
            TRY_data,
            [time_steps[t]],
            duration,
            self.Tsmax,
            self.Longitude,
            self.STD_Longitude,
            self.Latitude,
            self.East_West_collector_azimuth_angle,
            self.Collector_tilt_angle,
            self.Tm_rl,
            self.Qsa,
            self.Vorwärmung_K,
            self.DT_WT_Solar_K,
            self.DT_WT_Netz_K
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

def Berechnung_STA(Bruttofläche_STA, VS, Typ, Last_L, VLT_L, RLT_L, TRY_data, time_steps, duration, Tsmax=90, Longitude=-14.4222, STD_Longitude=-15, Latitude=51.1676,
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
        TRY_data (tuple): TRY-Daten (Temperatur, Windgeschwindigkeit, Direktstrahlung, Globalstrahlung).
        time_steps (array): Zeitstempel.
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
    # To do: Refining data processing that calc1 and calc2 are not necessary, dont give the whole TRY to this function
    Temperatur_L, Windgeschwindigkeit_L, Direktstrahlung_L, Globalstrahlung_L = TRY_data[0], TRY_data[1], TRY_data[2], TRY_data[3]

    # Bestimmen Sie das kleinste Zeitintervall in time_steps
    min_interval = np.min(np.diff(time_steps)).astype('timedelta64[m]').astype(int)

    # Anpassen der stündlichen Werte an die time_steps
    # Wiederholen der stündlichen Werte entsprechend des kleinsten Zeitintervalls
    repeat_factor = 60 // min_interval  # Annahme: min_interval teilt 60 ohne Rest
    start_time_step, end_time_step = 0, len(time_steps)
    Temperatur_L = np.repeat(Temperatur_L, repeat_factor)[start_time_step:end_time_step]
    Windgeschwindigkeit_L = np.repeat(Windgeschwindigkeit_L, repeat_factor)[start_time_step:end_time_step]
    Direktstrahlung_L = np.repeat(Direktstrahlung_L, repeat_factor)[start_time_step:end_time_step]
    Globalstrahlung_L = np.repeat(Globalstrahlung_L, repeat_factor)[start_time_step:end_time_step]

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

