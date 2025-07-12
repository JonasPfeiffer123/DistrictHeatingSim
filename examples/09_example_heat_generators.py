"""
Filename: 09_example_heat_generators.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-07-12
Description: Script for testing the heat generator functions.

# Not up-to-date: This script is not up-to-date with the latest version of all heat generator classes.
"""

from districtheatingsim.heat_generators.solar_thermal import SolarThermal
from districtheatingsim.heat_generators.gas_boiler import GasBoiler
from districtheatingsim.heat_generators.biomass_boiler import BiomassBoiler
from districtheatingsim.heat_generators.chp import CHP
from districtheatingsim.heat_generators.waste_heat_pump import WasteHeatPump
from districtheatingsim.heat_generators.river_heat_pump import RiverHeatPump
from districtheatingsim.heat_generators.geothermal_heat_pump import Geothermal
from districtheatingsim.heat_generators.power_to_heat import PowerToHeat
from districtheatingsim.utilities.test_reference_year import import_TRY

import numpy as np

import matplotlib.pyplot as plt

def test_gas_boiler(Last_L, duration, economic_parameters, gBoiler=GasBoiler(name="Gas_Boiler_1",
                                                                             thermal_capacity_kW=200,
                                                                             spez_Investitionskosten=30, 
                                                                             Nutzungsgrad=0.9)):
    results = gBoiler.calculate(economic_parameters, duration, Last_L)
    
    print(f"Wärmemenge Gaskessel: {results['Wärmemenge']:.2f} MWh")
    print(f"Wärmeleistung Gaskessel: {results['Wärmeleistung_L']} kW")
    print(f"Brennstoffbedarf Gaskessel: {results['Brennstoffbedarf']:.2f} MWh")
    print(f"Wärmegestehungskosten Gaskessel: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Gaskessel: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Gaskessel: {results['primärenergie']:.2f} MWh")

def test_power_to_heat(Last_L, duration, economic_parameters, PTH=PowerToHeat(name="PowerToHeat", 
                                                                              thermal_capacity_kW=1000, 
                                                                              spez_Investitionskosten=30, 
                                                                              Nutzungsgrad=0.98)):
    results = PTH.calculate(economic_parameters, duration, Last_L)

    print(f"Wärmemenge Power-to-Heat: {results['Wärmemenge']:.2f} MWh")
    print(f"Wärmeleistung Power-to-Heat: {results['Wärmeleistung_L']} kW")
    print(f"Strombedarf Power-to-Heat: {results['Strombedarf']:.2f} MWh")
    print(f"Wärmegestehungskosten Power-to-Heat: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Power-to-Heat: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Power-to-Heat: {results['primärenergie']:.2f} MWh")

def test_biomass_boiler(Last_L, duartion, economic_parameters, bBoiler=BiomassBoiler(name="Biomasss_Boiler_1", thermal_capacity_kW=200, Größe_Holzlager=40, spez_Investitionskosten=200, spez_Investitionskosten_Holzlager=400, 
                                           Nutzungsgrad_BMK=0.8, min_Teillast=0.3, speicher_aktiv=False, Speicher_Volumen=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, 
                                           min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750, active=True, opt_BMK_min=0, opt_BMK_max=1000, opt_Speicher_min=0, 
                                           opt_Speicher_max=100)):
    results = bBoiler.calculate(economic_parameters, duartion, Last_L)
    
    print(f"Wärmemenge Biomassekessel: {results['Wärmemenge']:.2f} MWh")
    print(f"Wärmeleistung Biomassekessel: {results['Wärmeleistung_L']} kW")
    print(f"Brennstoffbedarf Biomassekessel: {results['Brennstoffbedarf']:.2f} MWh")
    print(f"Wärmegestehungskosten Biomassekessel: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Biomassekessel: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Biomassekessel: {results['primärenergie']:.2f} MWh")
    print(f"Anzahl Starts Biomassekessel: {results['Anzahl_Starts']}")
    print(f"Betriebsstunden Biomassekessel: {results['Betriebsstunden']} h")
    print(f"Betriebsstunden pro Start Biomassekessel: {results['Betriebsstunden_pro_Start']:.2f} h")

def test_biomass_boiler_storage(Last_L, 
                                duration, 
                                economic_parameters, 
                                bBoiler=BiomassBoiler(name="Biomasss_Boiler_1", thermal_capacity_kW=200, 
                                                                     Größe_Holzlager=40, spez_Investitionskosten=200, 
                                                                     spez_Investitionskosten_Holzlager=400, 
                                                                     Nutzungsgrad_BMK=0.8, min_Teillast=0.3, 
                                                                     speicher_aktiv=True, Speicher_Volumen=20, 
                                                                     T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, 
                                                                     min_fill=0.2, max_fill=0.8, 
                                                                     spez_Investitionskosten_Speicher=750, active=True, 
                                                                     opt_BMK_min=0, opt_BMK_max=1000, opt_Speicher_min=0, 
                                                                     opt_Speicher_max=100)):

    results = bBoiler.calculate(economic_parameters, duration, Last_L)
    
    print(f"Wärmemenge Biomassekessel mit Speicher: {results['Wärmemenge']:.2f} MWh")
    print(f"Wärmeleistung Biomassekessel mit Speicher: {results['Wärmeleistung_L']} kW")
    print(f"Wärmeleistung Speicher Biomassekessel: {results['Wärmeleistung_Speicher_L']} kW")
    print(f"Brennstoffbedarf Biomassekessel mit Speicher: {results['Brennstoffbedarf']:.2f} MWh")
    print(f"Wärmegestehungskosten Biomassekessel mit Speicher: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Biomassekessel mit Speicher: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Biomassekessel mit Speicher: {results['primärenergie']:.2f} MWh")
    print(f"Anzahl Starts Biomassekessel mit Speicher: {results['Anzahl_Starts']}")
    print(f"Betriebsstunden Biomassekessel mit Speicher: {results['Betriebsstunden']} h")
    print(f"Betriebsstunden pro Start Biomassekessel mit Speicher: {results['Betriebsstunden_pro_Start']:.2f} h")

def test_chp(Last_L, duration, economic_parameters, chp=CHP(name="BHKW", th_Leistung_kW=100, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850, el_Wirkungsgrad=0.33, 
                                                                KWK_Wirkungsgrad=0.9, min_Teillast=0.7, speicher_aktiv=False, Speicher_Volumen_BHKW=20, T_vorlauf=90, T_ruecklauf=60, 
                                                                initial_fill=0.0, min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750, active=True, opt_BHKW_min=0, opt_BHKW_max=1000, 
                                                                opt_BHKW_Speicher_min=0, opt_BHKW_Speicher_max=100)):

    results = chp.calculate(economic_parameters, duration, Last_L)

    print(f"Wärmemenge BHKW: {results['Wärmemenge']:.2f} MWh")
    print(f"Wärmeleistung BHKW: {results['Wärmeleistung_L']} kW")
    print(f"Brennstoffbedarf BHKW: {results['Brennstoffbedarf']:.2f} MWh")
    print(f"Wärmegestehungskosten BHKW: {results['WGK']:.2f} €/MWh")
    print(f"Strommenge BHKW: {results['Strommenge']:.2f} MWh")
    print(f"Stromleistung BHKW: {results['el_Leistung_L']} kW")
    print(f"Anzahl Starts BHKW: {results['Anzahl_Starts']}")
    print(f"Betriebsstunden BHKW: {results['Betriebsstunden']} h")
    print(f"Betriebsstunden pro Start BHKW: {results['Betriebsstunden_pro_Start']:.2f} h")
    print(f"spezifische CO2-Emissionen BHKW: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf BHKW: {results['primärenergie']:.2f} MWh")

def test_chp_storage(Last_L, duration, economic_parameters, chp=CHP(name="BHKW", th_Leistung_kW=100, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850, el_Wirkungsgrad=0.33, 
                                                                        KWK_Wirkungsgrad=0.9, min_Teillast=0.7, speicher_aktiv=True, Speicher_Volumen_BHKW=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, 
                                                                        min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750, active=True, opt_BHKW_min=0, opt_BHKW_max=1000, 
                                                                        opt_BHKW_Speicher_min=0, opt_BHKW_Speicher_max=100)):

    results = chp.calculate(economic_parameters, duration, Last_L)
    
    print(f"Wärmemenge BHKW mit Speicher: {results['Wärmemenge']:.2f} MWh")
    print(f"Wärmeleistung BHKW mit Speicher: {results['Wärmeleistung_L']} kW")
    print(f"Wärmeleistung Speicher BHKW: {results['Wärmeleistung_Speicher_L']} kW")
    print(f"Brennstoffbedarf BHKW mit Speicher: {results['Brennstoffbedarf']:.2f} MWh")
    print(f"Wärmegestehungskosten BHKW mit Speicher: {results['WGK']:.2f} €/MWh")
    print(f"Strommenge BHKW mit Speicher: {results['Strommenge']:.2f} MWh")
    print(f"Stromleistung BHKW mit Speicher: {results['el_Leistung_L']} kW")
    print(f"Anzahl Starts BHKW mit Speicher: {results['Anzahl_Starts']}")
    print(f"Betriebsstunden BHKW mit Speicher: {results['Betriebsstunden']} h")
    print(f"Betriebsstunden pro Start BHKW mit Speicher: {results['Betriebsstunden_pro_Start']:.2f} h")
    print(f"spezifische CO2-Emissionen BHKW mit Speicher: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf BHKW mit Speicher: {results['primärenergie']:.2f} MWh")

def test_waste_heat_pump(Last_L, duration, economic_parameters, VLT_L, COP_data, wasteHeatPump=WasteHeatPump(name="Abwärmepumpe", Kühlleistung_Abwärme=50, Temperatur_Abwärme=30, spez_Investitionskosten_Abwärme=500, spezifische_Investitionskosten_WP=1000, min_Teillast=0.2)):

    results = wasteHeatPump.calculate(economic_parameters, duration, Last_L, VLT_L=VLT_L, COP_data=COP_data)
    
    print(f"Wärmemenge Abwärme-WP: {results['Wärmemenge']:.2f} MWh")
    print(f"Strombedarf Abwärme-WP: {results['Strombedarf']:.2f} MWh")
    print(f"Wärmeleistung Abwärme-WP: {results['Wärmeleistung_L']} kW")
    print(f"elektrische Leistung Abwärme-WP: {results['el_Leistung_L']} kW")
    print(f"Wärmegestehungskosten Abwärme-WP: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Abwärme-WP: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Abwärme-WP: {results['primärenergie']:.2f} MWh")

def test_river_heat_pump(Last_L, duration, economic_parameters, VLT_L, COP_data, riverHeatPump=RiverHeatPump(name="Flusswärmepumpe", Wärmeleistung_FW_WP=200, Temperatur_FW_WP=10, dT=0, spez_Investitionskosten_Flusswasser=1000, spezifische_Investitionskosten_WP=1000, min_Teillast=0.2)):   
    
    results = riverHeatPump.calculate(economic_parameters, duration, Last_L, VLT_L=VLT_L, COP_data=COP_data)
    
    print(f"Wärmemenge Fluss-WP: {results['Wärmemenge']:.2f} MWh")
    print(f"Strombedarf Fluss-WP: {results['Strombedarf']:.2f} MWh")
    print(f"Wärmeleistung Fluss-WP: {results['Wärmeleistung_L']} kW")
    print(f"elektrische Leistung Fluss-WP: {results['el_Leistung_L']} kW")
    print(f"Wärmegestehungskosten Fluss-WP: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Fluss-WP: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Fluss-WP: {results['primärenergie']:.2f} MWh")

def test_geothermal_heat_pump(Last_L, duration, economic_parameters, VLT_L, COP_data, geothermalHeatPump=Geothermal(name="Geothermie", Fläche=200, Bohrtiefe=100, Temperatur_Geothermie=10, spez_Bohrkosten=100, spez_Entzugsleistung=50, Vollbenutzungsstunden=2400, Abstand_Sonden=10, spezifische_Investitionskosten_WP=1000, min_Teillast=0.2)):
    
    results = geothermalHeatPump.calculate(economic_parameters, duration, Last_L, VLT_L=VLT_L, COP_data=COP_data)

    print(f"Wärmemenge Geothermie-WP: {results['Wärmemenge']:.2f} MWh")
    print(f"Strombedarf Geothermie-WP: {results['Strombedarf']:.2f} MWh")
    print(f"Wärmeleistung Geothermie-WP: {results['Wärmeleistung_L']} kW")
    print(f"elektrische Leistung Geothermie-WP: {results['el_Leistung_L']} kW")
    print(f"Wärmegestehungskosten Geothermie-WP: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Geothermie-WP: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Geothermie-WP: {results['primärenergie']:.2f} MWh")

def test_solar_thermal(Last_L, duration, economic_parameters, VLT_L, RLT_L, TRY_data, time_steps, solarThermal=SolarThermal(name="Solarthermie", bruttofläche_STA=200, vs=20, Typ="Vakuumröhrenkollektor", 
                                                                                                            kosten_speicher_spez=750, kosten_fk_spez=430, kosten_vrk_spez=590, Tsmax=90, 
                                                                                                            Longitude=-14.4222, STD_Longitude=-15, Latitude=51.1676, East_West_collector_azimuth_angle=0, 
                                                                                                            Collector_tilt_angle=36, Tm_rl=60, Qsa=0, Vorwärmung_K=8, DT_WT_Solar_K=5, DT_WT_Netz_K=5, 
                                                                                                            opt_volume_min=0, opt_volume_max=200, opt_area_min=0, opt_area_max=2000)):

    results = solarThermal.calculate(economic_parameters, duration, Last_L, VLT_L=VLT_L, RLT_L=RLT_L, TRY_data=TRY_data, time_steps=time_steps)

    print(f"Wärmemenge Solarthermie: {results['Wärmemenge']:.2f} MWh")
    print(f"Wärmeleistung Solarthermie: {results['Wärmeleistung_L']} kW")
    print(f"Wärmegestehungskosten Solarthermie: {results['WGK']:.2f} €/MWh")
    print(f"spezifische CO2-Emissionen Solarthermie: {results['spec_co2_total']:.2f} tCO2/MWh")
    print(f"Primärenergiebedarf Solarthermie: {results['primärenergie']:.2f} MWh")
    print(f"Speicherladung Solarthermie: {results['Speicherladung_L']} kW")
    print(f"Speicherfüllstand Solarthermie: {results['Speicherfüllstand_L']} MWh")

if __name__ == "__main__":
    # Heat demand profile for one year (8760 hours)
    min_last = 50
    max_last = 400
    Last_L = np.random.randint(min_last, max_last, 8760).astype(float)

    # Duration
    duration = 1

    # Arrays for VLT and RLT, assuming constant values for the example
    VLT_L, RLT_L = np.full(8760, 80), np.full(8760, 55)

    # Load COP data from CSV file
    COP_data = np.genfromtxt("examples/data/COP/Kennlinien WP.csv", delimiter=';')

    # Filename for TRY data
    TRY_data = import_TRY("examples/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat")

    # Time steps for the simulation
    # Angaben zum zu betrchtende Zeitraum
    # Erstelle ein Array mit stündlichen Zeitwerten für ein Jahr
    start_date = np.datetime64('2019-01-01')
    end_date = np.datetime64('2020-01-01', 'D')  # Enddatum ist exklusiv, daher 'D' für Tage

    # Erstelle das Array mit stündlichen Zeitwerten für ein Jahr
    time_steps = np.arange(start_date, end_date, dtype='datetime64[h]')


    # Define economic parameters
    electricity_price = 150 # €/MWh
    gas_price = 70 # €/MWh
    wood_price = 60 # €/MWh
    q = 1.05
    r = 1.03
    T = 20
    BEW = "Nein"
    hourly_rate = 45

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
    
    # Test Gas Boiler
    gBoiler = GasBoiler(name="Gas_Boiler_1", thermal_capacity_kW=1000, spez_Investitionskosten=30, Nutzungsgrad=0.9)
    test_gas_boiler(Last_L, duration, economic_parameters, gBoiler)

    # Test Power to Heat
    PTH = PowerToHeat(name="PowerToHeat_1", thermal_capacity_kW=1000, spez_Investitionskosten=30, Nutzungsgrad=0.98)    
    test_power_to_heat(Last_L, duration, economic_parameters, PTH)

    # Test Biomass Boiler without storage
    bBoiler = BiomassBoiler(name="Biomasss_Boiler_1", thermal_capacity_kW=200, Größe_Holzlager=40, spez_Investitionskosten=200, 
                                           spez_Investitionskosten_Holzlager=400, Nutzungsgrad_BMK=0.8, min_Teillast=0.3, speicher_aktiv=False, 
                                           Speicher_Volumen=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, min_fill=0.2, max_fill=0.8, 
                                           spez_Investitionskosten_Speicher=750, active=True, opt_BMK_min=0, opt_BMK_max=1000, opt_Speicher_min=0, 
                                           opt_Speicher_max=100)
    test_biomass_boiler(Last_L, duration, economic_parameters, bBoiler)

    # Test Biomass Boiler with storage
    bBoiler_storage = BiomassBoiler(name="Biomasss_Boiler_1", thermal_capacity_kW=200, Größe_Holzlager=40, spez_Investitionskosten=200, 
                                                   spez_Investitionskosten_Holzlager=400, Nutzungsgrad_BMK=0.8, min_Teillast=0.3, speicher_aktiv=True, 
                                                   Speicher_Volumen=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, min_fill=0.2, max_fill=0.8, 
                                                   spez_Investitionskosten_Speicher=750, active=True, opt_BMK_min=0, opt_BMK_max=1000, opt_Speicher_min=0, 
                                                   opt_Speicher_max=100)
    test_biomass_boiler_storage(Last_L, duration, economic_parameters, bBoiler_storage)

    # Test CHP without storage
    CHP_1 = CHP(name="BHKW", th_Leistung_kW=100, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850, el_Wirkungsgrad=0.33, 
                  KWK_Wirkungsgrad=0.9, min_Teillast=0.7, speicher_aktiv=False, Speicher_Volumen_BHKW=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, 
                  min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750, active=True, opt_BHKW_min=0, opt_BHKW_max=1000, opt_BHKW_Speicher_min=0, 
                  opt_BHKW_Speicher_max=100)    
    test_chp(Last_L, duration, economic_parameters, CHP_1)

    # Test CHP with storage
    CHP_storage = CHP(name="BHKW", th_Leistung_kW=100, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850, el_Wirkungsgrad=0.33, 
                          KWK_Wirkungsgrad=0.9, min_Teillast=0.7, speicher_aktiv=True, Speicher_Volumen_BHKW=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0, 
                          min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750, active=True, opt_BHKW_min=0, opt_BHKW_max=1000, opt_BHKW_Speicher_min=0, 
                          opt_BHKW_Speicher_max=100)
    test_chp_storage(Last_L, duration, economic_parameters, CHP_storage)

    # Test Waste Heat Pump
    wasteHeatPump = WasteHeatPump(name="Abwärmepumpe", Kühlleistung_Abwärme=50, Temperatur_Abwärme=30, spez_Investitionskosten_Abwärme=500, 
                                             spezifische_Investitionskosten_WP=1000, min_Teillast=0.2)
    test_waste_heat_pump(Last_L, duration, economic_parameters, VLT_L, COP_data, wasteHeatPump)

    # Test River Heat Pump
    riverHeatPump = RiverHeatPump(name="Flusswärmepumpe", Wärmeleistung_FW_WP=200, Temperatur_FW_WP=10, dT=0, spez_Investitionskosten_Flusswasser=1000, 
                                             spezifische_Investitionskosten_WP=1000, min_Teillast=0.2)
    test_river_heat_pump(Last_L, duration, economic_parameters, VLT_L, COP_data, riverHeatPump) 

    # Test Geothermal Heat Pump
    geothermal_heat_pump = Geothermal(name="Geothermie", Fläche=200, Bohrtiefe=100, Temperatur_Geothermie=10, spez_Bohrkosten=100, spez_Entzugsleistung=50,
                                                Vollbenutzungsstunden=2400, Abstand_Sonden=10, spezifische_Investitionskosten_WP=1000, min_Teillast=0.2)
    test_geothermal_heat_pump(Last_L, duration, economic_parameters, VLT_L, COP_data, geothermal_heat_pump)

    # Test Solar Thermal
    solarThermal = SolarThermal(name="Solarthermie", bruttofläche_STA=200, vs=20, Typ="Vakuumröhrenkollektor", kosten_speicher_spez=750, kosten_fk_spez=430, kosten_vrk_spez=590, 
                                            Tsmax=90, Longitude=-14.4222, STD_Longitude=-15, Latitude=51.1676, East_West_collector_azimuth_angle=0, Collector_tilt_angle=36, Tm_rl=60, 
                                            Qsa=0, Vorwärmung_K=8, DT_WT_Solar_K=5, DT_WT_Netz_K=5, opt_volume_min=0, opt_volume_max=200, opt_area_min=0, opt_area_max=2000)
    test_solar_thermal(Last_L, duration, economic_parameters, VLT_L, RLT_L, TRY_data, time_steps, solarThermal)
