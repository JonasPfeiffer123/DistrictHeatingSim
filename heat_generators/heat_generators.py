import numpy as np
from scipy.interpolate import RegularGridInterpolator
import matplotlib.pyplot as plt
from math import pi

def COP_WP(VLT_L, QT, COP_data):
    # Interpolationsformel für den COP
    values = COP_data  # np.genfromtxt('Kennlinien WP.csv', delimiter=';')
    row_header = values[0, 1:]  # Vorlauftempertauren
    col_header = values[1:, 0]  # Quelltemperaturen
    values = values[1:, 1:]
    f = RegularGridInterpolator((col_header, row_header), values, method='linear')
    # technische Grenze der Wärmepumpe ist Temperaturhub von 75 °C
    VLT_L = np.minimum(VLT_L, 75)
    QT_array = np.full_like(VLT_L, QT)

    COP_L = f(np.column_stack((QT_array, VLT_L)))
    return COP_L, VLT_L

def Berechnung_WP(Kühlleistung, QT, VLT_L, COP_data):
    COP_L, VLT_L = COP_WP(VLT_L, QT, COP_data)
    Wärmeleistung_L = Kühlleistung / (1 - (1 / COP_L))
    el_Leistung_L = Wärmeleistung_L - Kühlleistung
    return Wärmeleistung_L, el_Leistung_L

# Änderung Kühlleistung und Temperatur zu Numpy-Array in aw sowie vor- und nachgelagerten Funktionen
def aw(Last_L, VLT_L, Kühlleistung, Temperatur, COP_data):
    if Kühlleistung == 0:
        return 0, 0, np.zeros_like(Last_L), np.zeros_like(VLT_L), 0

    Wärmeleistung_L, el_Leistung_L = Berechnung_WP(Kühlleistung, Temperatur, VLT_L, COP_data)

    mask = Last_L >= Wärmeleistung_L
    Wärmemenge = np.sum(np.where(mask, Wärmeleistung_L / 1000, 0))
    Strombedarf = np.sum(np.where(mask, el_Leistung_L / 1000, 0))
    Betriebsstunden = np.sum(mask)

    max_Wärmeleistung = np.max(Wärmeleistung_L)

    return Wärmemenge, Strombedarf, Wärmeleistung_L, el_Leistung_L, max_Wärmeleistung, Betriebsstunden

def Geothermie(Last_L, VLT_L, Fläche, Bohrtiefe, Quelltemperatur, COP_data, spez_Bohrkosten=120, spez_Entzugsleistung=50,
               Vollbenutzungsstunden=2400, Abstand_Sonden=6):
    if Fläche == 0 or Bohrtiefe == 0:
        return 0, 0, np.zeros_like(Last_L), np.zeros_like(VLT_L), 0, 0

    Fläche_Sonde = (pi/4) * (2*Abstand_Sonden)**2
    Anzahl_Sonden = round(Fläche / Fläche_Sonde, 0)  # 22
    Anzahl_Sonden = 40

    Entzugsleistung_2400 = Bohrtiefe * spez_Entzugsleistung * Anzahl_Sonden / 1000
    # kW bei 2400 h, 22 Sonden, 50 W/m: 220 kW
    Entzugswärmemenge = Entzugsleistung_2400 * Vollbenutzungsstunden / 1000  # MWh
    Investitionskosten_Sonden = Bohrtiefe * spez_Bohrkosten * Anzahl_Sonden

    COP_L, VLT_WP = COP_WP(VLT_L, Quelltemperatur, COP_data)

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

        # Bestimmen des Anteils, der tatsächlich genutzt wird
        Anteil = np.minimum(1, Last_L / Wärmeleistung_L)

        # Berechnen der tatsächlichen Werte
        Wärmeleistung_tat_L = Wärmeleistung_L * Anteil
        el_Leistung_tat_L = el_Leistung_L * Anteil
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

    max_Wärmeleistung = max(Wärmeleistung_tat_L)
    JAZ = Wärmemenge / Strombedarf

    return Wärmemenge, Strombedarf, Wärmeleistung_tat_L, el_Leistung_tat_L, max_Wärmeleistung, Investitionskosten_Sonden

def BHKW(el_Leistung_Soll, Last_L, el_Wirkungsgrad=0.33, KWK_Wirkungsgrad=0.9):
    # Berechnen der thermischen Effizienz
    thermischer_Wirkungsgrad = KWK_Wirkungsgrad - el_Wirkungsgrad

    # Berechnen der Wärmeleistung des BHKW
    Wärmeleistung_BHKW = el_Leistung_Soll / el_Wirkungsgrad * thermischer_Wirkungsgrad

    # Berechnen der Strom- und Wärmemenge des BHKW
    Wärmeleistung_BHKW_L = np.where(Last_L >= Wärmeleistung_BHKW, Wärmeleistung_BHKW, Last_L)
    el_Leistung_BHKW_L = np.where(Last_L >= Wärmeleistung_BHKW, el_Leistung_Soll,
                                  el_Leistung_Soll * (Last_L / Wärmeleistung_BHKW))
    Wärmemenge_BHKW = np.sum(Wärmeleistung_BHKW_L / 1000)
    Strommenge_BHKW = np.sum(el_Leistung_BHKW_L / 1000)

    # Berechnen des Brennstoffbedarfs
    Brennstoffbedarf_BHKW = (Wärmemenge_BHKW + Strommenge_BHKW) / KWK_Wirkungsgrad

    # Rückgabe der berechneten Werte
    return Wärmeleistung_BHKW, Wärmeleistung_BHKW_L, el_Leistung_BHKW_L, Wärmemenge_BHKW, Strommenge_BHKW, \
        Brennstoffbedarf_BHKW

def Biomassekessel(Last_L, P_BMK):
    Wärmeleistung_BMK_L = np.where(Last_L >= P_BMK, P_BMK, Last_L)
    Wärmemenge_BMK = np.sum(Wärmeleistung_BMK_L / 1000)

    return Wärmeleistung_BMK_L, Wärmemenge_BMK
def Gaskessel(Last_L, Nutzungsgrad=0.9):
    Erzeugung_L = np.maximum(Last_L, 0)
    Wärmemenge = np.sum(Erzeugung_L) / 1000
    Brennstoffbedarf = Wärmemenge / Nutzungsgrad

    return Wärmemenge, Erzeugung_L, Brennstoffbedarf