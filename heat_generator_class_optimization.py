import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.interpolate import RegularGridInterpolator
import matplotlib.pyplot as plt
from math import pi

from heat_generators.Solarthermie import Berechnung_STA
from heat_generators.heat_generators import aw, Geothermie, BHKW, Biomassekessel, Gaskessel
from heat_generators.Wirtschaftlichkeitsbetrachtung import WGK_WP, WGK_BHKW, WGK_Biomassekessel, WGK_Gaskessel, WGK_STA

class WasteHeatPump:
    def __init__(self, name, Kühlleistung_Abwärme, Temperatur_Abwärme):
        self.name = name
        self.Kühlleistung_Abwärme = Kühlleistung_Abwärme
        self.Temperatur_Abwärme = Temperatur_Abwärme
    
    def calculate(self, Restlast_L, VLT_L, COP_data, el_Leistung_ges_L, Restwärmebedarf, Strombedarf_WP, \
                  Jahreswärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK, tech, Strompreis, q, r, T, duration):
       
        Wärmemenge_Abwärme, Strombedarf_Abwärme, Wärmeleistung_Abwärme_L, el_Leistung_Abwärme_L, max_Wärmeleistung_Abwärme = \
        aw(Restlast_L, VLT_L, self.Kühlleistung_Abwärme, self.Temperatur_Abwärme, COP_data, duration)

        el_Leistung_ges_L += el_Leistung_Abwärme_L
        Restlast_L -= Wärmeleistung_Abwärme_L

        Restwärmebedarf -= Wärmemenge_Abwärme
        Strombedarf_WP += Strombedarf_Abwärme

        Anteil_Abwärme = Wärmemenge_Abwärme / Jahreswärmebedarf

        data.append(Wärmeleistung_Abwärme_L)
        colors.append("grey")

        WGK_Abwärme = WGK_WP(max_Wärmeleistung_Abwärme, Wärmemenge_Abwärme, Strombedarf_Abwärme, tech, 0,
                                Strompreis, q, r, T)
        WGK_Gesamt += Wärmemenge_Abwärme * WGK_Abwärme

        Wärmemengen.append(Wärmemenge_Abwärme)
        Anteile.append(Anteil_Abwärme)
        WGK.append(WGK_Abwärme)

        return el_Leistung_ges_L, Restlast_L, Restwärmebedarf, Strombedarf_WP, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

class Geothermal:
    def __init__(self, name, Fläche, Bohrtiefe, Temperatur_Geothermie):
        self.name = name
        self.Fläche = Fläche
        self.Bohrtiefe = Bohrtiefe
        self.Temperatur_Geothermie = Temperatur_Geothermie
    
    def calculate(self, Restlast_L, VLT_L, COP_data,el_Leistung_ges_L, Restwärmebedarf, Strombedarf_WP, \
                    Jahreswärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK, \
                    tech, Strompreis, q, r, T, duration):
        # Hier fügen Sie die spezifische Logik für die Geothermie-Berechnung ein
        Wärmemenge_Geothermie, Strombedarf_Geothermie, Wärmeleistung_Geothermie_L, el_Leistung_Geothermie_L, \
        max_Wärmeleistung, Investitionskosten_Sonden = Geothermie(Restlast_L, VLT_L, self.Fläche, self.Bohrtiefe, self.Temperatur_Geothermie, COP_data, duration)

        spez_Investitionskosten_Erdsonden = Investitionskosten_Sonden / max_Wärmeleistung

        el_Leistung_ges_L -= el_Leistung_Geothermie_L
        Restlast_L -= Wärmeleistung_Geothermie_L

        Restwärmebedarf -= Wärmemenge_Geothermie
        Strombedarf_WP += Strombedarf_Geothermie

        Anteil_Geothermie = Wärmemenge_Geothermie / Jahreswärmebedarf

        data.append(Wärmeleistung_Geothermie_L)
        colors.append("blue")

        WGK_Geothermie = WGK_WP(max_Wärmeleistung, Wärmemenge_Geothermie, Strombedarf_Geothermie, tech,
                                spez_Investitionskosten_Erdsonden, Strompreis, q, r, T)
        WGK_Gesamt += Wärmemenge_Geothermie * WGK_Geothermie

        Wärmemengen.append(Wärmemenge_Geothermie)
        Anteile.append(Anteil_Geothermie)
        WGK.append(WGK_Geothermie)

        return el_Leistung_ges_L, Restlast_L, Restwärmebedarf, Strombedarf_WP, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

class CHP:
    def __init__(self, name, th_Leistung_BHKW):
        self.name = name
        self.th_Leistung_BHKW = th_Leistung_BHKW

    def calculate(self, Restlast_L, Gaspreis, Holzpreis, tech, Restwärmebedarf, \
                  Jahreswärmebedarf, data, colors, Strompreis, q, r, T, Wärmemengen, Anteile, WGK, \
                  el_Leistung_ges_L, Strommenge_BHKW, WGK_Gesamt, duration):
        
        Wärmeleistung_BHKW, Wärmeleistung_BHKW_L, el_Leistung_BHKW_L, Wärmemenge_BHKW, Strommenge_BHKW, \
        Brennstoffbedarf_BHKW = BHKW(self.th_Leistung_BHKW, Restlast_L, duration)

        if tech == "BHKW":
            Brennstoffpreis = Gaspreis
        elif tech == "Holzgas-BHKW":
            Brennstoffpreis = Holzpreis

        Restlast_L -= Wärmeleistung_BHKW_L
        Restwärmebedarf -= Wärmemenge_BHKW
        el_Leistung_ges_L += el_Leistung_BHKW_L

        Anteil_BHKW = Wärmemenge_BHKW / Jahreswärmebedarf

        data.append(Wärmeleistung_BHKW_L)
        colors.append("yellow")

        if tech == "BHKW":
            Brennstoffpreis = Gaspreis
        elif tech == "Holzgas-BHKW":
            Brennstoffpreis = Holzpreis

        wgk_BHKW = WGK_BHKW(Wärmeleistung_BHKW, Wärmemenge_BHKW, Strommenge_BHKW, tech, Brennstoffbedarf_BHKW,
                            Brennstoffpreis, Strompreis, q, r, T)
        WGK_Gesamt += Wärmemenge_BHKW * wgk_BHKW

        Wärmemengen.append(Wärmemenge_BHKW)
        Anteile.append(Anteil_BHKW)
        WGK.append(wgk_BHKW)

        return el_Leistung_ges_L, Restlast_L, Restwärmebedarf, Strommenge_BHKW, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

class BiomassBoiler:
    def __init__(self, name, P_BMK):
        self.name = name
        self.P_BMK = P_BMK

    def calculate(self, Restlast_L, Restwärmebedarf, Jahreswärmebedarf, data, \
                             colors, Holzpreis, q, r, T, WGK_Gesamt, Wärmemengen, Anteile, WGK, duration):
        # Hier fügen Sie die spezifische Logik für die Biomassekessel-Berechnung ein
        Wärmeleistung_BMK_L, Wärmemenge_BMK = Biomassekessel(Restlast_L, self.P_BMK, duration)

        Restlast_L -= Wärmeleistung_BMK_L
        Restwärmebedarf -= Wärmemenge_BMK

        Anteil_BMK = Wärmemenge_BMK / Jahreswärmebedarf

        data.append(Wärmeleistung_BMK_L)
        colors.append("green")

        Nutzungsgrad_BMK = 0.8
        Brennstoffbedarf_BMK = Wärmemenge_BMK/Nutzungsgrad_BMK
        WGK_BMK = WGK_Biomassekessel(self.P_BMK, Wärmemenge_BMK, Brennstoffbedarf_BMK, Holzpreis, q, r, T)
        WGK_Gesamt += Wärmemenge_BMK * WGK_BMK

        Wärmemengen.append(Wärmemenge_BMK)
        Anteile.append(Anteil_BMK)
        WGK.append(WGK_BMK)

        return Restlast_L, Restwärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

class GasBoiler:
    def __init__(self, name):
        self.name = name

    def calculate(self, Restlast_L, Restwärmebedarf, Jahreswärmebedarf, data, colors, Gaspreis, \
                         q, r, T, WGK_Gesamt, Wärmemengen, Anteile, WGK, Last_L, duration):
        # Hier fügen Sie die spezifische Logik für die Gaskessel-Berechnung ein
        Wärmemenge_GK, Wärmeleistung_GK_L, Gasbedarf = Gaskessel(Restlast_L, duration)
        P_max = max(Last_L) * 1
        WGK_GK = WGK_Gaskessel(P_max, Wärmemenge_GK, Gasbedarf, Gaspreis, q, r, T)

        Restlast_L -= Wärmeleistung_GK_L
        Restwärmebedarf -= Wärmemenge_GK

        Anteil_GK = Wärmemenge_GK / Jahreswärmebedarf

        data.append(Wärmeleistung_GK_L)
        colors.append("purple")

        WGK_Gesamt += Wärmemenge_GK * WGK_GK

        Wärmemengen.append(Wärmemenge_GK)
        Anteile.append(Anteil_GK)
        WGK.append(WGK_GK)

        return Restlast_L, Restwärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

class solar_thermal:
    def __init__(self, name, bruttofläche_STA, vs, Typ):
        self.name = name
        self.bruttofläche_STA = bruttofläche_STA
        self.vs = vs
        self.Typ = Typ

    def calculate(self, Last_L, VLT_L, RLT_L, TRY, time_steps, calc1, calc2, Restlast_L, \
                  Restwärmebedarf, Jahreswärmebedarf, data, colors, q, r, T, BEW, WGK_Gesamt, \
                    Wärmemengen, Anteile, WGK, duration):
        # Hier fügen Sie die spezifische Logik für die Solarthermie-Berechnung ein
        Wärmemenge_Solarthermie, Wärmeleistung_Solarthermie_L = Berechnung_STA(
            self.bruttofläche_STA, self.vs, self.Typ, Last_L, VLT_L, RLT_L, TRY, time_steps, calc1, calc2, duration)
        
        Restlast_L -= Wärmeleistung_Solarthermie_L
        Restwärmebedarf -= Wärmemenge_Solarthermie
        Anteil_Solarthermie = Wärmemenge_Solarthermie / Jahreswärmebedarf

        data.append(Wärmeleistung_Solarthermie_L)
        colors.append("red")

        WGK_Solarthermie = WGK_STA(self.bruttofläche_STA, self.vs, self.Typ, Wärmemenge_Solarthermie, q, r, T, BEW)
        WGK_Gesamt += Wärmemenge_Solarthermie * WGK_Solarthermie

        Wärmemengen.append(Wärmemenge_Solarthermie)
        Anteile.append(Anteil_Solarthermie)
        WGK.append(WGK_Solarthermie)

        return Restlast_L, Restwärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

### ###
def calculate_solar_thermal(bruttofläche_STA, vs, Typ, Last_L, VLT_L, RLT_L, TRY, \
                            time_steps, calc1, calc2, Restlast_L, Restwärmebedarf, Jahreswärmebedarf, \
                            data, colors, q, r, T, BEW, WGK_Gesamt, Wärmemengen, Anteile, WGK, duration):
    # Hier fügen Sie die spezifische Logik für die Solarthermie-Berechnung ein
    Wärmemenge_Solarthermie, Wärmeleistung_Solarthermie_L = Berechnung_STA(
        bruttofläche_STA, vs, Typ, Last_L, VLT_L, RLT_L, TRY, time_steps, calc1, calc2, duration)
    
    Restlast_L -= Wärmeleistung_Solarthermie_L
    Restwärmebedarf -= Wärmemenge_Solarthermie
    Anteil_Solarthermie = Wärmemenge_Solarthermie / Jahreswärmebedarf

    data.append(Wärmeleistung_Solarthermie_L)
    colors.append("red")

    WGK_Solarthermie = WGK_STA(bruttofläche_STA, vs, Typ, Wärmemenge_Solarthermie, q, r, T, BEW)
    WGK_Gesamt += Wärmemenge_Solarthermie * WGK_Solarthermie

    Wärmemengen.append(Wärmemenge_Solarthermie)
    Anteile.append(Anteil_Solarthermie)
    WGK.append(WGK_Solarthermie)

    return Restlast_L, Restwärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

def calculate_geothermal(Restlast_L, VLT_L, Fläche, Bohrtiefe, Temperatur_Geothermie, \
                         COP_data,el_Leistung_ges_L, Restwärmebedarf, Strombedarf_WP, \
                         Jahreswärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK, \
                         tech, Strompreis, q, r, T, duration):
    # Hier fügen Sie die spezifische Logik für die Geothermie-Berechnung ein
    Wärmemenge_Geothermie, Strombedarf_Geothermie, Wärmeleistung_Geothermie_L, el_Leistung_Geothermie_L, \
    max_Wärmeleistung, Investitionskosten_Sonden = Geothermie(Restlast_L, VLT_L, Fläche, Bohrtiefe, Temperatur_Geothermie, COP_data, duration)

    spez_Investitionskosten_Erdsonden = Investitionskosten_Sonden / max_Wärmeleistung

    el_Leistung_ges_L -= el_Leistung_Geothermie_L
    Restlast_L -= Wärmeleistung_Geothermie_L

    Restwärmebedarf -= Wärmemenge_Geothermie
    Strombedarf_WP += Strombedarf_Geothermie

    Anteil_Geothermie = Wärmemenge_Geothermie / Jahreswärmebedarf

    data.append(Wärmeleistung_Geothermie_L)
    colors.append("blue")

    WGK_Geothermie = WGK_WP(max_Wärmeleistung, Wärmemenge_Geothermie, Strombedarf_Geothermie, tech,
                            spez_Investitionskosten_Erdsonden, Strompreis, q, r, T)
    WGK_Gesamt += Wärmemenge_Geothermie * WGK_Geothermie

    Wärmemengen.append(Wärmemenge_Geothermie)
    Anteile.append(Anteil_Geothermie)
    WGK.append(WGK_Geothermie)

    return el_Leistung_ges_L, Restlast_L, Restwärmebedarf, Strombedarf_WP, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

def calculate_wasteheat(Restlast_L, VLT_L, Kühlleistung_Abwärme, Temperatur_Abwärme, \
                         COP_data, el_Leistung_ges_L, Restwärmebedarf, Strombedarf_WP, \
                         Jahreswärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK, \
                         tech, Strompreis, q, r, T, duration):
    
    Wärmemenge_Abwärme, Strombedarf_Abwärme, Wärmeleistung_Abwärme_L, el_Leistung_Abwärme_L, \
                max_Wärmeleistung_Abwärme, Betriebsstunden_Abwärme = aw(Restlast_L, VLT_L, Kühlleistung_Abwärme,
                                                                        Temperatur_Abwärme, COP_data, duration)

    el_Leistung_ges_L += el_Leistung_Abwärme_L
    Restlast_L -= Wärmeleistung_Abwärme_L

    Restwärmebedarf -= Wärmemenge_Abwärme
    Strombedarf_WP += Strombedarf_Abwärme

    Anteil_Abwärme = Wärmemenge_Abwärme / Jahreswärmebedarf

    data.append(Wärmeleistung_Abwärme_L)
    colors.append("grey")

    WGK_Abwärme = WGK_WP(max_Wärmeleistung_Abwärme, Wärmemenge_Abwärme, Strombedarf_Abwärme, tech, 0,
                            Strompreis, q, r, T)
    WGK_Gesamt += Wärmemenge_Abwärme * WGK_Abwärme

    Wärmemengen.append(Wärmemenge_Abwärme)
    Anteile.append(Anteil_Abwärme)
    WGK.append(WGK_Abwärme)

    return el_Leistung_ges_L, Restlast_L, Restwärmebedarf, Strombedarf_WP, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

def calculate_chp(Restlast_L, th_Leistung_BHKW, Gaspreis, Holzpreis, tech, Restwärmebedarf, \
                  Jahreswärmebedarf, data, colors, Strompreis, q, r, T, Wärmemengen, Anteile, WGK, \
                  el_Leistung_ges_L, Strommenge_BHKW, WGK_Gesamt, duration):
    
    Wärmeleistung_BHKW, Wärmeleistung_BHKW_L, el_Leistung_BHKW_L, Wärmemenge_BHKW, Strommenge_BHKW, \
    Brennstoffbedarf_BHKW = BHKW(th_Leistung_BHKW, Restlast_L, duration)

    if tech == "BHKW":
        Brennstoffpreis = Gaspreis
    elif tech == "Holzgas-BHKW":
        Brennstoffpreis = Holzpreis

    Restlast_L -= Wärmeleistung_BHKW_L
    Restwärmebedarf -= Wärmemenge_BHKW
    el_Leistung_ges_L += el_Leistung_BHKW_L

    Anteil_BHKW = Wärmemenge_BHKW / Jahreswärmebedarf

    data.append(Wärmeleistung_BHKW_L)
    colors.append("yellow")

    if tech == "BHKW":
        Brennstoffpreis = Gaspreis
    elif tech == "Holzgas-BHKW":
        Brennstoffpreis = Holzpreis

    wgk_BHKW = WGK_BHKW(Wärmeleistung_BHKW, Wärmemenge_BHKW, Strommenge_BHKW, tech, Brennstoffbedarf_BHKW,
                        Brennstoffpreis, Strompreis, q, r, T)
    WGK_Gesamt += Wärmemenge_BHKW * wgk_BHKW

    Wärmemengen.append(Wärmemenge_BHKW)
    Anteile.append(Anteil_BHKW)
    WGK.append(wgk_BHKW)

    return el_Leistung_ges_L, Restlast_L, Restwärmebedarf, Strommenge_BHKW, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

def calculate_biomass_boiler(Restlast_L, P_BMK, Restwärmebedarf, Jahreswärmebedarf, data, \
                             colors, Holzpreis, q, r, T, WGK_Gesamt, Wärmemengen, Anteile, WGK, duration):
    # Hier fügen Sie die spezifische Logik für die Biomassekessel-Berechnung ein
    Wärmeleistung_BMK_L, Wärmemenge_BMK = Biomassekessel(Restlast_L, P_BMK, duration)

    Restlast_L -= Wärmeleistung_BMK_L
    Restwärmebedarf -= Wärmemenge_BMK

    Anteil_BMK = Wärmemenge_BMK / Jahreswärmebedarf

    data.append(Wärmeleistung_BMK_L)
    colors.append("green")

    Nutzungsgrad_BMK = 0.8
    Brennstoffbedarf_BMK = Wärmemenge_BMK/Nutzungsgrad_BMK
    WGK_BMK = WGK_Biomassekessel(P_BMK, Wärmemenge_BMK, Brennstoffbedarf_BMK, Holzpreis, q, r, T)
    WGK_Gesamt += Wärmemenge_BMK * WGK_BMK

    Wärmemengen.append(Wärmemenge_BMK)
    Anteile.append(Anteil_BMK)
    WGK.append(WGK_BMK)

    return Restlast_L, Restwärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

def calculate_gas_boiler(Restlast_L, Restwärmebedarf, Jahreswärmebedarf, data, colors, Gaspreis, \
                         q, r, T, WGK_Gesamt, Wärmemengen, Anteile, WGK, Last_L, duration):
    # Hier fügen Sie die spezifische Logik für die Gaskessel-Berechnung ein
    Wärmemenge_GK, Wärmeleistung_GK_L, Gasbedarf = Gaskessel(Restlast_L, duration)
    P_max = max(Last_L) * 1
    WGK_GK = WGK_Gaskessel(P_max, Wärmemenge_GK, Gasbedarf, Gaspreis, q, r, T)

    Restlast_L -= Wärmeleistung_GK_L
    Restwärmebedarf -= Wärmemenge_GK

    Anteil_GK = Wärmemenge_GK / Jahreswärmebedarf

    data.append(Wärmeleistung_GK_L)
    colors.append("purple")

    WGK_Gesamt += Wärmemenge_GK * WGK_GK

    Wärmemengen.append(Wärmemenge_GK)
    Anteile.append(Anteil_GK)
    WGK.append(WGK_GK)

    return Restlast_L, Restwärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK

def calculate_factors(Kapitalzins, Preissteigerungsrate, Betrachtungszeitraum):
    q = 1 + Kapitalzins / 100
    r = 1 + Preissteigerungsrate / 100
    T = Betrachtungszeitraum
    return q, r, T

def Berechnung_Erzeugermix(time_steps, calc1, calc2, bruttofläche_STA, vs, Typ, Fläche, Bohrtiefe, Temperatur_Geothermie, P_BMK, Gaspreis,
                           Strompreis, Holzpreis, initial_data, TRY, tech_order, BEW, th_Leistung_BHKW, Kühlleistung_Abwärme,
                           Temperatur_Abwärme, COP_data, Kapitalzins=5, Preissteigerungsrate=3, Betrachtungszeitraum=20):

    # Kapitalzins und Preissteigerungsrate in % -> Umrechung in Zinsfaktor und Preissteigerungsfaktor
    q, r, T = calculate_factors(Kapitalzins, Preissteigerungsrate, Betrachtungszeitraum)
    Last_L, VLT_L, RLT_L = initial_data

    duration = np.diff(time_steps[0:2]) / np.timedelta64(1, 'h')
    duration = duration[0]

    Jahreswärmebedarf = (np.sum(Last_L)/1000) * duration

    Restlast_L, Restwärmebedarf, WGK_Gesamt = Last_L.copy(), Jahreswärmebedarf, 0
    data, colors, Wärmemengen, Anteile, WGK = [], [], [], [], []

    Strombedarf_WP, Strommenge_BHKW = 0, 0
    el_Leistung_ges_L = np.zeros_like(Last_L)

    # zunächst Berechnung der Erzeugung
    for tech in tech_order:
        if tech == "Solarthermie":
            Restlast_L, Restwärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK = \
                calculate_solar_thermal(bruttofläche_STA, vs, Typ, Last_L, VLT_L, RLT_L, TRY, time_steps, calc1, calc2, Restlast_L, \
                                        Restwärmebedarf, Jahreswärmebedarf, data, colors, q, r, T, BEW, WGK_Gesamt, Wärmemengen, Anteile, WGK, duration)
        
        elif tech == "Abwärme" or tech == "Abwasserwärme":
            el_Leistung_ges_L, Restlast_L, Restwärmebedarf, Strombedarf_WP, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK = \
                calculate_wasteheat(Restlast_L, VLT_L, Kühlleistung_Abwärme, Temperatur_Abwärme, COP_data, el_Leistung_ges_L, \
                                    Restwärmebedarf, Strombedarf_WP, Jahreswärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK, \
                                    tech, Strompreis, q, r, T, duration)
            
        elif tech == "Geothermie":
            el_Leistung_ges_L, Restlast_L, Restwärmebedarf, Strombedarf_WP, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK = \
                calculate_geothermal(Restlast_L, VLT_L, Fläche, Bohrtiefe, Temperatur_Geothermie, COP_data,el_Leistung_ges_L, \
                                     Restwärmebedarf, Strombedarf_WP, Jahreswärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK, \
                                     tech, Strompreis, q, r, T, duration)
            
        elif tech == "BHKW" or tech == "Holzgas-BHKW":
            el_Leistung_ges_L, Restlast_L, Restwärmebedarf, Strommenge_BHKW, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK = \
                calculate_chp(Restlast_L, th_Leistung_BHKW, Gaspreis, Holzpreis, tech, Restwärmebedarf, Jahreswärmebedarf, data, colors, \
                              Strompreis, q, r, T, Wärmemengen, Anteile, WGK, el_Leistung_ges_L, Strommenge_BHKW, WGK_Gesamt, duration)
            
        elif tech == "Biomassekessel":
            Restlast_L, Restwärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK = calculate_biomass_boiler(
                Restlast_L, P_BMK, Restwärmebedarf, Jahreswärmebedarf, data, colors, Holzpreis, q, r, T, WGK_Gesamt, Wärmemengen, Anteile, WGK, duration)
            
        elif tech == "Gaskessel":
            Restlast_L, Restwärmebedarf, data, colors, WGK_Gesamt, Wärmemengen, Anteile, WGK = calculate_gas_boiler(
                Restlast_L, Restwärmebedarf, Jahreswärmebedarf, data, colors, Gaspreis, q, r, T, WGK_Gesamt, Wärmemengen, Anteile, WGK, Last_L, duration)

    WGK_Gesamt /= Jahreswärmebedarf
    
    return WGK_Gesamt, Jahreswärmebedarf, Last_L, data, tech_order, colors, Wärmemengen, WGK, Anteile

def optimize_mix(initial_values, time_steps, calc1, calc2, initial_data, TRY, COP_data, Typ, Fläche, Bohrtiefe, Temperatur_Geothermie, Gaspreis, Strompreis, Holzpreis, BEW, tech_order, Kühlleistung_Abwärme, Temperatur_Abwärme):
    def objective(variables):
        bruttofläche_STA, vs, P_BMK, th_Leistung_BHKW = variables

        WGK_Gesamt, Jahreswärmebedarf, Last_L, data_L, data_labels_L, colors_L, Wärmemengen, WGK, Anteile = \
            Berechnung_Erzeugermix(time_steps, calc1, calc2, bruttofläche_STA, vs, Typ, Fläche, Bohrtiefe, Temperatur_Geothermie, P_BMK, Gaspreis, Strompreis, \
                                        Holzpreis, initial_data, TRY, tech_order, BEW, \
                                        th_Leistung_BHKW, Kühlleistung_Abwärme, Temperatur_Abwärme, COP_data)
        
        return WGK_Gesamt

    # Optimierung durchführen
    result = minimize(objective, initial_values, method='SLSQP', bounds=[(0, 1000), (0, 100), (0, 500), (0, 500)], options={'maxiter': 1000})
    #result = minimize(objective, initial_values, method='L-BFGS-B', bounds=[(0, 1000), (0, 1000), (0, 1000), (0, 1000)], options={'maxiter': 1000})
    #result = minimize(objective, initial_values, method='TNC', bounds=[(0, 1000), (0, 100), (0, 500), (0, 500)], options={'maxiter': 1000})

    if result.success:
        optimized_values = result.x
        optimized_WGK_Gesamt = objective(optimized_values)
        print(f"Optimierte Werte: {optimized_values}")
        print(f"Minimale Wärmegestehungskosten: {optimized_WGK_Gesamt:.2f} €/MWh")
        return optimized_values
    else:
        print("Optimierung nicht erfolgreich")
        print(result.message)
