import numpy as np
from datetime import datetime, timezone
from math import pi, exp, log, sqrt
from solar_radiation import calculate_solar_radiation
from test_reference_year import import_TRY

import matplotlib.pyplot as plt

def calculate_solar_thermal(Bruttofläche_STA, Typ, TRY, time_steps, RLT_array, calc1, calc2, 
                         Longitude=-14.4222, STD_Longitude=-15, Latitude=51.1676,
                         East_West_collector_azimuth_angle=0, Collector_tilt_angle=36):
    """
    Berechnung der thermischen Solaranlage (STA) zur Wärmegewinnung ohne Speichersystem.

    Args:
        Bruttofläche_STA (float): Bruttofläche der Solaranlage.
        Typ (str): Typ der Solaranlage ("Flachkollektor" oder "Vakuumröhrenkollektor").
        TRY (tuple): TRY-Daten (Temperatur, Windgeschwindigkeit, Direktstrahlung, Globalstrahlung).
        time_steps (array): Zeitstempel.
        RLT_array (array): Rücklauftemperaturprofil aus dem Speicher.
        calc1 (int): Startindex für die Berechnung.
        calc2 (int): Endindex für die Berechnung.
        Longitude (float, optional): Längengrad des Standorts. Defaults to -14.4222.
        STD_Longitude (float, optional): Standardlängengrad. Defaults to -15.
        Latitude (float, optional): Breitengrad des Standorts. Defaults to 51.1676.
        East_West_collector_azimuth_angle (float, optional): Azimutwinkel des Kollektors. Defaults to 0.
        Collector_tilt_angle (float, optional): Neigungswinkel des Kollektors. Defaults to 36.
        Vorwärmung_K (float, optional): Vorwärmung in Kelvin. Defaults to 8.
        DT_WT_Solar_K (float, optional): Temperaturdifferenz Wärmetauscher Solar in Kelvin. Defaults to 5.

    Returns:
        tuple: Kollektorfeldertrag, Strahlungsdaten
    """
    Temperatur_L, Windgeschwindigkeit_L, Direktstrahlung_L, Globalstrahlung_L = TRY[0], TRY[1], TRY[2], TRY[3]

    # Bestimmen Sie das kleinste Zeitintervall in time_steps
    min_interval = np.min(np.diff(time_steps)).astype('timedelta64[m]').astype(int)

    # Anpassen der stündlichen Werte an die time_steps
    repeat_factor = 60 // min_interval
    Temperatur_L = np.repeat(Temperatur_L, repeat_factor)[calc1:calc2]
    Windgeschwindigkeit_L = np.repeat(Windgeschwindigkeit_L, repeat_factor)[calc1:calc2]
    Direktstrahlung_L = np.repeat(Direktstrahlung_L, repeat_factor)[calc1:calc2]
    Globalstrahlung_L = np.repeat(Globalstrahlung_L, repeat_factor)[calc1:calc2]

    if Bruttofläche_STA == 0:
        return 0, np.zeros_like(time_steps)

    Tag_des_Jahres_L = np.array([datetime.fromtimestamp(t.astype('datetime64[s]').astype(np.int64), tz=timezone.utc).timetuple().tm_yday for t in time_steps])

    # Definition Albedo-Wert
    Albedo = 0.2
    wcorr = 0.5  # Windkorrekturfaktor

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

    # Berechnung der Strahlung auf den Kollektor
    _, K_beam_L, GbT_L, GdT_H_Dk_L = calculate_solar_radiation(Globalstrahlung_L, Direktstrahlung_L, 
                                                                     Tag_des_Jahres_L, time_steps, Longitude,
                                                                     STD_Longitude, Latitude, Albedo, 
                                                                     East_West_collector_azimuth_angle, Collector_tilt_angle,
                                                                     IAM_W, IAM_N)

    # Berechnung der Temperaturunterschiede für Kollektor
    delta_T = RLT_array - Temperatur_L
    delta_T2 = delta_T ** 2

    # Berechnung der Kollektorleistung (Pkoll_a)
    c1 = Koll_c1 * delta_T
    c2 = Koll_c2 * delta_T2
    c3 = Koll_c3 * wcorr * Windgeschwindigkeit_L * delta_T

    # Berechnung der Faktoren für die Berechnung der Kollektorleistung
    Eta0b_neu_K_beam_GbT = Eta0b_neu * K_beam_L * GbT_L
    Eta0b_neu_Kthetadiff_GdT_H_Dk = Eta0b_neu * Kthetadiff * GdT_H_Dk_L

    # Berechnung der Kollektorleistung (Pkoll_a)
    Pkoll_a = np.maximum(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1 - c2 - c3) * Bezugsfläche / 1000)

    # Berechnung der Kollektortemperatur (T_koll_a)
    Tgkoll_a = RLT_array
    T_koll_a = Temperatur_L - (Temperatur_L - Tgkoll_a) * np.exp(-Koll_c1 / KollCeff_A * 3.6) + (Pkoll_a * 3600) / (KollCeff_A * Bezugsfläche)

    return Pkoll_a, T_koll_a

def Berechnung_STA(Bruttofläche_STA, Typ, TRY, time_steps, RLT_L, calc1, calc2, Longitude=-14.4222, STD_Longitude=-15, Latitude=51.1676,
                   East_West_collector_azimuth_angle=0, Collector_tilt_angle=36, Vorwärmung_K=8, DT_WT_Solar_K=5, DT_WT_Netz_K=5):
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

    if Bruttofläche_STA == 0:
        return np.zeros_like(RLT_L), np.zeros_like(RLT_L)
    
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

    _, K_beam_L, GbT_L, GdT_H_Dk_L = calculate_solar_radiation(Globalstrahlung_L, Direktstrahlung_L, 
                                                                     Tag_des_Jahres_L, time_steps, Longitude,
                                                                     STD_Longitude, Latitude, Albedo, East_West_collector_azimuth_angle,
                                                                     Collector_tilt_angle, IAM_W, IAM_N)

    Kollektorfeldertrag_L = np.full_like(RLT_L, 0)
    VLT_Solar_L = np.full_like(RLT_L, 0)

    Zähler = 0

    for K_beam, GbT, GdT_H_Dk, Temperatur, Windgeschwindigkeit, RLT in zip(K_beam_L, GbT_L, GdT_H_Dk_L, Temperatur_L, Windgeschwindigkeit_L, RLT_L):
        Eta0b_neu_K_beam_GbT = Eta0b_neu * K_beam * GbT
        Eta0b_neu_Kthetadiff_GdT_H_Dk = Eta0b_neu * Kthetadiff * GdT_H_Dk

        if Zähler < 1:
            Zieltemperatur_Solaranlage = RLT + Vorwärmung_K + DT_WT_Solar_K + DT_WT_Netz_K
            Tm_a = (Zieltemperatur_Solaranlage + RLT) / 2
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

            # Calculate solar target temperature and return line temperature
            Zieltemperatur_Solaranlage = RLT + Vorwärmung_K + DT_WT_Solar_K + DT_WT_Netz_K
            TRL_Solar = RLT + DT_WT_Solar_K

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

                Kollektorfeldertrag = value2
            else:
                Kollektorfeldertrag = 0

            # Rohrleitungsverluste aufsummiert
            if (Kollektorfeldertrag == 0 and Kollektorfeldertrag_alt == 0) or Kollektorfeldertrag <= Summe_PRV_alt:
                Summe_PRV = PRV + Summe_PRV_alt - Kollektorfeldertrag
            else:
                Summe_PRV = PRV

            # Kollektorfeldertrag aufsummiert
            Kollektorfeldertrag_L[Zähler] = Kollektorfeldertrag
            VLT_Solar_L[Zähler] = T_koll

        Zähler += 1

    return Kollektorfeldertrag_L, VLT_Solar_L

def test_solar_thermal():
    # Testdaten
    Bruttofläche_STA = 10
    Typ = "Vakuumröhrenkollektor"
    TRY = import_TRY("currently_not_used/STES/TRY2015_511676144222_Jahr.dat")
    time_steps = np.arange(np.datetime64('2023-01-01T00:00'), np.datetime64('2024-01-01T00:00'), np.timedelta64(1, 'h'))
    RLT_array = np.full(8760, 10)
    calc1 = 0
    calc2 = 8760

    # Test
    #Kollektorfeldertrag_L, VLT_Solar_L = calculate_solar_thermal(Bruttofläche_STA, Typ, TRY, time_steps, RLT_array, calc1, calc2)
    Kollektorfeldertrag_L, VLT_Solar_L = Berechnung_STA(Bruttofläche_STA, Typ, TRY, time_steps, RLT_array, calc1, calc2)

    # Plot
    plt.figure()
    plt.plot(time_steps, Kollektorfeldertrag_L)
    plt.xlabel('Zeit')
    plt.ylabel('Kollektorfeldertrag [kWh]')
    plt.legend(['Kollektorfeldertrag'])

    plt.figure()
    plt.plot(time_steps, VLT_Solar_L)
    plt.xlabel('Zeit')
    plt.ylabel('Kollektortemperatur [°C]')
    plt.legend(['Kollektortemperatur'])

    plt.show()

test_solar_thermal()
