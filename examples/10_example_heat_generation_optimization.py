"""
Filename: 10_example_heat_generation_optimization.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-19
Description: Example for the optimization of a heat generator mix
"""

from districtheatingsim.heat_generators import solar_thermal
from districtheatingsim.heat_generators import gas_boiler
from districtheatingsim.heat_generators import biomass_boiler
from districtheatingsim.heat_generators import chp
from districtheatingsim.heat_generators import heat_pumps
from districtheatingsim.heat_generators import power_to_heat
from districtheatingsim.heat_generators import heat_generation_mix
from districtheatingsim.utilities.test_reference_year import import_TRY

import numpy as np

import matplotlib.pyplot as plt

def test_berechnung_erzeugermix(optimize=False, plot=True):
    # Lastgang, z.B. in kW, muss derzeitig für korrekte wirtschaftliche Betrachtung Länge von 8760 haben
    min_last = 50
    max_last = 400
    Last_L = np.random.randint(min_last, max_last, 8760).astype(float)

    # Wirtschaftliche Randbedingungen
    electricity_price = 150 # €/MWh
    gas_price = 70 # €/MWh
    wood_price = 60 # €/MWh

    q = 1.05
    r = 1.03
    T = 20
    BEW = "Nein"
    hourly_rate = 45

    # Arrays für Vor- und Rücklauftemperatur
    VLT_L, RLT_L = np.full(8760, 80), np.full(8760, 55)

    # Laden des COP-Kennfeldes
    COP_data = np.genfromtxt("examples/data/COP/Kennlinien WP.csv", delimiter=';')

    # Dateiname Testreferenzjahr für Wetterdaten, Dateiname muss ggf. angepasst werden
    TRY_data = import_TRY("examples/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat")  
    gBoiler = gas_boiler.GasBoiler(name="Gaskessel_1", spez_Investitionskosten=30, Nutzungsgrad=0.9, Faktor_Dimensionierung=1)

    PTH = power_to_heat.PowerToHeat(name="Power-to-Heat_1", spez_Investitionskosten=30, Nutzungsgrad=0.9, Faktor_Dimensionierung=1)

    bBoiler = biomass_boiler.BiomassBoiler(name="Biomassekessel_1", P_BMK=200, Größe_Holzlager=40, spez_Investitionskosten=200, 
                                           spez_Investitionskosten_Holzlager=400, Nutzungsgrad_BMK=0.8, min_Teillast=0.3, speicher_aktiv=False, 
                                           Speicher_Volumen=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, min_fill=0.2, max_fill=0.8, 
                                           spez_Investitionskosten_Speicher=750, BMK_an=True, opt_BMK_min=0, opt_BMK_max=1000, opt_Speicher_min=0, 
                                           opt_Speicher_max=100)

    bBoiler_storage = biomass_boiler.BiomassBoiler(name="Biomassekessel_2", P_BMK=200, Größe_Holzlager=40, spez_Investitionskosten=200, 
                                                   spez_Investitionskosten_Holzlager=400, Nutzungsgrad_BMK=0.8, min_Teillast=0.3, speicher_aktiv=True, 
                                                   Speicher_Volumen=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, min_fill=0.2, max_fill=0.8, 
                                                   spez_Investitionskosten_Speicher=750, BMK_an=True, opt_BMK_min=0, opt_BMK_max=1000, opt_Speicher_min=0, 
                                                   opt_Speicher_max=100)

    CHP = chp.CHP(name="BHKW_1", th_Leistung_BHKW=100, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850, el_Wirkungsgrad=0.33, 
                  KWK_Wirkungsgrad=0.9, min_Teillast=0.7, speicher_aktiv=False, Speicher_Volumen_BHKW=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, 
                  min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750, BHKW_an=True, opt_BHKW_min=0, opt_BHKW_max=1000, opt_BHKW_Speicher_min=0, 
                  opt_BHKW_Speicher_max=100)    

    CHP_storage = chp.CHP(name="BHKW_2", th_Leistung_BHKW=100, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850, el_Wirkungsgrad=0.33, 
                          KWK_Wirkungsgrad=0.9, min_Teillast=0.7, speicher_aktiv=True, Speicher_Volumen_BHKW=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, 
                          min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750, BHKW_an=True, opt_BHKW_min=0, opt_BHKW_max=1000, opt_BHKW_Speicher_min=0, 
                          opt_BHKW_Speicher_max=100)

    riverHeatPump = heat_pumps.WasteHeatPump(name="Abwärme_1", Kühlleistung_Abwärme=50, Temperatur_Abwärme=30, spez_Investitionskosten_Abwärme=500, 
                                             spezifische_Investitionskosten_WP=1000, min_Teillast=0.2)

    riverHeatPump = heat_pumps.RiverHeatPump(name="Flusswasser_1", Wärmeleistung_FW_WP=200, Temperatur_FW_WP=10, dT=0, spez_Investitionskosten_Flusswasser=1000, 
                                             spezifische_Investitionskosten_WP=1000, min_Teillast=0.2)

    geothermal_heat_pump = heat_pumps.Geothermal(name="Geothermie_1", Fläche=200, Bohrtiefe=100, Temperatur_Geothermie=10, spez_Bohrkosten=100, spez_Entzugsleistung=50,
                                                Vollbenutzungsstunden=2400, Abstand_Sonden=10, spezifische_Investitionskosten_WP=1000, min_Teillast=0.2)
    
    # not implemented yet
    #aqva_heat = heat_pumps.AqvaHeat(name="AqvaHeat_1", nominal_power=100, temperature_difference=0)
    #test_aqva_heat(Last_L, duration, Strompreis, q, r, T, BEW, stundensatz, VLT_L, COP_data, aqva_heat)  

    solarThermal = solar_thermal.SolarThermal(name="Solarthermie_1", bruttofläche_STA=200, vs=20, Typ="Vakuumröhrenkollektor", kosten_speicher_spez=750, kosten_fk_spez=430, kosten_vrk_spez=590, 
                                            Tsmax=90, Longitude=-14.4222, STD_Longitude=-15, Latitude=51.1676, East_West_collector_azimuth_angle=0, Collector_tilt_angle=36, Tm_rl=60, 
                                            Qsa=0, Vorwärmung_K=8, DT_WT_Solar_K=5, DT_WT_Netz_K=5, opt_volume_min=0, opt_volume_max=200, opt_area_min=0, opt_area_max=2000)

    tech_objects = [solarThermal, CHP, geothermal_heat_pump, bBoiler, gBoiler]

    # Angaben zum zu betrchtende Zeitraum
    # Erstelle ein Array mit stündlichen Zeitwerten für ein Jahr
    start_date = np.datetime64('2019-01-01')
    end_date = np.datetime64('2020-01-01', 'D')  # Enddatum ist exklusiv, daher 'D' für Tage

    # Erstelle das Array mit stündlichen Zeitwerten für ein Jahr
    time_steps = np.arange(start_date, end_date, dtype='datetime64[h]')

    economic_parameters = {
                "gas_price": gas_price,
                "electricity_price": electricity_price,
                "wood_price": wood_price,
                "capital_interest_rate": q,
                "inflation_rate": r,
                "time_period": T,
                "hourly_rate": hourly_rate,
                "subsidy_eligibility": BEW
            }

    weights = {
        "WGK_Gesamt": 1.0,
        "specific_emissions_Gesamt": 0.0,
        "primärenergiefaktor_Gesamt": 0.0
    }

    energy_system = heat_generation_mix.EnergySystem(
                time_steps=time_steps,
                load_profile=Last_L,
                VLT_L=VLT_L,
                RLT_L=RLT_L,
                TRY_data=TRY_data,
                COP_data=COP_data,
                economic_parameters=economic_parameters,
            )

        # Add technologies to the system
    for tech in tech_objects:
        energy_system.add_technology(tech)

    # Calculate the energy mix
    general_results = energy_system.calculate_mix()
    print(f"Calculated energy mix: {general_results}")

    # Perform optimization if needed
    if optimize:
        print("Optimizing mix")
        optimized_energy_system = energy_system.optimize_mix(weights)
        print("Optimization done")

        # Calculate the energy mix
        general_results = optimized_energy_system.calculate_mix()
        print(f"Optimized energy mix: {general_results}")

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