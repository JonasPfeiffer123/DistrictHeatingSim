"""
Filename: 10_example_heat_generation_optimization.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-19
Description: Example for the optimization of a heat generator mix
"""

from districtheatingsim.heat_generators import heat_generation_mix
from districtheatingsim.utilities.test_reference_year import import_TRY

import numpy as np

import matplotlib.pyplot as plt

def test_berechnung_erzeugermix(optimize=False, plot=True):
    solarThermal = heat_generation_mix.SolarThermal(name="Solarthermie", bruttofläche_STA=200, vs=20, Typ="Vakuumröhrenkollektor", kosten_speicher_spez=800, kosten_vrk_spez=500)
    bBoiler = heat_generation_mix.BiomassBoiler(name="Biomassekessel", P_BMK=150, Größe_Holzlager=20, spez_Investitionskosten=200, spez_Investitionskosten_Holzlager=400)
    gBoiler = heat_generation_mix.GasBoiler(name="Gaskessel", spez_Investitionskosten=30)  # Angenommen, GasBoiler benötigt keine zusätzlichen Eingaben
    gCHP = heat_generation_mix.CHP(name="BHKW", th_Leistung_BHKW=50, spez_Investitionskosten_GBHKW=1500)
    wCHP = heat_generation_mix.CHP(name="Holz-BHKW", th_Leistung_BHKW=30, spez_Investitionskosten_HBHKW=1800)  # Angenommen, Holzgas-BHKW verwendet dieselbe Klasse wie BHKW
    geothermalHeatPump = heat_generation_mix.Geothermal(name="Geothermie", Fläche=200, Bohrtiefe=100, Temperatur_Geothermie=10, Abstand_Sonden=10, spez_Bohrkosten=100, spez_Entzugsleistung=45, Vollbenutzungsstunden=2400, spezifische_Investitionskosten_WP=1000)
    wasteHeatPump = heat_generation_mix.WasteHeatPump(name="Abwärme", Kühlleistung_Abwärme=40, Temperatur_Abwärme=30, spez_Investitionskosten_Abwärme=500, spezifische_Investitionskosten_WP=1000)
    wasteWaterHeatPump = heat_generation_mix.WasteHeatPump(name="Abwasserwärme", Kühlleistung_Abwärme=20, Temperatur_Abwärme=18, spez_Investitionskosten_Abwärme=500, spezifische_Investitionskosten_WP=1000)
    riverHeatPump = heat_generation_mix.RiverHeatPump(name="Flusswasser", Wärmeleistung_FW_WP=200, Temperatur_FW_WP=8, dT=0, spez_Investitionskosten_Flusswasser=600, spezifische_Investitionskosten_WP=1000)
       
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
    TRY = import_TRY("examples/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat")

    # Laden des COP-Kennfeldes
    COP_data = np.genfromtxt("examples/data/TRY/Kennlinien WP.csv", delimiter=';')

    Strompreis = 150 # €/MWh
    Gaspreis = 70 # €/MWh
    Holzpreis = 60 # €/MWh

    BEW = "Nein"
    stundensatz = 45

    kapitalzins = 5 # %
    preissteigerungsrate = 3 # %
    betrachtungszeitraum = 20 # Jahre

    if optimize == True:
        tech_order = heat_generation_mix.optimize_mix(tech_order, initial_data, start, end, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, \
                                            kapitalzins=kapitalzins, preissteigerungsrate=preissteigerungsrate, betrachtungszeitraum=betrachtungszeitraum, stundensatz=stundensatz)
        
    general_results = heat_generation_mix.Berechnung_Erzeugermix(tech_order, initial_data, start, end, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW, kapitalzins=kapitalzins, preissteigerungsrate=preissteigerungsrate, betrachtungszeitraum=betrachtungszeitraum)
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

if __name__ == "__main__":
    test_berechnung_erzeugermix(optimize=False, plot=True)
    test_berechnung_erzeugermix(optimize=True, plot=True)