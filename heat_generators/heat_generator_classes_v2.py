import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.interpolate import RegularGridInterpolator
import matplotlib.pyplot as plt
from math import pi, sqrt

from heat_generators.Solarthermie import Berechnung_STA

# Wirtschaftlichkeitsberechnung für technische Anlagen nach VDI 2067
def annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand=0, q=1.05, r=1.03, T=20, Energiebedarf=0, Energiekosten=0, E1=0):
    if T > TN:
        n = T // TN
    else:
        n = 0

    a = (q - 1) / (1 - (q ** (-T)))  # Annuitätsfaktor
    b = (1 - (r / q) ** T) / (q - r)  # preisdynamischer Barwertfaktor
    b_v = b_B = b_IN = b_s = b_E = b

    # kapitalgebundene Kosten
    AN = A0
    AN_L = [A0]
    for i in range(1, n+1):
        Ai = A0*((r**(n*TN))/(q**(n*TN)))
        AN += Ai
        AN_L.append(Ai)

    R_W = A0 * (r**(n*TN)) * (((n+1)*TN-T)/TN) * 1/(q**T)
    A_N_K = (AN - R_W) * a

    # bedarfsgebundene Kosten
    A_V1 = Energiebedarf * Energiekosten
    A_N_V = A_V1 * a * b_v

    # betriebsgebundene Kosten#
    stundensatz = 100  # €
    A_B1 = Bedienaufwand * stundensatz
    A_IN = A0 * (f_Inst + f_W_Insp)/100
    A_N_B = A_B1 * a * b_B + A_IN * a * b_IN

    # sonstige Kosten
    A_S1 = 0
    A_N_S = A_S1 * a * b_s

    A_N = - (A_N_K + A_N_V + A_N_B + A_N_S)  # Annuität

    # Erlöse
    A_NE = E1*a*b_E

    A_N += A_NE

    return -A_N

class HeatPump:
    def __init__(self, name, spezifische_Investitionskosten_WP=1000):
        self.name = name
        self.spezifische_Investitionskosten_WP = spezifische_Investitionskosten_WP

    def COP_WP(self, VLT_L, QT, COP_data):
        # Interpolationsformel für den COP
        values = COP_data  # np.genfromtxt('Kennlinien WP.csv', delimiter=';')
        row_header = values[0, 1:]  # Vorlauftemperaturen
        col_header = values[1:, 0]  # Quelltemperaturen
        values = values[1:, 1:]
        f = RegularGridInterpolator((col_header, row_header), values, method='linear')

        # technische Grenze der Wärmepumpe ist Temperaturhub von 75 °C
        VLT_L = np.minimum(VLT_L, 75+QT)

        # Überprüfen, ob QT eine Zahl oder ein Array ist
        if np.isscalar(QT):
            # Wenn QT eine Zahl ist, erstellen wir ein Array mit dieser Zahl
            QT_array = np.full_like(VLT_L, QT)
        else:
            # Wenn QT bereits ein Array ist, prüfen wir, ob es die gleiche Länge wie VLT_L hat
            if len(QT) != len(VLT_L):
                raise ValueError("QT muss entweder eine einzelne Zahl oder ein Array mit der gleichen Länge wie VLT_L sein.")
            QT_array = QT

        # Berechnung von COP_L
        COP_L = f(np.column_stack((QT_array, VLT_L)))

        return COP_L, VLT_L
    
    def WGK(self, Wärmeleistung, Wärmemenge, Strombedarf, spez_Investitionskosten_WQ, Strompreis, q, r, T, BEW):
        if Wärmemenge == 0:
            return 0
        # Kosten Wärmepumpe: Viessmann Vitocal 350 HT-Pro: 140.000 €, 350 kW Nennleistung; 120 kW bei 10/85
        # Annahme Kosten Wärmepumpe: 1000 €/kW; Vereinfachung
        spezifische_Investitionskosten_WP = self.spezifische_Investitionskosten_WP
        Nutzungsdauer_WP = 20
        f_Inst_WP, f_W_Insp_WP, Bedienaufwand_WP = 1, 1.5, 0
        f_Inst_WQ, f_W_Insp_WQ, Bedienaufwand_WQ = 0.5, 0.5, 0

        Investitionskosten_WP = spezifische_Investitionskosten_WP * round(Wärmeleistung, 0)

        E1_WP = annuität(Investitionskosten_WP, Nutzungsdauer_WP, f_Inst_WP, f_W_Insp_WP, Bedienaufwand_WP, q, r, T,
                            Strombedarf, Strompreis)
        WGK_WP_a = E1_WP/Wärmemenge

        Nutzungsdauer_WQ_dict = {"Abwärme": 20, "Abwasserwärme": 20, "Flusswasser": 20, "Geothermie": 30}

        Investitionskosten_WQ = spez_Investitionskosten_WQ * Wärmeleistung

        E1_WQ = annuität(Investitionskosten_WQ, Nutzungsdauer_WQ_dict[self.name], f_Inst_WQ, f_W_Insp_WQ,
                            Bedienaufwand_WQ, q, r, T)
        WGK_WQ_a = E1_WQ / Wärmemenge

        WGK_Gesamt_a = WGK_WP_a + WGK_WQ_a

        return WGK_Gesamt_a

class RiverHeatPump(HeatPump):
    def __init__(self, name, Wärmeleistung_FW_WP, Temperatur_FW_WP, dT=0, spez_Investitionskosten_Flusswasser=1000, spezifische_Investitionskosten_WP=1000):
        super().__init__(name, spezifische_Investitionskosten_WP=spezifische_Investitionskosten_WP)
        self.Wärmeleistung_FW_WP = Wärmeleistung_FW_WP
        self.Temperatur_FW_WP = Temperatur_FW_WP
        self.dT = dT
        self.spez_Investitionskosten_Flusswasser = spez_Investitionskosten_Flusswasser

    def Berechnung_WP(self, VLT_L, COP_data):
        COP_L, VLT_L_WP = self.COP_WP(VLT_L, self.Temperatur_FW_WP, COP_data)
        Kühlleistung_L = self.Wärmeleistung_FW_WP * (1 - (1 / COP_L))
        el_Leistung_L = self.Wärmeleistung_FW_WP - Kühlleistung_L
        return Kühlleistung_L, el_Leistung_L, VLT_L_WP

    # Änderung Kühlleistung und Temperatur zu Numpy-Array in aw sowie vor- und nachgelagerten Funktionen
    def abwärme(self, Last_L, VLT_L, COP_data, duration):
        if self.Wärmeleistung_FW_WP == 0:
            return 0, 0, np.zeros_like(Last_L), np.zeros_like(VLT_L), 0, np.zeros_like(VLT_L)

        Wärmeleistung_L = np.where(Last_L >= self.Wärmeleistung_FW_WP, self.Wärmeleistung_FW_WP, Last_L)

        Kühlleistung_L, el_Leistung_L, VLT_L_WP = self.Berechnung_WP(VLT_L, COP_data)

        # Wärmepumpe soll nur in Betrieb sein, wenn Sie die Vorlauftemperatur erreichen kann
        Wärmeleistung_L = np.where(VLT_L_WP < VLT_L-self.dT, 0, Wärmeleistung_L)
        Kühlleistung_L = np.where(VLT_L_WP < VLT_L-self.dT, 0, Kühlleistung_L)
        el_Leistung_L = np.where(VLT_L_WP < VLT_L-self.dT, 0, el_Leistung_L)
        
        Wärmemenge = np.sum(Wärmeleistung_L / 1000)*duration
        Kühlmenge = np.sum(Kühlleistung_L / 1000)*duration
        Strombedarf = np.sum(el_Leistung_L / 1000)*duration

        return Wärmemenge, Strombedarf, Wärmeleistung_L, el_Leistung_L, Kühlmenge, Kühlleistung_L
    
    def calculate(self,VLT_L, COP_data, Strompreis, q, r, T, BEW, duration, general_results):
        
        Wärmemenge, Strombedarf_FW_WP, Wärmeleistung_L, el_Leistung_L, Kühlmenge, Kühlleistung_L = self.abwärme(general_results["Restlast_L"], VLT_L, COP_data, duration)

        WGK_Abwärme = self.WGK(self.Wärmeleistung_FW_WP, Wärmemenge, Strombedarf_FW_WP, self.spez_Investitionskosten_Flusswasser, Strompreis, q, r, T, BEW)

        results = {
            'Wärmemenge': Wärmemenge,
            'Wärmeleistung_L': Wärmeleistung_L,
            'Strombedarf': Strombedarf_FW_WP,
            'el_Leistung_L': el_Leistung_L,
            'WGK': WGK_Abwärme,
            'color': "purple"
        }

        return results
    
class WasteHeatPump(HeatPump):
    def __init__(self, name, Kühlleistung_Abwärme, Temperatur_Abwärme, spez_Investitionskosten_Abwärme=500, spezifische_Investitionskosten_WP=1000):
        super().__init__(name, spezifische_Investitionskosten_WP=spezifische_Investitionskosten_WP)
        self.Kühlleistung_Abwärme = Kühlleistung_Abwärme
        self.Temperatur_Abwärme = Temperatur_Abwärme
        self.spez_Investitionskosten_Abwärme = spez_Investitionskosten_Abwärme

    def Berechnung_WP(self, Kühlleistung, QT, VLT_L, COP_data):
        COP_L, VLT_L = self.COP_WP(VLT_L, QT, COP_data)
        Wärmeleistung_L = Kühlleistung / (1 - (1 / COP_L))
        el_Leistung_L = Wärmeleistung_L - Kühlleistung
        return Wärmeleistung_L, el_Leistung_L

    # Änderung Kühlleistung und Temperatur zu Numpy-Array in aw sowie vor- und nachgelagerten Funktionen
    def abwärme(self, Last_L, VLT_L, Kühlleistung, Temperatur, COP_data, duration):
        if Kühlleistung == 0:
            return 0, 0, np.zeros_like(Last_L), np.zeros_like(VLT_L)

        Wärmeleistung_L, el_Leistung_L = self.Berechnung_WP(Kühlleistung, Temperatur, VLT_L, COP_data)

        Wärmeleistung_L = np.where(Last_L >= Wärmeleistung_L, Wärmeleistung_L, Last_L)
        el_Leistung_L = np.where(Last_L >= Wärmeleistung_L, el_Leistung_L, el_Leistung_L * (Last_L / Wärmeleistung_L))

        Wärmemenge = np.sum(Wärmeleistung_L / 1000)*duration
        Strombedarf = np.sum(el_Leistung_L / 1000)*duration

        self.max_Wärmeleistung = np.max(Wärmeleistung_L)

        return Wärmemenge, Strombedarf, Wärmeleistung_L, el_Leistung_L
    
    def calculate(self, VLT_L, COP_data, Strompreis, q, r, T, BEW, duration, general_results):
        
        Wärmemenge, Strombedarf_Abwärme, Wärmeleistung_L, el_Leistung_L= self.abwärme(general_results['Restlast_L'], VLT_L, self.Kühlleistung_Abwärme, self.Temperatur_Abwärme, COP_data, duration)

        WGK_Abwärme = self.WGK(self.max_Wärmeleistung, Wärmemenge, Strombedarf_Abwärme, self.spez_Investitionskosten_Abwärme, Strompreis, q, r, T, BEW)

        results = {
            'Wärmemenge': Wärmemenge,
            'Wärmeleistung_L': Wärmeleistung_L,
            'Strombedarf': Strombedarf_Abwärme,
            'el_Leistung_L': el_Leistung_L,
            'WGK': WGK_Abwärme,
            'color': "grey"
        }

        return results

class Geothermal(HeatPump):
    def __init__(self, name, Fläche, Bohrtiefe, Temperatur_Geothermie, spez_Bohrkosten=120, spez_Entzugsleistung=50,
                 Vollbenutzungsstunden=2400, Abstand_Sonden=10, spezifische_Investitionskosten_WP=1000):
        super().__init__(name, spezifische_Investitionskosten_WP=spezifische_Investitionskosten_WP)
        self.Fläche = Fläche
        self.Bohrtiefe = Bohrtiefe
        self.Temperatur_Geothermie = Temperatur_Geothermie
        self.spez_Bohrkosten = spez_Bohrkosten
        self.spez_Entzugsleistung = spez_Entzugsleistung
        self.Vollbenutzungsstunden = Vollbenutzungsstunden
        self.Abstand_Sonden = Abstand_Sonden

    def Geothermie(self, Last_L, VLT_L, Quelltemperatur, COP_data, duration):
        if self.Fläche == 0 or self.Bohrtiefe == 0:
            return 0, 0, np.zeros_like(Last_L), np.zeros_like(VLT_L)

        Anzahl_Sonden = (round(sqrt(self.Fläche)/self.Abstand_Sonden)+1)**2

        Entzugsleistung_2400 = self.Bohrtiefe * self.spez_Entzugsleistung * Anzahl_Sonden / 1000
        # kW bei 2400 h, 22 Sonden, 50 W/m: 220 kW
        Entzugswärmemenge = Entzugsleistung_2400 * self.Vollbenutzungsstunden / 1000  # MWh
        self.Investitionskosten_Sonden = self.Bohrtiefe * self.spez_Bohrkosten * Anzahl_Sonden

        COP_L, VLT_WP = self.COP_WP(VLT_L, Quelltemperatur, COP_data)

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
            Wärmeleistung_tat_L = Wärmeleistung_L * np.minimum(1, Last_L / Wärmeleistung_L)
            el_Leistung_tat_L = el_Leistung_L * np.minimum(1, Last_L / Wärmeleistung_L)
            Entzugsleistung_tat_L = Wärmeleistung_tat_L - el_Leistung_tat_L
            Entzugswärme = np.sum(Entzugsleistung_tat_L) / 1000
            Wärmemenge = np.sum(Wärmeleistung_tat_L) / 1000
            Strombedarf = np.sum(el_Leistung_tat_L) / 1000
            Betriebsstunden = np.count_nonzero(Wärmeleistung_tat_L)

            # Falls es keine Nutzung gibt, wird das Ergebnis 0
            if Betriebsstunden == 0:
                Wärmeleistung_tat_L = np.array([0])
                el_Leistung_tat_L = np.array([0])

            if Entzugswärme > Entzugswärmemenge:
                B_min = B
            else:
                B_max = B

        self.max_Wärmeleistung = max(Wärmeleistung_tat_L)
        JAZ = Wärmemenge / Strombedarf
        Wärmemenge, Strombedarf = Wärmemenge*duration, Strombedarf*duration
        
        return Wärmemenge, Strombedarf, Wärmeleistung_tat_L, el_Leistung_tat_L
    
    def calculate(self, VLT_L, COP_data, Strompreis, q, r, T, BEW, duration, general_results):
        # Hier fügen Sie die spezifische Logik für die Geothermie-Berechnung ein
        print(self.Geothermie(general_results['Restlast_L'], VLT_L, self.Temperatur_Geothermie, COP_data, duration))
        Wärmemenge, Strombedarf, Wärmeleistung_L, el_Leistung_Geothermie_L = self.Geothermie(general_results['Restlast_L'], VLT_L, self.Temperatur_Geothermie, COP_data, duration)

        self.spez_Investitionskosten_Erdsonden = self.Investitionskosten_Sonden / self.max_Wärmeleistung
        WGK_Geothermie = self.WGK(self.max_Wärmeleistung, Wärmemenge, Strombedarf, self.spez_Investitionskosten_Erdsonden, Strompreis, q, r, T, BEW)

        results = {
            'Wärmemenge': Wärmemenge,
            'Wärmeleistung_L': Wärmeleistung_L,
            'Strombedarf': Strombedarf,
            'el_Leistung_L': el_Leistung_Geothermie_L,
            'WGK': WGK_Geothermie,
            'color': "blue"
        }

        return results

class CHP:
    def __init__(self, name, th_Leistung_BHKW, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850):
        self.name = name
        self.th_Leistung_BHKW = th_Leistung_BHKW
        self.spez_Investitionskosten_GBHKW = spez_Investitionskosten_GBHKW
        self.spez_Investitionskosten_HBHKW = spez_Investitionskosten_HBHKW

    def WGK(self, Wärmemenge, Strommenge, Brennstoffbedarf, Brennstoffkosten, Strompreis, q, r, T, BEW):
        if Wärmemenge == 0:
            return 0
        # Holzvergaser-BHKW: 130 kW: 240.000 -> 1850 €/kW
        # (Erd-)Gas-BHKW: 100 kW: 150.000 € -> 1500 €/kW
        if self.name == "BHKW":
            spez_Investitionskosten = self.spez_Investitionskosten_GBHKW  # €/kW
        elif self.name == "Holzgas-BHKW":
            spez_Investitionskosten = self.spez_Investitionskosten_HBHKW  # €/kW

        self.Investitionskosten = spez_Investitionskosten * self.th_Leistung_BHKW
        Nutzungsdauer = 15
        f_Inst, f_W_Insp, Bedienaufwand = 6, 2, 0

        Stromeinnahmen = Strommenge * Strompreis

        A_N = annuität(self.Investitionskosten, Nutzungsdauer, f_Inst, f_W_Insp, Bedienaufwand, q, r, T,
                            Brennstoffbedarf, Brennstoffkosten, Stromeinnahmen)
        WGK_a = A_N / Wärmemenge

        return WGK_a

    def BHKW(self, Last_L, duration, el_Wirkungsgrad=0.33, KWK_Wirkungsgrad=0.9):
        # Berechnen der thermischen Effizienz
        thermischer_Wirkungsgrad = KWK_Wirkungsgrad - el_Wirkungsgrad

        # Berechnen der Wärmeleistung des BHKW
        self.el_Leistung_Soll = self.th_Leistung_BHKW / thermischer_Wirkungsgrad * el_Wirkungsgrad

        # Berechnen der Strom- und Wärmemenge des BHKW
        if self.th_Leistung_BHKW > 0:
            Wärmeleistung_BHKW_L = np.where(Last_L >= self.th_Leistung_BHKW, self.th_Leistung_BHKW, Last_L)
            el_Leistung_BHKW_L = np.where(Last_L >= self.th_Leistung_BHKW, self.el_Leistung_Soll,
                                        self.el_Leistung_Soll * (Last_L / self.th_Leistung_BHKW))
        else:
            Wärmeleistung_BHKW_L, el_Leistung_BHKW_L = np.zeros_like(Last_L), np.zeros_like(Last_L)

        Wärmemenge_BHKW = np.sum(Wärmeleistung_BHKW_L / 1000)*duration
        Strommenge_BHKW = np.sum(el_Leistung_BHKW_L / 1000)*duration

        # Berechnen des Brennstoffbedarfs
        Brennstoffbedarf_BHKW = (Wärmemenge_BHKW + Strommenge_BHKW) / KWK_Wirkungsgrad

        # Rückgabe der berechneten Werte
        return Wärmeleistung_BHKW_L, el_Leistung_BHKW_L, Wärmemenge_BHKW, Strommenge_BHKW, \
            Brennstoffbedarf_BHKW

    def calculate(self, Gaspreis, Holzpreis, Strompreis, q, r, T, BEW, duration, general_results):
        
        Wärmeleistung_BHKW_L, el_Leistung_BHKW_L, Wärmemenge, Strommenge_BHKW, Brennstoffbedarf_BHKW = self.BHKW(general_results["Restlast_L"], duration)
        
        if self.name == "BHKW":
            Brennstoffpreis = Gaspreis
        elif self.name == "Holzgas-BHKW":
            Brennstoffpreis = Holzpreis

        wgk_BHKW = self.WGK(Wärmemenge, Strommenge_BHKW, Brennstoffbedarf_BHKW, Brennstoffpreis, Strompreis, q, r, T, BEW)

        results = {
            'Wärmemenge': Wärmemenge,
            'Wärmeleistung_L': Wärmeleistung_BHKW_L,
            'Brennstoffbedarf': Brennstoffbedarf_BHKW,
            'WGK': wgk_BHKW,
            'Strommenge': Strommenge_BHKW,
            'el_Leistung_L': el_Leistung_BHKW_L,
            'color': "orange"
        }


        return results

class BiomassBoiler:
    def __init__(self, name, P_BMK, Größe_Holzlager=40, spez_Investitionskosten=200, spez_Investitionskosten_Holzlager=400):
        self.name = name
        self.P_BMK = P_BMK
        self.Größe_Holzlager = Größe_Holzlager
        self.spez_Investitionskosten = spez_Investitionskosten
        self.spez_Investitionskosten_Holzlager = spez_Investitionskosten_Holzlager

    def Biomassekessel(self, Last_L, P_BMK, duration):
        Wärmeleistung_BMK_L = np.where(Last_L >= P_BMK, P_BMK, Last_L)
        Wärmemenge_BMK = np.sum(Wärmeleistung_BMK_L / 1000)*duration

        return Wärmeleistung_BMK_L, Wärmemenge_BMK

    def WGK(self, Wärmemenge, Brennstoffbedarf, Brennstoffkosten, q, r, T, BEW):
        if Wärmemenge == 0:
            return 0
        
        Nutzungsdauer = 15
        self.Investitionskosten_Kessel = self.spez_Investitionskosten * self.P_BMK
        self.Investitionskosten_Holzlager = self.spez_Investitionskosten_Holzlager * self.Größe_Holzlager
        self.Investitionskosten =  self.Investitionskosten_Kessel + self.Investitionskosten_Holzlager
        f_Inst, f_W_Insp, Bedienaufwand = 3, 3, 0

        self.A_N = annuität(self.Investitionskosten, Nutzungsdauer, f_Inst, f_W_Insp, Bedienaufwand, q, r, T, Brennstoffbedarf,
                            Brennstoffkosten)
        WGK_a = self.A_N / Wärmemenge

        return WGK_a

    def calculate(self, Holzpreis, q, r, T, BEW, duration, general_results):
        # Hier fügen Sie die spezifische Logik für die Biomassekessel-Berechnung ein
        Wärmeleistung_BMK_L, Wärmemenge = self.Biomassekessel(general_results["Restlast_L"], self.P_BMK, duration)

        Nutzungsgrad_BMK = 0.8
        Brennstoffbedarf_BMK = Wärmemenge/Nutzungsgrad_BMK
        WGK_BMK = self.WGK(Wärmemenge, Brennstoffbedarf_BMK, Holzpreis, q, r, T, BEW)
        
        results = {
            'Wärmemenge': Wärmemenge,
            'Wärmeleistung_L': Wärmeleistung_BMK_L,
            'Brennstoffbedarf': Brennstoffbedarf_BMK,
            'WGK': WGK_BMK,
            'color': "green"
        }

        return results
    
class GasBoiler:
    def __init__(self, name, spez_Investitionskosten=30):
        self.name = name
        self.spez_Investitionskosten = spez_Investitionskosten

    def Gaskessel(self, Last_L, duration, Nutzungsgrad=0.9):
        Erzeugung_L = np.maximum(Last_L, 0)
        Wärmemenge = np.sum(Erzeugung_L/1000)*duration
        Brennstoffbedarf = Wärmemenge / Nutzungsgrad

        return Wärmemenge, Erzeugung_L, Brennstoffbedarf

    def WGK(self, P_max, Wärmemenge, Brennstoffbedarf, Brennstoffkosten, q, r, T, BEW):
        if Wärmemenge == 0:
            return 0
        
        self.Investitionskosten = self.spez_Investitionskosten * P_max
        Nutzungsdauer = 20
        f_Inst, f_W_Insp, Bedienaufwand = 1, 2, 0

        A_N = annuität(self.Investitionskosten, Nutzungsdauer, f_Inst, f_W_Insp, Bedienaufwand, q, r, T,
                            Brennstoffbedarf, Brennstoffkosten)
        WGK_a = A_N / Wärmemenge

        return WGK_a

    def calculate(self, Gaspreis, q, r, T, BEW, duration, Last_L, general_results):
        # Hier fügen Sie die spezifische Logik für die Gaskessel-Berechnung ein
        Wärmemenge, Wärmeleistung_GK_L, Gasbedarf = self.Gaskessel(general_results['Restlast_L'], duration)
        self.P_max = max(Last_L) * 1
        WGK_GK = self.WGK(self.P_max, Wärmemenge, Gasbedarf, Gaspreis, q, r, T, BEW)

        results = {
            'Wärmemenge': Wärmemenge,
            'Wärmeleistung_L': Wärmeleistung_GK_L,
            'Brennstoffbedarf': Gasbedarf,
            'WGK': WGK_GK,
            "color": "brown"
        }

        return results

class SolarThermal:
    def __init__(self, name, bruttofläche_STA, vs, Typ, kosten_speicher_spez=750, kosten_fk_spez=430, kosten_vrk_spez=590):
        self.name = name
        self.bruttofläche_STA = bruttofläche_STA
        self.vs = vs
        self.Typ = Typ
        self.kosten_speicher_spez = kosten_speicher_spez
        self.kosten_fk_spez = kosten_fk_spez
        self.kosten_vrk_spez = kosten_vrk_spez
    
    def calc_WGK(self, Wärmemenge, q=1.05, r=1.03, T=20, BEW="Nein"):
        if Wärmemenge == 0:
            return 0

        kosten_pro_typ = {
            # Viessmann Flachkollektor Vitosol 200-FM, 2,56 m²: 697,9 € (brutto); 586,5 € (netto) -> 229 €/m²
            # + 200 €/m² Installation/Zubehör
            "Flachkollektor": self.kosten_fk_spez,
            # Ritter Vakuumröhrenkollektor CPC XL1921 (4,99m²): 2299 € (brutto); 1932 € (Netto) -> 387 €/m²
            # + 200 €/m² Installation/Zubehör
            "Vakuumröhrenkollektor": self.kosten_vrk_spez
        }

        self.Kosten_STA_spez = kosten_pro_typ[self.Typ]  # €/m^2
        Nutzungsdauer = 20
        f_Inst, f_W_Insp, Bedienaufwand = 0.5, 1, 0

        self.Investitionskosten_Speicher = self.vs * self.kosten_speicher_spez
        self.Investitionskosten_STA = self.bruttofläche_STA * self.Kosten_STA_spez
        self.Investitionskosten = self.Investitionskosten_Speicher + self.Investitionskosten_STA

        self.A_N = annuität(self.Investitionskosten, Nutzungsdauer, f_Inst, f_W_Insp, Bedienaufwand, q, r, T)
        self.WGK = self.A_N / Wärmemenge

        Anteil_Förderung_BEW = 0.4
        Eigenanteil = 1 - Anteil_Förderung_BEW
        Investitionskosten_Gesamt_BEW = self.Investitionskosten * Eigenanteil
        Annuität_BEW = annuität(Investitionskosten_Gesamt_BEW, Nutzungsdauer, f_Inst, f_W_Insp, Bedienaufwand, q, r, T)
        self.WGK_BEW = Annuität_BEW / Wärmemenge

        self.WGK_BEW_BKF = self.WGK_BEW - 10  # €/MWh 10 Jahre

        if BEW == "Nein":
            return self.WGK
        elif BEW == "Ja":
            return self.WGK_BEW_BKF
        
        #tech_results = tech.calculate(VLT_L, RLT_L, TRY, time_steps, calc1, calc2, q, r, T, BEW, duration, general_results)
    def calculate(self, VLT_L, RLT_L, TRY, time_steps, calc1, calc2, q, r, T, BEW, duration, general_results):
        # Hier fügen Sie die spezifische Logik für die Solarthermie-Berechnung ein
        Wärmemenge, Wärmeleistung_Solarthermie_L = Berechnung_STA(self.bruttofläche_STA, self.vs, self.Typ, general_results['Restlast_L'], VLT_L, RLT_L, TRY, time_steps, calc1, calc2, duration)

        WGK_Solarthermie = self.calc_WGK(Wärmemenge, q, r, T, BEW)

        results = {
            'Wärmemenge': Wärmemenge,
            'Wärmeleistung_L': Wärmeleistung_Solarthermie_L,
            'WGK': WGK_Solarthermie,
            'color': "red"
        }

        return results


def calculate_factors(Kapitalzins, Preissteigerungsrate, Betrachtungszeitraum):
    q = 1 + Kapitalzins / 100
    r = 1 + Preissteigerungsrate / 100
    T = Betrachtungszeitraum
    return q, r, T

def Berechnung_Erzeugermix(tech_order, initial_data, calc1, calc2, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, variables=[], variables_order=[], kapitalzins=5, preissteigerungsrate=3, betrachtungszeitraum=20):
    # Kapitalzins und Preissteigerungsrate in % -> Umrechung in Zinsfaktor und Preissteigerungsfaktor
    q, r, T = calculate_factors(kapitalzins, preissteigerungsrate, betrachtungszeitraum)
    time_steps, Last_L, VLT_L, RLT_L = initial_data

    duration = np.diff(time_steps[0:2]) / np.timedelta64(1, 'h')
    duration = duration[0]

    general_results = {
        'time_steps': time_steps,
        'Last_L': Last_L,
        'VLT_L': VLT_L,
        'RLT_L': RLT_L,
        'Jahreswärmebedarf': (np.sum(Last_L)/1000) * duration,
        'WGK_Gesamt': 0,
        'Restwärmebedarf': (np.sum(Last_L)/1000) * duration,
        'Restlast_L': Last_L.copy(),
        'Wärmeleistung_L': [],
        'colors': [],
        'Wärmemengen': [],
        'Anteile': [],
        'WGK': [],
        'Strombedarf': 0,
        'Strommenge': 0,
        'el_Leistungsbedarf_L': np.zeros_like(Last_L),
        'el_Leistung_L': np.zeros_like(Last_L),
        'el_Leistung_ges_L': np.zeros_like(Last_L),
        'specific_emissions': 1,
        'techs': []
    }

    # zunächst Berechnung der Erzeugung
    for tech in tech_order.copy():
        if len(variables) > 0:
            if tech.name == "Solarthermie":
                tech.bruttofläche_STA, tech.vs = variables[variables_order.index("bruttofläche_STA")], variables[variables_order.index("vs")]
            elif tech.name == "Abwärme" or tech == "Abwasserwärme":
                tech.Kühlleistung_Abwärme = variables[variables_order.index("Kühlleistung_Abwärme")]
            elif tech.name == "Flusswasser":
                tech.Wärmeleistung_FW_WP = variables[variables_order.index("Wärmeleistung_FW_WP")]
            elif tech.name == "Geothermie":
                tech.Fläche, tech.Bohrtiefe = variables[variables_order.index("Fläche")], variables[variables_order.index("Bohrtiefe")]
            elif tech.name == "BHKW" or tech.name == "Holzgas-BHKW":
                tech.th_Leistung_BHKW = variables[variables_order.index("th_Leistung_BHKW")]
            elif tech.name == "Biomassekessel":
                tech.P_BMK = variables[variables_order.index("P_BMK")]

        if tech.name == "Solarthermie":
            tech_results = tech.calculate(VLT_L, RLT_L, TRY, time_steps, calc1, calc2, q, r, T, BEW, duration, general_results)

        elif tech.name == "Abwärme" or tech.name == "Abwasserwärme":
            tech_results = tech.calculate(VLT_L, COP_data, Strompreis, q, r, T, BEW, duration, general_results)
        
        elif tech.name == "Flusswasser":
            tech_results = tech.calculate(VLT_L, COP_data, Strompreis, q, r, T, BEW, duration, general_results)

        elif tech.name == "Geothermie":
            tech_results = tech.calculate(VLT_L, COP_data, Strompreis, q, r, T, BEW, duration, general_results)
            
        elif tech.name == "BHKW" or tech.name == "Holzgas-BHKW":
            tech_results = tech.calculate(Gaspreis, Holzpreis, Strompreis, q, r, T, BEW, duration, general_results)
            
        elif tech.name == "Biomassekessel":
            tech_results = tech.calculate(Holzpreis, q, r, T, BEW, duration, general_results)
            
        elif tech.name == "Gaskessel":
            tech_results = tech.calculate(Gaspreis, q, r, T, BEW, duration, Last_L, general_results)
            
        else:
            tech_order.remove(tech)
            print(f"{tech.name} ist kein gültiger Erzeugertyp und wird daher nicht betrachtet.")

        if tech_results['Wärmemenge'] > 0:
            general_results['Wärmeleistung_L'].append(tech_results['Wärmeleistung_L'])
            general_results['Wärmemengen'].append(tech_results['Wärmemenge'])
            general_results['Anteile'].append(tech_results['Wärmemenge']/general_results['Jahreswärmebedarf'])
            general_results['WGK'].append(tech_results['WGK'])

            general_results['colors'].append(tech_results['color'])

            general_results['Restlast_L'] -= tech_results['Wärmeleistung_L']
            general_results['Restwärmebedarf'] -= tech_results['Wärmemenge']
            general_results['WGK_Gesamt'] += (tech_results['Wärmemenge']*tech_results['WGK'])/general_results['Jahreswärmebedarf']

            if tech.name == "BHKW" or tech.name == "Holzgas-BHKW":
                general_results['Strommenge'] += tech_results["Strommenge"]
                general_results['el_Leistung_L'] += tech_results["el_Leistung_L"]
                general_results['el_Leistung_ges_L'] += tech_results["el_Leistung_L"]

            if tech.name in ["Abwärme", "Abwasserwärme", "Flusswasser", "Geothermie"]:
                general_results['Strombedarf'] += tech_results["Strombedarf"]
                general_results['el_Leistungsbedarf_L'] += tech_results["el_Leistung_L"]
                general_results['el_Leistung_ges_L'] -= tech_results['el_Leistung_L']

        else:
            tech_order.remove(tech)

    for tech in tech_order:
        general_results['techs'].append(tech.name)

    return general_results

def optimize_mix(tech_order, initial_data, calc1, calc2, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, kapitalzins, preissteigerungsrate, betrachtungszeitraum):
    # solar Fläche, Speichervolumen solar, Leistung Biomasse, Leistung BHKW
    initial_values = []
    variables_order = []
    bounds = []
    for tech in tech_order:
        if isinstance(tech, SolarThermal):
            initial_values.append(tech.bruttofläche_STA)
            variables_order.append("bruttofläche_STA")
            bounds.append((0, 1000))
            initial_values.append(tech.vs)
            variables_order.append("vs")
            bounds.append((0, 100))
        elif isinstance(tech, CHP):
            initial_values.append(tech.th_Leistung_BHKW)
            variables_order.append("th_Leistung_BHKW")
            bounds.append((0, 500))
        elif isinstance(tech, BiomassBoiler):
            initial_values.append(tech.P_BMK)
            variables_order.append("P_BMK")
            bounds.append((0, 500))
        elif isinstance(tech, Geothermal):
            initial_values.append(tech.Fläche)
            variables_order.append("Fläche")
            bounds.append((0, 5000))
            initial_values.append(tech.Bohrtiefe)
            variables_order.append("Bohrtiefe")
            bounds.append((0, 400))
        elif isinstance(tech, WasteHeatPump):
            initial_values.append(tech.Kühlleistung_Abwärme)
            variables_order.append("Kühlleistung_Abwärme")
            bounds.append((0, 500))
        elif isinstance(tech, RiverHeatPump):
            initial_values.append(tech.Wärmeleistung_FW_WP)
            variables_order.append("Wärmeleistung_FW_WP")
            bounds.append((0, 1000))


    def objective(variables):
        general_results = Berechnung_Erzeugermix(tech_order, initial_data, calc1, calc2, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, variables, variables_order, \
                                            kapitalzins=kapitalzins, preissteigerungsrate=preissteigerungsrate, betrachtungszeitraum=betrachtungszeitraum)
        
        return general_results["WGK_Gesamt"]

    # optimization
    result = minimize(objective, initial_values, method='SLSQP', bounds=bounds, options={'maxiter': 1000})
    #result = minimize(objective, initial_values, method='L-BFGS-B', bounds=bounds, options={'maxiter': 1000})
    #result = minimize(objective, initial_values, method='TNC', bounds=bounds, options={'maxiter': 1000})

    if result.success:
        optimized_values = result.x
        optimized_WGK_Gesamt = objective(optimized_values)
        print(f"Optimierte Werte: {optimized_values}")
        print(f"Minimale Wärmegestehungskosten: {optimized_WGK_Gesamt:.2f} €/MWh")

        for tech in tech_order:
            if isinstance(tech, SolarThermal):
                tech.bruttofläche_STA, tech.vs = optimized_values[variables_order.index("bruttofläche_STA")], optimized_values[variables_order.index("vs")]
            elif isinstance(tech, BiomassBoiler):
                tech.P_BMK = optimized_values[variables_order.index("P_BMK")]
            elif isinstance(tech, CHP):
                tech.th_Leistung_BHKW = optimized_values[variables_order.index("th_Leistung_BHKW")]
            elif isinstance(tech, Geothermal):
                tech.Fläche, tech.Bohrtiefe = optimized_values[variables_order.index("Fläche")], optimized_values[variables_order.index("Bohrtiefe")]
            elif isinstance(tech, WasteHeatPump):
                tech.Kühlleistung_Abwärme = optimized_values[variables_order.index("Kühlleistung_Abwärme")]
            elif isinstance(tech, RiverHeatPump):
                tech.Wärmeleistung_FW_WP = optimized_values[variables_order.index("Wärmeleistung_FW_WP")]

        return tech_order
    else:
        print("Optimierung nicht erfolgreich")
        print(result.message)