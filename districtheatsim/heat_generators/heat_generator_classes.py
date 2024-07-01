import numpy as np
from math import pi, sqrt

from scipy.optimize import minimize
from scipy.interpolate import RegularGridInterpolator

from heat_generators.Solarthermie import Berechnung_STA
from heat_generators.Photovoltaik import Calculate_PV

# Wirtschaftlichkeitsberechnung für technische Anlagen nach VDI 2067
def annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand=0, q=1.05, r=1.03, T=20, Energiebedarf=0, Energiekosten=0, E1=0, stundensatz=45):
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

    # betriebsgebundene Kosten
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
        self.Nutzungsdauer_WP = 20
        self.f_Inst_WP, self.f_W_Insp_WP, self.Bedienaufwand_WP = 1, 1.5, 0
        self.f_Inst_WQ, self.f_W_Insp_WQ, self.Bedienaufwand_WQ = 0.5, 0.5, 0
        self.Nutzungsdauer_WQ_dict = {"Abwärme": 20, "Abwasserwärme": 20, "Flusswasser": 20, "Geothermie": 30}

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
    
    def WGK(self, Wärmeleistung, Wärmemenge, Strombedarf, spez_Investitionskosten_WQ, Strompreis, q, r, T, BEW, stundensatz):
        if Wärmemenge == 0:
            return 0
        # Kosten Wärmepumpe: Viessmann Vitocal 350 HT-Pro: 140.000 €, 350 kW Nennleistung; 120 kW bei 10/85
        # Annahme Kosten Wärmepumpe: 1000 €/kW; Vereinfachung
        spezifische_Investitionskosten_WP = self.spezifische_Investitionskosten_WP
        Investitionskosten_WP = spezifische_Investitionskosten_WP * round(Wärmeleistung, 0)
        E1_WP = annuität(Investitionskosten_WP, self.Nutzungsdauer_WP, self.f_Inst_WP, self.f_W_Insp_WP, self.Bedienaufwand_WP, q, r, T,
                            Strombedarf, Strompreis, stundensatz=stundensatz)
        WGK_WP_a = E1_WP/Wärmemenge

        Investitionskosten_WQ = spez_Investitionskosten_WQ * Wärmeleistung
        E1_WQ = annuität(Investitionskosten_WQ, self.Nutzungsdauer_WQ_dict[self.name], self.f_Inst_WQ, self.f_W_Insp_WQ,
                            self.Bedienaufwand_WQ, q, r, T, stundensatz=stundensatz)
        WGK_WQ_a = E1_WQ / Wärmemenge

        WGK_Gesamt_a = WGK_WP_a + WGK_WQ_a

        return WGK_Gesamt_a

class RiverHeatPump(HeatPump):
    def __init__(self, name, Wärmeleistung_FW_WP, Temperatur_FW_WP, dT=0, spez_Investitionskosten_Flusswasser=1000, spezifische_Investitionskosten_WP=1000, min_Teillast=0.2):
        super().__init__(name, spezifische_Investitionskosten_WP=spezifische_Investitionskosten_WP)
        self.Wärmeleistung_FW_WP = Wärmeleistung_FW_WP
        self.Temperatur_FW_WP = Temperatur_FW_WP
        self.dT = dT
        self.spez_Investitionskosten_Flusswasser = spez_Investitionskosten_Flusswasser
        self.min_Teillast = min_Teillast

    def Berechnung_WP(self, Wärmeleistung_L, VLT_L, COP_data):
        COP_L, VLT_L_WP = self.COP_WP(VLT_L, self.Temperatur_FW_WP, COP_data)
        Kühlleistung_L = Wärmeleistung_L * (1 - (1 / COP_L))
        el_Leistung_L = Wärmeleistung_L - Kühlleistung_L
        return Kühlleistung_L, el_Leistung_L, VLT_L_WP

    # Änderung Kühlleistung und Temperatur zu Numpy-Array in aw sowie vor- und nachgelagerten Funktionen
    def abwärme(self, Last_L, VLT_L, COP_data, duration):
        if self.Wärmeleistung_FW_WP == 0:
            return 0, 0, np.zeros_like(Last_L), np.zeros_like(VLT_L), 0, np.zeros_like(VLT_L)

        Wärmeleistung_tat_L = np.zeros_like(Last_L)
        Kühlleistung_tat_L = np.zeros_like(Last_L)
        el_Leistung_tat_L = np.zeros_like(Last_L)
        VLT_L_WP = np.zeros_like(VLT_L)

        # Fälle, in denen die Wärmepumpe betrieben werden kann
        betrieb_mask = Last_L >= self.Wärmeleistung_FW_WP * self.min_Teillast
        Wärmeleistung_tat_L[betrieb_mask] = np.minimum(Last_L[betrieb_mask], self.Wärmeleistung_FW_WP)

        Kühlleistung_tat_L[betrieb_mask], el_Leistung_tat_L[betrieb_mask], VLT_L_WP[betrieb_mask] = self.Berechnung_WP(Wärmeleistung_tat_L[betrieb_mask], VLT_L[betrieb_mask], COP_data)

        # Wärmepumpe soll nur in Betrieb sein, wenn Sie die Vorlauftemperatur erreichen kann
        betrieb_mask_vlt = VLT_L_WP >= VLT_L - self.dT
        Wärmeleistung_tat_L[~betrieb_mask_vlt] = 0
        Kühlleistung_tat_L[~betrieb_mask_vlt] = 0
        el_Leistung_tat_L[~betrieb_mask_vlt] = 0

        Wärmemenge = np.sum(Wärmeleistung_tat_L / 1000) * duration
        Kühlmenge = np.sum(Kühlleistung_tat_L / 1000) * duration
        Strombedarf = np.sum(el_Leistung_tat_L / 1000) * duration

        return Wärmemenge, Strombedarf, Wärmeleistung_tat_L, el_Leistung_tat_L, Kühlmenge, Kühlleistung_tat_L
    
    def calculate(self,VLT_L, COP_data, Strompreis, q, r, T, BEW, stundensatz, duration, general_results):
        
        self.Wärmemenge_Flusswärme, self.Strombedarf_Flusswärme, self.Wärmeleistung_Flusswärme_L, self.el_Leistung_Flusswärme_L, self.Kühlmenge_Flusswärme, self.Kühlleistung_Flusswärme_L = self.abwärme(general_results["Restlast_L"], VLT_L, COP_data, duration)

        WGK_Abwärme = self.WGK(self.Wärmeleistung_FW_WP, self.Wärmemenge_Flusswärme, self.Strombedarf_Flusswärme, self.spez_Investitionskosten_Flusswasser, Strompreis, q, r, T, BEW, stundensatz)

        results = {
            'Wärmemenge': self.Wärmemenge_Flusswärme,
            'Wärmeleistung_L': self.Wärmeleistung_Flusswärme_L,
            'Strombedarf': self.Strombedarf_Flusswärme,
            'el_Leistung_L': self.el_Leistung_Flusswärme_L,
            'WGK': WGK_Abwärme,
            'color': "blue"
        }

        return results
    
class WasteHeatPump(HeatPump):
    def __init__(self, name, Kühlleistung_Abwärme, Temperatur_Abwärme, spez_Investitionskosten_Abwärme=500, spezifische_Investitionskosten_WP=1000, min_Teillast=0.2):
        super().__init__(name, spezifische_Investitionskosten_WP=spezifische_Investitionskosten_WP)
        self.Kühlleistung_Abwärme = Kühlleistung_Abwärme
        self.Temperatur_Abwärme = Temperatur_Abwärme
        self.spez_Investitionskosten_Abwärme = spez_Investitionskosten_Abwärme
        self.min_Teillast = min_Teillast

    def Berechnung_WP(self, VLT_L, COP_data):
        COP_L, VLT_L = self.COP_WP(VLT_L, self.Temperatur_Abwärme, COP_data)
        Wärmeleistung_L = self.Kühlleistung_Abwärme / (1 - (1 / COP_L))
        el_Leistung_L = Wärmeleistung_L - self.Kühlleistung_Abwärme
        return Wärmeleistung_L, el_Leistung_L

    # Änderung Kühlleistung und Temperatur zu Numpy-Array in aw sowie vor- und nachgelagerten Funktionen
    def abwärme(self, Last_L, VLT_L, COP_data, duration):
        if self.Kühlleistung_Abwärme == 0:
            return 0, 0, np.zeros_like(Last_L), np.zeros_like(VLT_L)

        Wärmeleistung_L, el_Leistung_L = self.Berechnung_WP(VLT_L, COP_data)

        Wärmeleistung_tat_L = np.zeros_like(Last_L)
        el_Leistung_tat_L = np.zeros_like(Last_L)

        # Fälle, in denen die Wärmepumpe betrieben werden kann
        betrieb_mask = Last_L >= Wärmeleistung_L * self.min_Teillast
        Wärmeleistung_tat_L[betrieb_mask] = np.minimum(Last_L[betrieb_mask], Wärmeleistung_L[betrieb_mask])
        el_Leistung_tat_L[betrieb_mask] = Wärmeleistung_tat_L[betrieb_mask] - (Wärmeleistung_tat_L[betrieb_mask] / Wärmeleistung_L[betrieb_mask]) * el_Leistung_L[betrieb_mask]

        Wärmemenge = np.sum(Wärmeleistung_tat_L / 1000) * duration
        Strombedarf = np.sum(el_Leistung_tat_L / 1000) * duration

        self.max_Wärmeleistung = np.max(Wärmeleistung_tat_L)

        return Wärmemenge, Strombedarf, Wärmeleistung_tat_L, el_Leistung_tat_L
    
    def calculate(self, VLT_L, COP_data, Strompreis, q, r, T, BEW, stundensatz, duration, general_results):
        
        self.Wärmemenge_Abwärme, self.Strombedarf_Abwärme, self.Wärmeleistung_Abwärme_L, self.el_Leistung_Abwärme_L= self.abwärme(general_results['Restlast_L'], VLT_L, COP_data, duration)

        WGK_Abwärme = self.WGK(self.max_Wärmeleistung, self.Wärmemenge_Abwärme, self.Strombedarf_Abwärme, self.spez_Investitionskosten_Abwärme, Strompreis, q, r, T, BEW, stundensatz)

        results = {
            'Wärmemenge': self.Wärmemenge_Abwärme,
            'Wärmeleistung_L': self.Wärmeleistung_Abwärme_L,
            'Strombedarf': self.Strombedarf_Abwärme,
            'el_Leistung_L': self.el_Leistung_Abwärme_L,
            'WGK': WGK_Abwärme,
            'color': "grey"
        }

        return results

class Geothermal(HeatPump):
    def __init__(self, name, Fläche, Bohrtiefe, Temperatur_Geothermie, spez_Bohrkosten=100, spez_Entzugsleistung=50,
                 Vollbenutzungsstunden=2400, Abstand_Sonden=10, spezifische_Investitionskosten_WP=1000, min_Teillast=0.2):
        super().__init__(name, spezifische_Investitionskosten_WP=spezifische_Investitionskosten_WP)
        self.Fläche = Fläche
        self.Bohrtiefe = Bohrtiefe
        self.Temperatur_Geothermie = Temperatur_Geothermie
        self.spez_Bohrkosten = spez_Bohrkosten
        self.spez_Entzugsleistung = spez_Entzugsleistung
        self.Vollbenutzungsstunden = Vollbenutzungsstunden
        self.Abstand_Sonden = Abstand_Sonden
        self.min_Teillast = min_Teillast

    def Geothermie(self, Last_L, VLT_L, COP_data, duration):
        if self.Fläche == 0 or self.Bohrtiefe == 0:
            return 0, 0, np.zeros_like(Last_L), np.zeros_like(VLT_L)

        Anzahl_Sonden = (round(sqrt(self.Fläche)/self.Abstand_Sonden)+1)**2

        Entzugsleistung_2400 = self.Bohrtiefe * self.spez_Entzugsleistung * Anzahl_Sonden / 1000
        # kW bei 2400 h, 22 Sonden, 50 W/m: 220 kW
        Entzugswärmemenge = Entzugsleistung_2400 * self.Vollbenutzungsstunden / 1000  # MWh
        self.Investitionskosten_Sonden = self.Bohrtiefe * self.spez_Bohrkosten * Anzahl_Sonden

        COP_L, VLT_WP = self.COP_WP(VLT_L, self.Temperatur_Geothermie, COP_data)

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
            Wärmeleistung_tat_L = np.zeros_like(Last_L)
            el_Leistung_tat_L = np.zeros_like(Last_L)
            Entzugsleistung_tat_L = np.zeros_like(Last_L)

            # Fälle, in denen die Wärmepumpe betrieben werden kann
            betrieb_mask = Last_L >= Wärmeleistung_L * self.min_Teillast
            Wärmeleistung_tat_L[betrieb_mask] = np.minimum(Last_L[betrieb_mask], Wärmeleistung_L[betrieb_mask])
            el_Leistung_tat_L[betrieb_mask] = Wärmeleistung_tat_L[betrieb_mask] - (Entzugsleistung * np.ones_like(Last_L))[betrieb_mask]
            Entzugsleistung_tat_L[betrieb_mask] = Wärmeleistung_tat_L[betrieb_mask] - el_Leistung_tat_L[betrieb_mask]

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
    
    def calculate(self, VLT_L, COP_data, Strompreis, q, r, T, BEW, stundensatz, duration, general_results):
        # Hier fügen Sie die spezifische Logik für die Geothermie-Berechnung ein
        self.Wärmemenge_Geothermie, self.Strombedarf_Geothermie, self.Wärmeleistung_Geothermie_L, self.el_Leistung_Geothermie_L = self.Geothermie(general_results['Restlast_L'], VLT_L, COP_data, duration)

        self.spez_Investitionskosten_Erdsonden = self.Investitionskosten_Sonden / self.max_Wärmeleistung
        WGK_Geothermie = self.WGK(self.max_Wärmeleistung, self.Wärmemenge_Geothermie, self.Strombedarf_Geothermie, self.spez_Investitionskosten_Erdsonden, Strompreis, q, r, T, BEW, stundensatz)

        results = {
            'Wärmemenge': self.Wärmemenge_Geothermie,
            'Wärmeleistung_L': self.Wärmeleistung_Geothermie_L,
            'Strombedarf': self.Strombedarf_Geothermie,
            'el_Leistung_L': self.el_Leistung_Geothermie_L,
            'WGK': WGK_Geothermie,
            'color': "darkorange"
        }

        return results

class CHP:
    def __init__(self, name, th_Leistung_BHKW, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850, el_Wirkungsgrad=0.33, KWK_Wirkungsgrad=0.9, 
                 min_Teillast=0.7, speicher_aktiv=False, Speicher_Volumen_BHKW=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, min_fill=0.2, max_fill=0.8, 
                 spez_Investitionskosten_Speicher=750, BHKW_an=True, opt_BHKW_min=0, opt_BHKW_max=1000, opt_BHKW_Speicher_min=0, opt_BHKW_Speicher_max=100):
        self.name = name
        self.th_Leistung_BHKW = th_Leistung_BHKW
        self.spez_Investitionskosten_GBHKW = spez_Investitionskosten_GBHKW
        self.spez_Investitionskosten_HBHKW = spez_Investitionskosten_HBHKW
        self.el_Wirkungsgrad = el_Wirkungsgrad
        self.KWK_Wirkungsgrad = KWK_Wirkungsgrad
        self.min_Teillast = min_Teillast
        self.speicher_aktiv = speicher_aktiv
        self.Speicher_Volumen_BHKW = Speicher_Volumen_BHKW
        self.T_vorlauf = T_vorlauf
        self.T_ruecklauf = T_ruecklauf
        self.initial_fill = initial_fill
        self.min_fill = min_fill
        self.max_fill = max_fill
        self.spez_Investitionskosten_Speicher = spez_Investitionskosten_Speicher
        self.BHKW_an = BHKW_an
        self.opt_BHKW_min = opt_BHKW_min
        self.opt_BHKW_max = opt_BHKW_max
        self.opt_BHKW_Speicher_min = opt_BHKW_Speicher_min
        self.opt_BHKW_Speicher_max = opt_BHKW_Speicher_max
        self.thermischer_Wirkungsgrad = self.KWK_Wirkungsgrad - self.el_Wirkungsgrad
        self.el_Leistung_Soll = self.th_Leistung_BHKW / self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad
        self.Nutzungsdauer = 15
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 6, 2, 0
        if self.name == "BHKW":
            self.co2_factor_fuel = 0.201 # tCO2/MWh gas
        elif self.name == "Holzgas-BHKW":
            self.co2_factor_fuel = 0.036 # tCO2/MWh pellets
        self.co2_factor_electricity = 0.4 # tCO2/MWh electricity 

    def BHKW(self, Last_L, duration):
        # Berechnen der Strom- und Wärmemenge des BHKW
        self.Wärmeleistung_BHKW_L = np.zeros_like(Last_L)
        self.el_Leistung_BHKW_L = np.zeros_like(Last_L)

        # Fälle, in denen das BHKW betrieben werden kann
        betrieb_mask = Last_L >= self.th_Leistung_BHKW * self.min_Teillast
        self.Wärmeleistung_BHKW_L[betrieb_mask] = np.minimum(Last_L[betrieb_mask], self.th_Leistung_BHKW)
        self.el_Leistung_BHKW_L[betrieb_mask] = self.Wärmeleistung_BHKW_L[betrieb_mask] / self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad

        self.Wärmemenge_BHKW = np.sum(self.Wärmeleistung_BHKW_L / 1000)*duration
        self.Strommenge_BHKW = np.sum(self.el_Leistung_BHKW_L / 1000)*duration

        # Berechnen des Brennstoffbedarfs
        self.Brennstoffbedarf_BHKW = (self.Wärmemenge_BHKW + self.Strommenge_BHKW) / self.KWK_Wirkungsgrad

        # Anzahl Starts und Betriebsstunden pro Start berechnen
        starts = np.diff(betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden_gesamt = np.sum(betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = self.Betriebsstunden_gesamt / self.Anzahl_Starts if self.Anzahl_Starts > 0 else 0

    def storage(self, Last_L, duration):
        # Speicherparameter
        speicher_kapazitaet = self.Speicher_Volumen_BHKW * 4186 * (self.T_vorlauf - self.T_ruecklauf) / 3600  # kWh
        speicher_fill = self.initial_fill * speicher_kapazitaet
        min_speicher_fill = self.min_fill * speicher_kapazitaet
        max_speicher_fill = self.max_fill * speicher_kapazitaet

        self.Wärmeleistung_BHKW_Speicher = np.zeros_like(Last_L)
        self.Wärmeleistung_Speicher_BHKW = np.zeros_like(Last_L)
        self.el_Leistung_BHKW_Speicher = np.zeros_like(Last_L)
        self.speicher_fuellstand_BHKW = np.zeros_like(Last_L)

        for i in range(len(Last_L)):
            if self.BHKW_an:
                if speicher_fill >= max_speicher_fill:
                    self.BHKW_an = False
                else:
                    self.Wärmeleistung_BHKW_Speicher[i] = self.th_Leistung_BHKW
                    if Last_L[i] < self.th_Leistung_BHKW:
                        self.Wärmeleistung_Speicher_BHKW[i] = Last_L[i] - self.th_Leistung_BHKW
                        speicher_fill += (self.th_Leistung_BHKW - Last_L[i]) * duration
                        speicher_fill = float(min(speicher_fill, speicher_kapazitaet))
                    else:
                        self.Wärmeleistung_Speicher_BHKW[i] = 0
            else:
                if speicher_fill <= min_speicher_fill:
                    self.BHKW_an = True
            
            if not self.BHKW_an:
                self.Wärmeleistung_BHKW_Speicher[i] = 0
                self.Wärmeleistung_Speicher_BHKW[i] = Last_L[i]
                speicher_fill -= Last_L[i] * duration
                speicher_fill = float(max(speicher_fill, 0))

            self.el_Leistung_BHKW_Speicher[i] = self.Wärmeleistung_BHKW_Speicher[i] / self.thermischer_Wirkungsgrad * self.el_Wirkungsgrad
            self.speicher_fuellstand_BHKW[i] = speicher_fill / speicher_kapazitaet * 100  # %

        self.Wärmemenge_BHKW_Speicher = np.sum(self.Wärmeleistung_BHKW_Speicher / 1000) * duration
        self.Strommenge_BHKW_Speicher = np.sum(self.el_Leistung_BHKW_Speicher / 1000) * duration

        # Berechnen des Brennstoffbedarfs
        self.Brennstoffbedarf_BHKW_Speicher = (self.Wärmemenge_BHKW_Speicher + self.Strommenge_BHKW_Speicher) / self.KWK_Wirkungsgrad

        # Anzahl Starts und Betriebsstunden pro Start berechnen
        betrieb_mask = self.Wärmeleistung_BHKW_Speicher > 0
        starts = np.diff(betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts_Speicher = np.sum(starts)
        self.Betriebsstunden_gesamt_Speicher = np.sum(betrieb_mask) * duration
        self.Betriebsstunden_pro_Start_Speicher = self.Betriebsstunden_gesamt_Speicher / self.Anzahl_Starts_Speicher if self.Anzahl_Starts_Speicher > 0 else 0
    
    def WGK(self, Wärmemenge, Strommenge, Brennstoffbedarf, Brennstoffkosten, Strompreis, q, r, T, BEW, stundensatz):
        if Wärmemenge == 0:
            return 0
        # Holzvergaser-BHKW: 130 kW: 240.000 -> 1850 €/kW
        # (Erd-)Gas-BHKW: 100 kW: 150.000 € -> 1500 €/kW
        if self.name == "BHKW":
            spez_Investitionskosten_BHKW = self.spez_Investitionskosten_GBHKW  # €/kW
        elif self.name == "Holzgas-BHKW":
            spez_Investitionskosten_BHKW = self.spez_Investitionskosten_HBHKW  # €/kW

        self.Investitionskosten_BHKW = spez_Investitionskosten_BHKW * self.th_Leistung_BHKW
        self.Investitionskosten_Speicher = self.spez_Investitionskosten_Speicher * self.Speicher_Volumen_BHKW
        self.Investitionskosten = self.Investitionskosten_BHKW + self.Investitionskosten_Speicher

        self.Stromeinnahmen = Strommenge * Strompreis

        self.A_N = annuität(self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, q, r, T, Brennstoffbedarf, Brennstoffkosten, self.Stromeinnahmen, stundensatz)
        self.WGK_BHKW = self.A_N / Wärmemenge

    def calculate(self, Gaspreis, Holzpreis, Strompreis, q, r, T, BEW, stundensatz, duration, general_results):
        if self.speicher_aktiv:
            self.storage(general_results["Restlast_L"], duration)
            Wärmemenge = self.Wärmemenge_BHKW_Speicher
            Strommenge = self.Strommenge_BHKW_Speicher
            Brennstoffbedarf = self.Brennstoffbedarf_BHKW_Speicher
            Wärmeleistung_BHKW = self.Wärmeleistung_BHKW_Speicher
            el_Leistung_BHKW = self.el_Leistung_BHKW_Speicher
            Anzahl_Starts = self.Anzahl_Starts_Speicher
            Betriebsstunden = self.Betriebsstunden_gesamt_Speicher
            Betriebsstunden_pro_Start= self.Betriebsstunden_pro_Start_Speicher
        else:
            self.BHKW(general_results["Restlast_L"], duration)
            Wärmemenge = self.Wärmemenge_BHKW
            Strommenge = self.Strommenge_BHKW
            Brennstoffbedarf = self.Brennstoffbedarf_BHKW
            Wärmeleistung_BHKW = self.Wärmeleistung_BHKW_L
            el_Leistung_BHKW = self.el_Leistung_BHKW_L
            Anzahl_Starts = self.Anzahl_Starts
            Betriebsstunden = self.Betriebsstunden_gesamt
            Betriebsstunden_pro_Start= self.Betriebsstunden_pro_Start

        if self.name == "BHKW":
            self.Brennstoffpreis = Gaspreis
        elif self.name == "Holzgas-BHKW":
            self.Brennstoffpreis = Holzpreis

        self.WGK(Wärmemenge, Strommenge, Brennstoffbedarf, self.Brennstoffpreis, Strompreis, q, r, T, BEW, stundensatz)

        # CO2 emissions due to fuel usage
        self.co2_emissions = Brennstoffbedarf * self.co2_factor_fuel # tCO2
        # CO2 savings due to electricity generation
        self.co2_savings = Strommenge * self.co2_factor_electricity # tCO2
        # total co2
        self.co2_total = self.co2_emissions - self.co2_savings # tCO2
        # specific emissions heat
        self.spec_co2_total = self.co2_total / Wärmemenge if Wärmemenge > 0 else 0 # tCO2/MWh_heat

        results = {
            'Wärmemenge': Wärmemenge,
            'Wärmeleistung_L': Wärmeleistung_BHKW,
            'Brennstoffbedarf': Brennstoffbedarf,
            'WGK': self.WGK_BHKW,
            'Strommenge': Strommenge,
            'el_Leistung_L': el_Leistung_BHKW,
            'Anzahl_Starts': Anzahl_Starts,
            'Betriebsstunden': Betriebsstunden,
            'Betriebsstunden_pro_Start': Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'color': "yellow"
        }

        if self.speicher_aktiv:
            results['Wärmeleistung_Speicher_L'] = self.Wärmeleistung_Speicher_BHKW

        return results

class BiomassBoiler:
    def __init__(self, name, P_BMK, Größe_Holzlager=40, spez_Investitionskosten=200, spez_Investitionskosten_Holzlager=400, Nutzungsgrad_BMK=0.8, min_Teillast=0.3,
                 speicher_aktiv=False, Speicher_Volumen=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, min_fill=0.2, max_fill=0.8, 
                 spez_Investitionskosten_Speicher=750, BMK_an=True, opt_BMK_min=0, opt_BMK_max=1000, opt_BMK_Speicher_min=0, opt_BMK_Speicher_max=100):
        self.name = name
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
        self.opt_BMK_Speicher_min = opt_BMK_Speicher_min
        self.opt_BMK_Speicher_max = opt_BMK_Speicher_max
        self.Nutzungsdauer = 15
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 3, 3, 0
        self.co2_factor_fuel = 0.036 # tCO2/MWh pellets

    def Biomassekessel(self, Last_L, duration):
        self.Wärmeleistung_Biomassekessel = np.zeros_like(Last_L)

        # Fälle, in denen der Biomassekessel betrieben werden kann
        betrieb_mask = Last_L >= self.P_BMK * self.min_Teillast
        self.Wärmeleistung_Biomassekessel[betrieb_mask] = np.minimum(Last_L[betrieb_mask], self.P_BMK)

        self.Wärmemenge_BMK = np.sum(self.Wärmeleistung_Biomassekessel / 1000)*duration
        self.Brennstoffbedarf_BMK = self.Wärmemenge_BMK / self.Nutzungsgrad_BMK

        # Anzahl Starts und Betriebsstunden pro Start berechnen
        starts = np.diff(betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden_gesamt = np.sum(betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = self.Betriebsstunden_gesamt / self.Anzahl_Starts if self.Anzahl_Starts > 0 else 0

    def storage(self, Last_L, duration):
        # Speicherparameter
        speicher_kapazitaet = self.Speicher_Volumen * 4186 * (self.T_vorlauf - self.T_ruecklauf) / 3600  # kWh
        speicher_fill = self.initial_fill * speicher_kapazitaet
        min_speicher_fill = self.min_fill * speicher_kapazitaet
        max_speicher_fill = self.max_fill * speicher_kapazitaet

        self.Wärmeleistung_Biomassekessel_Speicher = np.zeros_like(Last_L)
        self.Wärmeleistung_Speicher_BMK = np.zeros_like(Last_L)
        self.speicher_fuellstand_BMK = np.zeros_like(Last_L)

        for i in range(len(Last_L)):
            if self.BMK_an:
                if speicher_fill >= max_speicher_fill:
                    self.BMK_an = False
                else:
                    self.Wärmeleistung_Biomassekessel_Speicher[i] = self.P_BMK
                    if Last_L[i] < self.P_BMK:
                        self.Wärmeleistung_Speicher_BMK[i] = Last_L[i] - self.P_BMK
                        speicher_fill += (self.P_BMK - Last_L[i]) * duration
                        speicher_fill = float(min(speicher_fill, speicher_kapazitaet))
                    else:
                        self.Wärmeleistung_Speicher_BMK[i] = 0
            else:
                if speicher_fill <= min_speicher_fill:
                    self.BMK_an = True
            
            if not self.BMK_an:
                self.Wärmeleistung_Biomassekessel_Speicher[i] = 0
                self.Wärmeleistung_Speicher_BMK[i] = Last_L[i]
                speicher_fill -= Last_L[i] * duration
                speicher_fill = float(max(speicher_fill, 0))

            self.speicher_fuellstand_BMK[i] = speicher_fill / speicher_kapazitaet * 100  # %

        self.Wärmemenge_Biomassekessel_Speicher = np.sum(self.Wärmeleistung_Biomassekessel_Speicher / 1000) * duration

        # Berechnen des Brennstoffbedarfs
        self.Brennstoffbedarf_BMK_Speicher = self.Wärmemenge_Biomassekessel_Speicher / self.Nutzungsgrad_BMK

        # Anzahl Starts und Betriebsstunden pro Start berechnen
        betrieb_mask = self.Wärmeleistung_Biomassekessel_Speicher > 0
        starts = np.diff(betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts_Speicher = np.sum(starts)
        self.Betriebsstunden_gesamt_Speicher = np.sum(betrieb_mask) * duration
        self.Betriebsstunden_pro_Start_Speicher = self.Betriebsstunden_gesamt_Speicher / self.Anzahl_Starts_Speicher if self.Anzahl_Starts_Speicher > 0 else 0

    def WGK(self, Wärmemenge, Brennstoffbedarf, Brennstoffkosten, q, r, T, BEW, stundensatz):
        if Wärmemenge == 0:
            return 0
        
        self.Investitionskosten_Kessel = self.spez_Investitionskosten * self.P_BMK
        self.Investitionskosten_Holzlager = self.spez_Investitionskosten_Holzlager * self.Größe_Holzlager
        self.Investitionskosten_Speicher = self.spez_Investitionskosten_Speicher * self.Speicher_Volumen
        self.Investitionskosten = self.Investitionskosten_Kessel + self.Investitionskosten_Holzlager + self.Investitionskosten_Speicher

        self.A_N = annuität(self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, q, r, T, Brennstoffbedarf,
                            Brennstoffkosten, stundensatz=stundensatz)
        
        self.WGK_BMK = self.A_N / Wärmemenge

    def calculate(self, Holzpreis, q, r, T, BEW, stundensatz, duration, general_results):
        if self.speicher_aktiv:
            self.storage(general_results["Restlast_L"], duration)
            Wärmemenge = self.Wärmemenge_Biomassekessel_Speicher
            Brennstoffbedarf = self.Brennstoffbedarf_BMK_Speicher
            Wärmeleistung = self.Wärmeleistung_Biomassekessel_Speicher
            Anzahl_Starts = self.Anzahl_Starts_Speicher
            Betriebsstunden = self.Betriebsstunden_gesamt_Speicher
            Betriebsstunden_pro_Start= self.Betriebsstunden_pro_Start_Speicher
        else:
            self.Biomassekessel(general_results["Restlast_L"], duration)
            Wärmemenge = self.Wärmemenge_BMK
            Brennstoffbedarf = self.Brennstoffbedarf_BMK
            Wärmeleistung = self.Wärmeleistung_Biomassekessel
            Anzahl_Starts = self.Anzahl_Starts
            Betriebsstunden = self.Betriebsstunden_gesamt
            Betriebsstunden_pro_Start= self.Betriebsstunden_pro_Start

        self.WGK(Wärmemenge, Brennstoffbedarf, Holzpreis, q, r, T, BEW, stundensatz)

        # CO2 emissions due to fuel usage
        self.co2_emissions = Brennstoffbedarf * self.co2_factor_fuel # tCO2
        # specific emissions heat
        self.spec_co2_total = self.co2_emissions / Wärmemenge if Wärmemenge > 0 else 0 # tCO2/MWh_heat
        
        results = {
            'Wärmemenge': Wärmemenge,
            'Wärmeleistung_L': Wärmeleistung,
            'Brennstoffbedarf': Brennstoffbedarf,
            'WGK': self.WGK_BMK,
            'Anzahl_Starts': Anzahl_Starts,
            'Betriebsstunden': Betriebsstunden,
            'Betriebsstunden_pro_Start': Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'color': "green"
        }

        if self.speicher_aktiv:
            results['Wärmeleistung_Speicher_L'] = self.Wärmeleistung_Speicher_BMK

        return results
    
class GasBoiler:
    def __init__(self, name, spez_Investitionskosten=30, Nutzungsgrad=0.9, Faktor_Dimensionierung=1):
        self.name = name
        self.spez_Investitionskosten = spez_Investitionskosten
        self.Nutzungsgrad = Nutzungsgrad
        self.Faktor_Dimensionierung = Faktor_Dimensionierung
        self.Nutzungsdauer = 20
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 1, 2, 0
        self.co2_factor_fuel = 0.201 # tCO2/MWh gas

    def Gaskessel(self, Last_L, duration):
        self.Wärmeleistung_GK = np.maximum(Last_L, 0)
        self.Wärmemenge_Gaskessel = np.sum(self.Wärmeleistung_GK/1000)*duration
        self.Gasbedarf = self.Wärmemenge_Gaskessel / self.Nutzungsgrad
        self.P_max = max(Last_L) * self.Faktor_Dimensionierung

    def WGK(self, Brennstoffkosten, q, r, T, BEW, stundensatz):
        if self.Wärmemenge_Gaskessel == 0:
            return 0
        
        self.Investitionskosten = self.spez_Investitionskosten * self.P_max

        self.A_N = annuität(self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, q, r, T,
                            self.Gasbedarf, Brennstoffkosten, stundensatz=stundensatz)
        self.WGK_GK = self.A_N / self.Wärmemenge_Gaskessel

    def calculate(self, Gaspreis, q, r, T, BEW, stundensatz, duration, Last_L, general_results):
        self.Gaskessel(general_results['Restlast_L'], duration)
        self.WGK(Gaspreis, q, r, T, BEW, stundensatz)

        # CO2 emissions due to fuel usage
        self.co2_emissions = self.Gasbedarf * self.co2_factor_fuel # tCO2
        # specific emissions heat
        self.spec_co2_total = self.co2_emissions / self.Wärmemenge_Gaskessel if self.Wärmemenge_Gaskessel > 0 else 0 # tCO2/MWh_heat

        results = {
            'Wärmemenge': self.Wärmemenge_Gaskessel,
            'Wärmeleistung_L': self.Wärmeleistung_GK,
            'Brennstoffbedarf': self.Gasbedarf,
            'WGK': self.WGK_GK,
            'spec_co2_total': self.spec_co2_total,
            "color": "saddlebrown"
        }

        return results

class SolarThermal:
    def __init__(self, name, bruttofläche_STA, vs, Typ, kosten_speicher_spez=750, kosten_fk_spez=430, kosten_vrk_spez=590, Tsmax=90, Longitude=-14.4222, 
                 STD_Longitude=-15, Latitude=51.1676, East_West_collector_azimuth_angle=0, Collector_tilt_angle=36, Tm_rl=60, Qsa=0, Vorwärmung_K=8, 
                 DT_WT_Solar_K=5, DT_WT_Netz_K=5, opt_volume_min=0, opt_volume_max=200, opt_area_min=0, opt_area_max=2000):
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
        self.Nutzungsdauer = 20 # Jahre
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 0.5, 1, 0
        self.Anteil_Förderung_BEW = 0.4
        self.Betriebskostenförderung_BEW = 10 # €/MWh 10 Jahre
        self.co2_factor_solar = 0.0 # tCO2/MWh heat is 0 ?

    def calc_WGK(self, q, r, T, BEW, stundensatz):
        if self.Wärmemenge_Solarthermie == 0:
            return 0

        self.Investitionskosten_Speicher = self.vs * self.kosten_speicher_spez
        self.Investitionskosten_STA = self.bruttofläche_STA * self.Kosten_STA_spez
        self.Investitionskosten = self.Investitionskosten_Speicher + self.Investitionskosten_STA

        self.A_N = annuität(self.Investitionskosten, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, q, r, T, stundensatz=stundensatz)
        self.WGK = self.A_N / self.Wärmemenge_Solarthermie

        self.Eigenanteil = 1 - self.Anteil_Förderung_BEW
        self.Investitionskosten_Gesamt_BEW = self.Investitionskosten * self.Eigenanteil
        self.Annuität_BEW = annuität(self.Investitionskosten_Gesamt_BEW, self.Nutzungsdauer, self.f_Inst, self.f_W_Insp, self.Bedienaufwand, q, r, T, stundensatz=stundensatz)
        self.WGK_BEW = self.Annuität_BEW / self.Wärmemenge_Solarthermie

        self.WGK_BEW_BKF = self.WGK_BEW - self.Betriebskostenförderung_BEW

        if BEW == "Nein":
            return self.WGK
        elif BEW == "Ja":
            return self.WGK_BEW_BKF
        
    def calculate(self, VLT_L, RLT_L, TRY, time_steps, calc1, calc2, q, r, T, BEW, stundensatz, duration, general_results):
        # Berechnung der Solarthermieanlage
        self.Wärmemenge_Solarthermie, self.Wärmeleistung_Solarthermie, self.Speicherladung_Solarthermie, self.Speicherfüllstand_Solarthermie = Berechnung_STA(self.bruttofläche_STA, 
                                                                                                        self.vs, self.Typ, general_results['Restlast_L'], VLT_L, RLT_L, 
                                                                                                        TRY, time_steps, calc1, calc2, duration, self.Tsmax, self.Longitude, self.STD_Longitude, 
                                                                                                        self.Latitude, self.East_West_collector_azimuth_angle, self.Collector_tilt_angle, self.Tm_rl, 
                                                                                                        self.Qsa, self.Vorwärmung_K, self.DT_WT_Solar_K, self.DT_WT_Netz_K)
        # Berechnung der Wärmegestehungskosten
        self.WGK_Solarthermie = self.calc_WGK(q, r, T, BEW, stundensatz)

        # Berechnung der Emissionen
        self.co2_emissions = self.Wärmemenge_Solarthermie * self.co2_factor_solar # tCO2
        # specific emissions heat
        self.spec_co2_total = self.co2_emissions / self.Wärmemenge_Solarthermie if self.Wärmemenge_Solarthermie > 0 else 0 # tCO2/MWh_heat


        results = { 
            'Wärmemenge': self.Wärmemenge_Solarthermie,
            'Wärmeleistung_L': self.Wärmeleistung_Solarthermie,
            'WGK': self.WGK_Solarthermie,
            'spec_co2_total': self.spec_co2_total,
            'Speicherladung_L': self.Speicherladung_Solarthermie,
            'Speicherfüllstand_L': self.Speicherfüllstand_Solarthermie,
            'color': "red"
        }

        return results

def calculate_factors(Kapitalzins, Preissteigerungsrate, Betrachtungszeitraum):
    q = 1 + Kapitalzins / 100
    r = 1 + Preissteigerungsrate / 100
    T = Betrachtungszeitraum
    return q, r, T

def Berechnung_Erzeugermix(tech_order, initial_data, start, end, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, variables=[], variables_order=[], kapitalzins=5, preissteigerungsrate=3, betrachtungszeitraum=20, stundensatz=45):
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
        'techs': [],
        'tech_classes': []
    }

    # zunächst Berechnung der Erzeugung
    for idx, tech in enumerate(tech_order.copy()):
        if len(variables) > 0:
            if tech.name == "Solarthermie":
                tech.bruttofläche_STA = variables[variables_order.index(f"bruttofläche_STA_{idx}")]
                tech.vs = variables[variables_order.index(f"vs_{idx}")]
            elif tech.name == "Abwärme" or tech.name == "Abwasserwärme":
                tech.Kühlleistung_Abwärme = variables[variables_order.index(f"Kühlleistung_Abwärme_{idx}")]
            elif tech.name == "Flusswasser":
                tech.Wärmeleistung_FW_WP = variables[variables_order.index(f"Wärmeleistung_FW_WP_{idx}")]
            elif tech.name == "Geothermie":
                tech.Fläche = variables[variables_order.index(f"Fläche_{idx}")]
                tech.Bohrtiefe = variables[variables_order.index(f"Bohrtiefe_{idx}")]
            elif tech.name == "BHKW" or tech.name == "Holzgas-BHKW":
                tech.th_Leistung_BHKW = variables[variables_order.index(f"th_Leistung_BHKW_{idx}")]
                if tech.speicher_aktiv == True:
                    tech.Speicher_Volumen_BHKW = variables[variables_order.index(f"Speicher_Volumen_BHKW_{idx}")]
            elif tech.name == "Biomassekessel":
                tech.P_BMK = variables[variables_order.index(f"P_BMK_{idx}")]

        if tech.name == "Solarthermie":
            tech_results = tech.calculate(VLT_L, RLT_L, TRY, time_steps, start, end, q, r, T, BEW, stundensatz, duration, general_results)

        elif tech.name == "Abwärme" or tech.name == "Abwasserwärme":
            tech_results = tech.calculate(VLT_L, COP_data, Strompreis, q, r, T, BEW, stundensatz, duration, general_results)
        
        elif tech.name == "Flusswasser":
            tech_results = tech.calculate(VLT_L, COP_data, Strompreis, q, r, T, BEW, stundensatz, duration, general_results)

        elif tech.name == "Geothermie":
            tech_results = tech.calculate(VLT_L, COP_data, Strompreis, q, r, T, BEW, stundensatz, duration, general_results)
            
        elif tech.name == "BHKW" or tech.name == "Holzgas-BHKW":
            tech_results = tech.calculate(Gaspreis, Holzpreis, Strompreis, q, r, T, BEW, stundensatz, duration, general_results)
            
        elif tech.name == "Biomassekessel":
            tech_results = tech.calculate(Holzpreis, q, r, T, BEW, stundensatz, duration, general_results)
            
        elif tech.name == "Gaskessel":
            tech_results = tech.calculate(Gaspreis, q, r, T, BEW, stundensatz, duration, Last_L, general_results)
            
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

            if "Wärmeleistung_Speicher_L" in tech_results.keys():
                # general_results['Wärmeleistung_L'].append(tech_results['Wärmeleistung_Speicher_L']) führt bestimmt nur zu Problemen
                # general_results['Wärmemengen'].append(tech_results['Wärmemenge_Speicher_L']) eigentlich nicht oder?
                general_results['Restlast_L'] -= tech_results['Wärmeleistung_Speicher_L']

        else:
            tech_order.remove(tech)
            print(f"{tech.name} wurde durch die Optimierung entfernt.")

    for tech in tech_order:
        general_results['techs'].append(tech.name)
        general_results['tech_classes'].append(tech)

    return general_results

def optimize_mix(tech_order, initial_data, start, end, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, kapitalzins, preissteigerungsrate, betrachtungszeitraum, stundensatz):
    initial_values = []
    variables_order = []
    bounds = []
    for idx, tech in enumerate(tech_order):
        if isinstance(tech, SolarThermal):
            initial_values.append(tech.bruttofläche_STA)
            variables_order.append(f"bruttofläche_STA_{idx}")
            bounds.append((tech.opt_area_min, tech.opt_area_max))

            initial_values.append(tech.vs)
            variables_order.append(f"vs_{idx}")
            bounds.append((tech.opt_volume_min, tech.opt_volume_max))

        elif isinstance(tech, CHP):
            initial_values.append(tech.th_Leistung_BHKW)
            variables_order.append(f"th_Leistung_BHKW_{idx}")
            bounds.append((tech.opt_BHKW_min, tech.opt_BHKW_max))

            if tech.speicher_aktiv == True:
                initial_values.append(tech.Speicher_Volumen_BHKW)
                variables_order.append(f"Speicher_Volumen_BHKW_{idx}")
                bounds.append((tech.opt_BHKW_Speicher_min, tech.opt_BHKW_Speicher_max))

        elif isinstance(tech, BiomassBoiler):
            initial_values.append(tech.P_BMK)
            variables_order.append(f"P_BMK_{idx}")
            bounds.append((tech.opt_BMK_min, tech.opt_BMK_max))

            if tech.speicher_aktiv == True:
                initial_values.append(tech.Speicher_Volumen)
                variables_order.append(f"Speicher_Volumen_{idx}")
                bounds.append((tech.opt_BMK_Speicher_min, tech.opt_BMK_Speicher_max))

        elif isinstance(tech, Geothermal):
            initial_values.append(tech.Fläche)
            variables_order.append(f"Fläche_{idx}")
            min_area_geothermal = 0
            max_area_geothermal = 5000
            bounds.append((min_area_geothermal, max_area_geothermal))

            initial_values.append(tech.Bohrtiefe)
            variables_order.append(f"Bohrtiefe_{idx}")
            min_area_depth = 0
            max_area_depth = 400
            bounds.append((min_area_depth, max_area_depth))

        elif isinstance(tech, WasteHeatPump):
            initial_values.append(tech.Kühlleistung_Abwärme)
            variables_order.append(f"Kühlleistung_Abwärme_{idx}")
            min_cooling = 0
            max_cooling = 500
            bounds.append((min_cooling, max_cooling))

        elif isinstance(tech, RiverHeatPump):
            initial_values.append(tech.Wärmeleistung_FW_WP)
            variables_order.append(f"Wärmeleistung_FW_WP_{idx}")
            min_power_river = 0
            max_power_river = 1000
            bounds.append((min_power_river, max_power_river))


    def objective(variables):
        general_results = Berechnung_Erzeugermix(tech_order, initial_data, start, end, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, variables, variables_order, \
                                            kapitalzins=kapitalzins, preissteigerungsrate=preissteigerungsrate, betrachtungszeitraum=betrachtungszeitraum, stundensatz=stundensatz)
        
        return general_results["WGK_Gesamt"]
    
    #def objective2(variables):
    #    general_results = Berechnung_Erzeugermix(tech_order, initial_data, start, end, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, variables, variables_order, \
    #                                        kapitalzins=kapitalzins, preissteigerungsrate=preissteigerungsrate, betrachtungszeitraum=betrachtungszeitraum, stundensatz=stundensatz)
    #    
    #   return general_results["spec_co2_emissions"]

    # optimization
    result = minimize(objective, initial_values, method='SLSQP', bounds=bounds, options={'maxiter': 100})

    if result.success:
        optimized_values = result.x
        optimized_WGK_Gesamt = objective(optimized_values)
        print(f"Optimierte Werte: {optimized_values}")
        print(f"Minimale Wärmegestehungskosten: {optimized_WGK_Gesamt:.2f} €/MWh")

        for idx, tech in enumerate(tech_order):
            if isinstance(tech, SolarThermal):
                tech.bruttofläche_STA = optimized_values[variables_order.index(f"bruttofläche_STA_{idx}")]
                tech.vs = optimized_values[variables_order.index(f"vs_{idx}")]
            elif isinstance(tech, BiomassBoiler):
                tech.P_BMK = optimized_values[variables_order.index(f"P_BMK_{idx}")]
            elif isinstance(tech, CHP):
                tech.th_Leistung_BHKW = optimized_values[variables_order.index(f"th_Leistung_BHKW_{idx}")]
            elif isinstance(tech, Geothermal):
                tech.Fläche = optimized_values[variables_order.index(f"Fläche_{idx}")]
                tech.Bohrtiefe = optimized_values[variables_order.index(f"Bohrtiefe_{idx}")]
            elif isinstance(tech, WasteHeatPump):
                tech.Kühlleistung_Abwärme = optimized_values[variables_order.index(f"Kühlleistung_Abwärme_{idx}")]
            elif isinstance(tech, RiverHeatPump):
                tech.Wärmeleistung_FW_WP = optimized_values[variables_order.index(f"Wärmeleistung_FW_WP_{idx}")]

        return tech_order
    else:
        print("Optimierung nicht erfolgreich")
        print(result.message)


# Diese Klasse ist nocht fertig implementiert und die Nutzung auch noch nicht durchdacht, Wie muss dass ganze bilanziert werden?
class Photovoltaics:
    def __init__(self, name, TRY_data, Gross_area, Longitude, STD_Longitude, Latitude, East_West_collector_azimuth_angle=0, Collector_tilt_angle=36, Albedo=0.2):
        self.name = name
        self.TRY_data = TRY_data
        self.Gross_area = Gross_area
        self.Longitude = Longitude
        self.STD_Longitude = STD_Longitude
        self.Latitude = Latitude
        self.East_West_collector_azimuth_angle = East_West_collector_azimuth_angle
        self.Collector_tilt_angle = Collector_tilt_angle
        self.Albedo = Albedo

    def calc_WGK(self, Strommenge, q=1.05, r=1.03, T=20, BEW="Nein"):
        if Strommenge == 0:
            return 0

        self.Kosten_STA_spez = 100 # €/m²
        Nutzungsdauer = 20
        f_Inst, f_W_Insp, Bedienaufwand = 0.5, 1, 0

        self.Investitionskosten = self.Gross_area * self.Kosten_STA_spez

        self.A_N = annuität(self.Investitionskosten, Nutzungsdauer, f_Inst, f_W_Insp, Bedienaufwand, q, r, T)
        self.WGK = self.A_N / Strommenge

        Anteil_Förderung_BEW = 0.4
        Eigenanteil = 1 - Anteil_Förderung_BEW
        Investitionskosten_Gesamt_BEW = self.Investitionskosten * Eigenanteil
        Annuität_BEW = annuität(Investitionskosten_Gesamt_BEW, Nutzungsdauer, f_Inst, f_W_Insp, Bedienaufwand, q, r, T)
        self.WGK_BEW = Annuität_BEW / Strommenge

        self.WGK_BEW_BKF = self.WGK_BEW - 10  # €/MWh 10 Jahre

        if BEW == "Nein":
            return self.WGK
        elif BEW == "Ja":
            return self.WGK_BEW_BKF
        
    def calculate(self, q, r, T, BEW):
        # Hier fügen Sie die spezifische Logik für die PV-Berechnung ein
        yield_kWh, P_max, P_L = Calculate_PV(self.TRY_data, self.Gross_area, self.Longitude, self.STD_Longitude, self.Latitude, self.Albedo, self.East_West_collector_azimuth_angle, self.Collector_tilt_angle)

        WGK_PV = self.calc_WGK(yield_kWh/1000, q, r, T, BEW)

        results = { 
            'Strommenge': yield_kWh,
            'el_Leistung_L': P_L,
            'WGK': WGK_PV,
            'color': "red"
        }

        return results

# Idee Photovoltaisch-Thermische-Anlagen (PVT) mit zu simulieren
class PVT:
    def __init__(self, area):
        self.area = area

    def calculate(self):
        pass