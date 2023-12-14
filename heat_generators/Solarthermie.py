# Ertragsberechnungsprogramm Solarthermie in Wärmenetz von Dipl.-Ing. (FH) Jonas Pfeiffer (Berechnungsgrundlage: ScenoCalc Fernwärme 2.0)
# https://www.scfw.de/)

# Import Bibliotheken
from math import pi, exp, log, sqrt
import csv
import numpy as np
import pandas as pd
from datetime import datetime

from heat_generators.Wirtschaftlichkeitsbetrachtung import WGK_STA
from heat_generators.Solarstrahlung import Berechnung_Solarstrahlung

def Berechnung_STA(Bruttofläche_STA, VS, Typ, Last_L, VLT_L, RLT_L, TRY, time_steps, calc1, calc2, duration, Tsmax=90, Longitude=-14.4222, STD_Longitude=-15, Latitude=51.1676):
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
        return 0, np.zeros_like(Last_L)

    Tag_des_Jahres_L = np.array([datetime.utcfromtimestamp(t.astype(int) * 60 * 15).timetuple().tm_yday for t in time_steps])

    Albedo = 0.2
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
    Tm_rl = 53.4
    QSmax = 1.16 * VS * (Tsmax - Tm_rl)
    Qsa = 0  # Speicherinhalt zu Beginn

    # Vorgabewerte Wärmenetz
    # Vorwärmbetrieb = 1
    Vorwärmung = 8  # K
    DT_WT_Solar = 5
    DT_WT_Netz = 5

    East_West_collector_azimuth_angle = 0
    Collector_tilt_angle = 36

    GT_H_Gk, K_beam_L, GbT_L, GdT_H_Dk_L = Berechnung_Solarstrahlung(Globalstrahlung_L, Direktstrahlung_L, 
                                                                     Tag_des_Jahres_L, time_steps, Longitude,
                                                                     STD_Longitude, Latitude, Albedo, IAM_W, IAM_N,
                                                                     East_West_collector_azimuth_angle,
                                                                     Collector_tilt_angle)

    Speicher_Wärmeoutput_L = []
    Speicherladung_L = []
    Gesamtwärmemenge = 0

    Zähler = 0

    for Tag_des_Jahres, K_beam, GbT, GdT_H_Dk, Temperatur, Windgeschwindigkeit, Last, VLT, RLT in zip(Tag_des_Jahres_L, K_beam_L, GbT_L, GdT_H_Dk_L, Temperatur_L, Windgeschwindigkeit_L, Last_L, VLT_L, RLT_L):
        Eta0b_neu_K_beam_GbT = Eta0b_neu * K_beam * GbT
        Eta0b_neu_Kthetadiff_GdT_H_Dk = Eta0b_neu * Kthetadiff * GdT_H_Dk

        if Zähler < 1:
            TS_unten = RLT
            Zieltemperatur_Solaranlage = TS_unten + Vorwärmung + DT_WT_Solar + DT_WT_Netz
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
                TS_unten = RLT + DT_WT_Netz + (2/3 * (VLT - RLT) / 0.2 * QS/QSmax) + (1 / 3 * (VLT - RLT)) - (2/3 * (VLT - RLT) / 0.2 * QS/QSmax)
            else:
                TS_unten = RLT + DT_WT_Netz + (1 / 3 * (VLT - RLT) / 0.8) * QS/QSmax

            # Calculate solar target temperature and return line temperature
            Zieltemperatur_Solaranlage = TS_unten + Vorwärmung + DT_WT_Solar + DT_WT_Netz
            TRL_Solar = TS_unten + DT_WT_Solar

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
            value2 = Zieltemperatur_Solaranlage - DT_WT_Solar
            if QS <= 0:
                ergebnis1 = value2
            else:
                value3 = (value2 - Tm_rl) / (Tsmax - Tm_rl)
                if value1 < value3:
                    ergebnis1 = VLT + DT_WT_Netz
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

        Speicherladung_L.append(QS)
        Speicher_Wärmeoutput_L.append(PSout)
        Gesamtwärmemenge += (PSout / 1000) * duration

        Zähler += 1

    return Gesamtwärmemenge, np.array(Speicher_Wärmeoutput_L).astype("float64")


def Optimierung_WGK_STA(typ, solar_data, BEW="Nein", speicher=range(5, 60, 5), fläche=range(100, 1000, 100)):
    results = [(WGK_STA(f, v, typ, Berechnung_STA(f, v, typ, solar_data)[0], 1.05, 1.03, 20, BEW), f, v) for v in speicher for f in fläche]
    min_WGK, optimum_Bruttofläche, optimum_VS = min(results)
    print(typ)
    print("Die minimalen Wärmegestehungskosten der Solarthermieanlage betragen: " + str(round(min_WGK, 2)) + " €/MWh")
    print("Die Speichergröße beträgt: " + str(optimum_VS) + " m^3")
    print("Die Bruttokollektorfläche beträgt: " + str(optimum_Bruttofläche) + " m^2")
