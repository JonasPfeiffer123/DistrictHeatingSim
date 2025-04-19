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
from districtheatingsim.heat_generators import energy_system
from districtheatingsim.utilities.test_reference_year import import_TRY

import numpy as np

import matplotlib.pyplot as plt

def test_berechnung_erzeugermix(optimize=False, plot=True, opt_method="SLSQP"):
    # Lastgang, z.B. in kW, muss derzeitig für korrekte wirtschaftliche Betrachtung Länge von 8760 haben
    min_last = 50
    max_last = 400
    Last_L = np.random.randint(min_last, max_last, 8760).astype(float)

    # Load profile from csv file
    Last_L = np.genfromtxt("examples/data/Lastgang/Lastgang.csv", delimiter=';', skip_header=1)
    # 5 column
    Last_L = Last_L[:, 4]
    print(Last_L)

    # Wirtschaftliche Randbedingungen
    electricity_price = 200 # €/MWh
    gas_price = 70 # €/MWh
    wood_price = 40 # €/MWh

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

    bBoiler = biomass_boiler.BiomassBoiler(name="Biomassekessel_1", thermal_capacity_kW=200, Größe_Holzlager=40, spez_Investitionskosten=200, 
                                           spez_Investitionskosten_Holzlager=400, Nutzungsgrad_BMK=0.8, min_Teillast=0.3, speicher_aktiv=False, 
                                           Speicher_Volumen=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, min_fill=0.2, max_fill=0.8, 
                                           spez_Investitionskosten_Speicher=750, active=True, opt_BMK_min=0, opt_BMK_max=1000, opt_Speicher_min=0, 
                                           opt_Speicher_max=100)

    bBoiler_storage = biomass_boiler.BiomassBoiler(name="Biomassekessel_2", thermal_capacity_kW=200, Größe_Holzlager=40, spez_Investitionskosten=200, 
                                                   spez_Investitionskosten_Holzlager=400, Nutzungsgrad_BMK=0.8, min_Teillast=0.3, speicher_aktiv=True, 
                                                   Speicher_Volumen=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, min_fill=0.2, max_fill=0.8, 
                                                   spez_Investitionskosten_Speicher=750, active=True, opt_BMK_min=0, opt_BMK_max=1000, opt_Speicher_min=0, 
                                                   opt_Speicher_max=100)

    CHP = chp.CHP(name="BHKW_1", th_Leistung_BHKW=100, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850, el_Wirkungsgrad=0.33, 
                  KWK_Wirkungsgrad=0.9, min_Teillast=0.7, speicher_aktiv=False, Speicher_Volumen_BHKW=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, 
                  min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750, active=True, opt_BHKW_min=0, opt_BHKW_max=1000, opt_BHKW_Speicher_min=0, 
                  opt_BHKW_Speicher_max=100)    

    CHP_storage = chp.CHP(name="BHKW_2", th_Leistung_BHKW=100, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850, el_Wirkungsgrad=0.33, 
                          KWK_Wirkungsgrad=0.9, min_Teillast=0.7, speicher_aktiv=True, Speicher_Volumen_BHKW=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, 
                          min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750, active=True, opt_BHKW_min=0, opt_BHKW_max=1000, opt_BHKW_Speicher_min=0, 
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

    tech_objects = [CHP_storage, bBoiler, gBoiler]

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

    energy_system = energy_system.EnergySystem(
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
    system_results = energy_system.calculate_mix()
    print(f"Techs: {system_results['techs']}")
    print(f"Energy mix: {system_results['Anteile']}")
    print(f"WGK: {system_results['WGK_Gesamt']}")

    if plot:
        energy_system.plot_stack_plot(plt.figure())
        energy_system.plot_pie_chart(plt.figure())

    # Perform optimization if needed
    if optimize:
        if opt_method == "SLSQP":
            print("Optimizing mix with SLSQP")
            optimized_energy_system = energy_system.optimize_mix(weights, num_restarts=5)
        elif opt_method == "MILP":
            print("Optimizing mix with MILP")
            optimized_energy_system = energy_system.optimize_milp(weights, num_restarts=5)
        print("Optimization done")

        # Calculate the energy mix
        optimized_system_results = optimized_energy_system.calculate_mix()
        print(f"Optimized Techs: {optimized_system_results['techs']}")
        print(f"Optimized energy mix: {optimized_system_results['Anteile']}")
        print(f"Optimized WGK: {optimized_system_results['WGK_Gesamt']}")

        if plot:
            optimized_energy_system.plot_stack_plot(plt.figure())
            optimized_energy_system.plot_pie_chart(plt.figure())

if __name__ == "__main__":
    test_berechnung_erzeugermix(optimize=True, plot=True, opt_method="SLSQP")

    plt.show()