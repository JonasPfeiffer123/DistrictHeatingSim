### Erstellt von Jonas Pfeiffer ###

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from heat_generators import Solarthermie, heat_generator_classes
from utilities.test_reference_year import import_TRY

import numpy as np

import matplotlib.pyplot as plt

# defines the map path
def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist, ist der Basispfad der Temp-Ordner, wo PyInstaller alles extrahiert
        base_path = sys._MEIPASS
    else:
        # Wenn die Anwendung nicht eingefroren ist, ist der Basispfad der Ordner, in dem die Hauptdatei liegt
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

# Test Annuitätsberechnung
def test_annuität():
    # Investition in €
    A0 = 10000

    # Technische Nutzungsdauer in Jahren
    TN = 20

    # Kostenfaktor Installationskosten als Anteil der Investitionskosten
    f_Inst = 0.03

    # Kostenfaktor Wartungs- und Instandhaltungskosten als Anteil der Investitionskosten
    f_W_Insp = 0.02

    # Bedienaufwand in Stunden (Stundensatz aktuell fix in der Funktion mit 45 €/h hinterlegt)
    # muss unbedingt noch weg von der fixen Definition
    Bedienaufwand = 10

    # Kapitalzinsfaktor 
    q = 1.05 # 5 %

    # Preissteigerungsfaktor
    r = 1.03 # 3 %

    # Betrachtungszeitraum in Jahren
    T = 20

    # Energiebedarf / Brennstoffbedarf in z.B. kWh
    Energiebedarf = 15000

    # Energiekosten in z.B. €/kWh --> Einheit Energie muss mit der des Energiebedarfs übereinstimmen
    Energiekosten = 0.15

    # Erlöse, könnte z.B. Stromverkauf aus BHKW sein oder auch Wärmeverkauf, kann auf 0 gesetzt werden, dann nur Aussage über Höhe der Kosten
    E1 = 0

    A_N = heat_generator_classes.annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand, q, r, T, Energiebedarf, Energiekosten, E1)

    print(f"Annuität: {A_N:.2f} €")

def test_gas_boiler():
    # spez Investitionskosten in €/kW
    gBoiler = heat_generator_classes.GasBoiler(name="Gas_Boiler_1", spez_Investitionskosten=25)

    # Lastgang, z.B. in kW, muss derzeitig für korrekte wirtschaftliche Betrachtung Länge von 8760 haben
    min_last = 50
    max_last = 400
    Last_L = np.random.randint(min_last, max_last, 8760)

    # Dauer Zeitschritte 1 h
    duration = 1

    # Nutzungsgrad Gaskessel
    Nutzungsgrad = 0.9

    # Die Wärmemenge und der Brennstoffbedarf wird in der nächstgrößeren Einheit zurückgegeben, hier MWh
    Wärmemenge, Erzeugung_L, Brennstoffbedarf = gBoiler.Gaskessel(Last_L, duration, Nutzungsgrad)
    print(f"Wärmemenge: {Wärmemenge:.2f} MWh, Erzeugung: {Erzeugung_L}, Brennstoffbedarf: {Brennstoffbedarf:.2f} MWh")

    P_max = max(Erzeugung_L) * 1.2
    Brennstoffkosten = 60 # hier €/MWh

    q = 1.05
    r = 1.03
    T = 20
    BEW = "Nein"
    Stundensatz = 45

    WGK = gBoiler.WGK(P_max, Wärmemenge, Brennstoffbedarf, Brennstoffkosten, q, r, T, BEW, Stundensatz)
    print(f"Wärmegestehungskosten Gaskessel: {WGK:.2f} €/MWh")

def test_biomass_boiler():
    bBoiler = heat_generator_classes.BiomassBoiler(name="Biomasss_Boiler_1", P_BMK=200, Größe_Holzlager=20, spez_Investitionskosten=200, spez_Investitionskosten_Holzlager=400)

    # Lastgang, z.B. in kW, muss derzeitig für korrekte wirtschaftliche Betrachtung Länge von 8760 haben
    min_last = 50
    min_last = 50
    max_last = 400
    Last_L = np.random.randint(min_last, max_last, 8760)

    # Dauer Zeitschritte 1 h
    duration = 1

    Wärmeleistung_BMK_L, Wärmemenge_BMK = bBoiler.Biomassekessel(Last_L, duration)
    print(f"Wärmeleistung BMK: {Wärmeleistung_BMK_L} kW, Wärmemenge BMK: {Wärmemenge_BMK:.2f} MWh")

    # muss noch angepasst werden, dass Nutzungsgrad mit definiert wird
    Nutzungsgrad_BMK = 0.8
    Brennstoffbedarf_BMK = Wärmemenge_BMK/Nutzungsgrad_BMK

    Holzpreis = 60 # €/MWh
    q = 1.05
    r = 1.03
    T = 20
    BEW = "Nein"
    Stundensatz = 45

    WGK = bBoiler.WGK(Wärmemenge_BMK, Brennstoffbedarf_BMK, Holzpreis, q, r, T, BEW, Stundensatz)
    print(f"Wärmegestehungskosten Biomassekessel: {WGK:.2f} €/MWh")

def test_chp():
    chp = heat_generator_classes.CHP(name="BHKW", th_Leistung_BHKW=100, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850)

    # Lastgang, z.B. in kW, muss derzeitig für korrekte wirtschaftliche Betrachtung Länge von 8760 haben
    min_last = 50
    min_last = 50
    max_last = 400
    Last_L = np.random.randint(min_last, max_last, 8760)

    # Dauer Zeitschritte 1 h
    duration = 1

    el_Wirkungsgrad = 0.33
    KWK_Wirkungsgrad = 0.9

    Wärmeleistung_BHKW_L, el_Leistung_BHKW_L, Wärmemenge_BHKW, Strommenge_BHKW, Brennstoffbedarf_BHKW = chp.BHKW(Last_L, duration, el_Wirkungsgrad, KWK_Wirkungsgrad)
    print(f"Wärmeleistung BHkW: {Wärmeleistung_BHKW_L} kW, elektrische Leistung BHKW: {el_Leistung_BHKW_L} kW, Wärmemenge BHKW: {Wärmemenge_BHKW:.2f} MWh, Strommenge BHKW: {Strommenge_BHKW:.2f} MWh, Brennstoffbedarf BHKW: {Brennstoffbedarf_BHKW:.2f} MWh")

    Strompreis = 150 # €/MWh
    Gaspreis = 70 # €/MWh
    Holzpreis = 60 # €/MWh

    if chp.name == "BHKW":
        Brennstoffpreis = Gaspreis
    elif chp.name == "Holzgas-BHKW":
        Brennstoffpreis = Holzpreis

    q = 1.05
    r = 1.03
    T = 20
    BEW = "Nein"
    Stundensatz = 45

    WGK= chp.WGK(Wärmemenge_BHKW, Strommenge_BHKW, Brennstoffbedarf_BHKW, Brennstoffpreis, Strompreis, q, r, T, BEW, Stundensatz)
    print(f"Wärmegestehungskosten BHKW: {WGK:.2f} €/MWh")

def test_solar_thermal():
    solarThermal = heat_generator_classes.SolarThermal(name="STA", bruttofläche_STA=200, vs=20, Typ="Vakuumröhrenkollektor", kosten_speicher_spez=750, kosten_fk_spez=430, kosten_vrk_spez=590, Tsmax=90, Longitude=-14.4222, 
                 STD_Longitude=-15, Latitude=51.1676, East_West_collector_azimuth_angle=0, Collector_tilt_angle=36, Tm_rl=60, Qsa=0, Vorwärmung_K=8, DT_WT_Solar_K=5, DT_WT_Netz_K=5)
    
    # Lastgang, z.B. in kW, muss derzeitig für korrekte wirtschaftliche Betrachtung Länge von 8760 haben
    min_last = 50
    min_last = 50
    max_last = 400
    Last_L = np.random.randint(min_last, max_last, 8760)

    # Arrays für Vor- und Rücklauftemperatur
    VLT_L, RLT_L = np.full(8760, 80), np.full(8760, 55)

    # Dateiname Testreferenzjahr für Wetterdaten, Dateiname muss ggf. angepasst werden
    TRY = import_TRY(get_resource_path("heat_requirement/TRY_511676144222/TRY2015_511676144222_Jahr.dat"))

    # Angaben zum zu betrchtende Zeitraum
    # Erstelle ein Array mit stündlichen Zeitwerten für ein Jahr
    start_date = np.datetime64('2019-01-01')
    end_date = np.datetime64('2020-01-01', 'D')  # Enddatum ist exklusiv, daher 'D' für Tage

    # Erstelle das Array mit stündlichen Zeitwerten für ein Jahr
    time_steps = np.arange(start_date, end_date, dtype='datetime64[h]')
    calc1 = 0
    calc2 = 8760

    duration = 1

    # Die Berechnung der Solarthermie erfolgt niht in der Klasse sondern in einer externen Funktion
    Wärmemenge, Wärmeleistung_Solarthermie_L, Speicherladung_L, Speicherfüllstand_L = Solarthermie.Berechnung_STA(solarThermal.bruttofläche_STA, solarThermal.vs, solarThermal.Typ, Last_L, VLT_L, RLT_L, 
                                                                                                        TRY, time_steps, calc1, calc2, duration, solarThermal.Tsmax, solarThermal.Longitude, solarThermal.STD_Longitude, 
                                                                                                        solarThermal.Latitude, solarThermal.East_West_collector_azimuth_angle, solarThermal.Collector_tilt_angle, solarThermal.Tm_rl, 
                                                                                                        solarThermal.Qsa, solarThermal.Vorwärmung_K, solarThermal.DT_WT_Solar_K, solarThermal.DT_WT_Netz_K)

    print(f"Wärmemenge Solarthermie: {Wärmemenge} MWh, Wärmeleistung Solarthermie: {Wärmeleistung_Solarthermie_L} kW, Speicherladung Solarthermie: {Speicherladung_L}, Speicherfüllstand: {Speicherfüllstand_L}")

    q = 1.05
    r = 1.03
    T = 20
    BEW = "Nein"
    Stundensatz = 45

    WGK = solarThermal.calc_WGK(Wärmemenge, q, r, T, BEW, Stundensatz)
    print(f"Wärmegestehungskosten Solarthermie: {WGK:.2f} €/MWh")

def test_waste_heat_pump():
    wasteHeatPump = heat_generator_classes.WasteHeatPump(name="Abwärme", Kühlleistung_Abwärme=50, Temperatur_Abwärme=30, spez_Investitionskosten_Abwärme=500, spezifische_Investitionskosten_WP=1000)
    
    # Lastgang, z.B. in kW, muss derzeitig für korrekte wirtschaftliche Betrachtung Länge von 8760 haben
    min_last = 50
    min_last = 50
    max_last = 400
    Last_L = np.random.randint(min_last, max_last, 8760)

    # Arrays für Vor- und Rücklauftemperatur
    VLT_L = np.full(8760, 80)

    # Laden des COP-Kennfeldes
    COP_data = np.genfromtxt(get_resource_path("heat_generators/Kennlinien WP.csv"), delimiter=';')

    duration = 1

    Wärmemenge, Strombedarf_Abwärme, Wärmeleistung_L, el_Leistung_L= wasteHeatPump.abwärme(Last_L, VLT_L, COP_data, duration)
    print(f"Abwärmemenge: {Wärmemenge:.2f} MWh, Strombedarf Abwärme: {Strombedarf_Abwärme:.2f} MWh, Abwärmeleistung: {Wärmeleistung_L} kW, elektrische Leistung Abwärme: {el_Leistung_L} kW")

    Strompreis = 150 # €/MWh
    q = 1.05
    r = 1.03
    T = 20
    BEW = "Nein"
    Stundensatz = 45

    WGK = wasteHeatPump.WGK(wasteHeatPump.max_Wärmeleistung, Wärmemenge, Strombedarf_Abwärme, wasteHeatPump.spez_Investitionskosten_Abwärme, Strompreis, q, r, T, BEW, Stundensatz)
    print(f"Wärmegestehungskosten Abwärme: {WGK:.2f} €/MWh")

def test_river_heat_pump():
    riverHeatPump = heat_generator_classes.RiverHeatPump(name="Flusswasser", Wärmeleistung_FW_WP=200, Temperatur_FW_WP=10, dT=0, spez_Investitionskosten_Flusswasser=1000, spezifische_Investitionskosten_WP=1000)
    
    # Lastgang, z.B. in kW, muss derzeitig für korrekte wirtschaftliche Betrachtung Länge von 8760 haben
    min_last = 50
    min_last = 50
    max_last = 400
    Last_L = np.random.randint(min_last, max_last, 8760)

    # Arrays für Vor- und Rücklauftemperatur
    VLT_L = np.full(8760, 80)

    # Laden des COP-Kennfeldes
    COP_data = np.genfromtxt(get_resource_path("heat_generators/Kennlinien WP.csv"), delimiter=';')

    duration = 1

    Wärmemenge, Strombedarf_FW_WP, Wärmeleistung_L, el_Leistung_L, Kühlmenge, Kühlleistung_L = riverHeatPump.abwärme(Last_L, VLT_L, COP_data, duration)
    print(f"Wärmemenge Flusswasser-WP: {Wärmemenge:.2f} MWh, Strombedarf Flusswasser-WP: {Strombedarf_FW_WP:.2f} MWh, Kühlmenge Flusswasser-WP: {Kühlmenge:.2f} MWh, Wärmeleistung Flusswasser-WP: {Wärmeleistung_L} kW, elektrische Leistung Flusswasser-WP: {el_Leistung_L} kW, Kühlleistung Flusswasser-WP: {Kühlleistung_L} kW")

    Strompreis = 150 # €/MWh
    q = 1.05
    r = 1.03
    T = 20
    BEW = "Nein"
    Stundensatz = 45

    WGK= riverHeatPump.WGK(riverHeatPump.Wärmeleistung_FW_WP, Wärmemenge, Strombedarf_FW_WP, riverHeatPump.spez_Investitionskosten_Flusswasser, Strompreis, q, r, T, BEW, Stundensatz)
    print(f"Wärmegestehungskosten Flusswasserwärme: {WGK:.2f} €/MWh")

def test_geothermal_heat_pump():
    geothermalHeatPump = heat_generator_classes.Geothermal(name="Geothermie", Fläche=200, Bohrtiefe=100, Temperatur_Geothermie=10, spez_Bohrkosten=100, spez_Entzugsleistung=50, Vollbenutzungsstunden=2400, 
                                                           Abstand_Sonden=10, spezifische_Investitionskosten_WP=1000)
    
    # Lastgang, z.B. in kW, muss derzeitig für korrekte wirtschaftliche Betrachtung Länge von 8760 haben
    min_last = 50
    min_last = 50
    max_last = 400
    Last_L = np.random.randint(min_last, max_last, 8760)

    # Arrays für Vor- und Rücklauftemperatur
    VLT_L = np.full(8760, 80)

    # Laden des COP-Kennfeldes
    COP_data = np.genfromtxt(get_resource_path("heat_generators/Kennlinien WP.csv"), delimiter=';')

    duration = 1

    Wärmemenge, Strombedarf, Wärmeleistung_L, el_Leistung_Geothermie_L = geothermalHeatPump.Geothermie(Last_L, VLT_L, COP_data, duration)
    print(f"Wärmemenge Geothermie: {Wärmemenge:.2f} MWh, Strombedarf Geothermie: {Strombedarf:.2f} MWh, Wärmeleistung Geothermie: {Wärmeleistung_L} kW, elektrische Leistung Geothermie: {el_Leistung_Geothermie_L} kW")

    Strompreis = 150 # €/MWh
    q = 1.05
    r = 1.03
    T = 20
    BEW = "Nein"
    Stundensatz = 45

    geothermalHeatPump.spez_Investitionskosten_Erdsonden = geothermalHeatPump.Investitionskosten_Sonden / geothermalHeatPump.max_Wärmeleistung
    WGK = geothermalHeatPump.WGK(geothermalHeatPump.max_Wärmeleistung, Wärmemenge, Strombedarf, geothermalHeatPump.spez_Investitionskosten_Erdsonden, Strompreis, q, r, T, BEW, Stundensatz)
    print(f"Wärmegestehungskosten Geothermie: {WGK:.2f} €/MWh")

def test_berechnung_erzeugermix(optimize=False, plot=True):
    solarThermal = heat_generator_classes.SolarThermal(name="Solarthermie", bruttofläche_STA=200, vs=20, Typ="Vakuumröhrenkollektor", kosten_speicher_spez=800, kosten_vrk_spez=500)
    bBoiler = heat_generator_classes.BiomassBoiler(name="Biomassekessel", P_BMK=150, Größe_Holzlager=20, spez_Investitionskosten=200, spez_Investitionskosten_Holzlager=400)
    gBoiler = heat_generator_classes.GasBoiler(name="Gaskessel", spez_Investitionskosten=30)  # Angenommen, GasBoiler benötigt keine zusätzlichen Eingaben
    gCHP = heat_generator_classes.CHP(name="BHKW", th_Leistung_BHKW=50, spez_Investitionskosten_GBHKW=1500)
    wCHP = heat_generator_classes.CHP(name="Holz-BHKW", th_Leistung_BHKW=30, spez_Investitionskosten_HBHKW=1800)  # Angenommen, Holzgas-BHKW verwendet dieselbe Klasse wie BHKW
    geothermalHeatPump = heat_generator_classes.Geothermal(name="Geothermie", Fläche=200, Bohrtiefe=100, Temperatur_Geothermie=10, Abstand_Sonden=10, spez_Bohrkosten=100, spez_Entzugsleistung=45, Vollbenutzungsstunden=2400, spezifische_Investitionskosten_WP=1000)
    wasteHeatPump = heat_generator_classes.WasteHeatPump(name="Abwärme", Kühlleistung_Abwärme=40, Temperatur_Abwärme=30, spez_Investitionskosten_Abwärme=500, spezifische_Investitionskosten_WP=1000)
    wasteWaterHeatPump = heat_generator_classes.WasteHeatPump(name="Abwasserwärme", Kühlleistung_Abwärme=20, Temperatur_Abwärme=18, spez_Investitionskosten_Abwärme=500, spezifische_Investitionskosten_WP=1000)
    riverHeatPump = heat_generator_classes.RiverHeatPump(name="Flusswasser", Wärmeleistung_FW_WP=200, Temperatur_FW_WP=8, dT=0, spez_Investitionskosten_Flusswasser=600, spezifische_Investitionskosten_WP=1000)
       
    tech_order = [solarThermal, gCHP, geothermalHeatPump, bBoiler, gBoiler]
    #tech_order = [gCHP, wCHP, bBoiler, riverHeatPump, wasteHeatPump, gBoiler]

    # Lastgang, z.B. in kW, muss derzeitig für korrekte wirtschaftliche Betrachtung Länge von 8760 haben
    min_last = 50
    min_last = 50
    max_last = 400
    Last_L = np.random.randint(min_last, max_last, 8760).astype("float")

    # Arrays für Vor- und Rücklauftemperatur
    VLT_L, RLT_L = np.full(8760, 80), np.full(8760, 55)

    # Angaben zum zu betrchtende Zeitraum
    # Erstelle ein Array mit stündlichen Zeitwerten für ein Jahr
    start_date = np.datetime64('2019-01-01')
    end_date = np.datetime64('2020-01-01', 'D')  # Enddatum ist exklusiv, daher 'D' für Tage

    # Erstelle das Array mit stündlichen Zeitwerten für ein Jahr
    time_steps = np.arange(start_date, end_date, dtype='datetime64[h]')

    # Die zeitabhängigen Daten werden gemeinsam übergeben
    initial_data = time_steps, Last_L, VLT_L, RLT_L

    # Start und End Zeitschritt
    start = 0
    end = 8760

    # Dateiname Testreferenzjahr für Wetterdaten, Dateiname muss ggf. angepasstw werden
    TRY = import_TRY(get_resource_path("heat_requirement/TRY_511676144222/TRY2015_511676144222_Jahr.dat"))

    # Laden des COP-Kennfeldes
    COP_data = np.genfromtxt(get_resource_path("heat_generators/Kennlinien WP.csv"), delimiter=';')

    Strompreis = 150 # €/MWh
    Gaspreis = 70 # €/MWh
    Holzpreis = 60 # €/MWh

    BEW = "Nein"
    stundensatz = 45

    kapitalzins = 5 # %
    preissteigerungsrate = 3 # %
    betrachtungszeitraum = 20 # Jahre

    if optimize == True:
        tech_order = heat_generator_classes.optimize_mix(tech_order, initial_data, start, end, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, \
                                            kapitalzins=kapitalzins, preissteigerungsrate=preissteigerungsrate, betrachtungszeitraum=betrachtungszeitraum, stundensatz=stundensatz)
        
    general_results = heat_generator_classes.Berechnung_Erzeugermix(tech_order, initial_data, start, end, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, kapitalzins=kapitalzins, preissteigerungsrate=preissteigerungsrate, betrachtungszeitraum=betrachtungszeitraum)
    print(general_results)

    if plot == True:
        figure1 = plt.figure()
        figure2 = plt.figure()

        plotStackPlot(figure1, general_results['time_steps'], general_results['Wärmeleistung_L'], general_results['techs'], general_results['Last_L'])
        plotPieChart(figure2, general_results['Anteile'], general_results['techs'])

        plt.show()

def plotStackPlot(figure, t, data, labels, Last):
    ax = figure.add_subplot(111)
    ax.stackplot(t, data, labels=labels)
    ax.set_title("Jahresdauerlinie")
    ax.set_xlabel("Jahresstunden")
    ax.set_ylabel("thermische Leistung in kW")
    ax.legend(loc='upper center')
    ax.grid()

    # Hinzufügen von Last_L als Linienplot
    ax1 = figure.gca()  # Get current axis
    ax1.plot(t, Last, color='black', linewidth=0.5)  # Zeichnen der Last_L Linie

def plotPieChart(figure, Anteile, labels):
    ax = figure.add_subplot(111)

    # Überprüfen, ob die Summe der Anteile weniger als 1 (100 %) beträgt
    summe = sum(Anteile)
    if summe < 1:
        # Fügen Sie den fehlenden Anteil hinzu, um die Lücke darzustellen
        Anteile.append(1 - summe)
        labels.append("ungedeckter Bedarf")  # Oder einen anderen passenden Text für den leeren Bereich

    ax.pie(Anteile, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.set_title("Anteile Wärmeerzeugung")
    ax.legend(loc='lower left')
    ax.axis("equal")  # Stellt sicher, dass der Pie-Chart kreisförmig bleibt

#test_annuität()
#test_biomass_boiler()
#test_gas_boiler()
#test_chp()
#test_solar_thermal()
#test_waste_heat_pump()
#test_river_heat_pump()
test_geothermal_heat_pump()
#test_berechnung_erzeugermix(optimize=False, plot=True)
#test_berechnung_erzeugermix(optimize=True, plot=True)