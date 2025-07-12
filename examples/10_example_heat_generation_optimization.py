"""
Filename: 10_example_heat_generation_optimization.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-07-12
Description: Example for the optimization of a heat generator mix

Updated to match the latest version of all heat generator classes.
"""

from districtheatingsim.heat_generators.solar_thermal import SolarThermal
from districtheatingsim.heat_generators.gas_boiler import GasBoiler
from districtheatingsim.heat_generators.biomass_boiler import BiomassBoiler
from districtheatingsim.heat_generators.chp import CHP
from districtheatingsim.heat_generators.waste_heat_pump import WasteHeatPump
from districtheatingsim.heat_generators.river_heat_pump import RiverHeatPump
from districtheatingsim.heat_generators.geothermal_heat_pump import Geothermal
from districtheatingsim.heat_generators.power_to_heat import PowerToHeat
from districtheatingsim.heat_generators.energy_system import EnergySystem
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
    electricity_price = 150 # €/MWh - Updated to match 09 example
    gas_price = 70 # €/MWh
    wood_price = 60 # €/MWh - Updated to match 09 example

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

    # UPDATED: Technology definitions matching 09 example
    gBoiler = GasBoiler(
        name="Gas_Boiler_1", 
        thermal_capacity_kW=1000,  # Updated parameter name
        spez_Investitionskosten=30, 
        Nutzungsgrad=0.9
    )

    PTH = PowerToHeat(
        name="PowerToHeat_1", 
        thermal_capacity_kW=1000,  # Updated parameter name
        spez_Investitionskosten=30, 
        Nutzungsgrad=0.98  # Updated efficiency
    )

    bBoiler = BiomassBoiler(
        name="Biomass_Boiler_1", 
        thermal_capacity_kW=200, 
        Größe_Holzlager=40, 
        spez_Investitionskosten=200, 
        spez_Investitionskosten_Holzlager=400, 
        Nutzungsgrad_BMK=0.8, 
        min_Teillast=0.3, 
        speicher_aktiv=False, 
        Speicher_Volumen=20, 
        T_vorlauf=90, 
        T_ruecklauf=60, 
        initial_fill=0.0, 
        min_fill=0.2, 
        max_fill=0.8, 
        spez_Investitionskosten_Speicher=750, 
        active=True, 
        opt_BMK_min=0, 
        opt_BMK_max=1000, 
        opt_Speicher_min=0, 
        opt_Speicher_max=100
    )

    bBoiler_storage = BiomassBoiler(
        name="Biomass_Boiler_2", 
        thermal_capacity_kW=200, 
        Größe_Holzlager=40, 
        spez_Investitionskosten=200, 
        spez_Investitionskosten_Holzlager=400, 
        Nutzungsgrad_BMK=0.8, 
        min_Teillast=0.3, 
        speicher_aktiv=True,  # Updated: with storage
        Speicher_Volumen=20, 
        T_vorlauf=90, 
        T_ruecklauf=60, 
        initial_fill=0.0, 
        min_fill=0.2, 
        max_fill=0.8, 
        spez_Investitionskosten_Speicher=750, 
        active=True, 
        opt_BMK_min=0, 
        opt_BMK_max=1000, 
        opt_Speicher_min=0, 
        opt_Speicher_max=100
    )

    CHP_1 = CHP(
        name="BHKW_1", 
        th_Leistung_kW=100,  # Updated parameter name
        spez_Investitionskosten_GBHKW=1500, 
        spez_Investitionskosten_HBHKW=1850, 
        el_Wirkungsgrad=0.33, 
        KWK_Wirkungsgrad=0.9, 
        min_Teillast=0.7, 
        speicher_aktiv=False, 
        Speicher_Volumen_BHKW=20, 
        T_vorlauf=90, 
        T_ruecklauf=60, 
        initial_fill=0.0, 
        min_fill=0.2, 
        max_fill=0.8, 
        spez_Investitionskosten_Speicher=750, 
        active=True, 
        opt_BHKW_min=0, 
        opt_BHKW_max=1000, 
        opt_BHKW_Speicher_min=0, 
        opt_BHKW_Speicher_max=100
    )

    CHP_storage = CHP(
        name="BHKW_2", 
        th_Leistung_kW=100,  # Updated parameter name
        spez_Investitionskosten_GBHKW=1500, 
        spez_Investitionskosten_HBHKW=1850, 
        el_Wirkungsgrad=0.33, 
        KWK_Wirkungsgrad=0.9, 
        min_Teillast=0.7, 
        speicher_aktiv=True,  # Updated: with storage
        Speicher_Volumen_BHKW=20, 
        T_vorlauf=90, 
        T_ruecklauf=60, 
        initial_fill=0.0, 
        min_fill=0.2, 
        max_fill=0.8, 
        spez_Investitionskosten_Speicher=750, 
        active=True, 
        opt_BHKW_min=0, 
        opt_BHKW_max=1000, 
        opt_BHKW_Speicher_min=0, 
        opt_BHKW_Speicher_max=100
    )

    # UPDATED: Heat pump definitions matching 09 example
    wasteHeatPump = WasteHeatPump(
        name="Abwärmepumpe", 
        Kühlleistung_Abwärme=50, 
        Temperatur_Abwärme=30, 
        spez_Investitionskosten_Abwärme=500, 
        spezifische_Investitionskosten_WP=1000, 
        min_Teillast=0.2
    )

    riverHeatPump = RiverHeatPump(
        name="Flusswärmepumpe", 
        Wärmeleistung_FW_WP=200, 
        Temperatur_FW_WP=10, 
        dT=0, 
        spez_Investitionskosten_Flusswasser=1000, 
        spezifische_Investitionskosten_WP=1000, 
        min_Teillast=0.2
    )

    geothermal_heat_pump = Geothermal(
        name="Geothermie", 
        Fläche=200, 
        Bohrtiefe=100, 
        Temperatur_Geothermie=10, 
        spez_Bohrkosten=100, 
        spez_Entzugsleistung=50,
        Vollbenutzungsstunden=2400, 
        Abstand_Sonden=10, 
        spezifische_Investitionskosten_WP=1000, 
        min_Teillast=0.2
    )

    solarThermal = SolarThermal(
        name="Solarthermie", 
        bruttofläche_STA=200, 
        vs=20, 
        Typ="Vakuumröhrenkollektor", 
        kosten_speicher_spez=750, 
        kosten_fk_spez=430, 
        kosten_vrk_spez=590, 
        Tsmax=90, 
        Longitude=-14.4222, 
        STD_Longitude=-15, 
        Latitude=51.1676, 
        East_West_collector_azimuth_angle=0, 
        Collector_tilt_angle=36, 
        Tm_rl=60, 
        Qsa=0, 
        Vorwärmung_K=8, 
        DT_WT_Solar_K=5, 
        DT_WT_Netz_K=5, 
        opt_volume_min=0, 
        opt_volume_max=200, 
        opt_area_min=0, 
        opt_area_max=2000
    )

    # UPDATED: Technology selection - mix of different technologies
    tech_objects = [
        solarThermal,  # Solar thermal
        CHP_1,      # CHP with storage
        gBoiler,          # Gas boiler as backup
    ]

    # Time steps for simulation
    start_date = np.datetime64('2019-01-01')
    end_date = np.datetime64('2020-01-01', 'D')
    time_steps = np.arange(start_date, end_date, dtype='datetime64[h]')

    # UPDATED: Economic parameters matching 09 example
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

    # Optimization weights
    weights = {
        "WGK_Gesamt": 1.0,                    # Focus on cost optimization
        "specific_emissions_Gesamt": 0.1,     # Small weight for emissions
        "primärenergiefaktor_Gesamt": 0.0     # No weight for primary energy
    }

    # Create energy system
    energy_system = EnergySystem(
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

    # Calculate the initial energy mix
    system_results = energy_system.calculate_mix()
    print("=== Initial Energy Mix Results ===")
    print(f"Technologies: {system_results['techs']}")
    print(f"Energy mix shares: {system_results['Anteile']}")
    print(f"Heat generation costs: {system_results['WGK_Gesamt']:.2f} €/MWh")
    print(f"Specific emissions: {system_results.get('specific_emissions_Gesamt', 'N/A'):.3f} tCO2/MWh")
    print(f"Primary energy factor: {system_results.get('primärenergiefaktor_Gesamt', 'N/A'):.3f}")

    if plot:
        print("\nGenerating initial plots...")
        fig1 = plt.figure(figsize=(12, 8))
        energy_system.plot_stack_plot(fig1)
        fig1.suptitle('Initial Energy Mix - Stack Plot')
        
        fig2 = plt.figure(figsize=(10, 8))
        energy_system.plot_pie_chart(fig2)
        fig2.suptitle('Initial Energy Mix - Pie Chart')

    # Perform optimization if requested
    if optimize:
        print(f"\n=== Starting Optimization with {opt_method} ===")
        
        if opt_method == "SLSQP":
            print("Optimizing mix with SLSQP...")
            optimized_energy_system = energy_system.optimize_mix(weights, num_restarts=5)
        else:
            print(f"Unknown optimization method: {opt_method}")
            return
            
        print("Optimization completed!")

        # Calculate the optimized energy mix
        optimized_system_results = optimized_energy_system.calculate_mix()
        print("\n=== Optimized Energy Mix Results ===")
        print(f"Technologies: {optimized_system_results['techs']}")
        print(f"Energy mix shares: {optimized_system_results['Anteile']}")
        print(f"Heat generation costs: {optimized_system_results['WGK_Gesamt']:.2f} €/MWh")
        print(f"Specific emissions: {optimized_system_results.get('specific_emissions_Gesamt', 'N/A'):.3f} tCO2/MWh")
        print(f"Primary energy factor: {optimized_system_results.get('primärenergiefaktor_Gesamt', 'N/A'):.3f}")

        # Compare results
        print("\n=== Optimization Comparison ===")
        initial_cost = system_results['WGK_Gesamt']
        optimized_cost = optimized_system_results['WGK_Gesamt']
        cost_savings = initial_cost - optimized_cost
        cost_savings_percent = (cost_savings / initial_cost) * 100

        print(f"Initial costs: {initial_cost:.2f} €/MWh")
        print(f"Optimized costs: {optimized_cost:.2f} €/MWh")
        print(f"Cost savings: {cost_savings:.2f} €/MWh ({cost_savings_percent:.1f}%)")

        if plot:
            print("\nGenerating optimized plots...")
            fig3 = plt.figure(figsize=(12, 8))
            optimized_energy_system.plot_stack_plot(fig3)
            fig3.suptitle('Optimized Energy Mix - Stack Plot')
            
            fig4 = plt.figure(figsize=(10, 8))
            optimized_energy_system.plot_pie_chart(fig4)
            fig4.suptitle('Optimized Energy Mix - Pie Chart')

    print("\n=== Analysis Complete ===")
    return energy_system

if __name__ == "__main__":
    print("Starting Heat Generation Optimization Example")
    print("=" * 50)
    
    # Test with different optimization methods
    print("\n1. Testing without optimization:")
    energy_system_base = test_berechnung_erzeugermix(optimize=False, plot=True)
    
    print("\n2. Testing with SLSQP optimization:")
    energy_system_slsqp = test_berechnung_erzeugermix(optimize=True, plot=True, opt_method="SLSQP")

    print("\nShowing all plots...")
    plt.show()