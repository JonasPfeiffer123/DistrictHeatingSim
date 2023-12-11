# Berechnungsprogramm Fernwärme-Erzeugermix
# Import Bibliotheken
import numpy as np
from heat_generators.Solarthermie import Berechnung_STA
from heat_generators.heat_generators import aw, Geothermie, BHKW, Biomassekessel, Gaskessel
from heat_generators.Wirtschaftlichkeitsbetrachtung import WGK_WP, WGK_BHKW, WGK_Biomassekessel, WGK_Gaskessel, WGK_STA

def calculate_factors(Kapitalzins, Preissteigerungsrate, Betrachtungszeitraum):
    q = 1 + Kapitalzins / 100
    r = 1 + Preissteigerungsrate / 100
    T = Betrachtungszeitraum
    return q, r, T

def Berechnung_Erzeugermix(time_steps, calc1, calc2, bruttofläche_STA, vs, Typ, Fläche, Bohrtiefe, Temperatur_Geothermie, P_BMK, Gaspreis,
                           Strompreis, Holzpreis, initial_data, TRY_filename, tech_order, BEW, th_Leistung_BHKW, Kühlleistung_Abwärme,
                           Temperatur_Abwärme, COP_data, Kapitalzins=5, Preissteigerungsrate=3,
                           Betrachtungszeitraum=20):

    # Kapitalzins und Preissteigerungsrate in % -> Umrechung in Zinsfaktor und Preissteigerungsfaktor
    q, r, T = calculate_factors(Kapitalzins, Preissteigerungsrate, Betrachtungszeitraum)
    Last_L, VLT_L, RLT_L = initial_data
    Jahreswärmebedarf = np.sum(Last_L)/1000

    Restlast_L, Restwärmebedarf, WGK_Gesamt = Last_L.copy(), Jahreswärmebedarf, 0
    data, colors, Wärmemengen, Anteile, WGK = [], [], [], [], []

    Strombedarf_WP, Strommenge_BHKW = 0, 0
    el_Leistung_ges_L = np.zeros_like(Last_L)

    # zunächst Berechnung der Erzeugung
    for tech in tech_order:
        if tech == "Solarthermie":
            Wärmemenge_Solarthermie, Wärmeleistung_Solarthermie_L = Berechnung_STA(bruttofläche_STA, vs, Typ, Last_L, VLT_L, RLT_L, TRY_filename, time_steps, calc1, calc2)

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
            #print("Wärmemenge Solarthermie: " + str(round(Wärmemenge_Solarthermie, 2)) + " MWh")
            #print("Anteil Solarthermie an Wärmeversorgung: " + str(round(Anteil_Solarthermie, 3)))
            #print("Wärmegestehungskosten Solarthermie: " + str(round(WGK_Solarthermie, 2)) + " €/MWh")

            Deckungsanteil = Wärmemenge_Solarthermie / Jahreswärmebedarf * 100  # %

        elif tech == "Abwärme":
            Wärmemenge_Abwärme, Strombedarf_Abwärme, Wärmeleistung_Abwärme_L, el_Leistung_Abwärme_L, \
                max_Wärmeleistung_Abwärme, Betriebsstunden_Abwärme = aw(Restlast_L, VLT_L, Kühlleistung_Abwärme,
                                                                        Temperatur_Abwärme, COP_data)

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

            #print("Wärmemenge Abwärme: " + str(round(Wärmemenge_Abwärme, 2)) + " MWh")
            #print("Anteil Abwärme an Wärmeversorgung: " + str(round(Anteil_Abwärme, 3)))
            #print("Wärmegestehungskosten Abwärme: " + str(round(WGK_Abwärme, 2)) + " €/MWh")

        elif tech == "Geothermie":
            Wärmemenge_Geothermie, Strombedarf_Geothermie, Wärmeleistung_Geothermie_L, el_Leistung_Geothermie_L, \
                max_Wärmeleistung, Investitionskosten_Sonden = Geothermie(Restlast_L, VLT_L, Fläche, Bohrtiefe,
                                                                          Temperatur_Geothermie, COP_data)
            spez_Investitionskosten_Erdsonden = Investitionskosten_Sonden / max_Wärmeleistung

            el_Leistung_ges_L += el_Leistung_Geothermie_L
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
            #print("Wärmemenge Geothermie: " + str(round(Wärmemenge_Geothermie, 2)) + " MWh")
            #print("Anteil Geothermie an Wärmeversorgung: " + str(round(Anteil_Geothermie, 3)))
            #print("Wärmegestehungskosten Geothermie: " + str(round(WGK_Geothermie, 2)) + " €/MWh")

        elif tech == "BHKW" or tech == "Holzgas-BHKW":
            Wärmeleistung_BHKW, Wärmeleistung_BHKW_L, el_Leistung_BHKW_L, Wärmemenge_BHKW, Strommenge_BHKW, \
                Brennstoffbedarf_BHKW = BHKW(th_Leistung_BHKW, Restlast_L)

            Restlast_L -= Wärmeleistung_BHKW_L
            Restwärmebedarf -= Wärmemenge_BHKW

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
            #print("Wärmemenge BHKW: " + str(round(Wärmemenge_BHKW, 2)) + " MWh")
            #print("Anteil BHKW an Wärmeversorgung: " + str(round(Anteil_BHKW, 3)))
            #print("Wärmegestehungskosten BHKW: " + str(round(wgk_BHKW, 2)) + " €/MWh")

        elif tech == "Gaskessel":
            Wärmemenge_GK, Wärmeleistung_GK_L, Gasbedarf = Gaskessel(Restlast_L)
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
            #print("Wärmemenge Gaskessel: " + str(round(Wärmemenge_GK, 2)) + " MWh")
            #print("Anteil Erdgas an Wärmeversorgung: " + str(round(Anteil_GK, 3)))
            #print("Wärmegestehungskosten Gaskessel: " + str(round(WGK_GK, 2)) + " €/MWh")

        elif tech == "Biomassekessel":
            Wärmeleistung_BMK_L, Wärmemenge_BMK = Biomassekessel(Restlast_L, P_BMK)

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
            #print("Wärmemenge Biomassekessel: " + str(round(Wärmemenge_BMK, 2)) + " MWh")
            #print("Anteil Biomassekessel an Wärmeversorgung: " + str(round(Anteil_BMK, 3)))
            #print("Wärmegestehungskosten Biomassekessel: " + str(round(WGK_BMK, 2)) + " €/MWh")

    WGK_Gesamt /= Jahreswärmebedarf
    # print("Wärmegestehungskosten Gesamt: " + str(round(WGK_Gesamt, 2)) + " €/MWh")

    #if BEW == "Ja":
    #    WGK_Gesamt = 0
    
    return WGK_Gesamt, Jahreswärmebedarf, Last_L, data, tech_order, colors, Wärmemengen, WGK, Anteile